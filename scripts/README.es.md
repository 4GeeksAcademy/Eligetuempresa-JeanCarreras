# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## Scripts disponibles

### `run_api_local.sh`

Levanta la API de Brasaland en local de forma robusta.

- Busca Python en este orden:
	- `services/brasaland-api/.venv/bin/python`
	- `.venv/bin/python` (raiz del repo)
	- `python3` del sistema
- Ejecuta `python -m uvicorn app.main:app` con host/puerto configurables.

Ejemplo:

```bash
bash scripts/run_api_local.sh
```

Variables opcionales:

- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)

### `stop_api_local.sh`

Detiene procesos que esten escuchando en el puerto de la API local.

Ejemplo:

```bash
bash scripts/stop_api_local.sh
```

Variables opcionales:

- `PORT` (default: `8000`)

### `restart_api_local.sh`

Reinicia la API local en un solo comando (`stop` + `run`).

Ejemplo:

```bash
bash scripts/restart_api_local.sh
```

Variables opcionales:

- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)

### `run_qa_local.sh`

Ejecuta en secuencia toda la bateria QA local:

- `workflows/scripts/smoke_api.sh`
- `workflows/scripts/integration_api.sh`
- `workflows/scripts/integration_data_api.sh`

Ejemplo:

```bash
bash scripts/run_qa_local.sh
```

### `dev_cycle.sh`

Ejecuta un ciclo completo de desarrollo local:

1. Limpia puerto de API.
2. Levanta API en background.
3. Ejecuta `run_qa_local.sh`.
4. Detiene API al finalizar.

Ejemplo:

```bash
bash scripts/dev_cycle.sh
```

Variables opcionales:

- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)
- `LOG_FILE` (default: `/tmp/uvicorn-dev-cycle.log`)
