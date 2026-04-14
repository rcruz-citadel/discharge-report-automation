"""Outreach status service: upsert operations and activity logging."""
import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import OutreachRecord, OutreachUpsertRequest

logger = logging.getLogger(__name__)

_GET_OUTREACH_QUERY = text("""
SELECT event_id, discharge_date, status, notes, updated_by, updated_at
FROM discharge_app.outreach_status
WHERE event_id = :event_id
  AND discharge_date = :discharge_date
""")

_UPSERT_OUTREACH_QUERY = text("""
INSERT INTO discharge_app.outreach_status
    (event_id, discharge_date, status, updated_by, updated_at, notes)
VALUES
    (:event_id, :discharge_date, :status, :updated_by, now(), :notes)
ON CONFLICT (event_id, discharge_date) DO UPDATE
    SET status     = EXCLUDED.status,
        updated_by = EXCLUDED.updated_by,
        updated_at = now(),
        notes      = EXCLUDED.notes
RETURNING event_id, discharge_date, status, notes, updated_by, updated_at
""")

_LOG_ACTIVITY_QUERY = text("""
INSERT INTO discharge_app.user_activity_log (user_email, action, metadata_json)
VALUES (:user_email, 'outreach_update', :metadata_json)
""")


async def get_outreach(
    db: AsyncSession,
    event_id: str,
    discharge_date: date,
) -> OutreachRecord | None:
    """Return the outreach record for a single event, or None if no record exists."""
    result = await db.execute(
        _GET_OUTREACH_QUERY,
        {"event_id": event_id, "discharge_date": discharge_date},
    )
    row = result.mappings().one_or_none()
    if row is None:
        return None
    return OutreachRecord(
        event_id=row["event_id"],
        discharge_date=row["discharge_date"],
        status=row["status"],
        notes=row["notes"] or "",
        updated_by=row["updated_by"],
        updated_at=row["updated_at"],
    )


async def upsert_outreach(
    db: AsyncSession,
    event_id: str,
    payload: OutreachUpsertRequest,
    updated_by: str,
) -> OutreachRecord:
    """Upsert outreach status for one discharge event.

    Runs atomically via ON CONFLICT DO UPDATE. Last write wins.
    Also appends a row to user_activity_log for audit/manager metrics.
    """
    import json

    result = await db.execute(
        _UPSERT_OUTREACH_QUERY,
        {
            "event_id": event_id,
            "discharge_date": payload.discharge_date,
            "status": payload.status,
            "updated_by": updated_by,
            "notes": payload.notes,
        },
    )
    row = result.mappings().one()

    # Append activity log (non-critical — don't fail the request if this errors)
    try:
        metadata = json.dumps({
            "event_id": event_id,
            "discharge_date": str(payload.discharge_date),
            "status": payload.status,
        })
        await db.execute(
            _LOG_ACTIVITY_QUERY,
            {"user_email": updated_by, "metadata_json": metadata},
        )
    except Exception as exc:
        logger.warning("activity_log insert failed (non-critical): %s", exc)

    await db.commit()

    return OutreachRecord(
        event_id=row["event_id"],
        discharge_date=row["discharge_date"],
        status=row["status"],
        notes=row["notes"] or "",
        updated_by=row["updated_by"],
        updated_at=row["updated_at"],
    )
