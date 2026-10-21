-- Orchestration layer for nightly jobs. Not to be merged with pipeline_runs (ETL layer).
CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    target_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    started_at TEXT,
    finished_at TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_job_runs_job_name_target_date
    ON job_runs (job_name, target_date);

CREATE INDEX IF NOT EXISTS idx_job_runs_job_name_status
    ON job_runs (job_name, status);
