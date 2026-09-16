"""
FastAPI application entrypoint.
Run locally with: uvicorn app.main:app --reload
"""
from fastapi import FastAPI

from app.api.routes.posts import router as posts_router
from app.api.routes.variants import router as variants_router
from app.api.routes.review import router as review_router
from app.api.routes.oauth import router as oauth_router
from app.api.routes.schedule import router as schedule_router

app = FastAPI(
    title="Social Media Studio",
    description="Turn one blog post into a scheduled, multi-platform social campaign.",
    version="0.1.0",
)

app.include_router(posts_router)
app.include_router(variants_router)
app.include_router(review_router)
app.include_router(oauth_router)
app.include_router(schedule_router)


@app.get("/health")
def health_check():
    """
    Simple liveness check — confirms the API process is running.
    Does NOT check Postgres/Redis yet; we'll extend this on Day 2
    once the database connection exists.
    """
    return {"status": "ok", "service": "social-media-studio"}