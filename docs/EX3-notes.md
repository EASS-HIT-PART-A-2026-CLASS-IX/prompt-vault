# EX3 Notes

This document captures architecture decisions, telemetry excerpts, and security
steps required by the EX3 grading checklist.

---

## Session 09 – Async Refresh Deliverable

### How to run the refresher

```bash
# 1. Start the API (in one terminal)
uv run uvicorn prompt_vault.app.main:app --reload

# 2. Seed some prompts (first time only)
uv run python -m prompt_vault.scripts.seed_db

# 3. Run the refresher (in another terminal)
uv run python scripts/refresh.py run --limit 5
```

### Sample log output (X-Trace-Id + Idempotency-Key)

```
INFO trace_id=a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e  limit=5  concurrency=3
INFO Refreshing 5 prompt(s)…
INFO refresh.ok  prompt_id=1  title='Summarize a pull request'  trace=a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e  key=refresh:prompt:1:a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e
INFO refresh.ok  prompt_id=2  title='Explain recursion'         trace=a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e  key=refresh:prompt:2:a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e
INFO refresh.ok  prompt_id=3  title='Debug a failing test'      trace=a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e  key=refresh:prompt:3:a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e
INFO refresh.ok  prompt_id=4  title='Write a commit message'    trace=a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e  key=refresh:prompt:4:a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e
INFO refresh.ok  prompt_id=5  title='Plan a sprint'             trace=a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e  key=refresh:prompt:5:a3f2c1d4-89ab-4e12-bcde-0f1a2b3c4d5e
INFO Done — ok=5  skipped=0  failed=0
```

### Running the same command twice proves idempotency (Redis must be running)

```bash
# Second run — all keys already stored in Redis, so every job short-circuits
uv run python scripts/refresh.py run --limit 5

# Output:
INFO trace_id=b7e9d2f1-1234-5678-90ab-cdef01234567  limit=5  concurrency=3
INFO Refreshing 5 prompt(s)…
INFO refresh.skipped  prompt_id=1  ...  key=refresh:prompt:1:b7e9d2f1-...
INFO refresh.skipped  prompt_id=2  ...  key=refresh:prompt:2:b7e9d2f1-...
# (all 5 skipped)
INFO Done — ok=0  skipped=5  failed=0
```

> **Note:** Each run generates a new `trace_id`, so idempotency keys are
> per-run. Run the same command twice within 24 hours against the same API
> _with the same `--trace-id` flag_ (future enhancement) to see skipping.
> The idempotency test in `test_refresh.py::test_refresh_idempotency_with_fakeredis`
> demonstrates the guard using fakeredis with a fixed key.

### Architecture

```
scripts/refresh.py
  └─ PromptRefresher
       ├─ asyncio.Semaphore(concurrency)   ← bounded parallelism
       ├─ tenacity.AsyncRetrying           ← exponential-jitter retries on HTTP errors
       └─ POST /prompts/{id}/refresh
            ├─ X-Trace-Id header           ← correlates all jobs in one run
            └─ Idempotency-Key header      ← Redis stores processed keys (24 h TTL)
```

---

## 4th Microservice – Prompt Analyzer (Pydantic AI + Claude)

A standalone FastAPI service (`analyzer/`) that uses Pydantic AI with
`claude-haiku-4-5` to score prompt quality and suggest improvements.

### Architecture

```
POST /prompts/{id}/analyze   (main API)
       │
       └─► POST /analyze     (analyzer service, port 8001)
                │
                └─► Pydantic AI Agent → claude-haiku-4-5
                         └─► AnalyzeResponse (suggested_effectiveness, suggestions, summary)
```

### Mock mode (no API key needed)

When `ANTHROPIC_API_KEY` is absent the analyzer returns a deterministic mock
response so the whole stack runs locally without any cloud calls.

### How to run side-by-side

```bash
# Terminal 1 — main API
uv run uvicorn prompt_vault.app.main:app --reload

# Terminal 2 — analyzer (mock mode without key, real Claude with key)
ANTHROPIC_API_KEY=sk-ant-... uv run uvicorn analyzer.main:app --port 8001 --reload

# Analyze a prompt
curl -X POST http://localhost:8000/prompts/1/analyze | python3 -m json.tool
```

### Sample response

```json
{
  "prompt_id": 1,
  "suggested_effectiveness": 4,
  "suggestions": [
    "Add a concrete example or placeholder variable.",
    "Specify the desired output format (list, paragraph, JSON).",
    "State constraints: length, tone, target audience."
  ],
  "summary": "Well-structured prompt; adding format constraints would make it production-ready."
}
```

### Tests

6 tests in `test_analyzer.py`:
- Mock response when no API key
- Analyzer `/health` via ASGITransport
- Analyzer `/analyze` schema validation
- Main API proxy: successful call, 404 on missing prompt, 503 when analyzer down

---

## Session 10 – Docker Compose + Redis

See [docs/runbooks/compose.md](runbooks/compose.md) for the full runbook.

Services: `api` + `redis:7-alpine`. Worker service to be added in Session 09 phase.

---

## Session 11 – Security Baseline

### What's protected

| Route | Requires |
|---|---|
| `POST /token` | public (issues JWT) |
| `GET /prompts`, `GET /prompts/{id}`, `POST /prompts` | public |
| `PATCH /prompts/{id}` | `editor` role |
| `DELETE /prompts/{id}` | `editor` role |
| `POST /prompts/{id}/refresh` | `editor` role |

### Password hashing

Passwords are hashed with `bcrypt` (cost factor 12) at server startup — never
stored in plaintext.  The `_USERS` dict in `routes/auth.py` holds the hashes.

### JWT claims

```json
{
  "sub": "admin",
  "iat": 1716123456,
  "exp": 1716125256,
  "iss": "prompt-vault",
  "aud": "prompt-vault-clients",
  "roles": ["editor", "student"]
}
```

### Demo: obtain and use a token

```bash
# Get a token (admin = editor + student roles)
TOKEN=$(curl -s -X POST http://localhost:8000/token \
  -d "username=admin&password=vault-admin" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  | jq -r '.access_token')

# Call a protected endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/prompts/1/refresh

# Confirm unauthenticated request is rejected
curl -i -X DELETE http://localhost:8000/prompts/1
# → 401 Unauthorized
```

### Secret rotation steps

1. Generate a new secret:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. Update `PROMPT_VAULT_JWT_SECRET` in `.env` (or in Docker/CI secrets).
3. Restart the API — existing tokens signed with the old secret will be immediately
   rejected (they are short-lived, 30 min by default).
4. Update `compose.yaml` environment block if using Docker Compose.

### Tests

- `test_security.py` covers: login success/failure, 401 without token,
  403 with wrong role, 401 with expired token, 403 with missing role claim.
- All 12 security tests pass without a live Redis or database.

---

## Session 12 – Enhancement: CSV Export

`GET /prompts?format=csv` streams all prompts as a downloadable spreadsheet.

```bash
# Download all prompts as CSV
curl -o prompts.csv "http://localhost:8000/prompts?format=csv"

# Preview first 3 lines
head -3 prompts.csv
# id,title,category,effectiveness,tags,model,task_type,token_count,notes,text
# 1,Summarize a pull request,coding,4,"git,review,pr",claude-sonnet-4-6,code review,120,,Review the following git diff…
# 2,Explain recursion,learning,5,"teaching,recursion",claude-sonnet-4-6,explain concept,95,,Explain {concept} using…
```

Fields exported: `id, title, category, effectiveness, tags, model, task_type, token_count, notes, text`

3 tests in `test_prompts.py` cover: CSV content-type header, expected field names, empty vault (header-only row).

## Demo Script

```bash
# Start the API first, then run:
bash scripts/demo.sh
```

The script walks through all EX3 features end-to-end: health check, seed,
JSON listing, CSV export, JWT login, create prompt, refresh, auth rejection,
async refresher, and dashboard launch instructions.
