# Prompt Vault

A personal library for saving, rating, and managing AI prompts — built with FastAPI, SQLModel, and SQLite.

## What it does

Prompt Vault lets you store the AI prompts that actually work. Save a prompt with its model, category, effectiveness score, and token count. Update its rating after testing. Find your best prompts without rewriting them from scratch.

## Project structure

```
PromptVault/
├── prompt_vault/
│   ├── app/
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── models.py        # SQLModel table + Pydantic schemas
│   │   ├── database.py      # Engine, session, init_db
│   │   ├── repository.py    # CRUD logic (DB-backed)
│   │   ├── dependencies.py  # FastAPI dependency wiring
│   │   └── main.py          # Routes
│   ├── tests/
│   │   ├── conftest.py      # Hermetic SQLite fixtures
│   │   └── test_prompts.py  # Full test suite
│   └── scripts/
│       └── seed_db.py       # Sample data seeder
├── migrations/              # Alembic schema history
├── data/                    # SQLite file (gitignored)
├── Dockerfile
├── prompts.http             # VS Code REST Client playground
└── .env.example
```

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — install with:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  exec "$SHELL" -l
  ```

## Setup

```bash
# 1. Clone the repo and enter the project folder
git clone <repo-url>
cd PromptVault

# 2. Create the virtual environment and install dependencies
uv sync

# 3. Copy environment config
cp .env.example .env

# 4. Create the database and run migrations
uv run alembic upgrade head

# 5. (Optional) load sample prompts
uv run python -m prompt_vault.scripts.seed_db
```

## Run the API

```bash
uv run uvicorn prompt_vault.app.main:app --reload
```

Open `http://localhost:8000/docs` for the interactive API explorer.

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/prompts` | List all prompts (supports `?skip=&limit=`) |
| POST | `/prompts` | Save a new prompt |
| GET | `/prompts/{id}` | Get a prompt by ID |
| PATCH | `/prompts/{id}` | Update fields (effectiveness, notes, etc.) |
| DELETE | `/prompts/{id}` | Delete a prompt |

### Example: save a prompt

```bash
curl -X POST http://localhost:8000/prompts \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Explain recursion",
    "text": "Explain {concept} using a simple analogy.",
    "model": "claude-sonnet-4-6",
    "category": "learning",
    "task_type": "explain concept",
    "effectiveness": 5,
    "tags": "teaching,recursion",
    "token_count": 95
  }'
```

## Run tests

```bash
uv run pytest prompt_vault/tests -v
```

All tests run against a temporary in-memory SQLite database — no shared state between tests.

## Run with Docker

```bash
docker build -t prompt-vault .
docker run -p 8000:8000 prompt-vault
```

## Data model

| Field | Type | Constraints |
|---|---|---|
| `id` | int | Auto, primary key |
| `title` | str | 1–100 chars |
| `text` | str | Required |
| `model` | str | e.g. `claude-sonnet-4-6`, `gpt-4o` |
| `category` | enum | `coding / writing / debugging / learning / other` |
| `task_type` | str | e.g. `explain concept`, `code review` |
| `effectiveness` | int | 1–5 |
| `tags` | str | Comma-separated, auto-lowercased |
| `notes` | str | Optional |
| `token_count` | int | Optional, ≥ 1 |
| `version` | int | Default 1 |

## AI Assistance

This project was built with AI assistance (Claude Sonnet 4.6 via Claude Code). The architecture follows the course sessions 03–04 pattern (FastAPI + SQLModel + Alembic). All generated code was reviewed, tests were run locally, and outputs verified via curl and the `/docs` explorer.
