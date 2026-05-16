from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    title: str
    text: str
    category: str
    current_effectiveness: int = Field(ge=1, le=5)


class AnalyzeResponse(BaseModel):
    suggested_effectiveness: int = Field(ge=1, le=5, description="Revised 1-5 score")
    suggestions: list[str] = Field(description="Actionable improvements (2-4 bullet points)")
    summary: str = Field(description="One-sentence verdict on the prompt quality")
