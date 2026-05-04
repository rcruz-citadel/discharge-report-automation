-- Migration 007: status_history table, original_failure_reason column, metadata_json fix
--
-- 1. Add original_failure_reason to outreach_status (set once by system, never cleared)
-- 2. Create status_history for full audit trail of coordinator overrides
-- 3. Fix missing metadata_json column in discharge_app_staging.user_activity_log

-- ── discharge_app (production) ────────────────────────────────────────────────

ALTER TABLE discharge_app.outreach_status
    ADD COLUMN IF NOT EXISTS original_failure_reason TEXT;

-- Backfill: records already flagged get their failure_reason copied over
UPDATE discharge_app.outreach_status
SET original_failure_reason = failure_reason
WHERE failure_reason IS NOT NULL
  AND original_failure_reason IS NULL;

CREATE TABLE IF NOT EXISTS discharge_app.status_history (
    id              BIGSERIAL PRIMARY KEY,
    event_id        TEXT        NOT NULL,
    discharge_date  DATE        NOT NULL,
    old_status      TEXT,
    new_status      TEXT        NOT NULL,
    old_failure_reason TEXT,
    changed_by      TEXT        NOT NULL,
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS status_history_event_idx
    ON discharge_app.status_history (event_id, discharge_date);

-- ── discharge_app_staging ─────────────────────────────────────────────────────

ALTER TABLE discharge_app_staging.outreach_status
    ADD COLUMN IF NOT EXISTS original_failure_reason TEXT;

UPDATE discharge_app_staging.outreach_status
SET original_failure_reason = failure_reason
WHERE failure_reason IS NOT NULL
  AND original_failure_reason IS NULL;

CREATE TABLE IF NOT EXISTS discharge_app_staging.status_history (
    id              BIGSERIAL PRIMARY KEY,
    event_id        TEXT        NOT NULL,
    discharge_date  DATE        NOT NULL,
    old_status      TEXT,
    new_status      TEXT        NOT NULL,
    old_failure_reason TEXT,
    changed_by      TEXT        NOT NULL,
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS status_history_event_idx
    ON discharge_app_staging.status_history (event_id, discharge_date);

-- Fix missing metadata_json column in staging user_activity_log
ALTER TABLE discharge_app_staging.user_activity_log
    ADD COLUMN IF NOT EXISTS metadata_json TEXT;
