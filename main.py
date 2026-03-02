from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="TicketFlow",
    description="Multi-Agent Customer Support System",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "project": "TicketFlow",
        "status": "running",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "message": "TicketFlow is online"
    }

@app.get("/hello/{name}")
def hello(name: str):
    return {
        "message": f"Hello {name}, welcome to TicketFlow!",
        "timestamp": datetime.now().isoformat()
    }