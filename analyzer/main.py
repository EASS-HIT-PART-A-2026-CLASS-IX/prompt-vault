import os

from fastapi import FastAPI

from .agent import analyze_prompt
from .schemas import AnalyzeRequest, AnalyzeResponse

app = FastAPI(
    title="Prompt Analyzer",
    version="1.0.0",
    description="LLM-powered prompt quality analysis microservice.",
)


@app.get("/health", tags=["diagnostics"])
def health() -> dict[str, str]:
    key_status = "configured" if os.getenv("ANTHROPIC_API_KEY") else "mock-mode"
    return {"status": "ok", "service": "prompt-analyzer", "llm": key_status}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["analysis"])
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze a prompt and return a quality score with improvement suggestions."""
    return await analyze_prompt(request)
