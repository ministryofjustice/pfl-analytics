"""OpenSearch client for fetching analytics events."""
import requests
import pandas as pd

from utils.audit_log import log_event


EXCLUDED_PATHS = [
    '/assets', '/images', '/js', '/fonts', '/css',
    '/.git', '/.env', '/.well-known',
    '/apple-touch-icon', '/apple-touch-precomposed', '/rebrand'
]


def fetch_all_events(proxy_url, index='cap-analytics', start_date=None, end_date=None, service_name=None):
    """Fetch all events from OpenSearch and return as DataFrame.

    Args:
        proxy_url: Base URL of the OpenSearch proxy (e.g. http://localhost:8080)
        index: OpenSearch index name
        start_date: Optional datetime to filter events from
        end_date: Optional datetime to filter events to
        service_name: Label added to every row as the 'service' column (e.g. 'CAP')
    """
    proxy_url = proxy_url.rstrip('/')

    log_event("opensearch_query", index=index, service=service_name,
              date_from=str(start_date), date_to=str(end_date))

    if start_date or end_date:
        date_range = {}
        if start_date:
            date_range['gte'] = start_date.isoformat()
        if end_date:
            date_range['lte'] = end_date.isoformat()
        query = {'query': {'range': {'timestamp': date_range}}}
    else:
        query = {'query': {'match_all': {}}}

    # Initialise scroll
    response = requests.post(
        f'{proxy_url}/{index}/_search?scroll=1m',
        json={**query, 'size': 1000},
        timeout=30
    )
    response.raise_for_status()
    result = response.json()

    scroll_id = result.get('_scroll_id')
    hits = result['hits']['hits']
    all_docs = [hit['_source'] for hit in hits]

    # Page through remaining results
    while scroll_id and hits:
        scroll_response = requests.post(
            f'{proxy_url}/_search/scroll',
            json={'scroll': '1m', 'scroll_id': scroll_id},
            timeout=30
        )
        scroll_response.raise_for_status()
        scroll_result = scroll_response.json()
        hits = scroll_result['hits']['hits']
        scroll_id = scroll_result.get('_scroll_id')
        all_docs.extend(hit['_source'] for hit in hits)

    log_event("opensearch_result", index=index, service=service_name, docs_fetched=len(all_docs))
    return _docs_to_dataframe(all_docs, service_name=service_name)


def _docs_to_dataframe(docs, service_name=None):
    """Convert OpenSearch documents to DataFrame matching parse_log_data output."""
    if not docs:
        return pd.DataFrame(columns=[
            'timestamp', 'event_type', 'user_id', 'path', 'exit_page',
            'method', 'status_code', 'download_type', 'link_url', 'link_type', 'service'
        ])

    rows = []
    for doc in docs:
        event_type = doc.get('event_type')

        # For link_click events the current page is stored in 'page', not 'path'
        path = doc.get('path') or doc.get('page')

        # Skip excluded paths
        if path and any(path.startswith(p) for p in EXCLUDED_PATHS):
            continue

        # Skip page_visit events with no path
        if event_type == 'page_visit' and not path:
            continue

        user_id = doc.get('hashed_user_id')

        # Skip missing or anonymous user IDs (mirrors parse_log_data filtering)
        if not user_id or str(user_id).strip().lower() in ('', 'unknown', 'anonymous'):
            continue

        status = doc.get('status_code')
        rows.append({
            'timestamp': doc.get('timestamp'),
            'event_type': event_type,
            'user_id': user_id,
            'path': path,
            'exit_page': doc.get('exit_page'),
            'method': doc.get('method'),
            'status_code': str(status) if status is not None else None,
            'download_type': doc.get('download_type'),
            'link_url': doc.get('link_url'),
            'link_type': doc.get('link_type'),
            'service': service_name,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df
