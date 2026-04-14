-- =============================================================================
-- V2 Database Setup — Discharge Report Automation
-- Citadel Health / Aylo Health
-- Generated: 2026-04-13
-- Run as: superuser or schema owner on CITADELBMI001 PostgreSQL instance
-- =============================================================================

-- =============================================================================
-- SECTION 0: SCHEMA DECISION
-- =============================================================================
--
-- RECOMMENDATION: Use a NEW schema named "discharge_app"
--
-- Rationale:
--   - The public schema already holds ~90 tables (claims, eligibility, ETL, etc.)
--     that are owned by upstream data pipelines. Mixing app-layer tables into
--     that namespace creates confusion about ownership and makes permission grants
--     harder to reason about.
--   - A dedicated schema lets you GRANT USAGE ON SCHEMA discharge_app TO app_role
--     without touching public schema permissions — principle of least privilege.
--   - It signals clearly in any DB explorer that these tables are "owned" by
--     the Streamlit application, not the ETL/claims pipeline.
--   - The discharge_event table and its dimension tables stay in public — the
--     app schema tables reference them via cross-schema FKs (fully supported).
--   - Schema creation is cheap and reversible. The downside (slightly longer
--     qualified names) is negligible.
--
-- How the app connects: set search_path = discharge_app, public
-- in the DATABASE_URL or as a connection default so unqualified names resolve
-- to discharge_app first, then public (for discharge_event FK targets).
-- Example: postgresql://user:pass@host/dbname?options=-c search_path=discharge_app,public
--
-- If you prefer to keep everything in public (simpler connection string, no
-- search_path needed), just remove the schema qualification and the CREATE SCHEMA
-- line — the DDL is otherwise identical.

CREATE SCHEMA IF NOT EXISTS discharge_app;

-- Set search path for this session so unqualified names below resolve correctly
SET search_path = discharge_app, public;


-- =============================================================================
-- SECTION 1: app_user
-- User registry with role and practice assignments.
-- Replaces the hardcoded PRACTICE_ASSIGNMENTS dict in streamlit_app.py.
-- =============================================================================

CREATE TABLE IF NOT EXISTS discharge_app.app_user (
    user_email   TEXT        PRIMARY KEY
                             CHECK (user_email = LOWER(user_email)),  -- enforce lowercase
    display_name TEXT        NOT NULL,
    role         TEXT        NOT NULL DEFAULT 'staff'
                             CHECK (role IN ('staff', 'manager')),
    practices    TEXT[]      NOT NULL DEFAULT '{}',
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  discharge_app.app_user              IS 'Application users with roles and practice assignments. Replaces PRACTICE_ASSIGNMENTS dict.';
COMMENT ON COLUMN discharge_app.app_user.user_email   IS 'SSO email from Entra ID — must match st.session_state["user_email"] exactly (lowercase enforced).';
COMMENT ON COLUMN discharge_app.app_user.role         IS 'staff = outreach worker; manager = can see manager analytics view.';
COMMENT ON COLUMN discharge_app.app_user.practices    IS 'Array of practice names this user is assigned to. Matches l.parent_org values in the discharge query.';
COMMENT ON COLUMN discharge_app.app_user.is_active    IS 'Soft-delete flag. Set FALSE to deactivate without losing history.';

-- Index: filter users by role (manager gate check on every page load)
CREATE INDEX IF NOT EXISTS app_user_role_idx
    ON discharge_app.app_user (role)
    WHERE is_active = TRUE;

-- Note: LOWER() index omitted — the CHECK constraint already enforces lowercase,
-- so the PK index covers all lookups.


-- =============================================================================
-- SECTION 2: outreach_status
-- One row per discharge event, tracking the latest outreach state.
-- Uses INSERT ... ON CONFLICT DO UPDATE (upsert) pattern from the app.
-- =============================================================================

-- NOTE ON KEY DESIGN (DMZ INSTANCE):
-- discharge_event PK on DMZ is composite: (event_id, source_event_key).
-- event_id alone is NOT unique — same patient can have multiple discharges.
-- However, (event_id, discharge_date) IS unique — each combo = one discharge occurrence.
-- Outreach is tracked per discharge occurrence, so we key on (event_id, discharge_date).
-- No FK constraint (composite PK mismatch makes it impractical) — referential integrity
-- is enforced at the application layer.

CREATE TABLE IF NOT EXISTS discharge_app.outreach_status (
    outreach_id    BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id       TEXT        NOT NULL,
    discharge_date DATE        NOT NULL,
    status         TEXT        NOT NULL DEFAULT 'no_outreach'
                               CHECK (status IN ('no_outreach', 'outreach_made', 'outreach_complete')),
    updated_by     TEXT        NOT NULL,   -- user_email from SSO (not FK — log survives user deactivation)
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes          TEXT                    -- optional free-text note per status change
);

COMMENT ON TABLE  discharge_app.outreach_status                  IS 'Current outreach status per discharge occurrence. One row per (event_id, discharge_date) pair.';
COMMENT ON COLUMN discharge_app.outreach_status.event_id         IS 'Patient event identifier from discharge_event. Not a FK due to composite PK on DMZ.';
COMMENT ON COLUMN discharge_app.outreach_status.discharge_date   IS 'Discharge date — combined with event_id forms the unique key for one discharge occurrence.';
COMMENT ON COLUMN discharge_app.outreach_status.status           IS 'no_outreach | outreach_made | outreach_complete';
COMMENT ON COLUMN discharge_app.outreach_status.updated_by       IS 'SSO email of the user who last changed the status.';
COMMENT ON COLUMN discharge_app.outreach_status.notes            IS 'Optional free-text. Shown per row in the outreach UI.';

-- Unique constraint: one outreach status per discharge occurrence.
-- App upserts with: INSERT ... ON CONFLICT (event_id, discharge_date) DO UPDATE
CREATE UNIQUE INDEX IF NOT EXISTS outreach_status_event_date_uidx
    ON discharge_app.outreach_status (event_id, discharge_date);

-- Index: look up all events updated by a specific user (manager view)
CREATE INDEX IF NOT EXISTS outreach_status_updated_by_idx
    ON discharge_app.outreach_status (updated_by);

-- Index: filter by status for roll-up metrics
CREATE INDEX IF NOT EXISTS outreach_status_status_idx
    ON discharge_app.outreach_status (status);


-- =============================================================================
-- SECTION 3: user_activity_log
-- Append-only audit log. Never update rows — only INSERT.
-- Captures login events and every outreach status change.
-- =============================================================================

CREATE TABLE IF NOT EXISTS discharge_app.user_activity_log (
    log_id      BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_email  TEXT        NOT NULL,
    user_name   TEXT,                   -- display name at time of action (denorm intentional — log is immutable)
    action      TEXT        NOT NULL
                            CHECK (action IN ('login', 'outreach_update')),
    detail      JSONB       NOT NULL DEFAULT '{}'
                            CHECK (jsonb_typeof(detail) = 'object'),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  discharge_app.user_activity_log            IS 'Append-only audit log. Captures logins and outreach status changes.';
COMMENT ON COLUMN discharge_app.user_activity_log.user_name  IS 'Snapshot of display name at time of action. Intentionally denormalized — log rows are immutable.';
COMMENT ON COLUMN discharge_app.user_activity_log.action     IS 'login | outreach_update';
COMMENT ON COLUMN discharge_app.user_activity_log.detail     IS 'Flexible JSONB payload. For outreach_update: {"event_id":"...", "old_status":"...", "new_status":"...", "notes":"..."}. For login: {}.';

-- Index: query all activity for a user within a date range (manager timeline view)
CREATE INDEX IF NOT EXISTS user_activity_log_user_date_idx
    ON discharge_app.user_activity_log (user_email, created_at DESC);

-- Index: filter by action type
CREATE INDEX IF NOT EXISTS user_activity_log_action_idx
    ON discharge_app.user_activity_log (action);

-- Index: GIN on detail JSONB for containment queries
-- e.g. WHERE detail @> '{"event_id": "abc123"}'
CREATE INDEX IF NOT EXISTS user_activity_log_detail_gin_idx
    ON discharge_app.user_activity_log USING GIN (detail);


-- =============================================================================
-- SECTION 4: SEED DATA — app_user
-- Migrated from PRACTICE_ASSIGNMENTS dict in streamlit_app.py.
-- Add your manager users at the bottom — just change role to 'manager'.
-- Email addresses confirmed from Entra ID SSO.
-- =============================================================================

INSERT INTO discharge_app.app_user (user_email, display_name, role, practices, is_active)
VALUES
    -- Bailey Graham
    (
        'bgraham@citadelhealth.com',
        'Bailey Graham',
        'staff',
        ARRAY[
            'All Care Medical Assocociates, LLC',
            'D. Conrad Harper, MD LLC',
            'Dawsonville Family Medicine',
            'Donald A Selph Jr MD, PC',
            'Dr. Jason R. Laney, PC',
            'Heart of Georgia Primary Care, LLC',
            'Internal Medicine Associates of Middle Georgia, PC',
            'Margaret M. Nichols MD LLC',
            'Medical Center, LLP',
            'Moon River Pediatrics',
            'Nicholas A. Pietrzak MD, LLC',
            'Russell G. O''Neal, M.D. LLC'
        ],
        TRUE
    ),
    -- Kiah Jones
    (
        'kjones3@citadelhealth.com',
        'Kiah Jones',
        'staff',
        ARRAY[
            'Cobb Medical Clinic',
            'Cumberland Womens Health Center',
            'HP Internal Medicine, LLC',
            'Lawrenceville Family Practice',
            'Northeast Family Practice, PC',
            'Rodriguez MD, LLC',
            'Rophe Adult and Pediatric Medicine'
        ],
        TRUE
    ),
    -- Makeba Crawford
    (
        'mcrawford@citadelhealth.com',
        'Makeba Crawford',
        'staff',
        ARRAY[
            'Aylo Health, LLC'
        ],
        TRUE
    ),
    -- Stephanie Nelson
    (
        'snelson@citadelhealth.com',
        'Stephanie Nelson',
        'staff',
        ARRAY[
            'Ajay Kumar MD, LLC',
            'Cornerstone Medical Associates, LLC',
            'Integrity Health and Wellness LLC',
            'Internal Medicine Associates of Waycross',
            'Internal Medicine Associates, PC',
            'Lawrence Kirk MD, LLC',
            'MCC Internal Medicine 2, LLC',
            'MCC Internal Medicine, LLC',
            'Robert C. Jones, MD, LLC',
            'Smith-Lambert Clinic, P.C.',
            'Southeast Georgia Pediatrics'
        ],
        TRUE
    )
ON CONFLICT (user_email) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        practices    = EXCLUDED.practices,
        is_active    = EXCLUDED.is_active;

-- Managers
INSERT INTO discharge_app.app_user (user_email, display_name, role, practices, is_active)
VALUES
    ('tstevens@citadelhealth.com', 'Trevor Stevens', 'manager', '{}', TRUE),
    ('soheron@citadelhealth.com',  'Shaun Oheron',   'manager', '{}', TRUE),
    ('rcruz@citadelhealth.com',    'Ronnie Cruz',    'manager', '{}', TRUE)
ON CONFLICT (user_email) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        role         = EXCLUDED.role,
        is_active    = EXCLUDED.is_active;


-- =============================================================================
-- SECTION 5: v_discharge_summary — Reconciled View
-- =============================================================================
--
-- Drop dependent views first, then rebuild everything clean.
-- All 4 dependents are simple date-filtered wrappers around v_discharge_summary.

DROP VIEW IF EXISTS public.v_open_discharges_30d;
DROP VIEW IF EXISTS public.v_recent_discharges_15d;
DROP VIEW IF EXISTS public.v_recent_discharges_1d;
DROP VIEW IF EXISTS public.v_recent_discharges_30d;
DROP VIEW IF EXISTS public.v_discharge_summary;

-- Rebuild v_discharge_summary: clean column set, no hardcoded date range.
CREATE VIEW public.v_discharge_summary AS
SELECT
    de.event_id,
    de.insurance_member_id,
    COALESCE(pt.first_name, '') || ' ' || COALESCE(pt.last_name, '') AS patient_name,
    de.admit_date,
    de.discharge_date,
    de.disposition,
    de.stay_type,
    de.discharge_hospital,
    de.length_of_stay,
    py.payer_name,
    lob.lob_name,
    p.full_name                        AS provider_name,
    l.parent_org                       AS practice,
    d.dx_code,
    d.description,
    d.dx_grouping,
    pt.address                         AS patient_address,
    pt.city,
    pt.zip_code::CHARACTER VARYING(5)  AS zip_code,
    pt.state
FROM public.discharge_event de
    LEFT JOIN public.provider         p   ON p.provider_id   = de.provider_id
    LEFT JOIN public.payer            py  ON py.payer_id     = de.payer_id
    LEFT JOIN public.line_of_business lob ON lob.lob_id      = de.lob_id
    LEFT JOIN public.patient          pt  ON pt.patient_id   = de.patient_id
    LEFT JOIN public.diagnosis_code   d   ON d.dx_id         = de.dx_id
    LEFT JOIN public.location         l   ON l.location_id   = p.location_id
WHERE de.discharge_date IS NOT NULL;

COMMENT ON VIEW public.v_discharge_summary IS
    'Authoritative discharge summary view. Joins discharge_event to all dimension tables. '
    'No date filter — the application layer filters. '
    'V2: clean column set with practice (parent_org), no hardcoded date range.';

-- Recreate dependent views on the new column set
CREATE VIEW public.v_open_discharges_30d AS
SELECT * FROM public.v_discharge_summary
WHERE admit_date >= (CURRENT_DATE - INTERVAL '30 days')
  AND discharge_date IS NULL;

CREATE VIEW public.v_recent_discharges_1d AS
SELECT * FROM public.v_discharge_summary
WHERE discharge_date = (CURRENT_DATE - INTERVAL '1 day');

CREATE VIEW public.v_recent_discharges_15d AS
SELECT * FROM public.v_discharge_summary
WHERE discharge_date >= (CURRENT_DATE - INTERVAL '15 days')
  AND discharge_date IS NOT NULL;

CREATE VIEW public.v_recent_discharges_30d AS
SELECT * FROM public.v_discharge_summary
WHERE discharge_date >= (CURRENT_DATE - INTERVAL '30 days')
  AND discharge_date IS NOT NULL;


-- =============================================================================
-- SECTION 6: GRANT STATEMENTS (template)
-- Replace "discharge_app_role" with whatever DB role your app connects as.
-- =============================================================================

-- Schema + app tables
-- GRANT USAGE ON SCHEMA discharge_app TO discharge_app_role;
-- GRANT SELECT, INSERT, UPDATE ON discharge_app.app_user          TO discharge_app_role;
-- GRANT SELECT, INSERT, UPDATE ON discharge_app.outreach_status   TO discharge_app_role;
-- GRANT SELECT, INSERT          ON discharge_app.user_activity_log TO discharge_app_role;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA discharge_app    TO discharge_app_role;

-- View + underlying base tables (SECURITY INVOKER means the caller needs SELECT on base tables)
-- GRANT SELECT ON public.v_discharge_summary  TO discharge_app_role;
-- GRANT SELECT ON public.discharge_event      TO discharge_app_role;
-- GRANT SELECT ON public.provider             TO discharge_app_role;
-- GRANT SELECT ON public.payer                TO discharge_app_role;
-- GRANT SELECT ON public.line_of_business     TO discharge_app_role;
-- GRANT SELECT ON public.patient              TO discharge_app_role;
-- GRANT SELECT ON public.diagnosis_code       TO discharge_app_role;
-- GRANT SELECT ON public.location             TO discharge_app_role;

-- Persist search_path on the app role so it resolves discharge_app tables without
-- requiring it in every connection string
-- ALTER ROLE discharge_app_role SET search_path = discharge_app, public;

-- Future-proof: auto-grant on new objects created in the schema
-- ALTER DEFAULT PRIVILEGES IN SCHEMA discharge_app
--     GRANT SELECT, INSERT, UPDATE ON TABLES TO discharge_app_role;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA discharge_app
--     GRANT USAGE, SELECT ON SEQUENCES TO discharge_app_role;


-- =============================================================================
-- SECTION 7: QUICK VERIFICATION QUERIES
-- Run these after applying to confirm everything landed correctly.
-- =============================================================================

-- Check tables were created
-- SELECT table_schema, table_name FROM information_schema.tables
-- WHERE table_schema = 'discharge_app' ORDER BY table_name;

-- Check seed data
-- SELECT user_email, display_name, role, array_length(practices, 1) AS practice_count
-- FROM discharge_app.app_user ORDER BY display_name;

-- Check view works
-- SELECT event_id, patient_name, discharge_date, practice
-- FROM public.v_discharge_summary
-- LIMIT 5;

-- Check indexes
-- SELECT indexname, tablename, indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'discharge_app'
-- ORDER BY tablename, indexname;
