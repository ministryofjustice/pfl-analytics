"""Log data parsing functionality."""
import pandas as pd
import re

# Maximum log entry length — entries beyond this are skipped as malformed/malicious
MAX_LOG_ENTRY_LENGTH = 2000

# Compiled patterns with bounded quantifiers to prevent ReDoS.
# The upper bound on each capture group limits worst-case backtracking.
_PATTERNS = {
    'timestamp':     re.compile(r'timestamp=([^,\)]{1,50})'),
    'event_type':    re.compile(r'event_type=([^,\)]{1,30})'),
    'user_id':       re.compile(r'user_id=([^,\)]{1,100})'),
    'path':          re.compile(r'path=([^,\)]{1,500})'),
    'exit_page':     re.compile(r'exit_page=([^,\)]{1,500})'),
    'method':        re.compile(r'method=([^,\)]{1,10})'),
    'status_code':   re.compile(r'status_code=([^,\)]{1,3})'),
    'download_type': re.compile(r'download_type=([^,\)]{1,50})'),
    'link_url':      re.compile(r'link_url=([^,\)]{1,500})'),
    'link_type':     re.compile(r'link_type=([^,\)]{1,50})'),
    'page':          re.compile(r'(?<!\w)page=([^,\)]{1,500})'),
}


def parse_log_data(df_raw):
    """Parse raw log data into structured format."""
    # Skip the first row if it's 'Log'
    if len(df_raw) > 0 and str(df_raw.iloc[0, 0]).strip() == 'Log':
        df_raw = df_raw.iloc[1:]
        print("Skipped 'Log' header row")

    # Parse the log entries into separate columns
    parsed_rows = []
    excluded_patterns = ['/assets', '/images', '/js', '/fonts', '/css', '/.git', '/.env', '/.well-known', '/apple-touch-icon', '/apple-touch-precomposed', '/rebrand']

    for idx, row in df_raw.iterrows():
        log_entry = str(row.iloc[0])

        # Skip entries that exceed the maximum length
        if len(log_entry) > MAX_LOG_ENTRY_LENGTH:
            continue

        # Extract fields using pre-compiled patterns
        timestamp_match = _PATTERNS['timestamp'].search(log_entry)
        event_type_match = _PATTERNS['event_type'].search(log_entry)
        user_id_match = _PATTERNS['user_id'].search(log_entry)
        path_match = _PATTERNS['path'].search(log_entry)
        exit_page_match = _PATTERNS['exit_page'].search(log_entry)
        method_match = _PATTERNS['method'].search(log_entry)
        status_code_match = _PATTERNS['status_code'].search(log_entry)
        download_type_match = _PATTERNS['download_type'].search(log_entry)
        link_url_match = _PATTERNS['link_url'].search(log_entry)
        link_type_match = _PATTERNS['link_type'].search(log_entry)
        page_match = _PATTERNS['page'].search(log_entry)

        # Get path and event_type values (use 'page' as fallback for 'path')
        path_value = path_match.group(1) if path_match else (page_match.group(1) if page_match else None)
        exit_page_value = exit_page_match.group(1) if exit_page_match else None
        event_type_value = event_type_match.group(1) if event_type_match else None

        # Skip if event_type is page_visit but no path
        if event_type_value == 'page_visit' and not path_value:
            continue

        # Skip if path matches excluded patterns
        if path_value:
            skip_row = False
            for pattern in excluded_patterns:
                if path_value.startswith(pattern):
                    skip_row = True
                    break
            if skip_row:
                continue

        parsed_row = {
            'timestamp': timestamp_match.group(1) if timestamp_match else None,
            'event_type': event_type_value,
            'user_id': user_id_match.group(1) if user_id_match else None,
            'path': path_value,
            'exit_page': exit_page_value,
            'method': method_match.group(1) if method_match else None,
            'status_code': status_code_match.group(1) if status_code_match else None,
            'download_type': download_type_match.group(1) if download_type_match else None,
            'link_url': link_url_match.group(1) if link_url_match else None,
            'link_type': link_type_match.group(1) if link_type_match else None,
        }

        parsed_rows.append(parsed_row)

    # Create DataFrame with parsed columns
    df = pd.DataFrame(parsed_rows)

    # Remove rows where user_id is blank, None, 'unknown', or 'anonymous'
    if not df.empty:
        df = df[df['user_id'].notna()]  # Remove None/NaN
        df = df[df['user_id'].str.strip() != '']  # Remove blank strings
        df = df[~df['user_id'].str.lower().isin(['unknown', 'anonymous'])]  # Remove 'unknown' or 'anonymous'

    return df
