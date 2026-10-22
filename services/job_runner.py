"""State control for nightly jobs persisted in the job_runs table.

State machine: pending -> processing -> completed | failed.
The 'processing' state is the distributed lock: no separate lock table/column.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

MIGRATION_PATH = Path(__file__).resolve().parent / "migrations" / "001_create_job_runs.sql"

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    # Autocommit mode so transactions are explicit (BEGIN IMMEDIATE for the lock).
    conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))


def create_job_run(conn: sqlite3.Connection, job_name: str, target_date: date) -> int:
    cursor = conn.execute(
        "INSERT INTO job_runs (job_name, target_date, status, created_at) VALUES (?, ?, ?, ?)",
        (job_name, target_date.isoformat(), STATUS_PENDING, _now()),
    )
    return int(cursor.lastrowid)


def mark_processing(conn: sqlite3.Connection, run_id: int) -> None:
    conn.execute(
        "UPDATE job_runs SET status = ?, started_at = ? WHERE id = ? AND status = ?",
        (STATUS_PROCESSING, _now(), run_id, STATUS_PENDING),
    )


def mark_completed(conn: sqlite3.Connection, run_id: int) -> None:
    conn.execute(
        "UPDATE job_runs SET status = ?, finished_at = ?, error_message = NULL WHERE id = ?",
        (STATUS_COMPLETED, _now(), run_id),
    )


def mark_failed(conn: sqlite3.Connection, run_id: int, error_message: str) -> None:
    conn.execute(
        "UPDATE job_runs SET status = ?, finished_at = ?, error_message = ? WHERE id = ?",
        (STATUS_FAILED, _now(), error_message[:2000], run_id),
    )


def get_job_run(conn: sqlite3.Connection, run_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM job_runs WHERE id = ?", (run_id,)).fetchone()


def has_processing_lock(conn: sqlite3.Connection, job_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM job_runs WHERE job_name = ? AND status = ? LIMIT 1",
        (job_name, STATUS_PROCESSING),
    ).fetchone()
    return row is not None


def has_completed_for_date(conn: sqlite3.Connection, job_name: str, target_date: date) -> bool:
    row = conn.execute(
        "SELECT 1 FROM job_runs WHERE job_name = ? AND target_date = ? AND status = ? LIMIT 1",
        (job_name, target_date.isoformat(), STATUS_COMPLETED),
    ).fetchone()
    return row is not None


def fail_stale_runs(conn: sqlite3.Connection, job_name: str, stale_after: timedelta) -> int:
    """Release locks left by a hard kill (SIGKILL/power loss) where finally never ran."""
    cutoff = (datetime.now(timezone.utc) - stale_after).isoformat()
    cursor = conn.execute(
        """
        UPDATE job_runs SET status = ?, finished_at = ?, error_message = ?
        WHERE job_name = ? AND status IN (?, ?) AND COALESCE(started_at, created_at) < ?
        """,
        (
            STATUS_FAILED,
            _now(),
            "stale run recovered: process died without releasing lock",
            job_name,
            STATUS_PENDING,
            STATUS_PROCESSING,
            cutoff,
        ),
    )
    return cursor.rowcount


def claim_job_run(conn: sqlite3.Connection, job_name: str, target_date: date) -> tuple[int | None, str]:
    """Atomically check lock + idempotency, then create the run and move it to processing.

    Returns (run_id, reason). run_id is None when the run must be skipped;
    reason is 'locked', 'already_completed' or 'claimed'.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        if has_processing_lock(conn, job_name):
            conn.execute("ROLLBACK")
            return None, "locked"
        if has_completed_for_date(conn, job_name, target_date):
            conn.execute("ROLLBACK")
            return None, "already_completed"
        run_id = create_job_run(conn, job_name, target_date)
        mark_processing(conn, run_id)
        conn.execute("COMMIT")
        return run_id, "claimed"
    except Exception:
        conn.execute("ROLLBACK")
        raise
