# Proyecto de Compañía - Ingeniería de IA — Plantilla para estudiantes

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
[![Smoke API](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/smoke-api.yml/badge.svg)](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/smoke-api.yml)
[![Integration API](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/integration-api.yml/badge.svg)](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/integration-api.yml)
[![Integration Data API](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/integration-data-api.yml/badge.svg)](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/integration-data-api.yml)

_Plantilla base para proyectos transversales del Programa de Carrera en Ingeniería de IA — 4Geeks Academy._

_Las instrucciones están [disponibles en inglés](./README.md)._

---

## Propósito

Este repositorio es la **plantilla de inicio** para los proyectos transversales. Trabajarás con escenarios de empresas reales (Brasaland, TrackFlow, Nexova) construyendo entregables que se corresponden con los hitos del curso (Web, Programación, Backend, Telemetría, RAG, Agentes, Workflows, Tiempo real).

- Crea una plantilla a partir de este repositorio.
- Reemplaza el `CONTEXT.md` placeholder por el contexto de tu empresa asignada.
- Usa `skills/` y los `README.md` por carpeta como guía de trabajo.

---

## Estado actual de la plantilla

Actualmente el repositorio ofrece una **estructura base de carpetas y documentación** con una primera base funcional orientada a Brasaland.

- `CONTEXT.md` ya contiene el contexto de Brasaland.
- Existe un `AGENTS.md` en la raíz con guardrails y prioridades de agentes.
- Se añadieron entregables iniciales en `docs/`, `workflows/`, `services/brasaland-api/` y `uis/executive-dashboard/`.
- Existe metadata del paquete compartido en `packages/shared/package.json` (`@repo/shared-types`), pero aún no hay runner de workspace en raíz.

## Novedades recientes

- API MVP operativa en `services/brasaland-api/` con endpoints de ventas, mercados, finanzas, export CSV y auditoría.
- Dashboard ejecutivo MVP en `uis/executive-dashboard/` conectado al API local y con modo demo fallback.
- Suite QA reproducible y auto-contenida:
	- `workflows/scripts/smoke_api.sh`
	- `workflows/scripts/integration_api.sh`
	- `workflows/scripts/integration_data_api.sh`
- CI encadenada en GitHub Actions:
	- `Smoke API` -> `Integration API` -> `Integration Data API`
- Documentación ES/EN alineada en README raíz, `services/`, `uis/`, `workflows/` y submódulos principales.
- Nueva interfaz web mobile-first de fidelización y pedidos en `uis/marketing-loyalty-app/` (integrada con endpoints de Marketing).
- Nuevo bloque RRHH con portal interno, onboarding automatizado y KPIs por pais en API + dashboard ejecutivo.

## Tablero de cumplimiento - Operaciones (Brasaland)

Estado objetivo para Felipe Guerrero (14 locales):

| Capacidad requerida | Estado | Evidencia tecnica |
| ---- | ---- | ---- |
| Dashboard de ventas en tiempo real por local (COP y USD) | Listo | `uis/executive-dashboard/app.js` (consumo de `/sales/summary`, `/sales/by-store`, `/sales/daily-trend`, filtros y auto-refresh) |
| Sistema inteligente de pedidos (historico + stock actual) | Listo | `services/brasaland-api/src/main.py` (`/api/v1/orders/recommendations`) + `uis/executive-dashboard/app.js` |
| Alertas automaticas por local sin ventas en horario de apertura | Listo | `services/brasaland-api/src/main.py` (`/api/v1/alerts/inactivity`, `STORE_OPENING_HOURS`) + acciones ACK/RESOLVER en `uis/executive-dashboard/app.js` |
| Cobertura de cadena (14 locales) | Listo | `services/brasaland-api/src/main.py` (seed de 14 locales + backfill de ventas y stock por local) |

Validacion rapida local:

```bash
# 1) Levantar API
bash scripts/run_api_local.sh

# 2) Smoke base
bash workflows/scripts/smoke_api.sh

# 3) Confirmar 14 locales
curl -s http://localhost:8000/api/v1/stores | grep -o '"id"' | wc -l

# 4) Confirmar alertas en horario de apertura
curl -s 'http://localhost:8000/api/v1/alerts/inactivity?window_minutes=60&opening_hours_only=true&limit=50' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 5) Confirmar recomendaciones de pedidos
curl -s 'http://localhost:8000/api/v1/orders/recommendations?days_history=14&target_days=7&only_at_risk=false&limit=200&country=CO&currency=COP' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'
```

## Tablero de cumplimiento - Compras y Proveedores (Brasaland)

Estado objetivo para Lucia Fernandez:

| Capacidad requerida | Estado | Evidencia tecnica |
| ---- | ---- | ---- |
| Historial de precios por proveedor y SKU (CO + US) | Listo | `services/brasaland-api/src/main.py` (`/api/v1/suppliers/prices`) |
| Alertas por variacion de precio configurable por umbral | Listo | `services/brasaland-api/src/main.py` (`/api/v1/suppliers/price-alerts?threshold_pct=...`) |
| Cobertura multipais y multimoneda (COP/USD) | Listo | Filtros `country` + `currency` en endpoints de proveedores |
| Consola visual centralizada para Compras | Listo | Panel dedicado en `uis/executive-dashboard` conectado a `/api/v1/suppliers/prices`, `/api/v1/suppliers/price-alerts` y `/api/v1/suppliers/purchases/consolidated` |

Validacion rapida local:

```bash
# 1) Historial de precios Colombia (COP)
curl -s 'http://localhost:8000/api/v1/suppliers/prices?country=CO&currency=COP&limit=20' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token'

# 2) Alertas de variacion de precio Colombia
curl -s 'http://localhost:8000/api/v1/suppliers/price-alerts?country=CO&threshold_pct=5&currency=COP' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token'

# 3) Historial de precios Florida (USD)
curl -s 'http://localhost:8000/api/v1/suppliers/prices?country=US&currency=USD&limit=20' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 4) Consolidado de compras cadena (30 dias)
curl -s 'http://localhost:8000/api/v1/suppliers/purchases/consolidated?days=30&currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'
```

## Tablero de cumplimiento - Marketing y experiencia digital (Brasaland)

Estado objetivo para Camila Ospina:

| Capacidad requerida | Estado | Evidencia tecnica |
| ---- | ---- | ---- |
| App digital de fidelizacion y pedidos | Listo | `POST /api/v1/marketing/orders` con acumulacion automatica de Brasa Points + interfaz dedicada en `uis/marketing-loyalty-app/` |
| CRM de clientes con historial de pedidos y preferencias | Listo | `GET /api/v1/marketing/crm/overview`, `GET /api/v1/marketing/crm/customers`, `GET /api/v1/marketing/customers/{customer_id}/history` |
| Motor de personalizacion por comportamiento | Listo | `GET /api/v1/marketing/personalization/recommendations` + panel de Marketing en `uis/executive-dashboard` |

Validacion rapida local:

```bash
# 1) App de pedidos/fidelizacion
curl -X POST 'http://localhost:8000/api/v1/marketing/orders' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"customer_id":"cus-co-001","store_id":"med-001","order_items":["combo_familiar","cola_350"],"total_amount":98000,"currency":"COP","channel":"app"}'

# 2) CRM consolidado de clientes
curl -s 'http://localhost:8000/api/v1/marketing/crm/overview?days=30&currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 3) Personalizacion por comportamiento
curl -s 'http://localhost:8000/api/v1/marketing/personalization/recommendations?customer_id=cus-us-001&currency=USD&limit=5' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'
```

## Tablero de cumplimiento - Personas y cultura (Brasaland)

Estado objetivo para Ashley Turner:

| Capacidad requerida | Estado | Evidencia tecnica |
| ---- | ---- | ---- |
| Portal interno RRHH para vacaciones y gestion de ausencias | Listo | `POST /api/v1/hr/time-off/requests`, `GET /api/v1/hr/time-off/requests`, `POST /api/v1/hr/time-off/requests/{request_id}/action` |
| Flujo automatizado de onboarding para personal de cocina | Listo | `POST /api/v1/hr/onboarding/cases/start`, `POST /api/v1/hr/onboarding/cases/{case_id}/advance`, `GET /api/v1/hr/onboarding/cases` |
| Dashboard de KPIs RRHH segmentado por pais (rotacion, absentismo, cobertura vacantes) | Listo | `GET /api/v1/hr/kpis/overview` + panel `Personas y cultura` en `uis/executive-dashboard` |
| Cobertura operativa para 115 personas activas en 14 locales | Listo | Seed `hr_employees` en `services/brasaland-api/src/main.py` (115 activos + historial de bajas por pais) |

Validacion rapida local:

```bash
# 1) Verificar base de colaboradores activos
curl -s 'http://localhost:8000/api/v1/hr/employees?employment_status=active&limit=300' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token' | grep -o '"id"' | wc -l

# 2) Crear solicitud RRHH (vacaciones/ausencia)
curl -X POST 'http://localhost:8000/api/v1/hr/time-off/requests' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"employee_id":"emp-us-070","request_type":"vacation","start_date":"2026-06-10","end_date":"2026-06-14","reason":"Vacaciones familiares"}'

# 3) Onboarding automatizado
curl -X POST 'http://localhost:8000/api/v1/hr/onboarding/cases/start' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"employee_id":"emp-us-082","position_title":"Prep Cook","mentor_name":"Ashley Turner"}'

# 4) KPI RRHH por pais
curl -s 'http://localhost:8000/api/v1/hr/kpis/overview?days=90' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 5) Export CSV RRHH (solicitudes + onboarding + KPIs)
curl -s 'http://localhost:8000/api/v1/reports/hr.csv?days=90&section=all' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token' > /tmp/hr-report.csv && wc -l /tmp/hr-report.csv
```

## Tablero de cumplimiento - Formacion y estandares de calidad (Brasaland)

Estado objetivo para Jake Morrison:

| Capacidad requerida | Estado | Evidencia tecnica |
| ---- | ---- | ---- |
| Plataforma de formacion con catalogo de recetas y busqueda | Listo | `GET /api/v1/training/recipes/search` + panel `Formacion y estandares de calidad` en `uis/executive-dashboard` |
| Itinerario de incorporacion estructurado por rol e idioma | Listo | `GET /api/v1/training/onboarding/itineraries`, `GET /api/v1/training/onboarding/itineraries/{itinerary_id}`, `POST /api/v1/training/onboarding/assign` |
| Distribucion simultanea de actualizaciones de receta a toda la cadena | Listo | `POST /api/v1/training/recipes/updates/publish` + `GET /api/v1/training/recipes/updates/{update_id}/deliveries` (fanout 14 locales) |
| Confirmacion por local (ACK) para trazabilidad operativa | Listo | `POST /api/v1/training/recipes/updates/{update_id}/acknowledge` + resumen de entregados/ACK/pendientes |
| Soporte bilingue ES/EN en contenido y panel | Listo | Seeds y filtros `locale` en endpoints + selector de idioma en dashboard |

Validacion rapida local:

```bash
# 1) Buscar recetas estandarizadas por termino e idioma
curl -s 'http://localhost:8000/api/v1/training/recipes/search?q=pollo&locale=es&limit=10' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 2) Consultar itinerarios de onboarding
curl -s 'http://localhost:8000/api/v1/training/onboarding/itineraries?locale=es&limit=10' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 3) Publicar update de receta (distribucion simultanea)
curl -s -X POST 'http://localhost:8000/api/v1/training/recipes/updates/publish' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"resource_id":"rec-brasa-pollo-v1","change_summary":"Ajuste estandar QA","locale":"es","mandatory":true}'

# Capturar el update_id mas reciente
UPDATE_ID=$(curl -s 'http://localhost:8000/api/v1/training/recipes/updates?locale=es&limit=1' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token' | grep -o '"update_id":[0-9]*' | head -n1 | cut -d: -f2)

# 4) Verificar entrega por local (esperado: 14 registros)
curl -s "http://localhost:8000/api/v1/training/recipes/updates/${UPDATE_ID}/deliveries?limit=30" \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token' | grep -o '"store_id"' | wc -l

# 5) Registrar ACK desde un local
curl -s -X POST "http://localhost:8000/api/v1/training/recipes/updates/${UPDATE_ID}/acknowledge" \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"store_id":"med-001","acknowledged_by":"kitchen-lead","ack_note":"Aplicado en turno AM"}'
```

## Tablero de cumplimiento - Tecnologia (Brasaland)

Estado objetivo para Nicolas Park:

| Capacidad requerida | Estado | Evidencia tecnica |
| ---- | ---- | ---- |
| API central de Brasaland para locales, menus, ventas, clientes y proveedores | Listo | `GET /api/v1/stores`, `GET/POST /api/v1/menus/items`, `/api/v1/sales/*`, `/api/v1/customers/*`, `/api/v1/suppliers/*` en `services/brasaland-api/src/main.py` |
| Telemetria en tiempo real desde cada local | Listo | `POST /api/v1/telemetry/events` + `GET /api/v1/telemetry/stores/status` |
| Pipeline de datos para dashboards de operaciones, marketing y finanzas | Listo | `data/pipelines/brasaland-core/pipeline.py` genera `mart_ops_dashboard.csv`, `mart_marketing_dashboard.csv`, `mart_finance_dashboard.csv` |

Validacion rapida local:

```bash
# 1) Health de API central
curl -s 'http://localhost:8000/health'

# 2) Catalogo de menu (lectura)
curl -s 'http://localhost:8000/api/v1/menus/items?country=CO&locale=es&currency=COP' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 3) Ingestar evento de telemetria
curl -s -X POST 'http://localhost:8000/api/v1/telemetry/events' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"store_id":"med-001","source_system":"pos","event_ts":"2026-05-10T22:00:00Z","pos_online":true,"sales_last_5m":4,"open_tickets":2,"avg_prep_seconds":410,"network_rtt_ms":31,"terminal_version":"pos-v2.1"}'

# 4) Estado de telemetria por local
curl -s 'http://localhost:8000/api/v1/telemetry/stores/status?window_minutes=10' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 5) Ejecutar pipeline de datos para dashboards
python data/pipelines/brasaland-core/pipeline.py
ls -1 data/process/brasaland-marts
```

## Tablero de cumplimiento - Direccion ejecutiva (Brasaland)

Estado objetivo para Mariana Restrepo:

| Capacidad requerida | Estado | Evidencia tecnica |
| ---- | ---- | ---- |
| Dashboard ejecutivo unificado para 14 locales en 2 mercados | Listo | `uis/executive-dashboard/` integra ventas, riesgo operativo y comparativos de cadena |
| Ventas totales de cadena en USD y COP en la misma vista | Listo | Tarjetas duales en dashboard (USD + COP) consumiendo `/api/v1/sales/summary` |
| Asistente IA en lenguaje natural para consultas ejecutivas | Listo | `GET /api/v1/executive/ask` responde preguntas semanales por mercado y top ticket mensual |
| Informe semanal automatizado enviado cada lunes 07:00 | Listo | `workflows/scripts/run_weekly_report.sh` + `send_weekly_report.py` + `weekly_report.cron.example` con `CRON_TZ=America/Bogota` |

Validacion rapida local:

```bash
# 1) Ventas semanales en USD y COP
curl -s 'http://localhost:8000/api/v1/sales/summary?period=week&currency=USD'
curl -s 'http://localhost:8000/api/v1/sales/summary?period=week&currency=COP'

# 2) Asistente IA - pregunta por Florida
curl -s 'http://localhost:8000/api/v1/executive/ask?question=Cuanto%20vendimos%20esta%20semana%20en%20Florida%3F&currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 3) Asistente IA - top ticket mensual
curl -s 'http://localhost:8000/api/v1/executive/ask?question=Que%20local%20tiene%20el%20ticket%20medio%20mas%20alto%20este%20mes%3F&currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 4) Preview del reporte semanal
curl -s 'http://localhost:8000/api/v1/executive/weekly-report?currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 5) Generar y enviar reporte (si ENABLE_REPORT_DISPATCH=1)
API_BASE='http://localhost:8000' ENABLE_REPORT_DISPATCH=1 bash workflows/scripts/run_weekly_report.sh
```

---

## Estructura del repositorio

```text
ai-engineering-company-project-monorepo/
├── README.md
├── README.es.md
├── CONTEXT.md
├── AGENTS.md
├── agents/                   # Patrones/plantillas de agentes y tests
├── data/                     # raw, process, pipelines, eval
├── docs/                     # Documentacion de proyecto y arquitectura
├── infra/                    # Docker, Terraform, configuraciones de despliegue
├── internal/                 # CLIs y utilidades internas
├── mcps/                     # Servidores Model Context Protocol (MCP)
├── packages/
│   └── shared/               # Paquete compartido (@repo/shared-types)
├── scripts/                  # Convenciones/documentación de scripts
├── services/
│   └── brasaland-api/
│       ├── src/              # Codigo fuente de la API
│       │   └── main.py
│       ├── requirements.txt
│       └── README.es.md
├── shared/                   # Recursos/convenciones compartidas a nivel repo
├── skills/                   # Skills reutilizables para agentes
├── uis/
│   ├── executive-dashboard/  # Dashboard ejecutivo MVP (HTML/CSS/JS)
│   ├── marketing-loyalty-app/ # App de fidelizacion y pedidos (HTML/CSS/JS)
│   └── public-website/       # Sitio web publico
└── workflows/                # Documentación de automatizaciones/orquestación
```

---

## Cómo empezar

1. **Usa este repositorio como plantilla** y crea tu propio repo de proyecto.
2. **Clona** tu repositorio (o ábrelo en Codespaces).
3. **Reemplaza** `CONTEXT.md` con el contexto completo de tu empresa asignada.
4. **Revisa** los `README.md` de cada carpeta raíz para entender responsabilidades (`uis/`, `services/`, `data/`, `skills/`, etc.).
5. **Empieza a implementar** entregables por hito en `uis/` y `services/`, reutilizando `packages/shared/` y `data/` según corresponda.

Tip rapido para entorno local (API Brasaland):

```bash
bash scripts/bootstrap_local_env.sh
```

Luego inicia la API:

```bash
bash scripts/run_api_local.sh
```

Para detener la API local:

```bash
bash scripts/stop_api_local.sh
```

Para reiniciar la API local:

```bash
bash scripts/restart_api_local.sh
```

Para ejecutar toda la QA local en un comando:

```bash
bash scripts/run_qa_local.sh
```

Para ejecutar ciclo de desarrollo completo (restart + QA + cleanup):

```bash
bash scripts/dev_cycle.sh
```

Para validar prerequisitos del entorno local:

```bash
bash scripts/check_env.sh
```

Nota: `run_api_local.sh` y `restart_api_local.sh` ya ejecutan este preflight automaticamente.

Opcional (si necesitas bootstrap manual):

```bash
cd services/brasaland-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

---

## Hitos (referencia)

| Hito | Enfoque       | Entregables típicos                              |
| ---- | ------------- | ------------------------------------------------ |
| 0    | Prework       | Configuración del entorno, primeros prompts      |
| 1    | Web           | Sitio corporativo, formularios, SEO              |
| 2    | Programación  | Lógica de negocio, puntuación, cálculos          |
| 3    | UI con IA     | Interfaces generadas con IA                      |
| 4    | Next.js       | Portales, app de fidelización, UI de operaciones |
| 5    | Backend       | API central (ubicaciones, menús, ventas, etc.)   |
| 6    | Telemetría    | Pipeline de datos, dashboards                    |
| 7    | RAG y memoria | Base de conocimiento semántica, búsqueda         |
| 8    | Agentes       | Agentes de soporte, onboarding, formación        |
| 9    | Workflows     | Automatizaciones con n8n                         |
| 10   | Tiempo real   | Dashboards en vivo, alertas, streaming           |

---

## Enlaces

- [4Geeks Academy — Ingeniería de IA](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [Cómo empezar un proyecto de código](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contribuidores

Esta plantilla fue creada como parte del Programa de Carrera de Ingeniería de IA de 4Geeks Academy por [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) y [@alezanchezr](https://x.com/alesanchezr), junto a otros muchos colaboradores. Descubre más sobre nuestro [Curso de Ingeniería de IA](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia) y sobre [otros cursos](https://4geeksacademy.com/es/comparar-programas).

Puedes encontrar otras plantillas y recursos similares en la [página de GitHub de 4Geeks Academy](https://github.com/4geeksacademy).

_Esta plantilla la mantiene 4Geeks Academy para el track de Ingeniería de IA. Uso exclusivo del programa._
