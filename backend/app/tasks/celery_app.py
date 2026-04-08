from __future__ import annotations

from celery import Celery

from backend.app.core.settings import get_settings


settings = get_settings()

broker_url = settings.celery_broker_url
result_backend = settings.celery_result_backend

if settings.celery_task_always_eager:
    broker_url = "memory://"
    result_backend = "cache+memory://"

celery_app = Celery(
    "tender_navigator",
    broker=broker_url,
    backend=result_backend,
)
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_store_eager_result=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
