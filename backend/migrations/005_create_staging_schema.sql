-- Migration 005: Create discharge_app_staging schema for staging environment
-- Run against care_analytics (production DB) as superuser.
-- After running, set APP_SCHEMA=discharge_app_staging in the staging .env.

CREATE SCHEMA IF NOT EXISTS discharge_app_staging;

CREATE TABLE IF NOT EXISTS discharge_app_staging.app_session (
    id           BIGSERIAL PRIMARY KEY,
    token        TEXT NOT NULL UNIQUE,
    user_email   TEXT NOT NULL,
    user_name    TEXT NOT NULL,
    user_role    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS staging_app_session_token_idx      ON discharge_app_staging.app_session (token);
CREATE INDEX IF NOT EXISTS staging_app_session_expires_at_idx ON discharge_app_staging.app_session (expires_at);

CREATE TABLE IF NOT EXISTS discharge_app_staging.app_user (
    user_email   TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role         TEXT NOT NULL,
    practices    TEXT[],
    is_active    BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS discharge_app_staging.outreach_status (
    event_id                  TEXT        NOT NULL,
    discharge_date            DATE        NOT NULL,
    status                    VARCHAR(50) NOT NULL DEFAULT 'no_outreach',
    updated_by                TEXT,
    updated_at                TIMESTAMPTZ,
    notes                     TEXT,
    discharge_summary_dropped BOOLEAN     NOT NULL DEFAULT FALSE,
    PRIMARY KEY (event_id, discharge_date)
);

CREATE TABLE IF NOT EXISTS discharge_app_staging.outreach_attempts (
    id             BIGSERIAL PRIMARY KEY,
    event_id       TEXT        NOT NULL,
    discharge_date DATE        NOT NULL,
    attempt_number INT         NOT NULL,
    attempted_by   TEXT        NOT NULL,
    attempted_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (event_id, discharge_date, attempt_number)
);

CREATE TABLE IF NOT EXISTS discharge_app_staging.user_activity_log (
    id            BIGSERIAL PRIMARY KEY,
    user_email    TEXT        NOT NULL,
    action        TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata_json TEXT
);

-- Grants for the app DB role
GRANT USAGE ON SCHEMA discharge_app_staging TO discharge_app_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA discharge_app_staging TO discharge_app_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA discharge_app_staging TO discharge_app_role;

-- Copy users from prod so logins work in staging
INSERT INTO discharge_app_staging.app_user
SELECT * FROM discharge_app.app_user
ON CONFLICT (user_email) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        role         = EXCLUDED.role,
        practices    = EXCLUDED.practices,
        is_active    = EXCLUDED.is_active;
