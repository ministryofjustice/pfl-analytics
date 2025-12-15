"""Main application entry point for CAP Analytics Dashboard.

NOTE: For the fully functional dashboard with all tabs, use: streamlit run dashboard.py
This app.py file demonstrates the new modular structure for key metrics and components.
Full tab extraction is a future enhancement.
"""
import streamlit as st
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_processing import process_log_file
from utils.file_utils import create_excel_download
from components.sidebar import display_file_selector, display_date_filter, display_download_section
from components.metrics_display import display_key_metrics

# Page configuration
st.set_page_config(
    page_title="CAP Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("📊 Care Arrangement Plan Analytics Dashboard")

# Info banner
st.info("💡 **Note:** This is the new modular version. For the full dashboard with all tabs, run: `streamlit run dashboard.py`")

# Setup input directory
input_dir = Path("input")
input_dir.mkdir(exist_ok=True)

# File selection
selected_file = display_file_selector(input_dir)

# Load data on button click or if already loaded
if 'load_data' not in st.session_state:
    st.info("👈 Select a file from the sidebar and click 'Load Data' to begin")
    st.stop()

# Process the selected file
file_path = input_dir / selected_file

with st.spinner(f"Processing {selected_file}..."):
    try:
        data = process_log_file(str(file_path))
        st.success(f"✅ Successfully loaded {len(data['parsed_data'])} records")
    except Exception as e:
        st.error(f"Error processing file: {e}")
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

# Date range filter
filtered_page_visits = display_date_filter(page_visits)

# Download section in sidebar
display_download_section(
    df, weekly_summary, completion_rate, page_visits,
    per_page_completion, funnel_data, selected_file, create_excel_download
)

st.divider()
st.subheader("📊 Data Summary")
st.write(f"**Total records processed:** {len(df):,}")
st.write(f"**Unique users:** {df['user_id'].nunique():,}")
st.write(f"**Date range:** {page_visits['timestamp'].min().date()} to {page_visits['timestamp'].max().date()}")

# Footer
st.divider()
st.caption(f"📁 Current file: {selected_file} | 📊 Dashboard generated with Streamlit")
st.caption("For detailed analytics and visualizations, use: `streamlit run dashboard.py`")
