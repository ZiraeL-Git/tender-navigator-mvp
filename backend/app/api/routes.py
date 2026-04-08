from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from backend.app.api.dependencies import get_auth_service, get_current_user, get_owner_user
from backend.app.api.schemas import (
    AnalysisListItem,
    AnalysisResponse,
    AuditActorResponse,
    AuditLogResponse,
    AuthBootstrapResponse,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthSessionResponse,
    AuthUserResponse,
    CompanyProfileCreate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
    HealthResponse,
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationInviterResponse,
    InvitationResponse,
    ManualCorrectionRequest,
    OrganizationResponse,
    QueueAnalysisRequest,
    TenderInputImportRequest,
    TenderInputListItem,
    TenderInputResponse,
)
from backend.app.services.auth import AuthService, AuthenticatedUser


router = APIRouter()


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_auth_user_response(record: dict) -> AuthUserResponse:
    return AuthUserResponse(
        id=record["id"],
        email=record["email"],
        full_name=record["full_name"],
        role=record["role"],
        is_active=record["is_active"],
        is_owner=record["is_owner"],
        organization=OrganizationResponse(
            id=record["organization"]["id"],
            name=record["organization"]["name"],
            slug=record["organization"]["slug"],
        ),
    )


def build_invitation_response(record: dict) -> InvitationResponse:
    organization = record.get("organization")
    invited_by = record.get("invited_by")
    return InvitationResponse(
        id=record["id"],
        organization_id=record["organization_id"],
        email=record["email"],
        role=record["role"],
        status=record["status"],
        token=record["token"],
        created_at=parse_datetime(record["created_at"]),
        updated_at=parse_datetime(record["updated_at"]),
        expires_at=parse_datetime(record["expires_at"]),
        accepted_at=parse_datetime(record["accepted_at"]),
        organization=(
            OrganizationResponse(
                id=organization["id"],
                name=organization["name"],
                slug=organization["slug"],
            )
            if organization is not None
            else None
        ),
        invited_by=(
            InvitationInviterResponse(
                id=invited_by["id"],
                email=invited_by["email"],
                full_name=invited_by["full_name"],
            )
            if invited_by is not None
            else None
        ),
    )


def build_audit_log_response(record: dict) -> AuditLogResponse:
    actor_user = record.get("actor_user")
    return AuditLogResponse(
        id=record["id"],
        organization_id=record["organization_id"],
        action=record["action"],
        entity_type=record["entity_type"],
        entity_id=record["entity_id"],
        payload=record["payload"],
        created_at=parse_datetime(record["created_at"]),
        actor_user=(
            AuditActorResponse(
                id=actor_user["id"],
                email=actor_user["email"],
                full_name=actor_user["full_name"],
                role=actor_user["role"],
            )
            if actor_user is not None
            else None
        ),
    )


def build_auth_session_response(record: dict) -> AuthSessionResponse:
    return AuthSessionResponse(
        access_token=record["access_token"],
        token_type=record["token_type"],
        user=build_auth_user_response(record["user"]),
    )


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


@router.get("/auth/bootstrap", response_model=AuthBootstrapResponse, tags=["auth"])
def get_bootstrap_status(
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthBootstrapResponse:
    return AuthBootstrapResponse(setup_required=auth_service.is_setup_required())


@router.post(
    "/auth/register",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
def register_owner(
    payload: AuthRegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    try:
        record = auth_service.register_owner(
            organization_name=payload.organization_name,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    request.app.state.storage.log_audit_event(
        organization_id=record["user"]["organization"]["id"],
        actor_user_id=record["user"]["id"],
        action="auth.register_owner",
        entity_type="user",
        entity_id=record["user"]["id"],
        payload={"email": record["user"]["email"], "role": record["user"]["role"]},
    )
    return build_auth_session_response(record)


@router.post("/auth/login", response_model=AuthSessionResponse, tags=["auth"])
def login(
    payload: AuthLoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    record = auth_service.login(email=payload.email, password=payload.password)
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    request.app.state.storage.log_audit_event(
        organization_id=record["user"]["organization"]["id"],
        actor_user_id=record["user"]["id"],
        action="auth.login",
        entity_type="user",
        entity_id=record["user"]["id"],
        payload={"email": record["user"]["email"]},
    )
    return build_auth_session_response(record)


@router.get("/auth/invitations/{token}", response_model=InvitationResponse, tags=["auth"])
def get_invitation(
    token: str,
    auth_service: AuthService = Depends(get_auth_service),
) -> InvitationResponse:
    record = auth_service.get_invitation(token)
    if record is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return build_invitation_response(record)


@router.post("/auth/accept-invitation", response_model=AuthSessionResponse, tags=["auth"])
def accept_invitation(
    payload: InvitationAcceptRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    try:
        record = auth_service.accept_invitation(
            token=payload.token,
            full_name=payload.full_name,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    request.app.state.storage.log_audit_event(
        organization_id=record["user"]["organization"]["id"],
        actor_user_id=record["user"]["id"],
        action="auth.accept_invitation",
        entity_type="user",
        entity_id=record["user"]["id"],
        payload={"email": record["user"]["email"], "role": record["user"]["role"]},
    )
    return build_auth_session_response(record)


@router.get("/auth/me", response_model=AuthUserResponse, tags=["auth"])
def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthUserResponse:
    record = auth_service.get_user_payload(current_user.user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    return build_auth_user_response(record)


@router.get("/organization/users", response_model=list[AuthUserResponse], tags=["organization"])
def list_organization_users(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[AuthUserResponse]:
    records = request.app.state.storage.list_organization_users(
        organization_id=current_user.organization_id
    )
    return [build_auth_user_response(record) for record in records]


@router.get(
    "/organization/invitations",
    response_model=list[InvitationResponse],
    tags=["organization"],
)
def list_organization_invitations(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[InvitationResponse]:
    records = request.app.state.storage.list_invitations(
        organization_id=current_user.organization_id
    )
    return [build_invitation_response(record) for record in records]


@router.post(
    "/organization/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["organization"],
)
def create_organization_invitation(
    payload: InvitationCreateRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_owner_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> InvitationResponse:
    try:
        record = auth_service.create_invitation(
            organization_id=current_user.organization_id,
            invited_by_user_id=current_user.user_id,
            email=payload.email,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    request.app.state.storage.log_audit_event(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="organization.invitation_created",
        entity_type="organization_invitation",
        entity_id=record["id"],
        payload={"email": record["email"], "role": record["role"]},
    )
    return build_invitation_response(record)


@router.get("/audit-logs", response_model=list[AuditLogResponse], tags=["audit"])
def list_audit_logs(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 50,
) -> list[AuditLogResponse]:
    records = request.app.state.storage.list_audit_logs(
        organization_id=current_user.organization_id,
        limit=limit,
    )
    return [build_audit_log_response(record) for record in records]


@router.post(
    "/company-profiles",
    response_model=CompanyProfileResponse,
    status_code=201,
    tags=["company_profiles"],
)
def create_company_profile(
    payload: CompanyProfileCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CompanyProfileResponse:
    record = request.app.state.storage.create_company_profile(
        payload.model_dump(),
        organization_id=current_user.organization_id,
        user_id=current_user.user_id,
    )
    request.app.state.storage.log_audit_event(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="company_profile.created",
        entity_type="company_profile",
        entity_id=record["id"],
        payload={"company_name": record["company_name"], "inn": record["inn"]},
    )
    return build_company_profile_response(record)


@router.get(
    "/company-profiles",
    response_model=list[CompanyProfileResponse],
    tags=["company_profiles"],
)
def list_company_profiles(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 50,
) -> list[CompanyProfileResponse]:
    records = request.app.state.storage.list_company_profiles(
        organization_id=current_user.organization_id,
        limit=limit,
    )
    return [build_company_profile_response(record) for record in records]


@router.get(
    "/company-profiles/{profile_id}",
    response_model=CompanyProfileResponse,
    tags=["company_profiles"],
)
def get_company_profile(
    profile_id: int,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CompanyProfileResponse:
    record = request.app.state.storage.get_company_profile(
        profile_id,
        organization_id=current_user.organization_id,
    )
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
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CompanyProfileResponse:
    record = request.app.state.storage.update_company_profile(
        profile_id,
        payload.model_dump(),
        organization_id=current_user.organization_id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Company profile not found")
    request.app.state.storage.log_audit_event(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="company_profile.updated",
        entity_type="company_profile",
        entity_id=record["id"],
        payload={"company_name": record["company_name"], "inn": record["inn"]},
    )

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
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TenderInputResponse:
    storage = request.app.state.storage
    tender_input_service = request.app.state.tender_input_service
    analysis_pipeline = request.app.state.analysis_pipeline

    company_profile = storage.get_company_profile(
        payload.company_profile_id,
        organization_id=current_user.organization_id,
    )
    if company_profile is None:
        raise HTTPException(status_code=404, detail="Company profile not found")

    tender_input = tender_input_service.import_from_reference(
        payload,
        organization_id=current_user.organization_id,
    )
    if payload.auto_analyze:
        analysis_pipeline.queue_analysis_for_tender_input(
            tender_input_id=tender_input["id"],
            organization_id=current_user.organization_id,
            include_ai_summary=payload.include_ai_summary,
        )
        tender_input = (
            storage.get_tender_input(
                tender_input["id"],
                organization_id=current_user.organization_id,
            )
            or tender_input
        )

    storage.log_audit_event(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="tender_input.imported",
        entity_type="tender_input",
        entity_id=tender_input["id"],
        payload={"source_type": tender_input["source_type"], "title": tender_input["title"]},
    )

    return build_tender_input_response(tender_input)


@router.get(
    "/tender-inputs/{tender_input_id}",
    response_model=TenderInputResponse,
    tags=["tender_inputs"],
)
def get_tender_input(
    tender_input_id: int,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TenderInputResponse:
    record = request.app.state.storage.get_tender_input(
        tender_input_id,
        organization_id=current_user.organization_id,
    )
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
    current_user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 50,
) -> list[TenderInputListItem]:
    records = request.app.state.storage.list_tender_inputs(
        organization_id=current_user.organization_id,
        limit=limit,
    )
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
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AnalysisResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    storage = request.app.state.storage
    tender_input_service = request.app.state.tender_input_service
    analysis_pipeline = request.app.state.analysis_pipeline

    company_profile = storage.get_company_profile(
        company_profile_id,
        organization_id=current_user.organization_id,
    )
    if company_profile is None:
        raise HTTPException(status_code=404, detail="Company profile not found")

    tender_input = await tender_input_service.create_manual_upload_input(
        company_profile_id=company_profile_id,
        organization_id=current_user.organization_id,
        files=files,
    )
    analysis = analysis_pipeline.queue_analysis_for_tender_input(
        tender_input_id=tender_input["id"],
        organization_id=current_user.organization_id,
        include_ai_summary=include_ai_summary,
    )
    storage.log_audit_event(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="analysis.created_from_files",
        entity_type="analysis",
        entity_id=analysis["id"],
        payload={"company_profile_id": company_profile_id, "tender_input_id": tender_input["id"]},
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
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AnalysisResponse:
    try:
        analysis = request.app.state.analysis_pipeline.queue_analysis_for_tender_input(
            tender_input_id=tender_input_id,
            organization_id=current_user.organization_id,
            include_ai_summary=payload.include_ai_summary,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    request.app.state.storage.log_audit_event(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="analysis.created_from_tender_input",
        entity_type="analysis",
        entity_id=analysis["id"],
        payload={"tender_input_id": tender_input_id},
    )

    return build_analysis_response(analysis)


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    tags=["analyses"],
)
def get_analysis(
    analysis_id: int,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AnalysisResponse:
    record = request.app.state.storage.get_analysis(
        analysis_id,
        organization_id=current_user.organization_id,
    )
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
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AnalysisResponse:
    record = request.app.state.storage.apply_manual_correction(
        analysis_id,
        payload.model_dump(mode="json", exclude_none=True),
        organization_id=current_user.organization_id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    request.app.state.storage.log_audit_event(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.user_id,
        action="analysis.manual_correction_applied",
        entity_type="analysis",
        entity_id=record["id"],
        payload={
            "decision_code": record["decision_code"],
            "decision_label": record["decision_label"],
        },
    )

    return build_analysis_response(record)


@router.get(
    "/analyses",
    response_model=list[AnalysisListItem],
    tags=["analyses"],
)
def list_analyses(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 50,
) -> list[AnalysisListItem]:
    records = request.app.state.storage.list_analyses(
        organization_id=current_user.organization_id,
        limit=limit,
    )
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
