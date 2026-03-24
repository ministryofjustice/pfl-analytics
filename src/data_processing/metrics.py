"""Metrics calculation functions."""
import numpy as np
import pandas as pd
from .constants import PAGE_ORDER, PAGE_NAMES


# CS journeys: (step_name used in column names, url pattern to match)
CS_JOURNEY_STEPS = [
    ('getting_help', 'getting-help'),
    ('parenting_plan', 'parenting-plan'),
    ('options_no_contact', 'options-no-contact'),
    ('court_order', 'court-order'),
    ('mediation', 'mediation'),
]


def calculate_weekly_page_visits(df):
    """Calculate weekly page visit statistics."""
    page_visits = df[df['event_type'] == 'page_visit'].copy()

    if not page_visits.empty and 'timestamp' in page_visits.columns:
        # Convert timestamp to datetime
        page_visits['timestamp'] = pd.to_datetime(page_visits['timestamp'])

        # Extract week (strip timezone first — to_period doesn't support tz-aware timestamps)
        ts = page_visits['timestamp']
        if hasattr(ts.dtype, 'tz') and ts.dtype.tz is not None:
            ts = ts.dt.tz_localize(None)
        page_visits['week'] = ts.dt.to_period('W')

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


def calculate_completion_rate_cs(page_visits):
    """Calculate weekly completion rates for each Connecting Services journey.

    Each journey uses domestic-abuse as the entry point and a specific step
    as the completion point, mirroring getFinalCompletionCS in main.py.

    Returns a dict of {step_name: DataFrame}, one entry per journey step.
    """
    empty = {
        step_name: pd.DataFrame(columns=[
            'week', 'domestic_abuse_visits', f'{step_name}_visits',
            f'{step_name}_simple_completion_rate', 'unique_users_domestic_abuse',
            f'unique_{step_name}_users_completed', f'{step_name}_user_completion_rate',
        ])
        for step_name, _ in CS_JOURNEY_STEPS
    }

    if page_visits.empty or 'timestamp' not in page_visits.columns:
        return empty

    paths = page_visits['path'].str.lower()
    domestic_abuse = page_visits[paths.str.contains('domestic-abuse', na=False)]
    domestic_weekly = domestic_abuse.groupby('week').size().reset_index(name='domestic_abuse_visits')
    unique_domestic = (
        domestic_abuse.groupby('week')['user_id']
        .nunique()
        .reset_index(name='unique_users_domestic_abuse')
    )

    result = {}
    for step_name, step_pattern in CS_JOURNEY_STEPS:
        step_df = page_visits[paths.str.contains(step_pattern, na=False)]
        step_weekly = step_df.groupby('week').size().reset_index(name=f'{step_name}_visits')

        weekly = pd.merge(domestic_weekly, step_weekly, on='week', how='outer').fillna(0)
        weekly[f'{step_name}_simple_completion_rate'] = np.where(
            weekly['domestic_abuse_visits'] > 0,
            (weekly[f'{step_name}_visits'] / weekly['domestic_abuse_visits']) * 100,
            0
        ).round(2)

        unique_step = (
            step_df.groupby('week')['user_id']
            .nunique()
            .reset_index(name=f'unique_{step_name}_users_completed')
        )

        user_completion = pd.merge(unique_domestic, unique_step, on='week', how='outer').fillna(0)
        user_completion[f'{step_name}_user_completion_rate'] = np.where(
            user_completion['unique_users_domestic_abuse'] > 0,
            (user_completion[f'unique_{step_name}_users_completed'] / user_completion['unique_users_domestic_abuse']) * 100,
            0
        ).round(2)

        final = pd.merge(weekly, user_completion, on='week', how='outer').fillna(0)
        final['week'] = final['week'].astype(str)
        result[step_name] = final

    return result


def calculate_per_page_completion_rate(page_visits, page_order=None):
    """Calculate completion rates for each page in the journey.

    Args:
        page_visits: DataFrame of page_visit events
        page_order: List of paths defining the journey. Defaults to CAP page order.
    """
    if page_order is None:
        page_order = PAGE_ORDER

    if page_visits.empty or 'timestamp' not in page_visits.columns:
        return pd.DataFrame()

    # Deduplicate page visits globally - keep only first visit per user-page combination
    deduplicated_visits = page_visits.sort_values('timestamp').drop_duplicates(subset=['user_id', 'path'], keep='first')

    # Calculate weekly stats per page using deduplicated data throughout
    results = []

    all_weeks = sorted(deduplicated_visits['week'].unique())

    for week in all_weeks:
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


def calculate_funnel_data(page_visits, page_order=None, page_names=None):
    """Calculate funnel data across all pages in the journey.

    Args:
        page_visits: DataFrame of page_visit events
        page_order: List of paths defining the journey. Defaults to CAP page order.
        page_names: Dict mapping paths to display names. Defaults to CAP page names.
    """
    if page_order is None:
        page_order = PAGE_ORDER
    if page_names is None:
        page_names = PAGE_NAMES

    if page_visits.empty:
        return pd.DataFrame()

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
