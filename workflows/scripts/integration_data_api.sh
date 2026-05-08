#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_BASE="${API_BASE:-http://localhost:8000}"

ADMIN_TOKEN="${BRASALAND_ADMIN_TOKEN:-brasaland-admin-token}"
OPS_TOKEN="${BRASALAND_OPERATIONS_TOKEN:-brasaland-operations-token}"

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

  echo "Levantando API local para integration-data tests..."
  (
    cd "$ROOT_DIR/services/brasaland-api"
    "$py_bin" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >/tmp/uvicorn-integration-data.log 2>&1
  ) &
  SERVER_PID=$!

  for _ in {1..30}; do
    if is_api_up; then
      echo "API lista para pruebas de datos"
      return 0
    fi
    sleep 1
  done

  echo "La API no inicio a tiempo"
  cat /tmp/uvicorn-integration-data.log || true
  exit 1
}

echo "== Integration Data API Brasaland =="
ensure_api_running

# 1) Invalid date format should return 400
invalid_date_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  "$API_BASE/api/v1/sales/summary?period=week&currency=USD&start_date=2026/05/01&end_date=2026-05-08")"
assert_status "sales summary fecha invalida" "400" "$invalid_date_status"

# 2) End date before start date should return 400
range_error_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  "$API_BASE/api/v1/sales/summary?period=week&currency=USD&start_date=2026-05-08&end_date=2026-05-01")"
assert_status "sales summary rango invalido" "400" "$range_error_status"

# 3) Empty future range should return 200 with total 0
future_summary="$(curl -fsS \
  "$API_BASE/api/v1/sales/summary?period=week&currency=USD&start_date=2100-01-01&end_date=2100-01-07")"
assert_contains "sales summary rango futuro" '"total_sales":0' "$future_summary"

# 4) Create sales event with unknown store should return 404
unknown_store_payload='{"store_id":"zzz-404","sold_at":"2026-05-08T12:00:00Z","total_amount":20.5,"currency":"USD"}'
unknown_store_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/api/v1/sales/events" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  -d "$unknown_store_payload")"
assert_status "create sale store inexistente" "404" "$unknown_store_status"

# 5) Create sales event with negative amount should return 400
negative_amount_payload='{"store_id":"mia-001","sold_at":"2026-05-08T12:00:00Z","total_amount":-1,"currency":"USD"}'
negative_amount_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/api/v1/sales/events" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  -d "$negative_amount_payload")"
assert_status "create sale amount negativo" "400" "$negative_amount_status"

# 6) Audit logs with admin role should still be accessible
audit_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: admin" \
  -H "X-API-Token: $ADMIN_TOKEN" \
  "$API_BASE/api/v1/audit/logs?limit=20")"
assert_status "audit logs admin" "200" "$audit_status"

echo ""
echo "Resultado integration-data: PASS=$PASS_COUNT FAIL=$FAIL_COUNT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi
