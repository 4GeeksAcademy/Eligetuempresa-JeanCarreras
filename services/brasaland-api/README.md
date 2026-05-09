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
- POST /api/v1/sales/events (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/sales/summary?period=week&currency=USD&country=CO&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/sales/by-store?currency=USD&country=US&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/sales/daily-trend?currency=USD&country=US&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/markets/summary?currency=USD&country=CO&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/alerts/inactivity?window_minutes=60&country=CO
- POST /api/v1/alerts/inactivity/actions (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/alerts/inactivity/sla?days=7&sla_target_minutes=30 (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/reports/sales.csv?currency=USD&start_date=2026-05-01&end_date=2026-05-08 (requires `X-API-Role` + `X-API-Token`, roles: `executive`, `finance`, `admin`)
- GET /api/v1/finance/kpis?currency=USD&start_date=2026-05-01&end_date=2026-05-08 (requires `X-API-Role` + `X-API-Token`, roles: `finance`, `executive`, `admin`)
- GET /api/v1/audit/logs?limit=100 (requires `X-API-Role` + `X-API-Token`, role: `admin`)
- GET /api/v1/training/resources?locale=es&q=opening (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/resources/{resource_id} (requires `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)

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

Example: export CSV

```bash
curl "http://localhost:8000/api/v1/reports/sales.csv?currency=USD&start_date=2026-05-01&end_date=2026-05-08" \
  -H "X-API-Role: executive" \
  -H "X-API-Token: brasaland-executive-token" \
  -o sales-report.csv
```

Example: finance KPI

```bash
curl "http://localhost:8000/api/v1/finance/kpis?currency=USD&start_date=2026-05-01&end_date=2026-05-08" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: brasaland-finance-token"
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
