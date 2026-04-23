"""GET /api/outreach/{event_id} and PUT /api/outreach/{event_id}."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_user
from app.database import get_db
from app.models.schemas import MeResponse, OutreachAttempt, LogAttemptResponse, OutreachRecord, OutreachUpsertRequest
from app.services.outreach_service import get_outreach, upsert_outreach, get_attempts, log_attempt

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.get("/{event_id}", response_model=OutreachRecord)
async def fetch_outreach(
    event_id: str,
    discharge_date: date,
    db: AsyncSession = Depends(get_db),
    _user: MeResponse = Depends(get_current_user),
) -> OutreachRecord:
    """Return the current outreach record for one discharge event.

    Returns 404 if no outreach record exists (meaning no_outreach status).
    Used by the detail panel to get fresh data when it opens.
    """
    record = await get_outreach(db, event_id, discharge_date)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No outreach record for event_id={event_id!r} discharge_date={discharge_date}",
        )
    return record


@router.put("/{event_id}", response_model=OutreachRecord)
async def save_outreach(
    event_id: str,
    payload: OutreachUpsertRequest,
    db: AsyncSession = Depends(get_db),
    user: MeResponse = Depends(get_current_user),
) -> OutreachRecord:
    """Upsert outreach status for one discharge event.

    Uses ON CONFLICT DO UPDATE — last write wins. Appends to user_activity_log.
    After success, the frontend calls queryClient.invalidateQueries(['discharges'])
    to trigger a background refetch.
    """
    return await upsert_outreach(db, event_id, payload, updated_by=user.email)


@router.get("/{event_id}/attempts", response_model=list[OutreachAttempt])
async def fetch_attempts(
    event_id: str,
    discharge_date: date,
    db: AsyncSession = Depends(get_db),
    _user: MeResponse = Depends(get_current_user),
) -> list[OutreachAttempt]:
    """Return all logged attempts for one discharge event (max 3)."""
    return await get_attempts(db, event_id, discharge_date)


@router.post("/{event_id}/attempts", response_model=LogAttemptResponse, status_code=201)
async def create_attempt(
    event_id: str,
    discharge_date: date,
    db: AsyncSession = Depends(get_db),
    user: MeResponse = Depends(get_current_user),
) -> LogAttemptResponse:
    """Log a new outreach attempt. Returns 409 if already at 3 attempts."""
    try:
        attempt = await log_attempt(db, event_id, discharge_date, attempted_by=user.email)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    all_attempts = await get_attempts(db, event_id, discharge_date)
    return LogAttemptResponse(
        attempt=attempt,
        attempt_number=attempt.attempt_number,
        attempts_remaining=3 - len(all_attempts),
    )
