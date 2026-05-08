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

## Ejecutar local

Opcion simple:

```bash
cd services/brasaland-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
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
