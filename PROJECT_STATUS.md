# Project Status Report
## Discharge Report Automation — Citadel Health / Aylo Health

**Report Date:** 2026-04-14
**Phase:** V2 Streamlit Complete — V3 React Migration Planning
**Status:** V2 feature-complete on `feature/outreach-tracking` branch. Planning migration to FastAPI + React for performance.

---

## Overview

The Discharge Report Automation project is an outreach tracking application for Citadel Health and Aylo Health staff. It surfaces hospital discharge events and allows staff to track outreach status per patient. Managers have an analytics dashboard with per-user and per-practice metrics.

The application was originally built with Streamlit (Python). V1 (read-only dashboard) and V2 (outreach tracking, activity logging, manager view) are feature-complete. However, Streamlit's full-page-rerun architecture creates a ~2-3 second lag on every interaction, which is unacceptable for bulk outreach workflows. V3 will migrate the frontend to React with a FastAPI backend to achieve sub-second interactions.

---

## Deployment

| Instance | Branch | Port | Role |
|---|---|---|---|
| Production (V1) | `main` | 8501 | Stable read-only dashboard, always-on via systemctl |
| V2 Test | `feature/outreach-tracking` | 8502 | Outreach tracking, manual start |
| Server | CITADELBMI001 | 10.1.116.2 | Internal Linux server |

---

## What's Done (V1 + V2)

### Database Layer (live on DMZ PostgreSQL)
- `discharge_app` schema with `app_user`, `outreach_status`, `user_activity_log` tables
- `v_discharge_summary` view — clean column set, no hardcoded date range
- `discharge_app_role` — dedicated login role with scoped grants
- 4 staff + 3 managers seeded in `app_user`
- Indexes for upsert, manager queries, activity timeline

### Application Features (Streamlit, feature branch)
- Microsoft Entra ID SSO with email domain enforcement
- Outreach status tracking — click row, detail panel, status radio, notes, save
- Activity logging — login events and outreach status changes
- Manager dashboard — role-gated tab with per-user and per-practice metrics
- Practice assignments loaded from DB (replaces hardcoded dict)
- CSV export on all filtered views

### What V2 Proved
- The data model and write path work correctly
- The UI design (detail panel, status controls, manager tables) is validated
- SSO identity and role-based gating work
- **Streamlit is the bottleneck** — full script re-execution on every interaction causes 2-3s lag regardless of optimization (st.fragment, cached merges, vectorized joins, CSS overlay suppression all attempted)

---

## V3 — React Migration

### Why Migrate
Streamlit re-executes the entire Python script on every user interaction. With 17k rows, 400 lines of CSS, sidebar widgets, 3-4 tabs, and a detail panel — every click takes 2-3 seconds. This is a framework limitation, not a code issue. For a bulk workflow where staff process 20-50 patients per session, this is a productivity tax.

React handles state client-side. Row clicks, status selection, panel open/close are instant. Only Save triggers a network request (~100ms). Filters recompute from cached client-side data.

### Architecture

```
Frontend: React (Vite)                    Backend: FastAPI (Python)
├── Auth (MSAL.js + Entra ID)            ├── /api/auth/callback
├── Sidebar filters                       ├── /api/discharges (GET)
├── DischargeTable (TanStack Table)       ├── /api/outreach/{event_id} (GET/PUT)
├── DetailPanel (split-pane right)        ├── /api/activity (POST)
├── ManagerDashboard (role-gated)         ├── /api/manager/metrics (GET)
└── Branded CSS (port existing tokens)    └── /api/users (GET)
```

### What Carries Over (no rebuild needed)
- PostgreSQL schema — `discharge_app.*` tables unchanged
- All SQL queries — translate to FastAPI route handlers
- Design tokens — #132e45, #e07b2a, component styles port directly
- SSO tenant config — same Entra ID app registration, MSAL.js replaces MSAL Python
- Business logic — outreach upsert, activity logging, role gating

### What Needs Building
| Component | Effort | Notes |
|---|---|---|
| FastAPI backend + API routes | 1-2 weeks | SQLAlchemy queries already written, wrap in endpoints |
| Entra ID auth (MSAL.js) | 2-3 days | Same app registration, JS callback flow |
| React app scaffold (Vite) | 1 day | Project setup, routing, auth context |
| Discharge table (TanStack Table) | 3-4 days | Sortable, filterable, selectable, 17k rows virtualized |
| Detail panel (split-pane) | 2-3 days | Status radio, notes, save — port from mockup design |
| Sidebar filters | 2-3 days | Practice, payer, LOB, stay type, date range |
| Manager dashboard | 2-3 days | Stat chips, per-user table, practice roll-up |
| Branded CSS / Tailwind | 2-3 days | Port existing design tokens and component styles |
| Testing + deployment | 2-3 days | Same server, reverse proxy or separate port |

**Estimated total: 4-6 weeks**

### Scale Considerations
- Expected to serve up to 20 concurrent users
- FastAPI connection pooling handles concurrent reads
- TanStack Query on the frontend caches API responses and invalidates after writes
- `outreach_status` upsert with unique constraint handles concurrent writes safely

---

## Carry-Forward Items

| Item | Priority | Notes |
|---|---|---|
| Production TLS certificate | Medium | Replace self-signed cert — matters more with broader rollout |
| Merge V2 Streamlit to main | Low | Optional — V2 works on feature branch for testing. May skip if React migration starts soon |
| Second report from discharge query | Pending | Requirements not yet defined |

---

## Repository

**GitHub:** `rcruz-citadel/discharge-report-automation`
**Branches:** `main` (V1 production), `feature/outreach-tracking` (V2 Streamlit)
**Server:** CITADELBMI001 — `/opt/discharge_report_automation`
