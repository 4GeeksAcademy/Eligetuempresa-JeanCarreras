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

## Proximo paso

- Incorporar drill-down por local.
- Integrar autenticacion para perfiles internos.
