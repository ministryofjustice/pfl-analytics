import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os
from data_processor import process_log_file

# Page configuration
st.set_page_config(
    page_title="CAP Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

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

# Metrics row
st.header("📈 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Records", f"{len(df):,}")

with col2:
    unique_users = df['user_id'].nunique()
    st.metric("Unique Users", f"{unique_users:,}")

with col3:
    if not page_visits.empty:
        total_visits = len(page_visits)
        st.metric("Total Page Visits", f"{total_visits:,}")
    else:
        st.metric("Total Page Visits", "0")

with col4:
    if not completion_rate.empty and 'user_completion_rate' in completion_rate.columns:
        avg_completion = completion_rate['user_completion_rate'].mean()
        st.metric("Avg Completion Rate", f"{avg_completion:.1f}%")
    else:
        st.metric("Avg Completion Rate", "N/A")

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

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📊 Weekly Overview", "🔍 Page Visits", "✅ Completion Rates", "📋 Raw Data"])

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

        # Funnel visualization
        st.subheader("Conversion Funnel")

        total_safety_check = completion_rate['safety_check_visits'].sum()
        total_confirmation = completion_rate['confirmation_visits'].sum()

        fig_funnel = go.Figure(go.Funnel(
            y=['Started (Safety Check)', 'Completed (Confirmation)'],
            x=[total_safety_check, total_confirmation],
            textposition="inside",
            textinfo="value+percent initial"
        ))

        fig_funnel.update_layout(height=400)
        st.plotly_chart(fig_funnel, use_container_width=True)
    else:
        st.info("No completion rate data available")

with tab4:
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
