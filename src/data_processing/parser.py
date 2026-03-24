"""Log data parsing functionality."""
import pandas as pd
import re

from .constants import EXCLUDED_PATHS

MAX_LOG_ENTRY_LENGTH = 2000

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


def _extract(match):
    return match.group(1) if match else None


def _is_excluded_path(path):
    return path and any(path.startswith(p) for p in EXCLUDED_PATHS)


def parse_log_data(df_raw):
    """Parse raw log data into structured format."""
    if len(df_raw) > 0 and str(df_raw.iloc[0, 0]).strip() == 'Log':
        df_raw = df_raw.iloc[1:]

    parsed_rows = []

    for _, row in df_raw.iterrows():
        log_entry = str(row.iloc[0])

        if len(log_entry) > MAX_LOG_ENTRY_LENGTH:
            continue

        path_match = _PATTERNS['path'].search(log_entry)
        page_match = _PATTERNS['page'].search(log_entry)
        event_type_match = _PATTERNS['event_type'].search(log_entry)

        path_value = _extract(path_match) or _extract(page_match)
        event_type_value = _extract(event_type_match)

        if event_type_value == 'page_visit' and not path_value:
            continue

        if _is_excluded_path(path_value):
            continue

        parsed_rows.append({
            'timestamp':     _extract(_PATTERNS['timestamp'].search(log_entry)),
            'event_type':    event_type_value,
            'user_id':       _extract(_PATTERNS['user_id'].search(log_entry)),
            'path':          path_value,
            'exit_page':     _extract(_PATTERNS['exit_page'].search(log_entry)),
            'method':        _extract(_PATTERNS['method'].search(log_entry)),
            'status_code':   _extract(_PATTERNS['status_code'].search(log_entry)),
            'download_type': _extract(_PATTERNS['download_type'].search(log_entry)),
            'link_url':      _extract(_PATTERNS['link_url'].search(log_entry)),
            'link_type':     _extract(_PATTERNS['link_type'].search(log_entry)),
        })

    df = pd.DataFrame(parsed_rows)

    if not df.empty:
        df = df[df['user_id'].notna()]
        df = df[df['user_id'].str.strip() != '']
        df = df[~df['user_id'].str.lower().isin(['unknown', 'anonymous'])]

    return df
