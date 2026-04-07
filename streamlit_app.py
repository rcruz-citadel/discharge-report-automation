import os
from datetime import datetime, timedelta

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


if __name__ == "__main__":
    main()
