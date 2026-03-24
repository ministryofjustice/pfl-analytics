"""Link clicks analysis tab."""
import streamlit as st
import plotly.express as px

from ._event_tab import display_event_summary_metrics, display_event_timeline


def display_link_clicks(df):
    st.header("Link Clicks Analysis")

    link_clicks = df[df['event_type'] == 'link_click'].copy()

    if link_clicks.empty:
        st.info("No link click data available")
        return

    display_event_summary_metrics(link_clicks, "Total Link Clicks", "Avg Clicks per User")
    st.divider()
    display_event_timeline(link_clicks, "Link Clicks Over Time", "Number of Clicks")

    if 'link_type' in link_clicks.columns:
        link_type_data = link_clicks[link_clicks['link_type'].notna()]
        if not link_type_data.empty:
            st.subheader("Clicks by Link Type")
            link_type_counts = link_type_data['link_type'].value_counts().reset_index()
            link_type_counts.columns = ['Link Type', 'Count']
            col1, col2 = st.columns(2)
            with col1:
                for _, row in link_type_counts.iterrows():
                    st.metric(row['Link Type'].title(), f"{row['Count']:,}")
            with col2:
                fig = px.pie(link_type_counts, values='Count', names='Link Type',
                             title='Link Click Distribution by Type')
                st.plotly_chart(fig, width='stretch')

    st.subheader("Most Clicked Links")
    link_clicks_with_url = link_clicks[link_clicks['link_url'].notna()] if 'link_url' in link_clicks.columns else None

    if link_clicks_with_url is not None and not link_clicks_with_url.empty:
        top_links = link_clicks_with_url['link_url'].value_counts().head(10).reset_index()
        top_links.columns = ['Link', 'Clicks']
        fig_top = px.bar(top_links, x='Clicks', y='Link', orientation='h',
                         title='Top 10 Most Clicked Links',
                         labels={'Clicks': 'Number of Clicks', 'Link': 'Link'},
                         color='Clicks', color_continuous_scale='Purples')
        fig_top.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_top, width='stretch')
    else:
        st.info("No link URL data found. Check that log entries contain a 'link_url' field.")

    st.subheader("Link Clicks by Page")
    clicks_with_path = link_clicks[link_clicks['path'].notna()] if 'path' in link_clicks.columns else None

    if clicks_with_path is not None and not clicks_with_path.empty:
        clicks_by_path = clicks_with_path['path'].value_counts().head(10).reset_index()
        clicks_by_path.columns = ['Page Path', 'Number of Clicks']
        fig_path = px.bar(clicks_by_path, x='Number of Clicks', y='Page Path', orientation='h',
                          title='Top 10 Pages with Link Clicks',
                          labels={'Number of Clicks': 'Number of Clicks', 'Page Path': 'Page Path'},
                          color='Number of Clicks', color_continuous_scale='Blues')
        fig_path.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_path, width='stretch')
    else:
        st.info("No page path data found for link click events.")
