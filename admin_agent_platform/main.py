import logging
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from crew import run_admin_crew

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("AdminAgentAPI")

# Initialize FastAPI App
app = FastAPI(
    title="Admin Agent API",
    description="Phase 1 Admin Agent platform backend with Google Sheets-based shared memory.",
    version="1.0.0"
)

# Request schema
class TaskCreateRequest(BaseModel):
    request: str = Field(
        ..., 
        description="The natural language request for a task.",
        example="Create a quiz about Machine Learning Chapter 3 with 20 MCQ questions"
    )

# Response schema
class TaskCreateResponse(BaseModel):
    task_id: str = Field(..., description="The generated task ID, e.g., T001")
    status: str = Field(..., description="The status of the task creation request.")

@app.post(
    "/task/create",
    response_model=TaskCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task and queue it in Google Sheets memory"
)
def create_task(payload: TaskCreateRequest):
    """
    Receives a natural language request, extracts task parameters using a CrewAI Agent,
    writes the structured task record to Google Sheets, and returns the generated task ID.
    """
    logger.info(f"Received task creation request: '{payload.request}'")
    try:
        # Run CrewAI workflow to analyze request and write to Excel
        result = run_admin_crew(payload.request)
        
        logger.info(f"Task successfully created. ID: {result['task_id']}. Status: {result['status']}")
        
        return TaskCreateResponse(
            task_id=result["task_id"],
            status="created"
        )
    except Exception as e:
        logger.exception("An error occurred during task processing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process task: {str(e)}"
        )

@app.get("/health", status_code=status.HTTP_200_OK, summary="API Health Check")
def health_check():
    """Returns the health status of the API service."""
    return {"status": "healthy", "service": "Admin Agent Platform"}
