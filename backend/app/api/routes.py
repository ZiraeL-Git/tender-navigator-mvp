from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from backend.app.api.schemas import (
    AnalysisListItem,
    AnalysisResponse,
    CompanyProfileCreate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
    HealthResponse,
    ManualCorrectionRequest,
    QueueAnalysisRequest,
    TenderInputImportRequest,
    TenderInputListItem,
    TenderInputResponse,
)


router = APIRouter()


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_company_profile_response(record: dict) -> CompanyProfileResponse:
    return CompanyProfileResponse(
        id=record["id"],
        created_at=parse_datetime(record["created_at"]),
        company_name=record["company_name"],
        inn=record["inn"],
        region=record["region"],
        categories=record["categories"],
        has_license=record["has_license"],
        has_experience=record["has_experience"],
        can_prepare_fast=record["can_prepare_fast"],
        notes=record["notes"],
    )


def build_analysis_response(record: dict) -> AnalysisResponse:
    return AnalysisResponse(
        id=record["id"],
        created_at=parse_datetime(record["created_at"]),
        company_profile_id=record["company_profile_id"],
        tender_input_id=record["tender_input_id"],
        package_name=record["package_name"],
        status=record["status"],
        background_task_id=record["background_task_id"],
        failure_reason=record["failure_reason"],
        started_at=parse_datetime(record["started_at"]),
        completed_at=parse_datetime(record["completed_at"]),
        ai_summary_requested=record["ai_summary_requested"],
        raw_text=record["raw_text"],
        extracted=record["extracted"],
        decision_code=record["decision_code"],
        decision_label=record["decision_label"],
        decision_reasons=record["decision_reasons"],
        checklist=record["checklist"],
        ai_summary=record["ai_summary"],
        documents=record["documents"],
        warnings=record["warnings"],
        errors=record["errors"],
        events=[
            {
                **event,
                "created_at": parse_datetime(event["created_at"]),
            }
            for event in record["events"]
        ],
    )


def build_tender_input_response(record: dict) -> TenderInputResponse:
    return TenderInputResponse(
        id=record["id"],
        created_at=parse_datetime(record["created_at"]),
        updated_at=parse_datetime(record["updated_at"]),
        company_profile_id=record["company_profile_id"],
        source_type=record["source_type"],
        source_value=record["source_value"],
        source_url=record["source_url"],
        notice_number=record["notice_number"],
        title=record["title"],
        customer_name=record["customer_name"],
        deadline=record["deadline"],
        max_price=record["max_price"],
        status=record["status"],
        normalized_payload=record["normalized_payload"],
        documents=record["documents"],
        last_error=record["last_error"],
        latest_analysis_id=record["latest_analysis_id"],
    )


@router.get("/health", response_model=HealthResponse, tags=["health"])
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post(
    "/company-profiles",
    response_model=CompanyProfileResponse,
    status_code=201,
    tags=["company_profiles"],
)
def create_company_profile(
    payload: CompanyProfileCreate,
    request: Request,
) -> CompanyProfileResponse:
    record = request.app.state.storage.create_company_profile(payload.model_dump())
    return build_company_profile_response(record)


@router.get(
    "/company-profiles",
    response_model=list[CompanyProfileResponse],
    tags=["company_profiles"],
)
def list_company_profiles(
    request: Request,
    limit: int = 50,
) -> list[CompanyProfileResponse]:
    records = request.app.state.storage.list_company_profiles(limit=limit)
    return [build_company_profile_response(record) for record in records]


@router.get(
    "/company-profiles/{profile_id}",
    response_model=CompanyProfileResponse,
    tags=["company_profiles"],
)
def get_company_profile(
    profile_id: int,
    request: Request,
) -> CompanyProfileResponse:
    record = request.app.state.storage.get_company_profile(profile_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Company profile not found")

    return build_company_profile_response(record)


@router.put(
    "/company-profiles/{profile_id}",
    response_model=CompanyProfileResponse,
    tags=["company_profiles"],
)
def update_company_profile(
    profile_id: int,
    payload: CompanyProfileUpdate,
    request: Request,
) -> CompanyProfileResponse:
    record = request.app.state.storage.update_company_profile(profile_id, payload.model_dump())
    if record is None:
        raise HTTPException(status_code=404, detail="Company profile not found")

    return build_company_profile_response(record)


@router.post(
    "/tender-inputs/import",
    response_model=TenderInputResponse,
    status_code=201,
    tags=["tender_inputs"],
)
def import_tender_input(
    payload: TenderInputImportRequest,
    request: Request,
) -> TenderInputResponse:
    storage = request.app.state.storage
    tender_input_service = request.app.state.tender_input_service
    analysis_pipeline = request.app.state.analysis_pipeline

    company_profile = storage.get_company_profile(payload.company_profile_id)
    if company_profile is None:
        raise HTTPException(status_code=404, detail="Company profile not found")

    tender_input = tender_input_service.import_from_reference(payload)
    if payload.auto_analyze:
        analysis_pipeline.queue_analysis_for_tender_input(
            tender_input_id=tender_input["id"],
            include_ai_summary=payload.include_ai_summary,
        )
        tender_input = storage.get_tender_input(tender_input["id"]) or tender_input

    return build_tender_input_response(tender_input)


@router.get(
    "/tender-inputs/{tender_input_id}",
    response_model=TenderInputResponse,
    tags=["tender_inputs"],
)
def get_tender_input(
    tender_input_id: int,
    request: Request,
) -> TenderInputResponse:
    record = request.app.state.storage.get_tender_input(tender_input_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tender input not found")

    return build_tender_input_response(record)


@router.get(
    "/tender-inputs",
    response_model=list[TenderInputListItem],
    tags=["tender_inputs"],
)
def list_tender_inputs(
    request: Request,
    limit: int = 50,
) -> list[TenderInputListItem]:
    records = request.app.state.storage.list_tender_inputs(limit=limit)
    return [
        TenderInputListItem(
            id=record["id"],
            created_at=parse_datetime(record["created_at"]),
            company_profile_id=record["company_profile_id"],
            source_type=record["source_type"],
            source_value=record["source_value"],
            title=record["title"],
            status=record["status"],
            notice_number=record["notice_number"],
            latest_analysis_id=record["latest_analysis_id"],
            document_count=len(record["documents"]),
        )
        for record in records
    ]


@router.post(
    "/analyses/from-files",
    response_model=AnalysisResponse,
    status_code=201,
    tags=["analyses"],
)
async def create_analysis_from_files(
    request: Request,
    company_profile_id: int,
    include_ai_summary: bool = False,
    files: list[UploadFile] = File(...),
) -> AnalysisResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    storage = request.app.state.storage
    tender_input_service = request.app.state.tender_input_service
    analysis_pipeline = request.app.state.analysis_pipeline

    company_profile = storage.get_company_profile(company_profile_id)
    if company_profile is None:
        raise HTTPException(status_code=404, detail="Company profile not found")

    tender_input = await tender_input_service.create_manual_upload_input(
        company_profile_id=company_profile_id,
        files=files,
    )
    analysis = analysis_pipeline.queue_analysis_for_tender_input(
        tender_input_id=tender_input["id"],
        include_ai_summary=include_ai_summary,
    )
    return build_analysis_response(analysis)


@router.post(
    "/analyses/from-tender-input/{tender_input_id}",
    response_model=AnalysisResponse,
    status_code=201,
    tags=["analyses"],
)
def create_analysis_from_tender_input(
    tender_input_id: int,
    payload: QueueAnalysisRequest,
    request: Request,
) -> AnalysisResponse:
    try:
        analysis = request.app.state.analysis_pipeline.queue_analysis_for_tender_input(
            tender_input_id=tender_input_id,
            include_ai_summary=payload.include_ai_summary,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return build_analysis_response(analysis)


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    tags=["analyses"],
)
def get_analysis(
    analysis_id: int,
    request: Request,
) -> AnalysisResponse:
    record = request.app.state.storage.get_analysis(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return build_analysis_response(record)


@router.patch(
    "/analyses/{analysis_id}/manual-correction",
    response_model=AnalysisResponse,
    tags=["analyses"],
)
def apply_manual_correction(
    analysis_id: int,
    payload: ManualCorrectionRequest,
    request: Request,
) -> AnalysisResponse:
    record = request.app.state.storage.apply_manual_correction(
        analysis_id,
        payload.model_dump(mode="json", exclude_none=True),
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return build_analysis_response(record)


@router.get(
    "/analyses",
    response_model=list[AnalysisListItem],
    tags=["analyses"],
)
def list_analyses(
    request: Request,
    limit: int = 50,
) -> list[AnalysisListItem]:
    records = request.app.state.storage.list_analyses(limit=limit)
    return [
        AnalysisListItem(
            id=record["id"],
            created_at=parse_datetime(record["created_at"]),
            company_profile_id=record["company_profile_id"],
            tender_input_id=record["tender_input_id"],
            package_name=record["package_name"],
            status=record["status"],
            background_task_id=record["background_task_id"],
            decision_code=record["decision_code"],
            decision_label=record["decision_label"],
            notice_number=record["extracted"].get("notice_number"),
            object_name=record["extracted"].get("object_name"),
            deadline=record["extracted"].get("deadline"),
        )
        for record in records
    ]
