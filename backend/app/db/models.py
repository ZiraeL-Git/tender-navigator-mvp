from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    invitations: Mapped[list["OrganizationInvitation"]] = relationship(back_populates="organization")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="organization")
    company_profiles: Mapped[list["CompanyProfile"]] = relationship(back_populates="organization")
    tender_inputs: Mapped[list["TenderInput"]] = relationship(back_populates="organization")
    analyses: Mapped[list["TenderAnalysis"]] = relationship(back_populates="organization")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="operator", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="users")
    company_profiles: Mapped[list["CompanyProfile"]] = relationship(back_populates="user")
    sent_invitations: Mapped[list["OrganizationInvitation"]] = relationship(
        back_populates="invited_by",
        foreign_keys="OrganizationInvitation.invited_by_user_id",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor_user")


class OrganizationInvitation(TimestampMixin, Base):
    __tablename__ = "organization_invitations"
    __table_args__ = (
        UniqueConstraint("token", name="uq_organization_invitations_token"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    invited_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="invitations")
    invited_by: Mapped[User | None] = relationship(
        back_populates="sent_invitations",
        foreign_keys=[invited_by_user_id],
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="audit_logs")
    actor_user: Mapped[User | None] = relationship(back_populates="audit_logs")


class CompanyProfile(TimestampMixin, Base):
    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    inn: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    region: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    has_license: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_experience: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_prepare_fast: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="company_profiles")
    user: Mapped[User | None] = relationship(back_populates="company_profiles")
    tender_inputs: Mapped[list["TenderInput"]] = relationship(back_populates="company_profile")
    analyses: Mapped[list["TenderAnalysis"]] = relationship(back_populates="company_profile")


class TenderInput(TimestampMixin, Base):
    __tablename__ = "tender_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    company_profile_id: Mapped[int] = mapped_column(ForeignKey("company_profiles.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_value: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notice_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_price: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="imported", nullable=False)
    normalized_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    documents: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="tender_inputs")
    company_profile: Mapped[CompanyProfile] = relationship(back_populates="tender_inputs")
    analyses: Mapped[list["TenderAnalysis"]] = relationship(back_populates="tender_input")


class TenderAnalysis(TimestampMixin, Base):
    __tablename__ = "tender_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    company_profile_id: Mapped[int] = mapped_column(ForeignKey("company_profiles.id"), nullable=False)
    tender_input_id: Mapped[int | None] = mapped_column(ForeignKey("tender_inputs.id"), nullable=True)
    package_name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    background_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_summary_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="analyses")
    company_profile: Mapped[CompanyProfile] = relationship(back_populates="analyses")
    tender_input: Mapped[TenderInput | None] = relationship(back_populates="analyses")
    documents: Mapped[list["TenderDocument"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    result: Mapped["AnalysisResult | None"] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        uselist=False,
    )
    events: Mapped[list["AnalysisEvent"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
    )


class TenderDocument(Base):
    __tablename__ = "tender_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("tender_analyses.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    analysis: Mapped[TenderAnalysis] = relationship(back_populates="documents")


class AnalysisResult(TimestampMixin, Base):
    __tablename__ = "analysis_results"
    __table_args__ = (UniqueConstraint("analysis_id", name="uq_analysis_results_analysis_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("tender_analyses.id"), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    decision_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    checklist: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    errors: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    analysis: Mapped[TenderAnalysis] = relationship(back_populates="result")


class AnalysisEvent(Base):
    __tablename__ = "analysis_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("tender_analyses.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    analysis: Mapped[TenderAnalysis] = relationship(back_populates="events")
