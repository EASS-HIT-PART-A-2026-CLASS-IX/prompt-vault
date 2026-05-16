import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from .cache import get_redis
from .database import SettingsDep, init_db
from .dependencies import RepositoryDep
from .models import PromptCreate, PromptRead, PromptUpdate
from .rate_limit import rate_limit_middleware

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

app.middleware("http")(rate_limit_middleware)


@app.get("/health", tags=["diagnostics"])
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/prompts", response_model=list[PromptRead], tags=["prompts"])
def list_prompts(
    repository: RepositoryDep,
    settings: SettingsDep,
    skip: int = 0,
    limit: int = 100,
) -> list[PromptRead]:
    """List all saved prompts with optional pagination. Cached in Redis for 60 s."""
    cache_key = f"prompts:list:{skip}:{limit}"
    redis = get_redis(settings)

    if redis is not None:
        cached = redis.get(cache_key)
        if cached:
            return json.loads(cached)

    result = repository.list(skip=skip, limit=limit)

    if redis is not None:
        redis.setex(cache_key, 60, json.dumps([p.model_dump() for p in result]))

    return result


def _invalidate_list_cache(settings: SettingsDep) -> None:
    redis = get_redis(settings)
    if redis is not None:
        for key in redis.scan_iter("prompts:list:*"):
            redis.delete(key)


@app.post(
    "/prompts",
    response_model=PromptRead,
    status_code=status.HTTP_201_CREATED,
    tags=["prompts"],
)
def create_prompt(payload: PromptCreate, repository: RepositoryDep, settings: SettingsDep) -> PromptRead:
    """Save a new prompt to the vault."""
    prompt = repository.create(payload)
    logger.info("prompt.created id=%s title=%s", prompt.id, prompt.title)
    _invalidate_list_cache(settings)
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
    prompt_id: int, payload: PromptUpdate, repository: RepositoryDep, settings: SettingsDep
) -> PromptRead:
    """Update fields on an existing prompt (e.g. effectiveness, notes)."""
    prompt = repository.update(prompt_id, payload)
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with id {prompt_id} not found",
        )
    logger.info("prompt.updated id=%s", prompt_id)
    _invalidate_list_cache(settings)
    return prompt


@app.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["prompts"])
def delete_prompt(prompt_id: int, repository: RepositoryDep, settings: SettingsDep) -> None:
    """Delete a prompt from the vault."""
    deleted = repository.delete(prompt_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with id {prompt_id} not found",
        )
    logger.info("prompt.deleted id=%s", prompt_id)
    _invalidate_list_cache(settings)
