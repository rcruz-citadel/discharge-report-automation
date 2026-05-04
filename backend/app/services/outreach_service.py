"""Outreach status service: upsert operations and activity logging."""
import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.schemas import OutreachAttempt, LogAttemptResponse, OutreachRecord, OutreachUpsertRequest

logger = logging.getLogger(__name__)
_SCHEMA = get_settings().app_schema

_GET_OUTREACH_QUERY = text(f"""
SELECT event_id, discharge_date, status, notes, updated_by, updated_at,
       discharge_summary_dropped, failure_reason, original_failure_reason
FROM {_SCHEMA}.outreach_status
WHERE event_id = :event_id
  AND discharge_date = :discharge_date
""")

_UPSERT_OUTREACH_QUERY = text(f"""
INSERT INTO {_SCHEMA}.outreach_status
    (event_id, discharge_date, status, updated_by, updated_at, notes, discharge_summary_dropped,
     original_failure_reason)
VALUES
    (:event_id, :discharge_date, :status, :updated_by, now(), :notes, :discharge_summary_dropped,
     NULL)
ON CONFLICT (event_id, discharge_date) DO UPDATE
    SET status                    = EXCLUDED.status,
        updated_by                = EXCLUDED.updated_by,
        updated_at                = now(),
        notes                     = EXCLUDED.notes,
        discharge_summary_dropped = EXCLUDED.discharge_summary_dropped,
        -- Clear failure_reason when coordinator overrides a failed record
        failure_reason            = CASE
            WHEN EXCLUDED.status = 'failed' THEN {_SCHEMA}.outreach_status.failure_reason
            ELSE NULL
        END
RETURNING event_id, discharge_date, status, notes, updated_by, updated_at,
          discharge_summary_dropped, failure_reason, original_failure_reason
""")

_LOG_ACTIVITY_QUERY = text(f"""
INSERT INTO {_SCHEMA}.user_activity_log (user_email, action, metadata_json)
VALUES (:user_email, 'outreach_update', :metadata_json)
""")

_LOG_STATUS_HISTORY_QUERY = text(f"""
INSERT INTO {_SCHEMA}.status_history
    (event_id, discharge_date, old_status, new_status, old_failure_reason, changed_by)
VALUES
    (:event_id, :discharge_date, :old_status, :new_status, :old_failure_reason, :changed_by)
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
        discharge_summary_dropped=bool(row["discharge_summary_dropped"]),
    )


async def upsert_outreach(
    db: AsyncSession,
    event_id: str,
    payload: OutreachUpsertRequest,
    updated_by: str,
) -> OutreachRecord:
    """Upsert outreach status for one discharge event.

    Runs atomically via ON CONFLICT DO UPDATE. Last write wins.
    When a coordinator overrides a system-failed record, failure_reason is
    cleared on the main row and logged to status_history for audit/reporting.
    """
    import json

    # Capture current state before overwrite so we can log the transition
    prev = await db.execute(
        _GET_OUTREACH_QUERY,
        {"event_id": event_id, "discharge_date": payload.discharge_date},
    )
    prev_row = prev.mappings().one_or_none()
    old_status = prev_row["status"] if prev_row else None
    old_failure_reason = prev_row["failure_reason"] if prev_row else None

    result = await db.execute(
        _UPSERT_OUTREACH_QUERY,
        {
            "event_id": event_id,
            "discharge_date": payload.discharge_date,
            "status": payload.status,
            "updated_by": updated_by,
            "notes": payload.notes,
            "discharge_summary_dropped": payload.discharge_summary_dropped,
        },
    )
    row = result.mappings().one()

    # Commit the upsert before attempting non-critical side effects.
    # If a subsequent insert fails it aborts the transaction — committing first
    # keeps the critical write durable regardless.
    await db.commit()

    # Log status transition to status_history and activity_log (non-critical)
    try:
        await db.execute(
            _LOG_STATUS_HISTORY_QUERY,
            {
                "event_id": event_id,
                "discharge_date": payload.discharge_date,
                "old_status": old_status,
                "new_status": payload.status,
                "old_failure_reason": old_failure_reason,
                "changed_by": updated_by,
            },
        )
        metadata = json.dumps({
            "event_id": event_id,
            "discharge_date": str(payload.discharge_date),
            "status": payload.status,
        })
        await db.execute(
            _LOG_ACTIVITY_QUERY,
            {"user_email": updated_by, "metadata_json": metadata},
        )
        await db.commit()
    except Exception as exc:
        logger.warning("status_history/activity_log insert failed (non-critical): %s", exc)
        await db.rollback()

    return OutreachRecord(
        event_id=row["event_id"],
        discharge_date=row["discharge_date"],
        status=row["status"],
        notes=row["notes"] or "",
        updated_by=row["updated_by"],
        updated_at=row["updated_at"],
        discharge_summary_dropped=bool(row["discharge_summary_dropped"]),
    )


_GET_ATTEMPTS_QUERY = text(f"""
SELECT id, event_id, discharge_date, attempt_number, attempted_by, attempted_at
FROM {_SCHEMA}.outreach_attempts
WHERE event_id = :event_id AND discharge_date = :discharge_date
ORDER BY attempt_number
""")

_LOG_ATTEMPT_QUERY = text(f"""
INSERT INTO {_SCHEMA}.outreach_attempts
    (event_id, discharge_date, attempt_number, attempted_by)
SELECT
    :event_id,
    :discharge_date,
    COALESCE(MAX(attempt_number), 0) + 1,
    :attempted_by
FROM {_SCHEMA}.outreach_attempts
WHERE event_id = :event_id AND discharge_date = :discharge_date
HAVING COALESCE(MAX(attempt_number), 0) < 3
RETURNING id, event_id, discharge_date, attempt_number, attempted_by, attempted_at
""")

_AUTO_COMPLETE_QUERY = text(f"""
INSERT INTO {_SCHEMA}.outreach_status
    (event_id, discharge_date, status, updated_by, updated_at, notes, discharge_summary_dropped)
VALUES
    (:event_id, :discharge_date, 'outreach_complete', 'system (3 attempts)', now(), '', FALSE)
ON CONFLICT (event_id, discharge_date) DO UPDATE
    SET status     = 'outreach_complete',
        updated_by = 'system (3 attempts)',
        updated_at  = now()
""")


async def get_attempts(
    db: AsyncSession,
    event_id: str,
    discharge_date: date,
) -> list[OutreachAttempt]:
    result = await db.execute(
        _GET_ATTEMPTS_QUERY,
        {"event_id": event_id, "discharge_date": discharge_date},
    )
    return [
        OutreachAttempt(
            id=row["id"],
            event_id=row["event_id"],
            discharge_date=row["discharge_date"],
            attempt_number=row["attempt_number"],
            attempted_by=row["attempted_by"],
            attempted_at=row["attempted_at"],
        )
        for row in result.mappings().all()
    ]


async def log_attempt(
    db: AsyncSession,
    event_id: str,
    discharge_date: date,
    attempted_by: str,
) -> tuple[OutreachAttempt, bool]:
    """Log a new outreach attempt.

    Returns (attempt, auto_completed) where auto_completed=True means the
    3rd attempt was just reached and the status was auto-set to outreach_complete.
    Raises ValueError if already at 3 attempts.
    """
    result = await db.execute(
        _LOG_ATTEMPT_QUERY,
        {
            "event_id": event_id,
            "discharge_date": discharge_date,
            "attempted_by": attempted_by,
        },
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise ValueError("Maximum of 3 attempts already reached for this discharge event.")

    attempt = OutreachAttempt(
        id=row["id"],
        event_id=row["event_id"],
        discharge_date=row["discharge_date"],
        attempt_number=row["attempt_number"],
        attempted_by=row["attempted_by"],
        attempted_at=row["attempted_at"],
    )

    auto_completed = attempt.attempt_number == 3
    if auto_completed:
        await db.execute(
            _AUTO_COMPLETE_QUERY,
            {"event_id": event_id, "discharge_date": discharge_date},
        )

    await db.commit()
    return attempt, auto_completed
