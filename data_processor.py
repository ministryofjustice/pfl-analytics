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
        exit_page_match = re.search(r'exit_page=([^,\)]+)', log_entry)
        method_match = re.search(r'method=([^,\)]+)', log_entry)
        status_code_match = re.search(r'status_code=([^,\)]+)', log_entry)
        download_type_match = re.search(r'download_type=([^,\)]+)', log_entry)

        # Get path and event_type values
        path_value = path_match.group(1) if path_match else None
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


def calculate_weekly_page_visits(df):
    """Calculate weekly page visit statistics."""
    page_visits = df[df['event_type'] == 'page_visit'].copy()

    if not page_visits.empty and 'timestamp' in page_visits.columns:
        # Convert timestamp to datetime
        page_visits['timestamp'] = pd.to_datetime(page_visits['timestamp'])

        # Extract week
        page_visits['week'] = page_visits['timestamp'].dt.to_period('W')

        # Group by week and path, count occurrences
        weekly_summary = page_visits.groupby(['week', 'path']).size().reset_index(name='count')

        # Sort by week and count (descending within each week)
        weekly_summary = weekly_summary.sort_values(['week', 'count'], ascending=[True, False])

        # Convert week to string for compatibility
        weekly_summary['week'] = weekly_summary['week'].astype(str)

        return weekly_summary, page_visits
    else:
        return pd.DataFrame(columns=['week', 'path', 'count']), pd.DataFrame()


def calculate_completion_rate(page_visits):
    """Calculate weekly completion rates."""
    if page_visits.empty or 'timestamp' not in page_visits.columns:
        return pd.DataFrame(columns=['week', 'safety_check_visits', 'confirmation_visits',
                                     'simple_completion_rate', 'unique_users_safety_check',
                                     'unique_users_completed', 'user_completion_rate'])

    # Filter for safety-check and confirmation pages
    safety_check = page_visits[page_visits['path'].str.contains('safety-check', case=False, na=False)]
    confirmation = page_visits[page_visits['path'].str.contains('confirmation', case=False, na=False)]

    # Simple method: count totals per week (for unknown IDs)
    safety_check_weekly = safety_check.groupby('week').size().reset_index(name='safety_check_visits')
    confirmation_weekly = confirmation.groupby('week').size().reset_index(name='confirmation_visits')

    # Merge and calculate simple completion rate
    weekly_completion = pd.merge(safety_check_weekly, confirmation_weekly, on='week', how='outer').fillna(0)
    weekly_completion['simple_completion_rate'] = (weekly_completion['confirmation_visits'] / weekly_completion['safety_check_visits'] * 100).round(2)
    weekly_completion['simple_completion_rate'] = weekly_completion['simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

    # Advanced method: unique user completion (for known IDs)
    # Get unique user_id + week combinations for safety-check
    safety_check_users = safety_check.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
    # Get unique user_id + week combinations for confirmation
    confirmation_users = confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]

    # Mark users who reached each stage
    safety_check_users['reached_safety_check'] = 1
    confirmation_users['reached_confirmation'] = 1

    # Merge to find users who reached both stages
    user_completion = pd.merge(safety_check_users, confirmation_users, on=['week', 'user_id'], how='left').fillna(0)

    # Count unique users per week
    unique_safety_check = user_completion.groupby('week')['reached_safety_check'].sum().reset_index(name='unique_users_safety_check')
    unique_completed = user_completion[user_completion['reached_confirmation'] == 1].groupby('week').size().reset_index(name='unique_users_completed')

    # Merge and calculate user-based completion rate
    user_based_completion = pd.merge(unique_safety_check, unique_completed, on='week', how='outer').fillna(0)
    user_based_completion['user_completion_rate'] = (user_based_completion['unique_users_completed'] / user_based_completion['unique_users_safety_check'] * 100).round(2)
    user_based_completion['user_completion_rate'] = user_based_completion['user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

    # Combine both methods
    final_completion = pd.merge(weekly_completion, user_based_completion, on='week', how='outer').fillna(0)
    final_completion['week'] = final_completion['week'].astype(str)

    return final_completion


def calculate_per_page_completion_rate(page_visits):
    """Calculate completion rates for each page in the journey."""
    if page_visits.empty or 'timestamp' not in page_visits.columns:
        return pd.DataFrame()

    # Define the page order
    page_order = [
        '/',
        '/safety-check',
        '/children-safety-check',
        '/do-whats-best',
        '/court-order-check',
        '/number-of-children',
        '/about-the-children',
        '/about-the-adults',
        '/make-a-plan',
        '/check-your-answers',
        '/share-plan',
        '/confirmation'
    ]

    # Deduplicate page visits globally - keep only first visit per user-page combination
    deduplicated_visits = page_visits.sort_values('timestamp').drop_duplicates(subset=['user_id', 'path'], keep='first')

    # Calculate weekly stats per page using deduplicated data
    results = []

    for week in sorted(deduplicated_visits['week'].unique()):
        week_data = deduplicated_visits[deduplicated_visits['week'] == week]

        for page in page_order:
            page_data = week_data[week_data['path'] == page]

            results.append({
                'week': week,
                'page': page,
                'total_visits': len(page_data),
                'unique_users': page_data['user_id'].nunique() if not page_data.empty else 0
            })

    per_page_df = pd.DataFrame(results)
    per_page_df['week'] = per_page_df['week'].astype(str)

    return per_page_df


def calculate_funnel_data(page_visits):
    """Calculate funnel data across all pages in the journey."""
    if page_visits.empty:
        return pd.DataFrame()

    # Define the page order
    page_order = [
        '/',
        '/safety-check',
        '/children-safety-check',
        '/do-whats-best',
        '/court-order-check',
        '/number-of-children',
        '/about-the-children',
        '/about-the-adults',
        '/make-a-plan',
        '/check-your-answers',
        '/share-plan',
        '/confirmation'
    ]

    # Page display names
    page_names = {
        '/': 'Home',
        '/safety-check': 'Safety Check',
        '/children-safety-check': 'Children Safety Check',
        '/do-whats-best': 'Do What\'s Best',
        '/court-order-check': 'Court Order Check',
        '/number-of-children': 'Number of Children',
        '/about-the-children': 'About the Children',
        '/about-the-adults': 'About the Adults',
        '/make-a-plan': 'Make a Plan',
        '/check-your-answers': 'Check Your Answers',
        '/share-plan': 'Share Plan',
        '/confirmation': 'Confirmation'
    }

    # Deduplicate page visits globally - keep only first visit per user-page combination
    deduplicated_visits = page_visits.sort_values('timestamp').drop_duplicates(subset=['user_id', 'path'], keep='first')

    funnel_data = []

    for page in page_order:
        page_data = deduplicated_visits[deduplicated_visits['path'] == page]

        funnel_data.append({
            'page': page,
            'page_name': page_names.get(page, page),
            'total_visits': len(page_data),
            'unique_users': page_data['user_id'].nunique() if not page_data.empty else 0
        })

    return pd.DataFrame(funnel_data)


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
