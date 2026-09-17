"""
Celery application instance. This is what turns "publish this at 3pm"
from a plan into something that actually happens without anyone watching
a terminal — Celery Beat periodically checks for due work, Celery workers
execute it in the background, independent of any HTTP request.

Run the worker with:    celery -A app.core.celery_app worker --loglevel=info
Run the scheduler with: celery -A app.core.celery_app beat --loglevel=info
(Both need to be running, in separate terminals, alongside the API server.)
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "social_media_studio",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.publish_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Celery Beat runs check_due_slots on a fixed interval, forever, as long as
# `celery beat` is running. Beat doesn't remember which slots are due — it
# asks the database fresh every tick. This is the "durable scheduling"
# pattern from the brief: the job store lives in the database, so a
# restarted worker (or a restarted Beat) just continues correctly.
celery_app.conf.beat_schedule = {
    "check-due-schedule-slots": {
        "task": "app.tasks.publish_tasks.check_due_slots",
        "schedule": 30.0,  # seconds
    },
    "recover-stuck-schedule-slots": {
        "task": "app.tasks.publish_tasks.recover_stuck_slots",
        "schedule": 60.0,  # seconds — checks less often than the main loop,
                            # since being stuck for a bit is expected/fine
    },
}