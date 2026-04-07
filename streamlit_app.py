import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

LOGO_PATH = r"c:\Users\rcruz\Documents\dcm-dashboard\assets\citadel_logo.png"

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
    .stApp {
        background-color: #f7f8fb;
    }
    .report-title {
        font-size: 2rem;
        font-weight: 700;
        color: #132e45;
        margin-bottom: 0.1rem;
    }
    .report-subtitle {
        color: #556e81;
        margin-top: 0;
        margin-bottom: 1rem;
    }
    .section-card {
        background: #ffffff;
        border: 1px solid #dde2e7;
        border-radius: 14px;
        padding: 1rem;
    }
    .metric-label {
        color: #667784;
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #14263b;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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

    if "discharge_date" in df.columns:
        df["discharge_date"] = pd.to_datetime(df["discharge_date"])
    
    # Format integer columns - handle float->int conversion
    if "age" in df.columns:
        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(0).astype(int)
    if "provider_npi" in df.columns:
        df["provider_npi"] = pd.to_numeric(df["provider_npi"], errors="coerce").fillna(0).astype(int)
    if "attributed_tin" in df.columns:
        df["attributed_tin"] = pd.to_numeric(df["attributed_tin"], errors="coerce").fillna(0).astype(int)
    
    # Clean up column headers - replace underscores with spaces
    df.columns = df.columns.str.replace("_", " ").str.title()
    
    return df


def format_count(value: int) -> str:
    return f"{value:,}"


def build_download_button(df: pd.DataFrame, label: str, key: str) -> None:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=f"discharge_report_{datetime.now():%Y%m%d_%H%M%S}.csv",
        mime="text/csv",
        key=key,
    )


def main():
    logo_col, title_col = st.columns([1, 4], gap="small")
    with logo_col:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=110)
        else:
            st.markdown(
                "<div style='font-size:1rem; font-weight:700; color:#132e45;'>Citadel Health</div>",
                unsafe_allow_html=True,
            )

    with title_col:
        st.markdown(
            "<div class='report-title'>Discharge Report Dashboard</div>"
            "<div class='report-subtitle'>Live report view for discharge activity, filters, and downloads.</div>",
            unsafe_allow_html=True,
        )

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

    dashboard_start = df["Discharge Date"].min().date()
    dashboard_end = df["Discharge Date"].max().date()

    practices = sorted(df["Practice Name"].dropna().astype(str).unique())
    selected_practices = st.multiselect(
        "Filter by practice",
        options=practices,
        help="Choose one or more practices to limit the report view. Leave empty to show all.",
    )

    with st.expander("Advanced filters", expanded=False):
        date_min = st.date_input(
            "From discharge date",
            value=dashboard_start,
            min_value=dashboard_start,
            max_value=dashboard_end,
        )
        date_max = st.date_input(
            "Through discharge date",
            value=dashboard_end,
            min_value=dashboard_start,
            max_value=dashboard_end,
        )

    filtered_df = df.copy()
    if selected_practices:
        filtered_df = filtered_df[filtered_df["Practice Name"].astype(str).isin(selected_practices)]
    filtered_df = filtered_df.loc[
        (filtered_df["Discharge Date"].dt.date >= date_min)
        & (filtered_df["Discharge Date"].dt.date <= date_max)
    ]

    recent_cutoff = datetime.now().date() - timedelta(days=14)
    six_months_cutoff = datetime.now().date() - timedelta(days=182)

    tabs = st.tabs(["Recent Discharges", "Last 6 Months", "All Discharges"])

    tab_filters = [
        (tabs[0], recent_cutoff, None, "Recent Discharges"),
        (tabs[1], six_months_cutoff, None, "Last 6 Months"),
        (tabs[2], dashboard_start, dashboard_end, "All Discharges"),
    ]

    for tab, start_date, end_date, label in tab_filters:
        with tab:
            view_df = filtered_df.copy()
            view_df = view_df[view_df["Discharge Date"].dt.date >= start_date]
            if end_date is not None:
                view_df = view_df[view_df["Discharge Date"].dt.date <= end_date]

            count = len(view_df)
            unique_hospitals = view_df["Discharge Hospital"].nunique()
            latest = view_df["Discharge Date"].max()

            st.markdown(
                f"### {label} — {format_count(count)} records"
            )
            cols = st.columns([1, 1, 1, 2])
            cols[0].markdown("<div class='metric-label'>Rows</div><div class='metric-value'>{count:,}</div>", unsafe_allow_html=True)
            cols[1].markdown(
                f"<div class='metric-label'>Hospitals</div><div class='metric-value'>{unique_hospitals:,}</div>",
                unsafe_allow_html=True,
            )
            cols[2].markdown(
                f"<div class='metric-label'>Latest discharge</div><div class='metric-value'>{latest.date() if pd.notna(latest) else '—'}</div>",
                unsafe_allow_html=True,
            )
            cols[3].markdown(
                f"<div class='metric-label'>Date range</div><div class='metric-value'>{start_date} to {datetime.now().date()}</div>",
                unsafe_allow_html=True,
            )

            if view_df.empty:
                st.info("No records match the selected filters.")
                continue

            view_df = view_df.sort_values(by="Discharge Date", ascending=False)
            st.dataframe(view_df, use_container_width=True, height=650)
            build_download_button(view_df, "Download Current View as CSV", key=f"download_{label.replace(' ', '_').lower()}")

    st.markdown(
        "---\n"
        "#### Notes\n"
        "Use the facility selector and date filters to refine the report. "
        "Each tab shows a filtered view of the same underlying discharge data."
    )


if __name__ == "__main__":
    main()
