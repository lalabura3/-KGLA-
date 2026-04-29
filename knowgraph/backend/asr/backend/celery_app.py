"""Celery application configuration.

Configures the Celery worker with Redis broker and result backend.
"""
from celery import Celery

from .config import get_settings

settings = get_settings()

celery_app = Celery(
    "studyai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["backend.tasks.asr_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_time_limit - 60,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    result_expires=86400,  # 24h TTL for results
    task_acks_late=True,  # Re-deliver on worker crash
    task_reject_on_worker_lost=True,
)

# Register ASR task
celery_app.task(name="process_video_asr", bind=True, max_retries=2)(
    lambda self, video_id, video_path, language="zh": (
        __import__("backend.tasks.asr_tasks", fromlist=["process_video_asr_task"])
        .process_video_asr_task(video_id, video_path, language)
    )
)
