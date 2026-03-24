"""Components for displaying key metrics."""
import streamlit as st


def display_key_metrics(df, page_visits, completion_rate, completion_rate_cs=None):
    st.header("📈 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Records", f"{len(df):,}")

    with col2:
        st.metric("Unique Users", f"{df['user_id'].nunique():,}")

    with col3:
        if not page_visits.empty:
            total_visits = len(page_visits)
            unique_visits = page_visits.drop_duplicates(subset=['user_id', 'path']).shape[0]
            st.metric("Total Page Visits", f"{total_visits:,}", delta=f"{unique_visits:,} unique",
                      help="Total page visit events (delta shows unique user-page combinations after deduplication)")
        else:
            st.metric("Total Page Visits", "0")

    with col4:
        if not completion_rate.empty and 'user_completion_rate' in completion_rate.columns:
            avg_completion = completion_rate['user_completion_rate'].mean()
            st.metric("Avg Completion Rate (CAP)", f"{avg_completion:.1f}%")
        elif completion_rate_cs:
            rates = [
                df[f'{step}_user_completion_rate'].mean()
                for step, df in completion_rate_cs.items()
                if f'{step}_user_completion_rate' in df.columns and not df.empty
            ]
            avg_cs = sum(rates) / len(rates) if rates else 0
            st.metric("Avg Completion Rate (CS)", f"{avg_cs:.1f}%")
        else:
            st.metric("Avg Completion Rate", "N/A")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Link Clicks", f"{len(df[df['event_type'] == 'link_click']):,}")

    with col2:
        st.metric("Total Page Exits", f"{len(df[df['event_type'] == 'page_exit']):,}")

    with col3:
        st.metric("Total Quick Exits", f"{len(df[df['event_type'] == 'quick_exit']):,}")

    with col4:
        st.metric("Total Downloads", f"{len(df[df['event_type'] == 'download']):,}")

    st.divider()
