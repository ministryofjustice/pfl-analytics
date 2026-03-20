"""Sidebar components for file selection and downloads."""
import streamlit as st
import pandas as pd
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import SERVICES


def display_data_source_selector(input_dir):
    """Display data source selector (File or OpenSearch) and return selection details.

    Returns a dict with keys:
      source: 'file' | 'opensearch'
      selected_file: filename (file source only)
      services: list of {name, url, index} for services with a URL entered (opensearch source only)
      date_range: (start_date, end_date) tuple or None (opensearch source only)
      load: True when the user clicked Load
    """
    st.sidebar.header("Data Source")

    source = st.sidebar.radio(
        "Source",
        options=['File', 'OpenSearch'],
        label_visibility='collapsed'
    )

    if source == 'File':
        available_files = [
            f for f in os.listdir(input_dir)
            if f.endswith(('.xlsx', '.csv')) and not f.startswith('~$')
        ]

        if not available_files:
            st.error(f"No Excel or CSV files found in the '{input_dir}/' directory.")
            st.info(f"Please add your data files to the '{input_dir}/' directory and refresh the page.")
            st.stop()

        selected_file = st.sidebar.selectbox(
            "Select a data file",
            available_files,
            help="Choose a log file to analyse"
        )

        service_name = st.sidebar.radio(
            "Service",
            options=[svc['name'] for svc in SERVICES],
            help="Which service does this log file belong to?"
        )

        load = st.sidebar.button("Load Data", type="primary")
        return {'source': 'file', 'selected_file': selected_file, 'service_name': service_name, 'load': load}

    else:  # OpenSearch
        st.sidebar.markdown("**Service connections**")
        configured_services = []
        for svc in SERVICES:
            default = os.environ.get(svc['url_env'], svc['default_url'])
            url = st.sidebar.text_input(
                svc['name'],
                value=default,
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


# Keep old name as an alias so any direct callers still work
def display_file_selector(input_dir):
    """Legacy wrapper — use display_data_source_selector instead."""
    result = display_data_source_selector(input_dir)
    return result.get('selected_file')


def display_date_filter(page_visits):
    """Display date range filter."""
    if not page_visits.empty and 'timestamp' in page_visits.columns:
        st.sidebar.header("Filters")

        min_date = page_visits['timestamp'].min().date()
        max_date = page_visits['timestamp'].max().date()

        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        # Apply date filter
        if len(date_range) == 2:
            mask = (page_visits['timestamp'].dt.date >= date_range[0]) & (page_visits['timestamp'].dt.date <= date_range[1])
            return page_visits[mask]

    return page_visits


def display_download_section(df, weekly_summary, completion_rate, page_visits, per_page_completion, funnel_data, selected_file, create_excel_download):
    """Display download buttons in sidebar."""
    st.sidebar.header("📥 Download Data")

    # Download individual datasets as CSV
    st.sidebar.subheader("CSV Downloads")

    # Parsed Data CSV
    csv_parsed = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📄 Download Parsed Data (CSV)",
        data=csv_parsed,
        file_name=f"parsed_data_{selected_file.split('.')[0]}.csv",
        mime="text/csv",
        use_container_width=True
    )

    # Weekly Summary CSV
    if not weekly_summary.empty:
        csv_weekly = weekly_summary.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button(
            label="📅 Download Weekly Summary (CSV)",
            data=csv_weekly,
            file_name=f"weekly_summary_{selected_file.split('.')[0]}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Completion Rate CSV
    if not completion_rate.empty:
        csv_completion = completion_rate.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button(
            label="✅ Download Completion Rates (CSV)",
            data=csv_completion,
            file_name=f"completion_rate_{selected_file.split('.')[0]}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Page Visits CSV
    if not page_visits.empty:
        csv_visits = page_visits.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button(
            label="🔍 Download Page Visits (CSV)",
            data=csv_visits,
            file_name=f"page_visits_{selected_file.split('.')[0]}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Download all data as Excel
    st.sidebar.subheader("Excel Download (All Data)")

    # Filter event types
    link_clicks = df[df['event_type'] == 'link_click'].copy() if 'event_type' in df.columns else pd.DataFrame()
    page_exits = df[df['event_type'] == 'page_exit'].copy() if 'event_type' in df.columns else pd.DataFrame()
    quick_exits = df[df['event_type'] == 'quick_exit'].copy() if 'event_type' in df.columns else pd.DataFrame()
    downloads = df[df['event_type'] == 'download'].copy() if 'event_type' in df.columns else pd.DataFrame()

    # Prepare all dataframes
    all_data = {
        'Parsed Data': df,
        'Page Visits': page_visits if not page_visits.empty else pd.DataFrame(),
        'Link Clicks': link_clicks if not link_clicks.empty else pd.DataFrame(),
        'Page Exits': page_exits if not page_exits.empty else pd.DataFrame(),
        'Quick Exits': quick_exits if not quick_exits.empty else pd.DataFrame(),
        'Downloads': downloads if not downloads.empty else pd.DataFrame(),
        'Weekly Summary': weekly_summary if not weekly_summary.empty else pd.DataFrame(),
        'Completion Rate': completion_rate if not completion_rate.empty else pd.DataFrame(),
        'Per Page Completion': per_page_completion if not per_page_completion.empty else pd.DataFrame(),
        'Funnel Data': funnel_data if not funnel_data.empty else pd.DataFrame()
    }

    # Create Excel file
    excel_file = create_excel_download(all_data)

    st.sidebar.download_button(
        label="📊 Download All Data (Excel)",
        data=excel_file,
        file_name=f"cap_analytics_all_data_{selected_file.split('.')[0]}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        help="Downloads all data including event types (Link Clicks, Page Exits, Quick Exits, Downloads) in a single Excel file with multiple sheets"
    )
