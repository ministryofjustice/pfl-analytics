"""Shared helpers for single-event-type analysis tabs."""
import streamlit as st
import pandas as pd
import plotly.express as px


def display_event_summary_metrics(events, label_total, label_avg):
    col1, col2, col3 = st.columns(3)
    unique_users = events['user_id'].nunique()
    avg = len(events) / unique_users if unique_users > 0 else 0
    with col1:
        st.metric(label_total, f"{len(events):,}")
    with col2:
        st.metric("Unique Users", f"{unique_users:,}")
    with col3:
        st.metric(label_avg, f"{avg:.1f}")


def display_event_timeline(events, title, y_label):
    if 'timestamp' not in events.columns:
        return
    events = events.copy()
    events['timestamp'] = pd.to_datetime(events['timestamp'])
    events['date'] = events['timestamp'].dt.date
    by_date = events.groupby('date').size().reset_index(name='count')
    fig = px.line(by_date, x='date', y='count', title=title,
                  labels={'date': 'Date', 'count': y_label}, markers=True)
    fig.update_layout(height=400)
    st.plotly_chart(fig, width='stretch')


def display_top_bar_chart(data, x_col, y_col, title, color_scale, height=400):
    fig = px.bar(data, x=x_col, y=y_col, orientation='h', title=title,
                 labels={x_col: x_col, y_col: y_col},
                 color=x_col, color_continuous_scale=color_scale)
    fig.update_layout(height=height, showlegend=False)
    st.plotly_chart(fig, width='stretch')
