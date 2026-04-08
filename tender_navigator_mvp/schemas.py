from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    notice = "notice"
    spec = "spec"
    contract = "contract"
    attachment = "attachment"
    other = "other"


class DecisionCode(str, Enum):
    go = "go"
    stop = "stop"
    manual_review = "manual_review"
    risk = "risk"


class ReasonSeverity(str, Enum):
    info = "info"
    warning = "warning"
    risk = "risk"
    stop = "stop"


class AnalysisStatus(str, Enum):
    uploaded = "uploaded"
    parsed = "parsed"
    analyzed = "analyzed"
    failed = "failed"


class TenderDocument(BaseModel):
    filename: str
    doc_type: DocumentType = DocumentType.other
    extracted_text: Optional[str] = None
    text_length: int = 0


class CompanyProfile(BaseModel):
    company_name: str = ""
    inn: str = ""
    region: str = ""
    categories: List[str] = Field(default_factory=list)
    has_license: bool = False
    has_experience: bool = False
    can_prepare_fast: bool = False
    notes: str = ""


class DecisionReason(BaseModel):
    code: str
    severity: ReasonSeverity
    message: str
    rule_id: str
    rule_title: str
    decision_code: DecisionCode


class TenderExtractedFields(BaseModel):
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


class TenderAnalysisResult(BaseModel):
    schema_version: str = "1.0"
    status: AnalysisStatus = AnalysisStatus.analyzed

    package_name: str
    raw_text: Optional[str] = None

    extracted: TenderExtractedFields
    decision_code: Optional[DecisionCode] = None
    decision_label: Optional[str] = None
    decision_reasons: List[DecisionReason] = Field(default_factory=list)
    checklist: List[str] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    documents: List[TenderDocument] = Field(default_factory=list)

    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
