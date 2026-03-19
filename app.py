"""Main application entry point for CAP Analytics Dashboard."""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_processing import process_log_file, process_dataframe, fetch_all_events
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

# Title
st.title("📊 Family Justice Analytics Dashboard")

# Setup input directory
input_dir = Path("input")
input_dir.mkdir(exist_ok=True)

# Data source selection
source_config = display_data_source_selector(input_dir)

# Determine label for footer / downloads
if source_config['source'] == 'file':
    data_label = source_config['selected_file']
else:
    service_names = [s['name'] for s in source_config.get('services', [])]
    data_label = ', '.join(service_names) if service_names else 'opensearch'

# Load data on button click or if already loaded in session
if source_config['load']:
    st.session_state['load_data'] = True
    st.session_state['data_label'] = data_label
    st.session_state['source_config'] = source_config

if 'load_data' not in st.session_state:
    st.info("👈 Choose a data source in the sidebar and click Load to begin")
    st.stop()

# Use the config that was active when Load was last clicked
active_config = st.session_state.get('source_config', source_config)
active_label = st.session_state.get('data_label', data_label)

with st.spinner("Loading data..."):
    try:
        if active_config['source'] == 'file':
            file_path = input_dir / active_config['selected_file']
            data = process_log_file(str(file_path))
        else:
            services = active_config.get('services', [])
            if not services:
                st.warning("No OpenSearch URLs configured. Enter at least one service URL.")
                st.stop()

            start_date, end_date = (active_config['date_range'] or (None, None))
            frames = []
            for svc in services:
                svc_df = fetch_all_events(
                    proxy_url=svc['url'],
                    index=svc['index'],
                    start_date=start_date,
                    end_date=end_date,
                    service_name=svc['name'],
                )
                frames.append(svc_df)

            combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            data = process_dataframe(combined)

        st.success(f"✅ Successfully loaded {len(data['parsed_data'])} records")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

# Extract data
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
