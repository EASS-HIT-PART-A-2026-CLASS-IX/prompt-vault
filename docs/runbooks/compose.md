# Compose Runbook

Prompt Vault runs as two cooperating services: the FastAPI backend and Redis.
A third service (async worker) will be added in the EX3 refresh script phase.

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Port 8000 and 6379 free on your machine

## Launch the stack

```bash
docker compose up --build
```

Wait until both services report healthy:

```
prompt-vault-redis-1  | Ready to accept connections
prompt-vault-api-1    | INFO:     Application startup complete.
```

## Verify health

```bash
# API health check
curl http://localhost:8000/health

# Redis is up
docker compose exec redis redis-cli ping
```

## Check rate-limit headers

```bash
curl -si http://localhost:8000/prompts | grep -i x-ratelimit
# X-RateLimit-Limit: 30
# X-RateLimit-Remaining: 29
```

## Confirm Redis cache is working

```bash
# First request — cache miss, populates Redis
curl -s http://localhost:8000/prompts > /dev/null

# Check the key exists in Redis
docker compose exec redis redis-cli keys "prompts:list:*"
# prompts:list:0:100

# Second request is served from cache (TTL 60 s)
curl -s http://localhost:8000/prompts > /dev/null
```

## Stop the stack

```bash
docker compose down          # keeps the SQLite volume
docker compose down -v       # also removes the volume (wipes data)
```

## Environment variables

| Variable | Default in Compose | Description |
|---|---|---|
| `PROMPT_VAULT_REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `PROMPT_VAULT_RATE_LIMIT_PER_MINUTE` | `30` | Max requests per IP per 60 s |
| `PROMPT_VAULT_DATABASE_URL` | `sqlite:///./data/prompts.db` | SQLite path (inside volume) |

Override any variable by adding it to a `.env` file in the repo root or setting it inline:

```bash
PROMPT_VAULT_RATE_LIMIT_PER_MINUTE=100 docker compose up
```

## Run tests against the live stack

```bash
# In a separate terminal while compose is up:
uv run pytest prompt_vault/tests -v
```

Tests use an in-memory SQLite and skip Redis (no `PROMPT_VAULT_REDIS_URL` set locally),
so they run independently of the Compose stack.
