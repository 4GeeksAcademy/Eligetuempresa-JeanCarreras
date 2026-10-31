"""
Persistent checkpointer for RFP flow state using SQLite.

Supports thread_id namespacing: rfp-{ticket_id} for ticket-level and
rfp-{ticket_id}:{department} for department-level checkpoints.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(__file__).resolve().parents[3] / "data" / "checkpoints"


def _get_db_path() -> str:
    """Return the path to the shared checkpoint database."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return str(CHECKPOINT_DIR / "rfp_checkpoints.db")


def _get_connection() -> sqlite3.Connection:
    """Get a thread-safe connection to the checkpoint database."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    """Create the checkpoints table if it does not exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flow_checkpoints (
                thread_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_checkpoint(thread_id: str, state: dict[str, Any]) -> None:
    """Persist a checkpoint for the given thread_id."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO flow_checkpoints (thread_id, state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(thread_id) DO UPDATE SET
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (thread_id, json.dumps(state, ensure_ascii=False), now, now),
        )
        conn.commit()
        logger.debug("Checkpoint saved: %s", thread_id)
    finally:
        conn.close()


def load_checkpoint(thread_id: str) -> dict[str, Any] | None:
    """Load a checkpoint for the given thread_id. Returns None if not found."""
    init_db()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT state_json FROM flow_checkpoints WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["state_json"])
    finally:
        conn.close()


def delete_checkpoint(thread_id: str) -> None:
    """Remove a checkpoint (e.g. after flow completes)."""
    init_db()
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM flow_checkpoints WHERE thread_id = ?", (thread_id,))
        conn.commit()
        logger.debug("Checkpoint deleted: %s", thread_id)
    finally:
        conn.close()


def list_checkpoints() -> list[dict[str, Any]]:
    """List all active checkpoints (for admin/debug)."""
    init_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT thread_id, created_at, updated_at FROM flow_checkpoints ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()