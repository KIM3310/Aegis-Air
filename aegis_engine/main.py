from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
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
LLM_FALLBACK_RESPONSE = (
    "[RCA Analysis]: Local Phi-3 model is unavailable, but checkout failures indicate a probable downstream "
    "database dependency outage.\n"
    "[Action Items]: 1) Verify `ollama serve` and model availability (`ollama list`). "
    "2) Inspect checkout database connectivity and recent deployment changes."
)

class AlertPayload(BaseModel):
    service_name: str
    incident_time: str
    status_code: int
    error_details: str

def sse_event(payload):
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

def sse_log(message):
    return sse_event({"type": "log", "content": f"{message}\n"})

def sse_token(message):
    return sse_event({"type": "token", "content": message})

def sse_done():
    return sse_event({"type": "done"})

async def generate_chaos_and_stream_response():
    # Step 1: Simulate Chaos
    yield sse_log("[Chaos Engine] Initiating assault on E-Commerce API...")
    
    incident_detected = False
    error_text = ""
    status_code = 500
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(1, 15):
            yield sse_log(f"[Request {i}] -> GET {TARGET_API_URL}")
            try:
                # We do a tiny sleep so the UI can see the logs pumping
                await asyncio.sleep(0.5 + random.random())
                response = await client.get(TARGET_API_URL)
                
                if response.status_code == 200:
                    yield sse_log("      ✅ Success 200 OK")
                elif response.status_code == 500:
                    yield sse_log("      🚨 INCIDENT DETECTED! HTTP 500")
                    incident_detected = True
                    status_code = response.status_code
                    error_text = response.text
                    break
            except Exception as exc:
                yield sse_log(f"      ❌ Connection Failed: {exc}")
        
        if not incident_detected:
            yield sse_log("[Chaos Engine] Failed to trigger an incident. Try again.")
            yield sse_done()
            return
            
    # Step 2: Query Zero-Trust LLM with streaming output
    yield sse_log(f"[Aegis-Air] 🚨 CRITICAL ALERT RECEIVED (Code: {status_code})")
    yield sse_log("[Aegis-Air] 🧠 Querying Local Zero-Trust LLM (Phi-3) for RCA...")
    
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
    
    llm_unavailable = False
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", OLLAMA_URL, json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": True
            }) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if not chunk:
                        continue
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("response", "")
                    if token:
                        yield sse_token(token)
    except httpx.HTTPError as exc:
        llm_unavailable = True
        yield sse_log(f"[Aegis-Air] ❌ Local LLM request failed: {exc}")
    except Exception as exc:
        llm_unavailable = True
        yield sse_log(f"[Aegis-Air] ❌ Unexpected LLM stream error: {exc}")

    if llm_unavailable:
        yield sse_token(LLM_FALLBACK_RESPONSE)

    yield sse_log("[Aegis-Air] ✅ RCA Generation Complete.")
    yield sse_done()

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
