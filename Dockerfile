FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev/test tools)
RUN uv sync --frozen --no-dev

# Copy application source
COPY prompt_vault/ ./prompt_vault/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY .env.example ./.env

# Create data directory for SQLite
RUN mkdir -p data

# Run migrations then start the server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn prompt_vault.app.main:app --host 0.0.0.0 --port 8000"]
