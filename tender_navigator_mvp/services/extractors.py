import re

from schemas import DocumentType, TenderDocument, ExtractionEvidence
from services.document_io import combine_documents_text
from services.text_utils import clean_object_name, normalize_text

from services.text_utils import clean_object_name, normalize_text, split_meaningful_lines


FIELD_START_PATTERNS = [
    r"^Номер\s+извещения\b",
    r"^Наименование\s+закупки\b",
    r"^Предмет\s+закупки\b",
    r"^Предмет\s+договора\b",
    r"^Наименование\s+объекта\s+закупки\b",
    r"^Наименование\s+организации\b",
    r"^Заказчик\b",
    r"^Место\s+нахождения\b",
    r"^Почтовый\s+адрес\b",
    r"^Дата\s+и\s+время\s+окончания\s+срока\s+подачи\s+заявок\b",
    r"^Дата\s+окончания\s+подачи\s+заявок\b",
    r"^Начальная\s*\(\s*максимальная\s*\)\s*цена\b",
    r"^НМЦК\b",
    r"^НМЦД\b",
    r"^Срок\s+поставки\b",
    r"^Срок\s+исполнения\b",
    r"^Размер\s+обеспечения\b",
    r"^Обеспечение\s+исполнени[ея]\b",
    r"^Обеспечение\s+заявк(?:и|ок)\b",
    r"^Требуется\s+гарантия\s+качества\b",
    r"^Способ\s+проведения\s+закупки\b",
    r"^Наименование\s+электронной\s+площадки\b",
    r"^Организатор\s+закупки\b",
    r"^РАЗДЕЛ\s+\d+\b",
]

def is_new_field_line(line: str) -> bool:
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in FIELD_START_PATTERNS)

def find_labeled_value(
    text: str,
    label_patterns: list[str],
    max_following_lines: int = 2,
) -> str | None:
    lines = split_meaningful_lines(text)

    for i, line in enumerate(lines):
        for label in label_patterns:
            match = re.search(rf"^(?:{label})\s*[:\-]?\s*(.*)$", line, re.IGNORECASE)
            if not match:
                continue

            parts = []
            first_value = match.group(1).strip()
            if first_value:
                parts.append(first_value)

            for j in range(i + 1, min(i + 1 + max_following_lines, len(lines))):
                next_line = lines[j]
                if is_new_field_line(next_line):
                    break
                parts.append(next_line)

            value = " ".join(parts).strip()
            value = value.rstrip(" .,:;")
            return value or None

    return None

def find_notice_number(text: str) -> str | None:
    flat = normalize_text(text)

    patterns = [
        r"Номер\s+извещения\s*[:\-]?\s*(\d{11,19})",
        r"для\s+закупки\s*№\s*(\d{11,19})",
    ]

    for pattern in patterns:
        match = re.search(pattern, flat, re.IGNORECASE)
        if match:
            return match.group(1)

    return None

def find_object_name(text: str) -> str | None:
    value = find_labeled_value(
        text,
        [
            r"Наименование\s+закупки",
            r"Предмет\s+закупки",
            r"Предмет\s+договора",
            r"Наименование\s+объекта\s+закупки",
        ],
        max_following_lines=2,
    )

    if value:
        cleaned = clean_object_name(value)
        if cleaned:
            return cleaned

    flat = normalize_text(text)

    stop_fields = (
        r"Способ\s+проведения\s+закупки|"
        r"Наименование\s+электронной\s+площадки|"
        r"Заказчик\b|"
        r"Наименование\s+организации\b|"
        r"Организатор\s+закупки\b|"
        r"Дата\s+и\s+время\s+окончания\s+срока\s+подачи\s+заявок\b|"
        r"Дата\s+окончания\s+подачи\s+заявок\b|"
        r"Начальная\s*\(\s*максимальная\s*\)\s*цена|"
        r"НМЦК\b|"
        r"НМЦД\b|"
        r"Место\s+нахождения\b|"
        r"Почтовый\s+адрес\b|"
        r"Требуется\s+обеспечение\b|"
        r"Размер\s+обеспечения\b"
    )

    patterns = [
        rf"Наименование\s+закупки\s*[:\-]?\s*(.+?)(?=\s+(?:{stop_fields})|$)",
        rf"Предмет\s+закупки\s*[:\-]?\s*(.+?)(?=\s+(?:{stop_fields})|$)",
        rf"Предмет\s+договора\s*[:\-]?\s*(.+?)(?=\s+(?:{stop_fields})|$)",
        rf"Наименование\s+объекта\s+закупки\s*[:\-]?\s*(.+?)(?=\s+(?:{stop_fields})|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, flat, re.IGNORECASE | re.DOTALL)
        if match:
            candidate = clean_object_name(match.group(1))
            if candidate:
                return candidate

    return None

def find_customer_name(text: str) -> str | None:
    value = find_labeled_value(
        text,
        [
            r"Наименование\s+организации",
            r"Заказчик",
        ],
        max_following_lines=2,
    )

    if value:
        return value

    flat = normalize_text(text)

    stop_fields = (
        r"Место\s+нахождения\b|"
        r"Почтовый\s+адрес\b|"
        r"Дата\s+и\s+время\s+окончания\s+срока\s+подачи\s+заявок\b|"
        r"Дата\s+окончания\s+подачи\s+заявок\b|"
        r"Начальная\s*\(\s*максимальная\s*\)\s*цена|"
        r"НМЦК\b|"
        r"НМЦД\b|"
        r"Требуется\s+обеспечение\b|"
        r"Размер\s+обеспечения\b|"
        r"Срок\s+поставки\b"
    )

    patterns = [
        rf"Наименование\s+организации\s*[:\-]?\s*(.+?)(?=\s+(?:{stop_fields})|$)",
        rf"Заказчик\s*[:\-]?\s*(.+?)(?=\s+(?:{stop_fields})|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, flat, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            value = value.rstrip(" .,:;")
            return value or None

    return None

def find_price(text: str) -> str | None:
    value = find_labeled_value(
        text,
        [
            r"Начальная\s*\(\s*максимальная\s*\)\s*цена\s+(?:контракта|договора)",
            r"НМЦК",
            r"НМЦД",
        ],
        max_following_lines=1,
    )

    if value:
        match = re.search(r"([\d\s]+(?:[.,]\d{2})?)", value)
        if match:
            return match.group(1).replace(" ", "").replace(",", ".")

    flat = normalize_text(text)

    patterns = [
        r"Начальная\s*\(\s*максимальная\s*\)\s*цена\s+(?:контракта|договора)\s*[:\-]?\s*([\d\s]+(?:[.,]\d{2})?)",
        r"НМЦК\s*[:\-]?\s*([\d\s]+(?:[.,]\d{2})?)",
        r"НМЦД\s*[:\-]?\s*([\d\s]+(?:[.,]\d{2})?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, flat, re.IGNORECASE)
        if match:
            return match.group(1).replace(" ", "").replace(",", ".")

    return None

def find_bid_security(text: str) -> str | None:
    lines = split_meaningful_lines(text)

    labels = [
        r"Обеспечение\s+заявк(?:и|ок)",
        r"Размер\s+обеспечения\s+заявк(?:и|ок)",
        r"Обеспечение\s+заявк(?:и|ок)\s+на\s+участие",
    ]

    for i, line in enumerate(lines):
        if any(re.search(label, line, re.IGNORECASE) for label in labels):
            candidate_lines = [line]
            for j in range(i + 1, min(i + 4, len(lines))):
                if is_new_field_line(lines[j]):
                    break
                candidate_lines.append(lines[j])

            candidate = " ".join(candidate_lines)

            if re.search(r"не\s+требуется|не\s+устанавливается|не\s+предусмотрено", candidate, re.IGNORECASE):
                return "Не требуется"

            if re.search(
                r"требуется|устанавливается|предоставляется|вносится|составляет|размер.*\d|в\s+размере",
                candidate,
                re.IGNORECASE,
            ):
                return "Требуется"

    flat = normalize_text(text)

    if re.search(
        r"обеспечение\s+заявк(?:и|ок).{0,80}(не\s+требуется|не\s+устанавливается|не\s+предусмотрено)",
        flat,
        re.IGNORECASE,
    ):
        return "Не требуется"

    if re.search(
        r"(обеспечение\s+заявк(?:и|ок)|размер\s+обеспечения\s+заявк(?:и|ок)).{0,100}(требуется|устанавливается|предоставляется|вносится|\d)",
        flat,
        re.IGNORECASE,
    ):
        return "Требуется"

    return None

def find_contract_security(text: str) -> str | None:
    lines = split_meaningful_lines(text)

    labels = [
        r"Размер\s+обеспечения\s+исполнения\s+(?:контракта|договора)",
        r"Обеспечение\s+исполнения\s+(?:контракта|договора)",
    ]

    for i, line in enumerate(lines):
        if any(re.search(label, line, re.IGNORECASE) for label in labels):
            candidate_lines = [line]
            for j in range(i + 1, min(i + 4, len(lines))):
                if is_new_field_line(lines[j]):
                    break
                candidate_lines.append(lines[j])

            candidate = " ".join(candidate_lines)

            if re.search(r"не\s+требуется|не\s+устанавливается|не\s+предусмотрено", candidate, re.IGNORECASE):
                return "Не требуется"

            percent_match = re.search(r"(\d+[.,]?\d*)\s*%", candidate)
            if percent_match:
                return f"{percent_match.group(1).replace(',', '.')}%"

            money_match = re.search(r"(\d[\d\s]+(?:[.,]\d{1,2})?)", candidate)
            if money_match:
                return money_match.group(1).replace(" ", "").replace(",", ".")

            if re.search(r"требуется|устанавливается|предоставляется|вносится", candidate, re.IGNORECASE):
                return "Требуется"

    flat = normalize_text(text)

    percent_match = re.search(
        r"(?:обеспечения\s+исполнения\s+(?:контракта|договора)|исполнения\s+(?:контракта|договора)).{0,120}?(\d+[.,]?\d*)\s*%",
        flat,
        re.IGNORECASE,
    )
    if percent_match:
        return f"{percent_match.group(1).replace(',', '.')}%"

    money_match = re.search(
        r"(?:обеспечения\s+исполнения\s+(?:контракта|договора)|исполнения\s+(?:контракта|договора)).{0,120}?(\d[\d\s]+(?:[.,]\d{1,2})?)",
        flat,
        re.IGNORECASE,
    )
    if money_match:
        return money_match.group(1).replace(" ", "").replace(",", ".")

    if re.search(
        r"обеспечение\s+исполнения\s+(?:контракта|договора).{0,80}(не\s+требуется|не\s+устанавливается|не\s+предусмотрено)",
        flat,
        re.IGNORECASE,
    ):
        return "Не требуется"

    if re.search(
        r"обеспечение\s+исполнения\s+(?:контракта|договора).{0,80}(требуется|устанавливается|предоставляется|вносится)",
        flat,
        re.IGNORECASE,
    ):
        return "Требуется"

    return None

def find_supply_term(text: str) -> str | None:
    value = find_labeled_value(
        text,
        [
            r"Срок\s+поставки",
            r"Срок\s+исполнения\s+(?:контракта|договора)",
        ],
        max_following_lines=2,
    )

    if value:
        return value

    flat = normalize_text(text)

    stop_fields = (
        r"Требуется\s+гарантия\s+качества\b|"
        r"Размер\s+обеспечения\b|"
        r"Обеспечение\s+исполнени[ея]\b|"
        r"Обеспечение\s+заявк(?:и|ок)\b|"
        r"Дата\s+и\s+время\s+окончания\s+срока\s+подачи\s+заявок\b|"
        r"Дата\s+окончания\s+подачи\s+заявок\b|"
        r"Начальная\s*\(\s*максимальная\s*\)\s*цена\b|"
        r"НМЦК\b|"
        r"НМЦД\b|"
        r"РАЗДЕЛ\s+\d+\b|"
        r"$"
    )

    patterns = [
        rf"Срок\s+поставки\s*[:\-]?\s*(.+?)(?=\s+(?:{stop_fields}))",
        rf"Срок\s+исполнения\s+(?:контракта|договора)\s*[:\-]?\s*(.+?)(?=\s+(?:{stop_fields}))",
        r"(в\s+течение\s+\d+\s+календарных\s+дней\s+с\s+даты\s+заключения\s+(?:договора|контракта))",
    ]

    for pattern in patterns:
        match = re.search(pattern, flat, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            value = value.rstrip(" .,:;")
            return value or None

    return None

def find_deadline(text: str) -> str | None:
    lines = split_meaningful_lines(text)

    deadline_labels = [
        r"Дата\s+и\s+время\s+окончания\s+срока\s+подачи\s+заявок",
        r"Дата\s+и\s+время\s+окончания\s+подачи\s+заявок",
        r"Дата\s+окончания\s+подачи\s+заявок",
        r"Окончание\s+срока\s+подачи\s+заявок",
        r"Срок\s+окончания\s+подачи\s+заявок",
        r"Окончание\s+приема\s+заявок",
        r"Дата\s+окончания\s+приема\s+заявок",
    ]

    date_patterns = [
        r"\d{1,2}\.\d{1,2}\.\d{4}\s*г?\.?\s*\d{1,2}:\d{2}",
        r"[«\"]?\d{1,2}[»\"]?\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\s*г?\.?\s*(?:в)?\s*\d{1,2}\s*ч\.?\s*\d{1,2}\s*мин\.?(?:\s*\([^)]*\))?",
        r"\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\s*г?\.?,?\s*\d{1,2}:\d{2}(?:\s*\([^)]*\))?",
    ]

    for i, line in enumerate(lines):
        if any(re.search(label, line, re.IGNORECASE) for label in deadline_labels):
            candidate_lines = [line]
            for j in range(i + 1, min(i + 3, len(lines))):
                if is_new_field_line(lines[j]):
                    break
                candidate_lines.append(lines[j])

            candidate = " ".join(candidate_lines)

            for pattern in date_patterns:
                match = re.search(pattern, candidate, re.IGNORECASE)
                if match:
                    return match.group(0).strip()

    flat = normalize_text(text)

    for pattern in date_patterns:
        match = re.search(pattern, flat, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return None

def detect_license_requirement(text: str) -> bool:
    lines = split_meaningful_lines(text)

    requirement_context = [
        r"участник",
        r"требования\s+к\s+участник",
        r"соответстви[ея]\s+участника",
        r"должен",
        r"обязан",
        r"необходимо",
        r"наличие",
        r"подтвержда",
    ]

    license_words = [
        r"\bлиценз\w*",
        r"\bдопуск\b",
        r"\bдопуск\s+сро\b",
        r"\bсро\b",
        r"\bразрешени[ея]\s+на\b",
        r"\bразрешительный\s+документ\b",
    ]

    negative_context = [
        r"разрешение\s+споров",
        r"разрешение\s+разноглас",
        r"аккредитованн\w*\s+лаборатор",
        r"сертификат\s+соответствия",
        r"паспорт\s+качества",
        r"поставщик\s+гарантирует",
    ]

    for i, line in enumerate(lines):
        window = " ".join(lines[max(0, i - 1): min(len(lines), i + 2)])

        if any(re.search(p, window, re.IGNORECASE) for p in negative_context):
            continue

        has_context = any(re.search(p, window, re.IGNORECASE) for p in requirement_context)
        has_license = any(re.search(p, window, re.IGNORECASE) for p in license_words)

        if has_context and has_license:
            return True

    return False

def detect_experience_requirement(text: str) -> bool:
    lines = split_meaningful_lines(text)

    experience_patterns = [
        r"опыт\s+исполнения",
        r"опыт\s+поставки",
        r"опыт\s+оказания\s+услуг",
        r"наличие\s+опыта",
        r"документальн\w*\s+подтвержденн\w*\s+опыт",
        r"опыт\s+успешного\s+исполнения",
        r"исполненн\w*\s+контракт",
        r"исполненн\w*\s+договор",
        r"аналогичн\w*\s+контракт",
        r"аналогичн\w*\s+договор",
        r"подтверждени\w*\s+опыта",
    ]

    context_patterns = [
        r"участник",
        r"требования\s+к\s+участник",
        r"подтвержда",
        r"необходимо",
        r"должен",
        r"обязан",
        r"наличие",
        r"соответстви[ея]\s+участника",
    ]

    for i, line in enumerate(lines):
        window = " ".join(lines[max(0, i - 1): min(len(lines), i + 2)])

        has_exp = any(re.search(pattern, window, re.IGNORECASE) for pattern in experience_patterns)
        has_ctx = any(re.search(pattern, window, re.IGNORECASE) for pattern in context_patterns)

        if has_exp and has_ctx:
            return True

    joined = " ".join(lines)
    return any(re.search(pattern, joined, re.IGNORECASE) for pattern in experience_patterns)

def find_quality_guarantee(text: str) -> str | None:
    lines = split_meaningful_lines(text)
    joined = " ".join(lines)

    negative_patterns = [
        r"гарантия\s+качества.{0,40}(не\s+требуется|не\s+предусмотрена)",
        r"гарантийный\s+срок.{0,40}(не\s+устанавливается|не\s+предусмотрен)",
    ]

    positive_patterns = [
        r"требуется\s+гарантия\s+качества",
        r"гарантия\s+качества\s+товара",
        r"гарантийн(?:ый|ого)\s+срок",
        r"гарантийн(?:ые|ых)\s+обязательств",
        r"поставщик\s+гарантирует\s+качество",
        r"гарантия\s+предоставляется",
    ]

    for pattern in negative_patterns:
        if re.search(pattern, joined, re.IGNORECASE):
            return "Нет"

    for pattern in positive_patterns:
        if re.search(pattern, joined, re.IGNORECASE):
            return "Да"

    return None

def extract_with_priority(
    documents: list[TenderDocument],
    extractor,
    preferred_types: tuple[DocumentType, ...] = (
        DocumentType.notice,
        DocumentType.contract,
        DocumentType.spec,
        DocumentType.other,
    ),
):
    for doc_type in preferred_types:
        for doc in documents:
            if doc.doc_type == doc_type:
                value = extractor(doc.extracted_text or "")
                if value:
                    return value

    combined_text = combine_documents_text(documents)
    return extractor(combined_text)

def make_snippet_from_value(text: str, value: str | None, radius: int = 120) -> str | None:
    if not text or not value:
        return None

    normalized_text = normalize_text(text)
    normalized_value = normalize_text(value)

    idx = normalized_text.lower().find(normalized_value.lower())
    match_len = len(normalized_value)

    if idx == -1:
        first_token = normalized_value.split()[0] if normalized_value.split() else normalized_value
        idx = normalized_text.lower().find(first_token.lower())
        match_len = len(first_token) if first_token else 0

    if idx == -1:
        return None

    start = max(0, idx - radius)
    end = min(len(normalized_text), idx + match_len + radius)
    return normalized_text[start:end].strip()


def extract_with_priority_debug(
    documents: list[TenderDocument],
    field_name: str,
    extractor,
    extractor_name: str,
    preferred_types: tuple[DocumentType, ...] = (
        DocumentType.notice,
        DocumentType.contract,
        DocumentType.spec,
        DocumentType.other,
    ),
) -> tuple[str | None, ExtractionEvidence | None]:
    for doc_type in preferred_types:
        for doc in documents:
            if doc.doc_type == doc_type:
                value = extractor(doc.extracted_text or "")
                if value:
                    evidence = ExtractionEvidence(
                        field_name=field_name,
                        value=str(value),
                        source_document=doc.filename,
                        source_doc_type=doc.doc_type,
                        extractor=extractor_name,
                        snippet=make_snippet_from_value(doc.extracted_text or "", str(value)),
                        confidence=0.9 if doc.doc_type in (DocumentType.notice, DocumentType.contract, DocumentType.spec) else 0.75,
                    )
                    return value, evidence

    combined_text = combine_documents_text(documents)
    value = extractor(combined_text)

    if value:
        evidence = ExtractionEvidence(
            field_name=field_name,
            value=str(value),
            source_document="__combined__",
            source_doc_type=None,
            extractor=extractor_name,
            snippet=make_snippet_from_value(combined_text, str(value)),
            confidence=0.6,
        )
        return value, evidence

    return None, None