from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import joinedload, selectinload, sessionmaker

from backend.app.db.models import (
    AnalysisEvent,
    AnalysisResult,
    AuditLog,
    CompanyProfile,
    Organization,
    OrganizationInvitation,
    TenderAnalysis,
    TenderDocument,
    TenderInput,
    User,
)


def isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    normalized = normalized.strip("-")
    return normalized or "organization"


class StorageRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    def has_users(self) -> bool:
        with self.session_factory() as session:
            return session.scalar(select(User.id).limit(1)) is not None

    def create_organization_with_owner(
        self,
        *,
        organization_name: str,
        full_name: str,
        email: str,
        password_hash: str,
        password_salt: str,
    ) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        with self.session_factory() as session:
            existing_user = session.scalar(select(User).where(User.email == normalized_email))
            if existing_user is not None:
                raise ValueError("User with this email already exists")

            organization = Organization(
                name=organization_name.strip(),
                slug=self._build_unique_organization_slug(session, organization_name),
                is_active=True,
            )
            session.add(organization)
            session.flush()

            user = User(
                organization_id=organization.id,
                email=normalized_email,
                full_name=full_name.strip() or None,
                password_hash=password_hash,
                password_salt=password_salt,
                role="owner",
                is_active=True,
                is_owner=True,
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            statement = (
                select(User)
                .options(joinedload(User.organization))
                .where(User.id == user.id)
            )
            created_user = session.scalar(statement)
            if created_user is None:
                raise RuntimeError("Owner user was not created")
            return self._user_to_dict(created_user)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        normalized_email = email.strip().lower()
        with self.session_factory() as session:
            statement = (
                select(User)
                .options(joinedload(User.organization))
                .where(User.email == normalized_email)
            )
            user = session.scalar(statement)
            if user is None:
                return None
            return self._user_to_dict(user)

    def get_user_auth_context(self, user_id: int) -> dict[str, Any] | None:
        with self.session_factory() as session:
            statement = (
                select(User)
                .options(joinedload(User.organization))
                .where(User.id == user_id)
            )
            user = session.scalar(statement)
            if user is None:
                return None
            return self._user_to_dict(user)

    def list_organization_users(self, *, organization_id: int) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement: Select[tuple[User]] = (
                select(User)
                .options(joinedload(User.organization))
                .where(User.organization_id == organization_id)
                .order_by(User.id.asc())
            )
            users = session.scalars(statement).all()
            return [self._user_to_dict(user) for user in users]

    def create_invitation(
        self,
        *,
        organization_id: int,
        invited_by_user_id: int,
        email: str,
        role: str,
        expires_in_days: int = 7,
    ) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        with self.session_factory() as session:
            existing_user = session.scalar(select(User.id).where(User.email == normalized_email))
            if existing_user is not None:
                raise ValueError("User with this email already exists")

            existing_invitation = session.scalar(
                select(OrganizationInvitation).where(
                    OrganizationInvitation.organization_id == organization_id,
                    OrganizationInvitation.email == normalized_email,
                    OrganizationInvitation.status == "pending",
                )
            )
            if existing_invitation is not None:
                raise ValueError("Pending invitation for this email already exists")

            invitation = OrganizationInvitation(
                organization_id=organization_id,
                invited_by_user_id=invited_by_user_id,
                email=normalized_email,
                role=role,
                status="pending",
                token=secrets.token_urlsafe(24),
                expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
            )
            session.add(invitation)
            session.commit()
            session.refresh(invitation)

            record = session.scalar(
                select(OrganizationInvitation)
                .options(
                    joinedload(OrganizationInvitation.organization),
                    joinedload(OrganizationInvitation.invited_by),
                )
                .where(OrganizationInvitation.id == invitation.id)
            )
            if record is None:
                raise RuntimeError("Invitation was not created")
            return self._invitation_to_dict(record)

    def get_invitation_by_token(self, token: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            invitation = session.scalar(
                select(OrganizationInvitation)
                .options(
                    joinedload(OrganizationInvitation.organization),
                    joinedload(OrganizationInvitation.invited_by),
                )
                .where(OrganizationInvitation.token == token)
            )
            if invitation is None:
                return None
            return self._invitation_to_dict(invitation)

    def accept_invitation(
        self,
        *,
        token: str,
        full_name: str,
        password_hash: str,
        password_salt: str,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            invitation = session.scalar(
                select(OrganizationInvitation)
                .options(joinedload(OrganizationInvitation.organization))
                .where(OrganizationInvitation.token == token)
            )
            if invitation is None:
                raise ValueError("Invitation not found")
            if invitation.status != "pending":
                raise ValueError("Invitation is no longer active")
            expires_at = invitation.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= datetime.now(UTC):
                invitation.status = "expired"
                session.commit()
                raise ValueError("Invitation has expired")

            existing_user = session.scalar(select(User.id).where(User.email == invitation.email))
            if existing_user is not None:
                raise ValueError("User with this email already exists")

            user = User(
                organization_id=invitation.organization_id,
                email=invitation.email,
                full_name=full_name.strip() or None,
                password_hash=password_hash,
                password_salt=password_salt,
                role=invitation.role,
                is_active=True,
                is_owner=invitation.role == "owner",
            )
            session.add(user)
            session.flush()

            invitation.status = "accepted"
            invitation.accepted_at = datetime.now(UTC)
            session.commit()

            created_user = session.scalar(
                select(User)
                .options(joinedload(User.organization))
                .where(User.id == user.id)
            )
            if created_user is None:
                raise RuntimeError("User was not created from invitation")
            return self._user_to_dict(created_user)

    def list_invitations(
        self,
        *,
        organization_id: int,
        include_inactive: bool = True,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement: Select[tuple[OrganizationInvitation]] = (
                select(OrganizationInvitation)
                .options(
                    joinedload(OrganizationInvitation.organization),
                    joinedload(OrganizationInvitation.invited_by),
                )
                .where(OrganizationInvitation.organization_id == organization_id)
                .order_by(desc(OrganizationInvitation.id))
            )
            if not include_inactive:
                statement = statement.where(OrganizationInvitation.status == "pending")
            invitations = session.scalars(statement).all()
            return [self._invitation_to_dict(invitation) for invitation in invitations]

    def create_company_profile(
        self,
        payload: dict[str, Any],
        *,
        organization_id: int,
        user_id: int | None,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            company_profile = CompanyProfile(
                organization_id=organization_id,
                user_id=user_id,
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

    def get_company_profile(
        self,
        profile_id: int,
        organization_id: int | None = None,
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            company_profile = self._get_company_profile_entity(session, profile_id, organization_id)
            if company_profile is None:
                return None
            return self._company_profile_to_dict(company_profile)

    def list_company_profiles(
        self,
        *,
        organization_id: int,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement: Select[tuple[CompanyProfile]] = (
                select(CompanyProfile)
                .where(CompanyProfile.organization_id == organization_id)
                .order_by(desc(CompanyProfile.id))
                .limit(limit)
            )
            profiles = session.scalars(statement).all()
            return [self._company_profile_to_dict(profile) for profile in profiles]

    def update_company_profile(
        self,
        profile_id: int,
        payload: dict[str, Any],
        *,
        organization_id: int,
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            company_profile = self._get_company_profile_entity(session, profile_id, organization_id)
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

    def create_tender_input(
        self,
        payload: dict[str, Any],
        *,
        organization_id: int,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            company_profile = self._get_company_profile_entity(
                session,
                payload["company_profile_id"],
                organization_id,
            )
            if company_profile is None:
                raise RuntimeError("Company profile not found")

            tender_input = TenderInput(
                organization_id=organization_id,
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

    def get_tender_input(
        self,
        tender_input_id: int,
        organization_id: int | None = None,
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            statement = (
                select(TenderInput)
                .options(selectinload(TenderInput.analyses))
                .where(TenderInput.id == tender_input_id)
            )
            if organization_id is not None:
                statement = statement.where(TenderInput.organization_id == organization_id)
            tender_input = session.scalar(statement)
            if tender_input is None:
                return None
            return self._tender_input_to_dict(tender_input)

    def list_tender_inputs(
        self,
        *,
        organization_id: int,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement: Select[tuple[TenderInput]] = (
                select(TenderInput)
                .options(selectinload(TenderInput.analyses))
                .where(TenderInput.organization_id == organization_id)
                .order_by(desc(TenderInput.id))
                .limit(limit)
            )
            tender_inputs = session.scalars(statement).all()
            return [self._tender_input_to_dict(tender_input) for tender_input in tender_inputs]

    def create_analysis_job(
        self,
        *,
        organization_id: int,
        company_profile_id: int,
        tender_input_id: int,
        package_name: str,
        ai_summary_requested: bool = False,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            company_profile = self._get_company_profile_entity(session, company_profile_id, organization_id)
            tender_input = session.scalar(
                select(TenderInput).where(
                    TenderInput.id == tender_input_id,
                    TenderInput.organization_id == organization_id,
                )
            )
            if company_profile is None or tender_input is None:
                raise RuntimeError("Analysis context is invalid")

            analysis = TenderAnalysis(
                organization_id=organization_id,
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

    def apply_manual_correction(
        self,
        analysis_id: int,
        payload: dict[str, Any],
        *,
        organization_id: int,
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            statement = (
                select(TenderAnalysis)
                .options(joinedload(TenderAnalysis.result))
                .where(
                    TenderAnalysis.id == analysis_id,
                    TenderAnalysis.organization_id == organization_id,
                )
            )
            analysis = session.scalar(statement)
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

    def log_audit_event(
        self,
        *,
        organization_id: int,
        action: str,
        entity_type: str,
        entity_id: str | int | None = None,
        actor_user_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            event = AuditLog(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                payload=payload or {},
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            record = session.scalar(
                select(AuditLog)
                .options(joinedload(AuditLog.actor_user))
                .where(AuditLog.id == event.id)
            )
            if record is None:
                raise RuntimeError("Audit log was not created")
            return self._audit_log_to_dict(record)

    def list_audit_logs(
        self,
        *,
        organization_id: int,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement: Select[tuple[AuditLog]] = (
                select(AuditLog)
                .options(joinedload(AuditLog.actor_user))
                .where(AuditLog.organization_id == organization_id)
                .order_by(desc(AuditLog.id))
                .limit(limit)
            )
            logs = session.scalars(statement).all()
            return [self._audit_log_to_dict(log) for log in logs]

    def get_analysis(
        self,
        analysis_id: int,
        organization_id: int | None = None,
    ) -> dict[str, Any] | None:
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
            if organization_id is not None:
                statement = statement.where(TenderAnalysis.organization_id == organization_id)
            analysis = session.scalar(statement)
            if analysis is None:
                return None
            return self._analysis_to_dict(analysis)

    def list_analyses(
        self,
        *,
        organization_id: int,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement: Select[tuple[TenderAnalysis]] = (
                select(TenderAnalysis)
                .options(joinedload(TenderAnalysis.result))
                .where(TenderAnalysis.organization_id == organization_id)
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

    def _build_unique_organization_slug(self, session, organization_name: str) -> str:
        base_slug = slugify(organization_name)
        candidate = base_slug
        index = 2
        while session.scalar(select(Organization.id).where(Organization.slug == candidate)) is not None:
            candidate = f"{base_slug}-{index}"
            index += 1
        return candidate

    def _get_company_profile_entity(
        self,
        session,
        profile_id: int,
        organization_id: int | None,
    ) -> CompanyProfile | None:
        statement = select(CompanyProfile).where(CompanyProfile.id == profile_id)
        if organization_id is not None:
            statement = statement.where(CompanyProfile.organization_id == organization_id)
        return session.scalar(statement)

    def _user_to_dict(self, user: User) -> dict[str, Any]:
        organization = user.organization
        if organization is None:
            raise RuntimeError("User organization is required")
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_owner": user.is_owner,
            "password_hash": user.password_hash,
            "password_salt": user.password_salt,
            "organization": {
                "id": organization.id,
                "name": organization.name,
                "slug": organization.slug,
                "is_active": organization.is_active,
            },
        }

    def _invitation_to_dict(self, invitation: OrganizationInvitation) -> dict[str, Any]:
        organization = invitation.organization
        invited_by = invitation.invited_by
        return {
            "id": invitation.id,
            "organization_id": invitation.organization_id,
            "email": invitation.email,
            "role": invitation.role,
            "status": invitation.status,
            "token": invitation.token,
            "created_at": isoformat_utc(invitation.created_at),
            "updated_at": isoformat_utc(invitation.updated_at),
            "expires_at": isoformat_utc(invitation.expires_at),
            "accepted_at": isoformat_utc(invitation.accepted_at),
            "organization": {
                "id": organization.id,
                "name": organization.name,
                "slug": organization.slug,
            }
            if organization is not None
            else None,
            "invited_by": {
                "id": invited_by.id,
                "email": invited_by.email,
                "full_name": invited_by.full_name,
            }
            if invited_by is not None
            else None,
        }

    def _audit_log_to_dict(self, audit_log: AuditLog) -> dict[str, Any]:
        actor = audit_log.actor_user
        return {
            "id": audit_log.id,
            "organization_id": audit_log.organization_id,
            "action": audit_log.action,
            "entity_type": audit_log.entity_type,
            "entity_id": audit_log.entity_id,
            "payload": audit_log.payload,
            "created_at": isoformat_utc(audit_log.created_at),
            "actor_user": {
                "id": actor.id,
                "email": actor.email,
                "full_name": actor.full_name,
                "role": actor.role,
            }
            if actor is not None
            else None,
        }

    def _company_profile_to_dict(self, company_profile: CompanyProfile) -> dict[str, Any]:
        return {
            "id": company_profile.id,
            "organization_id": company_profile.organization_id,
            "user_id": company_profile.user_id,
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
            "organization_id": tender_input.organization_id,
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
            "organization_id": analysis.organization_id,
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
