from schemas import (
    AnalysisDebugInfo,
    AnalysisStatus,
    CompanyProfile,
    DocumentType,
    ExtractionEvidence,
    TenderAnalysisResult,
    TenderDocument,
    TenderExtractedFields,
)

from services.decision import build_checklist, make_decision
from services.document_io import combine_documents_text
from services.extractors import (
    detect_experience_requirement,
    detect_license_requirement,
    extract_with_priority_debug,
    find_bid_security,
    find_contract_security,
    find_customer_name,
    find_deadline,
    find_notice_number,
    find_object_name,
    find_price,
    find_quality_guarantee,
    find_supply_term,
)


def build_company_profile(
    company_name,
    company_inn,
    company_region,
    company_categories_raw,
    company_has_license,
    company_has_experience,
    company_can_prepare_fast,
    company_notes,
) -> CompanyProfile:
    categories = (
        [item.strip() for item in company_categories_raw.split(",") if item.strip()]
        if company_categories_raw
        else []
    )

    return CompanyProfile(
        company_name=company_name.strip() if company_name else "",
        inn=company_inn.strip() if company_inn else "",
        region=company_region.strip() if company_region else "",
        categories=categories,
        has_license=(company_has_license == "Да"),
        has_experience=(company_has_experience == "Да"),
        can_prepare_fast=(company_can_prepare_fast == "Да"),
        notes=company_notes.strip() if company_notes else "",
    )


def build_package_name(documents: list[TenderDocument]) -> str:
    if not documents:
        return "Без названия"
    return ", ".join([doc.filename for doc in documents])


def build_extracted_fields(
    documents: list[TenderDocument],
) -> tuple[TenderExtractedFields, list[ExtractionEvidence]]:
    combined_text = combine_documents_text(documents)
    evidences: list[ExtractionEvidence] = []

    notice_number, ev = extract_with_priority_debug(
        documents=documents,
        field_name="notice_number",
        extractor=find_notice_number,
        extractor_name="find_notice_number",
        preferred_types=(
            DocumentType.notice,
            DocumentType.other,
            DocumentType.contract,
            DocumentType.spec,
        ),
    )
    if ev:
        evidences.append(ev)

    object_name, ev = extract_with_priority_debug(
        documents=documents,
        field_name="object_name",
        extractor=find_object_name,
        extractor_name="find_object_name",
    )
    if ev:
        evidences.append(ev)

    customer_name, ev = extract_with_priority_debug(
        documents=documents,
        field_name="customer_name",
        extractor=find_customer_name,
        extractor_name="find_customer_name",
        preferred_types=(
            DocumentType.notice,
            DocumentType.contract,
            DocumentType.other,
            DocumentType.spec,
        ),
    )
    if ev:
        evidences.append(ev)

    price, ev = extract_with_priority_debug(
        documents=documents,
        field_name="price",
        extractor=find_price,
        extractor_name="find_price",
        preferred_types=(
            DocumentType.notice,
            DocumentType.contract,
            DocumentType.other,
            DocumentType.spec,
        ),
    )
    if ev:
        evidences.append(ev)

    deadline, ev = extract_with_priority_debug(
        documents=documents,
        field_name="deadline",
        extractor=find_deadline,
        extractor_name="find_deadline",
        preferred_types=(
            DocumentType.notice,
            DocumentType.other,
            DocumentType.contract,
            DocumentType.spec,
        ),
    )
    if ev:
        evidences.append(ev)

    supply_term, ev = extract_with_priority_debug(
        documents=documents,
        field_name="supply_term",
        extractor=find_supply_term,
        extractor_name="find_supply_term",
        preferred_types=(
            DocumentType.contract,
            DocumentType.spec,
            DocumentType.notice,
            DocumentType.other,
        ),
    )
    if ev:
        evidences.append(ev)

    bid_security, ev = extract_with_priority_debug(
        documents=documents,
        field_name="bid_security",
        extractor=find_bid_security,
        extractor_name="find_bid_security",
        preferred_types=(
            DocumentType.notice,
            DocumentType.contract,
            DocumentType.other,
            DocumentType.spec,
        ),
    )
    if ev:
        evidences.append(ev)

    contract_security, ev = extract_with_priority_debug(
        documents=documents,
        field_name="contract_security",
        extractor=find_contract_security,
        extractor_name="find_contract_security",
        preferred_types=(
            DocumentType.contract,
            DocumentType.notice,
            DocumentType.other,
            DocumentType.spec,
        ),
    )
    if ev:
        evidences.append(ev)

    quality_guarantee, ev = extract_with_priority_debug(
        documents=documents,
        field_name="quality_guarantee",
        extractor=find_quality_guarantee,
        extractor_name="find_quality_guarantee",
        preferred_types=(
            DocumentType.contract,
            DocumentType.spec,
            DocumentType.notice,
            DocumentType.other,
        ),
    )
    if ev:
        evidences.append(ev)

    extracted = TenderExtractedFields(
        notice_number=notice_number,
        object_name=object_name,
        customer_name=customer_name,
        price=price,
        deadline=deadline,
        supply_term=supply_term,
        bid_security=bid_security,
        contract_security=contract_security,
        quality_guarantee=quality_guarantee,
        need_license=detect_license_requirement(combined_text),
        need_experience=detect_experience_requirement(combined_text),
    )

    return extracted, evidences


def analyze_tender_package(
    documents: list[TenderDocument],
    profile: CompanyProfile,
    ai_summary: str = "",
) -> TenderAnalysisResult:
    raw_text = combine_documents_text(documents)
    extracted, evidences = build_extracted_fields(documents)

    decision_code, decision_label, decision_reasons = make_decision(extracted, profile)
    checklist = build_checklist(extracted, profile)

    warnings: list[str] = []
    errors: list[str] = []

    if len(raw_text.strip()) < 50:
        warnings.append("Извлеченный текст слишком короткий. Возможно, PDF без текстового слоя и нужен OCR fallback.")

    if not extracted.notice_number:
        warnings.append("Не удалось определить номер извещения.")

    if not extracted.object_name:
        warnings.append("Не удалось определить объект закупки.")

    if not extracted.deadline:
        warnings.append("Не удалось определить срок подачи заявки.")

    return TenderAnalysisResult(
        schema_version="1.0",
        status=AnalysisStatus.analyzed,
        package_name=build_package_name(documents),
        raw_text=raw_text,
        extracted=extracted,
        decision_code=decision_code,
        decision_label=decision_label,
        decision_reasons=decision_reasons,
        checklist=checklist,
        ai_summary=ai_summary or None,
        documents=documents,
        warnings=warnings,
        errors=errors,
        debug=AnalysisDebugInfo(evidences=evidences),
    )