"""Tests para el pipeline de desempeño de negocio.

Verifica los tres subflows (extracción, transformación, carga)
usando datos en memoria sin depender de la base de datos de producción.
"""

import sqlite3
from datetime import datetime, timezone

import pytest

from data.pipelines.pipeline import (
    extract_telemetry_subflow,
    transform_telemetry_subflow,
    load_telemetry_subflow,
    extract_telemetry_events,
    transform_telemetry_events,
    load_reporting_rows,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def source_db(tmp_path):
    """Crea una base de datos fuente con telemetría de ejemplo."""
    path = tmp_path / "source.db"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE stores (id TEXT PRIMARY KEY, name TEXT, country TEXT);
            CREATE TABLE store_telemetry_events (
                id INTEGER PRIMARY KEY,
                store_id TEXT,
                event_ts TEXT,
                ingested_at TEXT,
                latency_seconds REAL,
                pos_online INTEGER,
                sales_last_5m INTEGER,
                open_tickets INTEGER,
                avg_prep_seconds REAL,
                network_rtt_ms REAL
            );
            INSERT INTO stores VALUES ('med-001', 'Medellin Centro', 'CO');
            INSERT INTO stores VALUES ('mia-001', 'Miami Brickell', 'US');
            INSERT INTO store_telemetry_events VALUES
                (1, 'med-001', '2026-10-12T10:00:00+00:00', '2026-10-12T10:00:01+00:00', 1, 1, 2, 3, 120, 15),
                (2, 'med-001', '2026-10-12T10:05:00+00:00', '2026-10-12T10:05:01+00:00', 1, 0, 4, 1, 180, 25),
                (3, 'mia-001', '2026-10-12T11:00:00+00:00', '2026-10-12T11:00:02+00:00', 2, 1, 5, 2, 90, 10);
        """)
    return str(path)


@pytest.fixture
def extracted_events(source_db):
    """Eventos extraídos listos para transformación."""
    return extract_telemetry_events.fn(source_db)


@pytest.fixture
def sample_kpis():
    """Filas de KPI prefabricadas para pruebas de carga."""
    return [
        {
            "store_id": "med-001",
            "store_name": "Medellin Centro",
            "country": "CO",
            "metric_date": "2026-10-12",
            "telemetry_events": 2,
            "pos_online_pct": 50.0,
            "avg_sales_last_5m": 3.0,
            "avg_open_tickets": 2.0,
            "avg_prep_seconds": 150.0,
            "avg_network_rtt_ms": 20.0,
            "avg_latency_seconds": 1.0,
        }
    ]


# ---------------------------------------------------------------------------
# Extract subflow
# ---------------------------------------------------------------------------

class TestExtractSubflow:
    """extract_telemetry_subflow —— lectura sin efectos secundarios."""

    def test_extract_returns_events(self, source_db):
        events = extract_telemetry_subflow.fn(source_db)
        assert len(events) == 3
        assert all(e["store_id"] in ("med-001", "mia-001") for e in events)
        assert all(e["country"] in ("CO", "US") for e in events)

    def test_extract_does_not_modify_source(self, source_db):
        _ = extract_telemetry_subflow.fn(source_db)
        with sqlite3.connect(source_db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM store_telemetry_events"
            ).fetchone()[0]
        assert count == 3

    def test_extract_empty_db_returns_empty_list(self, tmp_path):
        empty = tmp_path / "empty.db"
        with sqlite3.connect(empty) as conn:
            conn.execute("CREATE TABLE stores (id TEXT PRIMARY KEY, name TEXT, country TEXT)")
            conn.execute(
                "CREATE TABLE store_telemetry_events ("
                "id INTEGER PRIMARY KEY, store_id TEXT, event_ts TEXT, "
                "ingested_at TEXT, latency_seconds REAL, pos_online INTEGER, "
                "sales_last_5m INTEGER, open_tickets INTEGER, "
                "avg_prep_seconds REAL, network_rtt_ms REAL)"
            )
        events = extract_telemetry_subflow.fn(str(empty))
        assert events == []


# ---------------------------------------------------------------------------
# Transform subflow
# ---------------------------------------------------------------------------

class TestTransformSubflow:
    """transform_telemetry_subflow —— agregación diaria por local."""

    def test_transform_computes_kpis(self, extracted_events):
        kpis = transform_telemetry_subflow.fn(extracted_events)
        assert len(kpis) == 2  # med-001 y mia-001
        med = [k for k in kpis if k["store_id"] == "med-001"][0]
        assert med["telemetry_events"] == 2
        assert med["pos_online_pct"] == 50.0
        assert med["avg_sales_last_5m"] == 3.0  # (2 + 4) / 2
        assert med["avg_prep_seconds"] == 150.0  # (120 + 180) / 2

    def test_transform_kpi_calculated_by_hand(self, extracted_events):
        """Verifica un KPI con valor calculado manualmente."""
        kpis = transform_telemetry_subflow.fn(extracted_events)
        mia = [k for k in kpis if k["store_id"] == "mia-001"][0]
        # mia-001 tiene 1 evento, sales_last_5m = 5, open_tickets = 2
        # pos_online_pct = 100 * (1 / 1) = 100
        # avg_sales_last_5m = 5 / 1 = 5
        assert mia["pos_online_pct"] == 100.0
        assert mia["avg_sales_last_5m"] == 5.0
        assert mia["avg_open_tickets"] == 2.0
        assert mia["avg_prep_seconds"] == 90.0
        assert mia["avg_network_rtt_ms"] == 10.0
        assert mia["avg_latency_seconds"] == 2.0

    def test_transform_empty_events(self):
        kpis = transform_telemetry_subflow.fn([])
        assert kpis == []

    def test_transform_invalid_event_raises(self):
        """Un evento sin store_id debe producir error."""
        with pytest.raises((KeyError, TypeError, ValueError)):
            transform_telemetry_subflow.fn([{"not_store_id": "x"}])


# ---------------------------------------------------------------------------
# Load subflow
# ---------------------------------------------------------------------------

class TestLoadSubflow:
    """load_telemetry_subflow —— escritura idempotente en reporting."""

    def test_load_writes_kpis(self, tmp_path, sample_kpis):
        db_path = tmp_path / "reporting.db"
        started_at = datetime.now(timezone.utc).isoformat()

        result = load_telemetry_subflow.fn(
            sample_kpis,
            run_id="run-test-1",
            started_at=started_at,
            records_processed=1,
            reporting_db_path=str(db_path),
        )
        assert result["status"] == "completed"
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT * FROM telemetry_daily_kpis").fetchall()
        assert len(rows) == 1

    def test_load_is_idempotent(self, tmp_path, sample_kpis):
        """Cargar los mismos KPIs dos veces no duplica filas."""
        db_path = tmp_path / "reporting.db"
        started_at = datetime.now(timezone.utc).isoformat()

        for run_id in ("run-a", "run-b"):
            load_telemetry_subflow.fn(
                sample_kpis,
                run_id=run_id,
                started_at=started_at,
                records_processed=1,
                reporting_db_path=str(db_path),
            )

        with sqlite3.connect(db_path) as conn:
            kpi_count = conn.execute(
                "SELECT COUNT(*) FROM telemetry_daily_kpis"
            ).fetchone()[0]
            run_count = conn.execute(
                "SELECT COUNT(*) FROM pipeline_runs"
            ).fetchone()[0]
        assert kpi_count == 1  # upsert no duplica
        assert run_count == 2  # cada ejecución sí se registra

    def test_load_empty_kpis(self, tmp_path):
        db_path = tmp_path / "reporting.db"
        started_at = datetime.now(timezone.utc).isoformat()

        result = load_telemetry_subflow.fn(
            [],
            run_id="run-empty",
            started_at=started_at,
            records_processed=0,
            reporting_db_path=str(db_path),
        )
        assert result["status"] == "completed"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM telemetry_daily_kpis"
            ).fetchone()[0] == 0
            assert conn.execute(
                "SELECT COUNT(*) FROM pipeline_runs"
            ).fetchone()[0] == 1