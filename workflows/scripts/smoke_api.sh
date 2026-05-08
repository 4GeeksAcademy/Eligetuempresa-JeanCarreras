#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_BASE="${API_BASE:-http://localhost:8000}"
CURRENCY="${CURRENCY:-USD}"
START_DATE="${START_DATE:-$(date -u -d '7 days ago' +%Y-%m-%d)}"
END_DATE="${END_DATE:-$(date -u +%Y-%m-%d)}"

ADMIN_TOKEN="${BRASALAND_ADMIN_TOKEN:-brasaland-admin-token}"
EXEC_TOKEN="${BRASALAND_EXECUTIVE_TOKEN:-brasaland-executive-token}"
OPS_TOKEN="${BRASALAND_OPERATIONS_TOKEN:-brasaland-operations-token}"
FIN_TOKEN="${BRASALAND_FINANCE_TOKEN:-brasaland-finance-token}"

PASS_COUNT=0
FAIL_COUNT=0
SERVER_PID=""

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "[PASS] $1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo "[FAIL] $1"
}

assert_status() {
  local test_name="$1"
  local expected_status="$2"
  local actual_status="$3"
  if [[ "$actual_status" == "$expected_status" ]]; then
    pass "$test_name (status=$actual_status)"
  else
    fail "$test_name (status esperado=$expected_status, recibido=$actual_status)"
  fi
}

assert_contains() {
  local test_name="$1"
  local expected_fragment="$2"
  local body="$3"
  if grep -q "$expected_fragment" <<<"$body"; then
    pass "$test_name contiene '$expected_fragment'"
  else
    fail "$test_name no contiene '$expected_fragment'"
  fi
}

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

is_api_up() {
  curl -fsS "$API_BASE/health" >/dev/null 2>&1
}

ensure_api_running() {
  if is_api_up; then
    echo "API ya estaba corriendo en $API_BASE"
    return 0
  fi

  local py_bin=""
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    py_bin="$ROOT_DIR/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    py_bin="$(command -v python3)"
  else
    echo "No se encontro interprete Python para levantar la API"
    exit 1
  fi

  echo "Levantando API local para smoke tests..."
  (
    cd "$ROOT_DIR/services/brasaland-api"
    "$py_bin" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >/tmp/uvicorn-smoke.log 2>&1
  ) &
  SERVER_PID=$!

  for _ in {1..30}; do
    if is_api_up; then
      echo "API lista para smoke"
      return 0
    fi
    sleep 1
  done

  echo "La API no inicio a tiempo"
  cat /tmp/uvicorn-smoke.log || true
  exit 1
}

echo "== Smoke API Brasaland =="
echo "API_BASE=$API_BASE"
echo "CURRENCY=$CURRENCY"
echo "Rango=$START_DATE..$END_DATE"
ensure_api_running

# 1) Health
health_body="$(curl -fsS "$API_BASE/health")"
assert_contains "health" '"status":"ok"' "$health_body"

# 2) Sales summary
summary_body="$(curl -fsS "$API_BASE/api/v1/sales/summary?period=week&currency=$CURRENCY&start_date=$START_DATE&end_date=$END_DATE")"
assert_contains "sales summary" '"total_sales"' "$summary_body"

# 3) Finance KPI with valid finance role
finance_body_file="$(mktemp)"
finance_status="$(curl -sS -o "$finance_body_file" -w "%{http_code}" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: $FIN_TOKEN" \
  "$API_BASE/api/v1/finance/kpis?currency=$CURRENCY&start_date=$START_DATE&end_date=$END_DATE")"
finance_body="$(cat "$finance_body_file")"
rm -f "$finance_body_file"
assert_status "finance kpis autorizado" "200" "$finance_status"
assert_contains "finance kpis payload" '"gross_margin_pct"' "$finance_body"

# 4) Finance KPI with invalid token (should fail)
finance_unauth_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: invalid-token" \
  "$API_BASE/api/v1/finance/kpis?currency=$CURRENCY&start_date=$START_DATE&end_date=$END_DATE")"
assert_status "finance kpis sin token valido" "401" "$finance_unauth_status"

# 5) Create sales event with operations role
event_payload="$(cat <<JSON
{
  "store_id": "mia-001",
  "sold_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "total_amount": 21.75,
  "currency": "USD"
}
JSON
)"
create_body_file="$(mktemp)"
create_status="$(curl -sS -o "$create_body_file" -w "%{http_code}" \
  -X POST "$API_BASE/api/v1/sales/events" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  -d "$event_payload")"
create_body="$(cat "$create_body_file")"
rm -f "$create_body_file"
assert_status "crear evento venta" "201" "$create_status"
assert_contains "crear evento payload" '"id"' "$create_body"

# 6) CSV export with executive role
csv_file="$(mktemp)"
csv_status="$(curl -sS -o "$csv_file" -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/reports/sales.csv?currency=$CURRENCY&start_date=$START_DATE&end_date=$END_DATE")"
csv_head="$(head -n 1 "$csv_file")"
rm -f "$csv_file"
assert_status "exportar csv" "200" "$csv_status"
assert_contains "csv header" 'store_id,store_name,country,sold_at,amount,currency' "$csv_head"

# 7) Audit logs with admin role
audit_body_file="$(mktemp)"
audit_status="$(curl -sS -o "$audit_body_file" -w "%{http_code}" \
  -H "X-API-Role: admin" \
  -H "X-API-Token: $ADMIN_TOKEN" \
  "$API_BASE/api/v1/audit/logs?limit=10")"
audit_body="$(cat "$audit_body_file")"
rm -f "$audit_body_file"
assert_status "audit logs" "200" "$audit_status"
assert_contains "audit payload" '"action"' "$audit_body"

echo ""
echo "Resultado: PASS=$PASS_COUNT FAIL=$FAIL_COUNT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi
