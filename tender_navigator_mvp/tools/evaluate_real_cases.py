import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import os

import re
from decimal import Decimal, InvalidOperation

from schemas import CompanyProfile, TenderDocument, DocumentType
from services.analysis import analyze_tender_package
from services.document_io import detect_document_type, extract_text_from_docx, extract_text_from_pdf

def canon_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.replace("«", '"').replace("»", '"')
    value = value.replace("\xa0", " ").replace("\u202f", " ")
    value = value.replace("—", "-").replace("–", "-")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r'"\s+', '"', value)
    value = re.sub(r"\s+\"", '"', value)
    value = re.sub(r"№\s+", "№", value)
    value = value.strip(" .,:;\n\t")
    return value


def canon_compact_text(value: str | None) -> str | None:
    value = canon_text(value)
    if value is None:
        return None

    value = value.lower()
    value = value.replace('"', "")
    value = value.replace("№", "")
    value = value.replace("-", "")
    value = re.sub(r"\s+", "", value)
    return value

def find_snippets(text: str, patterns: list[str], window: int = 180) -> list[str]:
    import re

    if not text:
        return []

    snippets = []
    seen = set()

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            snippet = text[start:end].replace("\n", " ").strip()
            snippet = re.sub(r"\s+", " ", snippet)

            if snippet not in seen:
                seen.add(snippet)
                snippets.append(snippet)

            if len(snippets) >= 3:
                return snippets

    return snippets


def print_debug_snippets(case_name: str, documents, result):
    debug_map = {
        "bid_security": [
            r"обеспечени[ея]\s+заявк",
            r"размер\s+обеспечени[ея]\s+заявк",
        ],
        "contract_security": [
            r"обеспечени[ея]\s+исполнени[ея]\s+(контракта|договора)",
            r"размер\s+обеспечени[ея]\s+исполнени[ея]\s+(контракта|договора)",
        ],
        "quality_guarantee": [
            r"гаранти[яй]\s+качества",
            r"гарантийн\w+\s+срок",
            r"поставщик\s+гарантирует",
        ],
        "need_experience": [
            r"опыт\s+исполнения",
            r"опыт\s+поставки",
            r"аналогичн\w+\s+(договор|контракт)",
            r"подтверждени\w+\s+опыта",
        ],
        "need_license": [
            r"лиценз",
            r"допуск",
            r"\bсро\b",
            r"разрешени",
        ],
    }

    fields_to_debug = []
    if result.extracted.bid_security in [None, "Не требуется"]:
        fields_to_debug.append("bid_security")
    if result.extracted.contract_security in [None, "Не требуется"]:
        fields_to_debug.append("contract_security")
    if result.extracted.quality_guarantee is None:
        fields_to_debug.append("quality_guarantee")
    if result.extracted.need_experience is False:
        fields_to_debug.append("need_experience")
    if result.extracted.need_license is True:
        fields_to_debug.append("need_license")

    if not fields_to_debug:
        return

    print(f"\n--- DEBUG SNIPPETS: {case_name} ---")
    for field_name in fields_to_debug:
        print(f"\n[{field_name}]")
        patterns = debug_map[field_name]
        found_any = False

        for doc in documents:
            snippets = find_snippets(doc.extracted_text or "", patterns)
            if snippets:
                found_any = True
                print(f"  Документ: {doc.filename}")
                for idx, snippet in enumerate(snippets, start=1):
                    print(f"    {idx}) {snippet}")

        if not found_any:
            print("  Совпадений по ключевым словам не найдено")

def canon_money(value: str | None) -> str | None:
    if value is None:
        return None

    raw = value.replace(" ", "").replace(",", ".")
    raw = re.sub(r"[^\d.]", "", raw)

    if not raw:
        return None

    try:
        return str(Decimal(raw).quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError):
        return raw


def canon_deadline(value: str | None) -> str | None:
    if value is None:
        return None

    value = canon_text(value)
    value = value.replace("г. ", " ").replace("г.", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def values_equivalent(field_name: str, actual, expected) -> bool:
    if field_name in {"object_name", "customer_name"}:
        return canon_compact_text(actual) == canon_compact_text(expected)

    if field_name in {"notice_number", "supply_term"}:
        return canon_text(actual) == canon_text(expected)

    if field_name in {"price", "contract_security"}:
        a = canon_money(actual)
        e = canon_money(expected)

        if a is not None and e is not None:
            return a == e

        return canon_text(actual) == canon_text(expected)

    if field_name == "deadline":
        return canon_deadline(actual) == canon_deadline(expected)

    return actual == expected

def load_documents_from_case(case_dir: Path) -> list[TenderDocument]:
    documents = []

    for path in case_dir.iterdir():
        if path.name == "expected.json":
            continue

        if path.suffix.lower() == ".pdf":
            with open(path, "rb") as f:
                text = extract_text_from_pdf(f)
        elif path.suffix.lower() == ".docx":
            with open(path, "rb") as f:
                text = extract_text_from_docx(f)
        else:
            continue

        doc_type = detect_document_type(path.name, text)

        documents.append(
            TenderDocument(
                filename=path.name,
                doc_type=doc_type,
                extracted_text=text,
                text_length=len(text),
            )
        )

    return documents


def make_default_profile() -> CompanyProfile:
    return CompanyProfile(
        company_name="ООО Тест",
        inn="7000000000",
        region="Томская область",
        categories=["товары", "канцелярия"],
        has_license=True,
        has_experience=True,
        can_prepare_fast=True,
        notes="",
    )


def compare_field(field_name: str, actual, expected):
    ok = values_equivalent(field_name, actual, expected)
    return {
        "field": field_name,
        "actual": actual,
        "expected": expected,
        "ok": ok,
    }


def main():
    root = Path("real_cases")
    if not root.exists():
        print("Папка real_cases не найдена")
        return

    total = 0
    passed = 0

    for case_dir in sorted(root.iterdir()):
        if not case_dir.is_dir():
            continue

        expected_path = case_dir / "expected.json"
        if not expected_path.exists():
            print(f"[SKIP] {case_dir.name}: нет expected.json")
            continue

        with open(expected_path, "r", encoding="utf-8") as f:
            expected = json.load(f)

        documents = load_documents_from_case(case_dir)
        profile = make_default_profile()
        result = analyze_tender_package(documents, profile)

        actual_fields = {
            "notice_number": result.extracted.notice_number,
            "object_name": result.extracted.object_name,
            "customer_name": result.extracted.customer_name,
            "price": result.extracted.price,
            "deadline": result.extracted.deadline,
            "supply_term": result.extracted.supply_term,
            "bid_security": result.extracted.bid_security,
            "contract_security": result.extracted.contract_security,
            "quality_guarantee": result.extracted.quality_guarantee,
            "need_license": result.extracted.need_license,
            "need_experience": result.extracted.need_experience,
        }

        print(f"\n=== CASE: {case_dir.name} ===")
        for field_name, expected_value in expected.items():
            cmp = compare_field(field_name, actual_fields.get(field_name), expected_value)
            total += 1
            if cmp["ok"]:
                passed += 1
                print(f"[OK]   {field_name}: {cmp['actual']}")
            else:
                print(f"[FAIL] {field_name}")
                print(f"       expected: {cmp['expected']}")
                print(f"       actual:   {cmp['actual']}")
        print_debug_snippets(case_dir.name, documents, result)
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f" - {warning}")

    print("\n==============================")
    print(f"FIELD ACCURACY: {passed}/{total} = {round((passed / total) * 100, 2) if total else 0}%")
    print("==============================")


if __name__ == "__main__":
    main()