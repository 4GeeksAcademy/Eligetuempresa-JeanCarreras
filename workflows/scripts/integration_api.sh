#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_BASE="${API_BASE:-http://localhost:8000}"

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

  echo "Levantando API local para integration tests..."
  (
    cd "$ROOT_DIR/services/brasaland-api"
    "$py_bin" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >/tmp/uvicorn-integration.log 2>&1
  ) &
  SERVER_PID=$!

  for _ in {1..30}; do
    if is_api_up; then
      echo "API lista para pruebas"
      return 0
    fi
    sleep 1
  done

  echo "La API no inicio a tiempo"
  cat /tmp/uvicorn-integration.log || true
  exit 1
}

echo "== Integration API Brasaland =="
ensure_api_running

# 1) stores endpoint returns records
stores_body="$(curl -fsS "$API_BASE/api/v1/stores")"
assert_contains "stores payload" '"id"' "$stores_body"

# 2) country-filtered summary for CO
summary_co="$(curl -fsS "$API_BASE/api/v1/sales/summary?period=week&currency=USD&country=CO")"
assert_contains "sales summary CO" '"currency":"USD"' "$summary_co"

# 3) markets summary includes wow field
markets_body="$(curl -fsS "$API_BASE/api/v1/markets/summary?currency=USD")"
assert_contains "markets wow" '"wow_variation_pct"' "$markets_body"

# 4) by-store filtered to US includes market field
store_us_body="$(curl -fsS "$API_BASE/api/v1/sales/by-store?currency=USD&country=US")"
assert_contains "sales by-store US" '"market"' "$store_us_body"

# 5) daily trend returns day key
trend_body="$(curl -fsS "$API_BASE/api/v1/sales/daily-trend?currency=USD")"
assert_contains "daily trend" '"day"' "$trend_body"

# 6) finance endpoint with executive role (allowed)
finance_exec_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/finance/kpis?currency=USD")"
assert_status "finance con executive" "200" "$finance_exec_status"

# 7) audit endpoint with executive role (forbidden)
audit_exec_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/audit/logs?limit=5")"
assert_status "audit con executive prohibido" "403" "$audit_exec_status"

# 8) csv endpoint with operations role (forbidden)
csv_ops_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/reports/sales.csv?currency=USD")"
assert_status "csv con operations prohibido" "403" "$csv_ops_status"

# 9) finance endpoint with wrong token (unauthorized)
finance_bad_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: invalid-token" \
  "$API_BASE/api/v1/finance/kpis?currency=USD")"
assert_status "finance token invalido" "401" "$finance_bad_status"

# 10) inactivity alerts with executive role (allowed)
alerts_exec_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/alerts/inactivity?window_minutes=60")"
assert_status "alerts inactivity con executive" "200" "$alerts_exec_status"

alerts_exec_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/alerts/inactivity?window_minutes=60")"
assert_contains "alerts inactivity payload" '"severity"' "$alerts_exec_body"
assert_contains "alerts inactivity accion" '"recommended_action"' "$alerts_exec_body"

# 11) inactivity alerts without role (forbidden)
alerts_no_role_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  "$API_BASE/api/v1/alerts/inactivity?window_minutes=60")"
assert_status "alerts inactivity sin role" "403" "$alerts_no_role_status"

echo ""
echo "Resultado integration: PASS=$PASS_COUNT FAIL=$FAIL_COUNT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi
