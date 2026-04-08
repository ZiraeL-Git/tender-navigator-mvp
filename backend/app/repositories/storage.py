from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import joinedload, selectinload, sessionmaker

from backend.app.db.models import (
    AnalysisEvent,
    AnalysisResult,
    CompanyProfile,
    TenderAnalysis,
    TenderDocument,
    TenderInput,
)


def isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class StorageRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    def create_company_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.session_factory() as session:
            company_profile = CompanyProfile(
                company_name=payload["company_name"],
                inn=payload["inn"],
                region=payload["region"],
                categories=payload.get("categories", []),
                has_license=payload.get("has_license", False),
                has_experience=payload.get("has_experience", False),
                can_prepare_fast=payload.get("can_prepare_fast", True),
                notes=payload.get("notes", ""),
            )
            session.add(company_profile)
            session.commit()
            session.refresh(company_profile)
            return self._company_profile_to_dict(company_profile)

    def get_company_profile(self, profile_id: int) -> dict[str, Any] | None:
        with self.session_factory() as session:
            company_profile = session.get(CompanyProfile, profile_id)
            if company_profile is None:
                return None
            return self._company_profile_to_dict(company_profile)

    def list_company_profiles(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement: Select[tuple[CompanyProfile]] = (
                select(CompanyProfile)
                .order_by(desc(CompanyProfile.id))
                .limit(limit)
            )
            profiles = session.scalars(statement).all()
            return [self._company_profile_to_dict(profile) for profile in profiles]

    def update_company_profile(self, profile_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        with self.session_factory() as session:
            company_profile = session.get(CompanyProfile, profile_id)
            if company_profile is None:
                return None

            company_profile.company_name = payload["company_name"]
            company_profile.inn = payload["inn"]
            company_profile.region = payload["region"]
            company_profile.categories = payload.get("categories", [])
            company_profile.has_license = payload.get("has_license", False)
            company_profile.has_experience = payload.get("has_experience", False)
            company_profile.can_prepare_fast = payload.get("can_prepare_fast", True)
            company_profile.notes = payload.get("notes", "")
            session.commit()
            session.refresh(company_profile)
            return self._company_profile_to_dict(company_profile)

    def create_tender_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.session_factory() as session:
            tender_input = TenderInput(
                company_profile_id=payload["company_profile_id"],
                source_type=payload["source_type"],
                source_value=payload["source_value"],
                source_url=payload.get("source_url"),
                notice_number=payload.get("notice_number"),
                title=payload.get("title", ""),
                customer_name=payload.get("customer_name"),
                deadline=payload.get("deadline"),
                max_price=payload.get("max_price"),
                status=payload.get("status", "imported"),
                normalized_payload=payload.get("normalized_payload", {}),
                documents=payload.get("documents", []),
                last_error=payload.get("last_error"),
            )
            session.add(tender_input)
            session.commit()
            session.refresh(tender_input)
            return self._tender_input_to_dict(tender_input)

    def get_tender_input(self, tender_input_id: int) -> dict[str, Any] | None:
        with self.session_factory() as session:
            statement = (
                select(TenderInput)
                .options(selectinload(TenderInput.analyses))
                .where(TenderInput.id == tender_input_id)
            )
            tender_input = session.scalar(statement)
            if tender_input is None:
                return None
            return self._tender_input_to_dict(tender_input)

    def list_tender_inputs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement: Select[tuple[TenderInput]] = (
                select(TenderInput)
                .options(selectinload(TenderInput.analyses))
                .order_by(desc(TenderInput.id))
                .limit(limit)
            )
            tender_inputs = session.scalars(statement).all()
            return [self._tender_input_to_dict(tender_input) for tender_input in tender_inputs]

    def create_analysis_job(
        self,
        *,
        company_profile_id: int,
        tender_input_id: int,
        package_name: str,
        ai_summary_requested: bool = False,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            analysis = TenderAnalysis(
                company_profile_id=company_profile_id,
                tender_input_id=tender_input_id,
                package_name=package_name,
                status="queued",
                ai_summary_requested=ai_summary_requested,
            )
            session.add(analysis)
            session.flush()
            session.add(
                AnalysisEvent(
                    analysis_id=analysis.id,
                    event_type="analysis_queued",
                    payload={
                        "status": analysis.status,
                        "tender_input_id": tender_input_id,
                        "ai_summary_requested": ai_summary_requested,
                    },
                )
            )
            session.commit()
            analysis_id = analysis.id

        analysis_record = self.get_analysis(int(analysis_id))
        if analysis_record is None:
            raise RuntimeError("Analysis job was not created")
        return analysis_record

    def set_analysis_task(self, analysis_id: int, background_task_id: str | None) -> dict[str, Any]:
        with self.session_factory() as session:
            analysis = session.get(TenderAnalysis, analysis_id)
            if analysis is None:
                raise RuntimeError("Analysis not found")
            analysis.background_task_id = background_task_id
            session.commit()
        analysis_record = self.get_analysis(analysis_id)
        if analysis_record is None:
            raise RuntimeError("Analysis not found after task update")
        return analysis_record

    def mark_analysis_processing(self, analysis_id: int) -> None:
        with self.session_factory() as session:
            analysis = session.get(TenderAnalysis, analysis_id)
            if analysis is None:
                raise RuntimeError("Analysis not found")
            analysis.status = "processing"
            analysis.started_at = datetime.now(UTC)
            session.add(
                AnalysisEvent(
                    analysis_id=analysis_id,
                    event_type="analysis_processing_started",
                    payload={"status": analysis.status},
                )
            )
            session.commit()

    def complete_analysis(
        self,
        analysis_id: int,
        *,
        analysis_payload: dict[str, Any],
        ai_summary: str | None = None,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            analysis = session.get(TenderAnalysis, analysis_id, options=[selectinload(TenderAnalysis.documents)])
            if analysis is None:
                raise RuntimeError("Analysis not found")

            analysis.status = analysis_payload["status"]
            analysis.completed_at = datetime.now(UTC)
            analysis.failure_reason = None
            analysis.ai_summary = ai_summary or analysis_payload.get("ai_summary")

            for existing_document in list(analysis.documents):
                session.delete(existing_document)

            for document_payload in analysis_payload.get("documents", []):
                session.add(
                    TenderDocument(
                        analysis_id=analysis.id,
                        filename=document_payload["filename"],
                        doc_type=document_payload["doc_type"],
                        extracted_text=document_payload.get("extracted_text"),
                        text_length=document_payload.get("text_length", 0),
                    )
                )

            if analysis.result is None:
                analysis.result = AnalysisResult(analysis_id=analysis.id)

            analysis.result.raw_text = analysis_payload.get("raw_text")
            analysis.result.extracted = analysis_payload["extracted"]
            analysis.result.decision_code = analysis_payload.get("decision_code")
            analysis.result.decision_label = analysis_payload.get("decision_label")
            analysis.result.decision_reasons = analysis_payload.get("decision_reasons", [])
            analysis.result.checklist = analysis_payload.get("checklist", [])
            analysis.result.warnings = analysis_payload.get("warnings", [])
            analysis.result.errors = analysis_payload.get("errors", [])

            session.add(
                AnalysisEvent(
                    analysis_id=analysis.id,
                    event_type="analysis_completed",
                    payload={
                        "status": analysis.status,
                        "decision_code": analysis_payload.get("decision_code"),
                        "decision_label": analysis_payload.get("decision_label"),
                    },
                )
            )
            session.commit()

        analysis_record = self.get_analysis(analysis_id)
        if analysis_record is None:
            raise RuntimeError("Analysis not found after completion")
        return analysis_record

    def fail_analysis(self, analysis_id: int, reason: str) -> dict[str, Any]:
        with self.session_factory() as session:
            analysis = session.get(TenderAnalysis, analysis_id)
            if analysis is None:
                raise RuntimeError("Analysis not found")
            analysis.status = "failed"
            analysis.failure_reason = reason
            analysis.completed_at = datetime.now(UTC)
            session.add(
                AnalysisEvent(
                    analysis_id=analysis_id,
                    event_type="analysis_failed",
                    payload={"reason": reason},
                )
            )
            session.commit()

        analysis_record = self.get_analysis(analysis_id)
        if analysis_record is None:
            raise RuntimeError("Analysis not found after failure")
        return analysis_record

    def apply_manual_correction(self, analysis_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        with self.session_factory() as session:
            analysis = session.get(
                TenderAnalysis,
                analysis_id,
                options=[joinedload(TenderAnalysis.result)],
            )
            if analysis is None:
                return None

            if analysis.result is None:
                analysis.result = AnalysisResult(analysis_id=analysis.id, extracted={})

            if payload.get("decision_code") is not None:
                analysis.result.decision_code = payload["decision_code"]
            if payload.get("decision_label") is not None:
                analysis.result.decision_label = payload["decision_label"]
            if payload.get("checklist") is not None:
                analysis.result.checklist = payload["checklist"]
            if payload.get("extracted") is not None:
                analysis.result.extracted = payload["extracted"]
            if payload.get("ai_summary") is not None:
                analysis.ai_summary = payload["ai_summary"]

            analysis.status = "manual_reviewed"
            analysis.failure_reason = None
            analysis.completed_at = datetime.now(UTC)

            session.add(
                AnalysisEvent(
                    analysis_id=analysis.id,
                    event_type="manual_correction_applied",
                    payload={
                        "comment": payload.get("comment", ""),
                        "decision_code": analysis.result.decision_code,
                        "decision_label": analysis.result.decision_label,
                    },
                )
            )
            session.commit()

        return self.get_analysis(analysis_id)

    def add_event(self, analysis_id: int, event_type: str, payload: dict[str, Any]) -> None:
        with self.session_factory() as session:
            session.add(
                AnalysisEvent(
                    analysis_id=analysis_id,
                    event_type=event_type,
                    payload=payload,
                )
            )
            session.commit()

    def get_analysis(self, analysis_id: int) -> dict[str, Any] | None:
        with self.session_factory() as session:
            statement = (
                select(TenderAnalysis)
                .options(
                    selectinload(TenderAnalysis.documents),
                    joinedload(TenderAnalysis.result),
                    selectinload(TenderAnalysis.events),
                )
                .where(TenderAnalysis.id == analysis_id)
            )
            analysis = session.scalar(statement)
            if analysis is None:
                return None
            return self._analysis_to_dict(analysis)

    def list_analyses(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement: Select[tuple[TenderAnalysis]] = (
                select(TenderAnalysis)
                .options(joinedload(TenderAnalysis.result))
                .order_by(desc(TenderAnalysis.id))
                .limit(limit)
            )
            analyses = session.scalars(statement).all()
            return [self._analysis_to_dict(analysis, include_details=False) for analysis in analyses]

    def get_analysis_processing_context(self, analysis_id: int) -> dict[str, Any] | None:
        with self.session_factory() as session:
            statement = (
                select(TenderAnalysis)
                .options(
                    joinedload(TenderAnalysis.company_profile),
                    joinedload(TenderAnalysis.tender_input),
                )
                .where(TenderAnalysis.id == analysis_id)
            )
            analysis = session.scalar(statement)
            if analysis is None or analysis.company_profile is None or analysis.tender_input is None:
                return None

            return {
                "analysis_id": analysis.id,
                "company_profile": self._company_profile_to_dict(analysis.company_profile),
                "tender_input": self._tender_input_to_dict(analysis.tender_input),
                "ai_summary_requested": analysis.ai_summary_requested,
            }

    def count_analysis_events(self, analysis_id: int) -> int:
        with self.session_factory() as session:
            analysis = session.get(TenderAnalysis, analysis_id, options=[selectinload(TenderAnalysis.events)])
            if analysis is None:
                return 0
            return len(analysis.events)

    def _company_profile_to_dict(self, company_profile: CompanyProfile) -> dict[str, Any]:
        return {
            "id": company_profile.id,
            "created_at": isoformat_utc(company_profile.created_at),
            "company_name": company_profile.company_name,
            "inn": company_profile.inn,
            "region": company_profile.region,
            "categories": company_profile.categories,
            "has_license": company_profile.has_license,
            "has_experience": company_profile.has_experience,
            "can_prepare_fast": company_profile.can_prepare_fast,
            "notes": company_profile.notes,
        }

    def _tender_input_to_dict(self, tender_input: TenderInput) -> dict[str, Any]:
        latest_analysis_id = max((analysis.id for analysis in tender_input.analyses), default=None)
        return {
            "id": tender_input.id,
            "created_at": isoformat_utc(tender_input.created_at),
            "updated_at": isoformat_utc(tender_input.updated_at),
            "company_profile_id": tender_input.company_profile_id,
            "source_type": tender_input.source_type,
            "source_value": tender_input.source_value,
            "source_url": tender_input.source_url,
            "notice_number": tender_input.notice_number,
            "title": tender_input.title,
            "customer_name": tender_input.customer_name,
            "deadline": tender_input.deadline,
            "max_price": tender_input.max_price,
            "status": tender_input.status,
            "normalized_payload": tender_input.normalized_payload,
            "documents": tender_input.documents,
            "last_error": tender_input.last_error,
            "latest_analysis_id": latest_analysis_id,
        }

    def _analysis_to_dict(
        self,
        analysis: TenderAnalysis,
        *,
        include_details: bool = True,
    ) -> dict[str, Any]:
        result = analysis.result
        extracted = result.extracted if result is not None else {}

        return {
            "id": analysis.id,
            "created_at": isoformat_utc(analysis.created_at),
            "company_profile_id": analysis.company_profile_id,
            "tender_input_id": analysis.tender_input_id,
            "package_name": analysis.package_name,
            "status": analysis.status,
            "background_task_id": analysis.background_task_id,
            "failure_reason": analysis.failure_reason,
            "started_at": isoformat_utc(analysis.started_at),
            "completed_at": isoformat_utc(analysis.completed_at),
            "ai_summary_requested": analysis.ai_summary_requested,
            "raw_text": result.raw_text if result is not None else None,
            "extracted": extracted,
            "decision_code": result.decision_code if result is not None else None,
            "decision_label": result.decision_label if result is not None else None,
            "decision_reasons": result.decision_reasons if result is not None else [],
            "checklist": result.checklist if result is not None else [],
            "ai_summary": analysis.ai_summary,
            "documents": [
                {
                    "filename": document.filename,
                    "doc_type": document.doc_type,
                    "extracted_text": document.extracted_text,
                    "text_length": document.text_length,
                }
                for document in analysis.documents
            ]
            if include_details
            else [],
            "warnings": result.warnings if result is not None else [],
            "errors": result.errors if result is not None else [],
            "events": [
                {
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "created_at": isoformat_utc(event.created_at),
                }
                for event in analysis.events
            ]
            if include_details
            else [],
        }
