from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from prefect import flow, task
from prefect.states import State
from prefect.tasks import task_input_hash

LOGGER = logging.getLogger(__name__)
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DB_PATH = Path(
    os.getenv(
        "BRASALAND_SQLITE_DB_PATH",
        str(REPOSITORY_ROOT / "services/brasaland-api/brasaland.db"),
    )
)
REPORTING_DB_PATH = Path(
    os.getenv(
        "BRASALAND_REPORTING_DB_PATH",
        str(REPOSITORY_ROOT / "data/process/reporting.db"),
    )
)
UTC = timezone.utc


def get_reporting_db_path() -> Path:
    return Path(os.getenv("BRASALAND_REPORTING_DB_PATH", str(REPORTING_DB_PATH)))


@task(retries=3, retry_delay_seconds=2)
def extract_telemetry_events(source_db_path: str) -> list[dict[str, Any]]:
    source_path = Path(source_db_path).resolve()
    connection = sqlite3.connect(f"{source_path.as_uri()}?mode=ro", uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT event.id, event.store_id, store.name AS store_name,
                   store.country, event.event_ts, event.ingested_at,
                   event.latency_seconds, event.pos_online,
                   event.sales_last_5m, event.open_tickets,
                   event.avg_prep_seconds, event.network_rtt_ms
            FROM store_telemetry_events AS event
            JOIN stores AS store ON store.id = event.store_id
            ORDER BY event.event_ts, event.id
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@task(
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(minutes=15),
    persist_result=True,
)
def transform_telemetry_events(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    aggregates: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "event_count": 0,
            "online_count": 0,
            "sales_last_5m_total": 0,
            "open_tickets_total": 0,
            "avg_prep_seconds_total": 0.0,
            "network_rtt_ms_total": 0.0,
            "latency_seconds_total": 0.0,
        }
    )

    for event in events:
        event_time = datetime.fromisoformat(
            str(event["event_ts"]).replace("Z", "+00:00")
        )
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=UTC)
        date = event_time.astimezone(UTC).date().isoformat()
        key = (str(event["store_id"]), date)
        totals = aggregates[key]
        totals["store_id"] = str(event["store_id"])
        totals["store_name"] = str(event["store_name"])
        totals["country"] = str(event["country"])
        totals["event_count"] += 1
        totals["online_count"] += int(bool(event["pos_online"]))
        totals["sales_last_5m_total"] += int(event["sales_last_5m"])
        totals["open_tickets_total"] += int(event["open_tickets"])
        totals["avg_prep_seconds_total"] += float(event["avg_prep_seconds"])
        totals["network_rtt_ms_total"] += float(event["network_rtt_ms"])
        totals["latency_seconds_total"] += float(event["latency_seconds"])

    results = []
    for (_, date), totals in sorted(aggregates.items()):
        count = totals["event_count"]
        results.append(
            {
                "store_id": totals["store_id"],
                "store_name": totals["store_name"],
                "country": totals["country"],
                "metric_date": date,
                "telemetry_events": count,
                "pos_online_pct": round(totals["online_count"] * 100 / count, 2),
                "avg_sales_last_5m": round(totals["sales_last_5m_total"] / count, 2),
                "avg_open_tickets": round(totals["open_tickets_total"] / count, 2),
                "avg_prep_seconds": round(totals["avg_prep_seconds_total"] / count, 2),
                "avg_network_rtt_ms": round(totals["network_rtt_ms_total"] / count, 2),
                "avg_latency_seconds": round(totals["latency_seconds_total"] / count, 2),
            }
        )
    return results


@task
def validate_reporting_rows(rows: list[dict[str, Any]]) -> bool:
    required_fields = {
        "store_id",
        "store_name",
        "country",
        "metric_date",
        "telemetry_events",
        "pos_online_pct",
    }
    for row in rows:
        if not required_fields.issubset(row):
            raise ValueError("KPI row is missing required fields")
        if row["country"] not in {"CO", "US"}:
            raise ValueError(f"Unsupported country in KPI row: {row['country']}")
        if not 0 <= row["pos_online_pct"] <= 100:
            raise ValueError("pos_online_pct must be between 0 and 100")
    return True


def _connect_reporting_db(reporting_db_path: str) -> sqlite3.Connection:
    path = Path(reporting_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def _create_reporting_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS telemetry_daily_kpis (
            store_id TEXT NOT NULL,
            store_name TEXT NOT NULL,
            country TEXT NOT NULL CHECK (country IN ('CO', 'US')),
            metric_date TEXT NOT NULL,
            telemetry_events INTEGER NOT NULL,
            pos_online_pct REAL NOT NULL,
            avg_sales_last_5m REAL NOT NULL,
            avg_open_tickets REAL NOT NULL,
            avg_prep_seconds REAL NOT NULL,
            avg_network_rtt_ms REAL NOT NULL,
            avg_latency_seconds REAL NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (store_id, metric_date)
        );
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('completed', 'failed')),
            records_processed INTEGER NOT NULL,
            kpi_rows_written INTEGER NOT NULL,
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_telemetry_daily_kpis_country_date
            ON telemetry_daily_kpis (country, metric_date);
        """
    )


@task(retries=2, retry_delay_seconds=2)
def load_reporting_rows(
    rows: list[dict[str, Any]],
    *,
    run_id: str,
    started_at: str,
    records_processed: int,
    reporting_db_path: str,
) -> dict[str, Any]:
    finished_at = datetime.now(UTC).isoformat()
    connection = _connect_reporting_db(reporting_db_path)
    try:
        with connection:
            _create_reporting_schema(connection)
            connection.executemany(
                """
                INSERT INTO telemetry_daily_kpis (
                    store_id, store_name, country, metric_date, telemetry_events,
                    pos_online_pct, avg_sales_last_5m, avg_open_tickets,
                    avg_prep_seconds, avg_network_rtt_ms, avg_latency_seconds,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(store_id, metric_date) DO UPDATE SET
                    store_name = excluded.store_name,
                    country = excluded.country,
                    telemetry_events = excluded.telemetry_events,
                    pos_online_pct = excluded.pos_online_pct,
                    avg_sales_last_5m = excluded.avg_sales_last_5m,
                    avg_open_tickets = excluded.avg_open_tickets,
                    avg_prep_seconds = excluded.avg_prep_seconds,
                    avg_network_rtt_ms = excluded.avg_network_rtt_ms,
                    avg_latency_seconds = excluded.avg_latency_seconds,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        row["store_id"],
                        row["store_name"],
                        row["country"],
                        row["metric_date"],
                        row["telemetry_events"],
                        row["pos_online_pct"],
                        row["avg_sales_last_5m"],
                        row["avg_open_tickets"],
                        row["avg_prep_seconds"],
                        row["avg_network_rtt_ms"],
                        row["avg_latency_seconds"],
                        finished_at,
                    )
                    for row in rows
                ],
            )
            connection.execute(
                """
                INSERT INTO pipeline_runs (
                    run_id, started_at, finished_at, status,
                    records_processed, kpi_rows_written, error
                ) VALUES (?, ?, ?, 'completed', ?, ?, NULL)
                """,
                (run_id, started_at, finished_at, records_processed, len(rows)),
            )
        return {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": "completed",
            "records_processed": records_processed,
            "kpi_rows_written": len(rows),
            "error": None,
        }
    finally:
        connection.close()


@task(retries=2, retry_delay_seconds=2)
def record_failed_run(
    *,
    run_id: str,
    started_at: str,
    records_processed: int,
    reporting_db_path: str,
    error: str,
) -> None:
    finished_at = datetime.now(UTC).isoformat()
    connection = _connect_reporting_db(reporting_db_path)
    try:
        with connection:
            _create_reporting_schema(connection)
            connection.execute(
                """
                INSERT INTO pipeline_runs (
                    run_id, started_at, finished_at, status,
                    records_processed, kpi_rows_written, error
                ) VALUES (?, ?, ?, 'failed', ?, 0, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    finished_at = excluded.finished_at,
                    status = excluded.status,
                    records_processed = excluded.records_processed,
                    error = excluded.error
                """,
                (run_id, started_at, finished_at, records_processed, error[:1000]),
            )
    finally:
        connection.close()


@flow(name="extract-telemetry-subflow")
def extract_telemetry_subflow(source_db_path: str | None = None) -> list[dict[str, Any]]:
    """Subflow encargado de la fase de extracción."""
    return extract_telemetry_events(str(source_db_path or SOURCE_DB_PATH))


@flow(name="transform-telemetry-subflow")
def transform_telemetry_subflow(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Subflow encargado de la fase de transformación y validación."""
    kpis = transform_telemetry_events(events)
    validation_state: State = validate_reporting_rows(kpis, return_state=True)
    if validation_state.is_failed():
        validation_state.result(raise_on_failure=True)
    return kpis


@flow(name="load-telemetry-subflow")
def load_telemetry_subflow(
    kpis: list[dict[str, Any]],
    *,
    run_id: str,
    started_at: str,
    records_processed: int,
    reporting_db_path: str,
) -> dict[str, Any]:
    """Subflow encargado de la fase de carga a la base de datos de reporting."""
    return load_reporting_rows(
        kpis,
        run_id=run_id,
        started_at=started_at,
        records_processed=records_processed,
        reporting_db_path=reporting_db_path,
    )


@flow(name="brasaland-business-performance-pipeline")
def run_business_performance_pipeline(
    source_db_path: str | None = None,
    reporting_db_path: str | None = None,
) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    started_at = datetime.now(UTC).isoformat()
    destination = str(reporting_db_path or get_reporting_db_path())
    records_processed = 0
    try:
        events = extract_telemetry_subflow(source_db_path)
        records_processed = len(events)
        kpis = transform_telemetry_subflow(events)
        result = load_telemetry_subflow(
            kpis,
            run_id=run_id,
            started_at=started_at,
            records_processed=records_processed,
            reporting_db_path=destination,
        )
        LOGGER.info("Reporting pipeline completed: %s", result)
        return result
    except Exception as error:
        try:
            record_failed_run(
                run_id=run_id,
                started_at=started_at,
                records_processed=records_processed,
                reporting_db_path=destination,
                error=f"{type(error).__name__}: {error}",
            )
        except Exception:
            LOGGER.exception("Unable to persist reporting pipeline failure metadata")
        LOGGER.exception("Reporting pipeline failed (run_id=%s)", run_id)
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_business_performance_pipeline()