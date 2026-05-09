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
