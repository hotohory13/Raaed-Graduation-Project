import os
import sys
from dotenv import load_dotenv

# Ensure we read environment variables
load_dotenv()

# Add current directory to system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crew import run_admin_crew

def main():
    print("==================================================")
    print("Testing Admin Crew workflow directly...")
    print(f"GROQ_API_KEY is configured: {bool(os.getenv('GROQ_API_KEY'))}")
    print(f"GROQ_MODEL_NAME: {os.getenv('GROQ_MODEL_NAME')}")
    print("==================================================")
    
    test_requests = [
        "Create a quiz about Machine Learning Chapter 3 with 20 MCQ questions",
        "Generate a study guide for Deep Learning Chapter 5"
    ]
    
    import time
    for i, req in enumerate(test_requests):
        if i > 0:
            print("Sleeping for 60 seconds to clear Groq free-tier sliding window rate limits...")
            time.sleep(60)
        print(f"\nProcessing request: '{req}'")
        try:
            result = run_admin_crew(req)
            print("Response structure returned by runner:")
            print(result)
            print("-" * 50)
        except Exception as e:
            print(f"ERROR while processing request: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
