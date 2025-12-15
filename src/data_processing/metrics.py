"""Metrics calculation functions."""
import pandas as pd
from .constants import PAGE_ORDER, PAGE_NAMES


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

    # Deduplicate page visits globally - keep only first visit per user-page combination
    deduplicated_visits = page_visits.sort_values('timestamp').drop_duplicates(subset=['user_id', 'path'], keep='first')

    # Calculate weekly stats per page
    results = []

    # Get all weeks from both original and deduplicated data
    all_weeks = sorted(page_visits['week'].unique())

    for week in all_weeks:
        # Use original data for total visits count
        week_data_raw = page_visits[page_visits['week'] == week]
        # Use deduplicated data for unique users count
        week_data_dedup = deduplicated_visits[deduplicated_visits['week'] == week]

        for page in PAGE_ORDER:
            page_data_raw = week_data_raw[week_data_raw['path'] == page]
            page_data_dedup = week_data_dedup[week_data_dedup['path'] == page]

            results.append({
                'week': week,
                'page': page,
                'total_visits': len(page_data_raw),  # Count from original data
                'unique_users': page_data_dedup['user_id'].nunique() if not page_data_dedup.empty else 0  # Count from deduplicated data
            })

    per_page_df = pd.DataFrame(results)
    per_page_df['week'] = per_page_df['week'].astype(str)

    return per_page_df


def calculate_funnel_data(page_visits):
    """Calculate funnel data across all pages in the journey."""
    if page_visits.empty:
        return pd.DataFrame()

    # Deduplicate page visits globally - keep only first visit per user-page combination
    deduplicated_visits = page_visits.sort_values('timestamp').drop_duplicates(subset=['user_id', 'path'], keep='first')

    funnel_data = []

    for page in PAGE_ORDER:
        page_data = deduplicated_visits[deduplicated_visits['path'] == page]

        funnel_data.append({
            'page': page,
            'page_name': PAGE_NAMES.get(page, page),
            'total_visits': len(page_data),
            'unique_users': page_data['user_id'].nunique() if not page_data.empty else 0
        })

    return pd.DataFrame(funnel_data)
