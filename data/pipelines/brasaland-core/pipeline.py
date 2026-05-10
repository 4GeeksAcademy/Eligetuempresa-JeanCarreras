#!/usr/bin/env python3
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "services" / "brasaland-api" / "brasaland.db"
OUT_DIR = ROOT / "data" / "process" / "brasaland-marts"


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(filename: str, rows: list[dict], fieldnames: list[str]) -> None:
    out_path = OUT_DIR / filename
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fetch_all(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict]:
    cur = conn.execute(query, params)
    columns = [c[0] for c in cur.description]
    data = []
    for row in cur.fetchall():
        data.append({columns[i]: row[i] for i in range(len(columns))})
    return data


def build_dim_store(conn: sqlite3.Connection) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT id AS store_id, name AS store_name, country, city, timezone, base_currency
        FROM stores
        ORDER BY id ASC
        """,
    )


def build_dim_supplier(conn: sqlite3.Connection) -> list[dict]:
    return fetch_all(
        conn,
        """
        WITH ranked AS (
          SELECT supplier_id, supplier_name, country, sku, item_name, currency, price, valid_from,
                 ROW_NUMBER() OVER (PARTITION BY supplier_id, sku ORDER BY valid_from DESC, id DESC) AS rn
          FROM supplier_prices
        )
        SELECT supplier_id, supplier_name, country, sku, item_name,
               currency AS latest_currency,
               price AS latest_price,
               valid_from AS latest_valid_from
        FROM ranked
        WHERE rn = 1
        ORDER BY country ASC, supplier_name ASC, sku ASC
        """,
    )


def build_fact_sales_daily(conn: sqlite3.Connection) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT date(se.sold_at) AS sales_day,
               st.id AS store_id,
               st.country,
               COUNT(*) AS tickets,
               ROUND(SUM(CASE WHEN se.currency = st.base_currency THEN se.total_amount ELSE se.total_amount END), 2) AS total_sales_native,
               st.base_currency AS currency
        FROM sales_events se
        JOIN stores st ON st.id = se.store_id
        GROUP BY date(se.sold_at), st.id, st.country, st.base_currency
        ORDER BY sales_day DESC, st.id ASC
        """,
    )


def build_fact_ticket_hourly(conn: sqlite3.Connection) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT strftime('%Y-%m-%dT%H:00:00Z', se.sold_at) AS sold_hour_utc,
               st.id AS store_id,
               st.country,
               COUNT(*) AS tickets,
               ROUND(AVG(se.total_amount), 2) AS avg_ticket_native,
               se.currency
        FROM sales_events se
        JOIN stores st ON st.id = se.store_id
        GROUP BY strftime('%Y-%m-%dT%H:00:00Z', se.sold_at), st.id, st.country, se.currency
        ORDER BY sold_hour_utc DESC, st.id ASC
        """,
    )


def build_fact_inventory_status(conn: sqlite3.Connection) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT sl.store_id, st.country, sl.sku, sl.item_name, sl.category, sl.unit,
               ROUND(sl.current_stock, 3) AS current_stock,
               ROUND(sl.min_stock, 3) AS min_stock,
               ROUND(sl.current_stock - sl.min_stock, 3) AS stock_gap,
               CASE WHEN sl.current_stock < sl.min_stock THEN 'at_risk' ELSE 'ok' END AS risk_level,
               sl.updated_at
        FROM stock_levels sl
        JOIN stores st ON st.id = sl.store_id
        ORDER BY st.country ASC, sl.store_id ASC, sl.sku ASC
        """,
    )


def build_mart_ops_dashboard(conn: sqlite3.Connection) -> list[dict]:
    return fetch_all(
        conn,
        """
        WITH last_sale AS (
          SELECT se.store_id, MAX(se.sold_at) AS last_sale_at
          FROM sales_events se
          GROUP BY se.store_id
        ),
        stock_risk AS (
          SELECT sl.store_id,
                 SUM(CASE WHEN sl.current_stock < sl.min_stock THEN 1 ELSE 0 END) AS sku_at_risk
          FROM stock_levels sl
          GROUP BY sl.store_id
        )
        SELECT st.id AS store_id, st.name AS store_name, st.country,
               COALESCE(ls.last_sale_at, '') AS last_sale_at,
               COALESCE(sr.sku_at_risk, 0) AS sku_at_risk,
               datetime('now') AS generated_at
        FROM stores st
        LEFT JOIN last_sale ls ON ls.store_id = st.id
        LEFT JOIN stock_risk sr ON sr.store_id = st.id
        ORDER BY st.id ASC
        """,
    )


def build_mart_marketing_dashboard(conn: sqlite3.Connection) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT c.country,
               COUNT(*) AS total_customers,
               SUM(CASE WHEN c.segment = 'vip' THEN 1 ELSE 0 END) AS vip_customers,
               ROUND(AVG(c.points_balance), 2) AS avg_points,
               COALESCE((
                 SELECT ROUND(SUM(o.total_amount), 2)
                 FROM digital_orders o
                 JOIN customers c2 ON c2.id = o.customer_id
                 WHERE c2.country = c.country
               ), 0) AS digital_revenue_native,
               datetime('now') AS generated_at
        FROM customers c
        GROUP BY c.country
        ORDER BY c.country ASC
        """,
    )


def build_mart_finance_dashboard(conn: sqlite3.Connection) -> list[dict]:
    return fetch_all(
        conn,
        """
        WITH rev AS (
          SELECT st.country,
                 SUM(CASE WHEN se.currency = 'USD' THEN se.total_amount ELSE se.total_amount / 3950.0 END) AS revenue_usd
          FROM sales_events se
          JOIN stores st ON st.id = se.store_id
          GROUP BY st.country
        ),
        cogs AS (
          SELECT st.country,
                 SUM(CASE WHEN ir.currency = 'USD' THEN COALESCE(ir.unit_cost, 0) * ir.received_qty ELSE (COALESCE(ir.unit_cost, 0) * ir.received_qty) / 3950.0 END) AS cogs_usd
          FROM inventory_receipts ir
          JOIN stores st ON st.id = ir.store_id
          GROUP BY st.country
        )
        SELECT r.country,
               ROUND(COALESCE(r.revenue_usd, 0), 2) AS revenue_usd,
               ROUND(COALESCE(c.cogs_usd, 0), 2) AS cogs_usd,
               ROUND(COALESCE(r.revenue_usd, 0) - COALESCE(c.cogs_usd, 0), 2) AS gross_profit_usd,
               CASE
                 WHEN COALESCE(r.revenue_usd, 0) <= 0 THEN 0
                 ELSE ROUND(((COALESCE(r.revenue_usd, 0) - COALESCE(c.cogs_usd, 0)) / r.revenue_usd) * 100.0, 2)
               END AS gross_margin_pct,
               datetime('now') AS generated_at
        FROM rev r
        LEFT JOIN cogs c ON c.country = r.country
        ORDER BY r.country ASC
        """,
    )


def main() -> None:
    ensure_out_dir()

    with sqlite3.connect(DB_PATH) as conn:
        write_csv(
            "dim_store.csv",
            build_dim_store(conn),
            ["store_id", "store_name", "country", "city", "timezone", "base_currency"],
        )
        write_csv(
            "dim_supplier.csv",
            build_dim_supplier(conn),
            ["supplier_id", "supplier_name", "country", "sku", "item_name", "latest_currency", "latest_price", "latest_valid_from"],
        )
        write_csv(
            "fact_sales_daily.csv",
            build_fact_sales_daily(conn),
            ["sales_day", "store_id", "country", "tickets", "total_sales_native", "currency"],
        )
        write_csv(
            "fact_ticket_hourly.csv",
            build_fact_ticket_hourly(conn),
            ["sold_hour_utc", "store_id", "country", "tickets", "avg_ticket_native", "currency"],
        )
        write_csv(
            "fact_inventory_status.csv",
            build_fact_inventory_status(conn),
            ["store_id", "country", "sku", "item_name", "category", "unit", "current_stock", "min_stock", "stock_gap", "risk_level", "updated_at"],
        )
        write_csv(
            "mart_ops_dashboard.csv",
            build_mart_ops_dashboard(conn),
            ["store_id", "store_name", "country", "last_sale_at", "sku_at_risk", "generated_at"],
        )
        write_csv(
            "mart_marketing_dashboard.csv",
            build_mart_marketing_dashboard(conn),
            ["country", "total_customers", "vip_customers", "avg_points", "digital_revenue_native", "generated_at"],
        )
        write_csv(
            "mart_finance_dashboard.csv",
            build_mart_finance_dashboard(conn),
            ["country", "revenue_usd", "cogs_usd", "gross_profit_usd", "gross_margin_pct", "generated_at"],
        )

    print(f"[brasaland-core-pipeline] generated marts in {OUT_DIR}")
    print(f"[brasaland-core-pipeline] finished at {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
