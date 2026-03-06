from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import random
import time
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Dummy E-Commerce API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Instrument the app to expose /metrics for Prometheus
Instrumentator().instrument(app).expose(app)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "E-Commerce API"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "dummy-ecommerce-api",
        "links": {
            "meta": "/meta",
            "metrics": "/metrics",
        },
    }


@app.get("/meta")
def meta():
    return {
        "service": "dummy-ecommerce-api",
        "version": "1.0",
        "chaos_profile": {
            "checkout_error_rate": 0.30,
            "checkout_latency_rate": 0.10,
        },
        "routes": ["/", "/health", "/meta", "/api/products", "/api/checkout", "/metrics"],
    }

@app.get("/api/products")
def get_products():
    # Simulate some processing time
    time.sleep(random.uniform(0.01, 0.1))
    return [{"id": 1, "name": "Laptop"}, {"id": 2, "name": "Smartphone"}]

@app.get("/api/checkout")
def checkout():
    # Simulate random latency and potential 500 errors to create interesting metrics and trigger chaos testing
    chaos = random.random()
    if chaos < 0.30:  # 30% chance of severe error
        raise HTTPException(status_code=500, detail="Internal Server Error: Database Connection Lost")
    elif chaos < 0.40: # 10% chance of simulated latency
        time.sleep(random.uniform(1.0, 3.0))
        
    return {"status": "success", "order_id": random.randint(1000, 9999)}
