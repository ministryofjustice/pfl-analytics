"""Main data processing orchestration."""
import pandas as pd
from .parser import parse_log_data
from .metrics import (
    calculate_weekly_page_visits,
    calculate_completion_rate,
    calculate_per_page_completion_rate,
    calculate_funnel_data
)


def process_dataframe(df):
    """Run the metrics pipeline on an already-parsed DataFrame."""
    weekly_summary, page_visits = calculate_weekly_page_visits(df)
    final_completion = calculate_completion_rate(page_visits)
    per_page_completion = calculate_per_page_completion_rate(page_visits)
    funnel_data = calculate_funnel_data(page_visits)

    return {
        'parsed_data': df,
        'weekly_summary': weekly_summary,
        'completion_rate': final_completion,
        'page_visits': page_visits,
        'per_page_completion': per_page_completion,
        'funnel_data': funnel_data
    }


def process_log_file(file_path):
    """Main function to process a log file and return all analytics."""
    if file_path.endswith('.csv'):
        df_raw = pd.read_csv(file_path)
    else:
        df_raw = pd.read_excel(file_path)

    df = parse_log_data(df_raw)
    return process_dataframe(df)
