"""Page visits analysis tab."""
import streamlit as st
import plotly.express as px


def display_page_visits(page_visits):
    st.header("Page Visits Analysis")

    if page_visits.empty:
        st.info("No page visit data available for the selected date range")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Most Visited Pages")
        top_pages = page_visits['path'].value_counts().head(10).reset_index()
        top_pages.columns = ['Page Path', 'Visits']
        fig = px.bar(top_pages, x='Visits', y='Page Path', orientation='h',
                     labels={'Visits': 'Visits', 'Page Path': 'Page Path'},
                     color='Visits', color_continuous_scale='Viridis')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.subheader("Visits Over Time")
        visits_by_date = page_visits.groupby(page_visits['timestamp'].dt.date).size().reset_index()
        visits_by_date.columns = ['date', 'count']
        fig_timeline = px.line(visits_by_date, x='date', y='count',
                               labels={'date': 'Date', 'count': 'Number of Visits'}, markers=True)
        fig_timeline.update_layout(height=400)
        st.plotly_chart(fig_timeline, width='stretch')

    st.subheader("Page Detail View")
    selected_path = st.selectbox("Select a page to view details",
                                 options=sorted(page_visits['path'].unique()))
    path_data = page_visits[page_visits['path'] == selected_path]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Visits", len(path_data))
    with col2:
        st.metric("Unique Users", path_data['user_id'].nunique())
    with col3:
        avg_visits = len(path_data) / path_data['user_id'].nunique()
        st.metric("Avg Visits per User", f"{avg_visits:.1f}")
