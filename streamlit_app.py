import os
from datetime import datetime, timedelta

import msal
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

LOGO_PATH = r"c:\Users\rcruz\Documents\discharge_report_automation\citadel-logo-hd-transparent.png"

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

    # Centre the card
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=220)
        else:
            st.markdown(
                "<h2 style='color:#132e45;font-weight:900;'>Citadel Health</h2>",
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg,#132e45 0%,#1b4459 100%);
                border-radius:16px; padding:2rem 2rem 1.75rem;
                box-shadow:0 6px 28px rgba(19,46,69,0.22);
                margin-top:1.25rem;
            ">
                <div style="color:#ffffff;font-size:1.35rem;font-weight:800;margin-bottom:0.35rem;">
                    Discharge Report Dashboard
                </div>
                <div style="color:#a8c4d8;font-size:0.88rem;margin-bottom:1.75rem;">
                    Sign in with your Citadel Health Microsoft account to continue.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        auth_url = _build_auth_url()
        st.markdown(
            f"""
            <a href="{auth_url}" target="_self" style="
                display:block; text-align:center;
                background:#e07b2a; color:#fff;
                font-weight:700; font-size:0.95rem;
                padding:0.75rem 1.5rem; border-radius:9px;
                text-decoration:none; margin-top:1rem;
                box-shadow:0 2px 8px rgba(224,123,42,0.35);
            ">
                Sign in with Microsoft
            </a>
            """,
            unsafe_allow_html=True,
        )

        domains = _allowed_domains()
        if domains:
            st.markdown(
                f"<div style='color:#7e96a6;font-size:0.75rem;text-align:center;margin-top:1rem;'>"
                f"Access restricted to: {', '.join('@' + d for d in domains)}"
                f"</div>",
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
            insurance_member_id, patient_id, patient_full_name, birth_date, age,
            phone, payer, line_of_business, admit_date, discharge_date,
            dx_code, dx_desc, disposition, stay_type, discharge_hospital,
            provider_full_name, provider_npi, attributed_tin, practice_name
        FROM discharge_master
        WHERE discharge_date IS NOT NULL
        ORDER BY discharge_date DESC
        """
    )

    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, parse_dates=["discharge_date"])

    df.columns = df.columns.str.replace("_", " ").str.title()

    for col in ["Admit Date", "Discharge Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.date

    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(0).astype(int)
    if "Provider Npi" in df.columns:
        df["Provider Npi"] = pd.to_numeric(df["Provider Npi"], errors="coerce").fillna(0).astype(int)
    if "Attributed Tin" in df.columns:
        df["Attributed Tin"] = pd.to_numeric(df["Attributed Tin"], errors="coerce").fillna(0).astype(int)

    return df


# ── UI helpers ───────────────────────────────────────────────────────────────

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
    with st.container():
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #132e45 0%, #1b4459 100%);
                border-radius: 14px;
                padding: 1.25rem 1.75rem;
                margin-bottom: 1.25rem;
                box-shadow: 0 4px 18px rgba(19,46,69,0.18);
            ">
                <div style="font-size:0.8rem; color:#a8c4d8; margin-bottom:0.15rem; letter-spacing:0.04em;">
                    CITADEL HEALTH
                </div>
                <div style="font-size:1.7rem; font-weight:800; color:#ffffff; line-height:1.2; margin-bottom:0.25rem;">
                    Discharge Report Dashboard
                </div>
                <div style="color:#a8c4d8; font-size:0.88rem;">
                    Live report view for discharge activity &mdash; filter, explore, and export.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if os.path.exists(LOGO_PATH):
        pass  # logo rendered in sidebar instead


def render_sidebar_filters(df: pd.DataFrame):
    with st.sidebar:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        else:
            st.markdown(
                "<div style='font-size:1.1rem;font-weight:900;color:#fff;margin-bottom:0.5rem;'>Citadel Health</div>",
                unsafe_allow_html=True,
            )
        st.markdown("### Filters")

        practices = sorted(df["Practice Name"].dropna().astype(str).unique())
        selected_practices = st.multiselect(
            "Practice Name",
            options=practices,
            help="Filter by practice. Leave empty to show all.",
        )

        payers = sorted(df["Payer"].dropna().astype(str).unique()) if "Payer" in df.columns else []
        selected_payers = st.multiselect(
            "Payer",
            options=payers,
            help="Filter by insurance payer.",
        ) if payers else []

        lob_options = sorted(df["Line Of Business"].dropna().astype(str).unique()) if "Line Of Business" in df.columns else []
        selected_lob = st.multiselect(
            "Line of Business",
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

    return selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max


def apply_filters(df, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max):
    filtered = df.copy()
    if selected_practices:
        filtered = filtered[filtered["Practice Name"].astype(str).isin(selected_practices)]
    if selected_payers and "Payer" in filtered.columns:
        filtered = filtered[filtered["Payer"].astype(str).isin(selected_payers)]
    if selected_lob and "Line Of Business" in filtered.columns:
        filtered = filtered[filtered["Line Of Business"].astype(str).isin(selected_lob)]
    if selected_stay_types and "Stay Type" in filtered.columns:
        filtered = filtered[filtered["Stay Type"].astype(str).isin(selected_stay_types)]
    filtered = filtered.loc[
        (filtered["Discharge Date"] >= date_min) & (filtered["Discharge Date"] <= date_max)
    ]
    return filtered


def render_stats(view_df: pd.DataFrame) -> None:
    total = len(view_df)
    unique_patients = view_df["Patient Id"].nunique() if "Patient Id" in view_df.columns else total
    unique_practices = view_df["Practice Name"].nunique() if "Practice Name" in view_df.columns else "-"
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

    selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max = render_sidebar_filters(df)
    filtered_df = apply_filters(df, selected_practices, selected_payers, selected_lob, selected_stay_types, date_min, date_max)

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
