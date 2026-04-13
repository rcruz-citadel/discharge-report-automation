import base64
import os
from datetime import datetime, timedelta

import msal
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "citadel-logo-hd-transparent.png")

# Person-to-practice assignments (drives the "Assigned To" sidebar filter)
PRACTICE_ASSIGNMENTS = {
    "Bailey Graham": [
        "All Care Medical Assocociates, LLC",
        "D. Conrad Harper, MD LLC",
        "Dawsonville Family Medicine",
        "Donald A Selph Jr MD, PC",
        "Dr. Jason R. Laney, PC",
        "Heart of Georgia Primary Care, LLC",
        "Internal Medicine Associates of Middle Georgia, PC",
        "Margaret M. Nichols MD LLC",
        "Medical Center, LLP",
        "Moon River Pediatrics",
        "Nicholas A. Pietrzak MD, LLC",
        "Russell G. O'Neal, M.D. LLC",
    ],
    "Kiah Jones": [
        "Cobb Medical Clinic",
        "Cumberland Womens Health Center",
        "HP Internal Medicine, LLC",
        "Lawrenceville Family Practice",
        "Northeast Family Practice, PC",
        "Rodriguez MD, LLC",
        "Rophe Adult and Pediatric Medicine",
    ],
    "Makeba Crawford": [
        "Aylo Health, LLC",
    ],
    "Stephanie Nelson": [
        "Ajay Kumar MD, LLC",
        "Cornerstone Medical Associates, LLC",
        "Integrity Health and Wellness LLC",
        "Internal Medicine Associates of Waycross",
        "Internal Medicine Associates, PC",
        "Lawrence Kirk MD, LLC",
        "MCC Internal Medicine 2, LLC",
        "MCC Internal Medicine, LLC",
        "Robert C. Jones, MD, LLC",
        "Smith-Lambert Clinic, P.C.",
        "Southeast Georgia Pediatrics",
    ],
}

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
        st.session_state["user_email"] = email
        st.session_state["user_name"] = name
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
        padding-top: 0.75rem !important;
    }

    /* ── Remove default top padding from sidebar ── */
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.25rem !important;
    }
    section[data-testid="stSidebar"] .stMarkdown:first-child {
        margin-top: 0 !important;
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


@st.cache_data(ttl=300)
def load_discharge_data():
    query = text(
        """
        SELECT
            de.patient_id,
            COALESCE(pt.first_name, '') || ' ' || COALESCE(pt.last_name, '') AS patient_name,
            de.admit_date,
            de.discharge_date,
            de.disposition,
            de.stay_type,
            de.discharge_hospital,
            de.length_of_stay,
            py.payer_name,
            lob.lob_name,
            p.full_name AS provider_name,
            l.parent_org AS practice,
            d.dx_code,
            d.description,
            d.dx_grouping,
            pt.address AS patient_address,
            pt.city,
            pt.zip_code::character varying(5) AS zip_code,
            pt.state
        FROM discharge_event de
            LEFT JOIN provider p ON p.provider_id = de.provider_id
            LEFT JOIN payer py ON py.payer_id = de.payer_id
            LEFT JOIN line_of_business lob ON lob.lob_id = de.lob_id
            LEFT JOIN patient pt ON pt.patient_id = de.patient_id
            LEFT JOIN diagnosis_code d ON d.dx_id = de.dx_id
            LEFT JOIN location l ON l.location_id = p.location_id
        WHERE de.discharge_date IS NOT NULL
        ORDER BY de.discharge_date DESC
        """
    )

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


def stat_chip(label: str, value: str, orange: bool = False) -> str:
    cls = "stat-chip orange" if orange else "stat-chip"
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


def render_sidebar_filters(df: pd.DataFrame):
    with st.sidebar:
        st.markdown("### Filters")

        assignee_names = sorted(PRACTICE_ASSIGNMENTS.keys())
        selected_assignee = st.selectbox(
            "Assigned To",
            options=["All"] + assignee_names,
            help="Filter practices by assigned person.",
        )

        all_practices = sorted(df["Practice"].dropna().astype(str).unique())
        if selected_assignee != "All":
            assignee_practices = PRACTICE_ASSIGNMENTS[selected_assignee]
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
                for key in ["authenticated", "user_email", "user_name"]:
                    st.session_state.pop(key, None)
                st.rerun()

    return selected_assignee, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max


def apply_filters(df, selected_assignee, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max):
    filtered = df.copy()
    if selected_practices:
        filtered = filtered[filtered["Practice"].astype(str).isin(selected_practices)]
    elif selected_assignee != "All":
        filtered = filtered[filtered["Practice"].astype(str).isin(PRACTICE_ASSIGNMENTS[selected_assignee])]
    if selected_payers and "Payer Name" in filtered.columns:
        filtered = filtered[filtered["Payer Name"].astype(str).isin(selected_payers)]
    if selected_lob and "Lob Name" in filtered.columns:
        filtered = filtered[filtered["Lob Name"].astype(str).isin(selected_lob)]
    if selected_stay_types and "Stay Type" in filtered.columns:
        filtered = filtered[filtered["Stay Type"].astype(str).isin(selected_stay_types)]
    filtered = filtered.loc[
        (filtered["Discharge Date"] >= date_min) & (filtered["Discharge Date"] <= date_max)
    ]
    return filtered


def render_stats(view_df: pd.DataFrame) -> None:
    total = len(view_df)
    unique_patients = view_df["Patient Id"].nunique() if "Patient Id" in view_df.columns else total
    unique_practices = view_df["Practice"].nunique() if "Practice" in view_df.columns else "-"
    unique_hospitals = view_df["Discharge Hospital"].nunique() if "Discharge Hospital" in view_df.columns else "-"

    chips = (
        stat_chip("Total Records", format_count(total))
        + stat_chip("Unique Patients", format_count(unique_patients))
        + stat_chip("Practices", str(unique_practices), orange=True)
        + stat_chip("Hospitals", str(unique_hospitals))
    )
    st.markdown(f"<div class='stat-row'>{chips}</div>", unsafe_allow_html=True)


def render_tab(view_df: pd.DataFrame, label: str, tab_key: str) -> None:
    count = len(view_df)
    st.markdown(
        f"<div class='tab-heading'>{label} <span class='record-badge'>{format_count(count)}</span></div>",
        unsafe_allow_html=True,
    )

    if view_df.empty:
        st.info("No records match the selected filters.")
        return

    render_stats(view_df)

    sorted_df = view_df.sort_values(by="Discharge Date", ascending=False)
    st.dataframe(sorted_df, use_container_width=True, height=580, hide_index=True)

    build_download_button(sorted_df, "Export to CSV", key=f"dl_{tab_key}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    render_header()

    with st.spinner("Loading discharge data..."):
        try:
            df = load_discharge_data()
        except Exception as exc:
            st.error(f"Could not load discharge data: {exc}")
            st.info(
                "Configure `DATABASE_URL` in `.streamlit/secrets.toml` or as an environment variable and try again."
            )
            return

    if df.empty:
        st.warning("No discharge records found.")
        return

    selected_assignee, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max = render_sidebar_filters(df)
    filtered_df = apply_filters(df, selected_assignee, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max)

    recent_cutoff = datetime.now().date() - timedelta(days=14)
    six_months_cutoff = datetime.now().date() - timedelta(days=182)

    tabs = st.tabs(["Recent Discharges", "Last 6 Months", "All Discharges"])

    with tabs[0]:
        view = filtered_df[filtered_df["Discharge Date"] >= recent_cutoff]
        render_tab(view, "Recent Discharges (Last 14 Days)", "recent")

    with tabs[1]:
        view = filtered_df[filtered_df["Discharge Date"] >= six_months_cutoff]
        render_tab(view, "Last 6 Months", "six_months")

    with tabs[2]:
        render_tab(filtered_df, "All Discharges", "all")

    st.markdown(
        "<div class='citadel-footer'>Citadel Health &mdash; Discharge Report Dashboard &mdash; "
        "Data refreshes every 5 minutes. Use sidebar filters to refine the report view.</div>",
        unsafe_allow_html=True,
    )


if check_auth():
    main()
