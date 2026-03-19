"""Main data processing orchestration."""
import pandas as pd
from .parser import parse_log_data
from .metrics import (
    calculate_weekly_page_visits,
    calculate_completion_rate,
    calculate_per_page_completion_rate,
    calculate_funnel_data
)
from .constants import PAGE_ORDER, PAGE_NAMES, PAGE_ORDER_CS, PAGE_NAMES_CS

# Maps service names (matching the 'service' column values) to their journey page order.
# Add an entry here when a new service is connected.
SERVICE_PAGE_ORDERS = {
    'CAP': (PAGE_ORDER, PAGE_NAMES),
    'Connecting Services': (PAGE_ORDER_CS, PAGE_NAMES_CS),
}


def process_dataframe(df):
    """Run the metrics pipeline on an already-parsed DataFrame."""
    weekly_summary, page_visits = calculate_weekly_page_visits(df)
    final_completion = calculate_completion_rate(page_visits)

    # Per-page and funnel metrics are journey-specific, so split by service
    # when multiple services are present to use the correct page order for each.
    if 'service' in page_visits.columns and page_visits['service'].nunique() > 1:
        per_page_parts, funnel_parts = [], []
        for service_name, svc_visits in page_visits.groupby('service'):
            po, pn = SERVICE_PAGE_ORDERS.get(service_name, (PAGE_ORDER, PAGE_NAMES))
            svc_per_page = calculate_per_page_completion_rate(svc_visits, page_order=po)
            svc_funnel = calculate_funnel_data(svc_visits, page_order=po, page_names=pn)
            if not svc_per_page.empty:
                svc_per_page['service'] = service_name
                per_page_parts.append(svc_per_page)
            if not svc_funnel.empty:
                svc_funnel['service'] = service_name
                funnel_parts.append(svc_funnel)
        per_page_completion = pd.concat(per_page_parts, ignore_index=True) if per_page_parts else pd.DataFrame()
        funnel_data = pd.concat(funnel_parts, ignore_index=True) if funnel_parts else pd.DataFrame()
    else:
        # Single service — pick the right page order from the service column if present
        service_name = page_visits['service'].iloc[0] if ('service' in page_visits.columns and not page_visits.empty) else 'CAP'
        po, pn = SERVICE_PAGE_ORDERS.get(service_name, (PAGE_ORDER, PAGE_NAMES))
        per_page_completion = calculate_per_page_completion_rate(page_visits, page_order=po)
        funnel_data = calculate_funnel_data(page_visits, page_order=po, page_names=pn)

    return {
        'parsed_data': df,
        'weekly_summary': weekly_summary,
        'completion_rate': final_completion,
        'page_visits': page_visits,
        'per_page_completion': per_page_completion,
        'funnel_data': funnel_data
    }


def load_log_file(file_path):
    """Read and parse a log file, returning a raw DataFrame."""
    if file_path.endswith('.csv'):
        df_raw = pd.read_csv(file_path)
    else:
        df_raw = pd.read_excel(file_path)
    return parse_log_data(df_raw)


def process_log_file(file_path):
    """Convenience wrapper: load and process a log file in one step."""
    return process_dataframe(load_log_file(file_path))
