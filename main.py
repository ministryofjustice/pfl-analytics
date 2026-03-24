import os
import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_processing.parser import parse_log_data
from data_processing.metrics import (
    calculate_weekly_page_visits,
    calculate_completion_rate,
    calculate_completion_rate_cs,
)

INPUT_DIR = "input"
OUTPUT_DIR = "output"

_OUTPUT_FILES = {
    '1': "Data_Aggregation_Output_CAP.xlsx",
    '2': "Data_Aggregation_Output_CS.xlsx",
}


def _select_from_list(prompt, items, display=None):
    for idx, item in enumerate(items, 1):
        print(f"{idx}. {display(item) if display else item}")
    while True:
        raw = input(f"\n{prompt}: ").strip()
        try:
            index = int(raw) - 1
            if 0 <= index < len(items):
                return items[index]
            print(f"Please enter a number between 1 and {len(items)}")
        except ValueError:
            print("Please enter a valid number")


def _load_file(path):
    return pd.read_csv(path) if str(path).endswith('.csv') else pd.read_excel(path)


def _write_excel(output_path, sheets):
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def process():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    available_files = [
        f for f in os.listdir(INPUT_DIR)
        if f.endswith(('.xlsx', '.csv')) and not f.startswith('~$')
    ]

    if not available_files:
        print(f"No Excel or CSV files found in '{INPUT_DIR}/'. Add files and re-run.")
        sys.exit(1)

    print("\nSelect the system:")
    print("1. Care Arrangement Plan")
    print("2. Connecting Services")
    system = _select_from_list("Enter number", ['1', '2'])

    print("\nAvailable files:")
    selected_file = _select_from_list("Enter number of file to process", available_files)

    input_path = os.path.join(INPUT_DIR, selected_file)
    output_path = os.path.join(OUTPUT_DIR, _OUTPUT_FILES[system])

    df_raw = _load_file(input_path)
    print(f"Loaded {len(df_raw)} rows from {input_path}")

    df = parse_log_data(df_raw)
    df['service'] = 'CAP' if system == '1' else 'Connecting Services'
    print(f"Parsed {len(df)} rows after filtering")

    _, page_visits = calculate_weekly_page_visits(df)

    if system == '1':
        completion = calculate_completion_rate(page_visits)
        _write_excel(output_path, {
            'Parsed_Data': df,
            'Weekly_Page_Visits': page_visits,
            'Weekly_Completion_Rate': completion,
        })
    else:
        cs_completion = calculate_completion_rate_cs(page_visits)
        sheets = {'Parsed_Data': df, 'Weekly_Page_Visits': page_visits}
        sheet_names = {
            'getting_help':       'Getting_Help_Page_Visits',
            'parenting_plan':     'Parenting_Plan_Page_Visits',
            'options_no_contact': 'Options_No_Contact_Page_Visits',
            'court_order':        'Court_Order_Page_Visits',
            'mediation':          'Mediation_Page_Visits',
        }
        for step_name, sheet_name in sheet_names.items():
            sheets[sheet_name] = cs_completion.get(step_name, pd.DataFrame())
        _write_excel(output_path, sheets)

    print(f"\nData saved to {output_path}")


process()
