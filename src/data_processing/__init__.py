"""Data processing modules."""
from .parser import parse_log_data
from .metrics import (
    calculate_weekly_page_visits,
    calculate_completion_rate,
    calculate_per_page_completion_rate,
    calculate_funnel_data
)
from .processor import process_log_file

__all__ = [
    'parse_log_data',
    'calculate_weekly_page_visits',
    'calculate_completion_rate',
    'calculate_per_page_completion_rate',
    'calculate_funnel_data',
    'process_log_file'
]
