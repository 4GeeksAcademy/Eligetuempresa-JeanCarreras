# brasaland-core pipeline

Pipeline de datos base para Tecnologia (CTO) en Brasaland.

## Objetivo

Materializar datasets operativos y analiticos desde la API/DB central para alimentar dashboards de:

- Operaciones
- Marketing
- Finanzas

## Entradas

- SQLite central: `services/brasaland-api/brasaland.db`
- Tablas: `stores`, `sales_events`, `stock_levels`, `inventory_receipts`, `customers`, `digital_orders`, `supplier_prices`

## Salidas

Genera CSV en `data/process/brasaland-marts/`:

- `dim_store.csv`
- `dim_supplier.csv`
- `fact_sales_daily.csv`
- `fact_ticket_hourly.csv`
- `fact_inventory_status.csv`
- `mart_ops_dashboard.csv`
- `mart_marketing_dashboard.csv`
- `mart_finance_dashboard.csv`

## Ejecucion

```bash
python data/pipelines/brasaland-core/pipeline.py
```

## Cadencia sugerida

- Minutal para `fact_ticket_hourly` y `mart_ops_dashboard`.
- Cada 15 min para `fact_sales_daily` y `fact_inventory_status`.
- Horaria para `mart_marketing_dashboard` y `mart_finance_dashboard`.
