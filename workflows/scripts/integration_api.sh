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
total_stores_count="$(grep -o '"id"' <<<"$stores_body" | wc -l | tr -d ' ')"

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
assert_contains "alerts inactivity timezone" '"store_timezone"' "$alerts_exec_body"
assert_contains "alerts inactivity resumen" '"critical_alerts"' "$alerts_exec_body"
assert_contains "alerts inactivity ratio" '"critical_ratio_pct"' "$alerts_exec_body"
assert_contains "alerts inactivity nivel" '"risk_level"' "$alerts_exec_body"
assert_contains "alerts inactivity estado" '"alert_status"' "$alerts_exec_body"

# 11) create alert action with operations role (allowed)
alert_action_payload='{"store_id":"med-001","status":"acknowledged","owner":"ops-on-duty","note":"Investigando causa local"}'
alert_action_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/api/v1/alerts/inactivity/actions" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  -d "$alert_action_payload")"
assert_status "create alert action operations" "201" "$alert_action_status"

alerts_ops_body="$(curl -fsS \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/alerts/inactivity?window_minutes=15")"
assert_contains "alerts inactivity refleja estado" '"alert_status":"acknowledged"' "$alerts_ops_body"

# 12) create alert action with executive role (forbidden)
alert_action_exec_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/api/v1/alerts/inactivity/actions" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  -d "$alert_action_payload")"
assert_status "create alert action executive prohibido" "403" "$alert_action_exec_status"

# 13) inactivity alerts without role (forbidden)
alerts_no_role_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  "$API_BASE/api/v1/alerts/inactivity?window_minutes=60")"
assert_status "alerts inactivity sin role" "403" "$alerts_no_role_status"

# 15.1) alerts inactivity respects opening hours with deterministic reference time
alerts_opening_hours_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/alerts/inactivity?window_minutes=60&opening_hours_only=true&reference_at=2026-05-09T08:30:00Z")"
assert_contains "alerts inactivity horario apertura" '"total_stores":0' "$alerts_opening_hours_body"

alerts_opening_hours_disabled_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/alerts/inactivity?window_minutes=60&opening_hours_only=false&reference_at=2026-05-09T08:30:00Z")"
assert_contains "alerts inactivity sin filtro horario" "\"total_stores\":$total_stores_count" "$alerts_opening_hours_disabled_body"

# 14) alerts SLA with executive role (allowed)
alerts_sla_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/alerts/inactivity/sla?days=7&sla_target_minutes=30")"
assert_status "alerts sla con executive" "200" "$alerts_sla_status"

alerts_sla_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/alerts/inactivity/sla?days=7&sla_target_minutes=30")"
assert_contains "alerts sla payload" '"resolved_within_sla_pct"' "$alerts_sla_body"

# 15) alerts SLA without role (forbidden)
alerts_sla_no_role_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  "$API_BASE/api/v1/alerts/inactivity/sla?days=7")"
assert_status "alerts sla sin role" "403" "$alerts_sla_no_role_status"

# 16) training resources with operations role (allowed)
training_list_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/training/resources?locale=es&limit=10")"
assert_status "training resources operations" "200" "$training_list_status"

training_list_body="$(curl -fsS \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/training/resources?locale=es&q=apertura")"
assert_contains "training resources payload" '"category"' "$training_list_body"

# 17) training resource detail with operations role (allowed)
training_detail_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/training/resources/sop-apertura-cocina-v1")"
assert_status "training detail operations" "200" "$training_detail_status"

# 18) training resources with finance role (forbidden)
training_finance_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: $FIN_TOKEN" \
  "$API_BASE/api/v1/training/resources")"
assert_status "training resources finance prohibido" "403" "$training_finance_status"

# 19) HR resources with operations role (allowed)
hr_list_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/hr/resources?resource_type=onboarding&locale=es")"
assert_status "hr resources operations" "200" "$hr_list_status"

hr_list_body="$(curl -fsS \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/hr/resources?q=vacaciones")"
assert_contains "hr resources payload" '"resource_type"' "$hr_list_body"

# 20) HR resource detail with executive role (allowed)
hr_detail_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/hr/resources/hr-pol-vacaciones-001")"
assert_status "hr detail executive" "200" "$hr_detail_status"

# 21) HR resources with finance role (forbidden)
hr_finance_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: $FIN_TOKEN" \
  "$API_BASE/api/v1/hr/resources")"
assert_status "hr resources finance prohibido" "403" "$hr_finance_status"

# 22) supplier prices with operations role (allowed)
supplier_prices_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/suppliers/prices?country=CO&currency=USD&limit=10")"
assert_status "supplier prices operations" "200" "$supplier_prices_status"

supplier_prices_body="$(curl -fsS \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/suppliers/prices?country=US&currency=USD&limit=10")"
assert_contains "supplier prices payload" '"supplier_id"' "$supplier_prices_body"

# 23) supplier price alerts with executive role (allowed)
supplier_alerts_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/suppliers/price-alerts?country=CO&threshold_pct=5&currency=COP")"
assert_status "supplier alerts executive" "200" "$supplier_alerts_status"

supplier_alerts_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/suppliers/price-alerts?country=US&threshold_pct=5&currency=USD")"
assert_contains "supplier alerts payload" '"change_pct"' "$supplier_alerts_body"

# 24) supplier endpoints with finance role (forbidden)
supplier_prices_finance_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: $FIN_TOKEN" \
  "$API_BASE/api/v1/suppliers/prices")"
assert_status "supplier prices finance prohibido" "403" "$supplier_prices_finance_status"

# 25) supplier alerts without role (forbidden)
supplier_alerts_no_role_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  "$API_BASE/api/v1/suppliers/price-alerts")"
assert_status "supplier alerts sin role" "403" "$supplier_alerts_no_role_status"

# 26) customers summary with executive role (allowed)
customers_summary_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/customers/summary")"
assert_status "customers summary executive" "200" "$customers_summary_status"

customers_summary_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/customers/summary?country=CO")"
assert_contains "customers summary payload" '"total_customers"' "$customers_summary_body"

# 27) customer profile with operations role (allowed)
customer_profile_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/customers/cus-co-001")"
assert_status "customer profile operations" "200" "$customer_profile_status"

# 28) adjust points with operations role (allowed)
adjust_points_payload='{"delta_points":15,"reason":"manual_adjustment_test"}'
adjust_points_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/api/v1/customers/cus-co-001/points/adjust" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  -d "$adjust_points_payload")"
assert_status "adjust points operations" "200" "$adjust_points_status"

# 29) adjust points with executive role (forbidden)
adjust_points_exec_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/api/v1/customers/cus-co-001/points/adjust" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  -d "$adjust_points_payload")"
assert_status "adjust points executive prohibido" "403" "$adjust_points_exec_status"

# 30) inventory stock with operations role (allowed)
inventory_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/inventory/stock?country=CO&limit=10")"
assert_status "inventory stock operations" "200" "$inventory_status"

inventory_body="$(curl -fsS \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/inventory/stock?country=US&limit=10")"
assert_contains "inventory stock payload" '"current_stock"' "$inventory_body"

# 31) smart order recommendations with executive role (allowed)
smart_orders_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/orders/recommendations?country=CO&currency=COP&days_history=14&target_days=7")"
assert_status "smart orders executive" "200" "$smart_orders_status"

smart_orders_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/orders/recommendations?country=US&currency=USD&days_history=14&target_days=7")"
assert_contains "smart orders payload" '"recommended_order_qty"' "$smart_orders_body"
assert_contains "smart orders risk" '"risk_level"' "$smart_orders_body"
assert_contains "smart orders trazabilidad" '"days_history"' "$smart_orders_body"

# 32) smart order recommendations without role (forbidden)
smart_orders_no_role_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  "$API_BASE/api/v1/orders/recommendations?country=CO")"
assert_status "smart orders sin role" "403" "$smart_orders_no_role_status"

# 33) inventory receipt with operations role (allowed) and recommendation auto-close
inventory_receipt_payload='{"store_id":"med-001","sku":"CHICKEN","received_qty":5,"unit_cost":12100,"currency":"COP","note":"recepcion central"}'
inventory_receipt_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/api/v1/inventory/receipts?days_history=14&target_days=7" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  -d "$inventory_receipt_payload")"
assert_status "inventory receipt operations" "201" "$inventory_receipt_status"

inventory_receipt_body="$(curl -fsS \
  -X POST "$API_BASE/api/v1/inventory/receipts?days_history=14&target_days=7" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  -d '{"store_id":"med-001","sku":"CHICKEN","received_qty":1,"currency":"COP"}')"
assert_contains "inventory receipt payload" '"recommendation_after"' "$inventory_receipt_body"
assert_contains "inventory receipt cierre" '"recommendation_status":"closed"' "$inventory_receipt_body"

# 34) inventory receipt with executive role (forbidden)
inventory_receipt_exec_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/api/v1/inventory/receipts" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  -d '{"store_id":"med-001","sku":"CHICKEN","received_qty":1,"currency":"COP"}')"
assert_status "inventory receipt executive prohibido" "403" "$inventory_receipt_exec_status"

# 35) inventory receipts list with executive role (allowed)
inventory_receipts_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/inventory/receipts?country=CO&limit=10")"
assert_status "inventory receipts list executive" "200" "$inventory_receipts_status"

inventory_receipts_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/inventory/receipts?store_id=med-001&sku=CHICKEN&limit=10")"
assert_contains "inventory receipts payload" '"received_qty"' "$inventory_receipts_body"

inventory_receipts_offset_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/inventory/receipts?store_id=med-001&limit=5&offset=1")"
assert_status "inventory receipts offset" "200" "$inventory_receipts_offset_status"

# 36) inventory receipts list without role (forbidden)
inventory_receipts_no_role_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  "$API_BASE/api/v1/inventory/receipts?limit=5")"
assert_status "inventory receipts list sin role" "403" "$inventory_receipts_no_role_status"

# 22) executive ask with executive role (allowed)
exec_ask_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/executive/ask?question=Cuanto%20vendimos%20esta%20semana%20en%20Florida%20vs%20Colombia%3F&currency=USD")"
assert_status "executive ask executive" "200" "$exec_ask_status"

exec_ask_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/executive/ask?question=Cual%20es%20el%20riesgo%20actual%20de%20inactividad%3F")"
assert_contains "executive ask payload" '"sources"' "$exec_ask_body"

exec_ask_florida_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/executive/ask?question=Cuanto%20vendimos%20esta%20semana%20en%20Florida%3F&currency=USD")"
assert_contains "executive ask florida regla" '"rule:sales_week_country_single"' "$exec_ask_florida_body"

exec_ask_chain_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/executive/ask?question=Cuanto%20vendimos%20esta%20semana%3F&currency=USD")"
assert_contains "executive ask cadena regla" '"rule:sales_week_chain_total"' "$exec_ask_chain_body"

# 23) executive ask with operations role (forbidden)
exec_ask_ops_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/executive/ask?question=Cuanto%20vendimos%3F")"
assert_status "executive ask operations prohibido" "403" "$exec_ask_ops_status"

# 24) executive weekly report with executive role (allowed)
weekly_report_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/executive/weekly-report?currency=USD")"
assert_status "executive weekly report" "200" "$weekly_report_status"

weekly_report_body="$(curl -fsS \
  -H "X-API-Role: executive" \
  -H "X-API-Token: $EXEC_TOKEN" \
  "$API_BASE/api/v1/executive/weekly-report?currency=USD")"
assert_contains "executive weekly report payload" '"alerts_sla"' "$weekly_report_body"

# 25) executive weekly report with operations role (forbidden)
weekly_report_ops_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: $OPS_TOKEN" \
  "$API_BASE/api/v1/executive/weekly-report?currency=USD")"
assert_status "executive weekly report operations prohibido" "403" "$weekly_report_ops_status"

echo ""
echo "Resultado integration: PASS=$PASS_COUNT FAIL=$FAIL_COUNT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi
