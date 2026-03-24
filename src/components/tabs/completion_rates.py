"""Completion rates analysis tab."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

_CS_JOURNEY_LABELS = {
    'getting_help':      'Getting Help',
    'parenting_plan':    'Parenting Plan',
    'options_no_contact': 'Options (No Contact)',
    'court_order':       'Court Order',
    'mediation':         'Mediation',
}


def _completion_rate_chart(completion_rate):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=completion_rate['week'], y=completion_rate['simple_completion_rate'],
        mode='lines+markers', name='Simple Completion Rate',
        line=dict(color='lightblue', width=3)
    ))
    fig.add_trace(go.Scatter(
        x=completion_rate['week'], y=completion_rate['user_completion_rate'],
        mode='lines+markers', name='User-Based Completion Rate',
        line=dict(color='darkblue', width=3)
    ))
    fig.update_layout(title='Completion Rates Over Time', xaxis_title='Week',
                      yaxis_title='Completion Rate (%)', height=400, hovermode='x unified')
    st.plotly_chart(fig, width='stretch')


def _weekly_breakdown_table(completion_rate):
    st.subheader("Weekly Breakdown")
    display_df = completion_rate.copy()
    display_df['simple_completion_rate'] = display_df['simple_completion_rate'].apply(lambda x: f"{x:.1f}%")
    display_df['user_completion_rate'] = display_df['user_completion_rate'].apply(lambda x: f"{x:.1f}%")
    display_df.columns = [
        'Week', 'Safety Check Visits', 'Confirmation Visits',
        'Simple Completion Rate', 'Unique Users (Safety Check)',
        'Unique Users (Completed)', 'User Completion Rate'
    ]
    st.dataframe(display_df, width='stretch')


def _per_page_section(per_page_completion):
    st.subheader("Per-Page Completion Rates")
    if per_page_completion.empty:
        return

    selected_week = st.selectbox(
        "Select week to view",
        options=['All Weeks'] + sorted(per_page_completion['week'].unique().tolist()),
        key='week_selector'
    )

    if selected_week == 'All Weeks':
        page_summary = per_page_completion.groupby('page').agg(
            {'total_visits': 'sum', 'unique_users': 'sum'}
        ).reset_index()
    else:
        page_summary = per_page_completion[per_page_completion['week'] == selected_week]

    st.dataframe(page_summary, width='stretch')

    col1, col2 = st.columns(2)
    with col1:
        fig_visits = px.bar(page_summary, x='page', y='total_visits',
                            title='Total Visits per Page',
                            labels={'page': 'Page', 'total_visits': 'Total Visits'},
                            color='total_visits', color_continuous_scale='Blues')
        fig_visits.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig_visits, width='stretch')
    with col2:
        fig_users = px.bar(page_summary, x='page', y='unique_users',
                           title='Unique Users per Page',
                           labels={'page': 'Page', 'unique_users': 'Unique Users'},
                           color='unique_users', color_continuous_scale='Greens')
        fig_users.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig_users, width='stretch')


def _funnel_section(funnel_data):
    st.subheader("Conversion Funnel")
    if funnel_data.empty:
        return

    fig_funnel = go.Figure(go.Funnel(
        y=funnel_data['page_name'], x=funnel_data['unique_users'],
        textposition="inside", textinfo="value+percent initial",
        marker=dict(color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                           '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
                           '#aec7e8', '#ffbb78'])
    ))
    fig_funnel.update_layout(height=600, title='User Journey Funnel (Unique Users)')
    st.plotly_chart(fig_funnel, width='stretch')

    st.subheader("Funnel Data")
    funnel_display = funnel_data.copy()
    if len(funnel_display) > 0:
        funnel_display['completion_rate'] = (
            funnel_display['unique_users'] / funnel_display['unique_users'].iloc[0] * 100
        ).round(2).apply(lambda x: f"{x:.1f}%")
    st.dataframe(funnel_display, width='stretch')


def _cs_journey_section(step_name, journey_df):
    label = _CS_JOURNEY_LABELS.get(step_name, step_name.replace('_', ' ').title())
    rate_col = f'{step_name}_user_completion_rate'
    simple_col = f'{step_name}_simple_completion_rate'

    if journey_df.empty or rate_col not in journey_df.columns:
        st.info(f"No data for {label}")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=journey_df['week'], y=journey_df[simple_col],
        mode='lines+markers', name='Simple Completion Rate',
        line=dict(color='lightblue', width=3)
    ))
    fig.add_trace(go.Scatter(
        x=journey_df['week'], y=journey_df[rate_col],
        mode='lines+markers', name='User-Based Completion Rate',
        line=dict(color='darkblue', width=3)
    ))
    fig.update_layout(title=f'{label} — Completion Rate Over Time', xaxis_title='Week',
                      yaxis_title='Completion Rate (%)', height=350, hovermode='x unified')
    st.plotly_chart(fig, width='stretch')
    st.dataframe(journey_df, width='stretch')


def display_completion_rates(completion_rate, per_page_completion, funnel_data, completion_rate_cs=None):
    st.header("Completion Rate Analysis")

    if not completion_rate.empty:
        _completion_rate_chart(completion_rate)
        _weekly_breakdown_table(completion_rate)
        _per_page_section(per_page_completion)
        _funnel_section(funnel_data)

    if completion_rate_cs:
        st.divider()
        st.subheader("Connecting Services — Journey Completion Rates")
        for step_name, journey_df in completion_rate_cs.items():
            label = _CS_JOURNEY_LABELS.get(step_name, step_name.replace('_', ' ').title())
            with st.expander(label):
                _cs_journey_section(step_name, journey_df)

    if completion_rate.empty and not completion_rate_cs:
        st.info("No completion rate data available")
