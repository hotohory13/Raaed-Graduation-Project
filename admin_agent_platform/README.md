# Admin Agent Platform - Phase 1

This folder contains the complete, isolated implementation of **Phase 1 of the Educational Multi-Agent Platform**. 

The core responsibility of the **Admin Agent** is to ingest natural language requests from users (students/instructors), analyze the intent, classify the task parameters, and register them into an Excel-based shared memory task queue (`tasks.xlsx`) to be processed later by a Teaching Assistant (TA) agent.

---

## Architecture & Workflow Phases

Every request sent to the API goes through a structured pipeline of six distinct phases:

### Phase 1: API Request Ingestion
* **Endpoint**: `POST /task/create`
* **Handler**: [main.py](file:///c:/Users/Admin/Raaed-Graduation-Project/admin_agent_platform/main.py)
* **Description**: FastAPI receives a natural language task description (e.g. `"summarize chapter 10"`). It instantiates a fresh, stateless CrewAI workflow to isolate token counts and prevent cross-request memory contamination.

### Phase 2: Natural Language Analysis (CrewAI Task 1)
* **Agent**: `Admin Agent / Request Analyzer`
* **Model**: `openai/llama-3.1-8b-instant` (hosted on Groq)
* **Description**: The agent interprets the user's intent and extracts metadata:
  * **Task Type**: Classifies the request into `Quiz`, `Assignment`, `Flashcards`, `Study Guide`, `Summary`, or `Exam` (defaults to `Quiz`).
  * **Course**: Identifies the course name (defaults to `General` if unspecified).
  * **Description**: Generates a clean, concise description of the task.
  * **Priority**: Determines urgency (`High` for Exams/Quizzes, `Medium` for Assignments, `Low` for Study Guides/Summaries).
  * **Notes**: Extracts specific details like MCQ counts, chapter numbers, etc.

### Phase 3: Task Record Formatting (CrewAI Task 2)
* **Description**: The agent formats the analyzed details into a standardized task record:
  * Hardcodes the `assigned_agent` to `"TA"`.
  * Hardcodes the initial task `status` to `"Pending"`.
  * Normalizes the notes and descriptions into structured layouts.

### Phase 4: Schema Validation (CrewAI Task 3)
* **Description**: The formatted data is parsed and validated against a Pydantic model (`TaskRecordModel`):
  * Ensures all required fields are present and typed correctly.
  * Prevents malformed or corrupted metadata from entering the database.

### Phase 5: Excel Database Persistence
* **Utility**: [excel_writer.py](file:///c:/Users/Admin/Raaed-Graduation-Project/admin_agent_platform/excel_writer.py)
* **Description**: Once validated, the python execution thread:
  1. Opens the Excel file [tasks.xlsx](file:///c:/Users/Admin/Raaed-Graduation-Project/admin_agent_platform/tasks.xlsx).
  2. Scans the `TaskQueue` sheet to auto-increment and generate the next sequential Task ID (e.g., `T022`).
  3. Records a precise timestamp (`Created_At`).
  4. Appends a clean, single row containing all metadata.

### Phase 6: Client HTTP Response
* **Description**: The FastAPI endpoint returns an HTTP `201 Created` status with the generated `task_id` (e.g. `{"task_id": "T022", "status": "created"}`) to the calling system.

---

## Technical Solutions & Bug Fixes

### 1. Bypassing AgentRouter `AuthenticationError`
During Pydantic schema validation, CrewAI uses the `Instructor` library. By default, `instructor`'s internal client inherits global host environment variables like `OPENAI_API_BASE` and `OPENAI_API_KEY`. On machines configured with global variables pointing to `AgentRouter.org` (e.g., `https://agentrouter.org/v1`), this caused Instructor requests to route to AgentRouter, resulting in HTTP 500 errors (`OpenAIException - unauthorized client detected`).

* **Resolution**: In [crew.py](file:///c:/Users/Admin/Raaed-Graduation-Project/admin_agent_platform/crew.py), we override these variables inside the request runner to force direct connections to Groq:
  ```python
  os.environ["OPENAI_API_KEY"] = GROQ_API_KEY
  os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
  os.environ["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"
  ```
This routes all internal crew and schema parser requests securely and directly to Groq.

### 2. Thread-Safety & Rate Limits
* **Stateless Runs**: To comply with Groq's low TPM rate limits (6,000 TPM), all LLM and Crew objects are created fresh inside `run_admin_crew()`. This prevents token accumulation in conversational memory across requests.
* **Write Scoping**: The Excel writing tool is executed in python code *after* a successful crew kickoff, preventing the agent from triggering duplicate database writes during intermediate reasoning loops.

---

## Running and Testing the Platform

### Prerequisites
* Python 3.10+
* Groq API Key set in `admin_agent_platform/.env`

### Steps to Run

1. **Activate the Isolated Virtual Environment**:
   * **PowerShell**:
     ```powershell
     $env:PYTHONUTF8=1
     .\admin_agent_platform\.venv\Scripts\Activate.ps1
     ```
   * **Command Prompt / Git Bash**:
     ```bash
     set PYTHONUTF8=1
     source admin_agent_platform/.venv/Scripts/activate
     ```

2. **Start the FastAPI Server**:
   ```bash
   cd admin_agent_platform
   uvicorn main:app --reload --port 8000
   ```

3. **Run the Test API Client**:
   In a separate terminal (with the `.venv` activated):
   ```bash
   python test_api.py
   ```
   *This client tests multiple requests sequentially with a 60-second delay to respect free-tier rate limits.*
