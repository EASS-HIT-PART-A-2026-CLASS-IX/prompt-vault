"""Tests for the Streamlit dashboard helper functions (EX2 bonus)."""

from unittest.mock import MagicMock, patch

import pytest

import dashboard.app as app

SAMPLE_PROMPTS = [
    {
        "id": 1,
        "title": "Explain recursion",
        "text": "Explain {concept} using a simple analogy.",
        "model": "claude-sonnet-4-6",
        "category": "learning",
        "task_type": "explain concept",
        "effectiveness": 5,
        "tags": "teaching,recursion",
        "notes": None,
        "token_count": 95,
        "version": 1,
    },
    {
        "id": 2,
        "title": "Code review",
        "text": "Review this Python function for bugs and style.",
        "model": "claude-sonnet-4-6",
        "category": "coding",
        "task_type": "code review",
        "effectiveness": 4,
        "tags": "python,review",
        "notes": "Works well with short functions.",
        "token_count": None,
        "version": 1,
    },
]


def _mock_get(prompts: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = prompts
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_prompts_returns_list():
    with patch("httpx.get", return_value=_mock_get(SAMPLE_PROMPTS)) as mock_get:
        result = app.fetch_prompts()

    mock_get.assert_called_once()
    assert result == SAMPLE_PROMPTS
    assert len(result) == 2


def test_fetch_prompts_passes_limit_param():
    with patch("httpx.get", return_value=_mock_get([])) as mock_get:
        app.fetch_prompts()

    _, kwargs = mock_get.call_args
    assert kwargs.get("params", {}).get("limit", 0) >= 100


def test_create_prompt_posts_payload():
    payload = {
        "title": "Test",
        "text": "Do something useful.",
        "model": "claude-sonnet-4-6",
        "category": "coding",
        "task_type": "test",
        "effectiveness": 3,
        "tags": "test",
    }
    created = {**payload, "id": 99, "notes": None, "token_count": None, "version": 1}

    mock_resp = MagicMock()
    mock_resp.json.return_value = created
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        result = app.create_prompt(payload)

    mock_post.assert_called_once_with(
        f"{app.API_URL}/prompts", json=payload, timeout=5
    )
    assert result["id"] == 99
    assert result["title"] == "Test"


def test_fetch_prompts_raises_on_http_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("500 Server Error")

    with patch("httpx.get", return_value=mock_resp):
        with pytest.raises(Exception, match="500 Server Error"):
            app.fetch_prompts()
