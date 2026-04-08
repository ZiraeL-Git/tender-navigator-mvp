from __future__ import annotations

from backend.app.repositories.storage import StorageRepository
from backend.app.tasks.analysis_tasks import enqueue_analysis_processing


class AnalysisPipelineService:
    def __init__(self, storage: StorageRepository) -> None:
        self.storage = storage

    def queue_analysis_for_tender_input(
        self,
        *,
        tender_input_id: int,
        organization_id: int,
        include_ai_summary: bool = False,
    ) -> dict:
        tender_input = self.storage.get_tender_input(
            tender_input_id,
            organization_id=organization_id,
        )
        if tender_input is None:
            raise RuntimeError("Tender input not found")

        analysis = self.storage.create_analysis_job(
            organization_id=organization_id,
            company_profile_id=tender_input["company_profile_id"],
            tender_input_id=tender_input_id,
            package_name=tender_input["title"] or tender_input["source_value"],
            ai_summary_requested=include_ai_summary,
        )

        task_id = enqueue_analysis_processing(analysis["id"])
        return self.storage.set_analysis_task(analysis["id"], task_id)
