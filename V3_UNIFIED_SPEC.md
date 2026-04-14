# V3 Unified Specification — Discharge Report Dashboard
## Citadel Health / Aylo Health — React + FastAPI Migration

**Author:** Ronnie Cruz
**Date:** 2026-04-13
**Source of truth:** `streamlit_app.py` (V2, ~1606 lines) + `PROJECT_STATUS.md`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Agent 1: Database](#2-agent-1-database)
3. [Agent 2: Backend (FastAPI)](#3-agent-2-backend-fastapi)
4. [Agent 3: Frontend (React)](#4-agent-3-frontend-react)
5. [Agent 4: UI / Design System](#5-agent-4-ui--design-system)
6. [Agent 5: DevOps / Deployment](#6-agent-5-devops--deployment)
7. [Phase Timeline](#7-phase-timeline)
8. [Pre-Flight Checklist](#8-pre-flight-checklist)
9. [Risks and Mitigations](#9-risks-and-mitigations)

---

## 1. Overview

### What We're Building

Migrate the Streamlit V2 discharge report dashboard to a React + FastAPI architecture. The app tracks ~17k discharge records, lets staff update outreach status, and gives managers an analytics dashboard. ~20 concurrent users on an internal LAN.

### Architecture at a Glance

```
nginx (port 443, TLS)
  /        -> React static files (from /opt/discharge_report_automation/frontend/dist)
  /api/*   -> FastAPI on localhost:8000

Both processes run on CITADELBMI001 (10.1.116.2).
Streamlit V2 stays on port 8502 during parallel testing.
```

### Monorepo Structure

```
discharge-report-automation/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory, middleware, CORS
│   │   ├── config.py                 # pydantic-settings: DATABASE_URL, AUTH_*, SESSION_SECRET
│   │   ├── database.py               # SQLAlchemy async engine + session factory
│   │   ├── auth/
│   │   │   ├── router.py             # POST /api/auth/callback, POST /api/auth/logout, GET /api/auth/me
│   │   │   ├── session.py            # httpOnly cookie creation/validation
│   │   │   └── entra.py              # JWKS fetch, token validation (python-jose)
│   │   ├── routers/
│   │   │   ├── discharges.py         # GET /api/discharges
│   │   │   ├── outreach.py           # GET/PUT /api/outreach/{event_id}
│   │   │   ├── manager.py            # GET /api/manager/metrics
│   │   │   └── meta.py               # GET /api/meta/filters
│   │   ├── models/
│   │   │   ├── db.py                 # SQLAlchemy ORM table definitions
│   │   │   └── schemas.py            # Pydantic request/response models
│   │   └── services/
│   │       ├── discharge_service.py  # query v_discharge_summary, merge outreach
│   │       ├── outreach_service.py   # upsert outreach_status, activity log
│   │       └── manager_service.py    # per-user and per-practice aggregations
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── public/
│   │   └── citadel-logo-hd-transparent.png
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── auth/
│   │   │   ├── msalConfig.ts
│   │   │   ├── AuthProvider.tsx
│   │   │   ├── useAuth.ts
│   │   │   └── RequireAuth.tsx
│   │   ├── api/
│   │   │   ├── client.ts             # axios instance with credentials:include
│   │   │   ├── discharges.ts
│   │   │   ├── outreach.ts
│   │   │   ├── manager.ts
│   │   │   └── meta.ts
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── AppHeader.tsx
│   │   │   ├── ui/
│   │   │   │   ├── StatChip.tsx
│   │   │   │   ├── StatChipRow.tsx
│   │   │   │   ├── StatusPill.tsx
│   │   │   │   ├── Button.tsx
│   │   │   │   └── LoadingSpinner.tsx
│   │   │   ├── filters/
│   │   │   │   ├── FilterSidebar.tsx
│   │   │   │   ├── AssigneeSelect.tsx
│   │   │   │   ├── PracticeMultiSelect.tsx
│   │   │   │   ├── PayerMultiSelect.tsx
│   │   │   │   ├── LobMultiSelect.tsx
│   │   │   │   ├── StayTypeMultiSelect.tsx
│   │   │   │   └── DateRangePicker.tsx
│   │   │   ├── discharge/
│   │   │   │   ├── DischargeTable.tsx
│   │   │   │   ├── DischargeTableColumns.tsx
│   │   │   │   ├── DetailPanel.tsx
│   │   │   │   ├── OutreachStatusForm.tsx
│   │   │   │   └── OutreachLegend.tsx
│   │   │   └── manager/
│   │   │       ├── ManagerDashboard.tsx
│   │   │       ├── StaffBreakdownTable.tsx
│   │   │       └── PracticeRollupTable.tsx
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   └── DashboardPage.tsx
│   │   ├── hooks/
│   │   │   ├── useDischarges.ts
│   │   │   ├── useOutreach.ts
│   │   │   ├── useFilters.ts
│   │   │   └── useManagerMetrics.ts
│   │   ├── types/
│   │   │   ├── discharge.ts
│   │   │   ├── auth.ts
│   │   │   └── api.ts
│   │   ├── lib/
│   │   │   └── utils.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
├── streamlit_app.py                  # V2 — stays on port 8502 during migration
└── V3_UNIFIED_SPEC.md               # this file
```

### Shared Types Contract

TypeScript interfaces in `frontend/src/types/` are the source of truth for the frontend. Pydantic schemas in `backend/app/models/schemas.py` must match them. No automatic schema sync at launch. After API stabilizes, add `openapi-typescript` to generate types from FastAPI's `/openapi.json`.

---

## 2. Agent 1: Database

This agent owns schema migrations, the session table, view verification, and grants. All work here happens before backend or frontend code is written.

### 2.1 New Table: `discharge_app.app_session`

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
```

Cleanup (run via pg_cron or app startup):
```sql
DELETE FROM discharge_app.app_session WHERE expires_at < now();
```

### 2.2 Verify `v_discharge_summary`

Confirm the view returns all columns the frontend needs. Required columns:

| Column | Notes |
|---|---|
| `event_id` | Primary key (composite with discharge_date) |
| `discharge_date` | DATE |
| `patient_name` | |
| `insurance_member_id` | Recently added (commit `ffbc926`) — verify present |
| `practice` | |
| `payer_name` | |
| `lob_name` | |
| `stay_type` | |
| `discharge_hospital` | |
| `length_of_stay` | INT |
| `disposition` | |
| `dx_code` | |
| `description` | Diagnosis description |
| `admit_date` | DATE |

### 2.3 Grants

Ensure `discharge_app_role` has:
- SELECT on `v_discharge_summary`
- SELECT, INSERT, UPDATE, DELETE on `discharge_app.outreach_status`
- SELECT, INSERT, UPDATE, DELETE on `discharge_app.app_session`
- SELECT, INSERT on `discharge_app.user_activity_log`
- SELECT on `discharge_app.app_user`

### 2.4 Deliverable

Commit migration to `backend/migrations/001_add_app_session.sql`.

---

## 3. Agent 2: Backend (FastAPI)

This agent builds the entire FastAPI application — config, database connection, auth, all API endpoints, and tests.

### 3.1 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.x | API framework |
| `uvicorn[standard]` | 0.30.x | ASGI server |
| `sqlalchemy` | 2.0.x | ORM + connection pool (async style) |
| `asyncpg` | 0.29.x | Async PostgreSQL driver |
| `pydantic` | 2.x | Request/response validation |
| `pydantic-settings` | 2.x | Config from env vars / `.env` |
| `python-jose[cryptography]` | 3.3.x | JWT decoding for Entra ID |
| `httpx` | 0.27.x | Async HTTP client (JWKS fetch, token exchange) |
| `python-multipart` | 0.0.9 | Form data (auth callback) |
| `pytest` + `httpx` | latest | Tests |

**Why asyncpg:** 20 concurrent users with reads and writes — async I/O prevents thread blocking. Do NOT use the `databases` library; SQLAlchemy async is the mature path.

### 3.2 Environment Variables (`backend/.env`)

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

### 3.3 Connection Pooling

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

For 20 concurrent users, pool_size=10 is sufficient.

### 3.4 Auth System

**Strategy: Backend-mediated auth with httpOnly session cookies.**

The frontend uses MSAL.js only to initiate the Microsoft redirect and receive the authorization code. The backend exchanges the code for tokens, validates the ID token, and sets an httpOnly cookie. The frontend NEVER stores or forwards raw tokens.

**Why:** Tokens in localStorage are vulnerable to XSS. With 17k rows of PHI-adjacent patient data, this is not acceptable. httpOnly cookies are inaccessible to JavaScript. 20 concurrent users makes server-side sessions trivial.

#### Auth Middleware

```python
# backend/app/auth/session.py
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> AppUser:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(AppSession)
        .where(AppSession.token == token)
        .where(AppSession.expires_at > func.now())
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    # Touch last_seen_at (fire-and-forget)
    asyncio.create_task(touch_session(session.id, db))

    return AppUser(email=session.user_email, name=session.user_name, role=session.user_role)
```

Sessions are stored in `discharge_app.app_session`. Token is a cryptographically random 32-byte hex string (not a JWT).

#### Session Cleanup on Startup

```python
@app.on_event("startup")
async def cleanup_expired_sessions():
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM discharge_app.app_session WHERE expires_at < now()"))
        await db.commit()
```

#### Full Auth Flow (22 Steps)

```
1.  User loads https://citadelbmi001.citadelhealth.local/
2.  React AuthProvider calls GET /api/auth/me with credentials:include
3.  No session cookie -> 401
4.  AuthProvider redirects to /login
5.  User clicks "Sign in with Microsoft"
6.  MSAL.js calls loginRedirect() -> browser goes to Microsoft
7.  User authenticates on Microsoft's UI
8.  Microsoft redirects to /auth/callback?code=0.AXxx...
9.  React CallbackPage extracts the code from URL
10. CallbackPage POSTs to /api/auth/callback { code, redirect_uri }
11. FastAPI exchanges code with Microsoft token endpoint (httpx)
12. Backend decodes/validates ID token (python-jose):
    - Verify signature against Microsoft JWKS
    - Verify iss, aud, exp
    - Check email domain against AUTH_ALLOWED_DOMAINS
13. Backend looks up user in discharge_app.app_user
14. Backend creates session in discharge_app.app_session (32-byte token, 8h TTL)
15. Backend returns 200 { ok: true }
    Set-Cookie: session=TOKEN; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=28800
16. Frontend navigates to /
17. AuthProvider re-calls GET /api/auth/me (cookie attached automatically)
18. /api/auth/me returns { email, name, role }
19. AuthProvider stores user in React context
20. DashboardPage loads, calls GET /api/discharges (cookie attached automatically)
```

**SameSite=Lax** is correct. It blocks cross-site POSTs (CSRF protection) while allowing the OAuth redirect navigation. Do NOT use Strict (breaks OAuth callback) or None (unnecessary).

### 3.5 Endpoint Reference

Every endpoint maps to functions in `streamlit_app.py`. Line numbers reference V2 source.

---

#### `POST /api/auth/callback`

Receives OAuth authorization code from frontend after Microsoft redirect.

**Request:** `{ "code": "0.AXXX...", "redirect_uri": "https://..." }`

**What it does:**
1. Calls Microsoft token endpoint via httpx
2. Decodes ID token with python-jose, validates claims
3. Looks up or creates user in `discharge_app.app_user`
4. Creates session row in `discharge_app.app_session`
5. Sets httpOnly cookie

**Response:** `{ "ok": true }`
**Errors:** 401 (domain not allowed), 400 (token exchange fails)
**Maps to:** `_exchange_code()` (line 69), `check_auth()` (line 152-213), `get_user_role()` (line 842-858)

---

#### `POST /api/auth/logout`

Deletes session row, clears cookie.

**Response:** `{ "ok": true }` with `Set-Cookie: session=; Max-Age=0`
**Maps to:** sign-out handler (line 1038-1041)

---

#### `GET /api/auth/me`

Returns current user identity. Called on app load to hydrate React auth context.

**Response:**
```json
{ "email": "rcruz@citadelhealth.com", "name": "Ronnie Cruz", "role": "manager" }
```
**Requires:** valid session cookie
**Maps to:** `st.session_state` user fields (lines 194-207)

---

#### `GET /api/discharges`

Returns full merged discharge + outreach dataset. Heaviest endpoint.

**Query parameters:** None — all filtering client-side in React.

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

**Why return everything:** 17k rows = ~8-12 MB uncompressed, ~1.5 MB gzipped. Internal LAN loads in under a second. Client-side filtering is then instant. Revisit if dataset exceeds 100k rows.

**Caching:** TanStack Query on frontend caches for `staleTime: 5 * 60 * 1000` (5 min). After outreach upsert, `queryClient.invalidateQueries(['discharges'])` triggers background refetch.

**SQL:**
```sql
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

Server-side join replaces Python-side `_merge_outreach()` (lines 1090-1120). No pandas needed.

**Maps to:** `_load_raw_discharge_data()` (line 703), `load_outreach_statuses()` (line 738), `_merge_outreach()` (line 1090), `load_discharge_data_with_status()` (line 724)

**Return snake_case JSON** (e.g., `patient_name`, `discharge_date`). Do NOT title-case. Column names defined explicitly in Pydantic schema.

---

#### `GET /api/outreach/{event_id}`

Returns current outreach record for a single event. Used when detail panel opens for fresh data.

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

Returns 404 if no outreach record exists (means `no_outreach`).
**Maps to:** `load_outreach_statuses()` dict lookup (line 1165-1169)

---

#### `PUT /api/outreach/{event_id}`

Upserts outreach status for one discharge event. Core write operation.

**Path param:** `event_id`
**Request body:**
```json
{ "discharge_date": "2026-03-15", "status": "outreach_made", "notes": "Left voicemail at 9am" }
```

**What it does:**
1. Runs upsert SQL
2. Writes to `discharge_app.user_activity_log` with action `outreach_update`
3. Returns updated record

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

**Maps to:** `upsert_outreach_status()` (lines 641-697)

---

#### `GET /api/meta/filters`

Returns all distinct filter values. Called once on app load, cached 5 min.

**Response:**
```json
{
  "practices": ["Aylo Family Medicine", "Citadel Primary Care"],
  "payers": ["BCBS", "Aetna"],
  "lob_names": ["Commercial", "Medicare"],
  "stay_types": ["Inpatient", "Observation"],
  "assignees": [
    { "name": "Sarah Smith", "practices": ["Aylo Family Medicine", "Citadel West"] }
  ],
  "discharge_date_min": "2024-01-01",
  "discharge_date_max": "2026-04-13"
}
```

**Maps to:** `render_sidebar_filters()` (lines 956-1043), `load_practice_assignments()` (lines 771-789)

---

#### `GET /api/manager/metrics`

Manager dashboard aggregations. **Role-gated:** returns 403 for non-managers.

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

Aggregation done in SQL on the backend (not in the browser). Move from Python DataFrame loops (lines 1384-1544) to proper SQL.

**Staff breakdown SQL sketch:**
```sql
SELECT
    u.user_email,
    u.display_name,
    array_length(u.practices, 1)                                          AS practice_count,
    COUNT(d.event_id)                                                     AS total,
    COUNT(*) FILTER (WHERE COALESCE(o.status,'no_outreach')='no_outreach') AS no_outreach,
    COUNT(*) FILTER (WHERE o.status='outreach_made')                      AS outreach_made,
    COUNT(*) FILTER (WHERE o.status='outreach_complete')                  AS outreach_complete,
    MAX(al_login.created_at)                                              AS last_login,
    MAX(al_any.created_at)                                                AS last_activity
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

**Maps to:** `render_manager_dashboard()` (lines 1373-1544)

### 3.6 Build Order

1. Scaffold `backend/` directory, install deps, create `main.py`, `config.py`, `database.py`
2. `GET /api/discharges` — most important endpoint. Test with curl against live DB
3. `PUT /api/outreach/{event_id}` — copy upsert SQL from Streamlit
4. `GET /api/meta/filters`
5. Auth: `POST /api/auth/callback`, `GET /api/auth/me`, `POST /api/auth/logout`
6. `GET /api/manager/metrics`
7. Wire `get_current_user` dependency on all protected routes
8. Write tests for the three core endpoints

**During development:** stub auth — `get_current_user` returns a hardcoded test user. This lets you build/test the entire data API without touching Entra ID.

---

## 4. Agent 3: Frontend (React)

This agent builds the React application — scaffolding, routing, auth integration, data hooks, all components, and interactions.

### 4.1 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `vite` | 5.x | Build tool |
| `react` | 18.3.x | UI framework |
| `typescript` | 5.4.x | Type safety |
| `@tanstack/react-table` | 8.x | Discharge table — virtual rows, sorting, filtering |
| `@tanstack/react-virtual` | 3.x | Row virtualization for 17k rows |
| `@tanstack/react-query` | 5.x | Server state caching, background refetch, mutations |
| `@azure/msal-browser` | 3.x | Entra ID auth — SPA redirect flow |
| `@azure/msal-react` | 2.x | React context + hooks wrapping MSAL browser |
| `tailwindcss` | 3.x | Utility CSS |
| `@radix-ui/react-*` | latest | Accessible primitives: Dialog, Select, RadioGroup, Tooltip |
| `react-router-dom` | 6.x | Routing |
| `date-fns` | 3.x | Date formatting |
| `clsx` | 2.x | Conditional className utility |
| `axios` | 1.7.x | HTTP client with interceptors |

### 4.2 Component Tree

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
                        ├── TabStrip [Recent | 6 Months | All | Manager (role-gated)]
                        ├── StatChipRow
                        └── TabPanel
                            ├── OutreachLegend
                            ├── DischargeTable
                            ├── DetailPanel (conditional, slide-in)
                            │   └── OutreachStatusForm
                            └── ExportButton
                        (Manager tab):
                            └── ManagerDashboard
                                ├── StatChipRow (5 chips)
                                ├── StaffBreakdownTable
                                └── PracticeRollupTable
```

### 4.3 State Management

**Server state (TanStack Query):**

```typescript
// hooks/useDischarges.ts
export function useDischarges() {
  return useQuery({
    queryKey: ['discharges'],
    queryFn: () => api.get('/api/discharges').then(r => r.data),
    staleTime: 5 * 60 * 1000,   // 5 min — match Streamlit ttl=300
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

**UI state:**

| State | Where | Why |
|---|---|---|
| Active tab | `useState` in DashboardPage | No reason for URL |
| Selected row | `useState` in DashboardPage | Local interaction |
| Filter values | URL search params via `useFilters` | Shareable, survives refresh |
| Detail panel open | Derived from `selectedRow !== null` | Not independent state |

### 4.4 Filter State in URL

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

Client-side filtering in `useMemo`:

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

Runs in microseconds for 17k rows. No debouncing needed.

### 4.5 Table + Detail Panel Split Layout

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
        <DetailPanel row={selectedRow} onClose={() => setSelectedRow(null)} />
      </div>
    )}
  </div>
);
```

### 4.6 Table Virtualization

Required for 17k rows — without it, 17k DOM nodes makes the tab sluggish.

```typescript
// DischargeTable.tsx
import { useVirtualizer } from '@tanstack/react-virtual';

const rowVirtualizer = useVirtualizer({
  count: table.getRowModel().rows.length,
  getScrollElement: () => tableContainerRef.current,
  estimateSize: () => 40,
  overscan: 10,
});
```

Only ~20 visible rows in the DOM at any time.

### 4.7 Role-Gating

```tsx
const { isManager } = useAuth();
const tabs = ['Recent', 'Last 6 Months', 'All Discharges', ...(isManager ? ['Manager'] : [])];
```

Manager tab excluded entirely for non-managers (not just hidden). Backend also enforces role on `/api/manager/metrics`. Defense in depth.

### 4.8 MSAL.js Configuration

```typescript
// auth/msalConfig.ts
export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AUTH_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AUTH_TENANT_ID}`,
    redirectUri: `${window.location.origin}/auth/callback`,
    postLogoutRedirectUri: `${window.location.origin}/login`,
    navigateToLoginRequestUrl: false,
  },
  cache: {
    cacheLocation: 'sessionStorage',   // MSAL state only, not tokens we keep
    storeAuthStateInCookie: false,
  },
};

export const loginRequest = { scopes: ['openid', 'profile', 'email'] };
```

MSAL cache in sessionStorage only stores code verifier / state for PKCE. Access token never lives in the browser.

### 4.9 HTTP Client

```typescript
// api/client.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,   // sends session cookie on every request
});

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

No Authorization header. No token in localStorage. Cookie does the work.

### 4.10 Vite Dev Proxy

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

### 4.11 CSV Export (Browser-Side)

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

### 4.12 Interaction Patterns

#### Row Click -> Detail Panel
1. Click row -> highlighted (bg `#e8f0f7`, left border `3px solid #132e45`)
2. Main area transitions to split-pane: table 55%, detail panel 45% (220ms slide + fade)
3. Panel populated from client-side data (no API call to open)
4. Click same row again -> panel closes, table returns to full width
5. Click different row while panel open -> content swaps instantly (no re-animation)

#### Status Selection -> Save
1. Click status button -> immediate visual update (local state, no API)
2. Click Cancel -> reverts to last saved status
3. Click Save -> button shows spinner, table row pill updates optimistically
4. On success: toast "Status updated for [Patient Name]", panel closes, cache invalidated
5. On error: optimistic update reverts, error toast, panel stays open for retry

#### Filter Change -> Table Update
1. Any filter change -> table re-filters instantly (client-side)
2. If selected row no longer in results -> panel closes, selection cleared
3. Stat chips and record count badge update

#### Tab Switching
1. Row selection cleared (panel closes)
2. Filter state preserved across tabs
3. Stat chips update for new tab's record count

#### Keyboard Navigation

| Key | Action |
|---|---|
| `Tab` | Move focus through filters, tabs, table rows |
| `Arrow Down/Up` | Navigate table rows |
| `Enter` / `Space` | Select focused row |
| `Escape` | Close detail panel |
| `Tab` in panel | Status buttons -> notes -> Save -> Cancel |

Focus moves to first interactive element in panel when opened; returns to selected row when closed.

### 4.13 Build Order

1. `npm create vite@latest frontend -- --template react-ts`
2. Install all packages, configure Tailwind
3. `LoginPage.tsx` with branded card
4. `AuthProvider.tsx` + MSAL redirect flow
5. `/auth/callback` route handler
6. `RequireAuth.tsx` guard
7. `AppShell.tsx` (empty sidebar + content)
8. Verify login works end-to-end
9. `useDischarges` + `useFilters` hooks
10. `DischargeTable.tsx` with TanStack Table + Virtual
11. `FilterSidebar.tsx` with all controls
12. `StatChipRow.tsx`
13. Tab strip (Recent / 6 Months / All)
14. `DetailPanel.tsx` + `OutreachStatusForm.tsx`
15. `useUpsertOutreach` mutation
16. CSV export
17. `ManagerDashboard.tsx` + sub-tables
18. Role-gated 4th tab

---

## 5. Agent 4: UI / Design System

This agent owns the visual language — Tailwind config, design tokens, component styles, accessibility, loading/empty states. Provides the styling contracts that the Frontend Agent implements.

### 5.1 Layout Architecture

```
┌──────────────────────────────────────────────────────────┐
│  AppShell                                                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Sidebar (240px fixed)  │  Main Area (flex: 1)      │ │
│  │                         │  ┌───────────────────────┐ │ │
│  │  Logo                   │  │ Header bar            │ │ │
│  │  Filters section        │  ├───────────────────────┤ │ │
│  │  Date range             │  │ Tab strip             │ │ │
│  │  Clear Filters          │  ├───────────────────────┤ │ │
│  │  User info + Sign out   │  │ Stat chips row        │ │ │
│  │                         │  ├───────────────────────┤ │ │
│  │                         │  │ Table | Detail Panel  │ │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

- **Sidebar:** 240px fixed. Does not collapse on desktop. On tablet (768-1024px): drawer overlay with hamburger icon.
- **Main area:** 24px padding all sides. No max-width (internal tool, full-width expected).
- **Split-pane:** Table 55% / Detail panel 45% when row selected. `flex` + `gap: 16px`. On tablet: stacked vertically.

### 5.2 Tailwind Config — Colors

```js
// tailwind.config.ts — theme.extend.colors
colors: {
  navy: {
    DEFAULT: '#132e45',    // primary brand
    light:   '#1b4459',    // gradients, secondary
    dark:    '#0e2233',    // hover states
  },
  orange: {
    DEFAULT: '#e07b2a',    // CTA, accent
    hover:   '#c96920',
  },
  page:    '#f0f2f5',      // page background
  surface: '#ffffff',       // cards, panels
  'text-primary':   '#132e45',
  'text-secondary': '#556e81',
  'text-muted':     '#7e96a6',
  'text-light':     '#a8c4d8',
  border:       '#d0dae3',
  'border-light': '#e8ecf0',
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
}
```

### 5.3 Tailwind Config — Typography

Font: **Inter** (self-hosted for internal server). Fallback: `system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`.

| Role | Size | Weight | Color |
|---|---|---|---|
| Page title (header bar) | 26px / 1.625rem | 800 | `#ffffff` |
| Header subtitle | 13px / 0.8125rem | 400 | `#a8c4d8` |
| Welcome greeting | 21px / 1.3125rem | 400 | `#556e81` |
| Section heading | 16px / 1rem | 700 | `#132e45` |
| Tab label | 13.5px / 0.844rem | 600 | `#1b4459` |
| Stat chip label | 11.5px / 0.72rem | 700 | `#556e81` (uppercase, tracking-wider) |
| Stat chip value | 24.8px / 1.55rem | 800 | varies |
| Table header | 11px / 0.6875rem | 600 | `#ffffff` (uppercase) |
| Table body | 13px / 0.8125rem | 400 | `#2a3f50` |
| Detail field label | 11px / 0.7rem | 700 | `#7e96a6` (uppercase) |
| Detail field value | 14.4px / 0.9rem | 600 | `#132e45` |
| Sidebar label | 11px / 0.7rem | 600 | `#a8c4d8` (uppercase) |
| Sidebar section heading | 15.2px / 0.95rem | 700 | `#ffffff` |
| Status pill | 11.8px / 0.74rem | 600 | varies |
| Login card title | 21.6px / 1.35rem | 800 | `#ffffff` |

### 5.4 Tailwind Config — Border Radii, Shadows, Transitions

```js
borderRadius: {
  'sm':   '6px',     // minor elements
  'md':   '8px',     // buttons, inputs, status buttons
  'lg':   '10px',    // stat chips, tables
  'xl':   '12px',    // detail panel
  '2xl':  '14px',    // header bar
  '3xl':  '16px',    // login card
  'full': '9999px',  // pills, dots, tags
}

boxShadow: {
  'chip':    '0 2px 6px rgba(19,46,69,0.06)',
  'card':    '0 2px 8px rgba(19,46,69,0.07)',
  'panel':   '0 4px 18px rgba(19,46,69,0.10)',
  'header':  '0 4px 18px rgba(19,46,69,0.18)',
  'login':   '0 6px 28px rgba(19,46,69,0.22)',
  'btn-cta': '0 2px 8px rgba(224,123,42,0.35)',
  'input-focus': '0 0 0 2px rgba(19,46,69,0.15)',
}

transitionDuration: { 'fast': '120ms', 'base': '180ms', 'slow': '220ms' }
transitionTimingFunction: {
  'panel-in':  'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
  'panel-out': 'ease-in',
  'button':    'ease',
}
```

Key animations:
- Detail panel enter: 220ms `panel-in`, exit: 180ms `panel-out`
- Button hover: 200ms ease
- Status button selection: 150ms ease
- Row highlight: 100ms ease
- Tab switch: instant (no animation)
- Toast: 200ms fade-in, 3s auto-dismiss, 200ms fade-out

### 5.5 Component Specs

#### Sidebar

| Element | Style |
|---|---|
| Background | `#132e45` |
| Section heading | `#ffffff`, 14px, weight 700, `border-bottom: 1px solid #1b4459` |
| Label text | `#a8c4d8`, 11px, weight 600, uppercase, tracking 0.06em |
| Divider | `border-color: #1b4459` |
| Dropdown input text | `#1a1a2e` (dark) — **critical: inputs must render dark text** |
| Multi-select tag | Background `#e07b2a`, text `#ffffff` |
| User name | `#ffffff`, 13px, weight 700 |
| User email | `#7ea8c0`, 11px |
| Clear/Sign Out buttons | `border: 1.5px solid #1b4459`, bg transparent, text `#d6e6f0`, radius 8px |
| Button hover | bg `#1b4459`, text `#ffffff` |

Filter logic:
- "Assigned To" changes -> Practice options re-scoped to that person's practices
- All other filters independent multi-selects
- Changes fire immediately (no "Apply" button)
- If selected row no longer in filtered results -> detail panel closes

#### Header Bar

- Background: `linear-gradient(135deg, #132e45 0%, #1b4459 100%)`
- Border-radius: 14px, padding: 18px 28px
- Box-shadow: `0 4px 18px rgba(19,46,69,0.18)`
- Right edge accent: absolute, right 0, width 5px, `linear-gradient(180deg, #e07b2a 0%, #c96920 100%)`, radius 0 14px 14px 0
- Title: `#ffffff`, 26px, weight 800
- Subtitle: `#a8c4d8`, 13px

Logo: 300px wide, centered above header. Welcome line: `#556e81`, 21px, with name portion `#132e45` weight 700.

#### Tab Strip

- Container: bg `#e4eaf0`, radius 10px, padding 4px, inline-flex
- Each tab: radius 7px, `#1b4459`, weight 600, 13.5px, padding 6px 18px
- Active: bg `#132e45`, text `#ffffff`
- Hover (inactive): bg `rgba(19,46,69,0.08)`
- Pill/capsule style (no underline)

#### Stat Chips

```
┌─[4px left border]─────────────────┐
│  LABEL (uppercase, muted)          │
│  VALUE (large, bold)               │
└────────────────────────────────────┘
```

| Variant | Left border | Value color |
|---|---|---|
| Default (navy) | `#132e45` | `#132e45` |
| Orange | `#e07b2a` | `#e07b2a` |
| Green | `#38a169` | `#22753a` |
| Gray | `#a0aec0` | `#718096` |

Common: bg `#ffffff`, border `1px solid #d0dae3` + 4px left override, radius 10px, padding 10px 18px, shadow `chip`. Label: `#556e81`, 11.5px, weight 700, uppercase. Value: 24.8px, weight 800.

Staff tabs: Total Records (navy), Unique Patients (navy), Practices (orange), Hospitals (navy).
Manager: Total Discharges (navy), No Outreach (gray), Outreach Made (orange), Complete (green), % Complete (green).

#### Discharge Table

Columns: Patient Name (180px) | Discharge Date (120px, DESC default) | Practice (160px) | Payer (150px) | Hospital (180px) | LOS (80px, right-aligned) | Disposition (130px) | Status (160px, pill badge)

- Container: bg `#ffffff`, radius 10px, shadow `card`, overflow hidden
- Header: bg `#132e45`, text `#ffffff`, 11px, weight 600, uppercase, padding 10px 12px
- Rows: bg `#ffffff`, text `#2a3f50`, 13px, padding 9px 12px, border-bottom `1px solid #e8ecf0`
- Row hover: bg `#f7f9fb`
- Selected: bg `#e8f0f7`, left border `3px solid #132e45`
- Status-tinted rows: outreach_made `rgba(224,123,42,0.04)`, outreach_complete `rgba(56,161,105,0.04)`
- Sort: single-column, click to cycle asc/desc/none. Arrow indicators in header.
- Virtual scroll: viewport `calc(100vh - 380px)`, min 300px, row height 40px fixed.

Record count badge: section name 16px weight 700, count in `bg-navy text-white` pill (12px, radius 20px).

Outreach legend above table: `● No Outreach  ● Outreach Made  ● Outreach Complete` — dots 8px, 12.5px text, gap 24px.

Export button below table, right-aligned.

#### Detail Panel

Container: bg `#ffffff`, radius 12px, shadow `panel`, border `1.5px solid #132e45`.

Header: gradient navy, padding 16px 20px, title `#ffffff` 16px weight 700.

Patient info grid: 3 columns. Fields: Practice | Payer | Hospital (row 1), Diagnosis | LOS | Disposition (row 2). Label: `#7e96a6`, 11px, weight 700, uppercase. Value: `#132e45`, 14.4px, weight 600. Em dash for null.

**Status buttons — Segmented Button Group (not radios):**

Three buttons in a row: `[ No Outreach ] [ Outreach Made ] [ Outreach Complete ]`

- Unselected: bg `#f7f9fb`, border `1.5px solid #d0dae3`, text `#2a3f50`, radius 8px
- Selected No Outreach: bg `#edf2f7`, border `#a0aec0`, text `#718096`
- Selected Outreach Made: bg `#fff3e0`, border `#e07b2a`, text `#c05621`
- Selected Complete: bg `#e6ffed`, border `#38a169`, text `#22753a`
- 8px status dot inside each button, left of label

Notes textarea: bg `#f7f9fb`, border `1.5px solid #d0dae3`, radius 8px, focus border `#132e45` + `input-focus` shadow, 80px height, 13px text.

Last updated: 12px, `#7e96a6`, name portion weight 700. Only shown when record exists.

Save button: bg `#e07b2a`, text `#ffffff`, radius 8px, weight 700. Hover: `#c96920`. Loading: spinner replaces text.
Cancel button: bg transparent, border `1.5px solid #d0dae3`, text `#556e81`. Hover: border/text `#132e45`.

Panel slide-in: `translateX(100%) -> translateX(0)`, 220ms ease-out. Exit: 180ms ease-in. Unmounted from DOM when closed.

#### Login Page

Full-page, no sidebar. Page bg `#f0f2f5`.

Center column: max-width 420px, margin auto, padding-top 80px. Logo 160px above card.

Card: gradient navy, radius 16px, padding 32px, shadow `login`, orange right accent (5px). Title: `#ffffff`, 21.6px, weight 800. Subtitle: `#a8c4d8`, 14px.

Sign In button: full width, bg `#e07b2a`, text `#ffffff`, 15.2px, weight 700, radius 9px, shadow `btn-cta`. Hover: `#c96920`.

Domain note: `#7e96a6`, 12px, centered. "Access restricted to: @citadelhealth.com, @aylohealth.com"

#### Manager Dashboard

Full-width (no split-pane). 5 stat chips, then Staff Breakdown table, then Practice Roll-Up table.

**Staff Breakdown columns:** Name (160px) | Practices (80px, center) | Total (80px) | No Outreach (100px) | Made (80px) | Complete (80px) | % Done (80px, bold) | Last Login (100px) | Last Activity (100px)

**Practice Roll-Up columns:** Practice (200px) | Total (80px) | No Outreach (100px) | Made (80px) | Complete (80px) | % Done (80px, bold). Sorted by Total DESC.

Manager table styles: header bg `#132e45`, text `#ffffff`, 12px uppercase. Data cells: padding 9px 12px, border-bottom `#e8ecf0`. Row hover: `#f7f9fb`. Radius 10px, shadow `card`.

### 5.6 Status Visual System

| Status | DB value | Dot | Pill bg | Pill text | Row tint | Button selected bg | Button border | Button text |
|---|---|---|---|---|---|---|---|---|
| No Outreach | `no_outreach` | `#cbd5e0` | `#edf2f7` | `#718096` | none | `#edf2f7` | `#a0aec0` | `#718096` |
| Outreach Made | `outreach_made` | `#e07b2a` | `#fef3e2` | `#c05621` | `rgba(224,123,42,0.04)` | `#fff3e0` | `#e07b2a` | `#c05621` |
| Complete | `outreach_complete` | `#38a169` | `#e6ffed` | `#22753a` | `rgba(56,161,105,0.04)` | `#e6ffed` | `#38a169` | `#22753a` |

Pill badge: inline-flex, gap 5px, padding 3px 10px, radius 9999px, 11.8px weight 600. Dot 7px circle. No border on pills.

### 5.7 Accessibility

**Contrast (WCAG AA verified):**

| Combination | Ratio | Level |
|---|---|---|
| `#ffffff` on `#132e45` | 9.7:1 | AAA |
| `#ffffff` on `#1b4459` | 7.8:1 | AAA |
| `#ffffff` on `#e07b2a` | 3.1:1 | AA (large/UI) |
| `#2a3f50` on `#ffffff` | 10.4:1 | AAA |
| `#c05621` on `#fef3e2` | 4.7:1 | AA |
| `#22753a` on `#e6ffed` | 5.1:1 | AA |
| `#a8c4d8` on `#132e45` | 4.5:1 | AA |

**Focus ring:** `outline: 2px solid #e07b2a; outline-offset: 2px` via `:focus-visible`. Apply to all interactive elements.

**ARIA:**

| Element | ARIA |
|---|---|
| Sidebar | `role="navigation"`, `aria-label="Filters"` |
| Tab strip | `role="tablist"` |
| Each tab | `role="tab"`, `aria-selected`, `aria-controls` |
| Discharge table | `role="grid"`, `aria-label="Discharge records"` |
| Status button group | `role="group"`, `aria-label="Outreach status"` |
| Status buttons | `role="radio"`, `aria-checked` |
| Detail panel | `role="complementary"`, `aria-label="Patient detail"` |
| Save button (loading) | `aria-busy="true"` |
| Error toast | `role="alert"`, `aria-live="assertive"` |
| Success toast | `role="status"`, `aria-live="polite"` |

Virtual scroll: set `aria-rowcount` to full dataset size, `aria-rowindex` on each rendered row.

### 5.8 Loading and Empty States

**Initial load:** Skeleton rows (10 fake rows with shimmer animation, 40px height). Table header renders normally. Stat chips show skeleton bars.

```css
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position:  200% 0; }
}
.skeleton {
  background: linear-gradient(90deg, #e8ecf0 25%, #f0f3f5 50%, #e8ecf0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}
```

**No results after filtering:** Search icon (48px, `#a8c4d8`), "No records match the current filters", subtext, "Clear All Filters" button centered.

**Empty tab:** "No discharges in this time range" — informational only, no clear button.

**API error:** Warning triangle icon (48px, `#e07b2a`), "Could not load discharge data", retry button.

**Save error:** Optimistic update reverts. Error toast (red bg `#fee2e2`, text `#991b1b`, auto-dismiss 6s). Panel stays open.

**Success toast:** Fixed top-right, bg `#f0fff4`, border `#9ae6b4`, text `#22543d`, checkmark icon, "Status updated for [Patient Name]", auto-dismiss 3s, slide-down + fade.

**Loading during save:** Save button disabled with 16px spinner, status buttons + textarea + cancel disabled (opacity 0.6), table pill updates optimistically.

---

## 6. Agent 5: DevOps / Deployment

This agent handles nginx config, systemd services, TLS, and the cutover process.

### 6.1 Nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name citadelbmi001.citadelhealth.local;

    # TLS (existing self-signed or internal CA cert)
    # ssl_certificate / ssl_certificate_key paths here

    root /opt/discharge_report_automation/frontend/dist;
    index index.html;

    # Enable gzip for JSON payloads (~1.5MB compressed for 17k rows)
    gzip on;
    gzip_types application/json text/css application/javascript;

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

### 6.2 FastAPI Systemd Service

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

### 6.3 Parallel Operation

Both apps use the same database. Outreach updates in either are immediately visible in the other. Run V3 alongside V2 for at least 2-3 days of parallel testing.

- Streamlit V2: port 8502 (feature branch)
- Streamlit V1: port 8501 (main branch, emergency rollback)
- React V3: port 443 via nginx

### 6.4 Cutover Process

1. `npm run build` in `frontend/` -> generates `dist/`
2. Copy `dist/` to `/opt/discharge_report_automation/frontend/dist/`
3. Configure nginx, test
4. Run parallel for 2-3 days
5. Announce cutover date to staff
6. On cutover: stop Streamlit V2 service
7. Keep V1 on port 8501 as emergency rollback for 2 weeks

### 6.5 TLS Requirement

httpOnly cookies with `SameSite=Lax` require HTTPS. Self-signed cert is fine for internal use as long as staff machines trust it (internal CA or manual install). MSAL.js redirect may fail silently if browsers reject the cert.

---

## 7. Phase Timeline

| Phase | Agent | What | Duration | Depends On |
|---|---|---|---|---|
| 0 | Database | `app_session` table, view verification, grants | 1 day | — |
| 1 | Backend | Full FastAPI API, tested with curl | 1-2 weeks | Phase 0 |
| 2 | Frontend | React scaffold + auth flow working | 3-4 days | Phase 1 auth endpoints |
| 3 | Frontend + UI | Table, detail panel, filters, outreach workflow | 1 week | Phase 2 |
| 4 | Frontend + UI | Manager dashboard | 3 days | Phase 3 |
| 5 | DevOps | nginx, systemd, parallel testing, cutover | 2-3 days | Phase 4 |
| **Total** | | | **4-6 weeks** | |

---

## 8. Pre-Flight Checklist

Before writing any code:

- [ ] Add `https://citadelbmi001.citadelhealth.local/auth/callback` to Entra ID app registration
- [ ] Add `http://localhost:5173/auth/callback` to Entra ID app registration (local dev)
- [ ] Run `CREATE TABLE discharge_app.app_session` migration on DMZ PostgreSQL
- [ ] Confirm `v_discharge_summary` has `insurance_member_id` column
- [ ] Confirm TLS cert on CITADELBMI001 is trusted by staff machines
- [ ] Note existing `AUTH_CLIENT_ID`, `AUTH_CLIENT_SECRET`, `AUTH_TENANT_ID` from Streamlit secrets
- [ ] Install nginx on CITADELBMI001 if not already present

---

## 9. Risks and Mitigations

### Entra ID Auth is Harder Than Expected

**Mitigation:**
1. Build Phase 1 with auth stubbed (`get_current_user` returns hardcoded test user)
2. Implement auth last, in isolation
3. Fallback: simple email/password login against `app_user` table (bypass SSO, layer it on later)
4. If python-jose JWKS validation is difficult, use Microsoft Graph API (`GET /v1.0/me` with access token) to validate identity

### 17k Rows JSON Payload is Too Slow

**Mitigation:**
- Enable gzip in nginx: `gzip on; gzip_types application/json;`
- 17k rows at ~500 bytes each = ~8.5MB uncompressed, ~1.5MB gzipped. At 100Mbps LAN: under 200ms
- If still slow: add server-side date filtering (`date_from`, `date_to` params). Default to last 6 months.

### Concurrent Write Conflicts

Already handled. `ON CONFLICT DO UPDATE` upsert is atomic. Last write wins. No optimistic locking needed at 20 users.

### TLS / DNS Issues

- Use IP address as redirect URI for initial testing: `https://10.1.116.2/auth/callback`
- Switch to hostname once DNS resolves correctly

### Streamlit Can't Be Shut Down

V2 and V3 share the same database. No "must cut over by date X" constraint. Keep V2 running indefinitely as safety net.
