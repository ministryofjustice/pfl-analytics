"""Quick exits analysis tab."""
import streamlit as st
import plotly.express as px

from ._event_tab import display_event_summary_metrics, display_event_timeline


def display_quick_exits(df):
    st.header("Quick Exits Analysis")

    quick_exits = df[df['event_type'] == 'quick_exit'].copy()

    if quick_exits.empty:
        st.info("No quick exit data available")
        return

    display_event_summary_metrics(quick_exits, "Total Quick Exits", "Avg Quick Exits per User")
    st.divider()
    display_event_timeline(quick_exits, "Quick Exits Over Time", "Number of Quick Exits")

    if 'exit_page' in quick_exits.columns:
        st.subheader("Quick Exit Pages")
        quick_by_path = quick_exits['exit_page'].value_counts().head(10).reset_index()
        quick_by_path.columns = ['Exit Page', 'Number of Quick Exits']
        fig = px.bar(quick_by_path, x='Number of Quick Exits', y='Exit Page', orientation='h',
                     title='Top 10 Quick Exit Pages',
                     labels={'Number of Quick Exits': 'Number of Quick Exits', 'Exit Page': 'Exit Page'},
                     color='Number of Quick Exits', color_continuous_scale='Oranges')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, width='stretch')
