from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, model_validator


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str


class AuthUserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_owner: bool
    organization: OrganizationResponse


class AuthBootstrapResponse(BaseModel):
    setup_required: bool


class AuthRegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    full_name: str = Field(min_length=2, max_length=255)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=255)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=255)


class AuthSessionResponse(BaseModel):
    access_token: str
    token_type: str
    user: AuthUserResponse


class InvitationCreateRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    role: str = Field(default="operator", pattern="^(owner|operator|viewer)$")


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=10, max_length=255)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class InvitationInviterResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None


class InvitationResponse(BaseModel):
    id: int
    organization_id: int
    email: str
    role: str
    status: str
    token: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    organization: Optional[OrganizationResponse] = None
    invited_by: Optional[InvitationInviterResponse] = None


class AuditActorResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str


class AuditLogResponse(BaseModel):
    id: int
    organization_id: int
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    actor_user: Optional[AuditActorResponse] = None


class CompanyProfileCreate(BaseModel):
    company_name: str = ""
    inn: str = ""
    region: str = ""
    categories: List[str] = Field(default_factory=list)
    has_license: bool = False
    has_experience: bool = False
    can_prepare_fast: bool = True
    notes: str = ""


class CompanyProfileUpdate(CompanyProfileCreate):
    pass


class CompanyProfileResponse(CompanyProfileCreate):
    id: int
    created_at: datetime


class TenderDocumentResponse(BaseModel):
    filename: str
    doc_type: str
    extracted_text: Optional[str] = None
    text_length: int


class DecisionReasonResponse(BaseModel):
    code: str
    severity: str
    message: str
    rule_id: str
    rule_title: str
    decision_code: str


class ExtractedFieldsResponse(BaseModel):
    notice_number: Optional[str] = None
    object_name: Optional[str] = None
    customer_name: Optional[str] = None
    price: Optional[str] = None
    deadline: Optional[str] = None
    supply_term: Optional[str] = None
    bid_security: Optional[str] = None
    contract_security: Optional[str] = None
    quality_guarantee: Optional[str] = None
    need_license: bool = False
    need_experience: bool = False


class AnalysisEventResponse(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AnalysisResponse(BaseModel):
    id: int
    created_at: datetime
    company_profile_id: int
    tender_input_id: Optional[int] = None
    package_name: str
    status: str
    background_task_id: Optional[str] = None
    failure_reason: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    ai_summary_requested: bool = False
    raw_text: Optional[str] = None
    extracted: ExtractedFieldsResponse
    decision_code: Optional[str] = None
    decision_label: Optional[str] = None
    decision_reasons: List[DecisionReasonResponse] = Field(default_factory=list)
    checklist: List[str] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    documents: List[TenderDocumentResponse] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    events: List[AnalysisEventResponse] = Field(default_factory=list)


class AnalysisListItem(BaseModel):
    id: int
    created_at: datetime
    company_profile_id: int
    tender_input_id: Optional[int] = None
    package_name: str
    status: str
    background_task_id: Optional[str] = None
    decision_code: Optional[str] = None
    decision_label: Optional[str] = None
    notice_number: Optional[str] = None
    object_name: Optional[str] = None
    deadline: Optional[str] = None


class TenderInputDocumentResponse(BaseModel):
    filename: str
    content_type: str
    size: int
    kind: str


class TenderInputImportRequest(BaseModel):
    company_profile_id: int
    notice_number: Optional[str] = None
    source_url: Optional[str] = None
    title: Optional[str] = None
    customer_name: Optional[str] = None
    deadline: Optional[str] = None
    max_price: Optional[str] = None
    auto_analyze: bool = False
    include_ai_summary: bool = False

    @model_validator(mode="after")
    def validate_source(self) -> "TenderInputImportRequest":
        if not self.notice_number and not self.source_url:
            raise ValueError("Either notice_number or source_url is required")
        return self


class TenderInputResponse(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    company_profile_id: int
    source_type: str
    source_value: str
    source_url: Optional[str] = None
    notice_number: Optional[str] = None
    title: str
    customer_name: Optional[str] = None
    deadline: Optional[str] = None
    max_price: Optional[str] = None
    status: str
    normalized_payload: dict[str, Any] = Field(default_factory=dict)
    documents: List[TenderInputDocumentResponse] = Field(default_factory=list)
    last_error: Optional[str] = None
    latest_analysis_id: Optional[int] = None


class TenderInputListItem(BaseModel):
    id: int
    created_at: datetime
    company_profile_id: int
    source_type: str
    source_value: str
    title: str
    status: str
    notice_number: Optional[str] = None
    latest_analysis_id: Optional[int] = None
    document_count: int = 0


class QueueAnalysisRequest(BaseModel):
    include_ai_summary: bool = False


class ManualCorrectionRequest(BaseModel):
    decision_code: Optional[str] = None
    decision_label: Optional[str] = None
    checklist: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    extracted: Optional[ExtractedFieldsResponse] = None
    comment: str = ""


class HealthResponse(BaseModel):
    status: str
