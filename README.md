# Discharge Report Automation Dashboard

This Streamlit app shows discharge records from `discharge_master` and provides tabs for recent and 6-month discharge views.

## Run locally

1. Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`.
2. Set `DATABASE_URL` to your PostgreSQL connection string.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the app:

```bash
streamlit run streamlit_app.py
```

## Features

- Recent discharges (last 14 days)
- Last 6 months of discharges
- Filter by facility
- Download current view as CSV
- Sortable table view in Streamlit
