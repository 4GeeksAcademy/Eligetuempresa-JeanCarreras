# `workflows` folder

This folder holds **workflows and automations** for the monorepo (for example with n8n or other tools): integrations, scheduled jobs, process orchestration, notifications, synchronizations, and flows that connect systems.

- **Main purpose**: centralize operational automation related to the company and the cross-functional project milestones.
- **Recommendation**: document each workflow you add (triggers, inputs/outputs, required credentials, steps, error handling) and link it to the involved apps, pipelines, and agents.

## Current artifacts

- `BRASALAND-WORKFLOWS.es.md`: functional definition of priority workflows.
- `scripts/weekly_executive_report.py`: initial script to generate the weekly executive report from the API.
- `scripts/run_weekly_report.sh`: wrapper script that generates and stores weekly output in `workflows/output/`.
- `scripts/weekly_report.cron.example`: cron entry example for Monday 07:00 automated execution.
- `scripts/send_weekly_report.py`: optional report delivery through Slack webhook and/or SMTP email.
- `scripts/smoke_api.sh`: reproducible smoke tests for critical API endpoints.
- `scripts/integration_api.sh`: base integration suite for endpoints, filters, and role-based permissions.
- `scripts/integration_data_api.sh`: data edge-case suite (invalid dates, invalid ranges, invalid payloads).

## Quick API validation

Run smoke tests (self-contained: it starts the local API if it is not running):

```bash
bash workflows/scripts/smoke_api.sh
```

Optional variables:

- `API_BASE` (default: `http://localhost:8000`)
- `CURRENCY` (`USD` or `COP`)
- `START_DATE` / `END_DATE` (`YYYY-MM-DD`)
- `BRASALAND_ADMIN_TOKEN`, `BRASALAND_EXECUTIVE_TOKEN`, `BRASALAND_OPERATIONS_TOKEN`, `BRASALAND_FINANCE_TOKEN`

## VS Code tasks

- Available tasks:
	- `brasaland: smoke api`
	- `brasaland: integration api`
	- `brasaland: integration data api`
	- `brasaland: qa all` (full sequential run)
- File: `.vscode/tasks.json`

## Full local QA

You can run the full local battery in sequence:

```bash
bash workflows/scripts/smoke_api.sh && bash workflows/scripts/integration_api.sh && bash workflows/scripts/integration_data_api.sh
```

## Automated CI

- Workflows:
	- `.github/workflows/smoke-api.yml`:
		- runs on `push` and `pull_request` to `main`.
		- executes `workflows/scripts/smoke_api.sh`.
	- `.github/workflows/integration-api.yml`:
		- runs after successful `Smoke API` completion (or manually through `workflow_dispatch`).
		- executes `workflows/scripts/integration_api.sh`.
	- `.github/workflows/integration-data-api.yml`:
		- runs after successful `Integration API` completion (or manually through `workflow_dispatch`).
		- executes `workflows/scripts/integration_data_api.sh`.

> _Spanish version: [README.es.md](./README.es.md)._
