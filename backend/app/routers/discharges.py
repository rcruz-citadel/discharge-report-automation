"""GET /api/discharges — full discharge + outreach dataset."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_user
from app.database import get_db
from app.models.schemas import DischargesResponse, MeResponse
from app.services.discharge_service import get_all_discharges

router = APIRouter(prefix="/discharges", tags=["discharges"])


@router.get("", response_model=DischargesResponse)
async def list_discharges(
    db: AsyncSession = Depends(get_db),
    _user: MeResponse = Depends(get_current_user),
) -> DischargesResponse:
    """Return all ~17k discharge records merged with outreach status.

    All filtering is client-side (React). Nginx gzip compresses the payload
    from ~8.5 MB to ~1.5 MB. TanStack Query caches on the client for 5 min.
    """
    return await get_all_discharges(db)
