from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from routes.schemes.agent import (
    ChatRequest, ChatResponse, QuizRequest, QuizResponse, 
    SessionClearResponse, TaskWebhookRequest
)
from models.ProjectModel import ProjectModel
from models.db_schemes.instructor_guideline import InstructorGuideline
from models.InstructorGuidelineModel import InstructorGuidelineModel
from controllers import NLPController
from agent import session_manager, run_agent_chat, run_agent_quiz
import logging

logger = logging.getLogger("uvicorn.error")

agent_router = APIRouter(
    prefix="/api/v1/agent",
    tags=["api_v1", "agent"],
)

@agent_router.post("/chat/{project_id}", response_model=ChatResponse)
async def chat_with_agent(request: Request, project_id: str, chat_request: ChatRequest):
    try:
        # 1. Fetch or create project
        project_model = await ProjectModel.create_instance(
            db_client=request.app.db_client
        )
        project = await project_model.get_project_or_create_one(
            project_id=project_id
        )
        if not project:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Project not found"}
            )
            
        # 2. Get or create session
        session_id = session_manager.get_or_create_session(chat_request.session_id, project_id)
        
        # 3. Retrieve history
        history = session_manager.get_history(session_id)
        
        # 4. Instantiate NLPController
        nlp_controller = NLPController(
            vectordb_client=request.app.vectordb_client,
            generation_client=request.app.generation_client,
            embedding_client=request.app.embedding_client,
            template_parser=request.app.template_parser,
            reranker_client=getattr(request.app, 'reranker_client', None)
        )
        
        # Query active instructor guidelines
        guideline_model = await InstructorGuidelineModel.create_instance(
            db_client=request.app.db_client
        )
        active_guidelines = await guideline_model.get_active_guidelines(project_id)
        
        # 5. Run agent chat
        response_text = run_agent_chat(
            session_id=session_id,
            project_id=project_id,
            user_message=chat_request.message,
            chat_history=history,
            nlp_controller=nlp_controller,
            project=project,
            active_guidelines=active_guidelines
        )

        
        # 6. Update history
        session_manager.add_message(session_id, "user", chat_request.message)
        session_manager.add_message(session_id, "assistant", response_text)
        
        return ChatResponse(
            response=response_text,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An error occurred: {str(e)}"}
        )

@agent_router.post("/quiz/{project_id}", response_model=QuizResponse)
async def generate_quiz(request: Request, project_id: str, quiz_request: QuizRequest):
    try:
        # 1. Fetch or create project
        project_model = await ProjectModel.create_instance(
            db_client=request.app.db_client
        )
        project = await project_model.get_project_or_create_one(
            project_id=project_id
        )
        if not project:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Project not found"}
            )
            
        # 2. Instantiate NLPController
        nlp_controller = NLPController(
            vectordb_client=request.app.vectordb_client,
            generation_client=request.app.generation_client,
            embedding_client=request.app.embedding_client,
            template_parser=request.app.template_parser,
            reranker_client=getattr(request.app, 'reranker_client', None)
        )
        
        # 3. Run quiz agent directly
        quiz_data = run_agent_quiz(
            project_id=project_id,
            topic=quiz_request.topic,
            nlp_controller=nlp_controller,
            project=project,
            num_questions=quiz_request.num_questions
        )
        
        return QuizResponse(
            quiz=quiz_data
        )
        
    except Exception as e:
        logger.error(f"Error in quiz endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"An error occurred: {str(e)}"}
        )

@agent_router.delete("/session/{session_id}", response_model=SessionClearResponse)
async def clear_session(session_id: str):
    existed = session_manager.clear_session(session_id)
    status_msg = "cleared" if existed else "not_found"
    return SessionClearResponse(status=status_msg)

@agent_router.post("/webhook/task")
async def task_webhook(request: Request, payload: TaskWebhookRequest):
    try:
        # Normalize course name to project_id (lowercase alphanumeric)
        # e.g., "Machine Learning" -> "machinelearning"
        course_name = payload.course.strip()
        import re
        project_id = re.sub(r'[^a-zA-Z0-9]', '', course_name.lower())
        if not project_id:
            project_id = "general"

        # Fetch or create project in DB
        project_model = await ProjectModel.create_instance(
            db_client=request.app.db_client
        )
        await project_model.get_project_or_create_one(
            project_id=project_id
        )

        # Create guideline object
        guideline = InstructorGuideline(
            project_id=project_id,
            task_id=payload.task_id,
            task_type=payload.task_type,
            description=payload.description,
            priority=payload.priority,
            notes=payload.notes or "",
            created_at=payload.created_at,
            is_active=payload.is_active if payload.is_active is not None else True
        )

        # Save to DB
        guideline_model = await InstructorGuidelineModel.create_instance(
            db_client=request.app.db_client
        )
        await guideline_model.create_or_update_guideline(guideline)

        logger.info(f"Webhook processed successfully for task {payload.task_id} under project {project_id}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": f"Guideline successfully registered for project: {project_id}",
                "project_id": project_id,
                "task_id": payload.task_id
            }
        )

    except Exception as e:
        logger.error(f"Error in task webhook: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Failed to register task: {str(e)}"}
        )
