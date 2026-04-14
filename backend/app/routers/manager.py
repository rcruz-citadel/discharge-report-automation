"""GET /api/manager/metrics — role-gated manager dashboard aggregations."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_manager
from app.database import get_db
from app.models.schemas import ManagerMetricsResponse, MeResponse
from app.services.manager_service import get_manager_metrics

router = APIRouter(prefix="/manager", tags=["manager"])


@router.get("/metrics", response_model=ManagerMetricsResponse)
async def manager_metrics(
    db: AsyncSession = Depends(get_db),
    _user: MeResponse = Depends(get_current_manager),
) -> ManagerMetricsResponse:
    """Return manager dashboard aggregations: summary, staff breakdown, practice roll-up.

    Role-gated: returns 403 for non-managers (enforced in get_current_manager dependency).
    Defense-in-depth: frontend also hides the Manager tab for non-managers.
    """
    return await get_manager_metrics(db)
