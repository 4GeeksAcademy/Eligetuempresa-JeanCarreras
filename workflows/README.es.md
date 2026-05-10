# Carpeta `workflows`

Esta carpeta contiene **workflows y automatizaciones** del monorepo (por ejemplo con n8n u otras herramientas): integraciones, tareas programadas, orquestación de procesos, notificaciones, sincronizaciones y flujos que conectan sistemas.

- **Propósito principal**: centralizar la automatización operativa relacionada con la compañía y los hitos del proyecto transversal.
- **Recomendación**: documenta cada workflow que añadas (disparadores, entradas/salidas, credenciales requeridas, pasos, manejo de errores) y enlázalo con las apps/pipelines/agentes involucrados.

## Artefactos actuales

- `BRASALAND-WORKFLOWS.es.md`: definicion funcional de workflows prioritarios.
- `scripts/weekly_executive_report.py`: script inicial para generar reporte semanal ejecutivo consumiendo la API.
- `scripts/run_weekly_report.sh`: wrapper para generar y guardar el reporte semanal en `workflows/output/`.
- `scripts/weekly_report.cron.example`: ejemplo de entrada de cron para ejecucion automatizada cada lunes 07:00.
- `scripts/send_weekly_report.py`: envio opcional del reporte a Slack webhook y/o email SMTP.
- `scripts/smoke_api.sh`: smoke tests reproducibles para validar endpoints criticos de la API.
- `scripts/integration_api.sh`: suite base de integracion para endpoints, filtros y permisos por rol.
- `scripts/integration_data_api.sh`: suite de casos borde de datos (fechas invalidas, rango invalido, payloads invalidos).

## Programacion recomendada

1. Copiar la linea de `scripts/weekly_report.cron.example` en tu crontab.
	- Incluye `CRON_TZ=America/Bogota` para ejecutar a las 07:00 hora local de Colombia.
2. Configurar `API_BASE` y `CURRENCY` segun entorno.
3. Si proteges endpoints con roles, exportar tokens por rol en el entorno del job:
	- `BRASALAND_ADMIN_TOKEN`
	- `BRASALAND_EXECUTIVE_TOKEN`
	- `BRASALAND_OPERATIONS_TOKEN`
	- `BRASALAND_FINANCE_TOKEN`
4. Para despacho automatico, activar `ENABLE_REPORT_DISPATCH=1` y configurar segun canal:
	- Slack: `SLACK_WEBHOOK_URL`
	- Email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_SENDER`, `REPORT_RECIPIENTS`

## Validacion rapida de API

Ejecutar smoke tests (auto-contenido: levanta API local si no esta corriendo):

```bash
bash workflows/scripts/smoke_api.sh
```

Variables opcionales:

- `API_BASE` (default: `http://localhost:8000`)
- `CURRENCY` (`USD` o `COP`)
- `START_DATE` / `END_DATE` (`YYYY-MM-DD`)
- `BRASALAND_ADMIN_TOKEN`, `BRASALAND_EXECUTIVE_TOKEN`, `BRASALAND_OPERATIONS_TOKEN`, `BRASALAND_FINANCE_TOKEN`

## Ejecucion desde VS Code

- Tasks disponibles:
	- `brasaland: smoke api`
	- `brasaland: integration api`
	- `brasaland: integration data api`
	- `brasaland: qa all` (ejecucion secuencial completa)
- Archivo: `.vscode/tasks.json`

## QA local completo

Puedes ejecutar toda la bateria local en secuencia:

```bash
bash workflows/scripts/smoke_api.sh && bash workflows/scripts/integration_api.sh && bash workflows/scripts/integration_data_api.sh
```

## CI automatizado

- Workflows:
	- `.github/workflows/smoke-api.yml`:
		- dispara en `push` y `pull_request` hacia `main`.
		- ejecuta `workflows/scripts/smoke_api.sh`.
	- `.github/workflows/integration-api.yml`:
		- dispara al completar con exito `Smoke API` (o manual con `workflow_dispatch`).
		- ejecuta `workflows/scripts/integration_api.sh`.
	- `.github/workflows/integration-data-api.yml`:
		- dispara al completar con exito `Integration API` (o manual con `workflow_dispatch`).
		- ejecuta `workflows/scripts/integration_data_api.sh`.
