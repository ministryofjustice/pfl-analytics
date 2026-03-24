"""Weekly overview tab."""
import streamlit as st
import plotly.express as px


def display_weekly_overview(weekly_summary):
    st.header("Weekly Overview")

    if weekly_summary.empty:
        st.info("No page visit data available")
        return

    weekly_totals = weekly_summary.groupby('week')['count'].sum().reset_index()
    fig = px.bar(weekly_totals, x='week', y='count',
                 title='Total Page Visits by Week',
                 labels={'week': 'Week', 'count': 'Total Visits'},
                 color='count', color_continuous_scale='Blues')
    fig.update_layout(height=400)
    st.plotly_chart(fig, width='stretch')

    st.subheader("Top Pages by Week")
    top_n = st.slider("Number of top pages to show", 5, 20, 10)

    for week in sorted(weekly_summary['week'].unique()):
        week_data = weekly_summary[weekly_summary['week'] == week].head(top_n)
        with st.expander(f"Week: {week}"):
            fig_top = px.bar(week_data, x='count', y='path', orientation='h',
                             title=f'Top {top_n} Pages',
                             labels={'count': 'Visits', 'path': 'Page Path'})
            fig_top.update_layout(height=300)
            st.plotly_chart(fig_top, width='stretch')
