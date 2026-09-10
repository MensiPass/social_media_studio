"""
FastAPI application entrypoint.
Run locally with: uvicorn app.main:app --reload
"""
from fastapi import FastAPI

app = FastAPI(
    title="Social Media Studio",
    description="Turn one blog post into a scheduled, multi-platform social campaign.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """
    Simple liveness check — confirms the API process is running.
    Does NOT check Postgres/Redis yet; we'll extend this on Day 2
    once the database connection exists.
    """
    return {"status": "ok", "service": "social-media-studio"}