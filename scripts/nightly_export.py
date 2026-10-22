#!/usr/bin/env python3
"""Nightly telemetry job (ticket DEV-53).

1. Resolves target_date (env TARGET_DATE=YYYY-MM-DD or yesterday in UTC).
2. Exports store_telemetry_events for target_date to data/raw/telemetry_YYYY-MM-DD.csv
   (backup/audit only, skipped if the file already exists).
3. Runs the data pipeline as an independent subprocess (it reads from the DB, not the CSV).
4. Records the run in job_runs: pending -> processing -> completed | failed.

Runs as a standalone process: it never imports FastAPI nor the API app.
Usage: python scripts/nightly_export.py
"""

from __future__ import annotations

import csv
import logging
import os
import shlex
import signal
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services import job_runner  # noqa: E402

JOB_NAME = "nightly_export"
DB_PATH = Path(os.getenv("BRASALAND_DB_PATH", ROOT / "services" / "brasaland-api" / "brasaland.db"))
RAW_DIR = Path(os.getenv("NIGHTLY_RAW_DIR", ROOT / "data" / "raw"))
DEFAULT_PIPELINE_CMD = [sys.executable, str(ROOT / "data" / "pipelines" / "brasaland-core" / "pipeline.py")]
PIPELINE_TIMEOUT_SECONDS = int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "1800"))
STALE_AFTER = timedelta(minutes=int(os.getenv("JOB_STALE_MINUTES", "180")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s job=%(job)s status=%(status)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger(JOB_NAME)


def log(level: int, status: str, message: str) -> None:
    logger.log(level, message, extra={"job": JOB_NAME, "status": status})


def resolve_target_date() -> date:
    raw = os.getenv("TARGET_DATE", "").strip()
    if raw:
        return date.fromisoformat(raw)
    return datetime.now(timezone.utc).date() - timedelta(days=1)


def export_csv(conn, target_date: date) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"telemetry_{target_date.isoformat()}.csv"
    if out_path.exists():
        log(logging.INFO, "processing", f"csv already exists, skipping export path={out_path}")
        return out_path

    cursor = conn.execute(
        "SELECT * FROM store_telemetry_events WHERE substr(event_ts, 1, 10) = ? ORDER BY id",
        (target_date.isoformat(),),
    )
    columns = [col[0] for col in cursor.description]
    # Write to a temp file and rename so a crash never leaves a partial CSV that looks complete.
    tmp_path = out_path.with_suffix(".csv.tmp")
    rows = 0
    with tmp_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in cursor:
            writer.writerow(tuple(row))
            rows += 1
    os.replace(tmp_path, out_path)
    log(logging.INFO, "processing", f"csv exported rows={rows} path={out_path}")
    return out_path


def run_pipeline(target_date: date) -> None:
    cmd = shlex.split(os.environ["PIPELINE_CMD"]) if os.getenv("PIPELINE_CMD") else DEFAULT_PIPELINE_CMD
    log(logging.INFO, "processing", f"launching pipeline cmd={' '.join(cmd)}")
    env = {**os.environ, "TARGET_DATE": target_date.isoformat()}
    result = subprocess.run(
        cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=PIPELINE_TIMEOUT_SECONDS
    )
    if result.returncode != 0:
        stderr_tail = (result.stderr or result.stdout).strip()[-500:]
        raise RuntimeError(f"pipeline exited with code {result.returncode}: {stderr_tail}")
    log(logging.INFO, "processing", "pipeline finished ok")


def _raise_on_sigterm(signum, _frame) -> None:
    # Turn SIGTERM into an exception so the finally block releases the lock.
    raise SystemExit(f"terminated by signal {signum}")


def main() -> int:
    signal.signal(signal.SIGTERM, _raise_on_sigterm)
    target_date = resolve_target_date()
    conn = job_runner.connect(DB_PATH)
    try:
        job_runner.ensure_schema(conn)
        recovered = job_runner.fail_stale_runs(conn, JOB_NAME, STALE_AFTER)
        if recovered:
            log(logging.WARNING, "failed", f"recovered stale runs count={recovered}")

        run_id, reason = job_runner.claim_job_run(conn, JOB_NAME, target_date)
        if reason == "locked":
            log(logging.INFO, "skipped", f"another instance is processing, aborting target_date={target_date}")
            return 0
        if reason == "already_completed":
            log(logging.INFO, "skipped", f"duplicate run, already completed target_date={target_date}")
            return 0

        log(logging.INFO, "processing", f"started run_id={run_id} target_date={target_date}")
        finished = False
        try:
            export_csv(conn, target_date)
            run_pipeline(target_date)
            job_runner.mark_completed(conn, run_id)
            finished = True
            log(logging.INFO, "completed", f"run_id={run_id} target_date={target_date}")
            return 0
        except Exception as exc:
            job_runner.mark_failed(conn, run_id, f"{type(exc).__name__}: {exc}")
            finished = True
            log(logging.ERROR, "failed", f"run_id={run_id} target_date={target_date} error={exc!r}")
            logger.exception("traceback", extra={"job": JOB_NAME, "status": "failed"})
            return 1
        finally:
            # Covers SystemExit/KeyboardInterrupt: never leave a run in processing.
            if not finished:
                job_runner.mark_failed(conn, run_id, "interrupted before completion")
                log(logging.ERROR, "failed", f"run_id={run_id} interrupted")
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
