"""
FastAPI application entrypoint.
Run locally with: uvicorn app.main:app --reload
"""
from fastapi import FastAPI

from app.api.routes.posts import router as posts_router

app = FastAPI(
    title="Social Media Studio",
    description="Turn one blog post into a scheduled, multi-platform social campaign.",
    version="0.1.0",
)

app.include_router(posts_router)


@app.get("/health")
def health_check():
    """
    Simple liveness check — confirms the API process is running.
    Does NOT check Postgres/Redis yet; we'll extend this on Day 2
    once the database connection exists.
    """
    return {"status": "ok", "service": "social-media-studio"}