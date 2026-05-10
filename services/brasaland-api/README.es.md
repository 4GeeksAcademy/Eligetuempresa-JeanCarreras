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
- GET /api/v1/menus/items?country=CO&locale=es&currency=COP&active_only=true (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/menus/items (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/sales/events (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/telemetry/events (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/telemetry/stores/status?window_minutes=10&country=CO (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/sales/summary?period=week&currency=USD&country=CO&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/sales/by-store?currency=USD&country=US&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/sales/daily-trend?currency=USD&country=US&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/markets/summary?currency=USD&country=CO&start_date=2026-05-01&end_date=2026-05-08
- GET /api/v1/alerts/inactivity?window_minutes=60&country=CO
- POST /api/v1/alerts/inactivity/actions (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/alerts/inactivity/sla?days=7&sla_target_minutes=30 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/reports/sales.csv?currency=USD&start_date=2026-05-01&end_date=2026-05-08 (requiere `X-API-Role` + `X-API-Token`, roles: `executive`, `finance`, `admin`)
- GET /api/v1/reports/hr.csv?days=90&country=US&section=all (requiere `X-API-Role` + `X-API-Token`, roles: `executive`, `operations`, `admin`)
- GET /api/v1/finance/kpis?currency=USD&start_date=2026-05-01&end_date=2026-05-08 (requiere `X-API-Role` + `X-API-Token`, roles: `finance`, `executive`, `admin`)
- GET /api/v1/audit/logs?limit=100 (requiere `X-API-Role` + `X-API-Token`, rol: `admin`)
- GET /api/v1/training/resources?locale=es&q=apertura (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/resources/{resource_id} (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/recipes/search?q=pollo&locale=es&limit=20 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/onboarding/itineraries?locale=es&limit=20 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/onboarding/itineraries/{itinerary_id} (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/training/onboarding/assign (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/training/recipes/updates?locale=es&limit=20 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/training/recipes/updates/{update_id}/deliveries?limit=50 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/training/recipes/updates/publish (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/training/recipes/updates/{update_id}/acknowledge (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/hr/resources?resource_type=onboarding&locale=es&q=vacaciones (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/hr/resources/{resource_id} (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/hr/employees?employment_status=active&country=US&limit=200 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/hr/time-off/requests?status=pending&country=US&limit=50 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/hr/time-off/requests (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/hr/time-off/requests/{request_id}/action (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/hr/onboarding/cases?status=active&country=US&limit=50 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/hr/onboarding/cases/start (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/hr/onboarding/cases/{case_id}/advance (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/hr/kpis/overview?days=90&country=US (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/executive/ask?question=...&currency=USD (requiere `X-API-Role` + `X-API-Token`, roles: `executive`, `admin`)
- GET /api/v1/executive/weekly-report?currency=USD (requiere `X-API-Role` + `X-API-Token`, roles: `executive`, `admin`)
- GET /api/v1/suppliers/prices?country=CO&currency=USD&limit=100 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/suppliers/price-alerts?country=CO&threshold_pct=5&currency=COP (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/suppliers/purchases/consolidated?days=30&country=CO&currency=COP (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/customers/summary?country=CO (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/customers/{customer_id} (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/customers/{customer_id}/points/adjust (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- POST /api/v1/marketing/orders (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/marketing/crm/overview?days=30&country=CO&currency=COP (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/marketing/crm/customers?country=CO&currency=COP&limit=50 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/marketing/customers/{customer_id}/history?limit=20 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/marketing/personalization/recommendations?customer_id=cus-co-001&currency=COP&limit=5 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/inventory/stock?country=CO&store_id=med-001&limit=100 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- GET /api/v1/orders/recommendations?country=CO&currency=COP&days_history=14&target_days=7&only_at_risk=true (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)
- POST /api/v1/inventory/receipts?days_history=14&target_days=7 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `admin`)
- GET /api/v1/inventory/receipts?country=CO&store_id=med-001&sku=CHICKEN&limit=30&offset=0 (requiere `X-API-Role` + `X-API-Token`, roles: `operations`, `executive`, `admin`)

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

Ejemplo de gestion de menu centralizado:

```bash
curl -X POST http://localhost:8000/api/v1/menus/items \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token" \
	-H "Content-Type: application/json" \
	-d '{
		"id": "menu-co-main-qa-001",
		"country": "CO",
		"sku": "SKU-POLLO-QA",
		"name": "Pollo QA",
		"description": "Item de prueba para menu",
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

Ejemplo de telemetria en tiempo real por local:

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

Ejemplo de exportacion CSV:

```bash
curl "http://localhost:8000/api/v1/reports/sales.csv?currency=USD&start_date=2026-05-01&end_date=2026-05-08" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token" \
	-o sales-report.csv
```

Ejemplo de exportacion CSV RRHH (solicitudes, onboarding y KPIs):

```bash
curl "http://localhost:8000/api/v1/reports/hr.csv?days=90&section=all" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token" \
	-o hr-report.csv
```

Ejemplo de KPI financiero:

```bash
curl "http://localhost:8000/api/v1/finance/kpis?currency=USD&start_date=2026-05-01&end_date=2026-05-08" \
  -H "X-API-Role: finance" \
  -H "X-API-Token: brasaland-finance-token"
```

Ejemplo de accion sobre alerta de inactividad (ACK o RESOLVED):

```bash
curl -X POST "http://localhost:8000/api/v1/alerts/inactivity/actions" \
	-H "Content-Type: application/json" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token" \
	-d '{"store_id":"med-001","status":"acknowledged","owner":"ops-on-duty","note":"Validando POS local"}'
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

Ejemplo de busqueda de recetas estandarizadas:

```bash
curl "http://localhost:8000/api/v1/training/recipes/search?q=pollo&locale=es&limit=10" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token"
```

Ejemplo de publicacion simultanea de update de receta (14 locales):

```bash
curl -X POST "http://localhost:8000/api/v1/training/recipes/updates/publish" \
	-H "Content-Type: application/json" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token" \
	-d '{"resource_id":"rec-brasa-pollo-v1","change_summary":"Ajuste estandar de gramaje por porcion","locale":"es","mandatory":true}'

# Capturar el update_id devuelto para consultas posteriores
UPDATE_ID=$(curl -s "http://localhost:8000/api/v1/training/recipes/updates?locale=es&limit=1" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token" | grep -o '"update_id":[0-9]*' | head -n1 | cut -d: -f2)
```

Ejemplo de acuse (ACK) por local:

```bash
curl -X POST "http://localhost:8000/api/v1/training/recipes/updates/${UPDATE_ID}/acknowledge" \
	-H "Content-Type: application/json" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token" \
	-d '{"store_id":"med-001","acknowledged_by":"kitchen-lead","ack_note":"Receta aplicada en turno AM"}'
```

Ejemplo de recursos RRHH:

```bash
curl "http://localhost:8000/api/v1/hr/resources?resource_type=onboarding&locale=es" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token"
```

Ejemplo de solicitud de vacaciones/ausencias:

```bash
curl -X POST "http://localhost:8000/api/v1/hr/time-off/requests" \
	-H "Content-Type: application/json" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token" \
	-d '{"employee_id":"emp-us-070","request_type":"vacation","start_date":"2026-06-10","end_date":"2026-06-14","reason":"Vacaciones familiares"}'
```

Ejemplo de aprobacion/rechazo de solicitud:

```bash
curl -X POST "http://localhost:8000/api/v1/hr/time-off/requests/1/action" \
	-H "Content-Type: application/json" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token" \
	-d '{"status":"approved","note":"Cobertura validada por manager"}'
```

Ejemplo de onboarding automatizado:

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
	-d '{"step_key":"station_training","note":"Paso completado en turno supervisado"}'
```

Ejemplo de KPIs RRHH por pais:

```bash
curl "http://localhost:8000/api/v1/hr/kpis/overview?days=90" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token"
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

Ejemplo de compras consolidadas para negociacion centralizada:

```bash
curl "http://localhost:8000/api/v1/suppliers/purchases/consolidated?days=30&currency=USD" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token"
```

Ejemplo de ajuste de puntos de fidelizacion:

```bash
curl -X POST "http://localhost:8000/api/v1/customers/cus-co-001/points/adjust" \
	-H "Content-Type: application/json" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token" \
	-d '{"delta_points": 15, "reason": "manual_adjustment"}'
```

Ejemplo de pedido digital (app/web) con acumulacion de Brasa Points:

```bash
curl -X POST "http://localhost:8000/api/v1/marketing/orders" \
	-H "Content-Type: application/json" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token" \
	-d '{"customer_id":"cus-co-001","store_id":"med-001","order_items":["combo_familiar","cola_350"],"total_amount":98000,"currency":"COP","channel":"app"}'
```

Ejemplo de CRM + personalizacion:

```bash
curl "http://localhost:8000/api/v1/marketing/crm/overview?days=30&currency=USD" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token"

curl "http://localhost:8000/api/v1/marketing/personalization/recommendations?customer_id=cus-us-001&currency=USD&limit=5" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token"
```

Ejemplo de stock actual por local:

```bash
curl "http://localhost:8000/api/v1/inventory/stock?country=CO&limit=20" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token"
```

Ejemplo de pedidos inteligentes (historico + stock):

```bash
curl "http://localhost:8000/api/v1/orders/recommendations?country=US&currency=USD&days_history=14&target_days=7&only_at_risk=true" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token"
```

Ejemplo de recepcion de inventario (cierra recomendacion automaticamente si ya no hay riesgo):

```bash
curl -X POST "http://localhost:8000/api/v1/inventory/receipts?days_history=14&target_days=7" \
	-H "Content-Type: application/json" \
	-H "X-API-Role: operations" \
	-H "X-API-Token: brasaland-operations-token" \
	-d '{"store_id":"med-001","sku":"CHICKEN","received_qty":12,"unit_cost":12100,"currency":"COP","note":"recepcion proveedor semanal"}'
```

Ejemplo de consulta de ultimas recepciones:

```bash
curl "http://localhost:8000/api/v1/inventory/receipts?country=CO&store_id=med-001&limit=10&offset=0" \
	-H "X-API-Role: executive" \
	-H "X-API-Token: brasaland-executive-token"
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
