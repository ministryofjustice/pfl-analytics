"""Metrics calculation functions."""
import numpy as np
import pandas as pd
from .constants import PAGE_ORDER, PAGE_NAMES


CS_JOURNEY_STEPS = [
    ('getting_help',      'getting-help'),
    ('parenting_plan',    'parenting-plan'),
    ('options_no_contact', 'options-no-contact'),
    ('court_order',       'court-order'),
    ('mediation',         'mediation'),
]


def _strip_tz(ts):
    if hasattr(ts.dtype, 'tz') and ts.dtype.tz is not None:
        return ts.dt.tz_localize(None)
    return ts


def _safe_rate(numerator, denominator):
    return (numerator / denominator * 100).round(2).replace([float('inf'), float('-inf')], 0).fillna(0)


def calculate_weekly_page_visits(df):
    """Calculate weekly page visit statistics."""
    page_visits = df[df['event_type'] == 'page_visit'].copy()

    if page_visits.empty or 'timestamp' not in page_visits.columns:
        return pd.DataFrame(columns=['week', 'path', 'count']), pd.DataFrame()

    page_visits['timestamp'] = pd.to_datetime(page_visits['timestamp'])
    page_visits['week'] = _strip_tz(page_visits['timestamp']).dt.to_period('W')

    weekly_summary = (
        page_visits.groupby(['week', 'path'])
        .size()
        .reset_index(name='count')
        .sort_values(['week', 'count'], ascending=[True, False])
    )
    weekly_summary['week'] = weekly_summary['week'].astype(str)

    return weekly_summary, page_visits


def calculate_completion_rate(page_visits):
    """Calculate weekly completion rates for CAP."""
    if page_visits.empty or 'timestamp' not in page_visits.columns:
        return pd.DataFrame(columns=['week', 'safety_check_visits', 'confirmation_visits',
                                     'simple_completion_rate', 'unique_users_safety_check',
                                     'unique_users_completed', 'user_completion_rate'])

    safety_check = page_visits[page_visits['path'].str.contains('safety-check', case=False, na=False)]
    confirmation = page_visits[page_visits['path'].str.contains('confirmation', case=False, na=False)]

    safety_check_weekly = safety_check.groupby('week').size().reset_index(name='safety_check_visits')
    confirmation_weekly = confirmation.groupby('week').size().reset_index(name='confirmation_visits')

    weekly = pd.merge(safety_check_weekly, confirmation_weekly, on='week', how='outer').fillna(0)
    weekly['simple_completion_rate'] = _safe_rate(weekly['confirmation_visits'], weekly['safety_check_visits'])

    safety_users = safety_check.groupby(['week', 'user_id']).size().reset_index(name='_')[['week', 'user_id']]
    confirmation_users = confirmation.groupby(['week', 'user_id']).size().reset_index(name='_')[['week', 'user_id']]

    safety_users['reached_safety_check'] = 1
    confirmation_users['reached_confirmation'] = 1

    user_completion = pd.merge(safety_users, confirmation_users, on=['week', 'user_id'], how='left').fillna(0)

    unique_safety = user_completion.groupby('week')['reached_safety_check'].sum().reset_index(name='unique_users_safety_check')
    unique_completed = (
        user_completion[user_completion['reached_confirmation'] == 1]
        .groupby('week').size().reset_index(name='unique_users_completed')
    )

    user_based = pd.merge(unique_safety, unique_completed, on='week', how='outer').fillna(0)
    user_based['user_completion_rate'] = _safe_rate(user_based['unique_users_completed'], user_based['unique_users_safety_check'])

    final = pd.merge(weekly, user_based, on='week', how='outer').fillna(0)
    final['week'] = final['week'].astype(str)

    return final


def calculate_completion_rate_cs(page_visits):
    """Calculate weekly completion rates for each Connecting Services journey."""
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
    """Calculate completion rates for each page in the journey."""
    if page_order is None:
        page_order = PAGE_ORDER

    if page_visits.empty or 'timestamp' not in page_visits.columns:
        return pd.DataFrame()

    deduplicated = page_visits.sort_values('timestamp').drop_duplicates(subset=['user_id', 'path'], keep='first')
    all_weeks = sorted(deduplicated['week'].unique())

    results = []
    for week in all_weeks:
        week_data = deduplicated[deduplicated['week'] == week]
        for page in page_order:
            page_data = week_data[week_data['path'] == page]
            results.append({
                'week': week,
                'page': page,
                'total_visits': len(page_data),
                'unique_users': page_data['user_id'].nunique() if not page_data.empty else 0,
            })

    per_page_df = pd.DataFrame(results)
    per_page_df['week'] = per_page_df['week'].astype(str)
    return per_page_df


def calculate_funnel_data(page_visits, page_order=None, page_names=None):
    """Calculate funnel data across all pages in the journey."""
    if page_order is None:
        page_order = PAGE_ORDER
    if page_names is None:
        page_names = PAGE_NAMES

    if page_visits.empty:
        return pd.DataFrame()

    deduplicated = page_visits.sort_values('timestamp').drop_duplicates(subset=['user_id', 'path'], keep='first')

    funnel_data = []
    for page in page_order:
        page_data = deduplicated[deduplicated['path'] == page]
        funnel_data.append({
            'page': page,
            'page_name': page_names.get(page, page),
            'total_visits': len(page_data),
            'unique_users': page_data['user_id'].nunique() if not page_data.empty else 0,
        })

    return pd.DataFrame(funnel_data)
