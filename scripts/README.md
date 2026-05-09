# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## Available scripts

### `run_api_local.sh`

Starts Brasaland API locally with robust Python resolution.

- Resolves Python in this order:
	- `services/brasaland-api/.venv/bin/python`
	- `.venv/bin/python` (repo root)
	- system `python3`
- Runs `python -m uvicorn app.main:app` with configurable host/port.

Example:

```bash
bash scripts/run_api_local.sh
```

Optional variables:

- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)

### `stop_api_local.sh`

Stops processes listening on the local API port.

Example:

```bash
bash scripts/stop_api_local.sh
```

Optional variables:

- `PORT` (default: `8000`)

### `restart_api_local.sh`

Restarts the local API in one command (`stop` + `run`).

Example:

```bash
bash scripts/restart_api_local.sh
```

Optional variables:

- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)

### `run_qa_local.sh`

Runs the full local QA battery in sequence:

- `workflows/scripts/smoke_api.sh`
- `workflows/scripts/integration_api.sh`
- `workflows/scripts/integration_data_api.sh`

Example:

```bash
bash scripts/run_qa_local.sh
```

> _Spanish version: [README.es.md](./README.es.md)._
