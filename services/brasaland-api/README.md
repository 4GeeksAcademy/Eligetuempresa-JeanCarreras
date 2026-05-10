# brasaland-api

MVP central API for Brasaland focused on multi-country operations.

## Initial scope

- Health endpoint.
- Stores listing.
- Sales summary in COP or USD.
- Local persistence with SQLite and seed data.

## Stack

- Python 3.11+
- FastAPI
- Uvicorn

## Run locally

```bash
cd services/brasaland-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## MVP endpoints

- GET /health
- GET /api/v1/stores
- GET /api/v1/menus/items?country=CO&locale=es&currency=COP&active_only=true (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/menus/items (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/sales/events (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/telemetry/events (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/telemetry/stores/status?window_minutes=10&country=CO (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/sales/summary?period=week&currency=USD&country=CO&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/sales/by-store?currency=USD&country=US&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/sales/daily-trend?currency=USD&country=US&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/markets/summary?currency=USD&country=CO&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/alerts/inactivity?window_minutes=60&country=CO
- POST /api/v1/alerts/inactivity/actions (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/alerts/inactivity/sla?days=7&sla_target_minutes=30 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/reports/sales.csv?currency=USD&start_date=2026-05-01&end_date=2026-05-08 (requires `X-API-Role` + `X-API-Token`, roles: `executive`, `finance`, `admin`)
- GET /api/v1/reports/hr.csv?days=90&country=US&section=all (requires `X-API-Role` + `X-API-Token`, roles: `executive`, `operations`, `admin`)
- GET /api/v1/finance/kpis?currency=USD&start_date=2026-05-01&end_date=2026-05-08 (requires `X-API-Role` + `X-API-Token`, roles: `finance`, `executive`, `admin`)
- GET /api/v1/audit/logs?limit=100 (requires `X-API-Role` + `X-API-Token`, role: `admin`)
- GET /api/v1/training/resources?locale=es&q=opening (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/resources/{resource_id} (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/recipes/search?q=chicken&locale=en&limit=20 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/onboarding/itineraries?locale=en&limit=20 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/onboarding/itineraries/{itinerary_id} (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/training/onboarding/assign (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/training/recipes/updates?locale=en&limit=20 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/recipes/updates/{update_id}/deliveries?limit=50 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/training/recipes/updates/publish (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/training/recipes/updates/{update_id}/acknowledge (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/hr/resources?resource_type=onboarding&locale=es&q=vacation (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/hr/resources/{resource_id} (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/hr/employees?employment_status=active&country=US&limit=200 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/hr/time-off/requests?status=pending&country=US&limit=50 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/hr/time-off/requests (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/hr/time-off/requests/{request_id}/action (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/hr/onboarding/cases?status=active&country=US&limit=50 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/hr/onboarding/cases/start (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/hr/onboarding/cases/{case_id}/advance (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/hr/kpis/overview?days=90&country=US (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/executive/ask?question=...&currency=USD (requires `X-API-Role` + `X-API-Token`, roles: `executive`, `admin`)
- GET /api/v1/executive/weekly-report?currency=USD (requires `X-API-Role` + `X-API-Token`, roles: `executive`, `admin`)
- GET /api/v1/suppliers/prices?country=CO&currency=USD&limit=100 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/suppliers/price-alerts?country=CO&threshold_pct=5&currency=COP (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/suppliers/purchases/consolidated?days=30&country=CO&currency=COP (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/customers/summary?country=CO (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/customers/{customer_id} (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/customers/{customer_id}/points/adjust (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/marketing/orders (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/marketing/crm/overview?days=30&country=CO&currency=COP (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/marketing/crm/customers?country=CO&currency=COP&limit=50 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/marketing/customers/{customer_id}/history?limit=20 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/marketing/personalization/recommendations?customer_id=cus-co-001&currency=COP&limit=5 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)

Example: create sale event

```bash
curl -X POST http://localhost:8000/api/v1/sales/events \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": "mia-001",
    "sold_at": "2026-05-08T17:40:00Z",
    "total_amount": 24.5,
    "currency": "USD"
  }'
```

Example: centralized menu management

```bash
curl -X POST http://localhost:8000/api/v1/menus/items \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "menu-co-main-qa-001",
    "country": "CO",
    "sku": "SKU-POLLO-QA",
    "name": "QA Chicken",
    "description": "Menu QA test item",
    "category": "main",
    "price_amount": 45900,
    "currency": "COP",
    "locale": "es",
    "is_active": true
  }'

curl "http://localhost:8000/api/v1/menus/items?country=CO&locale=es&currency=COP" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token"
```

Example: real-time store telemetry

```bash
curl -X POST http://localhost:8000/api/v1/telemetry/events \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": "med-001",
    "source_system": "pos",
    "event_ts": "2026-05-10T22:00:00Z",
    "pos_online": true,
    "sales_last_5m": 3,
    "open_tickets": 2,
    "avg_prep_seconds": 420,
    "network_rtt_ms": 33,
    "terminal_version": "pos-v2.1"
  }'

curl "http://localhost:8000/api/v1/telemetry/stores/status?window_minutes=10" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token"
```

Example: export CSV

```bash
curl "http://localhost:8000/api/v1/reports/sales.csv?currency=USD&start_date=2026-05-01&end_date=2026-05-08" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token" \
  -o sales-report.csv
```

Example: HR CSV export (requests, onboarding, and KPIs)

```bash
curl "http://localhost:8000/api/v1/reports/hr.csv?days=90&section=all" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token" \
  -o hr-report.csv
```

Example: finance KPI

```bash
curl "http://localhost:8000/api/v1/finance/kpis?currency=USD&start_date=2026-05-01&end_date=2026-05-08" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: brasaland-finance-token"
```

Example: inactivity alert action (ACK or RESOLVED)

```bash
curl -X POST "http://localhost:8000/api/v1/alerts/inactivity/actions" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{"store_id":"med-001","status":"acknowledged","owner":"ops-on-duty","note":"Checking local POS"}'
```

Example: audit logs

```bash
curl "http://localhost:8000/api/v1/audit/logs?limit=50" \
  -H "X-API-Role: admin" \
  -H "X-API-Token: brasaland-admin-token"
```

Example: training catalog

```bash
curl "http://localhost:8000/api/v1/training/resources?locale=es&q=opening" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token"
```

Example: standardized recipe search

```bash
curl "http://localhost:8000/api/v1/training/recipes/search?q=chicken&locale=en&limit=10" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token"
```

Example: chain-wide recipe update publish (14 stores)

```bash
curl -X POST "http://localhost:8000/api/v1/training/recipes/updates/publish" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{"resource_id":"rec-brasa-pollo-v1","change_summary":"Standard serving-gram update","locale":"en","mandatory":true}'

# Capture returned update_id for follow-up calls
UPDATE_ID=$(curl -s "http://localhost:8000/api/v1/training/recipes/updates?locale=en&limit=1" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token" | grep -o '"update_id":[0-9]*' | head -n1 | cut -d: -f2)
```

Example: per-store acknowledgment (ACK)

```bash
curl -X POST "http://localhost:8000/api/v1/training/recipes/updates/${UPDATE_ID}/acknowledge" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{"store_id":"med-001","acknowledged_by":"kitchen-lead","ack_note":"Update validated in AM shift"}'
```

Example: HR resources

```bash
curl "http://localhost:8000/api/v1/hr/resources?resource_type=onboarding&locale=es" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token"
```

Example: time-off request (vacation/absence)

```bash
curl -X POST "http://localhost:8000/api/v1/hr/time-off/requests" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{"employee_id":"emp-us-070","request_type":"vacation","start_date":"2026-06-10","end_date":"2026-06-14","reason":"Family vacation"}'
```

Example: approve/reject request

```bash
curl -X POST "http://localhost:8000/api/v1/hr/time-off/requests/1/action" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{"status":"approved","note":"Manager coverage validated"}'
```

Example: automated onboarding flow

```bash
curl -X POST "http://localhost:8000/api/v1/hr/onboarding/cases/start" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{"employee_id":"emp-us-082","position_title":"Prep Cook","mentor_name":"Ashley Turner"}'

curl -X POST "http://localhost:8000/api/v1/hr/onboarding/cases/1/advance" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{"step_key":"station_training","note":"Step completed in supervised shift"}'
```

Example: HR KPI dashboard by country

```bash
curl "http://localhost:8000/api/v1/hr/kpis/overview?days=90" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token"
```

Example: executive natural-language query

```bash
curl "http://localhost:8000/api/v1/executive/ask?question=How%20much%20did%20we%20sell%20this%20week%20in%20Florida%20vs%20Colombia%3F&currency=USD" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token"
```

Example: supplier price variation alerts

```bash
curl "http://localhost:8000/api/v1/suppliers/price-alerts?country=CO&threshold_pct=5&currency=COP" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token"
```

Example: consolidated purchases for centralized negotiations

```bash
curl "http://localhost:8000/api/v1/suppliers/purchases/consolidated?days=30&currency=USD" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token"
```

Example: loyalty points adjustment

```bash
curl -X POST "http://localhost:8000/api/v1/customers/cus-co-001/points/adjust" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{"delta_points": 15, "reason": "manual_adjustment"}'
```

Example: digital app/web order with Brasa Points accumulation

```bash
curl -X POST "http://localhost:8000/api/v1/marketing/orders" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{"customer_id":"cus-co-001","store_id":"med-001","order_items":["family_combo","cola_350"],"total_amount":98000,"currency":"COP","channel":"app"}'
```

Example: CRM + personalization

```bash
curl "http://localhost:8000/api/v1/marketing/crm/overview?days=30&currency=USD" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token"

curl "http://localhost:8000/api/v1/marketing/personalization/recommendations?customer_id=cus-us-001&currency=USD&limit=5" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token"
```

## Next iteration

- Real persistence for sales and events.
- Store-level telemetry integration.
- Authentication hardening for internal endpoints.

## Reproducible smoke tests

Self-contained (if API is not running, the script starts it locally):

```bash
bash workflows/scripts/smoke_api.sh
```

If you want a different base URL or date range:

```bash
API_BASE=http://localhost:8000 CURRENCY=USD START_DATE=2026-05-01 END_DATE=2026-05-08 bash workflows/scripts/smoke_api.sh
```

## Reproducible integration

Functional suite for endpoints/filters/permissions:

```bash
bash workflows/scripts/integration_api.sh
```

Data edge-case and validation suite:

```bash
bash workflows/scripts/integration_data_api.sh
```

## Integration notes

- The dashboard in `uis/executive-dashboard` consumes these endpoints directly from `http://localhost:8000`.
- The database is created automatically at `services/brasaland-api/brasaland.db` when the API starts.
- Audit logs are automatically recorded for sensitive actions (sale creation, exports, finance reads).
- Default development tokens:
  - `admin`: `brasaland-admin-token`
  - `executive`: `brasaland-executive-token`
  - `operations`: `brasaland-operations-token`
  - `finance`: `brasaland-finance-token`
- Recommended production environment variables:
  - `BRASALAND_ADMIN_TOKEN`
  - `BRASALAND_EXECUTIVE_TOKEN`
  - `BRASALAND_OPERATIONS_TOKEN`
  - `BRASALAND_FINANCE_TOKEN`
