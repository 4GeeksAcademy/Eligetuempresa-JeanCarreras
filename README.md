# AI Engineering Company Project — Student Template

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
[![Smoke API](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/smoke-api.yml/badge.svg)](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/smoke-api.yml)
[![Integration API](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/integration-api.yml/badge.svg)](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/integration-api.yml)
[![Integration Data API](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/integration-data-api.yml/badge.svg)](https://github.com/4GeeksAcademy/Eligetuempresa-JeanCarreras/actions/workflows/integration-data-api.yml)

_Base template for transversal projects in the AI Engineering Career Program — 4Geeks Academy._

> _Instrucciones disponibles en español en [README.es.md](./README.es.md)._

---

## Purpose

This repository is the **starter template** for transversal projects. You will work on real company scenarios (Brasaland, TrackFlow, Nexova), building deliverables that map to course milestones (Web, Programming, Backend, Telemetry, RAG, Agents, Workflows, Real-time).

- Create a template from this repository.
- Replace the placeholder `CONTEXT.md` with your assigned company context.
- Use `skills/` and the directory-level `README.md` files as working guidance.

---

## Current status of the template

The repository currently provides a **base folder structure and documentation skeleton** with an initial Brasaland-focused working baseline.

- `CONTEXT.md` already includes Brasaland company context.
- A root `AGENTS.md` is available with priorities and guardrails.
- Initial deliverables were added under `docs/`, `workflows/`, `services/brasaland-api/`, and `uis/executive-dashboard/`.
- Shared package metadata exists in `packages/shared/package.json` (`@repo/shared-types`), but no workspace runner is configured at root.

## Recent updates

- MVP API running in `services/brasaland-api/` with sales, market, finance, CSV export, and audit endpoints.
- MVP executive dashboard in `uis/executive-dashboard/`, connected to local API with demo fallback mode.
- Reproducible, self-contained QA suite:
	- `workflows/scripts/smoke_api.sh`
	- `workflows/scripts/integration_api.sh`
	- `workflows/scripts/integration_data_api.sh`
- Chained CI in GitHub Actions:
	- `Smoke API` -> `Integration API` -> `Integration Data API`
- ES/EN documentation aligned across root README, `services/`, `uis/`, `workflows/`, and main submodules.
- New mobile-first loyalty and ordering web interface in `uis/marketing-loyalty-app/` (integrated with Marketing endpoints).
- New HR block with internal portal, automated onboarding, and country-segmented KPIs in API + executive dashboard.

## Operations compliance board (Brasaland)

Target status for Felipe Guerrero (14 stores):

| Required capability | Status | Technical evidence |
| ---- | ---- | ---- |
| Real-time sales dashboard by store (COP and USD) | Done | `uis/executive-dashboard/app.js` (consumes `/sales/summary`, `/sales/by-store`, `/sales/daily-trend`, filters and auto-refresh) |
| Smart ingredient ordering (historical sales + current stock) | Done | `services/brasaland-api/app/main.py` (`/api/v1/orders/recommendations`) + `uis/executive-dashboard/app.js` |
| Automatic alerts when a store has no sales during opening hours | Done | `services/brasaland-api/app/main.py` (`/api/v1/alerts/inactivity`, `STORE_OPENING_HOURS`) + ACK/RESOLVE actions in `uis/executive-dashboard/app.js` |
| Chain coverage (14 stores) | Done | `services/brasaland-api/app/main.py` (14-store seed + per-store sales/stock backfill) |

Quick local validation:

```bash
# 1) Start API
bash scripts/run_api_local.sh

# 2) Base smoke
bash workflows/scripts/smoke_api.sh

# 3) Confirm 14 stores
curl -s http://localhost:8000/api/v1/stores | grep -o '"id"' | wc -l

# 4) Confirm opening-hours inactivity alerts
curl -s 'http://localhost:8000/api/v1/alerts/inactivity?window_minutes=60&opening_hours_only=true&limit=50' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 5) Confirm smart order recommendations
curl -s 'http://localhost:8000/api/v1/orders/recommendations?days_history=14&target_days=7&only_at_risk=false&limit=200&country=CO&currency=COP' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'
```

## Procurement and suppliers compliance board (Brasaland)

Target status for Lucia Fernandez:

| Required capability | Status | Technical evidence |
| ---- | ---- | ---- |
| Price history by supplier and SKU (CO + US) | Done | `services/brasaland-api/app/main.py` (`/api/v1/suppliers/prices`) |
| Configurable supplier price-change alerts by threshold | Done | `services/brasaland-api/app/main.py` (`/api/v1/suppliers/price-alerts?threshold_pct=...`) |
| Multi-country and multi-currency coverage (COP/USD) | Done | `country` + `currency` filters in supplier endpoints |
| Central visual console for Procurement | Done | Dedicated panel in `uis/executive-dashboard` connected to `/api/v1/suppliers/prices`, `/api/v1/suppliers/price-alerts`, and `/api/v1/suppliers/purchases/consolidated` |

Quick local validation:

```bash
# 1) Colombia price history (COP)
curl -s 'http://localhost:8000/api/v1/suppliers/prices?country=CO&currency=COP&limit=20' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token'

# 2) Colombia price-change alerts
curl -s 'http://localhost:8000/api/v1/suppliers/price-alerts?country=CO&threshold_pct=5&currency=COP' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token'

# 3) Florida price history (USD)
curl -s 'http://localhost:8000/api/v1/suppliers/prices?country=US&currency=USD&limit=20' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 4) Chain consolidated purchases (30 days)
curl -s 'http://localhost:8000/api/v1/suppliers/purchases/consolidated?days=30&currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'
```

## Marketing and digital experience compliance board (Brasaland)

Target status for Camila Ospina:

| Required capability | Status | Technical evidence |
| ---- | ---- | ---- |
| Digital loyalty + ordering app | Done | `POST /api/v1/marketing/orders` with automatic Brasa Points accrual + dedicated UI in `uis/marketing-loyalty-app/` |
| Customer CRM with order history and preferences | Done | `GET /api/v1/marketing/crm/overview`, `GET /api/v1/marketing/crm/customers`, `GET /api/v1/marketing/customers/{customer_id}/history` |
| Behavior-based personalization engine | Done | `GET /api/v1/marketing/personalization/recommendations` + Marketing panel in `uis/executive-dashboard` |

Quick local validation:

```bash
# 1) Digital loyalty/ordering app
curl -X POST 'http://localhost:8000/api/v1/marketing/orders' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"customer_id":"cus-co-001","store_id":"med-001","order_items":["family_combo","cola_350"],"total_amount":98000,"currency":"COP","channel":"app"}'

# 2) Consolidated customer CRM
curl -s 'http://localhost:8000/api/v1/marketing/crm/overview?days=30&currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 3) Behavior-based personalization
curl -s 'http://localhost:8000/api/v1/marketing/personalization/recommendations?customer_id=cus-us-001&currency=USD&limit=5' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'
```

## People and culture compliance board (Brasaland)

Target status for Ashley Turner:

| Required capability | Status | Technical evidence |
| ---- | ---- | ---- |
| Internal HR portal for vacation requests and absence management | Done | `POST /api/v1/hr/time-off/requests`, `GET /api/v1/hr/time-off/requests`, `POST /api/v1/hr/time-off/requests/{request_id}/action` |
| Automated onboarding flow for kitchen staff | Done | `POST /api/v1/hr/onboarding/cases/start`, `POST /api/v1/hr/onboarding/cases/{case_id}/advance`, `GET /api/v1/hr/onboarding/cases` |
| HR KPI dashboard segmented by country (turnover, absenteeism, vacancy coverage time) | Done | `GET /api/v1/hr/kpis/overview` + `People and culture` panel in `uis/executive-dashboard` |
| Operational coverage for 115 active employees across 14 stores | Done | `hr_employees` seed in `services/brasaland-api/app/main.py` (115 active + country-level termination history) |

Quick local validation:

```bash
# 1) Verify active employee baseline
curl -s 'http://localhost:8000/api/v1/hr/employees?employment_status=active&limit=300' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token' | grep -o '"id"' | wc -l

# 2) Create HR request (vacation/absence)
curl -X POST 'http://localhost:8000/api/v1/hr/time-off/requests' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"employee_id":"emp-us-070","request_type":"vacation","start_date":"2026-06-10","end_date":"2026-06-14","reason":"Family vacation"}'

# 3) Automated onboarding
curl -X POST 'http://localhost:8000/api/v1/hr/onboarding/cases/start' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"employee_id":"emp-us-082","position_title":"Prep Cook","mentor_name":"Ashley Turner"}'

# 4) HR KPIs by country
curl -s 'http://localhost:8000/api/v1/hr/kpis/overview?days=90' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 5) HR CSV export (requests + onboarding + KPIs)
curl -s 'http://localhost:8000/api/v1/reports/hr.csv?days=90&section=all' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token' > /tmp/hr-report.csv && wc -l /tmp/hr-report.csv
```

## Training and quality standards compliance board (Brasaland)

Target status for Jake Morrison:

| Required capability | Status | Technical evidence |
| ---- | ---- | ---- |
| Training platform with searchable recipe catalog | Done | `GET /api/v1/training/recipes/search` + `Training and quality standards` panel in `uis/executive-dashboard` |
| Structured onboarding itinerary by role and language | Done | `GET /api/v1/training/onboarding/itineraries`, `GET /api/v1/training/onboarding/itineraries/{itinerary_id}`, `POST /api/v1/training/onboarding/assign` |
| Chain-wide simultaneous recipe update distribution | Done | `POST /api/v1/training/recipes/updates/publish` + `GET /api/v1/training/recipes/updates/{update_id}/deliveries` (14-store fanout) |
| Per-store acknowledgment (ACK) for operational traceability | Done | `POST /api/v1/training/recipes/updates/{update_id}/acknowledge` + delivered/ack/pending counters |
| Optional bilingual support (ES/EN) | Done | Locale seeds + `locale` filters in endpoints and dashboard selector |

Quick local validation:

```bash
# 1) Search standardized recipes by query and locale
curl -s 'http://localhost:8000/api/v1/training/recipes/search?q=chicken&locale=en&limit=10' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 2) List onboarding itineraries
curl -s 'http://localhost:8000/api/v1/training/onboarding/itineraries?locale=en&limit=10' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 3) Publish recipe update (simultaneous distribution)
curl -s -X POST 'http://localhost:8000/api/v1/training/recipes/updates/publish' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"resource_id":"rec-brasa-pollo-v1","change_summary":"Standard QA adjustment","locale":"en","mandatory":true}'

# Capture latest update_id
UPDATE_ID=$(curl -s 'http://localhost:8000/api/v1/training/recipes/updates?locale=en&limit=1' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token' | grep -o '"update_id":[0-9]*' | head -n1 | cut -d: -f2)

# 4) Verify per-store deliveries (expected: 14)
curl -s "http://localhost:8000/api/v1/training/recipes/updates/${UPDATE_ID}/deliveries?limit=30" \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token' | grep -o '"store_id"' | wc -l

# 5) Register ACK from one store
curl -s -X POST "http://localhost:8000/api/v1/training/recipes/updates/${UPDATE_ID}/acknowledge" \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"store_id":"med-001","acknowledged_by":"kitchen-lead","ack_note":"Applied in AM shift"}'
```

## Technology compliance board (Brasaland)

Target status for Nicolas Park:

| Required capability | Status | Technical evidence |
| ---- | ---- | ---- |
| Central Brasaland API for stores, menus, sales, customers, and suppliers | Done | `GET /api/v1/stores`, `GET/POST /api/v1/menus/items`, `/api/v1/sales/*`, `/api/v1/customers/*`, `/api/v1/suppliers/*` in `services/brasaland-api/app/main.py` |
| Real-time telemetry from each store | Done | `POST /api/v1/telemetry/events` + `GET /api/v1/telemetry/stores/status` |
| Data pipeline for operations, marketing, and finance dashboards | Done | `data/pipelines/brasaland-core/pipeline.py` generates `mart_ops_dashboard.csv`, `mart_marketing_dashboard.csv`, `mart_finance_dashboard.csv` |

Quick local validation:

```bash
# 1) Central API health
curl -s 'http://localhost:8000/health'

# 2) Menu catalog (read)
curl -s 'http://localhost:8000/api/v1/menus/items?country=CO&locale=es&currency=COP' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 3) Ingest telemetry event
curl -s -X POST 'http://localhost:8000/api/v1/telemetry/events' \
	-H 'Content-Type: application/json' \
	-H 'X-API-Role: operations' \
	-H 'X-API-Token: brasaland-operations-token' \
	-d '{"store_id":"med-001","source_system":"pos","event_ts":"2026-05-10T22:00:00Z","pos_online":true,"sales_last_5m":4,"open_tickets":2,"avg_prep_seconds":410,"network_rtt_ms":31,"terminal_version":"pos-v2.1"}'

# 4) Telemetry status by store
curl -s 'http://localhost:8000/api/v1/telemetry/stores/status?window_minutes=10' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 5) Run dashboard data pipeline
python data/pipelines/brasaland-core/pipeline.py
ls -1 data/process/brasaland-marts
```

## Executive direction compliance board (Brasaland)

Target status for Mariana Restrepo:

| Required capability | Status | Technical evidence |
| ---- | ---- | ---- |
| Unified executive dashboard across 14 stores and 2 markets | Done | `uis/executive-dashboard/` consolidates chain sales, operational risk, and market comparisons |
| Chain total sales in USD and COP in the same view | Done | Dual sales cards in dashboard calling `/api/v1/sales/summary` |
| Natural-language AI assistant for executive questions | Done | `GET /api/v1/executive/ask` answers weekly market sales and monthly top ticket questions |
| Automated weekly report sent every Monday at 07:00 | Done | `workflows/scripts/run_weekly_report.sh` + `send_weekly_report.py` + `weekly_report.cron.example` with `CRON_TZ=America/Bogota` |

Quick local validation:

```bash
# 1) Weekly sales in USD and COP
curl -s 'http://localhost:8000/api/v1/sales/summary?period=week&currency=USD'
curl -s 'http://localhost:8000/api/v1/sales/summary?period=week&currency=COP'

# 2) AI assistant - Florida weekly sales
curl -s 'http://localhost:8000/api/v1/executive/ask?question=How%20much%20did%20we%20sell%20this%20week%20in%20Florida%3F&currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 3) AI assistant - monthly highest average ticket
curl -s 'http://localhost:8000/api/v1/executive/ask?question=Which%20store%20has%20the%20highest%20average%20ticket%20this%20month%3F&currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 4) Weekly report preview
curl -s 'http://localhost:8000/api/v1/executive/weekly-report?currency=USD' \
	-H 'X-API-Role: executive' \
	-H 'X-API-Token: brasaland-executive-token'

# 5) Generate and dispatch report (if ENABLE_REPORT_DISPATCH=1)
API_BASE='http://localhost:8000' ENABLE_REPORT_DISPATCH=1 bash workflows/scripts/run_weekly_report.sh
```

---

## Repository structure

```text
ai-engineering-company-project-monorepo/
├── README.md
├── README.es.md
├── CONTEXT.md                # Placeholder to be replaced with assigned context
├── agents/                   # Agent patterns/templates and tools docs
├── data/                     # raw, process, pipelines, eval
├── docs/                     # Project and architecture documentation
├── infra/                    # Docker, Terraform, deployment configs
├── internal/                 # CLIs, packaged migration scripts, internal utilities
├── mcps/                     # Model Context Protocol (MCP) Servers
├── packages/
│   └── shared/               # Shared package (@repo/shared-types)
├── scripts/                  # Script conventions/documentation
├── services/                 # APIs and background workers
├── shared/                   # Shared assets/conventions at repo level
├── skills/                   # Reusable agent skills
├── uis/                      # User interfaces (React, Next.js, Streamlit, HTML)
└── workflows/                # Automation/orchestration documentation
```

---

## How to start

1. **Use this repository as a template** and create your own project repo.
2. **Clone** your repository (or open it in Codespaces).
3. **Replace** `CONTEXT.md` with the full context for your assigned company.
4. **Review** each top-level folder `README.md` to understand intended responsibilities (`uis/`, `services/`, `data/`, `skills/`, etc.).
5. **Start implementing** milestone deliverables in `uis/` and `services/`, reusing `packages/shared/` and `data/` as needed.

Quick local tip (Brasaland API):

```bash
bash scripts/bootstrap_local_env.sh
```

Then start the API:

```bash
bash scripts/run_api_local.sh
```

To stop the local API:

```bash
bash scripts/stop_api_local.sh
```

To restart the local API:

```bash
bash scripts/restart_api_local.sh
```

To run full local QA in one command:

```bash
bash scripts/run_qa_local.sh
```

To run full dev cycle (restart + QA + cleanup):

```bash
bash scripts/dev_cycle.sh
```

To validate local environment prerequisites:

```bash
bash scripts/check_env.sh
```

Note: `run_api_local.sh` and `restart_api_local.sh` already run this preflight automatically.

Optional (manual bootstrap if needed):

```bash
cd services/brasaland-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Milestones (reference)

| Milestone | Focus        | Typical deliverables                        |
| --------- | ------------ | ------------------------------------------- |
| 0         | Prework      | Environment setup, first prompts            |
| 1         | Web          | Corporate website, forms, SEO               |
| 2         | Programming  | Business logic, scoring, calculations       |
| 3         | AI-driven UI | AI-generated interfaces                     |
| 4         | Next.js      | Portals, loyalty app, operations UI         |
| 5         | Backend      | Central API (locations, menus, sales, etc.) |
| 6         | Telemetry    | Data pipeline, dashboards                   |
| 7         | RAG & Memory | Semantic knowledge base, search             |
| 8         | Agents       | Support, onboarding, training agents        |
| 9         | Workflows    | n8n automations                             |
| 10        | Real-time    | Live dashboards, alerts, streaming          |

---

## Links

- [4Geeks Academy — AI Engineering](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [How to start a coding project](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contributors

This template was built as part of the 4Geeks Academy AI Engineering Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) and [@alezanchezr](https://x.com/alesanchezr) and many other contributors. Find out more about our [AI Engineering Course](https://4geeksacademy.com/en/career-programs/ai-engineering), and [other courses](https://4geeksacademy.com/en/program-comparison).

You can find other templates and resources like this at the [4Geeks Academy GitHub page](https://github.com/4geeksacademy).

_This template is maintained by 4Geeks Academy for the AI Engineering track. For exclusive use in the programme._

# Brasaland — Sitio web público

Este proyecto contiene la landing page y el formulario de aplicación para Brasaland, cumpliendo los requisitos de accesibilidad, responsive, validación y uso de Tailwind CSS.

## Estructura

- `index.html`: Landing page principal.
- `application.html`: Formulario de aplicación/registro.
- `validation.js`: Lógica de validación del formulario.
- `styles.css`: (opcional, solo si necesitas personalizar más allá de Tailwind CDN).

## Cómo levantar el proyecto localmente

Puedes usar un servidor estático compatible con Codespaces. Por ejemplo:

```bash
npx http-server . -p 3000 -a 0.0.0.0
```

Luego abre la URL que te indique Codespaces (por ejemplo, https://3000-xxxx.preview.app.github.dev/).

## Requisitos cumplidos

- HTML5 semántico, etiquetas ARIA, imágenes con alt.
- Formulario estructurado con fieldset, legend, label, required.
- Validación completa y mensajes claros.
- Responsive y mobile-first con Tailwind.
- SEO básico y Schema.org en la landing.
- Sin CSS personalizado salvo que sea estrictamente necesario.

---

Para cambios, edita los archivos en la raíz del repositorio.
