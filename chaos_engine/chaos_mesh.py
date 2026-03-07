import requests
import time
import datetime
import random

TARGET_API_URL = "http://localhost:8000/api/checkout"
AEGIS_WEBHOOK_URL = "http://localhost:8001/webhook/alert"
REQUEST_TIMEOUT_SEC = 5

def simulate_chaos():
    print("[Chaos Engine] Starting checkout probe loop.")
    
    for i in range(1, 15):
        print(f"   [Request {i}] -> GET {TARGET_API_URL}")
        try:
            start_time = time.time()
            response = requests.get(TARGET_API_URL, timeout=REQUEST_TIMEOUT_SEC)
            latency = time.time() - start_time
            
            if response.status_code == 200:
                print(f"      OK ({latency:.2f}s) - {response.json()}")
            elif response.status_code == 500:
                print(f"      INCIDENT DETECTED: HTTP 500 {response.text}")
                trigger_incident_response(response.status_code, response.text)
                
                print("\n[Chaos Engine] Stopping after the first confirmed incident.")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"      Connection failed: {e}")
        
        time.sleep(random.uniform(0.5, 1.5))

def trigger_incident_response(status_code, error_text):
    print("\n[Monitoring Agent] Sending incident payload to Aegis-Air.")
    
    payload = {
        "service_name": "E-Commerce-Checkout-API",
        "incident_time": datetime.datetime.now().isoformat(),
        "status_code": status_code,
        "error_details": error_text
    }
    
    try:
        webhook_response = requests.post(AEGIS_WEBHOOK_URL, json=payload, timeout=REQUEST_TIMEOUT_SEC)
        
        if webhook_response.status_code == 200:
            result = webhook_response.json()
            display_rca(result)
        else:
            print(f"Webhook request failed with status {webhook_response.status_code}.")
            
    except requests.exceptions.RequestException as exc:
        print(f"Aegis-Air webhook is unreachable: {exc}")

def display_rca(result):
    print("\n" + "="*60)
    print("AEGIS-AIR RCA REPORT")
    print("="*60)
    print(result.get("rca_report", "No report content."))
    print("="*60 + "\n")

if __name__ == "__main__":
    simulate_chaos()
