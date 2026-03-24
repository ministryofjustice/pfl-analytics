"""Dashboard tab orchestrator."""
import streamlit as st

from .weekly_overview import display_weekly_overview
from .page_visits import display_page_visits
from .completion_rates import display_completion_rates
from .link_clicks import display_link_clicks
from .page_exits import display_page_exits
from .quick_exits import display_quick_exits
from .downloads import display_downloads
from .raw_data import display_raw_data


def display_all_tabs(df, weekly_summary, completion_rate, filtered_page_visits,
                     per_page_completion, funnel_data, completion_rate_cs=None):
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Weekly Overview",
        "🔍 Page Visits",
        "✅ Completion Rates",
        "🔗 Link Clicks",
        "🚪 Page Exits",
        "⚡ Quick Exits",
        "📥 Downloads",
        "📋 Raw Data"
    ])

    with tab1:
        display_weekly_overview(weekly_summary)
    with tab2:
        display_page_visits(filtered_page_visits)
    with tab3:
        display_completion_rates(completion_rate, per_page_completion, funnel_data, completion_rate_cs)
    with tab4:
        display_link_clicks(df)
    with tab5:
        display_page_exits(df)
    with tab6:
        display_quick_exits(df)
    with tab7:
        display_downloads(df)
    with tab8:
        display_raw_data(df, weekly_summary, completion_rate)
