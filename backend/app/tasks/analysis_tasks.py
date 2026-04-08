from __future__ import annotations

from backend.app.api.schemas import CompanyProfileCreate
from backend.app.core.settings import get_settings
from backend.app.db.session import create_engine_from_settings, create_session_factory, initialize_database
from backend.app.repositories.storage import StorageRepository
from backend.app.services.ai_summary import AiSummaryService
from backend.app.services.mvp_adapter import MvpAdapter
from backend.app.services.ocr import OcrService
from backend.app.tasks.celery_app import celery_app


settings = get_settings()
engine = create_engine_from_settings(settings)
initialize_database(engine, settings)
session_factory = create_session_factory(engine)
storage = StorageRepository(session_factory)
adapter = MvpAdapter(settings)
ai_summary_service = AiSummaryService(settings)
ocr_service = OcrService()


def enqueue_analysis_processing(analysis_id: int) -> str:
    task = process_analysis_task.delay(analysis_id)
    return str(task.id)


@celery_app.task(name="tender_navigator.process_analysis")
def process_analysis_task(analysis_id: int) -> dict:
    context = storage.get_analysis_processing_context(analysis_id)
    if context is None:
        raise RuntimeError("Analysis context not found")

    try:
        storage.mark_analysis_processing(analysis_id)

        company_profile = adapter.build_company_profile(
            CompanyProfileCreate(
                company_name=context["company_profile"]["company_name"],
                inn=context["company_profile"]["inn"],
                region=context["company_profile"]["region"],
                categories=context["company_profile"]["categories"],
                has_license=context["company_profile"]["has_license"],
                has_experience=context["company_profile"]["has_experience"],
                can_prepare_fast=context["company_profile"]["can_prepare_fast"],
                notes=context["company_profile"]["notes"],
            )
        )

        result = adapter.analyze_file_records(
            context["tender_input"]["documents"],
            company_profile,
        )
        analysis_payload = result.model_dump(mode="json")

        if len((result.raw_text or "").strip()) < 50:
            ocr_result = ocr_service.run_fallback(context["tender_input"]["documents"])
            if ocr_result is None:
                storage.add_event(
                    analysis_id,
                    "ocr_fallback_skipped",
                    {"reason": "ocr_provider_not_configured"},
                )

        ai_summary = None
        if context["ai_summary_requested"]:
            ai_summary = ai_summary_service.generate_summary(result.raw_text or "")
            storage.add_event(
                analysis_id,
                "ai_summary_completed" if ai_summary else "ai_summary_skipped",
                {"generated": bool(ai_summary)},
            )

        completed_analysis = storage.complete_analysis(
            analysis_id,
            analysis_payload=analysis_payload,
            ai_summary=ai_summary,
        )
        return {
            "analysis_id": completed_analysis["id"],
            "status": completed_analysis["status"],
        }
    except Exception as exc:
        storage.fail_analysis(analysis_id, str(exc))
        raise
