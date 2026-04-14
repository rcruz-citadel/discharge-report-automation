# V3 React Migration Plan
## Discharge Report Dashboard — Citadel Health / Aylo Health

**Author:** Ronnie Cruz  
**Date:** 2026-04-13  
**Source of truth for this plan:** `streamlit_app.py` (V2, ~1606 lines) + `PROJECT_STATUS.md`

---

## Table of Contents

1. [Tech Stack](#1-tech-stack)
2. [Project Structure](#2-project-structure)
3. [Backend API Design](#3-backend-api-design)
4. [Frontend Component Architecture](#4-frontend-component-architecture)
5. [Auth Flow](#5-auth-flow)
6. [Migration Phases](#6-migration-phases)
7. [Design System](#7-design-system)
8. [Risks and Decisions](#8-risks-and-decisions)

---

## 1. Tech Stack

### Backend

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.x | API framework |
| `uvicorn[standard]` | 0.30.x | ASGI server (includes websocket/watchfiles support) |
| `sqlalchemy` | 2.0.x | ORM + connection pool (use 2.0 async-compatible style) |
| `asyncpg` | 0.29.x | Async PostgreSQL driver (pairs with SQLAlchemy async engine) |
| `pydantic` | 2.x | Request/response validation (FastAPI uses Pydantic v2 natively) |
| `pydantic-settings` | 2.x | Load config from env vars / `.env` files |
| `python-jose[cryptography]` | 3.3.x | JWT decoding for Entra ID token validation |
| `httpx` | 0.27.x | Async HTTP client for JWKS key fetching |
| `python-multipart` | 0.0.9 | Required for form data (auth callback) |
| `pytest` + `httpx` | latest | Backend tests |

**Why asyncpg over psycopg2:** At 20 concurrent users with a mix of reads and occasional writes, async I/O prevents thread blocking. asyncpg with SQLAlchemy's async engine is the right choice. Do NOT use `databases` library — SQLAlchemy async is the mature path.

**Why NOT msal Python on the backend:** MSAL Python is designed for the backend-mediated flow (authorization code exchange). For V3, auth is entirely backend-mediated — the frontend never holds tokens. The backend exchanges the auth code and issues its own session cookie. See Section 5 for the full flow. MSAL Python is not needed in V3; python-jose handles JWT validation directly.

### Frontend

| Package | Version | Purpose |
|---|---|---|
| `vite` | 5.x | Build tool |
| `react` | 18.3.x | UI framework |
| `typescript` | 5.4.x | Type safety |
| `@tanstack/react-table` | 8.x | Discharge table — virtual rows, sorting, filtering |
| `@tanstack/react-virtual` | 3.x | Row virtualization for 17k rows |
| `@tanstack/react-query` | 5.x | Server state caching, background refetch, mutation handling |
| `@msal/browser` | 3.x | Entra ID auth — SPA redirect flow |
| `@msal/react` | 2.x | React context + hooks wrapping MSAL browser |
| `tailwindcss` | 3.x | Utility CSS |
| `@radix-ui/react-*` | latest | Accessible primitives: Dialog, Select, RadioGroup, Tooltip |
| `react-router-dom` | 6.x | Routing (login route, main app route) |
| `date-fns` | 3.x | Date formatting (replaces Python strftime) |
| `clsx` | 2.x | Conditional className utility |
| `axios` | 1.7.x | HTTP client (consistent interceptors for auth headers) |

**Why Tailwind over CSS Modules or plain CSS:** The existing design uses a tight set of design tokens (2 brand colors, 4 gray variants, 3 status colors). Tailwind config maps these tokens directly. The sidebar, stat chips, and detail panel are small custom components — Tailwind utility classes keep them co-located with JSX rather than scattered in CSS files. No CSS-in-JS runtime overhead.

**Why @radix-ui over headless-ui:** Radix has zero coupling to a specific styling system and has better TypeScript types. RadioGroup is exactly what the status selector needs.

### Auth Recommendation: Backend-Mediated Auth (NOT client-side token storage)

**Recommendation: The backend handles the OAuth code exchange and issues an httpOnly session cookie. MSAL.js is used only to initiate the redirect to Microsoft and read the returned code. The frontend never stores or forwards a raw access/ID token.**

Rationale:
- Tokens in localStorage are vulnerable to XSS. With 17k rows of PHI-adjacent patient data, this is not acceptable.
- httpOnly cookies are inaccessible to JavaScript — XSS cannot steal the session.
- 20 concurrent users is small enough that server-side sessions are trivial.
- The existing MSAL Python flow in Streamlit (lines 69–74) does exactly this on the backend side already. V3 extends that pattern.

The tradeoff is slightly more backend code (a `/api/auth/callback` endpoint, a session store). That work is worth it.

### Deployment

Both processes run on CITADELBMI001 (10.1.116.2). Use nginx as a reverse proxy.

```
nginx (port 443, TLS termination)
  /        -> React static files (served by nginx directly from /opt/discharge_report_automation/frontend/dist)
  /api/*   -> FastAPI on localhost:8000
```

FastAPI runs under systemd as a separate service. The Streamlit V2 app continues on port 8502 for parallel testing.

**Nginx config sketch:**

```nginx
server {
    listen 443 ssl;
    server_name citadelbmi001.citadelhealth.local;

    root /opt/discharge_report_automation/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;  # SPA fallback
    }
}
```

This is a monorepo — one git repo, two top-level directories (`backend/` and `frontend/`).

---

## 2. Project Structure

```
discharge-report-automation/          # repo root
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory, middleware, CORS
│   │   ├── config.py                 # pydantic-settings: DATABASE_URL, AUTH_*, SESSION_SECRET
│   │   ├── database.py               # SQLAlchemy async engine + session factory
│   │   │
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # POST /api/auth/callback, POST /api/auth/logout, GET /api/auth/me
│   │   │   ├── session.py            # httpOnly cookie creation/validation
│   │   │   └── entra.py              # JWKS fetch, token validation (python-jose)
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── discharges.py         # GET /api/discharges
│   │   │   ├── outreach.py           # GET /api/outreach/{event_id}, PUT /api/outreach/{event_id}
│   │   │   ├── manager.py            # GET /api/manager/metrics, GET /api/manager/staff
│   │   │   └── meta.py               # GET /api/meta/filters (practice list, payer list, etc.)
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── db.py                 # SQLAlchemy ORM table definitions
│   │   │   └── schemas.py            # Pydantic request/response models (shared types)
│   │   │
│   │   └── services/
│   │       ├── discharge_service.py  # query v_discharge_summary, merge outreach
│   │       ├── outreach_service.py   # upsert outreach_status, activity log
│   │       └── manager_service.py    # per-user and per-practice aggregations
│   │
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_discharges.py
│   │   └── test_outreach.py
│   │
│   ├── .env.example
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── public/
│   │   └── citadel-logo-hd-transparent.png
│   │
│   ├── src/
│   │   ├── main.tsx                  # React entry point, MsalProvider wrapper
│   │   ├── App.tsx                   # Router: /login route, / protected route
│   │   │
│   │   ├── auth/
│   │   │   ├── msalConfig.ts         # PublicClientApplication config (clientId, tenantId)
│   │   │   ├── AuthProvider.tsx      # MSAL React wrapper + session cookie check
│   │   │   ├── useAuth.ts            # hook: { user, role, isManager, logout }
│   │   │   └── RequireAuth.tsx       # route guard wrapper
│   │   │
│   │   ├── api/
│   │   │   ├── client.ts             # axios instance with credentials:include
│   │   │   ├── discharges.ts         # queryFn: GET /api/discharges
│   │   │   ├── outreach.ts           # queryFn + mutationFn: GET/PUT /api/outreach/:id
│   │   │   ├── manager.ts            # queryFn: GET /api/manager/*
│   │   │   └── meta.ts               # queryFn: GET /api/meta/filters
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.tsx      # Sidebar + main content area
│   │   │   │   ├── Sidebar.tsx       # Filter controls + user info + sign out
│   │   │   │   └── AppHeader.tsx     # Logo + "Discharge Report Dashboard" banner
│   │   │   │
│   │   │   ├── ui/
│   │   │   │   ├── StatChip.tsx      # Reusable stat chip (label, value, variant)
│   │   │   │   ├── StatChipRow.tsx   # Flex row of StatChips
│   │   │   │   ├── StatusPill.tsx    # Colored dot + label badge (no_outreach / made / complete)
│   │   │   │   ├── Button.tsx        # Branded button (primary=orange, secondary)
│   │   │   │   └── LoadingSpinner.tsx
│   │   │   │
│   │   │   ├── filters/
│   │   │   │   ├── FilterSidebar.tsx # Assembles all filter controls
│   │   │   │   ├── AssigneeSelect.tsx
│   │   │   │   ├── PracticeMultiSelect.tsx
│   │   │   │   ├── PayerMultiSelect.tsx
│   │   │   │   ├── LobMultiSelect.tsx
│   │   │   │   ├── StayTypeMultiSelect.tsx
│   │   │   │   └── DateRangePicker.tsx
│   │   │   │
│   │   │   ├── discharge/
│   │   │   │   ├── DischargeTable.tsx       # TanStack Table + virtualization
│   │   │   │   ├── DischargeTableColumns.tsx # Column definitions
│   │   │   │   ├── DetailPanel.tsx           # Right-side panel for selected row
│   │   │   │   ├── OutreachStatusForm.tsx    # Radio + notes + Save button
│   │   │   │   └── OutreachLegend.tsx        # Dot legend below table
│   │   │   │
│   │   │   └── manager/
│   │   │       ├── ManagerDashboard.tsx      # Role-gated tab content
│   │   │       ├── StaffBreakdownTable.tsx   # Per-user metrics table
│   │   │       └── PracticeRollupTable.tsx   # Per-practice metrics table
│   │   │
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx         # Branded login card + Microsoft SSO button
│   │   │   └── DashboardPage.tsx     # Main app: tabs, table, detail panel
│   │   │
│   │   ├── hooks/
│   │   │   ├── useDischarges.ts      # TanStack Query wrapper for discharge data
│   │   │   ├── useOutreach.ts        # Query + mutation for outreach status
│   │   │   ├── useFilters.ts         # URL search param based filter state
│   │   │   └── useManagerMetrics.ts  # Manager dashboard queries
│   │   │
│   │   ├── types/
│   │   │   ├── discharge.ts          # DischargeRow, OutreachStatus, OutreachEntry interfaces
│   │   │   ├── auth.ts               # AppUser, UserRole types
│   │   │   └── api.ts                # API response envelope types
│   │   │
│   │   ├── lib/
│   │   │   └── utils.ts              # formatCount, formatDate, statusDisplayMap
│   │   │
│   │   └── styles/
│   │       └── globals.css           # Tailwind base + custom scrollbar styles
│   │
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── streamlit_app.py                  # V2 — keep running on port 8502 during migration
├── PROJECT_STATUS.md
├── V3_REACT_MIGRATION_PLAN.md        # this file
└── README.md
```

### Shared Types

TypeScript interfaces in `frontend/src/types/` are the source of truth for the frontend. The Pydantic schemas in `backend/app/models/schemas.py` must match them. There is no automatic schema sync (no tRPC, no OpenAPI codegen configured at the start). After the API stabilizes, add `openapi-typescript` to generate types from the FastAPI `/openapi.json` endpoint — but do not set that up on day one.

---

## 3. Backend API Design

### Environment Variables (backend/.env)

```
DATABASE_URL=postgresql+asyncpg://discharge_app_role:PASSWORD@localhost:5432/your_db
AUTH_CLIENT_ID=<entra-app-client-id>
AUTH_CLIENT_SECRET=<entra-app-client-secret>
AUTH_TENANT_ID=<entra-tenant-id>
AUTH_REDIRECT_URI=https://citadelbmi001.citadelhealth.local/auth/callback
AUTH_ALLOWED_DOMAINS=citadelhealth.com,aylohealth.com
SESSION_SECRET=<random-32-byte-hex>
SESSION_MAX_AGE_SECONDS=28800
CORS_ORIGINS=https://citadelbmi001.citadelhealth.local
```

### Connection Pooling

```python
# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,          # 10 persistent connections
    max_overflow=5,        # up to 5 extra under burst
    pool_pre_ping=True,    # detect stale connections
    pool_recycle=1800,     # recycle connections every 30 min
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

For 20 concurrent users, pool_size=10 is sufficient. Most requests are reads that complete in under 100ms. The pool will never be exhausted.

### Auth Middleware

Every protected route depends on a `get_current_user` function injected via FastAPI `Depends`. It reads the session cookie and returns the user record. If the cookie is missing or invalid, it raises HTTP 401.

```python
# backend/app/auth/session.py
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AppUser:
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await validate_session_token(session_token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    return user
```

Sessions are stored in the `discharge_app.app_session` table (new table — see Phase 1). The session token is a cryptographically random 32-byte hex string. No JWT sessions on the backend — the token is just a lookup key.

---

### Endpoint Reference

Every endpoint maps directly to a function in `streamlit_app.py`. Line numbers reference the V2 source.

---

#### `POST /api/auth/callback`

Receives the OAuth authorization code from the frontend after the Microsoft redirect.

**Request body:**
```json
{ "code": "0.AXXX...", "redirect_uri": "https://..." }
```

**What it does:**
1. Calls Microsoft token endpoint directly via httpx (same as `_exchange_code()` at line 69–74, but async and without MSAL Python).
2. Decodes the ID token with python-jose, validates claims (issuer, audience, exp, domain).
3. Looks up or creates the user in `discharge_app.app_user` to get their role.
4. Creates a session row in `discharge_app.app_session`.
5. Sets `Set-Cookie: session=TOKEN; HttpOnly; Secure; SameSite=Lax; Path=/`.

**Response:** `{ "ok": true }`  
**Error:** 401 if domain not allowed, 400 if token exchange fails.

**Maps to:** `_exchange_code()` (line 69), `check_auth()` (line 152–213), `get_user_role()` (line 842–858), `log_activity()` login event (line 199).

---

#### `POST /api/auth/logout`

Deletes the session row from `discharge_app.app_session`. Clears the cookie.

**Response:** `{ "ok": true }` with `Set-Cookie: session=; Max-Age=0`.

**Maps to:** sign-out button handler at line 1038–1041.

---

#### `GET /api/auth/me`

Returns the current user's identity. Called on app load to hydrate the React auth context.

**Response:**
```json
{
  "email": "rcruz@citadelhealth.com",
  "name": "Ronnie Cruz",
  "role": "manager"
}
```

**Requires:** valid session cookie.  
**Maps to:** `st.session_state["user_email"]`, `["user_name"]`, `["user_role"]` (lines 194–207).

---

#### `GET /api/discharges`

Returns the full merged discharge + outreach dataset. This is the heaviest endpoint — it replaces `load_discharge_data_with_status()` (line 724–735).

**Query parameters:** none — all filtering happens client-side in the React table. The backend returns the full dataset. See note below.

**Response:**
```json
{
  "records": [
    {
      "event_id": "EVT-123",
      "discharge_date": "2026-03-15",
      "patient_name": "Jane Doe",
      "insurance_member_id": "M12345",
      "practice": "Aylo Family Medicine",
      "payer_name": "BCBS",
      "lob_name": "Commercial",
      "stay_type": "Inpatient",
      "discharge_hospital": "St. Luke's",
      "length_of_stay": 3,
      "disposition": "Home",
      "dx_code": "I21.9",
      "description": "Acute MI, unspecified",
      "admit_date": "2026-03-12",
      "outreach_status": "no_outreach",
      "outreach_notes": "",
      "outreach_updated_by": null,
      "outreach_updated_at": null
    }
  ],
  "total": 17482,
  "loaded_at": "2026-04-13T14:23:00Z"
}
```

**Why return everything client-side:** 17k rows serialized as JSON is approximately 8–12 MB uncompressed. With gzip (nginx enables this by default), that drops to 1–2 MB. On an internal LAN this loads in under a second. Client-side filtering is then instant. This mirrors the Streamlit approach (lines 703–735 load and cache all data). Server-side pagination would require moving filter logic to the backend — unnecessary complexity for this scale. Revisit if the dataset exceeds 100k rows.

**Caching:** FastAPI does not cache this in memory. TanStack Query on the frontend caches the response for `staleTime: 5 * 60 * 1000` (5 minutes, matching the Streamlit `ttl=300`). After a successful outreach upsert, the frontend calls `queryClient.invalidateQueries(['discharges'])`, which triggers a background refetch.

**SQL query:**
```sql
-- backend/app/services/discharge_service.py
SELECT
    d.*,
    o.status         AS outreach_status,
    o.notes          AS outreach_notes,
    o.updated_by     AS outreach_updated_by,
    o.updated_at     AS outreach_updated_at
FROM v_discharge_summary d
LEFT JOIN discharge_app.outreach_status o
    ON o.event_id = d.event_id
    AND o.discharge_date = d.discharge_date
ORDER BY d.discharge_date DESC
```

This is a server-side join replacing the Python-side `_merge_outreach()` function (lines 1090–1120). The DB does the merge — no pandas needed.

**Maps to:** `_load_raw_discharge_data()` (line 703), `load_outreach_statuses()` (line 738), `_merge_outreach()` (line 1090), `load_discharge_data_with_status()` (line 724).

---

#### `GET /api/outreach/{event_id}`

Returns the current outreach record for a single event. Used when the detail panel opens to get fresh data (handles the case where another user updated the record since the last full load).

**Path param:** `event_id` (string)  
**Query param:** `discharge_date` (date, YYYY-MM-DD, required — composite key)

**Response:**
```json
{
  "event_id": "EVT-123",
  "discharge_date": "2026-03-15",
  "status": "outreach_made",
  "notes": "Left voicemail",
  "updated_by": "ssmith@citadelhealth.com",
  "updated_at": "2026-04-01T09:15:00Z"
}
```

**Returns 404 if no outreach record exists** (no record means status is `no_outreach`).

**Maps to:** `load_outreach_statuses()` dict lookup at line 1165–1169.

---

#### `PUT /api/outreach/{event_id}`

Upserts the outreach status for one discharge event. This is the core write operation.

**Path param:** `event_id`  
**Request body:**
```json
{
  "discharge_date": "2026-03-15",
  "status": "outreach_made",
  "notes": "Left voicemail at 9am"
}
```

**What it does:**
1. Runs the upsert SQL (same as `upsert_outreach_status()` lines 641–697).
2. Writes to `discharge_app.user_activity_log` with action `outreach_update` and detail JSON (same as lines 682–693).
3. Returns the updated record.

**Response:**
```json
{
  "event_id": "EVT-123",
  "discharge_date": "2026-03-15",
  "status": "outreach_made",
  "notes": "Left voicemail",
  "updated_by": "rcruz@citadelhealth.com",
  "updated_at": "2026-04-13T14:30:00Z"
}
```

**SQL:**
```sql
INSERT INTO discharge_app.outreach_status
    (event_id, discharge_date, status, updated_by, updated_at, notes)
VALUES
    (:event_id, :discharge_date, :status, :updated_by, now(), :notes)
ON CONFLICT (event_id, discharge_date) DO UPDATE
    SET status     = EXCLUDED.status,
        updated_by = EXCLUDED.updated_by,
        updated_at = now(),
        notes      = EXCLUDED.notes
RETURNING *;
```

**Maps to:** `upsert_outreach_status()` lines 641–697.

---

#### `GET /api/meta/filters`

Returns all distinct values for sidebar filter dropdowns. Called once on app load and cached for 5 minutes.

**Response:**
```json
{
  "practices": ["Aylo Family Medicine", "Citadel Primary Care", ...],
  "payers": ["BCBS", "Aetna", ...],
  "lob_names": ["Commercial", "Medicare", ...],
  "stay_types": ["Inpatient", "Observation", ...],
  "assignees": [
    { "name": "Sarah Smith", "practices": ["Aylo Family Medicine", "Citadel West"] },
    ...
  ],
  "discharge_date_min": "2024-01-01",
  "discharge_date_max": "2026-04-13"
}
```

**SQL:** Pulls distinct values from `v_discharge_summary` plus the assignee list from `discharge_app.app_user`.

**Maps to:** `render_sidebar_filters()` lines 956–1043 (options derived from df), `load_practice_assignments()` lines 771–789.

---

#### `GET /api/manager/metrics`

Returns the manager dashboard aggregations. Only accessible to users with `role = 'manager'`.

**Response:**
```json
{
  "summary": {
    "total": 17482,
    "no_outreach": 14000,
    "outreach_made": 2100,
    "outreach_complete": 1382,
    "pct_complete": 7.9
  },
  "staff_breakdown": [
    {
      "user_email": "ssmith@citadelhealth.com",
      "display_name": "Sarah Smith",
      "practice_count": 3,
      "total": 820,
      "no_outreach": 600,
      "outreach_made": 150,
      "outreach_complete": 70,
      "pct_complete": 8.5,
      "last_login": "2026-04-12",
      "last_activity": "2026-04-12"
    }
  ],
  "practice_rollup": [
    {
      "practice": "Aylo Family Medicine",
      "total": 1200,
      "no_outreach": 900,
      "outreach_made": 200,
      "outreach_complete": 100,
      "pct_complete": 8.3
    }
  ]
}
```

**Note:** This endpoint does the aggregation in SQL/Python on the backend, not in the browser. The current Streamlit code (lines 1384–1544) loops over staff users in Python and filters the already-loaded DataFrame. Move this to a proper SQL aggregation query in `manager_service.py` — it will be faster and cleaner.

**SQL sketch for staff_breakdown:**
```sql
SELECT
    u.user_email,
    u.display_name,
    array_length(u.practices, 1)                            AS practice_count,
    COUNT(d.event_id)                                       AS total,
    COUNT(*) FILTER (WHERE COALESCE(o.status,'no_outreach')='no_outreach')  AS no_outreach,
    COUNT(*) FILTER (WHERE o.status='outreach_made')        AS outreach_made,
    COUNT(*) FILTER (WHERE o.status='outreach_complete')    AS outreach_complete,
    MAX(al_login.created_at)                                AS last_login,
    MAX(al_any.created_at)                                  AS last_activity
FROM discharge_app.app_user u
LEFT JOIN v_discharge_summary d ON d.practice = ANY(u.practices)
LEFT JOIN discharge_app.outreach_status o
    ON o.event_id = d.event_id AND o.discharge_date = d.discharge_date
LEFT JOIN discharge_app.user_activity_log al_login
    ON al_login.user_email = u.user_email AND al_login.action = 'login'
LEFT JOIN discharge_app.user_activity_log al_any
    ON al_any.user_email = u.user_email
WHERE u.is_active = TRUE AND u.role = 'staff'
GROUP BY u.user_email, u.display_name, u.practices
ORDER BY u.display_name;
```

**Optional query params:** `date_from`, `date_to`, `practice` (to support server-side filtering for the manager view — implement this in Phase 3 if needed).

**Auth guard:** Middleware checks `current_user.role == 'manager'` and returns 403 otherwise.

**Maps to:** `render_manager_dashboard()` lines 1373–1544, `load_all_staff_users()` lines 793–813, `load_user_last_activity()` lines 816–838.

---

#### New table: `discharge_app.app_session`

Add this table in a migration script before Phase 1 goes live.

```sql
CREATE TABLE discharge_app.app_session (
    id           BIGSERIAL PRIMARY KEY,
    token        TEXT NOT NULL UNIQUE,
    user_email   TEXT NOT NULL,
    user_name    TEXT NOT NULL,
    user_role    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON discharge_app.app_session (token);
CREATE INDEX ON discharge_app.app_session (expires_at);

-- Cleanup job: add a pg_cron schedule or run from the app on startup
-- DELETE FROM discharge_app.app_session WHERE expires_at < now();
```

---

## 4. Frontend Component Architecture

### Component Tree

```
App.tsx
└── MsalProvider (msalConfig)
    └── AuthProvider (session cookie check + /api/auth/me)
        ├── LoginPage          (route: /login)
        └── RequireAuth
            └── DashboardPage  (route: /)
                └── AppShell
                    ├── AppHeader
                    ├── FilterSidebar
                    │   ├── AssigneeSelect
                    │   ├── PracticeMultiSelect
                    │   ├── PayerMultiSelect
                    │   ├── LobMultiSelect
                    │   ├── StayTypeMultiSelect
                    │   └── DateRangePicker
                    └── MainContent
                        ├── StatChipRow [4 chips: Total, Patients, Practices, Hospitals]
                        ├── TabStrip [Recent | 6 Months | All | Manager (role-gated)]
                        └── TabPanel (active tab)
                            ├── OutreachLegend
                            ├── DischargeTable
                            │   └── DischargeTableColumns
                            ├── DetailPanel (conditionally rendered when row selected)
                            │   └── OutreachStatusForm
                            └── ExportButton
                        (Manager tab renders ManagerDashboard instead of table+panel)
                            └── ManagerDashboard
                                ├── StatChipRow [5 chips: Total, No Outreach, Made, Complete, % Done]
                                ├── StaffBreakdownTable
                                └── PracticeRollupTable
```

### State Management Strategy

**Server state (TanStack Query):**

```typescript
// hooks/useDischarges.ts
export function useDischarges() {
  return useQuery({
    queryKey: ['discharges'],
    queryFn: () => api.get('/api/discharges').then(r => r.data),
    staleTime: 5 * 60 * 1000,   // 5 minutes — match Streamlit ttl=300
    gcTime: 10 * 60 * 1000,
  });
}

// hooks/useOutreach.ts
export function useUpsertOutreach() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OutreachUpsertPayload) =>
      api.put(`/api/outreach/${payload.eventId}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discharges'] });
    },
  });
}
```

**UI state (React useState / URL search params):**

| State | Where | Why |
|---|---|---|
| Active tab | `useState` in DashboardPage | No reason to put tabs in the URL |
| Selected row | `useState` in DashboardPage | Local interaction state |
| Filter values | URL search params via `useFilters` hook | Shareable links, survives page refresh |
| Detail panel open | Derived from selectedRow !== null | Not independent state |

### Filter State in URL

```typescript
// hooks/useFilters.ts
export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters: FilterState = {
    assignee: searchParams.get('assignee') ?? 'All',
    practices: searchParams.getAll('practice'),
    payers: searchParams.getAll('payer'),
    lobNames: searchParams.getAll('lob'),
    stayTypes: searchParams.getAll('stayType'),
    dateFrom: searchParams.get('dateFrom') ?? null,
    dateTo: searchParams.get('dateTo') ?? null,
  };

  function setFilter<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    const next = new URLSearchParams(searchParams);
    // update param(s) for key
    setSearchParams(next, { replace: true });
  }

  return { filters, setFilter, clearAll };
}
```

Client-side filtering runs inside a `useMemo` in `DashboardPage.tsx`:

```typescript
const filteredRows = useMemo(() => {
  if (!discharges) return [];
  return discharges.records.filter(row => {
    if (filters.practices.length > 0 && !filters.practices.includes(row.practice)) return false;
    if (filters.payers.length > 0 && !filters.payers.includes(row.payer_name)) return false;
    // ... etc
    return true;
  });
}, [discharges, filters]);
```

This runs in microseconds for 17k rows in the browser. No debouncing needed.

### Table + Detail Panel Interaction

The Streamlit app renders the detail panel below the table. In React, use a **split layout**: table on the left, detail panel as a right-side panel that slides in when a row is selected. This is the standard pattern for this kind of workflow and eliminates the jarring full-page push of a below-table panel.

```
┌─────────────────────────────────┬────────────────────────────┐
│  DischargeTable (flex-grow)     │  DetailPanel (w-96, fixed) │
│  (shrinks when panel opens)     │  Patient Name — Date       │
│                                 │  Practice / Payer / Hosp   │
│                                 │  [Status radio]            │
│                                 │  [Notes textarea]          │
│                                 │  [Save] [Cancel]           │
└─────────────────────────────────┴────────────────────────────┘
```

Implementation in `DashboardPage.tsx`:

```tsx
const [selectedRow, setSelectedRow] = useState<DischargeRow | null>(null);

return (
  <div className="flex gap-4 h-full">
    <div className={selectedRow ? 'flex-1 min-w-0' : 'w-full'}>
      <DischargeTable
        data={filteredRows}
        selectedRowId={selectedRow?.event_id}
        onRowClick={row => setSelectedRow(row === selectedRow ? null : row)}
      />
    </div>
    {selectedRow && (
      <div className="w-96 shrink-0">
        <DetailPanel
          row={selectedRow}
          onClose={() => setSelectedRow(null)}
        />
      </div>
    )}
  </div>
);
```

Clicking the same row again (or clicking the X in the panel) closes it.

### Table Virtualization

TanStack Virtual is required for 17k rows. Without it the browser will render 17k DOM nodes and the tab will be sluggish.

```typescript
// DischargeTable.tsx (sketch)
import { useVirtualizer } from '@tanstack/react-virtual';

const rowVirtualizer = useVirtualizer({
  count: table.getRowModel().rows.length,
  getScrollElement: () => tableContainerRef.current,
  estimateSize: () => 40,
  overscan: 10,
});
```

Only the ~20 visible rows are in the DOM at any time. Scrolling through 17k rows is smooth.

### Role-Gating for Manager Tab

```tsx
// In DashboardPage.tsx
const { isManager } = useAuth();

const tabs = ['Recent', 'Last 6 Months', 'All Discharges', ...(isManager ? ['Manager'] : [])];
```

The Manager tab is excluded from the tab list entirely for non-managers — not just hidden. The `/api/manager/metrics` endpoint also enforces role on the backend. Defense in depth.

---

## 5. Auth Flow

### Decision: Backend-Mediated Auth with httpOnly Session Cookie

The frontend uses MSAL.js to **initiate** the Microsoft redirect and to **receive** the authorization code from the callback URL. It does NOT call `acquireTokenSilent` or store tokens. The code is immediately POSTed to `/api/auth/callback`, which exchanges it for tokens, validates the ID token, and sets an httpOnly cookie.

### Step-by-Step Flow

```
1. User loads https://citadelbmi001.citadelhealth.local/
2. React mounts, AuthProvider calls GET /api/auth/me with credentials:include
3. No session cookie exists -> 401 returned
4. AuthProvider redirects to /login
5. LoginPage renders the branded card (same design as Streamlit _render_login_page())
6. User clicks "Sign in with Microsoft"
7. MSAL.js calls loginRedirect() — browser navigates to:
      https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize
      ?client_id=...&redirect_uri=.../auth/callback&scope=openid profile email&response_type=code
8. User authenticates on Microsoft's UI
9. Microsoft redirects to:
      https://citadelbmi001.citadelhealth.local/auth/callback?code=0.AXxx...
10. React Router renders the /auth/callback route
11. CallbackPage extracts the code from the URL
12. CallbackPage POST /api/auth/callback { code: "...", redirect_uri: "..." }
13. FastAPI backend exchanges code with Microsoft token endpoint (httpx)
14. Backend decodes and validates ID token (python-jose):
      - Verify signature against Microsoft JWKS
      - Verify iss = https://login.microsoftonline.com/{tenant_id}/v2.0
      - Verify aud = {client_id}
      - Verify exp is in the future
      - Check email domain against AUTH_ALLOWED_DOMAINS
15. Backend looks up user in discharge_app.app_user
16. Backend creates session in discharge_app.app_session (32-byte random token, 8h TTL)
17. Backend returns 200 { ok: true }
    Set-Cookie: session=TOKEN; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=28800
18. Frontend receives 200, navigates to /
19. AuthProvider re-calls GET /api/auth/me, session cookie is attached automatically
20. /api/auth/me returns { email, name, role }
21. AuthProvider stores user in React context
22. DashboardPage loads, calls GET /api/discharges (cookie attached automatically)
```

### Token Storage Decision

| Option | Security | Complexity |
|---|---|---|
| localStorage (tokens) | Vulnerable to XSS | Simple |
| sessionStorage (tokens) | Vulnerable to XSS | Simple |
| httpOnly cookie (session ID) | XSS cannot read it | Medium (CSRF must be handled) |

**Use httpOnly cookies.** For CSRF protection, since `SameSite=Lax` is set, cross-site POST requests from other origins are blocked by the browser. Lax is sufficient for this internal app. If Strict causes issues with the OAuth redirect (it can, because the redirect from Microsoft is a cross-site navigation), stick with Lax. Do not use `SameSite=None` without a specific reason.

### How the Frontend Sends Credentials

```typescript
// api/client.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,   // sends the session cookie on every request automatically
});

// Global 401 handler — redirect to login when session expires
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

No Authorization header. No token in localStorage. The cookie does the work.

### How the Backend Validates Requests

```python
# auth/session.py
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(401)

    result = await db.execute(
        select(AppSession)
        .where(AppSession.token == token)
        .where(AppSession.expires_at > func.now())
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(401, detail="Session expired")

    # Touch last_seen_at (fire-and-forget, don't await)
    asyncio.create_task(touch_session(session.id, db))

    return AppUser(
        email=session.user_email,
        name=session.user_name,
        role=session.user_role,
    )
```

This runs on every API request. It's a single indexed primary-key lookup — microseconds.

### Session Management for 20 Concurrent Users

- Sessions expire after 8 hours (`SESSION_MAX_AGE_SECONDS=28800`). Users sign in once at the start of their shift.
- Session rows are cleaned up periodically. Add a startup event in `main.py`:

```python
@app.on_event("startup")
async def cleanup_expired_sessions():
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("DELETE FROM discharge_app.app_session WHERE expires_at < now()")
        )
        await db.commit()
```

- 20 concurrent users = 20 session rows max. Negligible storage.
- No Redis, no in-memory session store needed at this scale.

### MSAL.js Configuration

```typescript
// auth/msalConfig.ts
import { Configuration, LogLevel } from '@azure/msal-browser';

export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AUTH_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AUTH_TENANT_ID}`,
    redirectUri: `${window.location.origin}/auth/callback`,
    postLogoutRedirectUri: `${window.location.origin}/login`,
    navigateToLoginRequestUrl: false,
  },
  cache: {
    cacheLocation: 'sessionStorage',   // MSAL uses this for its own state, not tokens we keep
    storeAuthStateInCookie: false,
  },
};

export const loginRequest = {
  scopes: ['openid', 'profile', 'email'],
};
```

The MSAL cache in sessionStorage only stores the code verifier and state for PKCE. The access token itself never lives in the browser after the backend exchanges the code.

---

## 6. Migration Phases

### Phase 0 — Database Prep (1 day, do first, no code risk)

**What:**
1. Create `discharge_app.app_session` table (SQL in Section 3).
2. Verify `v_discharge_summary` returns all columns the frontend needs. Add any missing columns (e.g., `insurance_member_id`).
3. Add `discharge_app_role` grants for the new `app_session` table.

**When done:** DB is ready for the backend. Streamlit app is unaffected.

**Deliverable:** Migration SQL script committed to `backend/migrations/001_add_app_session.sql`.

---

### Phase 1 — FastAPI Backend (1–2 weeks)

**Dependencies:** Phase 0 complete.

**Build order:**
1. Scaffold `backend/` directory, install deps, create `main.py`, `config.py`, `database.py`.
2. Implement `GET /api/discharges` — this is the most important endpoint. Test it with curl/Postman against the live DB.
3. Implement `PUT /api/outreach/{event_id}` — copy the upsert SQL from Streamlit line 657–677.
4. Implement `GET /api/meta/filters`.
5. Implement auth: `POST /api/auth/callback`, `GET /api/auth/me`, `POST /api/auth/logout`.
6. Implement `GET /api/manager/metrics`.
7. Wire up `get_current_user` dependency on all protected routes.
8. Write tests for the three core endpoints.

**Testing during Phase 1:** Use curl or Bruno (REST client) to hit the API directly. No frontend needed yet. Test against the Streamlit V2 DB.

**When done:** Complete backend API, tested against real data, running on port 8000 on CITADELBMI001.

**Systemd service:**
```ini
# /etc/systemd/system/discharge-api.service
[Unit]
Description=Discharge Report FastAPI Backend
After=network.target

[Service]
User=discharge_svc
WorkingDirectory=/opt/discharge_report_automation/backend
EnvironmentFile=/opt/discharge_report_automation/backend/.env
ExecStart=/opt/discharge_report_automation/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Two workers is sufficient for 20 users. Each worker handles requests concurrently via async I/O.

---

### Phase 2 — React App Scaffold + Auth (3–4 days)

**Dependencies:** Phase 1 auth endpoints working.

**Build order:**
1. `npm create vite@latest frontend -- --template react-ts`
2. Install all packages from Section 1.
3. Configure Tailwind with the Citadel design tokens (Section 7).
4. Build `LoginPage.tsx` with the branded card (port from Streamlit lines 77–149).
5. Build `AuthProvider.tsx` and the MSAL.js login redirect flow.
6. Build the `/auth/callback` route handler that POSTs the code to the backend.
7. Build `RequireAuth.tsx` guard.
8. Build `AppShell.tsx` (empty sidebar + content area).
9. Verify: click "Sign in with Microsoft" -> redirect -> callback -> session cookie set -> `/api/auth/me` returns user.

**When done:** Login works end-to-end. Authenticated users land on a blank dashboard. Unauthenticated users are redirected to the login page. No real data yet.

---

### Phase 3 — Discharge Table + Detail Panel (1 week)

**Dependencies:** Phase 2 complete, Phase 1 `GET /api/discharges` working.

**Build order:**
1. Implement `useDischarges` hook (TanStack Query).
2. Implement `useFilters` hook (URL search params).
3. Build `DischargeTable.tsx` with TanStack Table + TanStack Virtual. Start with column definitions matching the Streamlit display_cols (line 1319–1323).
4. Build `FilterSidebar.tsx` with all controls (port options logic from lines 960–1043).
5. Build `StatChipRow.tsx` and the 4 main stats (port from lines 1062–1074).
6. Build tab strip: Recent / Last 6 Months / All (client-side date slicing — same logic as lines 1572–1591).
7. Build `DetailPanel.tsx` with the 3-column info grid (port from lines 1178–1215).
8. Build `OutreachStatusForm.tsx` with radio + textarea + Save (port from lines 1230–1289).
9. Implement `useUpsertOutreach` mutation + invalidation.
10. CSV export (browser-side, no API needed):

```typescript
function exportToCSV(rows: DischargeRow[]) {
  const columns = ['patient_name', 'discharge_date', 'practice', ...];
  const header = columns.join(',');
  const body = rows.map(r => columns.map(c => `"${r[c] ?? ''}"`).join(',')).join('\n');
  const blob = new Blob([header + '\n' + body], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `discharge_report_${format(new Date(), 'yyyyMMdd_HHmmss')}.csv`;
  a.click();
}
```

**When done:** The complete staff workflow is functional. Users can log in, filter, browse all three tabs, click rows, update outreach status. This is the MVP for staff — everything managers need to track is here.

---

### Phase 4 — Manager Dashboard (3 days)

**Dependencies:** Phase 3 complete, Phase 1 `GET /api/manager/metrics` working.

**Build order:**
1. Implement `useManagerMetrics` hook.
2. Build `ManagerDashboard.tsx` with the 5-chip summary row.
3. Build `StaffBreakdownTable.tsx` (port columns from lines 1458–1478).
4. Build `PracticeRollupTable.tsx` (port columns from lines 1528–1544).
5. Wire up the role-gated 4th tab in `DashboardPage.tsx`.

**When done:** Complete feature parity with Streamlit V2.

---

### Phase 5 — Deployment + Cutover (2–3 days)

**Dependencies:** Phase 4 complete and tested.

**Build order:**
1. `npm run build` in `frontend/` — generates `dist/`.
2. Copy `dist/` to `/opt/discharge_report_automation/frontend/dist/`.
3. Configure nginx as described in Section 1 (add the React site on port 443).
4. Run React app alongside Streamlit for at least 2–3 days of parallel testing.
5. Announce cutover date to staff and managers.
6. On cutover day: stop Streamlit V2 service (port 8502), update nginx to serve React as primary.
7. Keep Streamlit on port 8501 (main branch, V1) as emergency rollback for 2 weeks.

**What running parallel means:** Both apps use the same database. Outreach updates made in either app are immediately visible in the other (both query the same tables). Staff can test the new React app without risk.

---

### Phase Timeline Summary

| Phase | What | Duration | Start |
|---|---|---|---|
| 0 | DB migration | 1 day | Week 1 Day 1 |
| 1 | FastAPI backend | 1–2 weeks | Week 1 Day 2 |
| 2 | React scaffold + auth | 3–4 days | After Phase 1 auth endpoints |
| 3 | Table + detail panel | 1 week | After Phase 2 |
| 4 | Manager dashboard | 3 days | After Phase 3 |
| 5 | Deployment + cutover | 2–3 days | After Phase 4 |
| **Total** | | **4–6 weeks** | |

---

## 7. Design System

### Design Tokens (Tailwind Config)

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Primary brand colors (from Streamlit CSS, lines 300–598)
        navy: {
          DEFAULT: '#132e45',
          light:   '#1b4459',
          dark:    '#0e2233',
        },
        orange: {
          DEFAULT: '#e07b2a',
          hover:   '#c96920',
        },
        // Background
        page:    '#f0f2f5',
        surface: '#ffffff',
        // Text
        'text-primary':   '#132e45',
        'text-secondary': '#556e81',
        'text-muted':     '#7e96a6',
        'text-light':     '#a8c4d8',
        // Borders
        border:       '#d0dae3',
        'border-light': '#e8ecf0',
        // Status colors
        status: {
          none:           '#cbd5e0',
          'none-bg':      '#edf2f7',
          'none-text':    '#718096',
          made:           '#e07b2a',
          'made-bg':      '#fef3e2',
          'made-text':    '#c05621',
          complete:       '#38a169',
          'complete-bg':  '#e6ffed',
          'complete-text': '#22753a',
        },
      },
      borderRadius: {
        chip:  '10px',
        panel: '12px',
        card:  '14px',
        pill:  '20px',
      },
      boxShadow: {
        chip:  '0 2px 6px rgba(19,46,69,0.06)',
        panel: '0 4px 18px rgba(19,46,69,0.10)',
        card:  '0 4px 18px rgba(19,46,69,0.18)',
      },
    },
  },
} satisfies Config;
```

### Components to Build

Each component maps directly to Streamlit CSS classes defined in lines 300–598.

#### StatChip

```tsx
// components/ui/StatChip.tsx
interface StatChipProps {
  label: string;
  value: string | number;
  variant?: 'default' | 'orange' | 'green' | 'gray';
}

// Tailwind classes per variant:
// default:  border-l-navy border-l-4
// orange:   border-l-orange border-l-4, value color text-orange
// green:    border-l-[#38a169] border-l-4, value color text-[#22753a]
// gray:     border-l-[#a0aec0] border-l-4, value color text-[#718096]
```

#### StatusPill

```tsx
// components/ui/StatusPill.tsx
// Three variants: no_outreach, outreach_made, outreach_complete
// Renders the colored dot + label badge from lines 1123–1148
```

#### OutreachStatusForm (Radio)

Use `@radix-ui/react-radio-group` for the status selector. Three options: No Outreach / Outreach Made / Outreach Complete. Style the radio items to match the Streamlit `.stRadio > div > label` styles (lines 521–540):
- Unselected: white background, `#d0dae3` border, rounded-lg.
- Selected: `#132e45` background, white text.

#### DetailPanel

Three-column grid matching `.detail-grid` (lines 479–483). Fields: Practice, Payer, Hospital (row 1), Diagnosis, LOS, Disposition (row 2). Panel header is the navy gradient. Panel border is `1.5px solid #132e45`.

#### Sidebar

Background `bg-navy`. All label text `text-text-light`. Section headings `text-white` with a bottom border `border-navy-light`. Multi-select tags `bg-orange`. Dropdown input text must be dark (this was the bug documented in the MEMORY.md sidebar styling note) — achieved by styling the Radix Select trigger and item with explicit `text-gray-900`.

#### Manager Tables

Port `.manager-table` styles (lines 567–598) to a `<table>` component:
- `thead th`: `bg-navy text-white` with uppercase tiny text.
- `tbody td`: `border-b border-border-light text-text-primary`.
- Row hover: `hover:bg-page`.
- No external table library needed for the manager view — these are static display tables, not interactive.

#### App Header Banner

Port the navy gradient card from `render_header()` (lines 928–953):

```tsx
// components/layout/AppHeader.tsx
// div with: bg-gradient-to-br from-navy to-navy-light
// orange right-side accent bar: absolute right-0 top-0 bottom-0 w-[5px] bg-gradient-to-b from-orange to-orange-hover
// title text: text-white text-[1.65rem] font-extrabold
// subtitle text: text-text-light text-sm
```

#### Login Page

Port `_render_login_page()` (lines 77–149):
- Centered card, navy gradient background, orange right accent bar.
- Logo above the card.
- "Sign in with Microsoft" button: `bg-orange text-white font-bold rounded-[9px]`.
- Domain restriction note below the button.

---

## 8. Risks and Decisions

### Decisions to Make Before Starting

**D1: App Registration Redirect URI**  
The Entra ID app registration currently has `http://localhost:8501` as the redirect URI (line 50). Before Phase 2, add `https://citadelbmi001.citadelhealth.local/auth/callback` to the app registration in Azure Portal. Do this now — you need it before writing a single line of auth code.

**D2: TLS Certificate**  
`SameSite=Lax` cookies on an HTTPS site work correctly. On HTTP they may not be sent. The current server has a self-signed cert (noted in PROJECT_STATUS.md). Self-signed is fine for internal use as long as browsers trust it. Confirm that all staff machines have the cert installed or that an internal CA is used. If they don't, MSAL.js's redirect flow may fail silently because the browser blocks the callback. Sort this before Phase 2.

**D3: Vite Dev Proxy During Development**  
During local development, the React dev server runs on port 5173 and the FastAPI server on port 8000. Configure Vite's proxy to forward `/api/*` requests to `localhost:8000`:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
```

Also add `http://localhost:5173/auth/callback` to the Entra ID app registration for local dev. Remove it when going to production.

**D4: `v_discharge_summary` Column Names**  
The FastAPI endpoint returns snake_case JSON (e.g., `patient_name`, `discharge_date`). The view currently returns snake_case column names (confirmed in `_load_raw_discharge_data()` line 711 which applies `.str.replace("_", " ").str.title()` transformation). The backend should return raw snake_case — do NOT apply the title-case transformation. Define the column names explicitly in the Pydantic schema so there is no ambiguity.

**D5: `insurance_member_id` column**  
The Streamlit app references `Insurance Member Id` at line 1064. Verify this column exists in `v_discharge_summary`. The recent commit `ffbc926` ("Switch patient_id to insurance_member_id") suggests it was just added — confirm and include in the Pydantic response schema.

---

### Risk: Entra ID Auth is Harder Than Expected

**Scenario:** The OAuth redirect callback fails, MSAL.js throws errors, token validation fails.

**Mitigation plan:**
1. Build Phase 1 (backend) with auth stubbed — `get_current_user` always returns a hardcoded test user. This lets you develop and test the entire data API and frontend without touching auth.
2. Implement auth last, in isolation, with a dedicated test environment.
3. If MSAL.js redirect flow is problematic (it can be fussy with internal hostnames), fall back to a simpler approach: build a `/login` page that just POSTs email/password against `discharge_app.app_user`. This bypasses SSO entirely but lets the app ship. SSO can be layered on later.
4. If the backend token validation (python-jose + JWKS) is difficult to debug, use the Microsoft Graph API (`GET https://graph.microsoft.com/v1.0/me` with the access token) to validate identity. Simpler to implement, slightly more latency.

---

### Risk: 17k Rows JSON Payload is Too Slow

**Scenario:** The `/api/discharges` response takes more than 2 seconds over the internal network.

**Mitigation:**
- Enable gzip in nginx (it's off by default): `gzip on; gzip_types application/json;`
- Test on the actual server before assuming it's slow. 17k rows at ~500 bytes each = ~8.5MB uncompressed, ~1.5MB gzipped. At 100Mbps LAN this is under 200ms.
- If it is slow: add server-side date filtering (`date_from`, `date_to` query params on `/api/discharges`). Default to the last 6 months. Add a "Load all" button. The Streamlit V2 app already defaults to showing "Recent Discharges (Last 14 Days)" first — users rarely need all 17k rows at once.

---

### Risk: Concurrent Writes Conflict

**Scenario:** Two staff users update outreach status for the same patient simultaneously.

**Mitigation:** Already handled. The `ON CONFLICT (event_id, discharge_date) DO UPDATE` upsert is atomic at the DB level (lines 657–677, carried to the backend unchanged). The last write wins. No optimistic locking needed at this scale (20 users, low probability of simultaneous edit on the same row).

---

### Risk: Session Cookie Not Sent in MSAL Redirect

**Scenario:** Microsoft redirects back to `/auth/callback` with the code, but because this is a cross-origin navigation from `login.microsoftonline.com`, some browser configurations don't attach `SameSite=Lax` cookies on the GET request to the callback URL.

**Clarification:** The session cookie is not set until AFTER the POST to `/api/auth/callback` succeeds. The GET to `/auth/callback` from Microsoft is handled entirely by the React app (no cookie needed at that point — React just reads the `?code=` param and POSTs it). This risk does not apply.

---

### Risk: Staff Have Trouble with the Redirect (Internal HTTPS)

**Scenario:** The internal server hostname is not in DNS or the TLS cert is rejected, so the Microsoft redirect after login goes nowhere.

**Mitigation:** Use the IP address as the redirect URI for initial testing: `https://10.1.116.2/auth/callback`. Add it to the Entra ID app registration. Not ideal for production (IP-based certs are unusual) but removes the DNS dependency during development. Switch to the hostname-based URI once DNS resolves correctly.

---

### What to Do If Streamlit Can't Be Shut Down Immediately

V2 Streamlit on port 8502 and V3 React on port 443 share the same database. They can run indefinitely in parallel. There is no "must cut over by date X" constraint. The cutover happens when you and the users are confident in V3. Keep V2 running for at least 2 weeks post-cutover as a safety net.

---

## Quick-Start Checklist

Before writing any code:

- [ ] Add `https://citadelbmi001.citadelhealth.local/auth/callback` to the Entra ID app registration
- [ ] Add `http://localhost:5173/auth/callback` to the Entra ID app registration (for local dev)
- [ ] Run `CREATE TABLE discharge_app.app_session ...` migration on the DMZ PostgreSQL server
- [ ] Confirm `v_discharge_summary` has `insurance_member_id` column
- [ ] Confirm TLS cert on CITADELBMI001 is trusted by staff machines
- [ ] Note the existing `AUTH_CLIENT_ID`, `AUTH_CLIENT_SECRET`, `AUTH_TENANT_ID` values from the current Streamlit secrets (you'll need them for the backend `.env`)
- [ ] Install nginx on CITADELBMI001 if not already present (`sudo apt install nginx`)
