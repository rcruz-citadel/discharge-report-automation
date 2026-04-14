"""GET /api/meta/filters — distinct filter values for sidebar dropdowns."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_user
from app.database import get_db
from app.models.schemas import AssigneeInfo, MeResponse, MetaFiltersResponse

router = APIRouter(prefix="/meta", tags=["meta"])

_FILTER_VALUES_QUERY = text("""
SELECT
    array_agg(DISTINCT d.location_name ORDER BY d.location_name)
        FILTER (WHERE d.location_name IS NOT NULL)  AS practices,
    array_agg(DISTINCT d.payer_name ORDER BY d.payer_name)
        FILTER (WHERE d.payer_name IS NOT NULL)     AS payers,
    array_agg(DISTINCT d.lob_name ORDER BY d.lob_name)
        FILTER (WHERE d.lob_name IS NOT NULL)       AS lob_names,
    array_agg(DISTINCT d.stay_type ORDER BY d.stay_type)
        FILTER (WHERE d.stay_type IS NOT NULL)      AS stay_types,
    MIN(d.discharge_date)                           AS discharge_date_min,
    MAX(d.discharge_date)                           AS discharge_date_max
FROM v_discharge_summary d
""")

_ASSIGNEES_QUERY = text("""
SELECT display_name, practices
FROM discharge_app.app_user
WHERE is_active = TRUE
  AND array_length(practices, 1) > 0
ORDER BY display_name
""")


@router.get("/filters", response_model=MetaFiltersResponse)
async def get_filters(
    db: AsyncSession = Depends(get_db),
    _user: MeResponse = Depends(get_current_user),
) -> MetaFiltersResponse:
    """Return all distinct filter values for sidebar dropdowns.

    Called once on app load. TanStack Query caches for 5 minutes.
    Includes: practices, payers, LOBs, stay types, assignees, and date range.
    """
    filter_result = await db.execute(_FILTER_VALUES_QUERY)
    frow = filter_result.mappings().one()

    assignee_result = await db.execute(_ASSIGNEES_QUERY)
    assignees = [
        AssigneeInfo(name=row["display_name"], practices=list(row["practices"] or []))
        for row in assignee_result.mappings().all()
    ]

    return MetaFiltersResponse(
        practices=list(frow["practices"] or []),
        payers=list(frow["payers"] or []),
        lob_names=list(frow["lob_names"] or []),
        stay_types=list(frow["stay_types"] or []),
        assignees=assignees,
        discharge_date_min=frow["discharge_date_min"],
        discharge_date_max=frow["discharge_date_max"],
    )
