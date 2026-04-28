-- Migration 003: Add discharge_summary_dropped to outreach_status
-- Tracks whether a coordinator dropped the discharge summary in EMR
-- for records in the low-priority queue (past TCM time window).

ALTER TABLE discharge_app.outreach_status
    ADD COLUMN IF NOT EXISTS discharge_summary_dropped BOOLEAN NOT NULL DEFAULT FALSE;
