"""Dashboard tab orchestrator."""
import os
import streamlit as st

from .weekly_overview import display_weekly_overview
from .page_visits import display_page_visits
from .completion_rates import display_completion_rates
from .link_clicks import display_link_clicks
from .page_exits import display_page_exits
from .quick_exits import display_quick_exits
from .downloads import display_downloads
from .raw_data import display_raw_data

LOCAL_DEV = os.getenv("LOCAL_DEV", "false").lower() == "true"


def display_all_tabs(df, weekly_summary, completion_rate, filtered_page_visits,
                     per_page_completion, funnel_data, completion_rate_cs=None):
    tab_labels = [
        "📊 Weekly Overview",
        "🔍 Page Visits",
        "✅ Completion Rates",
        "🔗 Link Clicks",
        "🚪 Page Exits",
        "⚡ Quick Exits",
        "📥 Downloads",
    ]
    if LOCAL_DEV:
        tab_labels.append("📋 Raw Data")

    tabs = st.tabs(tab_labels)

    with tabs[0]:
        display_weekly_overview(weekly_summary)
    with tabs[1]:
        display_page_visits(filtered_page_visits)
    with tabs[2]:
        display_completion_rates(completion_rate, per_page_completion, funnel_data, completion_rate_cs)
    with tabs[3]:
        display_link_clicks(df)
    with tabs[4]:
        display_page_exits(df)
    with tabs[5]:
        display_quick_exits(df)
    with tabs[6]:
        display_downloads(df)
    if LOCAL_DEV:
        with tabs[7]:
            display_raw_data(df, weekly_summary, completion_rate)
