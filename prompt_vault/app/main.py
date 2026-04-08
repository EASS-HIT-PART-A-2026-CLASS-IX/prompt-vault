import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from .database import SettingsDep, init_db
from .dependencies import RepositoryDep
from .models import PromptCreate, PromptRead, PromptUpdate

logger = logging.getLogger("prompt-vault")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Prompt Vault",
    version="1.0.0",
    description="A personal library for managing and rating AI prompts.",
    lifespan=lifespan,
)


@app.get("/health", tags=["diagnostics"])
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/prompts", response_model=list[PromptRead], tags=["prompts"])
def list_prompts(
    repository: RepositoryDep,
    skip: int = 0,
    limit: int = 100,
) -> list[PromptRead]:
    """List all saved prompts with optional pagination."""
    return repository.list(skip=skip, limit=limit)


@app.post(
    "/prompts",
    response_model=PromptRead,
    status_code=status.HTTP_201_CREATED,
    tags=["prompts"],
)
def create_prompt(payload: PromptCreate, repository: RepositoryDep) -> PromptRead:
    """Save a new prompt to the vault."""
    prompt = repository.create(payload)
    logger.info("prompt.created id=%s title=%s", prompt.id, prompt.title)
    return prompt


@app.get("/prompts/{prompt_id}", response_model=PromptRead, tags=["prompts"])
def read_prompt(prompt_id: int, repository: RepositoryDep) -> PromptRead:
    """Retrieve a specific prompt by ID."""
    prompt = repository.get(prompt_id)
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with id {prompt_id} not found",
        )
    return prompt


@app.patch("/prompts/{prompt_id}", response_model=PromptRead, tags=["prompts"])
def update_prompt(
    prompt_id: int, payload: PromptUpdate, repository: RepositoryDep
) -> PromptRead:
    """Update fields on an existing prompt (e.g. effectiveness, notes)."""
    prompt = repository.update(prompt_id, payload)
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with id {prompt_id} not found",
        )
    logger.info("prompt.updated id=%s", prompt_id)
    return prompt


@app.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["prompts"])
def delete_prompt(prompt_id: int, repository: RepositoryDep) -> None:
    """Delete a prompt from the vault."""
    deleted = repository.delete(prompt_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with id {prompt_id} not found",
        )
    logger.info("prompt.deleted id=%s", prompt_id)
