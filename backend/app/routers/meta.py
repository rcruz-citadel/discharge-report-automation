"""GET /api/meta/filters — distinct filter values for sidebar dropdowns."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.schemas import AssigneeInfo, MeResponse, MetaFiltersResponse

router = APIRouter(prefix="/meta", tags=["meta"])
_SCHEMA = get_settings().app_schema

_FILTER_VALUES_QUERY = text("""
SELECT
    array_agg(DISTINCT l.parent_org ORDER BY l.parent_org)
        FILTER (WHERE l.parent_org IS NOT NULL)     AS practices,
    array_agg(DISTINCT py.payer_name ORDER BY py.payer_name)
        FILTER (WHERE py.payer_name IS NOT NULL)    AS payers,
    array_agg(DISTINCT lob.lob_name ORDER BY lob.lob_name)
        FILTER (WHERE lob.lob_name IS NOT NULL)     AS lob_names,
    array_agg(DISTINCT de.stay_type ORDER BY de.stay_type)
        FILTER (WHERE de.stay_type IS NOT NULL)     AS stay_types,
    MIN(de.discharge_date)                          AS discharge_date_min,
    MAX(de.discharge_date)                          AS discharge_date_max
FROM discharge_event de
    LEFT JOIN provider p ON p.provider_id = de.provider_id
    LEFT JOIN payer py ON py.payer_id = de.payer_id
    LEFT JOIN line_of_business lob ON lob.lob_id = de.lob_id
    LEFT JOIN location l ON l.location_id = p.location_id
WHERE de.discharge_date IS NOT NULL
""")

_ASSIGNEES_QUERY = text(f"""
SELECT display_name, practices
FROM {_SCHEMA}.app_user
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
