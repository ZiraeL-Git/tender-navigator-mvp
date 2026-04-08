from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default

    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str
    api_v1_prefix: str
    cors_allowed_origins: list[str]
    root_dir: Path
    backend_dir: Path
    data_dir: Path
    uploads_dir: Path
    database_url: str
    celery_broker_url: str
    celery_result_backend: str
    celery_task_always_eager: bool
    ollama_url: str
    ollama_model: str
    mvp_dir: Path


def get_settings() -> Settings:
    root_dir = Path(__file__).resolve().parents[3]
    backend_dir = root_dir / "backend"
    data_dir = backend_dir / "data"
    uploads_dir = data_dir / "tender_inputs"
    default_database_url = (
        f"sqlite:///{(data_dir / 'tender_navigator_backend.db').as_posix()}"
    )
    database_url = os.getenv("TENDER_NAVIGATOR_DATABASE_URL", default_database_url)
    celery_broker_url = os.getenv("TENDER_NAVIGATOR_CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_result_backend = os.getenv("TENDER_NAVIGATOR_CELERY_RESULT_BACKEND", celery_broker_url)

    return Settings(
        app_name="Tender Navigator API",
        api_v1_prefix="/api/v1",
        cors_allowed_origins=_env_csv(
            "TENDER_NAVIGATOR_CORS_ALLOWED_ORIGINS",
            [
                "http://127.0.0.1:3000",
                "http://localhost:3000",
            ],
        ),
        root_dir=root_dir,
        backend_dir=backend_dir,
        data_dir=data_dir,
        uploads_dir=uploads_dir,
        database_url=database_url,
        celery_broker_url=celery_broker_url,
        celery_result_backend=celery_result_backend,
        celery_task_always_eager=_env_bool("TENDER_NAVIGATOR_CELERY_EAGER", True),
        ollama_url=os.getenv("TENDER_NAVIGATOR_OLLAMA_URL", "http://localhost:11434/api/chat"),
        ollama_model=os.getenv("TENDER_NAVIGATOR_OLLAMA_MODEL", "gemma3:4b"),
        mvp_dir=root_dir / "tender_navigator_mvp",
    )
