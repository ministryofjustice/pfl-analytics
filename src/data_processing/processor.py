"""Main data processing orchestration."""
import pandas as pd
import streamlit as st
from .opensearch_client import fetch_all_events
from .metrics import (
    calculate_weekly_page_visits,
    calculate_completion_rate,
    calculate_completion_rate_cs,
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

    # Completion rates are journey-specific — route by service
    if 'service' in page_visits.columns:
        cap_visits = page_visits[page_visits['service'] == 'CAP']
        cs_visits = page_visits[page_visits['service'] == 'Connecting Services']
        final_completion = calculate_completion_rate(cap_visits) if not cap_visits.empty else pd.DataFrame()
        completion_rate_cs = calculate_completion_rate_cs(cs_visits) if not cs_visits.empty else None
    else:
        final_completion = calculate_completion_rate(page_visits)
        completion_rate_cs = None

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
        'completion_rate_cs': completion_rate_cs,
        'page_visits': page_visits,
        'per_page_completion': per_page_completion,
        'funnel_data': funnel_data,
    }


@st.cache_data(ttl=300, hash_funcs={list: lambda x: str(x)})
def fetch_services(services, start_date=None, end_date=None):
    """Fetch and combine raw DataFrames from one or more OpenSearch services.

    Args:
        services: List of {name, url, index} dicts (from sidebar config)
        start_date: Optional start of date range
        end_date: Optional end of date range

    Returns:
        Combined DataFrame with a 'service' column tagging each row.
    """
    frames = [
        fetch_all_events(
            proxy_url=svc['url'],
            index=svc['index'],
            start_date=start_date,
            end_date=end_date,
            service_name=svc['name'],
        )
        for svc in services
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
