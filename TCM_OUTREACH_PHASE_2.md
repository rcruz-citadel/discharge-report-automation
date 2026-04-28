# TCM Outreach Tracker — Phase 2 Project Brief

**Branch:** `feature/outreach-tracking`
**Date drafted:** 2026-04-24
**Drafted by:** Ronnie Cruz

---

## Overview

Phase 2 expands the TCM outreach tracker with two new workflow statuses, automatic home health exclusions, a nightly auto-fail job, urgency-based sorting with a days-remaining badge, and a proposed shift from time-based tabs to three workflow-oriented priority queues. Several implementation decisions are pending stakeholder confirmation from the 2026-04-24 meeting follow-up email.

---

## Current State

- **Statuses (4):** `no_outreach`, `outreach_made`, `outreach_complete`, `failed`
- **Attempt tracking:** max 3 attempts, timestamped
- **Tabs:** Recent (30 days), Last 6 Months, All Discharges
- **Sidebar filters:** practice, payer, LOB, stay type, date range, assignee
- **Manager dashboard:** KPI cards
- **Legend filter:** multi-select, clickable
- **Export:** CSV
- **Stack:** React (Vite + TypeScript) + FastAPI + PostgreSQL (`discharge_app` schema)
- **Deployment:** `discharge_v3_staging` on DMZ server

---

## Phase 2 Scope

### 1. Two New Statuses

Add `late_delivery` and `no_outreach_required` to the existing four statuses.

| Status | Meaning | Suggested Color |
|---|---|---|
| `late_delivery` | ADT received after 48-hr window but still within 7/30-day deadline; still workable | Amber / `#F59E0B` |
| `no_outreach_required` | No action needed (home health discharges, etc.) | Medium gray / `#9CA3AF` |

**Files:**
- `backend/app/models/schemas.py` — add to `VALID_STATUSES`
- `frontend/src/types/discharge.ts` — add statuses and color mappings
- `frontend/src/components/discharge/OutreachStatusForm.tsx` — add new status buttons
- `frontend/src/components/discharge/OutreachLegend.tsx` — add new statuses to legend/filter

---

### 2. Home Health Auto-Filter

Records where `discharge_hospital` contains "home health" (case-insensitive) must be excluded from all queues at the backend query level. These discharges do not require TCM outreach.

**Files:**
- `backend/app/services/discharge_service.py` — add `WHERE LOWER(discharge_hospital) NOT LIKE '%home health%'` to discharge query

---

### 3. Auto-Fail Logic

A nightly job auto-sets status to `failed` for records that have aged past their TCM deadline without reaching `outreach_complete`:

| Stay Type | Hard Stop | Condition |
|---|---|---|
| ER | 7 days | `(today - discharge_date) > 7` AND status != `outreach_complete` |
| Inpatient | 30 days | `(today - discharge_date) > 30` AND status != `outreach_complete` |

**Implementation options (choose one):**
- FastAPI background task (`APScheduler`) that runs at a scheduled time each night
- PostgreSQL scheduled function via `pg_cron` (if available on DMZ server)

**Files:**
- New: `backend/app/tasks/auto_fail.py` — auto-fail job logic
- `backend/app/services/outreach_service.py` — expose update function the job calls

---

### 4. Three-Queue Tab Structure *(pending stakeholder confirmation)*

Replace current time-based tabs with workflow-oriented priority queues. Each queue is sorted by urgency (fewest days remaining first).

| Queue | Label | Criteria |
|---|---|---|
| 1 | High Priority | Within 48-hour window from discharge; full TCM credit possible |
| 2 | Active | Past 48 hrs but within 7 days (ER) or 30 days (inpatient); partial credit still available |
| 3 | Low Priority | Past 7/30-day hard stop; only action is dropping discharge summary in chart |

*This restructure is a recommendation from the 2026-04-24 stakeholder meeting. Implementation is blocked until the queue structure is confirmed (see Open Items #2).*

**Files (if confirmed):**
- `frontend/src/pages/DashboardPage.tsx` — replace time-based tabs with queue tabs; add days-remaining computation

---

### 5. Days-Remaining Badge

Each table row displays a color-coded badge showing days left until TCM deadline.

| Stay Type | Formula |
|---|---|
| ER | `7 - (today - discharge_date)` |
| Inpatient | `30 - (today - discharge_date)` |

| Value | Badge Color |
|---|---|
| > 3 days | Green |
| 1–3 days | Yellow |
| < 1 day | Red |
| Past deadline | Gray |

**Files:**
- `frontend/src/components/discharge/DischargeTable.tsx` — add days-remaining column with badge
- `frontend/src/pages/DashboardPage.tsx` — pass computed days-remaining to table

---

### 6. Sort by Urgency

Default sort for all queues: ascending by days remaining (most urgent record first). Users can override with manual column sort.

**Files:**
- `frontend/src/pages/DashboardPage.tsx` — apply default sort before passing data to table

---

## Open Items (Blocking)

These decisions must be confirmed before the corresponding feature can be finalized. A follow-up email was sent to stakeholders on 2026-04-24.

1. **3-attempt rule** — After 3 failed attempts, does the record auto-advance to `outreach_complete` or remain as `outreach_made`?
2. **Queue structure** — Confirm the 3-queue tab layout (High Priority / Active / Low Priority) vs. keeping the current time-based tabs.
3. **`no_outreach_required` types** — What discharge types beyond home health should be auto-excluded or auto-set to `no_outreach_required`?
4. **Late delivery indicator** — Should the UI show how many days late the ADT arrived, or just the status label?
5. **Low-priority queue actions** — Does Queue 3 support the full status flow, or just a simple "Discharge Summary Dropped" checkbox?
6. **New team member onboarding** — Should the app include in-app tooltips, or is a separate workflow document sufficient?
7. **Discharge summary deadline** — Is there a hard cutoff date/time for dropping the summary, or is it open-ended?

---

## Files to Change

### Backend

| File | Change |
|---|---|
| `backend/app/models/schemas.py` | Add `late_delivery`, `no_outreach_required` to `VALID_STATUSES` and schema models |
| `backend/app/services/discharge_service.py` | Add home health exclusion filter to discharge query |
| `backend/app/services/outreach_service.py` | Expose bulk update function for auto-fail job |
| `backend/app/tasks/auto_fail.py` *(new)* | Nightly auto-fail job; mark expired records as `failed` |

### Frontend

| File | Change |
|---|---|
| `frontend/src/types/discharge.ts` | Add new statuses and color mappings |
| `frontend/src/components/discharge/OutreachStatusForm.tsx` | Add new status buttons |
| `frontend/src/components/discharge/OutreachLegend.tsx` | Add new statuses to legend/filter |
| `frontend/src/pages/DashboardPage.tsx` | Restructure tabs into queues; add days-remaining computation and default sort |
| `frontend/src/components/discharge/DischargeTable.tsx` | Add days-remaining column with color-coded badge |

---

## Not in Scope

The following items are explicitly deferred and do not belong to this phase:

- HEDIS measure tracking
- Payer-specific rules or billing integration
- Role-based access control beyond manager vs. coordinator distinction
- Active admits tab (belongs to `main` branch)
- PostgreSQL view for the inline discharge query (planned but not blocking)
- Mobile-responsive layout
- Email/SMS notification system
- Migration from `feature/outreach-tracking` to `main`
