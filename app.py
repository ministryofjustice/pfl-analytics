"""Main application entry point for CAP Analytics Dashboard."""
import logging
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import sys
from dotenv import load_dotenv

load_dotenv()

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_processing import process_dataframe, fetch_services, parse_log_data  # noqa: E402
from utils.file_utils import create_excel_download, validate_file  # noqa: E402
from components.sidebar import display_data_source_selector, display_download_section  # noqa: E402
from components.metrics_display import display_key_metrics  # noqa: E402
from components.tabs import display_all_tabs  # noqa: E402

logger = logging.getLogger(__name__)

# --- Rate limiting ---------------------------------------------------------
_RATE_LIMIT_MAX = 20       # max loads per session within the window
_RATE_LIMIT_WINDOW = 3600  # seconds (1 hour)


def _check_rate_limit() -> None:
    """Enforce a per-session load rate limit.

    Raises RuntimeError with a safe message when the limit is exceeded.
    """
    now = datetime.now(timezone.utc).timestamp()
    history: list = st.session_state.setdefault('_load_timestamps', [])
    # Discard entries outside the rolling window
    history[:] = [t for t in history if now - t < _RATE_LIMIT_WINDOW]
    if len(history) >= _RATE_LIMIT_MAX:
        raise RuntimeError(
            "Too many requests. Please wait before loading more data."
        )
    history.append(now)


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
            _check_rate_limit()
            if active_config['source'] == 'file':
                file_path = (input_dir / active_config['selected_file']).resolve()
                if not file_path.is_relative_to(input_dir.resolve()):
                    raise ValueError("Invalid file path.")
                validate_file(file_path)
                df_raw = pd.read_csv(file_path) if str(file_path).endswith('.csv') else pd.read_excel(file_path)
                if df_raw.empty or df_raw.shape[1] < 1:
                    raise ValueError("The file appears to be empty or has no readable columns.")
                raw_df = parse_log_data(df_raw)
                raw_df['service'] = active_config['service_name']
                st.session_state['raw_label'] = active_config['selected_file']
            else:
                services = active_config.get('services', [])
                if not services:
                    st.warning("No OpenSearch URLs configured. Enter at least one service URL.")
                    st.stop()

                start_date, end_date = (active_config['date_range'] or (None, None))
                raw_df = fetch_services(services, start_date=start_date, end_date=end_date)
                st.session_state['raw_label'] = ', '.join(s['name'] for s in services)

            st.session_state['raw_df'] = raw_df
        except (ValueError, RuntimeError) as e:
            # Safe, user-facing validation / rate-limit messages
            st.error(str(e))
            st.stop()
        except Exception:
            logger.exception("Unexpected error while loading data")
            st.error("An unexpected error occurred while loading the data. Please try again or contact support.")
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
completion_rate_cs = data['completion_rate_cs']
page_visits = data['page_visits']
per_page_completion = data['per_page_completion']
funnel_data = data['funnel_data']

# Display key metrics
display_key_metrics(df, page_visits, completion_rate, completion_rate_cs)

# Download section in sidebar
display_download_section(
    df, weekly_summary, completion_rate, page_visits,
    per_page_completion, funnel_data, active_label, create_excel_download
)

# Display all tabs
display_all_tabs(df, weekly_summary, completion_rate, page_visits, per_page_completion, funnel_data, completion_rate_cs)

# Footer
st.divider()
st.caption(f"📁 Source: {active_label} | 📊 Dashboard generated with Streamlit")
