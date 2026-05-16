"""Security tests: login, JWT validation, role guards, expiry.

These tests use a TestClient that hits a real (temp) SQLite DB via the
existing conftest fixtures.  Auth logic is exercised independently of data
by targeting non-existent IDs — 401/403 is returned before the DB is touched.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from prompt_vault.app.config import Settings
from prompt_vault.app.database import get_session
from prompt_vault.app.main import app
from prompt_vault.app.security import create_access_token


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(name="auth_client")
def auth_client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def _override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _token(client: TestClient, username: str = "admin", password: str = "vault-admin") -> str:
    resp = client.post("/token", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── login endpoint ────────────────────────────────────────────────────────────


def test_login_admin_returns_token(auth_client: TestClient):
    token = _token(auth_client)
    assert token and len(token) > 10


def test_login_student_returns_token(auth_client: TestClient):
    token = _token(auth_client, "student", "vault-student")
    assert token


def test_login_wrong_password_returns_401(auth_client: TestClient):
    resp = auth_client.post("/token", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user_returns_401(auth_client: TestClient):
    resp = auth_client.post("/token", data={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


# ── protected routes require a token ─────────────────────────────────────────


def test_delete_without_token_returns_401(auth_client: TestClient):
    assert auth_client.delete("/prompts/1").status_code == 401


def test_patch_without_token_returns_401(auth_client: TestClient):
    assert auth_client.patch("/prompts/1", json={"effectiveness": 5}).status_code == 401


def test_refresh_without_token_returns_401(auth_client: TestClient):
    assert auth_client.post("/prompts/1/refresh").status_code == 401


# ── role checks ───────────────────────────────────────────────────────────────


def test_student_cannot_delete_returns_403(auth_client: TestClient):
    token = _token(auth_client, "student", "vault-student")
    resp = auth_client.delete("/prompts/1", headers=_bearer(token))
    assert resp.status_code == 403


def test_student_cannot_patch_returns_403(auth_client: TestClient):
    token = _token(auth_client, "student", "vault-student")
    resp = auth_client.patch("/prompts/1", json={"effectiveness": 5}, headers=_bearer(token))
    assert resp.status_code == 403


def test_editor_auth_passes_to_route(auth_client: TestClient):
    token = _token(auth_client)
    # Auth passes (200-level not guaranteed since prompt 9999 won't exist → 404)
    resp = auth_client.delete("/prompts/9999", headers=_bearer(token))
    assert resp.status_code == 404  # auth ok, prompt not found


# ── token expiry ──────────────────────────────────────────────────────────────


def test_expired_token_returns_401(auth_client: TestClient):
    settings = Settings()
    expired = create_access_token(
        subject="admin",
        roles=["editor"],
        settings=settings,
        expires_delta=timedelta(seconds=-1),
    )
    resp = auth_client.delete("/prompts/1", headers=_bearer(expired))
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_missing_role_in_custom_token_returns_403(auth_client: TestClient):
    settings = Settings()
    read_only = create_access_token(
        subject="viewer",
        roles=["student"],
        settings=settings,
    )
    resp = auth_client.delete("/prompts/1", headers=_bearer(read_only))
    assert resp.status_code == 403
