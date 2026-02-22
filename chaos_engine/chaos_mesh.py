import requests
import time
import datetime
import random

TARGET_API_URL = "http://localhost:8000/api/checkout"
AEGIS_WEBHOOK_URL = "http://localhost:8001/webhook/alert"

def simulate_chaos():
    print("🔫 [Chaos Engine] Started: Assaulting Target E-Commerce API...")
    
    for i in range(1, 15):
        print(f"   [Request {i}] -> GET {TARGET_API_URL}")
        try:
            start_time = time.time()
            response = requests.get(TARGET_API_URL, timeout=5)
            latency = time.time() - start_time
            
            if response.status_code == 200:
                print(f"      ✅ Success ({latency:.2f}s) - {response.json()}")
            elif response.status_code == 500:
                print(f"      🚨 INCIDENT DETECTED! HTTP 500: {response.text}")
                trigger_incident_response(response.status_code, response.text)
                
                # We stop after causing one major incident and resolving it
                print("\n🔫 [Chaos Engine] Mission Accomplished. Ceasing fire.")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"      ❌ Connection Failed: {e}")
        
        # Add slight delay between requests
        time.sleep(random.uniform(0.5, 1.5))

def trigger_incident_response(status_code, error_text):
    print("\n📡 [Monitoring Agent] Alerting Aegis-Air Zero-Trust Engine...")
    
    payload = {
        "service_name": "E-Commerce-Checkout-API",
        "incident_time": datetime.datetime.now().isoformat(),
        "status_code": status_code,
        "error_details": error_text
    }
    
    try:
        # Fire webhook to Aegis-Engine
        webhook_response = requests.post(AEGIS_WEBHOOK_URL, json=payload)
        
        if webhook_response.status_code == 200:
            result = webhook_response.json()
            display_rca(result)
        else:
            print(f"❌ Failed to reach Aegis-Engine. Code: {webhook_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Aegis-Engine is unreachable. Is the webhook server (port 8001) running?")

def display_rca(result):
    print("\n" + "="*60)
    print("🛡️  AEGIS-AIR AUTONOMOUS RCA REPORT (ZERO-TRUST LOCAL AI) 🛡️")
    print("="*60)
    print(result.get("rca_report", "No report content."))
    print("="*60 + "\n")

if __name__ == "__main__":
    simulate_chaos()
