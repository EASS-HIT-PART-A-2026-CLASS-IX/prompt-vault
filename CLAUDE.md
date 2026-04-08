# Prompt Vault – Project Context for Claude Code

## What this project is
EX1 submission for the EASS course (Engineering of Advanced Software Solutions, HIT, 2026 Class IX).
A FastAPI backend for managing personal AI prompts — save, rate, and retrieve prompts that work well.

## Course context
- **Course org:** https://github.com/EASS-HIT-PART-A-2026-CLASS-IX
- **Lecture notes repo:** ~/lecture-notes (or https://github.com/EASS-HIT-PART-A-2026-CLASS-IX/lecture-notes)
- **3 exercises total:**
  - EX1 (this repo) – FastAPI backend. Due 30/03/2026 (submitting late).
  - EX2 – Streamlit dashboard that talks to this API. Due 18/05/2026.
  - EX3 – Full microservice stack: this API + SQLite + EX2 interface + LLM microservice. Due 01/07/2026.
- **Same domain across all 3 exercises** — Prompt Vault grows incrementally.

## Current state (EX1 complete)
- FastAPI CRUD API: list / create / get / update / delete prompts
- SQLite persistence via SQLModel + Alembic migrations (applied)
- 17 pytest tests, all green
- Seed script: `uv run python -m prompt_vault.scripts.seed_db`
- Dockerfile included
- REST Client playground: `prompts.http`

## How to run
```bash
uv run alembic upgrade head          # apply migrations (first time)
uv run uvicorn prompt_vault.app.main:app --reload
uv run pytest prompt_vault/tests -v
uv run python -m prompt_vault.scripts.seed_db
```

## Tech stack
- Python 3.12, uv (package manager)
- FastAPI + Pydantic v2 + pydantic-settings
- SQLModel + SQLAlchemy + Alembic + SQLite
- pytest + TestClient

## Prompt data model
| Field | Type | Notes |
|---|---|---|
| title | str | 1–100 chars |
| text | str | The actual prompt |
| model | str | e.g. claude-sonnet-4-6 |
| category | enum | coding/writing/debugging/learning/other |
| task_type | str | e.g. "explain concept" |
| effectiveness | int | 1–5 |
| tags | str | comma-separated, auto-lowercased |
| notes | str | optional |
| token_count | int | optional, ≥1 |
| version | int | default 1 |

## What comes next (EX2)
Build a Streamlit dashboard that connects to this API:
- List all prompts, filter by category / tag
- Add a new prompt via a form
- Show average effectiveness per category (the "one small extra" for the rubric)
- Run API and dashboard side-by-side locally

## Submission instructions
When GitHub Classroom org access is granted:
```bash
git remote add origin https://github.com/EASS-HIT-PART-A-2026-CLASS-IX/PromptVault.git
git push -u origin main
git tag ex1-final && git push origin ex1-final
```
