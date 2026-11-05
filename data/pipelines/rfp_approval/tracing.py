"""
Tracing for node execution in the RFP approval flow.

Records every node execution with agent, input, output, and timestamp
for full auditability.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRACE_DIR = Path(__file__).resolve().parents[3] / "data" / "checkpoints"


def _get_trace_db_path() -> str:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    return str(TRACE_DIR / "rfp_traces.db")


def _get_connection() -> sqlite3.Connection:
    db_path = _get_trace_db_path()
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_trace_db() -> None:
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trace_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                node_name TEXT NOT NULL,
                agent TEXT NOT NULL,
                input_json TEXT NOT NULL,
                output_json TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                run_id TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS trace_thread_idx ON trace_entries(thread_id, run_id)
        """)
        conn.commit()
    finally:
        conn.close()


def record_trace_entry(
    thread_id: str,
    node_name: str,
    agent: str,
    input_data: Any,
    output_data: Any,
    run_id: str,
) -> None:
    """Record a single node execution trace."""
    init_trace_db()
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO trace_entries (thread_id, node_name, agent, input_json, output_json, timestamp, run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                thread_id,
                node_name,
                agent,
                json.dumps(input_data, ensure_ascii=False, default=str),
                json.dumps(output_data, ensure_ascii=False, default=str),
                now,
                run_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_trace_for_thread(thread_id: str, run_id: str | None = None) -> list[dict[str, Any]]:
    """Retrieve trace entries for a thread, optionally filtered by run_id."""
    init_trace_db()
    conn = _get_connection()
    try:
        if run_id:
            rows = conn.execute(
                "SELECT * FROM trace_entries WHERE thread_id = ? AND run_id = ? ORDER BY id ASC",
                (thread_id, run_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trace_entries WHERE thread_id = ? ORDER BY id ASC",
                (thread_id,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "thread_id": r["thread_id"],
                "node_name": r["node_name"],
                "agent": r["agent"],
                "input": json.loads(r["input_json"]),
                "output": json.loads(r["output_json"]),
                "timestamp": r["timestamp"],
                "run_id": r["run_id"],
            }
            for r in rows
        ]
    finally:
        conn.close()