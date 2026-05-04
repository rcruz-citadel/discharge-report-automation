"""Nightly auto-fail: sets status='failed' for records past their TCM time window.

Time windows:
  - ER (stay_type ILIKE '%emergency%'):  7 days from discharge_date
  - All others (inpatient, SNF, etc.): 30 days from discharge_date

Records already in outreach_complete or no_outreach_required are never touched.
This runs once at startup (to catch any missed window) and then every 24 hours.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger = logging.getLogger(__name__)
_SCHEMA = get_settings().app_schema

# Update existing outreach_status rows that are past their window
_UPDATE_QUERY = text(f"""
UPDATE {_SCHEMA}.outreach_status o
SET status         = 'failed',
    failure_reason = 'missed_tcm_window',
    updated_by     = 'system',
    updated_at     = now()
FROM discharge_event de
WHERE o.event_id       = de.event_id
  AND o.discharge_date = de.discharge_date
  AND o.status NOT IN ('outreach_complete', 'no_outreach_required', 'failed')
  AND de.discharge_date IS NOT NULL
  AND (
      (LOWER(COALESCE(de.stay_type, '')) LIKE '%emergency%'
       AND (CURRENT_DATE - de.discharge_date::date) > 7)
      OR
      (LOWER(COALESCE(de.stay_type, '')) NOT LIKE '%emergency%'
       AND (CURRENT_DATE - de.discharge_date::date) > 30)
  )
""")

# Insert failed rows for records with no outreach row yet but past their window
_INSERT_QUERY = text(f"""
INSERT INTO {_SCHEMA}.outreach_status
    (event_id, discharge_date, status, failure_reason, original_failure_reason, updated_by, updated_at, discharge_summary_dropped)
SELECT
    de.event_id,
    de.discharge_date,
    'failed',
    'missed_tcm_window',
    'missed_tcm_window',
    'system',
    now(),
    FALSE
FROM discharge_event de
LEFT JOIN {_SCHEMA}.outreach_status o
    ON o.event_id = de.event_id AND o.discharge_date = de.discharge_date
WHERE o.event_id IS NULL
  AND de.discharge_date IS NOT NULL
  AND (
    de.discharge_hospital IS NULL
    OR (
      LOWER(de.discharge_hospital) NOT LIKE '%home health%'
      AND LOWER(de.discharge_hospital) NOT LIKE '%hospice%'
    )
  )
  AND (
      (LOWER(COALESCE(de.stay_type, '')) LIKE '%emergency%'
       AND (CURRENT_DATE - de.discharge_date::date) > 7)
      OR
      (LOWER(COALESCE(de.stay_type, '')) NOT LIKE '%emergency%'
       AND (CURRENT_DATE - de.discharge_date::date) > 30)
  )
ON CONFLICT (event_id, discharge_date) DO NOTHING
""")


async def run_auto_fail(db: AsyncSession) -> tuple[int, int]:
    """Run auto-fail logic. Returns (updated_count, inserted_count)."""
    r1 = await db.execute(_UPDATE_QUERY)
    r2 = await db.execute(_INSERT_QUERY)
    await db.commit()
    updated = r1.rowcount
    inserted = r2.rowcount
    if updated or inserted:
        logger.info("auto_fail: updated=%d inserted=%d", updated, inserted)
    return updated, inserted
