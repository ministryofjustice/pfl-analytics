"""Main application entry point for CAP Analytics Dashboard."""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_processing import load_log_file, process_dataframe, fetch_all_events
from utils.file_utils import create_excel_download
from components.sidebar import display_data_source_selector, display_download_section
from components.metrics_display import display_key_metrics
from components.tabs import display_all_tabs

# Page configuration
st.set_page_config(
    page_title="Family Justice Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Family Justice Analytics Dashboard")

input_dir = Path("input")
input_dir.mkdir(exist_ok=True)

# --- Step 1: data source selector (always rendered so sidebar stays visible) ---
source_config = display_data_source_selector(input_dir)

# When Load is clicked, clear any cached raw data and store the new config
if source_config['load']:
    st.session_state.pop('raw_df', None)
    st.session_state.pop('raw_label', None)
    st.session_state['source_config'] = source_config

if 'source_config' not in st.session_state:
    st.info("👈 Choose a data source in the sidebar and click Load to begin")
    st.stop()

active_config = st.session_state['source_config']

# --- Step 2: fetch / read raw DataFrame (cached so filter changes don't re-fetch) ---
if 'raw_df' not in st.session_state:
    with st.spinner("Loading data..."):
        try:
            if active_config['source'] == 'file':
                file_path = input_dir / active_config['selected_file']
                raw_df = load_log_file(str(file_path))
                st.session_state['raw_label'] = active_config['selected_file']
            else:
                services = active_config.get('services', [])
                if not services:
                    st.warning("No OpenSearch URLs configured. Enter at least one service URL.")
                    st.stop()

                start_date, end_date = (active_config['date_range'] or (None, None))
                frames = []
                for svc in services:
                    frames.append(fetch_all_events(
                        proxy_url=svc['url'],
                        index=svc['index'],
                        start_date=start_date,
                        end_date=end_date,
                        service_name=svc['name'],
                    ))
                raw_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                service_names = [s['name'] for s in services]
                st.session_state['raw_label'] = ', '.join(service_names)

            st.session_state['raw_df'] = raw_df
        except Exception as e:
            st.error(f"Error loading data: {e}")
            st.stop()

raw_df = st.session_state['raw_df']
active_label = st.session_state.get('raw_label', '')

# --- Step 3: service filter (only shown when multiple services are present) ---
if 'service' in raw_df.columns and raw_df['service'].nunique() > 1:
    available_services = sorted(raw_df['service'].dropna().unique().tolist())
    st.sidebar.header("Filters")
    selected_services = st.sidebar.multiselect(
        "Services",
        available_services,
        default=available_services,
    )
    filtered_df = raw_df[raw_df['service'].isin(selected_services)] if selected_services else raw_df
else:
    filtered_df = raw_df

if filtered_df.empty:
    st.warning("No data for the selected services.")
    st.stop()

# --- Step 4: process filtered data ---
data = process_dataframe(filtered_df)
st.success(f"✅ {len(data['parsed_data'])} records loaded")

df = data['parsed_data']
weekly_summary = data['weekly_summary']
completion_rate = data['completion_rate']
page_visits = data['page_visits']
per_page_completion = data['per_page_completion']
funnel_data = data['funnel_data']

# Display key metrics
display_key_metrics(df, page_visits, completion_rate)

# Download section in sidebar
display_download_section(
    df, weekly_summary, completion_rate, page_visits,
    per_page_completion, funnel_data, active_label, create_excel_download
)

# Display all tabs
display_all_tabs(df, weekly_summary, completion_rate, page_visits, per_page_completion, funnel_data)

# Footer
st.divider()
st.caption(f"📁 Source: {active_label} | 📊 Dashboard generated with Streamlit")
