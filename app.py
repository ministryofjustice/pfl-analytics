"""Main application entry point for CAP Analytics Dashboard."""
import streamlit as st
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_processing import process_log_file
from utils.file_utils import create_excel_download
from components.sidebar import display_file_selector, display_download_section
from components.metrics_display import display_key_metrics
from components.tabs import display_all_tabs

# Page configuration
st.set_page_config(
    page_title="CAP Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("📊 Care Arrangement Plan Analytics Dashboard")

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

# Download section in sidebar
display_download_section(
    df, weekly_summary, completion_rate, page_visits,
    per_page_completion, funnel_data, selected_file, create_excel_download
)

# Display all tabs
display_all_tabs(df, weekly_summary, completion_rate, page_visits, per_page_completion, funnel_data)

# Footer
st.divider()
st.caption(f"📁 Current file: {selected_file} | 📊 Dashboard generated with Streamlit")
