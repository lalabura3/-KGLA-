"""
Celery application configuration — updated with all task modules.

Includes:
  - asr_tasks:   process_video_asr (ASR pipeline with DB persistence)
  - link_tasks:  process_link_import (link import with full pipeline)
  - (future) note_tasks, graph_tasks

Usage:
    celery -A backend.celery_app worker --loglevel=info --queues=asr,notes,graph
"""
from __future__ import annotations

from celery import Celery

from .config import settings

celery_app = Celery(
    "studyai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "backend.tasks.asr_tasks",    # ASR pipeline + segment persistence
        "backend.tasks.link_tasks",   # Link import processing
        # Future (T17/T18 integration):
        # "backend.tasks.note_tasks",
        # "backend.tasks.graph_tasks",
    ],
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
    result_expires=86400,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes=settings.celery_task_routes,
    task_default_queue="asr",
)
