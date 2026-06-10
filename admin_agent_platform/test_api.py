import requests
import json
import time

def main():
    url = "http://127.0.0.1:8000/task/create"
    headers = {"Content-Type": "application/json"}
    
    test_cases = [
        {"request": "Create a quiz about Machine Learning Chapter 3 with 20 MCQ questions"},
        {"request": "Generate an assignment about Deep Learning Chapter 5"}
    ]
    
    print("==================================================")
    print("Testing FastAPI Task Creation API...")
    print("Make sure your FastAPI server is running (uvicorn main:app --reload)")
    print("==================================================")
    
    for i, payload in enumerate(test_cases):
        if i > 0:
            print("\nSleeping for 60 seconds to avoid Groq rate limits...")
            time.sleep(60)
            
        print(f"\nSending request: {json.dumps(payload)}")
        try:
            start_time = time.time()
            response = requests.post(url, json=payload, headers=headers)
            duration = time.time() - start_time
            
            print(f"Response Status Code: {response.status_code} (took {duration:.2f}s)")
            print("Response Body:")
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print("API request failed:", e)

if __name__ == "__main__":
    main()
