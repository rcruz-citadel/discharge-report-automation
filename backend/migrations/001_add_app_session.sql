-- Migration 001: Add app_session table for V3 React auth
-- Run on: DMZ PostgreSQL (production database)
-- Schema: discharge_app
-- Depends on: discharge_app schema, discharge_app_role role already existing

-- ============================================================
-- 1. Create app_session table
-- ============================================================

CREATE TABLE IF NOT EXISTS discharge_app.app_session (
    id           BIGSERIAL PRIMARY KEY,
    token        TEXT NOT NULL UNIQUE,
    user_email   TEXT NOT NULL,
    user_name    TEXT NOT NULL,
    user_role    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS app_session_token_idx      ON discharge_app.app_session (token);
CREATE INDEX IF NOT EXISTS app_session_expires_at_idx ON discharge_app.app_session (expires_at);

COMMENT ON TABLE discharge_app.app_session IS
    'Server-side session store for V3 React app. Token is a 32-byte random hex string (not a JWT). TTL = 8 hours.';

-- ============================================================
-- 2. Grants for discharge_app_role
-- ============================================================

-- v_discharge_summary (SELECT only — view is read-only)
GRANT SELECT ON v_discharge_summary TO discharge_app_role;

-- outreach_status (full CRUD for outreach updates)
GRANT SELECT, INSERT, UPDATE, DELETE ON discharge_app.outreach_status TO discharge_app_role;

-- app_session (full CRUD for session management)
GRANT SELECT, INSERT, UPDATE, DELETE ON discharge_app.app_session TO discharge_app_role;
GRANT USAGE, SELECT ON SEQUENCE discharge_app.app_session_id_seq TO discharge_app_role;

-- user_activity_log (INSERT + SELECT for activity tracking)
GRANT SELECT, INSERT ON discharge_app.user_activity_log TO discharge_app_role;

-- app_user (SELECT only — user records managed by admins)
GRANT SELECT ON discharge_app.app_user TO discharge_app_role;

-- ============================================================
-- 3. Optional: pg_cron cleanup job (run as superuser if pg_cron available)
-- ============================================================
-- SELECT cron.schedule('cleanup-expired-sessions', '0 * * * *',
--     $$DELETE FROM discharge_app.app_session WHERE expires_at < now()$$);

-- ============================================================
-- 4. Verify view has all required columns (informational check)
-- ============================================================
-- Run this to confirm v_discharge_summary is complete:
--
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'v_discharge_summary'
-- ORDER BY ordinal_position;
--
-- Required columns:
--   event_id, discharge_date, patient_name, insurance_member_id,
--   location_name (aliased as practice in backend query), payer_name,
--   lob_name, stay_type, discharge_hospital, length_of_stay,
--   disposition, dx_code, description, admit_date
--
-- NOTE: The view has location_name (not practice). The backend SQL
-- aliases it: SELECT ..., location_name AS practice, ... FROM v_discharge_summary
