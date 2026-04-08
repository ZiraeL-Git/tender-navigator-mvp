from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.schemas import HealthResponse
from backend.app.api.routes import router
from backend.app.core.settings import get_settings
from backend.app.db.session import create_engine_from_settings, create_session_factory, initialize_database
from backend.app.repositories.storage import StorageRepository
from backend.app.services.analysis_pipeline import AnalysisPipelineService
from backend.app.services.file_storage import FileStorageService
from backend.app.services.mvp_adapter import MvpAdapter
from backend.app.services.tender_inputs import TenderInputService


settings = get_settings()
engine = create_engine_from_settings(settings)
session_factory = create_session_factory(engine)
storage = StorageRepository(session_factory)
mvp_adapter = MvpAdapter(settings)
file_storage = FileStorageService(settings)
tender_input_service = TenderInputService(storage, file_storage)
analysis_pipeline = AnalysisPipelineService(storage)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database(engine, settings)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.storage = storage
    app.state.mvp_adapter = mvp_adapter
    app.state.file_storage = file_storage
    app.state.tender_input_service = tender_input_service
    app.state.analysis_pipeline = analysis_pipeline
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")


app.include_router(router, prefix=settings.api_v1_prefix)
