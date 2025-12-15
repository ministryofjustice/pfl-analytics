import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os
from io import BytesIO
from data_processor import process_log_file

# Page configuration
st.set_page_config(
    page_title="CAP Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Helper function to create Excel file with multiple sheets
def create_excel_download(dataframes_dict):
    """
    Create an Excel file with multiple sheets from a dictionary of DataFrames.

    Args:
        dataframes_dict: Dictionary with sheet names as keys and DataFrames as values

    Returns:
        BytesIO object containing the Excel file
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes_dict.items():
            # Create a copy to avoid modifying the original dataframe
            df_copy = df.copy()

            # Convert timezone-aware datetime columns to timezone-unaware
            for col in df_copy.select_dtypes(include=['datetime64[ns, UTC]', 'datetimetz']).columns:
                if hasattr(df_copy[col].dtype, 'tz') and df_copy[col].dtype.tz is not None:
                    df_copy[col] = df_copy[col].dt.tz_localize(None)

            df_copy.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output

# Title
st.title("📊 Care Arrangement Plan Analytics Dashboard")

# Sidebar for file selection
st.sidebar.header("Data Source")

input_dir = Path("input")
input_dir.mkdir(exist_ok=True)

# Get available files
available_files = [f for f in os.listdir(input_dir) if f.endswith(('.xlsx', '.csv')) and not f.startswith('~$')]

if not available_files:
    st.error(f"No Excel or CSV files found in the '{input_dir}/' directory.")
    st.info(f"Please add your data files to the '{input_dir}/' directory and refresh the page.")
    st.stop()

# File selector
selected_file = st.sidebar.selectbox(
    "Select a data file",
    available_files,
    help="Choose a log file to analyze"
)

# Process button
if st.sidebar.button("Load Data", type="primary"):
    st.session_state['load_data'] = True

# Load data on button click or if already loaded
if 'load_data' not in st.session_state:
    st.info("👈 Select a file from the sidebar and click 'Load Data' to begin")
    st.stop()

# Process the selected file
file_path = input_dir / selected_file

with st.spinner(f"Processing {selected_file}..."):
    try:
        data = process_log_file(str(file_path))
        st.success(f"✅ Successfully loaded {len(data['parsed_data'])} records")
    except Exception as e:
        st.error(f"Error processing file: {e}")
        st.stop()

# Extract data
df = data['parsed_data']
weekly_summary = data['weekly_summary']
completion_rate = data['completion_rate']
page_visits = data['page_visits']
per_page_completion = data['per_page_completion']
funnel_data = data['funnel_data']

# Metrics row
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
        # Count unique user-page combinations to avoid counting multiple visits to same page by same user
        unique_visits = page_visits.drop_duplicates(subset=['user_id', 'path']).shape[0]
        st.metric("Total Page Visits", f"{unique_visits:,}")
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

# Date range filter
if not page_visits.empty and 'timestamp' in page_visits.columns:
    st.sidebar.header("Filters")

    min_date = page_visits['timestamp'].min().date()
    max_date = page_visits['timestamp'].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Apply date filter
    if len(date_range) == 2:
        mask = (page_visits['timestamp'].dt.date >= date_range[0]) & (page_visits['timestamp'].dt.date <= date_range[1])
        filtered_page_visits = page_visits[mask]
    else:
        filtered_page_visits = page_visits
else:
    filtered_page_visits = page_visits

# Download section in sidebar
st.sidebar.header("📥 Download Data")

# Download individual datasets as CSV
st.sidebar.subheader("CSV Downloads")

# Parsed Data CSV
csv_parsed = df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="📄 Download Parsed Data (CSV)",
    data=csv_parsed,
    file_name=f"parsed_data_{selected_file.split('.')[0]}.csv",
    mime="text/csv",
    use_container_width=True
)

# Weekly Summary CSV
if not weekly_summary.empty:
    csv_weekly = weekly_summary.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📅 Download Weekly Summary (CSV)",
        data=csv_weekly,
        file_name=f"weekly_summary_{selected_file.split('.')[0]}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Completion Rate CSV
if not completion_rate.empty:
    csv_completion = completion_rate.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="✅ Download Completion Rates (CSV)",
        data=csv_completion,
        file_name=f"completion_rate_{selected_file.split('.')[0]}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Page Visits CSV
if not page_visits.empty:
    csv_visits = page_visits.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="🔍 Download Page Visits (CSV)",
        data=csv_visits,
        file_name=f"page_visits_{selected_file.split('.')[0]}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Download all data as Excel
st.sidebar.subheader("Excel Download (All Data)")

# Prepare all dataframes
all_data = {
    'Parsed Data': df,
    'Page Visits': page_visits if not page_visits.empty else pd.DataFrame(),
    'Weekly Summary': weekly_summary if not weekly_summary.empty else pd.DataFrame(),
    'Completion Rate': completion_rate if not completion_rate.empty else pd.DataFrame(),
    'Per Page Completion': per_page_completion if not per_page_completion.empty else pd.DataFrame(),
    'Funnel Data': funnel_data if not funnel_data.empty else pd.DataFrame()
}

# Create Excel file
excel_file = create_excel_download(all_data)

st.sidebar.download_button(
    label="📊 Download All Data (Excel)",
    data=excel_file,
    file_name=f"cap_analytics_all_data_{selected_file.split('.')[0]}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
    help="Downloads all data (Parsed Data, Page Visits, Weekly Summary, and Completion Rates) in a single Excel file with multiple sheets"
)

# Tabs for different views
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
    st.header("Weekly Overview")

    if not weekly_summary.empty:
        # Weekly total visits chart
        weekly_totals = weekly_summary.groupby('week')['count'].sum().reset_index()

        fig_weekly = px.bar(
            weekly_totals,
            x='week',
            y='count',
            title='Total Page Visits by Week',
            labels={'week': 'Week', 'count': 'Total Visits'},
            color='count',
            color_continuous_scale='Blues'
        )
        fig_weekly.update_layout(height=400)
        st.plotly_chart(fig_weekly, use_container_width=True)

        # Top pages per week
        st.subheader("Top Pages by Week")
        top_n = st.slider("Number of top pages to show", 5, 20, 10)

        for week in sorted(weekly_summary['week'].unique()):
            week_data = weekly_summary[weekly_summary['week'] == week].head(top_n)

            with st.expander(f"Week: {week}"):
                fig_top = px.bar(
                    week_data,
                    x='count',
                    y='path',
                    orientation='h',
                    title=f'Top {top_n} Pages',
                    labels={'count': 'Visits', 'path': 'Page Path'}
                )
                fig_top.update_layout(height=300)
                st.plotly_chart(fig_top, use_container_width=True)
    else:
        st.info("No page visit data available")

with tab2:
    st.header("Page Visits Analysis")

    if not filtered_page_visits.empty:
        # Most visited pages
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Most Visited Pages")
            top_pages = filtered_page_visits['path'].value_counts().head(10)

            fig_pages = px.bar(
                x=top_pages.values,
                y=top_pages.index,
                orientation='h',
                labels={'x': 'Visits', 'y': 'Page Path'},
                color=top_pages.values,
                color_continuous_scale='Viridis'
            )
            fig_pages.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_pages, use_container_width=True)

        with col2:
            st.subheader("Visits Over Time")
            visits_by_date = filtered_page_visits.groupby(filtered_page_visits['timestamp'].dt.date).size().reset_index()
            visits_by_date.columns = ['date', 'count']

            fig_timeline = px.line(
                visits_by_date,
                x='date',
                y='count',
                labels={'date': 'Date', 'count': 'Number of Visits'},
                markers=True
            )
            fig_timeline.update_layout(height=400)
            st.plotly_chart(fig_timeline, use_container_width=True)

        # Path selector for detailed view
        st.subheader("Page Detail View")
        selected_path = st.selectbox(
            "Select a page to view details",
            options=sorted(filtered_page_visits['path'].unique())
        )

        path_data = filtered_page_visits[filtered_page_visits['path'] == selected_path]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Visits", len(path_data))
        with col2:
            st.metric("Unique Users", path_data['user_id'].nunique())
        with col3:
            avg_visits = len(path_data) / path_data['user_id'].nunique()
            st.metric("Avg Visits per User", f"{avg_visits:.1f}")
    else:
        st.info("No page visit data available for the selected date range")

with tab3:
    st.header("Completion Rate Analysis")

    if not completion_rate.empty:
        # Completion rate over time
        fig_completion = go.Figure()

        fig_completion.add_trace(go.Scatter(
            x=completion_rate['week'],
            y=completion_rate['simple_completion_rate'],
            mode='lines+markers',
            name='Simple Completion Rate',
            line=dict(color='lightblue', width=3)
        ))

        fig_completion.add_trace(go.Scatter(
            x=completion_rate['week'],
            y=completion_rate['user_completion_rate'],
            mode='lines+markers',
            name='User-Based Completion Rate',
            line=dict(color='darkblue', width=3)
        ))

        fig_completion.update_layout(
            title='Completion Rates Over Time',
            xaxis_title='Week',
            yaxis_title='Completion Rate (%)',
            height=400,
            hovermode='x unified'
        )
        st.plotly_chart(fig_completion, use_container_width=True)

        # Detailed metrics
        st.subheader("Weekly Breakdown")

        # Format the dataframe for display
        display_df = completion_rate.copy()
        display_df['simple_completion_rate'] = display_df['simple_completion_rate'].apply(lambda x: f"{x:.1f}%")
        display_df['user_completion_rate'] = display_df['user_completion_rate'].apply(lambda x: f"{x:.1f}%")

        # Rename columns for better readability
        display_df.columns = [
            'Week',
            'Safety Check Visits',
            'Confirmation Visits',
            'Simple Completion Rate',
            'Unique Users (Safety Check)',
            'Unique Users (Completed)',
            'User Completion Rate'
        ]

        st.dataframe(display_df, use_container_width=True)

        # Per-page completion rates
        st.subheader("Per-Page Completion Rates")

        if not per_page_completion.empty:
            # Allow user to select week
            selected_week = st.selectbox(
                "Select week to view",
                options=['All Weeks'] + sorted(per_page_completion['week'].unique().tolist()),
                key='week_selector'
            )

            if selected_week == 'All Weeks':
                # Aggregate across all weeks
                page_summary = per_page_completion.groupby('page').agg({
                    'total_visits': 'sum',
                    'unique_users': 'sum'
                }).reset_index()
            else:
                # Filter for selected week
                page_summary = per_page_completion[per_page_completion['week'] == selected_week]

            # Display as a table
            st.dataframe(page_summary, use_container_width=True)

            # Visualize as bar chart
            col1, col2 = st.columns(2)

            with col1:
                fig_visits = px.bar(
                    page_summary,
                    x='page',
                    y='total_visits',
                    title='Total Visits per Page',
                    labels={'page': 'Page', 'total_visits': 'Total Visits'},
                    color='total_visits',
                    color_continuous_scale='Blues'
                )
                fig_visits.update_layout(height=400, xaxis_tickangle=-45)
                st.plotly_chart(fig_visits, use_container_width=True)

            with col2:
                fig_users = px.bar(
                    page_summary,
                    x='page',
                    y='unique_users',
                    title='Unique Users per Page',
                    labels={'page': 'Page', 'unique_users': 'Unique Users'},
                    color='unique_users',
                    color_continuous_scale='Greens'
                )
                fig_users.update_layout(height=400, xaxis_tickangle=-45)
                st.plotly_chart(fig_users, use_container_width=True)

        # Funnel visualization
        st.subheader("Conversion Funnel")

        if not funnel_data.empty:
            # Use unique users for the funnel
            fig_funnel = go.Figure(go.Funnel(
                y=funnel_data['page_name'],
                x=funnel_data['unique_users'],
                textposition="inside",
                textinfo="value+percent initial",
                marker=dict(color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                                   '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
                                   '#aec7e8', '#ffbb78'])
            ))

            fig_funnel.update_layout(
                height=600,
                title='User Journey Funnel (Unique Users)'
            )
            st.plotly_chart(fig_funnel, use_container_width=True)

            # Show the funnel data table
            st.subheader("Funnel Data")
            funnel_display = funnel_data.copy()

            # Calculate drop-off percentage
            if len(funnel_display) > 0:
                funnel_display['completion_rate'] = (funnel_display['unique_users'] / funnel_display['unique_users'].iloc[0] * 100).round(2)
                funnel_display['completion_rate'] = funnel_display['completion_rate'].apply(lambda x: f"{x:.1f}%")

            st.dataframe(funnel_display, use_container_width=True)
    else:
        st.info("No completion rate data available")

with tab4:
    st.header("Link Clicks Analysis")

    # Filter for link_click events
    link_clicks = df[df['event_type'] == 'link_click'].copy()

    if not link_clicks.empty:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Link Clicks", f"{len(link_clicks):,}")

        with col2:
            unique_users_clicks = link_clicks['user_id'].nunique()
            st.metric("Unique Users", f"{unique_users_clicks:,}")

        with col3:
            avg_clicks = len(link_clicks) / unique_users_clicks if unique_users_clicks > 0 else 0
            st.metric("Avg Clicks per User", f"{avg_clicks:.1f}")

        st.divider()

        # Link clicks over time
        if 'timestamp' in link_clicks.columns:
            link_clicks['timestamp'] = pd.to_datetime(link_clicks['timestamp'])
            link_clicks['date'] = link_clicks['timestamp'].dt.date

            clicks_by_date = link_clicks.groupby('date').size().reset_index(name='count')

            fig_clicks_timeline = px.line(
                clicks_by_date,
                x='date',
                y='count',
                title='Link Clicks Over Time',
                labels={'date': 'Date', 'count': 'Number of Clicks'},
                markers=True
            )
            fig_clicks_timeline.update_layout(height=400)
            st.plotly_chart(fig_clicks_timeline, use_container_width=True)

        # Most clicked links by path
        if 'path' in link_clicks.columns:
            st.subheader("Link Clicks by Page")
            clicks_by_path = link_clicks['path'].value_counts().head(10)

            fig_clicks_path = px.bar(
                x=clicks_by_path.values,
                y=clicks_by_path.index,
                orientation='h',
                title='Top 10 Pages with Link Clicks',
                labels={'x': 'Number of Clicks', 'y': 'Page Path'},
                color=clicks_by_path.values,
                color_continuous_scale='Blues'
            )
            fig_clicks_path.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_clicks_path, use_container_width=True)
    else:
        st.info("No link click data available")

with tab5:
    st.header("Page Exits Analysis")

    # Filter for page_exit events
    page_exits = df[df['event_type'] == 'page_exit'].copy()

    if not page_exits.empty:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Page Exits", f"{len(page_exits):,}")

        with col2:
            unique_users_exits = page_exits['user_id'].nunique()
            st.metric("Unique Users", f"{unique_users_exits:,}")

        with col3:
            avg_exits = len(page_exits) / unique_users_exits if unique_users_exits > 0 else 0
            st.metric("Avg Exits per User", f"{avg_exits:.1f}")

        st.divider()

        # Page exits over time
        if 'timestamp' in page_exits.columns:
            page_exits['timestamp'] = pd.to_datetime(page_exits['timestamp'])
            page_exits['date'] = page_exits['timestamp'].dt.date

            exits_by_date = page_exits.groupby('date').size().reset_index(name='count')

            fig_exits_timeline = px.line(
                exits_by_date,
                x='date',
                y='count',
                title='Page Exits Over Time',
                labels={'date': 'Date', 'count': 'Number of Exits'},
                markers=True
            )
            fig_exits_timeline.update_layout(height=400)
            st.plotly_chart(fig_exits_timeline, use_container_width=True)

        # Most common exit pages
        if 'exit_page' in page_exits.columns:
            st.subheader("Exit Pages")
            exits_by_path = page_exits['exit_page'].value_counts().head(10)

            fig_exits_path = px.bar(
                x=exits_by_path.values,
                y=exits_by_path.index,
                orientation='h',
                title='Top 10 Exit Pages',
                labels={'x': 'Number of Exits', 'y': 'Exit Page'},
                color=exits_by_path.values,
                color_continuous_scale='Reds'
            )
            fig_exits_path.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_exits_path, use_container_width=True)
    else:
        st.info("No page exit data available")

with tab6:
    st.header("Quick Exits Analysis")

    # Filter for quick_exit events
    quick_exits = df[df['event_type'] == 'quick_exit'].copy()

    if not quick_exits.empty:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Quick Exits", f"{len(quick_exits):,}")

        with col2:
            unique_users_quick = quick_exits['user_id'].nunique()
            st.metric("Unique Users", f"{unique_users_quick:,}")

        with col3:
            avg_quick = len(quick_exits) / unique_users_quick if unique_users_quick > 0 else 0
            st.metric("Avg Quick Exits per User", f"{avg_quick:.1f}")

        st.divider()

        # Quick exits over time
        if 'timestamp' in quick_exits.columns:
            quick_exits['timestamp'] = pd.to_datetime(quick_exits['timestamp'])
            quick_exits['date'] = quick_exits['timestamp'].dt.date

            quick_by_date = quick_exits.groupby('date').size().reset_index(name='count')

            fig_quick_timeline = px.line(
                quick_by_date,
                x='date',
                y='count',
                title='Quick Exits Over Time',
                labels={'date': 'Date', 'count': 'Number of Quick Exits'},
                markers=True
            )
            fig_quick_timeline.update_layout(height=400)
            st.plotly_chart(fig_quick_timeline, use_container_width=True)

        # Most common quick exit pages
        if 'exit_page' in quick_exits.columns:
            st.subheader("Quick Exit Pages")
            st.write("Pages where users quickly exit")

            quick_by_path = quick_exits['exit_page'].value_counts().head(10)

            fig_quick_path = px.bar(
                x=quick_by_path.values,
                y=quick_by_path.index,
                orientation='h',
                title='Top 10 Quick Exit Pages',
                labels={'x': 'Number of Quick Exits', 'y': 'Exit Page'},
                color=quick_by_path.values,
                color_continuous_scale='Oranges'
            )
            fig_quick_path.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_quick_path, use_container_width=True)
    else:
        st.info("No quick exit data available")

with tab7:
    st.header("Downloads Analysis")

    # Filter for download events
    downloads = df[df['event_type'] == 'download'].copy()

    if not downloads.empty:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Downloads", f"{len(downloads):,}")

        with col2:
            unique_users_downloads = downloads['user_id'].nunique()
            st.metric("Unique Users", f"{unique_users_downloads:,}")

        with col3:
            avg_downloads = len(downloads) / unique_users_downloads if unique_users_downloads > 0 else 0
            st.metric("Avg Downloads per User", f"{avg_downloads:.1f}")

        st.divider()

        # Downloads by type
        if 'download_type' in downloads.columns:
            st.subheader("Downloads by Type")

            download_types = downloads['download_type'].value_counts().reset_index()
            download_types.columns = ['Download Type', 'Count']

            col1, col2 = st.columns(2)

            with col1:
                fig_download_pie = px.pie(
                    download_types,
                    values='Count',
                    names='Download Type',
                    title='Distribution of Download Types'
                )
                st.plotly_chart(fig_download_pie, use_container_width=True)

            with col2:
                fig_download_bar = px.bar(
                    download_types,
                    x='Download Type',
                    y='Count',
                    title='Download Count by Type',
                    color='Count',
                    color_continuous_scale='Greens'
                )
                st.plotly_chart(fig_download_bar, use_container_width=True)

            # Detailed metrics for each download type
            st.subheader("Metrics by Download Type")

            download_type_metrics = []
            for dtype in downloads['download_type'].unique():
                dtype_data = downloads[downloads['download_type'] == dtype]
                download_type_metrics.append({
                    'Download Type': dtype,
                    'Total Downloads': len(dtype_data),
                    'Unique Users': dtype_data['user_id'].nunique(),
                    'Avg per User': f"{len(dtype_data) / dtype_data['user_id'].nunique():.2f}" if dtype_data['user_id'].nunique() > 0 else "0.00"
                })

            metrics_df = pd.DataFrame(download_type_metrics)
            st.dataframe(metrics_df, use_container_width=True)

            # Downloads over time
            if 'timestamp' in downloads.columns:
                st.subheader("Downloads Over Time")

                downloads['timestamp'] = pd.to_datetime(downloads['timestamp'])
                downloads['date'] = downloads['timestamp'].dt.date

                downloads_by_date_type = downloads.groupby(['date', 'download_type']).size().reset_index(name='count')

                fig_downloads_timeline = px.line(
                    downloads_by_date_type,
                    x='date',
                    y='count',
                    color='download_type',
                    title='Downloads Over Time by Type',
                    labels={'date': 'Date', 'count': 'Number of Downloads', 'download_type': 'Download Type'},
                    markers=True
                )
                fig_downloads_timeline.update_layout(height=400)
                st.plotly_chart(fig_downloads_timeline, use_container_width=True)

            # Specific metrics for each type
            st.subheader("Download Type Details")

            for dtype in ['output_pdf', 'offline_pdf', 'output_html']:
                dtype_data = downloads[downloads['download_type'] == dtype]

                if not dtype_data.empty:
                    with st.expander(f"📄 {dtype.replace('_', ' ').title()} ({len(dtype_data)} downloads)"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Total Downloads", f"{len(dtype_data):,}")

                        with col2:
                            unique_users_type = dtype_data['user_id'].nunique()
                            st.metric("Unique Users", f"{unique_users_type:,}")

                        with col3:
                            avg_type = len(dtype_data) / unique_users_type if unique_users_type > 0 else 0
                            st.metric("Avg per User", f"{avg_type:.2f}")

                        # Downloads by page
                        if 'path' in dtype_data.columns:
                            type_by_path = dtype_data['path'].value_counts().head(5)
                            if not type_by_path.empty:
                                st.write(f"**Top pages for {dtype}:**")
                                st.dataframe(type_by_path.reset_index().rename(columns={'index': 'Page', 'path': 'Downloads'}), use_container_width=True)
        else:
            st.warning("No download_type field found in the data")
    else:
        st.info("No download data available")

with tab8:
    st.header("Raw Data")

    # Data selector
    data_view = st.selectbox(
        "Select data to view",
        ["Parsed Data", "Weekly Summary", "Completion Rate"]
    )

    if data_view == "Parsed Data":
        st.subheader("Parsed Log Data")
        st.dataframe(df, use_container_width=True)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="parsed_data.csv",
            mime="text/csv"
        )

    elif data_view == "Weekly Summary":
        st.subheader("Weekly Page Visits Summary")
        st.dataframe(weekly_summary, use_container_width=True)

        csv = weekly_summary.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="weekly_summary.csv",
            mime="text/csv"
        )

    elif data_view == "Completion Rate":
        st.subheader("Weekly Completion Rates")
        st.dataframe(completion_rate, use_container_width=True)

        csv = completion_rate.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="completion_rate.csv",
            mime="text/csv"
        )

# Footer
st.divider()
st.caption(f"📁 Current file: {selected_file} | 📊 Dashboard generated with Streamlit")
