"""File handling utilities."""
import pandas as pd
from io import BytesIO


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
