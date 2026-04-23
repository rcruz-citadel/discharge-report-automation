"""Discharge data service: inline join across discharge tables + outreach_status."""
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import DischargeRecord, DischargesResponse

logger = logging.getLogger(__name__)

# Full discharge query matching the Streamlit app (streamlit_app.py main branch),
# plus a LEFT JOIN to outreach_status for outreach tracking.
_DISCHARGE_QUERY = text("""
SELECT
    de.event_id,
    de.insurance_member_id,
    COALESCE(pt.first_name, '') || ' ' || COALESCE(pt.last_name, '') AS patient_name,
    pt.birth_date,
    pt.phone,
    de.admit_date,
    de.discharge_date,
    d.dx_code,
    d.description,
    de.disposition,
    de.stay_type,
    de.discharge_hospital,
    de.length_of_stay,
    py.payer_name,
    lob.lob_name,
    p.full_name AS provider_name,
    l.parent_org AS practice,
    pt.address AS patient_address,
    pt.city,
    pt.zip_code::character varying(5) AS zip_code,
    pt.state,
    COALESCE(o.status, 'no_outreach') AS outreach_status,
    COALESCE(o.notes, '')             AS outreach_notes,
    o.updated_by                      AS outreach_updated_by,
    o.updated_at                      AS outreach_updated_at
FROM discharge_event de
    LEFT JOIN provider p ON p.provider_id = de.provider_id
    LEFT JOIN payer py ON py.payer_id = de.payer_id
    LEFT JOIN line_of_business lob ON lob.lob_id = de.lob_id
    LEFT JOIN patient pt ON pt.patient_id = de.patient_id
    LEFT JOIN diagnosis_code d ON d.dx_id = de.dx_id
    LEFT JOIN location l ON l.location_id = p.location_id
    LEFT JOIN discharge_app.outreach_status o
        ON o.event_id = de.event_id
        AND o.discharge_date = de.discharge_date
WHERE de.discharge_date IS NOT NULL
ORDER BY de.discharge_date DESC
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
            insurance_member_id=row["insurance_member_id"],
            patient_name=row["patient_name"],
            birth_date=row["birth_date"],
            phone=row["phone"],
            admit_date=row["admit_date"],
            discharge_date=row["discharge_date"],
            dx_code=row["dx_code"],
            description=row["description"],
            disposition=row["disposition"],
            stay_type=row["stay_type"],
            discharge_hospital=row["discharge_hospital"],
            length_of_stay=row["length_of_stay"],
            payer_name=row["payer_name"],
            lob_name=row["lob_name"],
            provider_name=row["provider_name"],
            practice=row["practice"],
            patient_address=row["patient_address"],
            city=row["city"],
            zip_code=row["zip_code"],
            state=row["state"],
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
