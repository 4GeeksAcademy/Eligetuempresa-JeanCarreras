# executive-dashboard

MVP de dashboard ejecutivo de Brasaland para visualizacion rapida de KPIs de cadena.

## Alcance inicial

- Ventas semanales consolidadas.
- Ticket promedio.
- Estado de actividad de locales.
- Filtros por pais y rango de fechas.
- Tabla de ventas por local.
- Grafico de tendencia diaria de ventas.
- Comparativo por mercado con variacion WoW.
- Panel de KPIs financieros estimados (ingresos, COGS, utilidad bruta, margen).
- Panel de compras y proveedores (historial, alertas y consolidado de cadena).
- Panel de marketing (CRM, clientes y personalizacion).
- Panel de personas y cultura (solicitudes de vacaciones/ausencias, onboarding y KPIs RRHH por pais).
- Panel de formacion y estandares de calidad (busqueda de recetas, itinerarios estructurados y publicacion simultanea de updates de receta).
- Panel de direccion ejecutiva (ventas semanales de cadena en USD y COP, asistente IA en lenguaje natural, y vista del reporte semanal automatizado de los lunes 07:00).

## Ejecutar local

Opcion simple:

```bash
cd services/brasaland-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

En otra terminal:

```bash
cd uis/executive-dashboard
python -m http.server 5500
```

Abrir en navegador:

- http://localhost:5500

## Telemetria

El servicio compartido está en `telemetry.js`. Acumula lotes de hasta 20 eventos o 10 segundos, reintenta con backoff y usa `sendBeacon` al ocultar la pestaña. En este frontend estático, el deployment puede inyectar `window.NEXT_PUBLIC_TELEMETRY_ENDPOINT` antes de cargar el servicio; el servidor local deriva `/telemetry/events` de la URL de la API cuando no se inyecta. El navegador no puede leer `.env.local` directamente.

Se capturan `navigation_section_viewed`, `frontend_page_load_recorded`, `frontend_error_captured` y `api_latency_recorded`; además de `inventory_validation_failed`, `inventory_receipt_created`, `training_recipe_update_published`, `auth_login_failed` y `auth_login_succeeded`. Las propiedades siguen las allowlists de `docs/telemetry/event-schemas.json`; no se envían credenciales, preguntas del asistente ni notas de recibo.

Los eventos de salida de inventario, edición directa rechazada y cruce descendente de umbral no se emiten porque este MVP no tiene esos flujos. Tampoco se infiere expiración de sesión a partir de un 401 genérico. Requieren productores de dominio que distingan esos hechos con certeza.

## Proximo paso

- Incorporar drill-down por local.
- Integrar autenticacion para perfiles internos.
