from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.security import (
    hash_password,
    issue_access_token,
    read_access_token,
    verify_password,
)
from backend.app.core.settings import Settings
from backend.app.repositories.storage import StorageRepository


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    organization_id: int
    email: str
    full_name: str | None
    role: str
    is_owner: bool
    organization_name: str
    organization_slug: str


class AuthService:
    def __init__(self, storage: StorageRepository, settings: Settings) -> None:
        self.storage = storage
        self.settings = settings

    def is_setup_required(self) -> bool:
        return not self.storage.has_users()

    def register_owner(
        self,
        *,
        organization_name: str,
        full_name: str,
        email: str,
        password: str,
    ) -> dict:
        password_hash, password_salt = hash_password(password)
        user = self.storage.create_organization_with_owner(
            organization_name=organization_name,
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            password_salt=password_salt,
        )
        return self._build_auth_payload(user)

    def create_invitation(
        self,
        *,
        organization_id: int,
        invited_by_user_id: int,
        email: str,
        role: str,
    ) -> dict:
        return self.storage.create_invitation(
            organization_id=organization_id,
            invited_by_user_id=invited_by_user_id,
            email=email,
            role=role,
        )

    def get_invitation(self, token: str) -> dict | None:
        return self.storage.get_invitation_by_token(token)

    def accept_invitation(
        self,
        *,
        token: str,
        full_name: str,
        password: str,
    ) -> dict:
        password_hash, password_salt = hash_password(password)
        user = self.storage.accept_invitation(
            token=token,
            full_name=full_name,
            password_hash=password_hash,
            password_salt=password_salt,
        )
        return self._build_auth_payload(user)

    def login(self, *, email: str, password: str) -> dict | None:
        user = self.storage.get_user_by_email(email)
        if user is None or not user["is_active"]:
            return None
        if not verify_password(password, user["password_hash"], user["password_salt"]):
            return None
        return self._build_auth_payload(user)

    def get_authenticated_user(self, token: str) -> AuthenticatedUser | None:
        claims = read_access_token(token, self.settings.auth_secret_key)
        if claims is None:
            return None

        user = self.storage.get_user_auth_context(claims.user_id)
        if user is None or not user["is_active"]:
            return None
        if user["organization"]["id"] != claims.organization_id:
            return None

        return AuthenticatedUser(
            user_id=user["id"],
            organization_id=user["organization"]["id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_owner=user["is_owner"],
            organization_name=user["organization"]["name"],
            organization_slug=user["organization"]["slug"],
        )

    def get_user_payload(self, user_id: int) -> dict | None:
        return self.storage.get_user_auth_context(user_id)

    def _build_auth_payload(self, user: dict) -> dict:
        access_token = issue_access_token(
            user_id=user["id"],
            organization_id=user["organization"]["id"],
            secret_key=self.settings.auth_secret_key,
            ttl_minutes=self.settings.auth_access_token_ttl_minutes,
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        }
