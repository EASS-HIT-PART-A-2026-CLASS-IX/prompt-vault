"""Async tests for the prompt-refresh endpoint and the PromptRefresher class.

Uses httpx.ASGITransport so tests hit FastAPI directly without a network
socket, and fakeredis for realistic idempotency-key behaviour.
"""
from __future__ import annotations

from unittest.mock import patch

import fakeredis
import httpx
import pytest
from sqlmodel import Session

from prompt_vault.app.database import get_session
from prompt_vault.app.main import app as fastapi_app
from scripts.refresh import PromptRefresher, RefreshJob

_SAMPLE = {
    "title": "Async refresh test prompt",
    "text": "Explain the concept of idempotency using a real-world analogy that a junior engineer would understand.",
    "model": "claude-sonnet-4-6",
    "category": "learning",
    "task_type": "explain concept",
    "effectiveness": 4,
    "tags": "async,idempotency",
}


# ── helpers ──────────────────────────────────────────────────────────────────


def _asgi_client(session: Session) -> httpx.AsyncClient:
    """Return an AsyncClient backed by ASGITransport with the test DB session."""

    def _override():
        yield session

    fastapi_app.dependency_overrides[get_session] = _override
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://testserver",
    )


# ── endpoint tests ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_refresh_endpoint_via_asgi(session: Session):
    """Hitting /prompts/{id}/refresh via ASGI transport returns a token estimate."""
    async with _asgi_client(session) as client:
        create = await client.post("/prompts", json=_SAMPLE)
        assert create.status_code == 201
        prompt_id = create.json()["id"]

        resp = await client.post(
            f"/prompts/{prompt_id}/refresh",
            headers={"X-Trace-Id": "test-trace-001", "Idempotency-Key": f"test:refresh:{prompt_id}"},
        )

    fastapi_app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["already_refreshed"] is False
    assert data["token_count"] >= 1
    assert data["prompt_id"] == prompt_id


@pytest.mark.anyio
async def test_refresh_idempotency_with_fakeredis(session: Session):
    """Second request with the same Idempotency-Key returns already_refreshed=True."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    headers = {"X-Trace-Id": "test-trace-002", "Idempotency-Key": "test:idem:fixed-key"}

    async with _asgi_client(session) as client:
        create = await client.post("/prompts", json=_SAMPLE)
        prompt_id = create.json()["id"]

        with patch("prompt_vault.app.main.get_redis", return_value=fake_redis):
            first = await client.post(f"/prompts/{prompt_id}/refresh", headers=headers)
            second = await client.post(f"/prompts/{prompt_id}/refresh", headers=headers)

    fastapi_app.dependency_overrides.clear()

    assert first.json()["already_refreshed"] is False
    assert second.json()["already_refreshed"] is True


@pytest.mark.anyio
async def test_refresh_missing_prompt_returns_404(session: Session):
    async with _asgi_client(session) as client:
        resp = await client.post("/prompts/9999/refresh")

    fastapi_app.dependency_overrides.clear()
    assert resp.status_code == 404


# ── PromptRefresher unit tests ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_refresher_calls_endpoint_for_each_job(session: Session):
    """PromptRefresher sends one POST per job and reports counts correctly."""
    async with _asgi_client(session) as client:
        ids = []
        for i in range(3):
            r = await client.post("/prompts", json={**_SAMPLE, "title": f"Prompt {i}"})
            ids.append(r.json()["id"])

        # concurrency=1 keeps requests serial so the shared test session stays consistent
        refresher = PromptRefresher(client, trace_id="test-trace-003", concurrency=1)
        jobs = [RefreshJob(pid, f"Prompt {i}") for i, pid in enumerate(ids)]
        counts = await refresher.refresh_all(jobs)

    fastapi_app.dependency_overrides.clear()

    assert counts["ok"] == 3
    assert counts["failed"] == 0
