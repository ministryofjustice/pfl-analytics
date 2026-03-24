"""Raw data tab."""
import streamlit as st


def _csv_download(df, filename):
    st.download_button(label="Download as CSV", data=df.to_csv(index=False),
                       file_name=filename, mime="text/csv")


def display_raw_data(df, weekly_summary, completion_rate):
    st.header("Raw Data")

    data_view = st.selectbox("Select data to view",
                             ["Parsed Data", "Weekly Summary", "Completion Rate"])

    if data_view == "Parsed Data":
        st.subheader("Parsed Log Data")
        st.dataframe(df, width='stretch')
        _csv_download(df, "parsed_data.csv")

    elif data_view == "Weekly Summary":
        st.subheader("Weekly Page Visits Summary")
        st.dataframe(weekly_summary, width='stretch')
        _csv_download(weekly_summary, "weekly_summary.csv")

    elif data_view == "Completion Rate":
        st.subheader("Weekly Completion Rates")
        st.dataframe(completion_rate, width='stretch')
        _csv_download(completion_rate, "completion_rate.csv")
