"""Async prompt-refresh CLI.

Re-estimates token counts for all prompts using bounded concurrency and
tenacity retries.  Redis idempotency keys (stored by the API) prevent
duplicate work when the script is run multiple times.

Usage:
    uv run python scripts/refresh.py
    uv run python scripts/refresh.py --limit 5 --concurrency 2
    uv run python scripts/refresh.py --base-url http://localhost:8000
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass

import httpx
import typer
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("prompt-refresh")

cli = typer.Typer(help="Async prompt-refresh — re-estimates token counts for all prompts.")

_DEFAULT_BASE_URL = "http://localhost:8000"
_DEFAULT_CONCURRENCY = 3
_MAX_ATTEMPTS = 3


@dataclass
class RefreshJob:
    prompt_id: int
    title: str


class PromptRefresher:
    def __init__(self, client: httpx.AsyncClient, trace_id: str, concurrency: int) -> None:
        self._client = client
        self._trace_id = trace_id
        self._sem = asyncio.Semaphore(concurrency)

    async def refresh_all(self, jobs: list[RefreshJob]) -> dict[str, int]:
        tasks = [self._bounded(job) for job in jobs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        counts: dict[str, int] = {"ok": 0, "skipped": 0, "failed": 0}
        for r in results:
            if isinstance(r, Exception):
                counts["failed"] += 1
            elif r == "skipped":
                counts["skipped"] += 1
            else:
                counts["ok"] += 1
        return counts

    async def _bounded(self, job: RefreshJob) -> str:
        async with self._sem:
            return await self._refresh_with_retry(job)

    async def _refresh_with_retry(self, job: RefreshJob) -> str:
        idempotency_key = f"refresh:prompt:{job.prompt_id}:{self._trace_id}"
        result = "ok"

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(_MAX_ATTEMPTS),
            wait=wait_exponential_jitter(initial=0.5, max=5.0),
            retry=retry_if_exception_type(httpx.HTTPError),
        ):
            with attempt:
                resp = await self._client.post(
                    f"/prompts/{job.prompt_id}/refresh",
                    headers={
                        "X-Trace-Id": self._trace_id,
                        "Idempotency-Key": idempotency_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

        result = "skipped" if data.get("already_refreshed") else "ok"
        logger.info(
            "refresh.%s  prompt_id=%s  title=%r  trace=%s  key=%s",
            result,
            job.prompt_id,
            job.title,
            self._trace_id,
            idempotency_key,
        )
        return result


@cli.command()
def run(
    limit: int = typer.Option(10, help="Max prompts to refresh."),
    concurrency: int = typer.Option(_DEFAULT_CONCURRENCY, help="Parallel refresh jobs."),
    base_url: str = typer.Option(_DEFAULT_BASE_URL, help="API base URL."),
    username: str = typer.Option("admin", help="Username for JWT auth."),
    password: str = typer.Option("vault-admin", help="Password for JWT auth."),
) -> None:
    """Refresh token-count estimates for all prompts with bounded async concurrency."""
    asyncio.run(_run(limit=limit, concurrency=concurrency, base_url=base_url, username=username, password=password))


async def _run(limit: int, concurrency: int, base_url: str, username: str, password: str) -> None:
    trace_id = str(uuid.uuid4())
    typer.echo(f"trace_id={trace_id}  limit={limit}  concurrency={concurrency}")

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        token_resp = await client.post(
            "/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_resp.raise_for_status()
        token = token_resp.json()["access_token"]

        resp = await client.get("/prompts", params={"limit": limit})
        resp.raise_for_status()
        prompts = resp.json()

    if not prompts:
        typer.echo("No prompts found — nothing to refresh.")
        return

    typer.echo(f"Refreshing {len(prompts)} prompt(s)…")

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0, headers={"Authorization": f"Bearer {token}"}) as client:
        refresher = PromptRefresher(client, trace_id, concurrency)
        jobs = [RefreshJob(p["id"], p["title"]) for p in prompts]
        counts = await refresher.refresh_all(jobs)

    typer.echo(
        f"Done — ok={counts['ok']}  skipped={counts['skipped']}  failed={counts['failed']}"
    )


if __name__ == "__main__":
    cli()
