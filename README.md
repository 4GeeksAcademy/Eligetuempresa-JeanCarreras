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
bash scripts/bootstrap_api_env.sh
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
