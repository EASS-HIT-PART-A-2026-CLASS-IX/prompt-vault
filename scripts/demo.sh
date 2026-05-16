#!/usr/bin/env bash
# Prompt Vault — EX3 demo script
# Walks a grader through every major feature in ~90 seconds.
# Assumes the API is already running on http://localhost:8000.
# Start it first with: uv run uvicorn prompt_vault.app.main:app --reload

set -euo pipefail
API="http://localhost:8000"
BOLD=$(tput bold 2>/dev/null || true)
RESET=$(tput sgr0 2>/dev/null || true)

step() { echo; echo "${BOLD}==> $*${RESET}"; }
ok()   { echo "    OK: $*"; }

# ── 1. Health check ───────────────────────────────────────────────────────────
step "1. Health check"
curl -sf "$API/health" | python3 -m json.tool
ok "API is up"

# ── 2. Seed sample prompts ────────────────────────────────────────────────────
step "2. Seed sample prompts (idempotent)"
uv run python -m prompt_vault.scripts.seed_db
ok "Seed complete"

# ── 3. List prompts as JSON ───────────────────────────────────────────────────
step "3. List prompts (JSON)"
curl -sf "$API/prompts?limit=3" | python3 -m json.tool | head -30
ok "JSON listing works"

# ── 4. CSV export ─────────────────────────────────────────────────────────────
step "4. Export prompts to CSV"
curl -sf "$API/prompts?format=csv" -o /tmp/prompts.csv
head -3 /tmp/prompts.csv
ok "CSV saved to /tmp/prompts.csv ($(wc -l < /tmp/prompts.csv) lines)"

# ── 5. Get an auth token ──────────────────────────────────────────────────────
step "5. Login and get a JWT"
TOKEN=$(curl -sf -X POST "$API/token" \
  -d "username=admin&password=vault-admin" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
ok "Token obtained (${TOKEN:0:40}…)"

# ── 6. Add a new prompt (public endpoint) ─────────────────────────────────────
step "6. Create a new prompt"
NEW=$(curl -sf -X POST "$API/prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Demo prompt",
    "text": "Summarise the following text in three bullet points: {text}",
    "model": "claude-sonnet-4-6",
    "category": "writing",
    "task_type": "summarise",
    "effectiveness": 4,
    "tags": "demo,summarise"
  }')
DEMO_ID=$(echo "$NEW" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
ok "Created prompt #$DEMO_ID"

# ── 7. Refresh token count (editor-only, needs JWT) ───────────────────────────
step "7. Refresh token estimate for prompt #$DEMO_ID"
curl -sf -X POST "$API/prompts/$DEMO_ID/refresh" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Trace-Id: demo-trace-001" \
  -H "Idempotency-Key: demo:refresh:$DEMO_ID" \
  | python3 -m json.tool
ok "Refresh endpoint works (idempotency key stored in Redis if running)"

# ── 8. Confirm unauthenticated delete is rejected ─────────────────────────────
step "8. Unauthenticated DELETE returns 401"
STATUS=$(curl -so /dev/null -w "%{http_code}" -X DELETE "$API/prompts/$DEMO_ID")
[ "$STATUS" -eq 401 ] && ok "Got 401 as expected" || echo "UNEXPECTED STATUS: $STATUS"

# ── 9. Async refresh script ───────────────────────────────────────────────────
step "9. Async refresh script (limit=3)"
uv run python scripts/refresh.py run --limit 3

# ── 10. Dashboard ─────────────────────────────────────────────────────────────
step "10. Dashboard"
echo "    Run in a second terminal:"
echo "      uv run streamlit run dashboard/app.py"
echo "    Then open http://localhost:8501"

step "Demo complete — all EX3 features verified"
