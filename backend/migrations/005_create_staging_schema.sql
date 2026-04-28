-- Migration 005: Create discharge_app_staging schema for staging environment
-- Clones the discharge_app schema structure without copying data.
-- Run once on care_analytics (production DB) to set up the staging schema.
--
-- After running this, set APP_SCHEMA=discharge_app_staging in the staging .env.

CREATE SCHEMA IF NOT EXISTS discharge_app_staging;

CREATE TABLE IF NOT EXISTS discharge_app_staging.app_session (LIKE discharge_app.app_session INCLUDING ALL);
CREATE TABLE IF NOT EXISTS discharge_app_staging.app_user    (LIKE discharge_app.app_user    INCLUDING ALL);
CREATE TABLE IF NOT EXISTS discharge_app_staging.outreach_status (LIKE discharge_app.outreach_status INCLUDING ALL);
CREATE TABLE IF NOT EXISTS discharge_app_staging.outreach_attempts (LIKE discharge_app.outreach_attempts INCLUDING ALL);
CREATE TABLE IF NOT EXISTS discharge_app_staging.user_activity_log (LIKE discharge_app.user_activity_log INCLUDING ALL);

-- Copy users from prod so logins work in staging
INSERT INTO discharge_app_staging.app_user
SELECT * FROM discharge_app.app_user
ON CONFLICT (user_email) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        role         = EXCLUDED.role,
        practices    = EXCLUDED.practices,
        is_active    = EXCLUDED.is_active;
