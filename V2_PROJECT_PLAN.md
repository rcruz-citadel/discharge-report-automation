# V2 Project Plan — Discharge Report Automation
**Citadel Health / Aylo Health**
**Plan Date:** 2026-04-13
**Last Updated:** 2026-04-13
**Status:** V1 Complete — V2 In Progress (Phase 1 SQL Ready)

---

## Team

| Name | Role | Email |
|------|------|-------|
| Ronnie Cruz | Developer / Analyst (sole implementer) | ronnie.cruz@citadelhealth.com |
| Trevor Stevens | Manager / Stakeholder | trevor.stevens@citadelhealth.com |
| Shaun Oheron | Manager / Stakeholder | shaun.oheron@citadelhealth.com |

---

## Executive Summary

V2 evolves the Discharge Report Dashboard from a read-only data display into an **interactive outreach tracking application**. Staff will be able to record whether they have contacted patients after discharge (No Outreach → Outreach Made → Outreach Complete), and managers will gain a dedicated analytics view showing team performance and outreach completion rates by practice and time window.

The application already has the hard parts done: SSO is live, user identity is captured in session state, and the normalized discharge data model is solid. V2 builds a write layer on top of that foundation. The architectural challenge is that Streamlit is a reactive, stateless framework — adding write operations requires careful separation of the cached read path from direct-write database sessions, and UI state management for per-row interactions is non-trivial.

V2 is scoped into five phases. Phases 1 and 2 are pure backend/infrastructure work and can be completed without touching the visible UI. Phases 3 and 4 are the user-facing changes. Phase 5 covers carry-forward polish items from V1.

**Phase 1 SQL is written and ready to run.** `v2_database_setup.sql` contains all DDL, indexes, seed data, and the reconciled view. The only blocker before running it is confirming actual SSO email addresses (D7) and manager users (D8).

---

## Architectural Note: Read-Only to Read-Write in Streamlit

This is the most important design constraint for V2.

**V1 architecture:** All DB access goes through `@st.cache_data(ttl=300)` which caches the entire discharge DataFrame in memory. This is correct and efficient for read-only display.

**V2 must preserve this for reads and add a separate path for writes.** Specifically:

- `get_engine()` is decorated with `@st.cache_resource` — it returns a shared engine and is fine as-is.
- Write operations (INSERT/UPDATE) must use `engine.begin()` directly — never through the cached `load_discharge_data()` path.
- After a write, the relevant cache entry must be cleared with `st.cache_data.clear()` or a targeted key clear so the UI reflects the new state on the next rerender.
- **Do not use `st.data_editor` for the outreach status column if row-level write confirmation is needed.** `st.data_editor` fires on every cell edit without a confirmation step — this can produce accidental writes. A per-row selectbox + "Save" button pattern is more controllable, though more verbose to build.
- Every write must be wrapped in a try/except with user-visible error feedback (`st.error()`). Silent failures in a status-tracking app are worse than visible errors.

---

## Phase 1: Database Layer

**Goal:** All new tables and the reconciled view are in place. No app code changes yet.

**Dependency:** None — this is the foundation everything else builds on.

**Status: SQL READY — pending email confirmation before running**

**Estimated effort:** 30 minutes to run once email addresses are confirmed (DDL is complete in `v2_database_setup.sql`)

### Tasks

| # | Task | Description | Status | Acceptance Criteria |
|---|------|-------------|--------|---------------------|
| 1.1 | Create `discharge_app` schema | Run `CREATE SCHEMA discharge_app` on CITADELBMI001 | Ready to run | Schema visible in `\dn` |
| 1.2 | Create `app_user` table | DDL in `v2_database_setup.sql` Section 1 | Ready to run | Table exists; constraints enforced; indexes in place |
| 1.3 | Create `outreach_status` table | DDL in `v2_database_setup.sql` Section 2 | Ready to run | Table exists; UNIQUE on `event_id`; FK to `discharge_event` valid |
| 1.4 | Create `user_activity_log` table | DDL in `v2_database_setup.sql` Section 3 | Ready to run | Table exists; GIN index on `detail`; composite index on `(user_email, created_at)` |
| 1.5 | Replace `v_discharge_summary` view | Run `CREATE OR REPLACE VIEW` from Section 5 | Ready to run | View returns rows; uses `patient` (not `patient_v1`); includes `event_id` and `practice` columns |
| 1.6 | Seed `app_user` data | Run INSERT statements from Section 4 | Blocked on D7 | 4 staff rows present; practice arrays match current `PRACTICE_ASSIGNMENTS` dict |
| 1.7 | Update email addresses | Replace placeholder emails with actual Entra ID SSO emails | **Blocked — need real emails** | `SELECT user_email FROM app_user` matches what the app sees in `session_state["user_email"]` |
| 1.8 | Add manager users | Insert Trevor Stevens and Shaun Oheron with `role = 'manager'` | Blocked on D8 | Both manager rows present with correct emails |
| 1.9 | Set `search_path` on DB connection | Update `DATABASE_URL` in `.streamlit/secrets.toml` to append `?options=-c%20search_path%3Ddischarge_app,public` | Ready to run | App connects and resolves `app_user` without schema prefix |

**Blocker for 1.6/1.7:** Confirm exact email format returned by Entra ID. Add a temporary `st.write(st.session_state.get("user_email"))` to the running app, have one staff member log in, read the exact format, then remove the debug line. This unblocks seeding.

**Blocker for 1.8:** Confirm Trevor Stevens and Shaun Oheron email addresses and that they should be the manager users. Emails listed in the team table above — verify these are their actual Entra ID UPNs.

---

## Phase 2: App Write Path

**Goal:** The app can write to the database. No visible UI changes — this is plumbing.

**Dependency:** Phase 1 complete (tables must exist before any write functions can be tested).

**Estimated effort:** 2–3 hours

### Tasks

| # | Task | Description | Acceptance Criteria |
|---|------|-------------|---------------------|
| 2.1 | Add write helper functions | `get_outreach_status(event_id)`, `upsert_outreach_status(event_id, status, user_email, notes)`, `log_activity(user_email, user_name, action, detail)` | Functions execute without error against the live DB; unit-testable in isolation |
| 2.2 | Login logging | Call `log_activity(..., action='login')` in `check_auth()` after successful authentication | A login row appears in `user_activity_log` after each SSO sign-in; verify with `SELECT * FROM discharge_app.user_activity_log ORDER BY created_at DESC LIMIT 5` |
| 2.3 | Replace `PRACTICE_ASSIGNMENTS` dict | Query `app_user` table instead of hardcoded dict; cache with `@st.cache_data(ttl=600)` | Sidebar "Assigned To" filter still works; dropdown options come from DB; adding/deactivating a user in `app_user` is reflected on next cache expiry |
| 2.4 | Add cache-clear after writes | After any `upsert_outreach_status()` call, clear the discharge data cache | The discharge table refreshes to show the new status after a write without requiring a manual page reload |

**Note on 2.3:** Query `SELECT display_name, practices FROM app_user WHERE is_active = TRUE AND role = 'staff'` and reconstruct the dict in Python. The sidebar filter logic does not change, only its data source.

---

## Phase 3: Staff Outreach UI

**Goal:** Staff can see and update outreach status for each discharge record.

**Dependency:** Phase 2 complete. Write path must exist and be verified before any UI can call it.

**Estimated effort:** 3–5 hours (largest single UI change in V2)

### Tasks

| # | Task | Description | Acceptance Criteria |
|---|------|-------------|---------------------|
| 3.1 | Load outreach status into DataFrame | LEFT JOIN `outreach_status` into `load_discharge_data()` on `event_id` | Each row has an `Outreach Status` column; NULL becomes `no_outreach`; existing data is unaffected |
| 3.2 | Display status per row | Show `Outreach Status` column in all three tab views | Column renders correctly; default value for new records shows as `no_outreach` |
| 3.3 | Per-row status update control | Selectbox (`no_outreach / outreach_made / outreach_complete`) + optional notes field + "Save" button per row (see D6) | User can select a status, optionally add a note, click Save, and the change is submitted |
| 3.4 | Write on submit | Call `upsert_outreach_status()` and `log_activity()` on Save | DB row upserted; `user_activity_log` entry created with old/new status in `detail`; UI refreshes to show updated status |
| 3.5 | Visual row indicators | Color-code rows: grey = no_outreach, yellow = outreach_made, green = outreach_complete | Outreach state is visually scannable without reading the status text |
| 3.6 | Error handling | Wrap writes in try/except; show `st.error()` on failure | Failed writes show a user-visible error message; no silent failures; partial writes do not corrupt state |

**Design decision gates this phase (D6):** Inline per-row controls vs. click-to-expand detail panel. See Decision Log. Pick before writing any Phase 3 code — the two approaches have different component structures.

---

## Phase 4: Manager View

**Goal:** Managers see a dedicated analytics view gated by role.

**Dependency:** Phase 2 complete for role lookup. Phase 3 should be substantially complete — you need real outreach data accumulating to validate that manager metrics are correct.

**Estimated effort:** 3–4 hours

### Tasks

| # | Task | Description | Acceptance Criteria |
|---|------|-------------|---------------------|
| 4.1 | Role gate | After auth, query `app_user.role` for the logged-in user; store in `session_state["user_role"]` | Staff users do not see the manager tab; manager users (Trevor Stevens, Shaun Oheron) do |
| 4.2 | Manager tab / page | Add a "Manager View" tab using `st.tabs` (or `st.navigation` if moving to multi-page) | Tab is visible only when `session_state["user_role"] == "manager"` |
| 4.3 | Outreach summary metrics | Per-user table: total assigned discharges, no_outreach count, outreach_made count, outreach_complete count, % complete | Table renders with counts that match what `SELECT ... GROUP BY updated_by FROM outreach_status` returns |
| 4.4 | Activity timeline | Per-user: last login time, last outreach update, count of updates in selected window | Timeline renders; date-range filter correctly scopes the counts |
| 4.5 | Practice-level roll-ups | Outreach completion rate grouped by `practice` (from `v_discharge_summary`) | Roll-up table or chart renders; percentages match manual spot-check |
| 4.6 | Date-range filter for manager view | Independent date range widget scoping manager metrics (separate from the existing discharge date filter) | Changing the manager date filter updates metrics without affecting the staff discharge view |

**Testing note:** If no outreach data has accumulated when you start Phase 4, insert a few test rows directly into `outreach_status` to verify the metrics queries work before wiring up the UI.

---

## Phase 5: Carry-Forward / Polish

**Goal:** Close out V1 deferred items and V2 polish.

**Dependency:** Independent of Phases 3–4. Can be worked in parallel at any point.

**Estimated effort:** Variable

### Tasks

| # | Task | Description | Acceptance Criteria |
|---|------|-------------|---------------------|
| 5.1 | Production TLS certificate | Replace self-signed cert on CITADELBMI001 — internal CA cert or Let's Encrypt (requires public DNS) | Browser no longer shows certificate warning for any staff user |
| 5.2 | Second discharge report | Requirements pending — blocked on stakeholder input from Trevor Stevens / Shaun Oheron | N/A until requirements are defined |

---

## Phase Dependencies

```
Phase 1 (DB Layer) ──► Phase 2 (Write Path) ──► Phase 3 (Staff UI) ──► Phase 4 (Manager View)
                                                                                │
Phase 5 (Polish) ───────────────────────────────────────────────────────────►──┘ (independent)
```

- Phase 1 must be 100% complete before Phase 2 begins. You cannot test write functions against tables that don't exist.
- Phase 2 must be 100% complete before Phase 3 begins. The UI cannot call write functions that don't exist.
- Phase 3 should be substantially complete (at minimum Task 3.4 working) before Phase 4, so manager metrics have real data to validate against.
- Phase 5 is fully independent and can be done at any point without affecting the other phases.

---

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R1 | SSO email format mismatch — `app_user.user_email` doesn't match what Entra ID returns in session state | High | High | Verify format from a live session before seeding any data. One debug `st.write()` line and one staff login resolves this permanently. Do not guess the format. |
| R2 | `outreach_status` UNIQUE constraint (one status per event) is wrong if multi-user conflict tracking is needed later | Medium | Medium | Design decision is intentional — document it (see D2). If history is needed, add `outreach_status_history` table; do not change the primary table. |
| R3 | Streamlit cache invalidation after writes causes full-page rerender / UX flicker | High | Low | Expected Streamlit behavior. Minimize by clearing only the specific cached function, not all caches. Worth a brief heads-up to staff so it's not filed as a bug. |
| R4 | `st.data_editor` used for outreach UI triggers accidental writes on cell focus | Medium | Medium | Avoid `st.data_editor` for the write path entirely. Use explicit selectbox + Save button (see architectural note). |
| R5 | Placeholder email addresses in seed data never get corrected, causing practice filter to silently break | Medium | High | Task 1.7 is a hard prerequisite before running ANY Phase 1 seeds. Do not run Section 4 of the SQL until emails are confirmed. |
| R6 | No outreach data in DB when Phase 4 is being built, making manager metrics impossible to validate | Medium | Low | Insert a handful of test rows into `outreach_status` manually before building Phase 4 UI — don't wait for organic data. |
| R7 | `v_discharge_summary` view reconciliation reveals row count differences vs. what V1 was showing | Low | Medium | After running Phase 1, run `SELECT COUNT(*) FROM v_discharge_summary` and compare to current app row counts. Spot-check 3–5 patient names across both. |
| R8 | Production TLS certificate (Phase 5) requires IT involvement or DNS change — long lead time | Medium | Low | Start the cert request in parallel with Phases 2–4. Do not block V2 launch on it, but don't leave it indefinitely. |
| R9 | Phase 3 UI pattern decision (D6) made too late, requiring a rework mid-implementation | Medium | Medium | Make D6 decision before writing any Phase 3 code. The inline vs. detail panel choice affects component structure throughout Phase 3. |
| R10 | Trevor Stevens or Shaun Oheron emails are not valid Entra ID UPNs (e.g., they use aliases or different domains) | Low | Medium | Confirm emails with both managers before inserting their rows. Ask them to send a test login to verify their UPN appears correctly in session state. |

---

## Decision Log

### Decisions Made

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| D1 | New `discharge_app` schema for V2 tables | public schema has ~90 pipeline-owned tables; separate schema gives clean ownership, simpler permission grants, and clearer intent | 2026-04-13 |
| D2 | `outreach_status` uses upsert (one row per event) rather than append-only history | Simpler app logic; the current status is what matters for staff view. Full history is reconstructable from `user_activity_log` which records old/new status on every change. | 2026-04-13 |
| D3 | Role management via `app_user` table (not hardcoded list, not Entra ID group claims) | Hardcoded list was the V1 pattern (PRACTICE_ASSIGNMENTS) — a table unifies both concerns and is already planned. Entra ID group claims require app registration changes and are higher complexity for a small team. | 2026-04-13 |
| D4 | `v_discharge_summary` view stays in `public` schema | The view references public schema tables and is read by the app without schema prefix. Moving it to `discharge_app` would require search_path changes and add confusion with cross-schema references. | 2026-04-13 |
| D5 | `updated_by` in `outreach_status` is TEXT (not FK to `app_user`) | Audit trail entries should survive user deactivation. Loose coupling is correct for log-style data. | 2026-04-13 |
| D6 | Phase 1 SQL (`v2_database_setup.sql`) is complete and ready to run | DDL, indexes, seed data template, and reconciled view are all written. Only blockers are confirming real email addresses before running the seed inserts. | 2026-04-13 |

### Decisions Still Needed

| ID | Question | Options | Owner | Needed By |
|----|----------|---------|-------|-----------|
| D7 | What are the exact Entra ID UPN/email addresses for the 4 staff members? | Check running app server logs or add temporary debug display to capture `session_state["user_email"]` | Ronnie | Before Phase 1 Task 1.6 — hard blocker |
| D8 | Confirm Trevor Stevens and Shaun Oheron email addresses for manager rows | Verify their actual Entra ID UPNs match the `@citadelhealth.com` format | Ronnie / Trevor / Shaun | Before Phase 1 Task 1.8 |
| D9 | Outreach UI pattern: inline per-row controls vs. click-to-expand detail panel | Inline = simpler dev, slightly cluttered table. Detail panel = cleaner UX but requires more Streamlit state management | Ronnie | Before Phase 3 starts — gates all of Phase 3 |
| D10 | Should per-event outreach history be visible to staff (all changes, not just current)? | Current design shows only current state per event. History exists in `user_activity_log` but is not surfaced in the UI. | Ronnie / Trevor / Shaun | Before Phase 3 starts |
| D11 | Second discharge report (Phase 5.2) — what is it, what data does it need? | Requirements undefined — Trevor Stevens / Shaun Oheron to provide | Trevor / Shaun | TBD |
| D12 | Production TLS — internal CA cert or public cert (Let's Encrypt)? | Internal CA: faster, no DNS changes, trusted inside network. Let's Encrypt: trusted by default in all browsers, requires public DNS for ACME challenge. | Ronnie / IT | Phase 5 |

---

## Files

| File | Purpose | Status |
|------|---------|--------|
| `v2_database_setup.sql` | Production-ready DDL for all 3 new tables, indexes, seed data template, and reconciled view. Run on CITADELBMI001 to complete Phase 1. | Ready — pending email confirmation |
| `V2_PROJECT_PLAN.md` | This file. Phase-by-phase plan, risk register, decision log. | Current |
| `PROJECT_STATUS.md` | V1 completion status and V2 gap analysis. | Reference — no changes needed |

---

## Immediate Next Steps

1. **Confirm SSO email format (D7)** — Add a temporary `st.write(st.session_state.get("user_email"))` to the running app. Have one staff member log in. Copy the exact string. Remove the debug line. This is the single most important action before anything else in Phase 1.

2. **Confirm Trevor Stevens and Shaun Oheron Entra ID emails (D8)** — Verify the `@citadelhealth.com` addresses are their actual UPNs, not aliases. Quick message to both of them.

3. **Run `v2_database_setup.sql` on CITADELBMI001 (Phase 1)** — Once emails are confirmed, update the seed INSERT statements in Section 4 of the SQL file and run the whole script. Phase 1 closes in one shot.

4. **Decide outreach UI pattern (D9)** — Make this call before writing any Phase 3 code. Inline selectbox + Save button is faster to ship. Detail panel is cleaner for users. Pick one.

5. **Start Phase 2 write helpers** — These can be written and unit-tested locally against the DB while D9 is still being decided, since Phase 2 has no UI dependency.
