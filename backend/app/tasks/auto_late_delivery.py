"""Nightly auto-late-delivery: flags records whose discharge summary arrived late.

A record is "late delivery" when discharge_master.first_ingested_date is more
than 2 days after discharge_event.discharge_date. We only flag records that:
  - are still within their TCM window (7 days for ER, 30 days for others)
  - currently have status='no_outreach' (or no outreach row yet)
  - are not home health or hospice

Records already in outreach_complete, no_outreach_required, failed, or
late_delivery are never touched. This runs once at startup and then every
24 hours.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger = logging.getLogger(__name__)
_SCHEMA = get_settings().app_schema

# Update existing no_outreach rows whose summary arrived late but window is still open
_UPDATE_QUERY = text(f"""
UPDATE {_SCHEMA}.outreach_status o
SET status     = 'late_delivery',
    updated_by = 'system',
    updated_at = now()
FROM discharge_event de
JOIN discharge_master dm
    ON dm.event_id = de.event_id
WHERE o.event_id       = de.event_id
  AND o.discharge_date = de.discharge_date
  AND o.status         = 'no_outreach'
  AND de.discharge_date IS NOT NULL
  AND dm.first_ingested_date IS NOT NULL
  AND (dm.first_ingested_date - de.discharge_date::date) > 2
  AND (
    de.discharge_hospital IS NULL
    OR (
      LOWER(de.discharge_hospital) NOT LIKE '%home health%'
      AND LOWER(de.discharge_hospital) NOT LIKE '%hospice%'
    )
  )
  AND (
      (LOWER(COALESCE(de.stay_type, '')) LIKE '%emergency%'
       AND de.discharge_date::date > (CURRENT_DATE - INTERVAL '7 days'))
      OR
      (LOWER(COALESCE(de.stay_type, '')) NOT LIKE '%emergency%'
       AND de.discharge_date::date > (CURRENT_DATE - INTERVAL '30 days'))
  )
""")

# Insert late_delivery rows for records with no outreach row yet
_INSERT_QUERY = text(f"""
INSERT INTO {_SCHEMA}.outreach_status
    (event_id, discharge_date, status, updated_by, updated_at, discharge_summary_dropped)
SELECT
    de.event_id,
    de.discharge_date,
    'late_delivery',
    'system',
    now(),
    FALSE
FROM discharge_event de
JOIN discharge_master dm
    ON dm.event_id = de.event_id
LEFT JOIN {_SCHEMA}.outreach_status o
    ON o.event_id = de.event_id AND o.discharge_date = de.discharge_date
WHERE o.event_id IS NULL
  AND de.discharge_date IS NOT NULL
  AND dm.first_ingested_date IS NOT NULL
  AND (dm.first_ingested_date - de.discharge_date::date) > 2
  AND (
    de.discharge_hospital IS NULL
    OR (
      LOWER(de.discharge_hospital) NOT LIKE '%home health%'
      AND LOWER(de.discharge_hospital) NOT LIKE '%hospice%'
    )
  )
  AND (
      (LOWER(COALESCE(de.stay_type, '')) LIKE '%emergency%'
       AND de.discharge_date::date > (CURRENT_DATE - INTERVAL '7 days'))
      OR
      (LOWER(COALESCE(de.stay_type, '')) NOT LIKE '%emergency%'
       AND de.discharge_date::date > (CURRENT_DATE - INTERVAL '30 days'))
  )
ON CONFLICT (event_id, discharge_date) DO NOTHING
""")


async def run_auto_late_delivery(db: AsyncSession) -> tuple[int, int]:
    """Run auto-late-delivery logic. Returns (updated_count, inserted_count)."""
    r1 = await db.execute(_UPDATE_QUERY)
    r2 = await db.execute(_INSERT_QUERY)
    await db.commit()
    updated = r1.rowcount
    inserted = r2.rowcount
    if updated or inserted:
        logger.info("auto_late_delivery: updated=%d inserted=%d", updated, inserted)
    return updated, inserted
