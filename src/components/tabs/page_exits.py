"""Page exits analysis tab."""
import streamlit as st
import plotly.express as px

from ._event_tab import display_event_summary_metrics, display_event_timeline


def display_page_exits(df):
    st.header("Page Exits Analysis")

    page_exits = df[df['event_type'] == 'page_exit'].copy()

    if page_exits.empty:
        st.info("No page exit data available")
        return

    display_event_summary_metrics(page_exits, "Total Page Exits", "Avg Exits per User")
    st.divider()
    display_event_timeline(page_exits, "Page Exits Over Time", "Number of Exits")

    if 'exit_page' in page_exits.columns:
        st.subheader("Exit Pages")
        exits_by_path = page_exits['exit_page'].value_counts().head(10).reset_index()
        exits_by_path.columns = ['Exit Page', 'Number of Exits']
        fig = px.bar(exits_by_path, x='Number of Exits', y='Exit Page', orientation='h',
                     title='Top 10 Exit Pages',
                     labels={'Number of Exits': 'Number of Exits', 'Exit Page': 'Exit Page'},
                     color='Number of Exits', color_continuous_scale='Reds')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, width='stretch')
