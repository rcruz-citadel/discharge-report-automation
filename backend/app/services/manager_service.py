"""Manager metrics service: per-user and per-practice aggregations in SQL."""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import ManagerMetricsResponse, OutreachSummary, PracticeRollupRow, StaffBreakdownRow

logger = logging.getLogger(__name__)

_SUMMARY_QUERY = text("""
SELECT
    COUNT(*)                                                              AS total,
    COUNT(*) FILTER (WHERE COALESCE(o.status, 'no_outreach') = 'no_outreach') AS no_outreach,
    COUNT(*) FILTER (WHERE o.status = 'outreach_made')                    AS outreach_made,
    COUNT(*) FILTER (WHERE o.status = 'outreach_complete')                AS outreach_complete
FROM v_discharge_summary d
LEFT JOIN discharge_app.outreach_status o
    ON o.event_id = d.event_id AND o.discharge_date = d.discharge_date
""")

_STAFF_QUERY = text("""
SELECT
    u.user_email,
    u.display_name,
    COALESCE(array_length(u.practices, 1), 0)                                 AS practice_count,
    COUNT(DISTINCT d.event_id)                                                AS total,
    COUNT(DISTINCT d.event_id) FILTER (
        WHERE COALESCE(o.status, 'no_outreach') = 'no_outreach')              AS no_outreach,
    COUNT(DISTINCT d.event_id) FILTER (
        WHERE o.status = 'outreach_made')                                      AS outreach_made,
    COUNT(DISTINCT d.event_id) FILTER (
        WHERE o.status = 'outreach_complete')                                  AS outreach_complete,
    MAX(al_login.created_at)::date                                            AS last_login,
    MAX(al_any.created_at)::date                                              AS last_activity
FROM discharge_app.app_user u
LEFT JOIN v_discharge_summary d
    ON u.practices IS NOT NULL AND d.location_name = ANY(u.practices)
LEFT JOIN discharge_app.outreach_status o
    ON o.event_id = d.event_id AND o.discharge_date = d.discharge_date
LEFT JOIN discharge_app.user_activity_log al_login
    ON al_login.user_email = u.user_email AND al_login.action = 'login'
LEFT JOIN discharge_app.user_activity_log al_any
    ON al_any.user_email = u.user_email
WHERE u.is_active = TRUE AND u.role = 'staff'
GROUP BY u.user_email, u.display_name, u.practices
ORDER BY u.display_name
""")

_PRACTICE_ROLLUP_QUERY = text("""
SELECT
    d.location_name                                                                 AS practice,
    COUNT(DISTINCT d.event_id)                                                     AS total,
    COUNT(DISTINCT d.event_id) FILTER (
        WHERE COALESCE(o.status, 'no_outreach') = 'no_outreach')                   AS no_outreach,
    COUNT(DISTINCT d.event_id) FILTER (WHERE o.status = 'outreach_made')           AS outreach_made,
    COUNT(DISTINCT d.event_id) FILTER (WHERE o.status = 'outreach_complete')       AS outreach_complete
FROM v_discharge_summary d
LEFT JOIN discharge_app.outreach_status o
    ON o.event_id = d.event_id AND o.discharge_date = d.discharge_date
WHERE d.location_name IS NOT NULL
GROUP BY d.location_name
ORDER BY total DESC
""")


def _pct(complete: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(complete / total * 100, 1)


async def get_manager_metrics(db: AsyncSession) -> ManagerMetricsResponse:
    """Return aggregated manager dashboard metrics.

    All aggregation is done in SQL (no pandas). Three queries: summary, staff
    breakdown, and practice roll-up.
    """
    # Summary totals
    summary_result = await db.execute(_SUMMARY_QUERY)
    s = summary_result.mappings().one()
    total = int(s["total"])
    no_outreach = int(s["no_outreach"])
    outreach_made = int(s["outreach_made"])
    outreach_complete = int(s["outreach_complete"])

    summary = OutreachSummary(
        total=total,
        no_outreach=no_outreach,
        outreach_made=outreach_made,
        outreach_complete=outreach_complete,
        pct_complete=_pct(outreach_complete, total),
    )

    # Staff breakdown
    staff_result = await db.execute(_STAFF_QUERY)
    staff_rows = [
        StaffBreakdownRow(
            user_email=row["user_email"],
            display_name=row["display_name"],
            practice_count=int(row["practice_count"] or 0),
            total=int(row["total"] or 0),
            no_outreach=int(row["no_outreach"] or 0),
            outreach_made=int(row["outreach_made"] or 0),
            outreach_complete=int(row["outreach_complete"] or 0),
            pct_complete=_pct(int(row["outreach_complete"] or 0), int(row["total"] or 0)),
            last_login=row["last_login"],
            last_activity=row["last_activity"],
        )
        for row in staff_result.mappings().all()
    ]

    # Practice roll-up
    practice_result = await db.execute(_PRACTICE_ROLLUP_QUERY)
    practice_rows = [
        PracticeRollupRow(
            practice=row["practice"],
            total=int(row["total"] or 0),
            no_outreach=int(row["no_outreach"] or 0),
            outreach_made=int(row["outreach_made"] or 0),
            outreach_complete=int(row["outreach_complete"] or 0),
            pct_complete=_pct(int(row["outreach_complete"] or 0), int(row["total"] or 0)),
        )
        for row in practice_result.mappings().all()
    ]

    return ManagerMetricsResponse(
        summary=summary,
        staff_breakdown=staff_rows,
        practice_rollup=practice_rows,
    )
