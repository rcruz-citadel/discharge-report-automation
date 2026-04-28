"""Pydantic request/response models.

These are the canonical contract between backend and frontend.
TypeScript interfaces in frontend/src/types/ must match these schemas.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────


class AuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


class AuthCallbackResponse(BaseModel):
    ok: bool = True


class MeResponse(BaseModel):
    email: str
    name: str
    role: Optional[str] = None

    @property
    def is_manager(self) -> bool:
        return self.role in ("manager", "admin")


class LogoutResponse(BaseModel):
    ok: bool = True


# ── Discharge records ─────────────────────────────────────────────────────────


class DischargeRecord(BaseModel):
    event_id: str
    insurance_member_id: Optional[str] = None
    patient_name: Optional[str] = None
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    admit_date: Optional[date] = None
    discharge_date: date
    dx_code: Optional[str] = None
    description: Optional[str] = None
    disposition: Optional[str] = None
    stay_type: Optional[str] = None
    discharge_hospital: Optional[str] = None
    length_of_stay: Optional[int] = None
    payer_name: Optional[str] = None
    lob_name: Optional[str] = None
    provider_name: Optional[str] = None
    practice: Optional[str] = None          # l.parent_org aliased as practice
    patient_address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    state: Optional[str] = None
    # Joined from outreach_status
    outreach_status: str = "no_outreach"
    outreach_notes: str = ""
    outreach_updated_by: Optional[str] = None
    outreach_updated_at: Optional[datetime] = None
    discharge_summary_dropped: bool = False


class DischargesResponse(BaseModel):
    records: list[DischargeRecord]
    total: int
    loaded_at: datetime


# ── Outreach ──────────────────────────────────────────────────────────────────


VALID_STATUSES = {
    "no_outreach",
    "outreach_made",
    "outreach_complete",
    "failed",
    "late_delivery",
    "no_outreach_required",
}


class OutreachUpsertRequest(BaseModel):
    discharge_date: date
    status: str
    notes: str = ""
    discharge_summary_dropped: bool = False

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


class OutreachRecord(BaseModel):
    event_id: str
    discharge_date: date
    status: str
    notes: str = ""
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    discharge_summary_dropped: bool = False


class OutreachAttempt(BaseModel):
    id: int
    event_id: str
    discharge_date: date
    attempt_number: int
    attempted_by: str
    attempted_at: datetime


class LogAttemptResponse(BaseModel):
    attempt: OutreachAttempt
    attempt_number: int
    attempts_remaining: int
    auto_completed: bool = False


# ── Meta / Filters ────────────────────────────────────────────────────────────


class AssigneeInfo(BaseModel):
    name: str
    practices: list[str]


class MetaFiltersResponse(BaseModel):
    practices: list[str]
    payers: list[str]
    lob_names: list[str]
    stay_types: list[str]
    assignees: list[AssigneeInfo]
    discharge_date_min: Optional[date] = None
    discharge_date_max: Optional[date] = None


# ── Manager metrics ───────────────────────────────────────────────────────────


class OutreachSummary(BaseModel):
    total: int
    no_outreach: int
    outreach_made: int
    outreach_complete: int
    failed: int
    late_delivery: int
    no_outreach_required: int
    pct_complete: float


class StaffBreakdownRow(BaseModel):
    user_email: str
    display_name: str
    practice_count: int
    total: int
    no_outreach: int
    outreach_made: int
    outreach_complete: int
    failed: int
    late_delivery: int
    no_outreach_required: int
    pct_complete: float
    last_login: Optional[date] = None
    last_activity: Optional[date] = None


class PracticeRollupRow(BaseModel):
    practice: str
    total: int
    no_outreach: int
    outreach_made: int
    outreach_complete: int
    failed: int
    late_delivery: int
    no_outreach_required: int
    pct_complete: float


class ManagerMetricsResponse(BaseModel):
    summary: OutreachSummary
    staff_breakdown: list[StaffBreakdownRow]
    practice_rollup: list[PracticeRollupRow]
