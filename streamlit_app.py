import base64
import json
import os
from datetime import datetime, timedelta

import msal
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "citadel-logo-hd-transparent.png")

PAGE_TITLE = "Discharge Report Dashboard"
PAGE_ICON = LOGO_PATH if os.path.exists(LOGO_PATH) else "📄"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Auth helpers ─────────────────────────────────────────────────────────────

def _auth_secret(key: str, default: str = "") -> str:
    """Read from st.secrets first, then env vars."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, default)


def _auth_enabled() -> bool:
    return bool(_auth_secret("AUTH_CLIENT_ID"))


def _get_msal_app() -> msal.ConfidentialClientApplication:
    # Single-tenant: only users in your Entra ID directory can sign in.
    # Citadel Health and Aylo Health share the same tenant — no multi-tenant needed.
    tenant_id = _auth_secret("AUTH_TENANT_ID")
    return msal.ConfidentialClientApplication(
        client_id=_auth_secret("AUTH_CLIENT_ID"),
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=_auth_secret("AUTH_CLIENT_SECRET"),
    )


def _redirect_uri() -> str:
    return _auth_secret("AUTH_REDIRECT_URI", "http://localhost:8501")


def _allowed_domains() -> list[str]:
    raw = _auth_secret("AUTH_ALLOWED_DOMAINS", "")
    if isinstance(raw, (list, tuple)):
        return [d.lower().strip() for d in raw if d.strip()]
    return [d.lower().strip() for d in raw.split(",") if d.strip()]


def _build_auth_url() -> str:
    return _get_msal_app().get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=_redirect_uri(),
        state="discharge_report",
        prompt="select_account",
    )


def _exchange_code(code: str) -> dict:
    return _get_msal_app().acquire_token_by_authorization_code(
        code=code,
        scopes=["User.Read"],
        redirect_uri=_redirect_uri(),
    )


def _render_login_page() -> None:
    """Full-page branded login screen."""
    # Hide the sidebar on the login page
    st.markdown(
        "<style>section[data-testid='stSidebar']{display:none}</style>",
        unsafe_allow_html=True,
    )

    logo_uri = _logo_data_uri()
    logo_html = (
        f'<img src="{logo_uri}" style="width:160px;height:auto;display:block;margin:0 auto 1.25rem;" alt="Citadel Health" />'
        if logo_uri
        else '<div style="color:#ffffff;font-size:1.1rem;font-weight:900;text-align:center;margin-bottom:1rem;">Citadel Health</div>'
    )

    auth_url = _build_auth_url()
    domains = _allowed_domains()
    domain_note = (
        f"<div style='color:#7e96a6;font-size:0.75rem;text-align:center;margin-top:1rem;'>"
        f"Access restricted to: {', '.join('@' + d for d in domains)}"
        f"</div>"
        if domains
        else ""
    )

    # ── Logo above the card ──
    _, logo_col, _ = st.columns([1, 1.4, 1])
    with logo_col:
        st.markdown(logo_html.replace(
            'style="width:160px;height:auto;display:block;margin:0 auto 1.25rem;"',
            'style="width:160px;height:auto;display:block;margin:2rem auto 1rem;"',
        ), unsafe_allow_html=True)

    # ── Login card (no logo inside) ──
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg,#132e45 0%,#1b4459 100%);
                border-radius:16px;
                padding:2rem 2rem 1.75rem;
                box-shadow:0 6px 28px rgba(19,46,69,0.22);
                margin-bottom:2rem;
                position:relative;
                overflow:hidden;
            ">
                <div style="
                    position:absolute; right:0; top:0; bottom:0; width:5px;
                    background: linear-gradient(180deg, #e07b2a 0%, #c96920 100%);
                    border-radius: 0 16px 16px 0;
                "></div>
                <div style="color:#ffffff;font-size:1.35rem;font-weight:800;text-align:center;margin-bottom:0.35rem;">
                    Discharge Report Dashboard
                </div>
                <div style="color:#a8c4d8;font-size:0.88rem;text-align:center;margin-bottom:1.75rem;">
                    Sign in with your Citadel Health Microsoft account to continue.
                </div>
                <a href="{auth_url}" target="_self" style="
                    display:block; text-align:center;
                    background:#e07b2a; color:#fff;
                    font-weight:700; font-size:0.95rem;
                    padding:0.75rem 1.5rem; border-radius:9px;
                    text-decoration:none;
                    box-shadow:0 2px 8px rgba(224,123,42,0.35);
                ">
                    Sign in with Microsoft
                </a>
                {domain_note}
            </div>
            """,
            unsafe_allow_html=True,
        )


def check_auth() -> bool:
    """
    Returns True if the user is authenticated.
    Handles the OAuth callback code if present in URL params.
    If auth is not configured (no CLIENT_ID), skips auth entirely.
    """
    if not _auth_enabled():
        return True  # auth not configured — open access

    if st.session_state.get("authenticated"):
        return True

    params = st.query_params
    if "code" in params:
        with st.spinner("Signing you in..."):
            result = _exchange_code(params["code"])

        if "error" in result:
            st.error(f"Sign-in failed: {result.get('error_description', result['error'])}")
            st.query_params.clear()
            return False

        claims = result.get("id_token_claims", {})
        email = (
            claims.get("preferred_username")
            or claims.get("email")
            or claims.get("upn", "")
        )
        name = claims.get("name", email)

        allowed = _allowed_domains()
        if allowed:
            domain = email.split("@")[-1].lower() if "@" in email else ""
            if domain not in allowed:
                st.error(
                    f"Access denied — @{domain} is not an authorized domain. "
                    f"Contact your administrator."
                )
                st.query_params.clear()
                return False

        st.session_state["authenticated"] = True
        st.session_state["user_email"] = email.lower()
        st.session_state["user_name"] = name

        # Log the login event — wrapped so a DB failure never blocks sign-in
        try:
            log_activity(email.lower(), name, "login", {})
        except Exception:
            pass

        # Load and store the user's role for Phase 3/4 gating
        try:
            st.session_state["user_role"] = get_user_role(email.lower())
        except Exception:
            st.session_state["user_role"] = None

        st.query_params.clear()
        st.rerun()

    _render_login_page()
    return False

st.markdown(
    """
    <style>
    /* ── Streamlit header: blend with page background so it's not jarring,
       but leave it fully functional so the native sidebar toggle works. ── */
    header[data-testid="stHeader"] {
        background-color: #f0f2f5 !important;
        height: 2rem !important;
        min-height: 2rem !important;
    }

    /* ── Global background ── */
    .stApp {
        background-color: #f0f2f5;
    }

    /* ── Top header banner ── */
    .citadel-header {
        background: linear-gradient(135deg, #132e45 0%, #1b4459 100%);
        border-radius: 14px;
        padding: 1.25rem 1.75rem;
        display: flex;
        align-items: center;
        gap: 1.25rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 18px rgba(19,46,69,0.18);
    }
    .citadel-header-text h1 {
        font-size: 1.7rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0 0 0.15rem 0;
        letter-spacing: -0.3px;
    }
    .citadel-header-text p {
        color: #a8c4d8;
        font-size: 0.88rem;
        margin: 0;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: #132e45 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #d6e6f0 !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #1a1a2e !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="input"] * {
        color: #1a1a2e !important;
    }
    section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
        background-color: #e07b2a !important;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown p {
        color: #a8c4d8 !important;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-size: 0.95rem;
        font-weight: 700;
        margin: 1rem 0 0.4rem 0;
        border-bottom: 1px solid #1b4459;
        padding-bottom: 0.4rem;
    }
    /* Sidebar divider */
    section[data-testid="stSidebar"] hr {
        border-color: #1b4459;
        margin: 1rem 0;
    }

    /* ── Stat chips ── */
    .stat-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.25rem;
        flex-wrap: wrap;
    }
    .stat-chip {
        background: #ffffff;
        border: 1px solid #d0dae3;
        border-left: 4px solid #132e45;
        border-radius: 10px;
        padding: 0.65rem 1.1rem;
        flex: 1;
        min-width: 130px;
        box-shadow: 0 2px 6px rgba(19,46,69,0.06);
    }
    .stat-chip .chip-label {
        font-size: 0.72rem;
        font-weight: 700;
        color: #556e81;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.2rem;
    }
    .stat-chip .chip-value {
        font-size: 1.55rem;
        font-weight: 800;
        color: #132e45;
        line-height: 1;
    }
    .stat-chip.orange {
        border-left-color: #e07b2a;
    }
    .stat-chip.orange .chip-value {
        color: #e07b2a;
    }
    .stat-chip.green {
        border-left-color: #38a169;
    }
    .stat-chip.green .chip-value {
        color: #22753a;
    }
    .stat-chip.gray {
        border-left-color: #a0aec0;
    }
    .stat-chip.gray .chip-value {
        color: #718096;
    }

    /* ── Tab strip ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #e4eaf0;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px;
        color: #1b4459 !important;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 6px 18px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #132e45 !important;
        color: #ffffff !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: transparent !important;
    }

    /* ── Dataframe container ── */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(19,46,69,0.07);
    }

    /* ── Download / Export button ── */
    div[data-testid="stDownloadButton"] > button,
    .stButton > button {
        background-color: #e07b2a !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 1.25rem !important;
        transition: background 0.2s;
    }
    div[data-testid="stDownloadButton"] > button:hover,
    .stButton > button:hover {
        background-color: #c96920 !important;
    }

    /* ── Section headings ── */
    .tab-heading {
        font-size: 1rem;
        font-weight: 700;
        color: #132e45;
        margin-bottom: 0.75rem;
    }
    .record-badge {
        display: inline-block;
        background-color: #132e45;
        color: #ffffff;
        font-size: 0.75rem;
        font-weight: 700;
        border-radius: 20px;
        padding: 2px 10px;
        margin-left: 8px;
        vertical-align: middle;
    }

    /* ── Footer ── */
    .citadel-footer {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #c9d5de;
        color: #7e96a6;
        font-size: 0.78rem;
        text-align: center;
    }

    /* ── Expander ── */
    .stExpander {
        border: 1px solid #d0dae3 !important;
        border-radius: 10px !important;
        background: #ffffff !important;
    }

    /* ── Spinner & info ── */
    .stAlert {
        border-radius: 10px !important;
    }

    /* ── Remove default top padding from main content area ── */
    .stMainBlockContainer, .block-container {
        padding-top: 1.75rem !important;
    }

    /* ── Remove default top padding from sidebar ── */
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.25rem !important;
    }
    section[data-testid="stSidebar"] .stMarkdown:first-child {
        margin-top: 0 !important;
    }

    /* ── Detail panel ── */
    .detail-panel {
        margin-top: 1rem;
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 4px 18px rgba(19,46,69,0.1);
        overflow: hidden;
        border: 1.5px solid #132e45;
    }
    .detail-header {
        background: linear-gradient(135deg, #132e45 0%, #1b4459 100%);
        padding: 1rem 1.25rem;
    }
    .detail-header h3 {
        color: #fff;
        font-size: 1rem;
        font-weight: 700;
        margin: 0;
    }
    .detail-body {
        padding: 1.25rem;
    }
    .detail-grid {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 1rem;
        margin-bottom: 1.25rem;
        padding-bottom: 1.25rem;
        border-bottom: 1px solid #e8ecf0;
    }
    .detail-field label {
        display: block;
        font-size: 0.7rem;
        font-weight: 700;
        color: #7e96a6;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.2rem;
    }
    .detail-field .value {
        font-size: 0.9rem;
        color: #132e45;
        font-weight: 600;
    }
    .last-updated-line {
        font-size: 0.75rem;
        color: #7e96a6;
        margin-top: 0.5rem;
        margin-bottom: 0.75rem;
    }

    /* ── Notes textarea: ensure it's visible against the white detail panel ── */
    .stTextArea textarea {
        background-color: #f7f9fb !important;
        border: 1.5px solid #d0dae3 !important;
        border-radius: 8px !important;
        color: #2a3f50 !important;
    }
    .stTextArea textarea:focus {
        border-color: #132e45 !important;
        box-shadow: 0 0 0 2px rgba(19,46,69,0.15) !important;
    }

    /* ── Status selection buttons override ── */
    .status-btn-none button {
        background-color: #edf2f7 !important;
        color: #718096 !important;
        border: 2px solid #cbd5e0 !important;
    }
    .status-btn-none button:hover {
        background-color: #e2e8f0 !important;
    }
    .status-btn-none-active button {
        background-color: #edf2f7 !important;
        color: #4a5568 !important;
        border: 2.5px solid #718096 !important;
        box-shadow: 0 0 0 2px rgba(113,128,150,0.25) !important;
    }
    .status-btn-made button {
        background-color: #fef3e2 !important;
        color: #c05621 !important;
        border: 2px solid #e07b2a !important;
    }
    .status-btn-made button:hover {
        background-color: #fde8c8 !important;
    }
    .status-btn-made-active button {
        background-color: #fef3e2 !important;
        color: #c05621 !important;
        border: 2.5px solid #c05621 !important;
        box-shadow: 0 0 0 2px rgba(192,86,33,0.25) !important;
    }
    .status-btn-complete button {
        background-color: #e6ffed !important;
        color: #22753a !important;
        border: 2px solid #38a169 !important;
    }
    .status-btn-complete button:hover {
        background-color: #d4f8e2 !important;
    }
    .status-btn-complete-active button {
        background-color: #e6ffed !important;
        color: #22753a !important;
        border: 2.5px solid #22753a !important;
        box-shadow: 0 0 0 2px rgba(34,117,58,0.25) !important;
    }

    /* ── Outreach legend ── */
    .outreach-legend {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 0.85rem;
        font-size: 0.78rem;
        color: #556e81;
        flex-wrap: wrap;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    .dot-none { background: #cbd5e0; }
    .dot-made { background: #e07b2a; }
    .dot-complete { background: #38a169; }

    /* ── Manager dashboard tables ── */
    .manager-table {
        width: 100%;
        border-collapse: collapse;
        background: #fff;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(19,46,69,0.07);
        font-size: 0.82rem;
        margin-bottom: 1.5rem;
    }
    .manager-table th {
        background: #132e45;
        color: #fff;
        padding: 0.6rem 0.75rem;
        text-align: left;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .manager-table td {
        padding: 0.55rem 0.75rem;
        border-bottom: 1px solid #e8ecf0;
        color: #2a3f50;
    }
    .manager-table tr:last-child td {
        border-bottom: none;
    }
    .manager-table tr:hover {
        background: #f7f9fb;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── DB helpers ──────────────────────────────────────────────────────────────

@st.cache_resource
def get_engine():
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError(
            "Database URL is not configured. Set DATABASE_URL in Streamlit secrets or as an environment variable."
        )
    return create_engine(db_url, pool_pre_ping=True)


# ── Write helpers (no caching — direct DB writes) ────────────────────────────

def log_activity(user_email: str, user_name: str, action: str, detail: dict) -> None:
    """Insert a row into discharge_app.user_activity_log. Swallows exceptions so callers never break."""
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO discharge_app.user_activity_log (user_email, user_name, action, detail)
                    VALUES (:email, :name, :action, :detail::jsonb)
                    """
                ),
                {
                    "email": user_email,
                    "name": user_name,
                    "action": action,
                    "detail": json.dumps(detail),
                },
            )
    except Exception:
        pass  # logging must never break the caller


def upsert_outreach_status(
    event_id: str,
    discharge_date,
    status: str,
    updated_by: str,
    notes: str,
    old_status: str = "no_outreach",
) -> bool:
    """
    INSERT ... ON CONFLICT (event_id, discharge_date) DO UPDATE outreach_status.
    Logs the change. Returns True on success, False on failure.
    """
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO discharge_app.outreach_status
                        (event_id, discharge_date, status, updated_by, updated_at, notes)
                    VALUES
                        (:event_id, :discharge_date, :status, :updated_by, now(), :notes)
                    ON CONFLICT (event_id, discharge_date) DO UPDATE
                        SET status     = EXCLUDED.status,
                            updated_by = EXCLUDED.updated_by,
                            updated_at = now(),
                            notes      = EXCLUDED.notes
                    """
                ),
                {
                    "event_id": event_id,
                    "discharge_date": discharge_date,
                    "status": status,
                    "updated_by": updated_by,
                    "notes": notes or "",
                },
            )
        # Clear both caches so the next load reflects the change
        load_outreach_statuses.clear()
        load_discharge_data_with_status.clear()
        # Audit log (fire-and-forget)
        user_name = st.session_state.get("user_name", updated_by)
        log_activity(
            updated_by,
            user_name,
            "outreach_update",
            {
                "event_id": event_id,
                "old_status": old_status,
                "new_status": status,
                "notes": notes or "",
            },
        )
        return True
    except Exception as exc:
        st.error(f"Failed to save outreach status: {exc}")
        return False


# ── Cached read helpers ───────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def _load_raw_discharge_data() -> pd.DataFrame:
    """Load and normalize the raw discharge DataFrame. Do not call directly — use load_discharge_data_with_status()."""
    query = text("SELECT * FROM v_discharge_summary ORDER BY discharge_date DESC")

    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, parse_dates=["discharge_date"])

    df.columns = df.columns.str.replace("_", " ").str.title()

    for col in ["Admit Date", "Discharge Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.date

    if "Length Of Stay" in df.columns:
        df["Length Of Stay"] = pd.to_numeric(df["Length Of Stay"], errors="coerce").fillna(0).astype(int)

    return df


@st.cache_data(ttl=300)
def load_discharge_data_with_status() -> tuple[pd.DataFrame, dict]:
    """
    Load discharge data, load outreach statuses, and return the merged DataFrame
    plus the raw outreach dict (needed for detail panel lookups).

    Cached with a 300-second TTL. Any outreach upsert explicitly calls
    load_discharge_data_with_status.clear() so updates propagate immediately.
    """
    df = _load_raw_discharge_data()
    outreach = load_outreach_statuses()
    merged_df = _merge_outreach(df, outreach)
    return merged_df, outreach


@st.cache_data(ttl=300)
def load_outreach_statuses() -> dict:
    """
    Load all outreach_status rows. Returns a dict keyed on (event_id, discharge_date)
    -> {status, updated_by, updated_at, notes}.
    TTL is 300 seconds. Explicit .clear() calls after any upsert ensure immediate propagation.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT event_id, discharge_date, status, updated_by, updated_at, notes
                    FROM discharge_app.outreach_status
                    """
                )
            ).fetchall()
        result = {}
        for row in rows:
            key = (str(row[0]), row[1])  # (event_id, discharge_date as date object)
            result[key] = {
                "status": row[2],
                "updated_by": row[3],
                "updated_at": row[4],
                "notes": row[5] or "",
            }
        return result
    except Exception:
        return {}


@st.cache_data(ttl=300)
def load_practice_assignments() -> dict:
    """
    Query discharge_app.app_user and return a dict mapping
    display_name -> list[practice] for all active users who have practice assignments.
    Includes both staff and managers with assigned practices.
    """
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT display_name, practices
                FROM discharge_app.app_user
                WHERE is_active = TRUE AND array_length(practices, 1) > 0
                ORDER BY display_name
                """
            )
        ).fetchall()
    return {row[0]: list(row[1]) for row in rows}


@st.cache_data(ttl=300)
def load_all_staff_users() -> list[dict]:
    """
    Load all active staff users for manager view.
    Returns list of dicts: {user_email, display_name, practices}.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT user_email, display_name, practices
                    FROM discharge_app.app_user
                    WHERE is_active = TRUE AND role = 'staff'
                    ORDER BY display_name
                    """
                )
            ).fetchall()
        return [{"user_email": r[0], "display_name": r[1], "practices": list(r[2])} for r in rows]
    except Exception:
        return []


@st.cache_data(ttl=300)
def load_user_last_activity() -> dict:
    """
    For manager view: returns {user_email: {last_login, last_activity}} from activity log.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT DISTINCT ON (user_email)
                        user_email,
                        MAX(created_at) FILTER (WHERE action = 'login') OVER (PARTITION BY user_email) AS last_login,
                        MAX(created_at) OVER (PARTITION BY user_email) AS last_activity
                    FROM discharge_app.user_activity_log
                    ORDER BY user_email, last_activity DESC
                    """
                )
            ).fetchall()
        return {r[0]: {"last_login": r[1], "last_activity": r[2]} for r in rows}
    except Exception:
        return {}


@st.cache_data(ttl=300)
def get_user_role(email: str) -> str | None:
    """
    Look up the role for a given SSO email from discharge_app.app_user.
    Returns 'staff', 'manager', or None if the user is not found / inactive.
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT role FROM discharge_app.app_user
                WHERE user_email = :email AND is_active = TRUE
                """
            ),
            {"email": email},
        ).fetchone()
    return result[0] if result else None


# ── UI helpers ───────────────────────────────────────────────────────────────

def _logo_data_uri() -> str | None:
    """Return the Citadel logo as a base64-encoded PNG data URI, or None if the file is missing."""
    if not os.path.exists(LOGO_PATH):
        return None
    with open(LOGO_PATH, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def format_count(value: int) -> str:
    return f"{value:,}"


def stat_chip(label: str, value: str, orange: bool = False, green: bool = False, gray: bool = False) -> str:
    if orange:
        cls = "stat-chip orange"
    elif green:
        cls = "stat-chip green"
    elif gray:
        cls = "stat-chip gray"
    else:
        cls = "stat-chip"
    return (
        f"<div class='{cls}'>"
        f"<div class='chip-label'>{label}</div>"
        f"<div class='chip-value'>{value}</div>"
        f"</div>"
    )


def build_download_button(df: pd.DataFrame, label: str, key: str) -> None:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"⬇  {label}",
        data=csv_bytes,
        file_name=f"discharge_report_{datetime.now():%Y%m%d_%H%M%S}.csv",
        mime="text/csv",
        key=key,
    )


def render_header() -> None:
    # ── Logo above the header bar ──
    logo_uri = _logo_data_uri()
    if logo_uri:
        st.markdown(
            f'<div style="text-align:center;margin-top:0;margin-bottom:0.4rem;">'
            f'<img src="{logo_uri}" style="width:300px;height:auto;" alt="Citadel Health" />'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Welcome greeting (only when auth is on and a name is known) ──
    if _auth_enabled():
        user_name = st.session_state.get("user_name", "")
        if user_name:
            st.markdown(
                f"<div style='text-align:center;font-size:1.3rem;color:#556e81;margin-bottom:0.4rem;'>"
                f"Welcome, <span style='color:#132e45;font-weight:700;'>{user_name}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Header bar ──
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #132e45 0%, #1b4459 100%);
            border-radius: 14px;
            padding: 1.1rem 1.75rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 4px 18px rgba(19,46,69,0.18);
            position: relative;
            overflow: hidden;
        ">
            <div style="
                position:absolute; right:0; top:0; bottom:0; width:5px;
                background: linear-gradient(180deg, #e07b2a 0%, #c96920 100%);
                border-radius: 0 14px 14px 0;
            "></div>
            <div style="font-size:1.65rem;font-weight:800;color:#ffffff;line-height:1.15;letter-spacing:-0.5px;">
                Discharge Report Dashboard
            </div>
            <div style="color:#a8c4d8;font-size:0.82rem;margin-top:0.2rem;">
                Live discharge activity &mdash; filter, explore, and export.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_filters(df: pd.DataFrame, practice_assignments: dict):

    with st.sidebar:
        st.markdown("### Filters")

        assignee_names = sorted(practice_assignments.keys())
        selected_assignee = st.selectbox(
            "Assigned To",
            options=["All"] + assignee_names,
            help="Filter practices by assigned person.",
        )

        all_practices = sorted(df["Practice"].dropna().astype(str).unique())
        if selected_assignee != "All":
            assignee_practices = practice_assignments[selected_assignee]
            practices = sorted(p for p in all_practices if p in assignee_practices)
        else:
            practices = all_practices

        selected_practices = st.multiselect(
            "Practice",
            options=practices,
            help="Filter by practice. Leave empty to show all.",
        )

        payers = sorted(df["Payer Name"].dropna().astype(str).unique()) if "Payer Name" in df.columns else []
        selected_payers = st.multiselect(
            "Payer Name",
            options=payers,
            help="Filter by insurance payer.",
        ) if payers else []

        lob_options = sorted(df["Lob Name"].dropna().astype(str).unique()) if "Lob Name" in df.columns else []
        selected_lob = st.multiselect(
            "Line Of Business",
            options=lob_options,
            help="Filter by line of business.",
        ) if lob_options else []

        stay_types = sorted(df["Stay Type"].dropna().astype(str).unique()) if "Stay Type" in df.columns else []
        selected_stay_types = st.multiselect(
            "Stay Type",
            options=stay_types,
        ) if stay_types else []

        st.markdown("---")
        st.markdown("### Date Range")

        date_min_default = df["Discharge Date"].min()
        date_max_default = df["Discharge Date"].max()

        date_min = st.date_input(
            "From",
            value=date_min_default,
            min_value=date_min_default,
            max_value=date_max_default,
        )
        date_max = st.date_input(
            "Through",
            value=date_max_default,
            min_value=date_min_default,
            max_value=date_max_default,
        )

        st.markdown("---")
        if st.button("Clear All Filters", use_container_width=True):
            st.rerun()

        # ── Signed-in user + sign-out ──
        if _auth_enabled() and st.session_state.get("authenticated"):
            st.markdown("---")
            name = st.session_state.get("user_name", "")
            email = st.session_state.get("user_email", "")
            st.markdown(
                f"<div style='color:#a8c4d8;font-size:0.75rem;line-height:1.5;'>"
                f"Signed in as<br>"
                f"<span style='color:#ffffff;font-weight:700;'>{name}</span><br>"
                f"<span style='color:#7ea8c0;font-size:0.7rem;'>{email}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Sign Out", use_container_width=True):
                for key in ["authenticated", "user_email", "user_name", "user_role"]:
                    st.session_state.pop(key, None)
                st.rerun()

    return selected_assignee, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max


def apply_filters(df, selected_assignee, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max, practice_assignments: dict):
    mask = pd.Series(True, index=df.index)
    if selected_practices:
        mask &= df["Practice"].astype(str).isin(selected_practices)
    elif selected_assignee != "All":
        mask &= df["Practice"].astype(str).isin(practice_assignments.get(selected_assignee, []))
    if selected_payers and "Payer Name" in df.columns:
        mask &= df["Payer Name"].astype(str).isin(selected_payers)
    if selected_lob and "Lob Name" in df.columns:
        mask &= df["Lob Name"].astype(str).isin(selected_lob)
    if selected_stay_types and "Stay Type" in df.columns:
        mask &= df["Stay Type"].astype(str).isin(selected_stay_types)
    mask &= (df["Discharge Date"] >= date_min) & (df["Discharge Date"] <= date_max)
    return df.loc[mask]


def render_stats(view_df: pd.DataFrame) -> None:
    total = len(view_df)
    unique_patients = view_df["Insurance Member Id"].nunique() if "Insurance Member Id" in view_df.columns else total
    unique_practices = view_df["Practice"].nunique() if "Practice" in view_df.columns else "-"
    unique_hospitals = view_df["Discharge Hospital"].nunique() if "Discharge Hospital" in view_df.columns else "-"

    chips = (
        stat_chip("Total Records", format_count(total))
        + stat_chip("Unique Patients", format_count(unique_patients))
        + stat_chip("Practices", str(unique_practices), orange=True)
        + stat_chip("Hospitals", str(unique_hospitals))
    )
    st.markdown(f"<div class='stat-row'>{chips}</div>", unsafe_allow_html=True)


# ── Status display helpers ────────────────────────────────────────────────────

# Internal DB value -> display label
STATUS_DISPLAY = {
    "no_outreach": "No Outreach",
    "outreach_made": "Outreach Made",
    "outreach_complete": "Outreach Complete",
}

# Display label -> internal DB value
STATUS_DB = {v: k for k, v in STATUS_DISPLAY.items()}


def _merge_outreach(df: pd.DataFrame, outreach: dict) -> pd.DataFrame:
    """
    Add a 'Status' column to df by merging outreach_status dict.
    Keyed on (Event Id, Discharge Date).

    Uses a vectorized pandas merge instead of row-level .apply() for 10-50x
    faster execution on large datasets.
    """
    df = df.copy()

    if not outreach:
        df["Status"] = "No Outreach"
        return df

    # Build a lookup DataFrame from the outreach dict
    outreach_records = [
        {
            "Event Id": str(key[0]),
            "Discharge Date": key[1],
            "Status": STATUS_DISPLAY.get(val["status"], "No Outreach"),
        }
        for key, val in outreach.items()
    ]
    outreach_df = pd.DataFrame(outreach_records)

    # Ensure merge key types match
    df["Event Id"] = df["Event Id"].astype(str)

    merged = df.merge(outreach_df, on=["Event Id", "Discharge Date"], how="left")
    merged["Status"] = merged["Status"].fillna("No Outreach")
    return merged


def _status_pill_html(status_label: str) -> str:
    """Return an HTML pill badge for the given display-label status."""
    if status_label == "Outreach Made":
        return (
            '<span style="display:inline-flex;align-items:center;gap:5px;'
            'padding:0.2rem 0.6rem;border-radius:20px;font-size:0.74rem;font-weight:600;'
            'background:#fef3e2;color:#c05621;">'
            '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#e07b2a;"></span>'
            'Outreach Made</span>'
        )
    elif status_label == "Outreach Complete":
        return (
            '<span style="display:inline-flex;align-items:center;gap:5px;'
            'padding:0.2rem 0.6rem;border-radius:20px;font-size:0.74rem;font-weight:600;'
            'background:#e6ffed;color:#22753a;">'
            '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#38a169;"></span>'
            'Complete</span>'
        )
    else:
        return (
            '<span style="display:inline-flex;align-items:center;gap:5px;'
            'padding:0.2rem 0.6rem;border-radius:20px;font-size:0.74rem;font-weight:600;'
            'background:#edf2f7;color:#718096;">'
            '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#cbd5e0;"></span>'
            'No Outreach</span>'
        )


def render_detail_panel(row: pd.Series, outreach: dict, tab_key: str) -> None:
    """Render the detail panel for the selected discharge row."""
    event_id = str(row.get("Event Id", ""))
    discharge_date = row.get("Discharge Date")
    patient_name = str(row.get("Patient Name", ""))
    practice = str(row.get("Practice", ""))
    payer = str(row.get("Payer Name", ""))
    hospital = str(row.get("Discharge Hospital", ""))
    dx_code = str(row.get("Dx Code", ""))
    description = str(row.get("Description", ""))
    los = row.get("Length Of Stay", "")
    disposition = str(row.get("Disposition", ""))

    # Look up current outreach entry
    lookup_key = (event_id, discharge_date)
    entry = outreach.get(lookup_key, {})
    current_status_db = entry.get("status", "no_outreach")
    current_status_label = STATUS_DISPLAY.get(current_status_db, "No Outreach")
    current_notes = entry.get("notes", "")
    updated_by = entry.get("updated_by", "")
    updated_at = entry.get("updated_at")

    diagnosis_display = f"{dx_code} — {description}" if dx_code and dx_code != "nan" else (description if description != "nan" else "—")
    los_display = f"{los} day{'s' if int(los) != 1 else ''}" if los != "" and str(los) != "nan" else "—"
    discharge_date_str = discharge_date.strftime("%m/%d/%Y") if hasattr(discharge_date, "strftime") else str(discharge_date)

    # ── Panel header ──
    st.markdown(
        f"""
        <div class="detail-panel">
            <div class="detail-header">
                <h3>{patient_name} &mdash; Discharge {discharge_date_str}</h3>
            </div>
            <div class="detail-body">
                <div class="detail-grid">
                    <div class="detail-field">
                        <label>Practice</label>
                        <div class="value">{practice if practice != "nan" else "—"}</div>
                    </div>
                    <div class="detail-field">
                        <label>Payer</label>
                        <div class="value">{payer if payer != "nan" else "—"}</div>
                    </div>
                    <div class="detail-field">
                        <label>Hospital</label>
                        <div class="value">{hospital if hospital != "nan" else "—"}</div>
                    </div>
                    <div class="detail-field">
                        <label>Diagnosis</label>
                        <div class="value">{diagnosis_display}</div>
                    </div>
                    <div class="detail-field">
                        <label>Length of Stay</label>
                        <div class="value">{los_display}</div>
                    </div>
                    <div class="detail-field">
                        <label>Disposition</label>
                        <div class="value">{disposition if disposition != "nan" else "—"}</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Outreach status section (rendered with Streamlit widgets, outside the HTML block) ──
    st.markdown(
        "<div style='margin-top:1rem;padding:1.25rem;background:#fff;border-radius:0 0 12px 12px;"
        "border:1.5px solid #132e45;border-top:none;margin-top:-12px;'>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='font-size:0.85rem;font-weight:700;color:#132e45;margin-bottom:0.75rem;'>Update Outreach Status</div>",
        unsafe_allow_html=True,
    )

    # Session state key for the pending status selection in this panel
    sel_key = f"pending_status_{tab_key}"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = current_status_label

    # 3 status buttons
    btn_col1, btn_col2, btn_col3 = st.columns(3)

    def _btn_css(status_val: str) -> str:
        """Return the CSS class wrapper div for a status button."""
        is_active = st.session_state[sel_key] == status_val
        mapping = {
            "No Outreach": ("none-active" if is_active else "none"),
            "Outreach Made": ("made-active" if is_active else "made"),
            "Outreach Complete": ("complete-active" if is_active else "complete"),
        }
        return f"status-btn-{mapping[status_val]}"

    with btn_col1:
        st.markdown(f"<div class='{_btn_css('No Outreach')}'>", unsafe_allow_html=True)
        if st.button("No Outreach", key=f"btn_none_{tab_key}", use_container_width=True):
            st.session_state[sel_key] = "No Outreach"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with btn_col2:
        st.markdown(f"<div class='{_btn_css('Outreach Made')}'>", unsafe_allow_html=True)
        if st.button("Outreach Made", key=f"btn_made_{tab_key}", use_container_width=True):
            st.session_state[sel_key] = "Outreach Made"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with btn_col3:
        st.markdown(f"<div class='{_btn_css('Outreach Complete')}'>", unsafe_allow_html=True)
        if st.button("Outreach Complete", key=f"btn_complete_{tab_key}", use_container_width=True):
            st.session_state[sel_key] = "Outreach Complete"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)

    notes_val = st.text_area(
        "Notes",
        value=current_notes,
        placeholder="Add details about the outreach attempt...",
        key=f"notes_{tab_key}",
        height=80,
    )

    # Last updated line
    if updated_by and updated_at:
        if hasattr(updated_at, "strftime"):
            updated_str = updated_at.strftime("%m/%d/%Y at %I:%M %p")
        else:
            updated_str = str(updated_at)
        st.markdown(
            f"<div class='last-updated-line'>Last updated by <strong>{updated_by}</strong> on {updated_str}</div>",
            unsafe_allow_html=True,
        )

    # Save / Cancel buttons
    action_col1, action_col2, action_col3 = st.columns([1, 1, 4])
    with action_col1:
        if st.button("Save Status", key=f"save_{tab_key}", type="primary"):
            new_status_label = st.session_state[sel_key]
            new_status_db = STATUS_DB.get(new_status_label, "no_outreach")
            user_email = st.session_state.get("user_email", "unknown")
            success = upsert_outreach_status(
                event_id=event_id,
                discharge_date=discharge_date,
                status=new_status_db,
                updated_by=user_email,
                notes=notes_val,
                old_status=current_status_db,
            )
            if success:
                st.success(f"Status updated to '{new_status_label}' for {patient_name}.")
                # Clear the selected row so the panel closes after save
                row_key = f"selected_row_{tab_key}"
                if row_key in st.session_state:
                    del st.session_state[row_key]
                if sel_key in st.session_state:
                    del st.session_state[sel_key]
                # Full-page rerun so the table reflects the updated status
                st.rerun()

    with action_col2:
        if st.button("Cancel", key=f"cancel_{tab_key}"):
            row_key = f"selected_row_{tab_key}"
            if row_key in st.session_state:
                del st.session_state[row_key]
            if sel_key in st.session_state:
                del st.session_state[sel_key]
            # Full-page rerun so the panel closes and the table is visible again
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_tab(view_df: pd.DataFrame, label: str, tab_key: str, outreach: dict) -> None:
    count = len(view_df)
    st.markdown(
        f"<div class='tab-heading'>{label} <span class='record-badge'>{format_count(count)}</span></div>",
        unsafe_allow_html=True,
    )

    if view_df.empty:
        st.info("No records match the selected filters.")
        return

    render_stats(view_df)

    # ── Outreach legend ──
    st.markdown(
        """
        <div class="outreach-legend">
            <div class="legend-item"><span class="status-dot dot-none"></span> No Outreach</div>
            <div class="legend-item"><span class="status-dot dot-made"></span> Outreach Made</div>
            <div class="legend-item"><span class="status-dot dot-complete"></span> Outreach Complete</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Columns to display — hide Event Id but keep it in data for lookup
    display_cols = [
        "Patient Name", "Discharge Date", "Practice", "Payer Name",
        "Discharge Hospital", "Length Of Stay", "Disposition", "Status",
    ]
    # Only include columns that exist
    display_cols = [c for c in display_cols if c in view_df.columns]

    # Build column config: make Status column wider for readability
    col_config = {}
    if "Status" in display_cols:
        col_config["Status"] = st.column_config.TextColumn("Status", width="medium")
    if "Discharge Date" in display_cols:
        col_config["Discharge Date"] = st.column_config.DateColumn("Discharge Date", format="MM/DD/YYYY")
    if "Length Of Stay" in display_cols:
        col_config["Length Of Stay"] = st.column_config.NumberColumn("LOS (days)", format="%d")

    row_key = f"selected_row_{tab_key}"

    # Render selectable dataframe
    selection = st.dataframe(
        view_df[display_cols],
        use_container_width=True,
        height=400,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config=col_config,
        key=f"df_{tab_key}",
    )

    # Detect selected row
    selected_indices = selection.selection.rows if hasattr(selection, "selection") else []
    if selected_indices:
        idx = selected_indices[0]
        # Store in session state so panel persists across reruns from status buttons
        st.session_state[row_key] = idx

    selected_row_idx = st.session_state.get(row_key)

    if selected_row_idx is not None:
        try:
            row = view_df.iloc[selected_row_idx]
            render_detail_panel(row, outreach, tab_key)
        except IndexError:
            # Row index out of range (filter changed) — clear the selection
            if row_key in st.session_state:
                del st.session_state[row_key]

    build_download_button(view_df[display_cols], "Export to CSV", key=f"dl_{tab_key}")


# ── Manager dashboard ────────────────────────────────────────────────────────

def render_manager_dashboard(filtered_df: pd.DataFrame, outreach: dict) -> None:
    """Render the manager analytics dashboard tab."""

    st.markdown(
        "<div class='tab-heading'>Manager Dashboard</div>",
        unsafe_allow_html=True,
    )

    if filtered_df.empty:
        st.info("No discharge records match the current filters.")
        return

    # Compute status counts for the filtered dataset
    total = len(filtered_df)
    status_counts = filtered_df["Status"].value_counts() if "Status" in filtered_df.columns else pd.Series(dtype=int)
    n_no_outreach = int(status_counts.get("No Outreach", 0))
    n_made = int(status_counts.get("Outreach Made", 0))
    n_complete = int(status_counts.get("Outreach Complete", 0))
    pct_complete = f"{(n_complete / total * 100):.1f}%" if total > 0 else "0%"

    # ── Summary stat chips ──
    chips = (
        stat_chip("Total Discharges", format_count(total))
        + stat_chip("No Outreach", format_count(n_no_outreach), gray=True)
        + stat_chip("Outreach Made", format_count(n_made), orange=True)
        + stat_chip("Complete", format_count(n_complete), green=True)
        + stat_chip("% Complete", pct_complete, green=True)
    )
    st.markdown(f"<div class='stat-row'>{chips}</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Per-user breakdown ──
    st.markdown(
        "<div style='font-size:0.9rem;font-weight:700;color:#132e45;margin-bottom:0.75rem;'>Staff Outreach Breakdown</div>",
        unsafe_allow_html=True,
    )

    staff_users = load_all_staff_users()
    activity = load_user_last_activity()
    practice_assignments = load_practice_assignments()

    if staff_users:
        rows_html = ""
        for user in staff_users:
            email = user["user_email"]
            name = user["display_name"]
            practices = user["practices"]
            practice_count = len(practices)

            # Filter discharge rows assigned to this user's practices
            if practices:
                user_df = filtered_df[filtered_df["Practice"].astype(str).isin(practices)]
            else:
                user_df = filtered_df.iloc[0:0]  # empty

            user_total = len(user_df)
            user_counts = user_df["Status"].value_counts() if "Status" in user_df.columns else pd.Series(dtype=int)
            u_none = int(user_counts.get("No Outreach", 0))
            u_made = int(user_counts.get("Outreach Made", 0))
            u_complete = int(user_counts.get("Outreach Complete", 0))
            u_pct = f"{(u_complete / user_total * 100):.0f}%" if user_total > 0 else "—"

            act = activity.get(email, {})
            last_login = act.get("last_login")
            last_activity = act.get("last_activity")
            last_login_str = last_login.strftime("%m/%d/%Y") if last_login and hasattr(last_login, "strftime") else "—"
            last_act_str = last_activity.strftime("%m/%d/%Y") if last_activity and hasattr(last_activity, "strftime") else "—"

            rows_html += (
                f"<tr>"
                f"<td><strong>{name}</strong></td>"
                f"<td>{practice_count}</td>"
                f"<td>{user_total:,}</td>"
                f"<td>{u_none:,}</td>"
                f"<td>{u_made:,}</td>"
                f"<td>{u_complete:,}</td>"
                f"<td><strong>{u_pct}</strong></td>"
                f"<td>{last_login_str}</td>"
                f"<td>{last_act_str}</td>"
                f"</tr>"
            )

        st.markdown(
            f"""
            <table class="manager-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Practices</th>
                        <th>Total</th>
                        <th>No Outreach</th>
                        <th>Made</th>
                        <th>Complete</th>
                        <th>% Done</th>
                        <th>Last Login</th>
                        <th>Last Activity</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No staff users found.")

    # ── Practice roll-up ──
    st.markdown(
        "<div style='font-size:0.9rem;font-weight:700;color:#132e45;margin-bottom:0.75rem;margin-top:1.5rem;'>Practice Roll-Up</div>",
        unsafe_allow_html=True,
    )

    if "Practice" in filtered_df.columns and "Status" in filtered_df.columns:
        practice_group = (
            filtered_df.groupby("Practice")["Status"]
            .value_counts()
            .unstack(fill_value=0)
            .reset_index()
        )

        # Ensure all status columns exist
        for col in ["No Outreach", "Outreach Made", "Outreach Complete"]:
            if col not in practice_group.columns:
                practice_group[col] = 0

        practice_group["Total"] = (
            practice_group["No Outreach"]
            + practice_group["Outreach Made"]
            + practice_group["Outreach Complete"]
        )
        practice_group["% Complete"] = practice_group.apply(
            lambda r: f"{(r['Outreach Complete'] / r['Total'] * 100):.0f}%" if r["Total"] > 0 else "—",
            axis=1,
        )
        practice_group = practice_group.sort_values("Total", ascending=False)

        rows_html = ""
        for _, r in practice_group.iterrows():
            rows_html += (
                f"<tr>"
                f"<td>{r['Practice']}</td>"
                f"<td>{int(r['Total']):,}</td>"
                f"<td>{int(r['No Outreach']):,}</td>"
                f"<td>{int(r['Outreach Made']):,}</td>"
                f"<td>{int(r['Outreach Complete']):,}</td>"
                f"<td><strong>{r['% Complete']}</strong></td>"
                f"</tr>"
            )

        st.markdown(
            f"""
            <table class="manager-table">
                <thead>
                    <tr>
                        <th>Practice</th>
                        <th>Total</th>
                        <th>No Outreach</th>
                        <th>Made</th>
                        <th>Complete</th>
                        <th>% Done</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            """,
            unsafe_allow_html=True,
        )


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    render_header()

    with st.spinner("Loading discharge data..."):
        try:
            df, outreach = load_discharge_data_with_status()
        except Exception as exc:
            st.error(f"Could not load discharge data: {exc}")
            st.info(
                "Configure `DATABASE_URL` in `.streamlit/secrets.toml` or as an environment variable and try again."
            )
            return

    if df.empty:
        st.warning("No discharge records found.")
        return

    # Load practice assignments once and pass to both sidebar and filter functions
    practice_assignments = load_practice_assignments()

    selected_assignee, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max = render_sidebar_filters(df, practice_assignments)
    filtered_df = apply_filters(df, selected_assignee, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max, practice_assignments)

    recent_cutoff = datetime.now().date() - timedelta(days=14)
    six_months_cutoff = datetime.now().date() - timedelta(days=182)

    is_manager = st.session_state.get("user_role") == "manager"

    if is_manager:
        tabs = st.tabs(["Recent Discharges", "Last 6 Months", "All Discharges", "Manager Dashboard"])
    else:
        tabs = st.tabs(["Recent Discharges", "Last 6 Months", "All Discharges"])

    with tabs[0]:
        view = filtered_df[filtered_df["Discharge Date"] >= recent_cutoff]
        render_tab(view, "Recent Discharges (Last 14 Days)", "recent", outreach)

    with tabs[1]:
        view = filtered_df[filtered_df["Discharge Date"] >= six_months_cutoff]
        render_tab(view, "Last 6 Months", "six_months", outreach)

    with tabs[2]:
        render_tab(filtered_df, "All Discharges", "all", outreach)

    if is_manager:
        with tabs[3]:
            render_manager_dashboard(filtered_df, outreach)

    st.markdown(
        "<div class='citadel-footer'>Citadel Health &mdash; Discharge Report Dashboard &mdash; "
        "Data refreshes every 5 minutes. Use sidebar filters to refine the report view.</div>",
        unsafe_allow_html=True,
    )


if check_auth():
    main()
