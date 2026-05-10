import requests
import json

def verify_api():
    try:
        response = requests.get("http://127.0.0.1:8000/api/dashboard_data")
        data = response.json()
        
        required_keys = ["metrics", "telemetry", "outcome", "shapImportance", "sarimaForecast", "clusters", "actionLog"]
        missing = [k for k in required_keys if k not in data]
        
        if missing:
            print(f"FAILED: Missing keys {missing}")
            print(f"Response: {response.text}")
        else:

            print("SUCCESS: All advanced telemetry keys present.")
            print(f"ReAct Path: {data['telemetry'].get('path')}")
            print(f"Intelligent Score: {data['telemetry'].get('score')}")
            print(f"Drift Outcome: {data['outcome']}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    verify_api()
