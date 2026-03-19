"""Data processing modules."""
from .parser import parse_log_data
from .metrics import (
    calculate_weekly_page_visits,
    calculate_completion_rate,
    calculate_per_page_completion_rate,
    calculate_funnel_data
)
from .processor import load_log_file, process_log_file, process_dataframe
from .opensearch_client import fetch_all_events

__all__ = [
    'parse_log_data',
    'calculate_weekly_page_visits',
    'calculate_completion_rate',
    'calculate_per_page_completion_rate',
    'calculate_funnel_data',
    'process_log_file',
    'process_dataframe',
    'fetch_all_events',
]
