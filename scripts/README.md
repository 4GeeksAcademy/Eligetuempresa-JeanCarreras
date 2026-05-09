# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## Available scripts

### `bootstrap_api_env.sh`

Prepares the Brasaland API local environment in one command.

- Creates a venv at `services/brasaland-api/.venv` (or `VENV_DIR` if set).
- Installs/updates dependencies from `services/brasaland-api/requirements.txt`.

Example:

```bash
bash scripts/bootstrap_api_env.sh
```

### `run_api_local.sh`

Starts Brasaland API locally with robust Python resolution.

- Runs automatic preflight with `check_env.sh` before startup.

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

- Runs automatic preflight with `check_env.sh` before restart.
- Avoids duplicate validation when delegating to `run_api_local.sh`.

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

### `dev_cycle.sh`

Runs a full local development cycle:

1. Cleans API port.
2. Starts API in background.
3. Runs `run_qa_local.sh`.
4. Stops API when done.

Example:

```bash
bash scripts/dev_cycle.sh
```

Optional variables:

- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)
- `LOG_FILE` (default: `/tmp/uvicorn-dev-cycle.log`)

### `check_env.sh`

Validates local prerequisites before running operational scripts.

Checks:

- Required commands: `bash`, `curl`, `lsof`.
- Available Python (service venv, repo root venv, or `python3`).
- Required Python dependencies: `fastapi`, `uvicorn`, `pydantic`.

Example:

```bash
bash scripts/check_env.sh
```

> _Spanish version: [README.es.md](./README.es.md)._
