from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from data.pipelines.pipeline import get_reporting_db_path, run_business_performance_pipeline


def create_reporting_router(
    require_roles: Callable[[set[str]], Any],
    source_db_path_provider: Callable[[], Path],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/reporting", tags=["reporting"])

    @router.get("/pipeline/status")
    def get_pipeline_status(
        _: str = Depends(require_roles({"executive", "finance", "admin"})),
    ) -> dict[str, Any]:
        reporting_path = get_reporting_db_path()
        if not reporting_path.exists():
            return {"run": None}
        with sqlite3.connect(reporting_path) as connection:
            connection.row_factory = sqlite3.Row
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'pipeline_runs'"
            ).fetchone()
            if exists is None:
                return {"run": None}
            row = connection.execute(
                "SELECT * FROM pipeline_runs ORDER BY started_at DESC, run_id DESC LIMIT 1"
            ).fetchone()
        return {"run": dict(row) if row else None}

    @router.post("/pipeline/run")
    def trigger_pipeline(
        _: str = Depends(require_roles({"admin"})),
    ) -> dict[str, Any]:
        result = run_business_performance_pipeline(
            source_db_path=str(source_db_path_provider()),
            reporting_db_path=str(get_reporting_db_path()),
        )
        return result

    @router.get("/kpis")
    def get_reporting_kpis(
        country: Literal["CO", "US"] | None = Query(default=None),
        store_id: str | None = Query(default=None, min_length=1),
        start_date: str | None = Query(default=None),
        end_date: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        _: str = Depends(require_roles({"executive", "finance", "admin"})),
    ) -> dict[str, Any]:
        reporting_path = get_reporting_db_path()
        if not reporting_path.exists():
            return {"rows": [], "count": 0}

        conditions = []
        parameters: list[Any] = []
        for column, value in (
            ("country", country),
            ("store_id", store_id),
            ("metric_date >=", start_date),
            ("metric_date <=", end_date),
        ):
            if value is not None:
                if column.startswith("metric_date"):
                    conditions.append(f"{column} ?")
                else:
                    conditions.append(f"{column} = ?")
                parameters.append(value)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with sqlite3.connect(reporting_path) as connection:
            connection.row_factory = sqlite3.Row
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'telemetry_daily_kpis'"
            ).fetchone()
            if exists is None:
                return {"rows": [], "count": 0}
            rows = connection.execute(
                f"SELECT * FROM telemetry_daily_kpis {where} "
                "ORDER BY metric_date DESC, store_id LIMIT ?",
                (*parameters, limit),
            ).fetchall()
        result = [dict(row) for row in rows]
        return {"rows": result, "count": len(result)}

    return router