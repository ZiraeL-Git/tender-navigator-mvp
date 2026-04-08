from __future__ import annotations

from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient

from backend.app.db.models import (
    AnalysisEvent,
    AnalysisResult,
    AuditLog,
    CompanyProfile,
    Organization,
    OrganizationInvitation,
    TenderAnalysis,
    TenderDocument,
    TenderInput,
    User,
)
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


def reset_database(client: TestClient) -> None:
    session_factory = client.app.state.session_factory
    with session_factory() as session:
        for model in (
            AnalysisEvent,
            AnalysisResult,
            TenderDocument,
            TenderAnalysis,
            TenderInput,
            CompanyProfile,
            AuditLog,
            OrganizationInvitation,
            User,
            Organization,
        ):
            session.query(model).delete()
        session.commit()


def register_and_get_headers(
    client: TestClient,
    *,
    organization_name: str = "ООО Навигатор",
    full_name: str = "Оператор отдела закупок",
    email: str = "owner@example.com",
    password: str = "TenderNavigator123",
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": organization_name,
            "full_name": full_name,
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_company_profile(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/company-profiles",
        headers=headers,
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
        reset_database(client)
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_for_frontend_origin():
    with TestClient(app) as client:
        reset_database(client)
        response = client.options(
            "/api/v1/company-profiles",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_auth_register_login_and_me():
    with TestClient(app) as client:
        reset_database(client)

        bootstrap = client.get("/api/v1/auth/bootstrap")
        assert bootstrap.status_code == 200
        assert bootstrap.json() == {"setup_required": True}

        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "ООО Север",
                "full_name": "Анна Смирнова",
                "email": "anna@example.com",
                "password": "TenderNavigator123",
            },
        )
        assert register_response.status_code == 201
        register_payload = register_response.json()
        assert register_payload["user"]["organization"]["name"] == "ООО Север"
        assert register_payload["user"]["is_owner"] is True

        bootstrap_after = client.get("/api/v1/auth/bootstrap")
        assert bootstrap_after.status_code == 200
        assert bootstrap_after.json() == {"setup_required": False}

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "anna@example.com",
                "password": "TenderNavigator123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "anna@example.com"
        assert me_response.json()["organization"]["slug"] == "organization"


def test_company_profiles_and_manual_upload_analysis_flow():
    with TestClient(app) as client:
        reset_database(client)
        headers = register_and_get_headers(client)
        profile_id = create_company_profile(client, headers)

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
            headers=headers,
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

        list_response = client.get("/api/v1/analyses", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        detail_response = client.get(f"/api/v1/analyses/{analysis_payload['id']}", headers=headers)
        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == analysis_payload["id"]
        assert len(detail_response.json()["events"]) >= 3

        repository = StorageRepository(client.app.state.session_factory)
        assert repository.count_analysis_events(analysis_payload["id"]) >= 3


def test_import_tender_input_and_queue_analysis():
    with TestClient(app) as client:
        reset_database(client)
        headers = register_and_get_headers(client)
        profile_id = create_company_profile(client, headers)

        import_response = client.post(
            "/api/v1/tender-inputs/import",
            headers=headers,
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

        tender_inputs_response = client.get("/api/v1/tender-inputs", headers=headers)
        assert tender_inputs_response.status_code == 200
        assert len(tender_inputs_response.json()) == 1

        tender_input_detail = client.get(f"/api/v1/tender-inputs/{tender_input['id']}", headers=headers)
        assert tender_input_detail.status_code == 200
        assert tender_input_detail.json()["id"] == tender_input["id"]

        analysis_id = tender_input["latest_analysis_id"]
        analysis_detail = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers)
        assert analysis_detail.status_code == 200
        analysis_payload = analysis_detail.json()
        assert analysis_payload["status"] == "analyzed"
        assert analysis_payload["tender_input_id"] == tender_input["id"]
        assert any(event["event_type"] == "analysis_completed" for event in analysis_payload["events"])


def test_organization_isolation_for_company_profiles():
    with TestClient(app) as client:
        reset_database(client)
        headers_first = register_and_get_headers(
            client,
            organization_name="ООО Первый контур",
            email="first@example.com",
        )
        headers_second = register_and_get_headers(
            client,
            organization_name="ООО Второй контур",
            email="second@example.com",
        )

        profile_id = create_company_profile(client, headers_first)

        first_list = client.get("/api/v1/company-profiles", headers=headers_first)
        second_list = client.get("/api/v1/company-profiles", headers=headers_second)
        second_detail = client.get(f"/api/v1/company-profiles/{profile_id}", headers=headers_second)

        assert first_list.status_code == 200
        assert len(first_list.json()) == 1
        assert second_list.status_code == 200
        assert second_list.json() == []
        assert second_detail.status_code == 404


def test_owner_can_invite_user_and_accept_invitation():
    with TestClient(app) as client:
        reset_database(client)
        owner_headers = register_and_get_headers(
            client,
            organization_name="ООО Команда",
            email="owner@team.local",
        )

        invitation_response = client.post(
            "/api/v1/organization/invitations",
            headers=owner_headers,
            json={
                "email": "operator@team.local",
                "role": "operator",
            },
        )
        assert invitation_response.status_code == 201
        invitation = invitation_response.json()
        assert invitation["status"] == "pending"
        assert invitation["role"] == "operator"

        public_invitation = client.get(f"/api/v1/auth/invitations/{invitation['token']}")
        assert public_invitation.status_code == 200
        assert public_invitation.json()["email"] == "operator@team.local"

        accept_response = client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "token": invitation["token"],
                "full_name": "Новый оператор",
                "password": "TenderNavigator123",
            },
        )
        assert accept_response.status_code == 200
        accepted_session = accept_response.json()
        assert accepted_session["user"]["email"] == "operator@team.local"
        assert accepted_session["user"]["role"] == "operator"

        users_response = client.get("/api/v1/organization/users", headers=owner_headers)
        assert users_response.status_code == 200
        assert len(users_response.json()) == 2
        assert {user["email"] for user in users_response.json()} == {
            "owner@team.local",
            "operator@team.local",
        }


def test_audit_log_collects_key_actions():
    with TestClient(app) as client:
        reset_database(client)
        headers = register_and_get_headers(
            client,
            organization_name="ООО Аудит",
            email="owner@audit.local",
        )
        profile_id = create_company_profile(client, headers)

        client.post(
            "/api/v1/organization/invitations",
            headers=headers,
            json={
                "email": "viewer@audit.local",
                "role": "viewer",
            },
        )

        client.post(
            "/api/v1/tender-inputs/import",
            headers=headers,
            json={
                "company_profile_id": profile_id,
                "notice_number": "0123500000126009900",
                "title": "Поставка бумаги",
                "customer_name": "Тестовый заказчик",
                "deadline": "21.04.2026 09:00",
                "max_price": "99999.00",
                "auto_analyze": False,
            },
        )

        audit_response = client.get("/api/v1/audit-logs", headers=headers)
        assert audit_response.status_code == 200
        actions = [item["action"] for item in audit_response.json()]
        assert "auth.register_owner" in actions
        assert "company_profile.created" in actions
        assert "organization.invitation_created" in actions
        assert "tender_input.imported" in actions
