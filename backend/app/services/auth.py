"""
Authentication — spec §7/§41.

DEMO_MODE: a small, real (not fake) email/password + signed-session-token
implementation backed by SQLiteStore, using only the standard library
(pbkdf2_hmac for password hashing, hmac+base64 for the session token).
This is what actually runs when you `docker run` this repo with no
external accounts — it is not a stub that always succeeds.

Real mode: verifies a Supabase-issued JWT using the project's JWT secret.
This path is written against Supabase's documented JWT shape but — like
the other real-mode adapters — has not been exercised against a live
Supabase project from this sandbox.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Header, HTTPException

from app.config import Settings, get_settings
from app.persistence.client import get_store

TOKEN_TTL_SECONDS = 24 * 3600
_DEMO_SECRET = os.environ.get("SYNTHETIX_DEMO_SECRET", "dev-insecure-secret-change-me")


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or base64.urlsafe_b64encode(os.urandom(16)).decode()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return base64.urlsafe_b64encode(digest).decode(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)


def create_demo_token(user_id: str, email: str) -> str:
    payload = json.dumps({"sub": user_id, "email": email, "exp": time.time() + TOKEN_TTL_SECONDS}).encode()
    sig = hmac.new(_DEMO_SECRET.encode(), payload, hashlib.sha256).digest()
    return f"{_b64(payload)}.{_b64(sig)}"


def verify_demo_token(token: str) -> dict:
    try:
        payload_b64, sig_b64 = token.split(".")
        payload = _unb64(payload_b64)
        sig = _unb64(sig_b64)
        expected = hmac.new(_DEMO_SECRET.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        data = json.loads(payload)
        if data["exp"] < time.time():
            raise ValueError("expired")
        return data
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid or expired session token") from exc


def _verify_real_jwt(token: str, settings: Settings) -> dict:
    import jwt  # PyJWT — pulled in transitively by supabase-py in requirements-real.txt

    try:
        return jwt.decode(token, settings.supabase_service_role_key, algorithms=["HS256"], options={"verify_aud": False})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid or expired session token") from exc


class CurrentUser:
    def __init__(self, user_id: str, email: str):
        self.user_id = user_id
        self.email = email


def get_current_user(authorization: str = Header(default="")) -> CurrentUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()

    settings = get_settings()
    if settings.persistence_mode == "real":
        data = _verify_real_jwt(token, settings)
        return CurrentUser(user_id=data["sub"], email=data.get("email", ""))

    data = verify_demo_token(token)
    return CurrentUser(user_id=data["sub"], email=data["email"])


def require_org_member(org_id: str, user: CurrentUser) -> None:
    store = get_store()
    if not store.is_org_member(org_id, user.user_id):
        raise HTTPException(status_code=403, detail="Not a member of this organization")
