"""Main application entry point for CAP Analytics Dashboard."""
import logging
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_processing import process_dataframe, fetch_services, parse_log_data  # noqa: E402
from utils.file_utils import create_excel_download, validate_file  # noqa: E402
from utils.audit_log import log_event  # noqa: E402
from components.sidebar import display_data_source_selector, display_download_section  # noqa: E402
from components.metrics_display import display_key_metrics  # noqa: E402
from components.tabs import display_all_tabs  # noqa: E402

logger = logging.getLogger(__name__)

_RATE_LIMIT_MAX = 20
_RATE_LIMIT_WINDOW = 3600


def _check_rate_limit() -> None:
    now = datetime.now(timezone.utc).timestamp()
    history: list = st.session_state.setdefault('_load_timestamps', [])
    history[:] = [t for t in history if now - t < _RATE_LIMIT_WINDOW]
    if len(history) >= _RATE_LIMIT_MAX:
        log_event("rate_limit_hit", loads_in_window=len(history), window_seconds=_RATE_LIMIT_WINDOW)
        raise RuntimeError("Too many requests. Please wait before loading more data.")
    history.append(now)


st.set_page_config(
    page_title="Family Justice Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Family Justice Analytics Dashboard")

input_dir = Path("input")
input_dir.mkdir(exist_ok=True)

source_config = display_data_source_selector(input_dir)

if source_config['load']:
    st.session_state.pop('raw_df', None)
    st.session_state.pop('raw_label', None)
    st.session_state['source_config'] = source_config

if 'source_config' not in st.session_state:
    st.info("👈 Choose a data source in the sidebar and click Load to begin")
    st.stop()

active_config = st.session_state['source_config']

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
                log_event("data_loaded", source="file", service=active_config['service_name'],
                          rows=len(raw_df))
            else:
                services = active_config.get('services', [])
                if not services:
                    st.warning("No OpenSearch URLs configured. Enter at least one service URL.")
                    st.stop()

                start_date, end_date = (active_config['date_range'] or (None, None))
                raw_df = fetch_services(services, start_date=start_date, end_date=end_date)
                st.session_state['raw_label'] = ', '.join(s['name'] for s in services)
                log_event("data_loaded", source="opensearch",
                          services=[s['name'] for s in services],
                          date_from=str(start_date), date_to=str(end_date),
                          rows=len(raw_df))

            st.session_state['raw_df'] = raw_df
        except (ValueError, RuntimeError) as e:
            st.error(str(e))
            st.stop()
        except Exception:
            logger.exception("Unexpected error while loading data")
            log_event("error", kind="data_load_failure", source=active_config.get('source'))
            st.error("An unexpected error occurred while loading the data. Please try again or contact support.")
            st.stop()

raw_df = st.session_state['raw_df']
active_label = st.session_state.get('raw_label', '')

if 'service' in raw_df.columns and raw_df['service'].nunique() > 1:
    available_services = sorted(raw_df['service'].dropna().unique().tolist())
    st.sidebar.header("Filters")
    selected_services = st.sidebar.multiselect("Services", available_services, default=available_services)
    filtered_df = raw_df[raw_df['service'].isin(selected_services)] if selected_services else raw_df
else:
    filtered_df = raw_df

if filtered_df.empty:
    st.warning("No data for the selected services.")
    st.stop()

data = process_dataframe(filtered_df)
st.success(f"✅ {len(data['parsed_data'])} records loaded")

df = data['parsed_data']
weekly_summary = data['weekly_summary']
completion_rate = data['completion_rate']
completion_rate_cs = data['completion_rate_cs']
page_visits = data['page_visits']
per_page_completion = data['per_page_completion']
funnel_data = data['funnel_data']

display_key_metrics(df, page_visits, completion_rate, completion_rate_cs)

display_download_section(
    df, weekly_summary, completion_rate, page_visits,
    per_page_completion, funnel_data, active_label, create_excel_download
)

display_all_tabs(df, weekly_summary, completion_rate, page_visits, per_page_completion, funnel_data, completion_rate_cs)

st.divider()
st.caption(f"📁 Source: {active_label} | 📊 Dashboard generated with Streamlit")
