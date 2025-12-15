"""Components for displaying key metrics."""
import streamlit as st


def display_key_metrics(df, page_visits, completion_rate):
    """Display key metrics section."""
    st.header("📈 Key Metrics")

    # First row - general metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Records", f"{len(df):,}")

    with col2:
        unique_users = df['user_id'].nunique()
        st.metric("Unique Users", f"{unique_users:,}")

    with col3:
        if not page_visits.empty:
            # Count total page visits (before deduplication)
            total_visits = len(page_visits)
            # Count unique user-page combinations (after deduplication)
            unique_visits = page_visits.drop_duplicates(subset=['user_id', 'path']).shape[0]
            st.metric(
                "Total Page Visits",
                f"{total_visits:,}",
                delta=f"{unique_visits:,} unique",
                help="Total page visit events (delta shows unique user-page combinations after deduplication)"
            )
        else:
            st.metric("Total Page Visits", "0")

    with col4:
        if not completion_rate.empty and 'user_completion_rate' in completion_rate.columns:
            avg_completion = completion_rate['user_completion_rate'].mean()
            st.metric("Avg Completion Rate", f"{avg_completion:.1f}%")
        else:
            st.metric("Avg Completion Rate", "N/A")

    # Second row - event type metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        link_clicks_count = len(df[df['event_type'] == 'link_click'])
        st.metric("Total Link Clicks", f"{link_clicks_count:,}")

    with col2:
        page_exits_count = len(df[df['event_type'] == 'page_exit'])
        st.metric("Total Page Exits", f"{page_exits_count:,}")

    with col3:
        quick_exits_count = len(df[df['event_type'] == 'quick_exit'])
        st.metric("Total Quick Exits", f"{quick_exits_count:,}")

    with col4:
        downloads_count = len(df[df['event_type'] == 'download'])
        st.metric("Total Downloads", f"{downloads_count:,}")

    st.divider()
