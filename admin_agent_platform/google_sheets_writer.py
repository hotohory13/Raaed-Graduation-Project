import os
import re
import datetime
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Config
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Ensure paths are relative to this script's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

def get_google_sheets_service():
    """
    Authenticates with the Google Sheets API using client ID/secret,
    running local server on first load, and caching OAuth credentials.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired Google credentials...")
            creds.refresh(Request())
        else:
            print("Authenticating with Google Sheets OAuth flow...")
            if not CLIENT_ID or not CLIENT_SECRET:
                raise ValueError("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured in .env file.")
                
            client_config = {
                "installed": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost"]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save credentials for future execution
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
            
    service = build("sheets", "v4", credentials=creds)
    return service

def ensure_worksheet_exists(service, title="Shared Memory"):
    """
    Checks if a worksheet with the specified title exists, and creates it if missing.
    """
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = spreadsheet.get("sheets", [])
    sheet_titles = [s.get("properties", {}).get("title") for s in sheets]
    
    if title not in sheet_titles:
        print(f"Worksheet '{title}' not found. Creating worksheet...")
        batch_update_request_body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": title
                        }
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=batch_update_request_body
        ).execute()
        return True
    return False

def format_sheet_text_black(service, title="Shared Memory"):
    """
    Sets the text color (foregroundColor) of all cells in the worksheet to black.
    """
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get("sheets", [])
        sheet_id = None
        for s in sheets:
            if s.get("properties", {}).get("title") == title:
                sheet_id = s.get("properties", {}).get("sheetId")
                break
        
        if sheet_id is not None:
            batch_update_request_body = {
                "requests": [
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "startColumnIndex": 0
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "textFormat": {
                                        "foregroundColor": {
                                            "red": 0.0,
                                            "green": 0.0,
                                            "blue": 0.0
                                        }
                                    }
                                }
                            },
                            "fields": "userEnteredFormat.textFormat.foregroundColor"
                        }
                    }
                ]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=batch_update_request_body
            ).execute()
    except Exception as e:
        print(f"Warning: Failed to format sheet text color to black: {e}")

def write_task_to_google_sheets_func(
    task_type: str,
    description: str,
    course: str = "General",
    priority: str = "High",
    assigned_agent: str = "TA",
    status: str = "Pending",
    notes: str = ""
) -> str:
    """
    Appends a new task row to the Google Sheet task queue, automatically
    generating an incremented task ID (e.g. T001, T002, etc.) and timestamp.
    """
    try:
        service = get_google_sheets_service()
        ensure_worksheet_exists(service, "Shared Memory")
        
        # Read existing rows to compute next Task ID
        range_name = "Shared Memory!A:I"
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        rows = result.get("values", [])
        
        # Determine headers and next ID
        headers = ["Task_ID", "Task_Type", "Description", "Course", "Priority", "Assigned_Agent", "Status", "Created_At", "Notes"]
        new_task_id = "T001"
        
        if not rows:
            # Sheet is empty, write headers first
            print("Initializing headers in Google Sheet...")
            body = {"values": [headers]}
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range="Shared Memory!A1",
                valueInputOption="RAW",
                body=body
            ).execute()
            rows = [headers]
        
        # Calculate next Task ID by scanning Task_ID column (index 0)
        max_num = 0
        if len(rows) > 1:
            for row in rows[1:]:
                if row and len(row) > 0:
                    task_id_val = row[0]
                    match = re.search(r"T(\d+)", str(task_id_val))
                    if match:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num
            new_task_id = f"T{max_num + 1:03d}"
            
        # Timestamp
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # New Row
        new_row = [
            new_task_id,
            task_type,
            description,
            course,
            priority,
            assigned_agent,
            status,
            created_at,
            notes
        ]
        
        # Append Row
        body = {"values": [new_row]}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Shared Memory!A:I",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        # Ensure text is formatted as black
        format_sheet_text_black(service, "Shared Memory")
        
        return f"SUCCESS: Task {new_task_id} successfully created and written to Google Sheets."
        
    except Exception as e:
        error_msg = f"ERROR: Failed to write task to Google Sheets: {e}"
        print(error_msg)
        raise e

if __name__ == "__main__":
    print("Testing Google Sheets Writer directly...")
    try:
        msg = write_task_to_google_sheets_func(
            task_type="Test",
            description="Direct worksheet append test",
            course="Test Subject",
            priority="Low",
            notes="Google Sheets API verification"
        )
        print(msg)
    except Exception as ex:
        print("Test failed:", ex)
