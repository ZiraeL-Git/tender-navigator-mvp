from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


PBKDF2_ITERATIONS = 240_000


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    organization_id: int
    expires_at: datetime


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return _b64encode(password_hash), _b64encode(salt)


def verify_password(password: str, password_hash: str, password_salt: str) -> bool:
    expected_hash = _b64decode(password_hash)
    salt = _b64decode(password_salt)
    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return hmac.compare_digest(candidate_hash, expected_hash)


def issue_access_token(
    *,
    user_id: int,
    organization_id: int,
    secret_key: str,
    ttl_minutes: int,
) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
    payload = {
        "sub": user_id,
        "org": organization_id,
        "exp": int(expires_at.timestamp()),
        "typ": "access",
    }
    encoded_payload = _b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(secret_key.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_b64encode(signature)}"


def read_access_token(token: str, secret_key: str) -> TokenClaims | None:
    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
    except ValueError:
        return None

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(_b64encode(expected_signature), encoded_signature):
        return None

    try:
        payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
        if payload.get("typ") != "access":
            return None
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
        if expires_at <= datetime.now(UTC):
            return None
        return TokenClaims(
            user_id=int(payload["sub"]),
            organization_id=int(payload["org"]),
            expires_at=expires_at,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")
