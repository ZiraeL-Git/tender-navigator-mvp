from schemas import CompanyProfile, DecisionCode, DocumentType, TenderDocument
from services.analysis import analyze_tender_package


def make_profile(
    has_license=False,
    has_experience=False,
    can_prepare_fast=False,
):
    return CompanyProfile(
        company_name="ООО Тест",
        inn="7000000000",
        region="Томская область",
        categories=["канцелярия", "товары"],
        has_license=has_license,
        has_experience=has_experience,
        can_prepare_fast=can_prepare_fast,
        notes="",
    )


def test_analyze_tender_package_rejects_if_license_required_but_missing():
    docs = [
        TenderDocument(
            filename="notice.docx",
            doc_type=DocumentType.notice,
            extracted_text="""
            Номер извещения: 0123500000126001234
            Наименование закупки: Поставка специализированного оборудования
            Дата и время окончания срока подачи заявок: 15.04.2026 10:00
            Участник обязан иметь лицензию на осуществление деятельности.
            """,
            text_length=250,
        )
    ]

    profile = make_profile(
        has_license=False,
        has_experience=True,
        can_prepare_fast=True,
    )

    result = analyze_tender_package(docs, profile)

    assert result.decision_code == DecisionCode.stop
    assert result.decision_label == "СТОП"
    assert any(reason.code == "missing_license" for reason in result.decision_reasons)
    assert any(reason.rule_id == "stop.missing_license_requirement" for reason in result.decision_reasons)


def test_analyze_tender_package_rejects_if_experience_required_but_missing():
    docs = [
        TenderDocument(
            filename="notice.docx",
            doc_type=DocumentType.notice,
            extracted_text="""
            Номер извещения: 0123500000126001234
            Наименование закупки: Поставка оборудования
            Дата и время окончания срока подачи заявок: 15.04.2026 10:00
            Участник должен иметь опыт исполнения аналогичных контрактов.
            """,
            text_length=250,
        )
    ]

    profile = make_profile(
        has_license=True,
        has_experience=False,
        can_prepare_fast=True,
    )

    result = analyze_tender_package(docs, profile)

    assert result.decision_code == DecisionCode.stop
    assert result.decision_label == "СТОП"
    assert any(reason.code == "missing_experience" for reason in result.decision_reasons)
    assert any(reason.rule_id == "stop.missing_confirmed_experience" for reason in result.decision_reasons)


def test_analyze_tender_package_returns_manual_review_when_deadline_missing():
    docs = [
        TenderDocument(
            filename="notice.docx",
            doc_type=DocumentType.notice,
            extracted_text="""
            Номер извещения: 0123500000126001234
            Наименование закупки: Поставка канцелярских товаров
            """,
            text_length=120,
        )
    ]

    profile = make_profile(
        has_license=True,
        has_experience=True,
        can_prepare_fast=True,
    )

    result = analyze_tender_package(docs, profile)

    assert result.decision_code == DecisionCode.manual_review
    assert result.decision_label == "ПРОВЕРИТЬ ВРУЧНУЮ"
    assert any(reason.code == "deadline_not_found" for reason in result.decision_reasons)
    assert any(reason.rule_id == "manual_review.deadline_missing" for reason in result.decision_reasons)


def test_analyze_tender_package_returns_risk_review_if_company_is_slow():
    docs = [
        TenderDocument(
            filename="notice.docx",
            doc_type=DocumentType.notice,
            extracted_text="""
            Номер извещения: 0123500000126001234
            Наименование закупки: Поставка канцелярских товаров
            Дата и время окончания срока подачи заявок: 15.04.2026 10:00
            Начальная (максимальная) цена контракта: 450 000,00
            """,
            text_length=200,
        )
    ]

    profile = make_profile(
        has_license=True,
        has_experience=True,
        can_prepare_fast=False,
    )

    result = analyze_tender_package(docs, profile)

    assert result.decision_code == DecisionCode.risk
    assert result.decision_label == "РИСК"
    assert any(reason.code == "slow_preparation_risk" for reason in result.decision_reasons)
    assert any(reason.rule_id == "risk.company_not_ready_for_fast_preparation" for reason in result.decision_reasons)


def test_analyze_tender_package_returns_go_for_simple_valid_case():
    docs = [
        TenderDocument(
            filename="notice.docx",
            doc_type=DocumentType.notice,
            extracted_text="""
            Номер извещения: 0123500000126001234
            Наименование закупки: Поставка канцелярских товаров
            Наименование организации: Муниципальное бюджетное учреждение "Школа №1"
            Дата и время окончания срока подачи заявок: 15.04.2026 10:00
            Начальная (максимальная) цена контракта: 450 000,00
            Требуется обеспечение заявки на участие в закупке.
            """,
            text_length=350,
        ),
        TenderDocument(
            filename="contract.docx",
            doc_type=DocumentType.contract,
            extracted_text="""
            Размер обеспечения исполнения контракта: 10%
            Срок поставки: в течение 10 календарных дней с даты заключения договора
            Требуется гарантия качества товара, работы, услуги: Да
            """,
            text_length=220,
        ),
    ]

    profile = make_profile(
        has_license=True,
        has_experience=True,
        can_prepare_fast=True,
    )

    result = analyze_tender_package(docs, profile)

    assert result.decision_code == DecisionCode.go
    assert result.decision_label == "ИДЕМ"
    assert any(reason.rule_id == "go.no_blockers_detected" for reason in result.decision_reasons)
    assert result.extracted.notice_number == "0123500000126001234"
    assert result.extracted.object_name == "Поставка канцелярских товаров"
    assert result.extracted.customer_name == 'Муниципальное бюджетное учреждение "Школа №1"'
    assert result.extracted.price == "450000.00"
    assert result.extracted.deadline == "15.04.2026 10:00"
    assert result.extracted.supply_term == "в течение 10 календарных дней с даты заключения договора"
    assert result.extracted.bid_security == "Требуется"
    assert result.extracted.contract_security == "10%"
    assert result.extracted.quality_guarantee == "Да"
