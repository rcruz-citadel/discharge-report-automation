# Project Status Report
## Discharge Report Automation — Citadel Health / Aylo Health

**Report Date:** 2026-04-13
**Phase:** V1 Complete — V2 Planning
**Status:** V1 POC Complete — Live on Internal Server

---

## Overview

The Discharge Report Automation project delivers a web-based dashboard that surfaces hospital discharge event data for Citadel Health and Aylo Health staff. The application is built with Python and Streamlit, queries a normalized PostgreSQL database via SQLAlchemy, and is secured with Microsoft Entra ID single-tenant SSO. It is deployed on the internal Linux server CITADELBMI001 (10.1.116.2) and accessible over HTTPS on port 8501.

V1 (read-only dashboard) is complete and live. V2 planning is underway to evolve it into an interactive outreach tracking application.

---

## V1 Status — COMPLETE

| Area | Status |
|---|---|
| Application deployment | Live on CITADELBMI001 |
| Authentication (SSO) | Working — Entra ID single-tenant |
| HTTPS / TLS | Active — self-signed certificate |
| Database schema | Normalized, fully joined |
| Core dashboard features | Complete |
| Assigned To filter | Shipped — pending data finalization |
| UI / header styling | Complete — branded, clean layout |
| Query optimization | Complete — boolean mask filtering, member ID switch |
| DB view for main query | Not yet created (carry to V2) |
| Production TLS certificate | Not yet addressed (carry to V2) |

---

## What's Working

- **Live application** — The Streamlit app is running on CITADELBMI001 over HTTPS (port 8501) and is accessible to internal staff.
- **SSO authentication** — Microsoft Entra ID single-tenant OAuth is active with email domain enforcement. Multi-tenant was evaluated and reverted; single-tenant is the correct configuration for the shared Citadel / Aylo Entra ID tenant.
- **Normalized data model** — The `discharge_event` fact table is joined to seven dimension tables: `provider`, `payer`, `line_of_business`, `patient`, `diagnosis_code`, and `location`. The prior `discharge_master` view has been replaced with an inline multi-join query.
- **Sidebar filters** — Six filters are available: Assigned To (new), Practice, Payer Name, Line of Business, Stay Type, and Date Range.
- **Assigned To filter** — Maps four staff members (Bailey Graham, Kiah Jones, Makeba Crawford, Stephanie Nelson) to their assigned practices, allowing each user to quickly scope the dashboard to their workload.
- **Three tab views** — Recent Discharges (last 14 days), Last 6 Months, and All Discharges.
- **Data caching** — Query results are cached for 5 minutes (`st.cache_data ttl=300`) to reduce database load.
- **CSV export** — Users can export any filtered view to CSV.

---

## Recent Changes

| Commit | Description |
|---|---|
| `ffbc926` | Switch patient_id to insurance_member_id in discharge query |
| `f269b2b` | Optimize filtering: boolean mask instead of chained copies, skip redundant sort |
| `56d2e34` | Shrink Streamlit header height to prevent logo overlap |
| `dce666c` | Add top padding so logo isn't cut off by header bar |
| `851c52d` | Simplify header CSS — blend header into background without hiding native toggle |
| `73bd057` | Add Assigned To sidebar filter mapping staff to their assigned practices |
| `d87b4c0` | Replace `discharge_master` view with inline multi-join query on normalized tables |
| `53b3f90` | Add self-signed TLS certificate generator; update `.gitignore` |
| `9cf811b` | Revert to single-tenant Entra ID auth (from multi-tenant attempt) |
| `fce79f6` | Add Microsoft OAuth authentication with email domain enforcement |

---

## V2 — Outreach Tracking Application

V2 evolves the project from a read-only dashboard into an interactive outreach tracking application with user-level accountability and manager analytics.

---

### V2 Gap Analysis — What Exists vs. What's Needed

#### 1. Outreach Status Tracking

**Goal:** Each discharge record can be marked: No Outreach → Outreach Made → Outreach Complete. Timestamped, attributed to the logged-in user.

| Component | Exists? | Notes |
|---|---|---|
| `discharge_event` table with `event_id` PK | Yes | This is the record users will be updating status on |
| Outreach status table (e.g. `outreach_status`) | **No** | **New table needed.** FK to `discharge_event.event_id`, status enum, `updated_by` (user email), `updated_at` timestamp |
| Write path in the app (INSERT/UPDATE) | **No** | V1 is entirely read-only via `@st.cache_data`. Need SQLAlchemy write operations — likely uncached, direct `INSERT`/`UPDATE` |
| UI for status updates | **No** | Need inline controls per row or a detail view. Streamlit supports `st.data_editor`, buttons, selectboxes — viable but this is the biggest UI change |
| SSO user identity available at runtime | Yes | `st.session_state["user_email"]` and `["user_name"]` are already captured from Entra ID during auth |

#### 2. User Activity Logging

**Goal:** Track when users log in and when they submit outreach status changes.

| Component | Exists? | Notes |
|---|---|---|
| Activity log table (e.g. `user_activity_log`) | **No** | **New table needed.** Columns: user email, action type (login / status_change), timestamp, optional metadata (event_id, old_status, new_status) |
| Login event capture | **Partially** | Auth flow already identifies the user in `check_auth()`. Just need to INSERT a log row after successful authentication |
| Status change event capture | **No** | Comes with outreach status tracking — log each write |

#### 3. Manager View

**Goal:** Dedicated view showing per-user outreach counts, activity timelines, roll-up metrics.

| Component | Exists? | Notes |
|---|---|---|
| Role-based access (staff vs manager) | **No** | **Decision needed.** Options: (a) hardcode manager emails like PRACTICE_ASSIGNMENTS, (b) `app_user` table with a `role` column, (c) Entra ID group claims. Simplest for POC: hardcode a manager list |
| Manager analytics page | **No** | New Streamlit page or tab. Aggregates: outreach counts by user, % complete, login frequency, time-to-outreach |
| Underlying queries / views | **No** | Simple `GROUP BY` on `outreach_status` and `user_activity_log` once those tables exist |

#### 4. Carry-Forward from V1

| Item | Status | Notes |
|---|---|---|
| PRACTICE_ASSIGNMENTS → DB table | **Not started** | Blocked on stakeholder finalization. More important for V2 since user↔practice mapping becomes central to the manager view |
| Main discharge query → PG view | **Partially exists** | `v_discharge_summary` view exists in the DB but uses `patient_v1` and has hardcoded date range. The app's inline query uses `patient` table with `first_name/last_name` concat and `l.parent_org`. These need to be reconciled |
| Self-signed TLS cert | **Not started** | Lower priority but matters more as the app becomes interactive (users submitting data) |

---

### V2 — New Database Objects Needed

```
-- 1. Outreach status per discharge event
CREATE TABLE outreach_status (
    outreach_id    SERIAL PRIMARY KEY,
    event_id       TEXT NOT NULL REFERENCES discharge_event(event_id),
    status         TEXT NOT NULL DEFAULT 'no_outreach',  -- no_outreach | outreach_made | outreach_complete
    updated_by     TEXT NOT NULL,                        -- user email from SSO
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes          TEXT                                  -- optional free-text
);

-- 2. User activity log
CREATE TABLE user_activity_log (
    log_id         SERIAL PRIMARY KEY,
    user_email     TEXT NOT NULL,
    user_name      TEXT,
    action         TEXT NOT NULL,    -- login | outreach_update
    detail         JSONB,           -- e.g. {"event_id": "...", "old_status": "...", "new_status": "..."}
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. App users with roles (optional — could start with hardcoded list)
CREATE TABLE app_user (
    user_email     TEXT PRIMARY KEY,
    display_name   TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'staff',  -- staff | manager
    practices      TEXT[],                         -- replaces PRACTICE_ASSIGNMENTS dict
    is_active      BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### V2 — App Changes Needed

| Change | Scope | Notes |
|---|---|---|
| Write operations (outreach status) | Medium | Add SQLAlchemy INSERT/UPDATE. Can't use `@st.cache_data` for writes — need a separate `get_engine()` write path |
| Outreach UI per discharge row | Medium-Large | `st.data_editor` or per-row selectbox + submit. Biggest UX lift in V2 |
| Login logging | Small | One INSERT in `check_auth()` after successful auth |
| Manager view / page | Medium | New tab or page with aggregate queries. Streamlit `st.tabs` or `st.navigation` |
| Role gate | Small | Check `app_user.role` or hardcoded email list to show/hide manager view |
| Reconcile inline query with `v_discharge_summary` | Small | Update the view or the app query so they match — currently they diverge on patient table and date filtering |

---

### V2 — Detailed Task Breakdown

#### Phase 1: Database Layer
- [x] **Decision: schema strategy** — New `discharge_app` schema. App tables separate from ETL/pipeline tables in `public`.
- [x] **Create `app_user` table** — user email (PK), display name, role (staff/manager), assigned practices array, active flag.
- [x] **Create `outreach_status` table** — Keyed on `(event_id, discharge_date)` — one row per discharge occurrence. No FK due to composite PK on DMZ.
- [x] **Create `user_activity_log` table** — user email, action type (login/outreach_update), JSONB detail, timestamp.
- [x] **Reconcile `v_discharge_summary` view** — Dropped old view + 4 dependents, rebuilt clean. Uses `patient` table, `parent_org` as practice, no hardcoded date range. Dependents recreated.
- [x] **Create indexes** — All indexes created for outreach upsert, manager queries, activity timeline.
- [x] **Seed `app_user` data** — 4 staff (bgraham, kjones3, snelson, mcrawford) + 3 managers (tstevens, soheron, rcruz) seeded.
- [x] **Create `discharge_app_role`** — Dedicated login role with grants on discharge_app schema + public base tables. App reconnected and running.

#### Phase 2: App Write Path
- [x] **Add write engine / session** — `log_activity()` write helper uses `engine.begin()` directly (no cache). `get_engine()` shared for reads and writes.
- [x] **Login logging** — `log_activity(..., action='login', detail={})` called in `check_auth()` after successful auth. Wrapped in try/except — DB failure cannot block sign-in.
- [x] **Outreach status API** — `upsert_outreach_status()` with INSERT ON CONFLICT, `load_outreach_statuses()` cached 60s, audit logging with old/new status.
- [x] **Replace `PRACTICE_ASSIGNMENTS` dict** — `load_practice_assignments()` queries `discharge_app.app_user` (staff, is_active=TRUE). Cached 5 min. Both `render_sidebar_filters()` and `apply_filters()` updated.
- [x] **User role loading** — `get_user_role(email)` queries `discharge_app.app_user`. Role stored in `st.session_state["user_role"]` on login. Cleared on sign-out.

#### Phase 3: Staff Outreach UI
- [x] **Outreach status column in dataframe** — Status column merged from `outreach_status` table. Displayed with color-coded pill badges.
- [x] **Detail panel (Option B)** — Click row to open panel below table. Shows patient info grid (practice, payer, hospital, diagnosis, LOS, disposition), 3 status buttons, notes textarea, last updated line, Save/Cancel.
- [x] **Status change confirmation + logging** — Save upserts `outreach_status`, logs to `user_activity_log`, clears cache, refreshes view.
- [x] **Visual indicators** — Color-coded status pills (gray/orange/green). Legend above table.

#### Phase 4: Manager View
- [x] **Role gate** — 4th "Manager Dashboard" tab visible only when `user_role == "manager"`.
- [x] **Outreach summary metrics** — Stat chips: Total, No Outreach, Outreach Made, Complete, % Complete.
- [x] **Per-user breakdown** — Staff table with name, practice count, totals by status, % done, last login, last activity.
- [x] **Practice-level roll-ups** — Practice table with status counts and % complete.
- [x] **Date-range filtering** — Manager view respects sidebar date filters.

#### Phase 5: Performance & Polish
- [ ] **Fix UI lag on filter/action (~3s pause)** — Every interaction triggers a full Streamlit rerun with re-render. Investigate: fragment reruns (`st.fragment`), reducing unnecessary reruns from status button clicks, optimizing `_merge_outreach()` (row-level apply is slow on large DataFrames — switch to vectorized merge), and minimizing HTML re-renders.
- [ ] **Production TLS certificate** — Replace self-signed cert.
- [ ] **Second report from discharge query** — Requirements pending.
- [ ] **Merge feature branch to main** — After testing and stakeholder sign-off.

### V2 — Summary Scorecard

| Requirement | Status | Notes |
|---|---|---|
| SSO identity | **Complete** | Email lowercase-normalized, stored in session state |
| Discharge data model | **Complete** | `v_discharge_summary` view reconciled and live |
| Outreach status storage | **Complete** | `discharge_app.outreach_status` keyed on (event_id, discharge_date) |
| Activity logging | **Complete** | `discharge_app.user_activity_log` — login + outreach_update events |
| User/role management | **Complete** | `discharge_app.app_user` — 4 staff + 3 managers seeded |
| Write path in app | **Complete** | `upsert_outreach_status()` + `log_activity()` |
| Outreach UI (detail panel) | **Complete** | Option B — click row, detail panel with status/notes/save |
| Manager analytics view | **Complete** | Role-gated tab with summary chips, per-user and per-practice tables |
| Practice assignments in DB | **Complete** | `load_practice_assignments()` from `app_user` |
| UI performance optimization | **To Do** | ~3s lag on filter/action — needs `st.fragment`, vectorized merge, rerun reduction |
| Production TLS cert | **To Do** | Self-signed cert still in use |
| Merge to main | **To Do** | After testing + stakeholder sign-off |

---

## Repository

**GitHub:** `rcruz-citadel/discharge-report-automation`
**Branch:** `main`
**Server:** CITADELBMI001 — `/opt/discharge_report_automation` (Python venv)
