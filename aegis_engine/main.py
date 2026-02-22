from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
import time
import asyncio
import random
from datetime import datetime

app = FastAPI(title="Aegis-Air Engine", description="Zero-Trust LLM SRE RCA Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "phi3"
TARGET_API_URL = "http://localhost:8000/api/checkout"

class AlertPayload(BaseModel):
    service_name: str
    incident_time: str
    status_code: int
    error_details: str

async def generate_chaos_and_stream_response():
    # Step 1: Simulate Chaos
    yield "data: {\"type\": \"log\", \"content\": \"[Chaos Engine] Initiating assault on E-Commerce API...\\n\"}\n\n"
    
    incident_detected = False
    error_text = ""
    status_code = 500
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(1, 15):
            yield f"data: {{\"type\": \"log\", \"content\": \"[Request {i}] -> GET {TARGET_API_URL}\\n\"}}\n\n"
            try:
                # We do a tiny sleep so the UI can see the logs pumping
                await asyncio.sleep(0.5 + random.random())
                response = await client.get(TARGET_API_URL)
                
                if response.status_code == 200:
                    yield f"data: {{\"type\": \"log\", \"content\": \"      ✅ Success 200 OK\\n\"}}\n\n"
                elif response.status_code == 500:
                    yield f"data: {{\"type\": \"log\", \"content\": \"      🚨 INCIDENT DETECTED! HTTP 500\\n\"}}\n\n"
                    incident_detected = True
                    error_text = response.text
                    break
            except Exception as e:
                yield f"data: {{\"type\": \"log\", \"content\": \"      ❌ Connection Failed: {e}\\n\"}}\n\n"
        
        if not incident_detected:
            yield "data: {\"type\": \"log\", \"content\": \"[Chaos Engine] Failed to trigger an incident. Try again.\\n\"}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
            return
            
    # Step 2: Query Zero-Trust LLM with streaming output
    yield "data: {\"type\": \"log\", \"content\": \"\\n[Aegis-Air] 🚨 CRITICAL ALERT RECEIVED (Code: 500)\\n\"}\n\n"
    yield "data: {\"type\": \"log\", \"content\": \"[Aegis-Air] 🧠 Querying Local Zero-Trust LLM (Phi-3) for RCA...\\n\\n\"}\n\n"
    
    prompt = f"""You are Aegis-Air, an elite Site Reliability Engineering (SRE) AI operating in a zero-trust, air-gapped environment.
    Analyze the following incident and provide a Root Cause Analysis (RCA) and 2 immediate action items. Keep it extremely concise and professional.
    
    Incident Context:
    - Service: E-Commerce-Checkout-API
    - Time: {datetime.now().isoformat()}
    - Error Code: {status_code}
    - Raw Logs: {error_text}
    
    Format exactly as:
    [RCA Analysis]: <text>
    [Action Items]: <text>
    """
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": True
        }) as response:
            async for chunk in response.aiter_lines():
                if chunk:
                    try:
                        data = json.loads(chunk)
                        token = data.get("response", "")
                        # Send the token to the frontend
                        escaped_token = json.dumps(token)
                        yield f"data: {{\"type\": \"token\", \"content\": {escaped_token}}}\n\n"
                    except:
                        pass
                        
    yield "data: {\"type\": \"log\", \"content\": \"\\n\\n[Aegis-Air] ✅ RCA Generation Complete.\\n\"}\n\n"
    yield "data: {\"type\": \"done\"}\n\n"

@app.get("/api/chaos/trigger")
async def trigger_chaos_endpoint():
    # Returns Server-Sent Events (SSE)
    return StreamingResponse(generate_chaos_and_stream_response(), media_type="text/event-stream")

@app.post("/webhook/alert")
async def handle_alert(payload: AlertPayload):
    # Backward compatibility for the CLI tool
    return {"status": "success", "message": "Webhook received. Use /api/chaos/trigger for UI streaming."}

@app.get("/health")
def health_check():
    return {"status": "Aegis-Engine Online. Zero-Trust Mode Active."}
    
from fastapi.staticfiles import StaticFiles
import os

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
