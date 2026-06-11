import os
import re
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from google_sheets_writer import write_task_to_google_sheets_func

# Disable CrewAI telemetry to speed up execution and avoid connection timeouts
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

# Load environment variables from .env file
load_dotenv()

# Verify OpenRouter configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://openrouter.ai/api/v1")
GENERATION_MODEL_ID = os.getenv("GENERATION_MODEL_ID", "openai/gpt-4o-mini")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

# Force environment variables for LiteLLM/Instructor to use OpenRouter endpoint,
# overriding any global AgentRouter environment variables that cause AuthenticationErrors.
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_API_BASE"] = OPENAI_API_URL
os.environ["OPENAI_BASE_URL"] = OPENAI_API_URL

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

from pydantic import BaseModel, Field

class TaskRecordModel(BaseModel):
    task_type: str = Field(description="Must be one of: Quiz, Assignment, Flashcards, Study Guide, Summary, Exam")
    description: str = Field(description="Clear, concise explanation of the task")
    course: str = Field(description="The course or subject name (e.g. Machine Learning, Deep Learning). Default to 'General'")
    priority: str = Field(description="Priority level (High, Medium, Low)")
    assigned_agent: str = Field(default="TA", description="The agent assigned to handle the task (always 'TA')")
    status: str = Field(default="Pending", description="The initial status (always 'Pending')")
    notes: str = Field(default="", description="Any extracted parameters, MCQ counts, chapters, formatting, etc.")

def run_admin_crew(user_request: str) -> dict:
    """
    Executes the Admin Crew to process the user request, 
    extract parameters as structured JSON, and then writes the
    record to Google Sheets deterministically in python.
    """
    # Initialize the OpenRouter LLM
    model_name = GENERATION_MODEL_ID
    if not model_name.startswith("openrouter/"):
        model_name = f"openrouter/{model_name}"

    llm = OpenRouterLLM(
        model=model_name,
        base_url=OPENAI_API_URL,
        api_key=OPENAI_API_KEY,
        temperature=0.1
    )

    # Define the Admin Agent fresh for this request (no tools needed here, we write in Python!)
    admin_agent = Agent(
        role="Admin Agent / Request Analyzer",
        goal="Analyze natural language educational requests, classify their task types, extract details, and format them into a structured task record.",
        backstory="""You are the core admin coordinator of an educational multi-agent platform. 
You specialize in processing student and instructor requests (like creating quizzes, exams, flashcards, or study guides). 
Your job is to analyze the user's intent, extract parameters (course name, description, priority, notes), 
assign the task to the TA agent, and structure the record for database storage.""",
        tools=[],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    # Task 1: Analyze Request Intent and Extract Details
    analyze_request_task = Task(
        description="""Analyze the user's natural language request: "{user_request}".
Identify the following information:
1. Task Type: Classify into one of: Quiz, Assignment, Flashcards, Study Guide, Summary, Exam. If not clear, default to Quiz.
2. Course: Extract the course or subject name. Default to "General" if not specified.
3. Description: Generate a clear, concise description of what needs to be created.
4. Priority: Determine priority (High if urgent, or if it is an Exam or Quiz; Medium for Assignments; Low for Flashcards/Study Guides/Summaries, unless specified otherwise).
5. Notes: Extract specific parameters or formatting details (e.g. "20 MCQs, Chapter 3", "5 pages long").""",
        expected_output="A structured summary of the request details: Task Type, Course, Description, Priority, and Notes.",
        agent=admin_agent
    )

    # Task 2: Format and Generate Task Record
    create_record_task = Task(
        description="""Using the extracted details from the previous task, prepare a final record for the task.
The task must be assigned to the "TA" agent, and its initial status must be "Pending".
Format the final description and notes so they are clean, actionable, and ready to be stored in the database.""",
        expected_output="A final structured representation of the task record.",
        agent=admin_agent
    )

    # Task 3: Format Structured Task Record JSON
    write_excel_task = Task(
        description="""Compile the final task record with all fields correctly extracted.
You MUST output it as a valid JSON object matching the requested schema:
- task_type: Quiz, Assignment, Flashcards, Study Guide, Summary, or Exam
- description: clear, concise description
- course: subject name (default to 'General')
- priority: High, Medium, Low
- assigned_agent: 'TA'
- status: 'Pending'
- notes: MCQ counts, chapter numbers, etc. (default to empty string)""",
        expected_output="A validated task record matching the TaskRecordModel schema.",
        agent=admin_agent,
        output_json=TaskRecordModel
    )

    # Define the Crew fresh for this request
    admin_crew = Crew(
        agents=[admin_agent],
        tasks=[analyze_request_task, create_record_task, write_excel_task],
        process=Process.sequential,
        verbose=True
    )

    print(f"Running Admin Crew for request: '{user_request}'")
    result = admin_crew.kickoff(inputs={"user_request": user_request})
    
    # Parse the Pydantic structured output from CrewAI and write to Excel
    task_id = "UNKNOWN"
    write_msg = ""
    try:
        task_data = None
        if result.json_dict:
            task_data = result.json_dict
        elif result.pydantic:
            task_data = result.pydantic.model_dump()
        else:
            # Fallback string parsing
            import json
            result_str = str(result.raw)
            match = re.search(r"\{.*\}", result_str, re.DOTALL)
            if match:
                task_data = json.loads(match.group(0))
        
        if task_data:
            print(f"Extracted task data: {task_data}")
            from google_sheets_writer import write_task_to_google_sheets_func
            write_msg = write_task_to_google_sheets_func(
                task_type=task_data.get("task_type", "Quiz"),
                description=task_data.get("description", ""),
                course=task_data.get("course", "General"),
                priority=task_data.get("priority", "High"),
                assigned_agent=task_data.get("assigned_agent", "TA"),
                status=task_data.get("status", "Pending"),
                notes=task_data.get("notes", "")
            )
            print(f"Google Sheets write result: {write_msg}")
            
            # Extract Task_ID from writing result
            match = re.search(r"T\d+", write_msg)
            if match:
                task_id = match.group(0)
                return {"task_id": task_id, "status": "created", "crew_output": write_msg}
                
    except Exception as e:
        print(f"Failed to parse or write structured agent output: {e}")

    # Fallback: Read Google Sheet to find the last added record's Task_ID
    try:
        from google_sheets_writer import get_google_sheets_service, SPREADSHEET_ID
        service = get_google_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Shared Memory!A:A"
        ).execute()
        rows = result.get("values", [])
        if len(rows) > 1:
            last_task_id = str(rows[-1][0])
            return {"task_id": last_task_id, "status": "created", "crew_output": write_msg or "Fallback used"}
    except Exception as e:
        print(f"Fallback Task_ID extraction failed: {e}")
        
    return {"task_id": "UNKNOWN", "status": "created_with_extraction_warning", "crew_output": write_msg or "Failed"}
