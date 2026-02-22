# 🛡️ Aegis-Air: Zero-Trust Autonomous SRE Platform

**Aegis-Air** is an enterprise-grade, privacy-first (Zero-Trust) Site Reliability Engineering (SRE) platform. It intercepts application outages and alerts, analyzes raw telemetry data using a fully air-gapped local Large Language Model (LLM), and auto-generates structured Root Cause Analysis (RCA) reports—without ever exposing sensitive enterprise logs to external public APIs like OpenAI.

Designed by **Doeon Kim (Full-Cycle AI Engineer)**, this project demonstrates extreme proficiency in **Cloud Infrastructure (Terraform/AWS)**, **Observability (Datadog/Prometheus)**, **Edge AI (Local LLM via Ollama)**, and **Real-Time Web Dashboards (FastAPI + Server-Sent Events)**.

---

## 🎯 Architecture Overview

1. **The Target (E-Commerce API)**: A dummy FastAPI backend running on port 8000.
2. **The Zero-Trust AI Engine (Aegis Engine)**: A localized FastAPI server on port 8001 that securely formats incident logs and queries an offline `phi3` LLM via Ollama. 
3. **The Ops Console (Glassmorphic Web Dashboard)**: A stunning Cyberpunk/SRE-themed web UI served directly from the Aegis Engine. It allows users to manually trigger *Chaos Engineering* simulations and watch the local AI generate the RCA report in real-time via Server-Sent Events (SSE).
4. **The Enterprise Proof (Terraform IaC)**: Found in `/infrastructure/aws`, these scripts prove the capability to deploy this exact architecture into an AWS production environment.

---

## 🚀 Quick Start (Local Sandbox)

The entire sandbox runs natively on macOS to maximize system performance for local Edge AI inference. No Docker required.

### 1. Prerequisites
- Python 3.11+
- `ollama` installed via Homebrew (`brew install ollama`)
- Phi-3 model pulled (`ollama pull phi3`)

### 2. Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the Sandbox
Open two separate terminal tabs. Ensure your virtual environment is activated in each.

**Terminal 1 (The Victim Target API):**
```bash
uvicorn app.main:app --port 8000
```

**Terminal 2 (The Zero-Trust AI Engine + Ops Console):**
```bash
uvicorn aegis_engine.main:app --port 8001
```

### 4. Experience the Ops Console:
1. Open your browser and navigate to: **http://localhost:8001**
2. You will see the Aegis-Air Ops Console.
3. Click the red **"UNLEASH CHAOS"** button.
4. Watch the terminal feed on the right side of the screen as the system bombards the target API, detects a Database outage, and streams the Local LLM's Root Cause Analysis back to the UI in real-time.

---

## ☁️ Enterprise Cloud Deployment (AWS)

To deploy the production-ready cluster using Terraform:
```bash
cd infrastructure/aws
terraform init
terraform plan
terraform apply
```
