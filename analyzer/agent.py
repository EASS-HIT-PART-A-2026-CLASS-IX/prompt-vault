"""Prompt-quality analysis agent using Pydantic AI + Claude.

Falls back to a deterministic mock response when ANTHROPIC_API_KEY is not set,
so the service starts and tests pass without a live API key.
"""
from __future__ import annotations

import os

from pydantic_ai import Agent

from .schemas import AnalyzeRequest, AnalyzeResponse

_SYSTEM_PROMPT = """\
You are an expert prompt engineer reviewing AI prompts for quality and effectiveness.

Given a prompt's title, text, category, and current human-assigned effectiveness score (1-5),
you must return a structured analysis with:
- suggested_effectiveness: your revised score (1-5), adjusting up or down based on clarity,
  specificity, structure, and real-world usefulness
- suggestions: 2-4 concrete, actionable improvements (each under 15 words)
- summary: one sentence verdict on the overall prompt quality

Be concise and honest. Do not inflate scores.
"""


def _make_agent() -> Agent[None, AnalyzeResponse] | None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    return Agent(
        "anthropic:claude-haiku-4-5",
        output_type=AnalyzeResponse,
        instructions=_SYSTEM_PROMPT,
    )


_agent = _make_agent()


def _mock_response(req: AnalyzeRequest) -> AnalyzeResponse:
    """Deterministic fallback used when ANTHROPIC_API_KEY is absent."""
    score = min(5, max(1, req.current_effectiveness))
    return AnalyzeResponse(
        suggested_effectiveness=score,
        suggestions=[
            "Add a concrete example or placeholder variable.",
            "Specify the desired output format (list, paragraph, JSON).",
            "State any constraints (length, tone, audience).",
        ],
        summary=f"Mock analysis — set ANTHROPIC_API_KEY to enable real scoring (current: {score}/5).",
    )


async def analyze_prompt(req: AnalyzeRequest) -> AnalyzeResponse:
    if _agent is None:
        return _mock_response(req)

    user_msg = (
        f"Title: {req.title}\n"
        f"Category: {req.category}\n"
        f"Current effectiveness score: {req.current_effectiveness}/5\n\n"
        f"Prompt text:\n{req.text}"
    )
    result = await _agent.run(user_msg)
    return result.output
