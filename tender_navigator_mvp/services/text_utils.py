import re
from typing import List


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("«", '"').replace("»", '"')
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_line(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("«", '"').replace("»", '"')
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_meaningful_lines(text: str) -> List[str]:
    if not text:
        return []

    text = text.replace("\r", "\n")
    raw_lines = re.split(r"\n+", text)

    lines: List[str] = []
    for line in raw_lines:
        cleaned = normalize_line(line)
        if cleaned:
            lines.append(cleaned)

    return lines


def clean_object_name(value: str) -> str | None:
    if not value:
        return None

    value = normalize_text(value)

    stop_markers = [
        "СОДЕРЖАНИЕ",
        "РАЗДЕЛ 1",
        "Подраздел 1.1",
        "Заказчик",
        "Наименование организации",
        "Организатор закупки",
        "Состав, объем, срок",
        "Краткое описание предмета закупки",
        "Способ проведения закупки",
        "Наименование электронной площадки",
        "Дата и время окончания срока подачи заявок",
        "Дата окончания подачи заявок",
        "Начальная (максимальная) цена",
        "НМЦК",
        "НМЦД",
    ]

    for marker in stop_markers:
        idx = value.find(marker)
        if idx != -1:
            value = value[:idx].strip()

    value = value.strip(' ":\n\t')

    if len(value) > 300:
        return None

    bad_tokens = ["СОДЕРЖАНИЕ", "РАЗДЕЛ", "Подраздел"]
    if any(token in value for token in bad_tokens):
        return None

    return value or None