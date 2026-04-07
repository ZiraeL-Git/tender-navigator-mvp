from schemas import DocumentType, TenderDocument
from services.extractors import (
    detect_experience_requirement,
    detect_license_requirement,
    extract_with_priority,
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


def test_find_notice_number():
    text = """
    Извещение о проведении закупки
    Номер извещения: 0123500000126001234
    """
    assert find_notice_number(text) == "0123500000126001234"


def test_find_object_name():
    text = """
    Наименование закупки: Поставка канцелярских товаров
    Способ проведения закупки: Электронный аукцион
    """
    assert find_object_name(text) == "Поставка канцелярских товаров"


def test_find_customer_name():
    text = """
    Наименование организации: Муниципальное бюджетное учреждение "Центр развития"
    Место нахождения: Томская область
    """
    assert find_customer_name(text) == 'Муниципальное бюджетное учреждение "Центр развития"'


def test_find_price():
    text = """
    Начальная (максимальная) цена контракта: 450 000,00
    """
    assert find_price(text) == "450000.00"


def test_find_deadline():
    text = """
    Дата и время окончания срока подачи заявок: 15.04.2026 10:00
    """
    assert find_deadline(text) == "15.04.2026 10:00"


def test_find_supply_term():
    text = """
    Срок поставки: в течение 10 календарных дней с даты заключения договора
    РАЗДЕЛ 15
    """
    assert find_supply_term(text) == "в течение 10 календарных дней с даты заключения договора"


def test_find_bid_security_required():
    text = """
    Требуется обеспечение заявки на участие в закупке.
    """
    assert find_bid_security(text) == "Требуется"


def test_find_contract_security_percent():
    text = """
    Размер обеспечения исполнения контракта: 10%
    """
    assert find_contract_security(text) == "10%"


def test_find_quality_guarantee():
    text = """
    Требуется гарантия качества товара, работы, услуги: Да
    """
    assert find_quality_guarantee(text) == "Да"


def test_detect_license_requirement_true():
    text = """
    Участник закупки должен иметь действующую лицензию на осуществление деятельности.
    """
    assert detect_license_requirement(text) is True


def test_detect_license_requirement_false():
    text = """
    Поставка бумаги и канцелярских принадлежностей.
    """
    assert detect_license_requirement(text) is False


def test_detect_experience_requirement_true():
    text = """
    Участник должен иметь опыт исполнения аналогичных контрактов за последние 3 года.
    """
    assert detect_experience_requirement(text) is True


def test_detect_experience_requirement_false():
    text = """
    Закупка канцелярских товаров без специальных квалификационных требований.
    """
    assert detect_experience_requirement(text) is False


def test_extract_with_priority_uses_notice_first():
    docs = [
        TenderDocument(
            filename="contract.docx",
            doc_type=DocumentType.contract,
            extracted_text="Номер извещения: 9999999999999999999",
            text_length=40,
        ),
        TenderDocument(
            filename="notice.docx",
            doc_type=DocumentType.notice,
            extracted_text="Номер извещения: 0123500000126001234",
            text_length=40,
        ),
    ]

    result = extract_with_priority(docs, find_notice_number)
    assert result == "0123500000126001234"

def test_find_object_name_stops_before_customer_field():
    text = """
    Наименование закупки: Поставка канцелярских товаров
    Наименование организации: Муниципальное бюджетное учреждение "Школа №1"
    """
    assert find_object_name(text) == "Поставка канцелярских товаров"


def test_detect_license_requirement_false_for_word_srok():
    text = """
    Срок поставки: в течение 10 календарных дней с даты заключения договора
    """
    assert detect_license_requirement(text) is False