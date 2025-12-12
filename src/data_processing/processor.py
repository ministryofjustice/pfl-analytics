"""Main data processing orchestration."""
import pandas as pd
from .parser import parse_log_data
from .metrics import (
    calculate_weekly_page_visits,
    calculate_completion_rate,
    calculate_per_page_completion_rate,
    calculate_funnel_data
)


def process_log_file(file_path):
    """Main function to process a log file and return all analytics."""
    # Read the file
    if file_path.endswith('.csv'):
        df_raw = pd.read_csv(file_path)
    else:
        df_raw = pd.read_excel(file_path)

    # Parse the data
    df = parse_log_data(df_raw)

    # Calculate weekly page visits
    weekly_summary, page_visits = calculate_weekly_page_visits(df)

    # Calculate completion rate
    final_completion = calculate_completion_rate(page_visits)

    # Calculate per-page completion rates
    per_page_completion = calculate_per_page_completion_rate(page_visits)

    # Calculate funnel data
    funnel_data = calculate_funnel_data(page_visits)

    return {
        'parsed_data': df,
        'weekly_summary': weekly_summary,
        'completion_rate': final_completion,
        'page_visits': page_visits,
        'per_page_completion': per_page_completion,
        'funnel_data': funnel_data
    }
