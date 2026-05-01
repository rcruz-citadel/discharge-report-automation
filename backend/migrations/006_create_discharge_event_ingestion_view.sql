-- Migration 006: Create discharge_event_ingestion view
-- Exposes event_id + first_ingested_date to discharge_app_role without
-- granting direct access to discharge_master (raw landing table).
--
-- Run against care_analytics as superuser.
-- Works for both discharge_app (prod) and discharge_app_staging (staging) —
-- both environments share the same discharge_event and discharge_master tables.

CREATE OR REPLACE VIEW discharge_app.discharge_event_ingestion AS
SELECT DISTINCT ON (de.event_id)
    de.event_id,
    dm.first_ingested_date
FROM discharge_event de
LEFT JOIN discharge_master dm ON dm.event_id = de.event_id
ORDER BY de.event_id, dm.first_ingested_date ASC NULLS LAST;

-- Lock ownership so app role cannot redefine the view
ALTER VIEW discharge_app.discharge_event_ingestion OWNER TO postgres;

-- Least-privilege grant — read only, view only
GRANT SELECT ON discharge_app.discharge_event_ingestion TO discharge_app_role;

-- Defensive: revoke any direct grant on discharge_master if it was added during debugging
REVOKE ALL ON discharge_master FROM discharge_app_role;
