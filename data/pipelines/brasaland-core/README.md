# brasaland-core pipeline

Core data pipeline for Technology (CTO) at Brasaland.

## Objective

Materialize operational and analytical datasets from the central API/DB to feed dashboards for:

- Operations
- Marketing
- Finance

## Inputs

- Central SQLite: `services/brasaland-api/brasaland.db`
- Tables: `stores`, `sales_events`, `stock_levels`, `inventory_receipts`, `customers`, `digital_orders`, `supplier_prices`

## Outputs

Generates CSVs in `data/process/brasaland-marts/`:

- `dim_store.csv`
- `dim_supplier.csv`
- `fact_sales_daily.csv`
- `fact_ticket_hourly.csv`
- `fact_inventory_status.csv`
- `mart_ops_dashboard.csv`
- `mart_marketing_dashboard.csv`
- `mart_finance_dashboard.csv`

## Run

```bash
python data/pipelines/brasaland-core/pipeline.py
```

## Suggested cadence

- Every minute for `fact_ticket_hourly` and `mart_ops_dashboard`.
- Every 15 minutes for `fact_sales_daily` and `fact_inventory_status`.
- Hourly for `mart_marketing_dashboard` and `mart_finance_dashboard`.
