"""Sidebar components for file selection and downloads."""
import streamlit as st
import pandas as pd
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import SERVICES
from utils.audit_log import log_event

ALLOW_FILE_UPLOAD = os.environ.get("ALLOW_FILE_UPLOAD", "").lower() == "true"


def _log_download(dataset: str, fmt: str, rows: int) -> None:
    log_event("data_exported", dataset=dataset, format=fmt, rows=rows)


def display_data_source_selector(input_dir):
    """Display data source selector and return selection details.

    Returns a dict with keys:
      source: 'file' | 'opensearch'
      selected_file: filename (file source only)
      services: list of {name, url, index} dicts (opensearch source only)
      date_range: (start_date, end_date) or None (opensearch source only)
      load: True when the user clicked Load
    """
    st.sidebar.header("Data Source")

    if ALLOW_FILE_UPLOAD:
        source = st.sidebar.radio("Source", options=['File', 'OpenSearch'], label_visibility='collapsed')
    else:
        source = 'OpenSearch'

    if source == 'File':
        available_files = [
            f for f in os.listdir(input_dir)
            if f.endswith(('.xlsx', '.csv')) and not f.startswith('~$')
        ]

        if not available_files:
            st.error(f"No Excel or CSV files found in the '{input_dir}/' directory.")
            st.info(f"Please add your data files to the '{input_dir}/' directory and refresh the page.")
            st.stop()

        selected_file = st.sidebar.selectbox("Select a data file", available_files,
                                             help="Choose a log file to analyse")
        service_name = st.sidebar.radio("Service", options=[svc['name'] for svc in SERVICES],
                                        help="Which service does this log file belong to?")
        load = st.sidebar.button("Load Data", type="primary")
        return {'source': 'file', 'selected_file': selected_file, 'service_name': service_name, 'load': load}

    st.sidebar.markdown("**Service connections**")
    configured_services = []
    for svc in SERVICES:
        default = os.environ.get(svc['url_env'], svc['default_url'])
        url = st.sidebar.text_input(
            svc['name'], value=default,
            placeholder="http://... (leave blank to skip)",
            help=f"kubectl port-forward -n {svc['namespace']} svc/<proxy-svc> 8080:8080"
        )
        if url.strip():
            configured_services.append({'name': svc['name'], 'url': url.strip(), 'index': svc['index']})

    st.sidebar.markdown("**Date range** (optional)")
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("From", value=None, label_visibility='collapsed')
    end_date = col2.date_input("To", value=None, label_visibility='collapsed')

    date_range = (start_date, end_date) if (start_date or end_date) else None
    load = st.sidebar.button("Fetch from OpenSearch", type="primary")

    return {
        'source': 'opensearch',
        'services': configured_services,
        'date_range': date_range,
        'load': load,
    }


def display_date_filter(page_visits):
    """Display date range filter and return filtered page_visits."""
    if page_visits.empty or 'timestamp' not in page_visits.columns:
        return page_visits

    st.sidebar.header("Filters")
    min_date = page_visits['timestamp'].min().date()
    max_date = page_visits['timestamp'].max().date()

    date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date),
                                       min_value=min_date, max_value=max_date)

    if len(date_range) == 2:
        mask = (
            (page_visits['timestamp'].dt.date >= date_range[0]) &
            (page_visits['timestamp'].dt.date <= date_range[1])
        )
        return page_visits[mask]

    return page_visits


def display_download_section(df, weekly_summary, completion_rate, page_visits,
                             per_page_completion, funnel_data, selected_file, create_excel_download):
    """Display download buttons in sidebar."""
    st.sidebar.header("📥 Download Data")
    st.sidebar.subheader("CSV Downloads")

    base_name = selected_file.split('.')[0]

    csv_downloads = [
        ("📄 Download Parsed Data (CSV)", df, f"parsed_data_{base_name}.csv", "parsed_data"),
        ("📅 Download Weekly Summary (CSV)", weekly_summary, f"weekly_summary_{base_name}.csv", "weekly_summary"),
        ("✅ Download Completion Rates (CSV)", completion_rate, f"completion_rate_{base_name}.csv", "completion_rate"),
        ("🔍 Download Page Visits (CSV)", page_visits, f"page_visits_{base_name}.csv", "page_visits"),
    ]

    for label, data_df, filename, dataset in csv_downloads:
        if not data_df.empty:
            st.sidebar.download_button(
                label=label,
                data=data_df.to_csv(index=False).encode('utf-8'),
                file_name=filename,
                mime="text/csv",
                width='stretch',
                on_click=_log_download,
                args=(dataset, "csv", len(data_df)),
            )

    st.sidebar.subheader("Excel Download (All Data)")

    event_frames = {
        event: df[df['event_type'] == event].copy() if 'event_type' in df.columns else pd.DataFrame()
        for event in ('link_click', 'page_exit', 'quick_exit', 'download')
    }

    all_data = {
        'Parsed Data':       df,
        'Page Visits':       page_visits,
        'Link Clicks':       event_frames['link_click'],
        'Page Exits':        event_frames['page_exit'],
        'Quick Exits':       event_frames['quick_exit'],
        'Downloads':         event_frames['download'],
        'Weekly Summary':    weekly_summary,
        'Completion Rate':   completion_rate,
        'Per Page Completion': per_page_completion,
        'Funnel Data':       funnel_data,
    }

    excel_file = create_excel_download(all_data)

    st.sidebar.download_button(
        label="📊 Download All Data (Excel)",
        data=excel_file,
        file_name=f"cap_analytics_all_data_{base_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width='stretch',
        help="Downloads all data including event types in a single Excel file with multiple sheets",
        on_click=_log_download,
        args=("all_data", "xlsx", len(df)),
    )
