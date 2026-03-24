"""Downloads analysis tab."""
import streamlit as st
import pandas as pd
import plotly.express as px

from ._event_tab import display_event_summary_metrics

_KNOWN_DOWNLOAD_TYPES = ['output_pdf', 'offline_pdf', 'output_html']


def _download_type_metrics_table(downloads):
    rows = []
    for dtype in downloads['download_type'].unique():
        dtype_data = downloads[downloads['download_type'] == dtype]
        unique = dtype_data['user_id'].nunique()
        rows.append({
            'Download Type': dtype,
            'Total Downloads': len(dtype_data),
            'Unique Users': unique,
            'Avg per User': f"{len(dtype_data) / unique:.2f}" if unique > 0 else "0.00"
        })
    st.dataframe(pd.DataFrame(rows), width='stretch')


def _downloads_timeline(downloads):
    if 'timestamp' not in downloads.columns:
        return
    st.subheader("Downloads Over Time")
    downloads = downloads.copy()
    downloads['timestamp'] = pd.to_datetime(downloads['timestamp'])
    downloads['date'] = downloads['timestamp'].dt.date
    by_date_type = downloads.groupby(['date', 'download_type']).size().reset_index(name='count')
    fig = px.line(by_date_type, x='date', y='count', color='download_type',
                  title='Downloads Over Time by Type',
                  labels={'date': 'Date', 'count': 'Number of Downloads', 'download_type': 'Download Type'},
                  markers=True)
    fig.update_layout(height=400)
    st.plotly_chart(fig, width='stretch')


def _download_type_details(downloads):
    st.subheader("Download Type Details")
    for dtype in _KNOWN_DOWNLOAD_TYPES:
        dtype_data = downloads[downloads['download_type'] == dtype]
        if dtype_data.empty:
            continue
        with st.expander(f"📄 {dtype.replace('_', ' ').title()} ({len(dtype_data)} downloads)"):
            unique = dtype_data['user_id'].nunique()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Downloads", f"{len(dtype_data):,}")
            with col2:
                st.metric("Unique Users", f"{unique:,}")
            with col3:
                avg = len(dtype_data) / unique if unique > 0 else 0
                st.metric("Avg per User", f"{avg:.2f}")
            if 'path' in dtype_data.columns:
                top = dtype_data['path'].value_counts().head(5)
                if not top.empty:
                    st.write(f"**Top pages for {dtype}:**")
                    st.dataframe(
                        top.reset_index().rename(columns={'index': 'Page', 'path': 'Downloads'}),
                        width='stretch'
                    )


def display_downloads(df):
    st.header("Downloads Analysis")

    downloads = df[df['event_type'] == 'download'].copy()

    if downloads.empty:
        st.info("No download data available")
        return

    display_event_summary_metrics(downloads, "Total Downloads", "Avg Downloads per User")
    st.divider()

    if 'download_type' not in downloads.columns:
        st.warning("No download_type field found in the data")
        return

    st.subheader("Downloads by Type")
    download_types = downloads['download_type'].value_counts().reset_index()
    download_types.columns = ['Download Type', 'Count']

    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(download_types, values='Count', names='Download Type',
                         title='Distribution of Download Types')
        st.plotly_chart(fig_pie, width='stretch')
    with col2:
        fig_bar = px.bar(download_types, x='Download Type', y='Count',
                         title='Download Count by Type',
                         color='Count', color_continuous_scale='Greens')
        st.plotly_chart(fig_bar, width='stretch')

    st.subheader("Metrics by Download Type")
    _download_type_metrics_table(downloads)
    _downloads_timeline(downloads)
    _download_type_details(downloads)
