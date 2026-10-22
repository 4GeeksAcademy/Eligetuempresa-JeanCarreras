import json
from contextlib import closing
from datetime import datetime
from pathlib import Path
from sqlite3 import connect
from typing import Any

import pandas as pd


DB_PATH = Path(__file__).resolve().parents[2] / "brasaland.db"
TECHNICAL_EVENT_TYPES = (
    "api_latency_recorded",
    "frontend_page_load_recorded",
    "frontend_error_captured",
    "backend_error_captured",
    "auth_login_failed",
    "auth_login_succeeded",
)


def _load_events(
    start_date: datetime,
    end_date: datetime,
    event_types: tuple[str, ...],
    db_path: str | Path,
) -> pd.DataFrame:
    placeholders = ", ".join("?" for _ in event_types)
    query = (
        "SELECT timestamp, event_type, tags FROM telemetry_events "
        "WHERE timestamp >= ? AND timestamp < ? "
        f"AND event_type IN ({placeholders})"
    )
    params = (start_date.isoformat(), end_date.isoformat(), *event_types)
    with closing(connect(db_path)) as connection:
        return pd.read_sql_query(query, connection, params=params)


def _expand_tags(events: pd.DataFrame) -> pd.DataFrame:
    tags = pd.json_normalize(events["tags"].map(json.loads))
    return pd.concat([events.drop(columns=["tags"]).reset_index(drop=True), tags], axis=1)


def _with_utc_date(events: pd.DataFrame) -> pd.DataFrame:
    events["timestamp"] = pd.to_datetime(events["timestamp"], utc=True)
    events["date"] = events["timestamp"].dt.strftime("%Y-%m-%d")
    return events


def events_per_day(
    start_date: datetime, end_date: datetime, db_path: str | Path = DB_PATH
) -> list[dict[str, Any]]:
    events = _load_events(start_date, end_date, TECHNICAL_EVENT_TYPES, db_path)
    if events.empty:
        return []

    events = _with_utc_date(events)
    return (
        events.groupby(["date", "event_type"], as_index=False)
        .agg(event_count=("event_type", "count"))
        .to_dict(orient="records")
    )


def api_latency_by_day(
    start_date: datetime, end_date: datetime, db_path: str | Path = DB_PATH
) -> list[dict[str, Any]]:
    events = _load_events(start_date, end_date, ("api_latency_recorded",), db_path)
    if events.empty:
        return []

    events = _with_utc_date(_expand_tags(events))
    events["duration_ms"] = pd.to_numeric(events["duration_ms"], errors="coerce")
    events["request_count"] = pd.to_numeric(
        events.get("request_count", pd.Series(1, index=events.index)), errors="coerce"
    ).fillna(1).clip(lower=1)
    events["weighted_duration_ms"] = events["duration_ms"] * events["request_count"]
    events = events.dropna(subset=["route_template", "duration_ms"])
    if events.empty:
        return []

    latency = events.groupby(["date", "route_template"], as_index=False).agg(
        request_count=("request_count", "sum"),
        weighted_duration_ms=("weighted_duration_ms", "sum"),
    )
    latency["mean_latency_ms"] = (
        latency["weighted_duration_ms"] / latency["request_count"]
    ).round(2)
    return latency.drop(columns=["weighted_duration_ms"]).to_dict(orient="records")


def error_rate_by_type(
    start_date: datetime, end_date: datetime, db_path: str | Path = DB_PATH
) -> list[dict[str, Any]]:
    events = _load_events(start_date, end_date, ("api_latency_recorded",), db_path)
    if events.empty:
        return []

    events = _with_utc_date(_expand_tags(events))
    events["status_code"] = pd.to_numeric(events["status_code"], errors="coerce")
    events["request_count"] = pd.to_numeric(
        events.get("request_count", pd.Series(1, index=events.index)), errors="coerce"
    ).fillna(1).clip(lower=1)
    events = events.dropna(subset=["route_template", "status_code"])
    if events.empty:
        return []

    events["error_count"] = events["request_count"].where(events["status_code"] >= 500, 0)
    errors = events.groupby(
        ["date", "event_type", "route_template"], as_index=False
    ).agg(
        request_count=("request_count", "sum"),
        error_count=("error_count", "sum"),
    )
    errors["error_rate_pct"] = (errors["error_count"] / errors["request_count"] * 100).round(2)
    return errors.to_dict(orient="records")


def auth_failure_rate(
    start_date: datetime, end_date: datetime, db_path: str | Path = DB_PATH
) -> list[dict[str, Any]]:
    events = _load_events(
        start_date, end_date, ("auth_login_failed", "auth_login_succeeded"), db_path
    )
    if events.empty:
        return []

    events = _with_utc_date(events)
    events["is_failure"] = events["event_type"].eq("auth_login_failed")
    failures = events.groupby("date", as_index=False).agg(
        failed_attempts=("is_failure", "sum"),
        total_attempts=("is_failure", "count"),
    )
    failures["failure_rate_pct"] = (
        failures["failed_attempts"] / failures["total_attempts"] * 100
    ).round(2)
    return failures.to_dict(orient="records")


def _load_store_events(
    start_date: datetime,
    end_date: datetime,
    db_path: str | Path,
) -> pd.DataFrame:
    query = """
        SELECT event_ts, source_system, pos_online
        FROM store_telemetry_events
        WHERE event_ts >= ? AND event_ts < ?
    """
    with closing(connect(db_path)) as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=(start_date.isoformat(), end_date.isoformat()),
        )


def availability_by_day_and_source(
    start_date: datetime, end_date: datetime, db_path: str | Path = DB_PATH
) -> list[dict[str, Any]]:
    events = _load_store_events(start_date, end_date, db_path)
    if events.empty:
        return []

    events["timestamp"] = pd.to_datetime(events["event_ts"], utc=True)
    events["date"] = events["timestamp"].dt.strftime("%Y-%m-%d")
    events["is_online"] = events["pos_online"].astype(bool)
    availability = events.groupby(["date", "source_system"], as_index=False).agg(
        event_count=("is_online", "count"),
        online_count=("is_online", "sum"),
        availability_pct=("is_online", "mean"),
    )
    availability["availability_pct"] = (availability["availability_pct"] * 100).round(2)
    return availability.to_dict(orient="records")