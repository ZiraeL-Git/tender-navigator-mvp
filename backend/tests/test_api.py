from __future__ import annotations

from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.repositories.storage import StorageRepository


def build_docx_bytes(text: str) -> bytes:
    document = Document()
    for line in text.strip().splitlines():
        cleaned = line.strip()
        if cleaned:
            document.add_paragraph(cleaned)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def create_company_profile(client: TestClient) -> int:
    response = client.post(
        "/api/v1/company-profiles",
        json={
            "company_name": "ООО Навигатор",
            "inn": "5400000000",
            "region": "Новосибирская область",
            "categories": ["канцелярия"],
            "has_license": True,
            "has_experience": True,
            "can_prepare_fast": True,
            "notes": "Тестовый профиль",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_healthcheck():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_for_frontend_origin():
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/company-profiles",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_company_profiles_and_manual_upload_analysis_flow():
    with TestClient(app) as client:
        profile_id = create_company_profile(client)

        file_bytes = build_docx_bytes(
            """
            Номер извещения: 0123500000126001234
            Наименование закупки: Поставка канцелярских товаров
            Наименование организации: Муниципальное бюджетное учреждение "Школа №1"
            Дата и время окончания срока подачи заявок: 15.04.2026 10:00
            Начальная (максимальная) цена контракта: 450 000,00
            """
        )

        analysis_response = client.post(
            f"/api/v1/analyses/from-files?company_profile_id={profile_id}",
            files={
                "files": (
                    "notice.docx",
                    file_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        assert analysis_response.status_code == 201
        analysis_payload = analysis_response.json()
        assert analysis_payload["decision_code"] == "go"
        assert analysis_payload["status"] == "analyzed"
        assert analysis_payload["tender_input_id"] is not None
        assert analysis_payload["extracted"]["notice_number"] == "0123500000126001234"

        list_response = client.get("/api/v1/analyses")
        assert list_response.status_code == 200
        assert len(list_response.json()) >= 1

        detail_response = client.get(f"/api/v1/analyses/{analysis_payload['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == analysis_payload["id"]
        assert len(detail_response.json()["events"]) >= 3

        repository = StorageRepository(client.app.state.session_factory)
        assert repository.count_analysis_events(analysis_payload["id"]) >= 3


def test_import_tender_input_and_queue_analysis():
    with TestClient(app) as client:
        profile_id = create_company_profile(client)

        import_response = client.post(
            "/api/v1/tender-inputs/import",
            json={
                "company_profile_id": profile_id,
                "notice_number": "0123500000126005678",
                "title": "Поставка офисной бумаги",
                "customer_name": "Муниципальное бюджетное учреждение Центр развития",
                "deadline": "20.04.2026 09:00",
                "max_price": "125000.00",
                "auto_analyze": True,
            },
        )

        assert import_response.status_code == 201
        tender_input = import_response.json()
        assert tender_input["notice_number"] == "0123500000126005678"
        assert tender_input["latest_analysis_id"] is not None
        assert len(tender_input["documents"]) == 1

        tender_inputs_response = client.get("/api/v1/tender-inputs")
        assert tender_inputs_response.status_code == 200
        assert len(tender_inputs_response.json()) >= 1

        tender_input_detail = client.get(f"/api/v1/tender-inputs/{tender_input['id']}")
        assert tender_input_detail.status_code == 200
        assert tender_input_detail.json()["id"] == tender_input["id"]

        analysis_id = tender_input["latest_analysis_id"]
        analysis_detail = client.get(f"/api/v1/analyses/{analysis_id}")
        assert analysis_detail.status_code == 200
        analysis_payload = analysis_detail.json()
        assert analysis_payload["status"] == "analyzed"
        assert analysis_payload["tender_input_id"] == tender_input["id"]
        assert any(event["event_type"] == "analysis_completed" for event in analysis_payload["events"])
