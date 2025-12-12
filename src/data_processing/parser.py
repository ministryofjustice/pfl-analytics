"""Log data parsing functionality."""
import pandas as pd
import re


def parse_log_data(df_raw):
    """Parse raw log data into structured format."""
    # Skip the first row if it's 'Log'
    if len(df_raw) > 0 and str(df_raw.iloc[0, 0]).strip() == 'Log':
        df_raw = df_raw.iloc[1:]
        print("Skipped 'Log' header row")

    # Parse the log entries into separate columns
    parsed_rows = []
    excluded_patterns = ['/assets', '/images', '/js', '/fonts', '/css', '/.git', '/.env', '/.well-known']

    for idx, row in df_raw.iterrows():
        log_entry = str(row.iloc[0])

        # Extract fields using regex
        timestamp_match = re.search(r'timestamp=([^,\)]+)', log_entry)
        event_type_match = re.search(r'event_type=([^,\)]+)', log_entry)
        user_id_match = re.search(r'user_id=([^,\)]+)', log_entry)
        path_match = re.search(r'path=([^,\)]+)', log_entry)
        method_match = re.search(r'method=([^,\)]+)', log_entry)
        status_code_match = re.search(r'status_code=([^,\)]+)', log_entry)
        download_type_match = re.search(r'download_type=([^,\)]+)', log_entry)

        # Get path and event_type values
        path_value = path_match.group(1) if path_match else None
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
            'method': method_match.group(1) if method_match else None,
            'status_code': status_code_match.group(1) if status_code_match else None,
            'download_type': download_type_match.group(1) if download_type_match else None,
        }

        parsed_rows.append(parsed_row)

    # Create DataFrame with parsed columns
    df = pd.DataFrame(parsed_rows)

    # Remove rows where user_id is blank, None, 'unknown', or 'anonymous'
    if not df.empty:
        original_count = len(df)
        df = df[df['user_id'].notna()]  # Remove None/NaN
        df = df[df['user_id'].str.strip() != '']  # Remove blank strings
        df = df[~df['user_id'].str.lower().isin(['unknown', 'anonymous'])]  # Remove 'unknown' or 'anonymous'

    return df
