"""Discharge data service: query v_discharge_summary joined with outreach_status."""
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import DischargeRecord, DischargesResponse

logger = logging.getLogger(__name__)

# Full merged discharge + outreach query.
# location_name aliased as practice (view uses location_name, app calls it practice).
_DISCHARGE_QUERY = text("""
SELECT
    d.event_id,
    d.discharge_date,
    d.patient_name,
    d.insurance_member_id,
    d.location_name                 AS practice,
    d.payer_name,
    d.lob_name,
    d.stay_type,
    d.discharge_hospital,
    d.length_of_stay,
    d.disposition,
    d.dx_code,
    d.description,
    d.admit_date,
    COALESCE(o.status, 'no_outreach') AS outreach_status,
    COALESCE(o.notes, '')             AS outreach_notes,
    o.updated_by                      AS outreach_updated_by,
    o.updated_at                      AS outreach_updated_at
FROM v_discharge_summary d
LEFT JOIN discharge_app.outreach_status o
    ON o.event_id = d.event_id
    AND o.discharge_date = d.discharge_date
ORDER BY d.discharge_date DESC
""")


async def get_all_discharges(db: AsyncSession) -> DischargesResponse:
    """Return all discharge records merged with outreach status.

    Returns ~17k rows (~1.5 MB gzipped). Nginx gzip compresses the JSON payload.
    Client caches for 5 minutes via TanStack Query (staleTime: 5 * 60 * 1000).
    """
    result = await db.execute(_DISCHARGE_QUERY)
    rows = result.mappings().all()

    records = [
        DischargeRecord(
            event_id=row["event_id"],
            discharge_date=row["discharge_date"],
            patient_name=row["patient_name"],
            insurance_member_id=row["insurance_member_id"],
            practice=row["practice"],
            payer_name=row["payer_name"],
            lob_name=row["lob_name"],
            stay_type=row["stay_type"],
            discharge_hospital=row["discharge_hospital"],
            length_of_stay=row["length_of_stay"],
            disposition=row["disposition"],
            dx_code=row["dx_code"],
            description=row["description"],
            admit_date=row["admit_date"],
            outreach_status=row["outreach_status"] or "no_outreach",
            outreach_notes=row["outreach_notes"] or "",
            outreach_updated_by=row["outreach_updated_by"],
            outreach_updated_at=row["outreach_updated_at"],
        )
        for row in rows
    ]

    return DischargesResponse(
        records=records,
        total=len(records),
        loaded_at=datetime.now(tz=timezone.utc),
    )
