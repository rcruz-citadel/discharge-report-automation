"""Auto-flag missed 48h window: sets status='failed', failure_reason='missed_48h'.

A record gets this flag when:
  - ADT was delivered on time (first_ingested_date - discharge_date <= 2 days)
  - 48 hours have passed since discharge (age > 2 days)
  - No outreach has been initiated (status = 'no_outreach')
  - The TCM window is still open (not yet past 7/30-day deadline)

This distinguishes "team missed the 48h call window" from "entire TCM window
expired" (missed_tcm_window, handled by auto_fail.py).

Records already in any status other than 'no_outreach' are never touched.
Runs once at startup and every 24 hours.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger = logging.getLogger(__name__)
_SCHEMA = get_settings().app_schema

_UPDATE_QUERY = text(f"""
UPDATE {_SCHEMA}.outreach_status o
SET status         = 'failed',
    failure_reason = 'missed_48h',
    updated_by     = 'system',
    updated_at     = now()
FROM discharge_event de
JOIN discharge_app.discharge_event_ingestion dei ON dei.event_id = de.event_id
WHERE o.event_id       = de.event_id
  AND o.discharge_date = de.discharge_date
  AND o.status         = 'no_outreach'
  AND de.discharge_date IS NOT NULL
  AND dei.first_ingested_date IS NOT NULL
  -- ADT arrived on time
  AND (dei.first_ingested_date::date - de.discharge_date::date) <= 2
  -- 48h window has passed
  AND (CURRENT_DATE - de.discharge_date::date) > 2
  -- TCM window still open (not yet auto-failed by window expiry)
  AND (
      (LOWER(COALESCE(de.stay_type, '')) LIKE '%emergency%'
       AND (CURRENT_DATE - de.discharge_date::date) <= 7)
      OR
      (LOWER(COALESCE(de.stay_type, '')) NOT LIKE '%emergency%'
       AND (CURRENT_DATE - de.discharge_date::date) <= 30)
  )
  AND (
    de.discharge_hospital IS NULL
    OR (
      LOWER(de.discharge_hospital) NOT LIKE '%home health%'
      AND LOWER(de.discharge_hospital) NOT LIKE '%hospice%'
    )
  )
""")

_INSERT_QUERY = text(f"""
INSERT INTO {_SCHEMA}.outreach_status
    (event_id, discharge_date, status, failure_reason, updated_by, updated_at, discharge_summary_dropped)
SELECT
    de.event_id,
    de.discharge_date,
    'failed',
    'missed_48h',
    'system',
    now(),
    FALSE
FROM discharge_event de
JOIN discharge_app.discharge_event_ingestion dei ON dei.event_id = de.event_id
LEFT JOIN {_SCHEMA}.outreach_status o
    ON o.event_id = de.event_id AND o.discharge_date = de.discharge_date
WHERE o.event_id IS NULL
  AND de.discharge_date IS NOT NULL
  AND dei.first_ingested_date IS NOT NULL
  AND (dei.first_ingested_date::date - de.discharge_date::date) <= 2
  AND (CURRENT_DATE - de.discharge_date::date) > 2
  AND (
      (LOWER(COALESCE(de.stay_type, '')) LIKE '%emergency%'
       AND (CURRENT_DATE - de.discharge_date::date) <= 7)
      OR
      (LOWER(COALESCE(de.stay_type, '')) NOT LIKE '%emergency%'
       AND (CURRENT_DATE - de.discharge_date::date) <= 30)
  )
  AND (
    de.discharge_hospital IS NULL
    OR (
      LOWER(de.discharge_hospital) NOT LIKE '%home health%'
      AND LOWER(de.discharge_hospital) NOT LIKE '%hospice%'
    )
  )
ON CONFLICT (event_id, discharge_date) DO NOTHING
""")


async def run_auto_flag_missed_48h(db: AsyncSession) -> tuple[int, int]:
    """Run missed-48h flag logic. Returns (updated_count, inserted_count)."""
    r1 = await db.execute(_UPDATE_QUERY)
    r2 = await db.execute(_INSERT_QUERY)
    await db.commit()
    updated = r1.rowcount
    inserted = r2.rowcount
    if updated or inserted:
        logger.info("auto_flag_missed_48h: updated=%d inserted=%d", updated, inserted)
    return updated, inserted
