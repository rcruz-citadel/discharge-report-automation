"""Unit tests for Pydantic schemas — no DB or HTTP needed."""
import pytest
from pydantic import ValidationError

from app.models.schemas import OutreachUpsertRequest


def test_valid_outreach_statuses() -> None:
    for status in ("no_outreach", "outreach_made", "outreach_complete"):
        req = OutreachUpsertRequest(discharge_date="2026-03-15", status=status)
        assert req.status == status


def test_invalid_outreach_status() -> None:
    with pytest.raises(ValidationError) as exc_info:
        OutreachUpsertRequest(discharge_date="2026-03-15", status="invalid_status")
    assert "status must be one of" in str(exc_info.value)


def test_outreach_notes_default_empty() -> None:
    req = OutreachUpsertRequest(discharge_date="2026-03-15", status="no_outreach")
    assert req.notes == ""


def test_discharge_record_outreach_defaults() -> None:
    from app.models.schemas import DischargeRecord
    rec = DischargeRecord(event_id="EVT-001", discharge_date="2026-03-15")
    assert rec.outreach_status == "no_outreach"
    assert rec.outreach_notes == ""
    assert rec.outreach_updated_by is None
