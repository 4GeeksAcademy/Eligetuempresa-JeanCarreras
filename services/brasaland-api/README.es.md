# brasaland-api

API central MVP para Brasaland enfocada en operaciones multipais.

## Alcance inicial

- Endpoint de salud.
- Listado de locales.
- Resumen de ventas en COP o USD.
- Persistencia local con SQLite y datos seed.

## Stack

- Python 3.11+
- FastAPI
- Uvicorn

## Ejecutar local

```bash
cd services/brasaland-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints MVP

- GET /health
- GET /api/v1/stores
- POST /api/v1/sales/events (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/sales/summary?period=week&currency=USD&country=CO&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/sales/by-store?currency=USD&country=US&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/sales/daily-trend?currency=USD&country=US&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/markets/summary?currency=USD&country=CO&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/alerts/inactivity?window_minutes=60&country=CO
- POST /api/v1/alerts/inactivity/actions (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/alerts/inactivity/sla?days=7&sla_target_minutes=30 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/reports/sales.csv?currency=USD&start_date=2026-05-01&end_date=2026-05-08 (requiere `X-API-Role` + `X-API-Token`, roles: `executive`, `finance`, `admin`)
- GET /api/v1/finance/kpis?currency=USD&start_date=2026-05-01&end_date=2026-05-08 (requiere `X-API-Role` + `X-API-Token`, roles: `finance`, `executive`, `admin`)
- GET /api/v1/audit/logs?limit=100 (requiere `X-API-Role` + `X-API-Token`, rol: `admin`)
- GET /api/v1/training/resources?locale=es&q=apertura (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/resources/{resource_id} (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/hr/resources?resource_type=onboarding&locale=es&q=vacaciones (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/hr/resources/{resource_id} (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/executive/ask?question=...&currency=USD (requiere `X-API-Role` + `X-API-Token`, roles: `executive`, `admin`)
- GET /api/v1/executive/weekly-report?currency=USD (requiere `X-API-Role` + `X-API-Token`, roles: `executive`, `admin`)
- GET /api/v1/suppliers/prices?country=CO&currency=USD&limit=100 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/suppliers/price-alerts?country=CO&threshold_pct=5&currency=COP (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)

Ejemplo de creacion de venta:

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

Ejemplo de exportacion CSV:

```bash
curl "http://localhost:8000/api/v1/reports/sales.csv?currency=USD&start_date=2026-05-01&end_date=2026-05-08" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token" \
	-o sales-report.csv
```

Ejemplo de KPI financiero:

```bash
curl "http://localhost:8000/api/v1/finance/kpis?currency=USD&start_date=2026-05-01&end_date=2026-05-08" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: brasaland-finance-token"
```

Ejemplo de auditoria:

```bash
curl "http://localhost:8000/api/v1/audit/logs?limit=50" \
	-H "X-API-Role: admin" \
	-H "X-API-Token: brasaland-admin-token"
```

Ejemplo de catalogo de formacion:

```bash
curl "http://localhost:8000/api/v1/training/resources?locale=es&q=apertura" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token"
```

Ejemplo de recursos RRHH:

```bash
curl "http://localhost:8000/api/v1/hr/resources?resource_type=onboarding&locale=es" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token"
```

Ejemplo de consulta ejecutiva en lenguaje natural:

```bash
curl "http://localhost:8000/api/v1/executive/ask?question=Cuanto%20vendimos%20esta%20semana%20en%20Florida%20vs%20Colombia%3F&currency=USD" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token"
```

Ejemplo de alertas de variacion de precio de proveedores:

```bash
curl "http://localhost:8000/api/v1/suppliers/price-alerts?country=CO&threshold_pct=5&currency=COP" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token"
```

## Siguiente iteracion

- Persistencia real de ventas y eventos.
- Integracion de telemetria por local.
- Autenticacion para endpoints internos.

## Smoke tests reproducibles

Auto-contenido (si la API no esta corriendo, el script la levanta localmente):

```bash
bash workflows/scripts/smoke_api.sh
```

Si quieres usar otra URL o rango:

```bash
API_BASE=http://localhost:8000 CURRENCY=USD START_DATE=2026-05-01 END_DATE=2026-05-08 bash workflows/scripts/smoke_api.sh
```

## Integracion reproducible

Suite funcional de endpoints/filtros/permisos:

```bash
bash workflows/scripts/integration_api.sh
```

Suite de casos borde de datos y validaciones:

```bash
bash workflows/scripts/integration_data_api.sh
```

## Notas de integracion

- El dashboard `uis/executive-dashboard` consume directamente estos endpoints sobre `http://localhost:8000`.
- La base de datos se crea automaticamente en `services/brasaland-api/brasaland.db` al iniciar la API.
- Se registra auditoria automatica para acciones sensibles (creacion de ventas, exportaciones y consultas financieras).
- Tokens por defecto para desarrollo:
	- `admin`: `brasaland-admin-token`
	- `executive`: `brasaland-executive-token`
	- `operations`: `brasaland-operations-token`
	- `finance`: `brasaland-finance-token`
- Variables de entorno recomendadas en produccion:
	- `BRASALAND_ADMIN_TOKEN`
	- `BRASALAND_EXECUTIVE_TOKEN`
	- `BRASALAND_OPERATIONS_TOKEN`
	- `BRASALAND_FINANCE_TOKEN`
