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

## Run the dashboard (EX2)

The Streamlit dashboard provides a browser UI for browsing prompts, adding new ones, and viewing effectiveness analytics.

**Start both services side-by-side** (two terminal tabs):

```bash
# Terminal 1 — backend
uv run uvicorn prompt_vault.app.main:app --reload

# Terminal 2 — dashboard
uv run streamlit run dashboard/app.py
```

Open `http://localhost:8501` in your browser. The dashboard connects to the API on `http://localhost:8000` by default.

### Dashboard features

| Tab | What it does |
|---|---|
| Browse Prompts | Lists all prompts; filter by category or tag; expand any row to read the full prompt text |
| Add Prompt | Form to create a new prompt without touching the API directly |
| Analytics | Bar chart of average effectiveness per category (small extra) |

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

## EX3 – Full-Stack Microservices

EX3 adds four production-grade layers on top of the EX1/EX2 foundation.

### 1. Docker Compose stack

Three cooperating services in `compose.yaml`:

```bash
docker compose up --build
```

| Service | Port | Role |
|---|---|---|
| `api` | 8000 | FastAPI backend + Redis-backed cache and rate limiting |
| `analyzer` | 8001 | Pydantic AI microservice (LLM prompt analysis) |
| `redis` | 6379 | Cache (60 s TTL) + idempotency keys (24 h TTL) |

See `docs/runbooks/compose.md` for health checks, rate-limit headers, and CI instructions.

### 2. Async refresh script

`scripts/refresh.py` refreshes token-count estimates for all prompts concurrently:

```bash
uv run python scripts/refresh.py run --limit 10 --concurrency 3
```

Features: `asyncio.Semaphore` for bounded parallelism, `tenacity` exponential-jitter retries, and Redis-backed idempotency keys — duplicate jobs short-circuit in under 1 ms.

### 3. JWT authentication and role-based access control

| Route | Requires |
|---|---|
| `POST /token` | public (issues JWT) |
| `GET /prompts*` | public |
| `PATCH /prompts/{id}`, `DELETE /prompts/{id}`, `POST /prompts/{id}/refresh` | `editor` role |

```bash
# Obtain a token and call a protected route
TOKEN=$(curl -s -X POST http://localhost:8000/token \
  -d "username=admin&password=vault-admin" \
  -H "Content-Type: application/x-www-form-urlencoded" | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" -X DELETE http://localhost:8000/prompts/1
```

Passwords are hashed with bcrypt (cost 12). See `docs/EX3-notes.md` for JWT claims and secret rotation steps.

### 4. LLM analyzer microservice

`POST /prompts/{id}/analyze` proxies to the `analyzer` service, which uses Pydantic AI with `claude-haiku-4-5` to score prompt quality:

```bash
curl -X POST http://localhost:8000/prompts/1/analyze | python3 -m json.tool
```

```json
{
  "prompt_id": 1,
  "suggested_effectiveness": 4,
  "suggestions": ["Add a concrete example.", "Specify output format.", "State target audience."],
  "summary": "Well-structured prompt; adding format constraints would make it production-ready."
}
```

The **Browse Prompts** tab in the Streamlit dashboard now shows an **Analyze with AI** button on any expanded prompt.

Run the analyzer without an API key (mock mode):

```bash
uv run uvicorn analyzer.main:app --port 8001 --reload
```

### 5. CSV export

```bash
curl -o prompts.csv "http://localhost:8000/prompts?format=csv"
```

### Demo

```bash
bash scripts/demo.sh
```

Walks through all EX3 features: health check, seed, JSON/CSV listing, JWT login, create, refresh, auth rejection, async refresh, and dashboard.

---

## AI Assistance

**EX1 (FastAPI backend):** Built with AI assistance following the sessions 03–04 pattern (FastAPI + SQLModel + Alembic). All generated code was reviewed, tests were run locally, and outputs verified via curl and the `/docs` explorer.

**EX2 (Streamlit dashboard):** Dashboard structure and helper functions drafted with AI assistance. The three-tab layout (Browse / Add / Analytics), filter logic, and form validation were reviewed and tested manually by running the API and dashboard side-by-side. Tests in `test_dashboard.py` were verified with `uv run pytest`.

**EX3 (Full-stack microservices):** Redis caching, rate limiting, async refresh script, JWT security, analyzer microservice, CSV export, and Docker Compose orchestration all developed with AI assistance. Architecture decisions were reviewed session by session; all 46 tests were run locally and verified green before each commit.
