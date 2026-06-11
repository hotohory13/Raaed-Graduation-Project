import os
import logging
from crewai import Agent, Task, Crew, Process, LLM
from helpers.config import get_settings
from .prompts import ORCHESTRATOR_SYSTEM_PROMPT, QUIZ_AGENT_SYSTEM_PROMPT
from .tools import create_rag_tools
from pydantic import BaseModel, Field
from typing import List, Dict
import json

# Disable CrewAI telemetry to speed up execution
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

logger = logging.getLogger("uvicorn.error")

class OpenRouterLLM(LLM):
    """
    Custom LLM wrapper for OpenRouter to strip out unsupported 'cache_breakpoint' keys
    inserted by CrewAI before passing messages to LiteLLM/OpenRouter.
    """
    def _format_messages_for_provider(self, messages):
        formatted = super()._format_messages_for_provider(messages)
        cleaned = []
        for msg in formatted:
            cleaned_msg = {k: v for k, v in msg.items() if k != "cache_breakpoint"}
            cleaned.append(cleaned_msg)
        return cleaned

class QuizQuestion(BaseModel):
    question: str = Field(description="The multiple-choice question text")
    options: Dict[str, str] = Field(description="Exactly 4 options with keys A, B, C, D")
    correct_answer: str = Field(description="The correct option key: A, B, C, or D")
    explanation: str = Field(description="A brief explanation of why the answer is correct")

class QuizModel(BaseModel):
    topic: str = Field(description="The topic or subject of the quiz")
    questions: List[QuizQuestion] = Field(description="List of multiple-choice questions")

def get_llm():
    settings = get_settings()
    api_key = settings.OPENAI_API_KEY
    api_url = settings.OPENAI_API_URL or "https://openrouter.ai/api/v1"
    model_name = settings.GENERATION_MODEL_ID or "openai/gpt-4o-mini"
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured in settings")
        
    if not model_name.startswith("openrouter/"):
        model_name = f"openrouter/{model_name}"
        
    return OpenRouterLLM(
        model=model_name,
        base_url=api_url,
        api_key=api_key,
        temperature=0.2
    )

def create_orchestrator_tools(nlp_controller, project):
    # Get base RAG tools
    rag_tools = create_rag_tools(nlp_controller, project)
    
    from crewai.tools import tool
    
    @tool("Generate Quiz from Course Materials")
    def generate_quiz_tool(topic: str) -> str:
        """
        Generate a multiple-choice quiz on a specific topic using the course materials.
        Use this tool when the student explicitly requests a quiz, exam, or test on a topic.
        Input should be the topic of the quiz.
        """
        try:
            quiz_result = run_agent_quiz(
                project_id=project.project_id,
                topic=topic,
                nlp_controller=nlp_controller,
                project=project,
                num_questions=5
            )
            return json.dumps(quiz_result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Quiz tool error: {e}")
            return f"Error generating quiz: {str(e)}"
            
    return [*rag_tools, generate_quiz_tool]

def run_agent_chat(
    session_id: str,
    project_id: str,
    user_message: str,
    chat_history: list,
    nlp_controller,
    project,
    active_guidelines: list = None,
) -> str:
    """
    Runs the orchestrator agent (Raaed) for a single conversation turn.
    """
    llm = get_llm()
    tools = create_orchestrator_tools(nlp_controller, project)
    
    orchestrator_agent = Agent(
        role="رائد (Study Assistant)",
        goal="Help students understand their course materials and study effectively.",
        backstory=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # Format chat history
    formatted_history = ""
    for msg in chat_history:
        role = "Student" if msg["role"] == "user" else "Raaed"
        formatted_history += f"{role}: {msg['content']}\n"
        
    # Format active guidelines from instructor
    guidelines_prompt = ""
    if active_guidelines:
        guidelines_prompt = "\n## Active Instructor Guidelines for today's session:\n"
        for g in active_guidelines:
            guidelines_prompt += f"- [{g.task_id}] (Type: {g.task_type}, Priority: {g.priority}): {g.description}\n"
        guidelines_prompt += "\nAs Raaed, you MUST steer the conversation and focus your help on these guidelines to help the student learn what the instructor specified.\n"

    chat_task = Task(
        description=f"""
The student is asking a question or requesting study help.
Here is the previous conversation history:
{formatted_history}
{guidelines_prompt}
Student's new message: "{user_message}"

Decide whether to use the search or answer tools to find information in the course materials, 
or call the 'Generate Quiz from Course Materials' tool if they want a quiz, 
or respond directly if it is a general message (greeting, simple chat).
Always respond in a friendly, supportive tone matching the student's language (Arabic or English).
""",
        expected_output="A helpful, accurate response to the student's message.",
        agent=orchestrator_agent
    )
    
    crew = Crew(
        agents=[orchestrator_agent],
        tasks=[chat_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    return str(result.raw)


def run_agent_quiz(
    project_id: str,
    topic: str,
    nlp_controller,
    project,
    num_questions: int = 5
) -> dict:
    """
    Runs the Quiz Generator agent directly to produce a structured JSON quiz.
    """
    llm = get_llm()
    tools = create_rag_tools(nlp_controller, project)
    
    quiz_agent = Agent(
        role="Quiz Generator Specialist",
        goal="Create high-quality, accurate multiple-choice quizzes from course materials.",
        backstory=QUIZ_AGENT_SYSTEM_PROMPT,
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    quiz_task = Task(
        description=f"""
Search the course materials for content related to the topic: "{topic}".
Based on the retrieved content, generate exactly {num_questions} multiple-choice questions.
Each question must have 4 options (A, B, C, D), a single correct answer, and an explanation.
You MUST output a valid JSON object matching the requested schema.
""",
        expected_output="A structured JSON quiz matching the schema.",
        agent=quiz_agent,
        output_json=QuizModel
    )
    
    crew = Crew(
        agents=[quiz_agent],
        tasks=[quiz_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    
    # Return parsed JSON dict
    if result.json_dict:
        return result.json_dict
    elif result.pydantic:
        return result.pydantic.model_dump()
    else:
        # Fallback parsing
        try:
            cleaned_raw = str(result.raw).strip()
            if "```json" in cleaned_raw:
                cleaned_raw = cleaned_raw.split("```json")[1].split("```")[0].strip()
            return json.loads(cleaned_raw)
        except Exception as e:
            logger.error(f"Failed to parse quiz raw output: {e}")
            return {
                "topic": topic,
                "questions": [
                    {
                        "question": "Failed to generate quiz questions dynamically.",
                        "options": {"A": "N/A", "B": "N/A", "C": "N/A", "D": "N/A"},
                        "correct_answer": "A",
                        "explanation": str(e)
                    }
                ]
            }
