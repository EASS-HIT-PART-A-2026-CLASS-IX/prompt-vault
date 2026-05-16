"""Tests for the LLM analyzer microservice and the /prompts/{id}/analyze proxy."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from prompt_vault.app.database import get_session
from prompt_vault.app.main import app

_SAMPLE = {
    "title": "Explain async/await",
    "text": "Explain async/await in Python using a simple analogy.",
    "model": "claude-sonnet-4-6",
    "category": "learning",
    "task_type": "explain concept",
    "effectiveness": 3,
    "tags": "python,async",
}

_MOCK_ANALYSIS = {
    "suggested_effectiveness": 4,
    "suggestions": [
        "Add a concrete real-world analogy (e.g. restaurant kitchen).",
        "Specify the target audience experience level.",
        "Include a minimal code example alongside the analogy.",
    ],
    "summary": "Solid starting point; adding an example would push it to a 5.",
}


# ── analyzer microservice unit tests ─────────────────────────────────────────


@pytest.mark.anyio
async def test_analyzer_mock_response_when_no_api_key():
    """analyze_prompt falls back to mock when ANTHROPIC_API_KEY is absent."""
    from analyzer.agent import analyze_prompt
    from analyzer.schemas import AnalyzeRequest

    req = AnalyzeRequest(
        title="Test",
        text="Do something useful.",
        category="coding",
        current_effectiveness=3,
    )
    # Patch the agent to None (simulates missing API key)
    with patch("analyzer.agent._agent", None):
        result = await analyze_prompt(req)

    assert 1 <= result.suggested_effectiveness <= 5
    assert len(result.suggestions) >= 1
    assert result.summary


@pytest.mark.anyio
async def test_analyzer_health_endpoint():
    """Analyzer /health returns ok."""
    import httpx
    from analyzer.main import app as analyzer_app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=analyzer_app),
        base_url="http://testserver",
    ) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_analyzer_analyze_endpoint_returns_schema():
    """POST /analyze returns valid AnalyzeResponse shape using mock agent."""
    import httpx
    from analyzer.main import app as analyzer_app

    payload = {
        "title": "Summarise meeting notes",
        "text": "Summarise the following meeting notes in 3 bullets: {notes}",
        "category": "writing",
        "current_effectiveness": 4,
    }

    with patch("analyzer.agent._agent", None):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=analyzer_app),
            base_url="http://testserver",
        ) as client:
            resp = await client.post("/analyze", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert "suggested_effectiveness" in data
    assert "suggestions" in data
    assert "summary" in data
    assert 1 <= data["suggested_effectiveness"] <= 5


# ── main API proxy endpoint tests ─────────────────────────────────────────────


@pytest.fixture(name="api_client")
def api_client_fixture(session: Session):
    def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_analyze_proxy_calls_analyzer_service(api_client: TestClient):
    """POST /prompts/{id}/analyze proxies to the analyzer and returns suggestions."""
    created = api_client.post("/prompts", json=_SAMPLE).json()
    prompt_id = created["id"]

    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.json.return_value = _MOCK_ANALYSIS
    mock_resp.raise_for_status = MagicMock()

    with patch("prompt_vault.app.main.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        resp = api_client.post(f"/prompts/{prompt_id}/analyze")

    assert resp.status_code == 200
    data = resp.json()
    assert data["prompt_id"] == prompt_id
    assert data["suggested_effectiveness"] == 4
    assert len(data["suggestions"]) == 3


def test_analyze_proxy_returns_404_for_missing_prompt(api_client: TestClient):
    resp = api_client.post("/prompts/9999/analyze")
    assert resp.status_code == 404


def test_analyze_proxy_returns_503_when_analyzer_down(api_client: TestClient):
    import httpx as httpx_lib

    created = api_client.post("/prompts", json=_SAMPLE).json()

    with patch("prompt_vault.app.main.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx_lib.ConnectError("refused")
        )
        resp = api_client.post(f"/prompts/{created['id']}/analyze")

    assert resp.status_code == 503
