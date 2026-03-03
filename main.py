import pandas as pd
import re
import os

# Define directories
input_dir = "input"
output_dir = "output"

def process():
    # Ensure directories exist
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # List available files in input directory
    available_files = [f for f in os.listdir(input_dir) if f.endswith(('.xlsx', '.csv')) and not f.startswith('~$')]

    if not available_files:
        print(f"No Excel or CSV files found in the '{input_dir}/' directory.")
        print(f"Please add your data files to the '{input_dir}/' directory and run the script again.")
        exit(1)

    print("\nSelect the system you would like initiate the process for:")
    print("1. Care Arrangement Plan")
    print("2. Connecting Services")

    while True:
        systemSelection = input("\nEnter the number to select the system: ").strip()
        try:
            if int(systemSelection) > 0 and int(systemSelection) < 3:
                print(systemSelection)
                break
            else:
                print("Please enter the correct number")
        except ValueError:
            print("Please enter a valid number")

    print("Available files in input directory:")
    for idx, filename in enumerate(available_files, 1):
        print(f"{idx}. {filename}")

    while True:
        selection = input("\nEnter the number of the file you want to process: ").strip()
        try:
            file_index = int(selection) - 1
            if 0 <= file_index < len(available_files):
                input_filename = available_files[file_index]
                break
            else:
                print(f"Please enter a number between 1 and {len(available_files)}")
        except ValueError:
            print("Please enter a valid number")

    input_file = os.path.join(input_dir, input_filename)
    output_file= getOutputFile(systemSelection)

    # Read the file
    if input_file.endswith('.csv'):
        df_raw = pd.read_csv(input_file)
    else:
        df_raw = pd.read_excel(input_file)

    print(f"Loaded {len(df_raw)} rows from {input_file}")

    # Skip the first row if it's 'Log'
    if len(df_raw) > 0 and str(df_raw.iloc[0, 0]).strip() == 'Log':
        df_raw = df_raw.iloc[1:]
        print("Skipped 'Log' header row")

    # Parse the log entries into separate columns
    parsed_rows = []
    excluded_patterns = ['/assets', '/images', '/js', '/fonts', '/css']

    for idx, row in df_raw.iterrows():
        log_entry = str(row.iloc[0])

        # Extract fields using regex
        timestamp_match = re.search(r'timestamp=([^,\)]+)', log_entry)
        event_type_match = re.search(r'event_type=([^,\)]+)', log_entry)
        user_id_match = re.search(r'user_id=([^,\)]+)', log_entry)
        path_match = re.search(r'path=([^,\)]+)', log_entry)
        method_match = re.search(r'method=([^,\)]+)', log_entry)
        status_code_match = re.search(r'status_code=([^,\)]+)', log_entry)
        download_type_match = re.search(r'download_type=([^,\)]+)', log_entry)

        # Get path and event_type values
        path_value = path_match.group(1) if path_match else None
        event_type_value = event_type_match.group(1) if event_type_match else None

        # Skip if event_type is page_visit but no path
        if event_type_value == 'page_visit' and not path_value:
            continue

        # Skip if path matches excluded patterns
        if path_value:
            skip_row = False
            for pattern in excluded_patterns:
                if path_value.startswith(pattern):
                    skip_row = True
                    break
            if skip_row:
                continue

        parsed_row = {
            'timestamp': timestamp_match.group(1) if timestamp_match else None,
            'event_type': event_type_value,
            'user_id': user_id_match.group(1) if user_id_match else None,
            'path': path_value,
            'method': method_match.group(1) if method_match else None,
            'status_code': status_code_match.group(1) if status_code_match else None,
            'download_type': download_type_match.group(1) if download_type_match else None,
        }

        parsed_rows.append(parsed_row)

    # Create DataFrame with parsed columns
    df = pd.DataFrame(parsed_rows)

    print(f"\nParsed and filtered {len(df)} rows (excluded /assets, /images, /js, /fonts, /css)")

    # Remove rows where user_id is blank, None, 'unknown', or 'anonymous'
    original_count = len(df)
    df = df[df['user_id'].notna()]  # Remove None/NaN
    df = df[df['user_id'].str.strip() != '']  # Remove blank strings
    df = df[~df['user_id'].str.lower().isin(['unknown', 'anonymous'])]  # Remove 'unknown' or 'anonymous'

    removed_count = original_count - len(df)
    print(f"Removed {removed_count} rows with blank/unknown/anonymous user_id")
    print(f"Remaining rows: {len(df)}")

    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst 10 rows:")
    print(df.head(10))

    # Filter for page_visit events and create weekly summary
    page_visits = df[df['event_type'] == 'page_visit'].copy()

    # Calculate weekly summary
    weeklySummaryToWrite = getWeeklySummaryCAP(page_visits) if int(systemSelection) == 1 else getWeeklySummaryCS(page_visits)

    # Calculate weekly completion rate
    finalCompletionToWrite = getFinalCompletionCAP(page_visits) if int(systemSelection) == 1 else getFinalCompletionCS(page_visits)

    # Save to Excel with multiple sheets
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Parsed_Data', index=False)
        weeklySummaryToWrite.to_excel(writer, sheet_name='Weekly_Page_Visits', index=False)
        finalCompletionToWrite.to_excel(writer, sheet_name='Weekly_Completion_Rate', index=False)

    print(f"\nData saved to {output_file}")

def getWeeklySummaryCAP(page_visits):
    if not page_visits.empty and 'timestamp' in page_visits.columns:
        # Convert timestamp to datetime
        page_visits['timestamp'] = pd.to_datetime(page_visits['timestamp'])

        # Extract week
        page_visits['week'] = page_visits['timestamp'].dt.to_period('W')

        # Group by week and path, count occurrences
        weekly_summary = page_visits.groupby(['week', 'path']).size().reset_index(name='count')

        # Sort by week and count (descending within each week)
        weekly_summary = weekly_summary.sort_values(['week', 'count'], ascending=[True, False])

        # Add a blank row between weeks for readability
        formatted_weekly_summary = []
        current_week = None

        for idx, row in weekly_summary.iterrows():
            week_str = str(row['week'])

            # Add blank row between weeks (except for the first week)
            if current_week is not None and current_week != week_str:
                formatted_weekly_summary.append({'week': '', 'path': '', 'count': ''})

            formatted_weekly_summary.append({
                'week': week_str,
                'path': row['path'],
                'count': row['count']
            })

            current_week = week_str

        weekly_summary = pd.DataFrame(formatted_weekly_summary)

        print(f"\nWeekly page visit summary created with {len(weekly_summary)} rows")
    else:
        weekly_summary = pd.DataFrame(columns=['week', 'path', 'count'])
        print("\nNo page_visit events found or no timestamp column")

    return weekly_summary

def getWeeklySummaryCS(page_visits):
    if not page_visits.empty and 'timestamp' in page_visits.columns:
        # Convert timestamp to datetime
        page_visits['timestamp'] = pd.to_datetime(page_visits['timestamp'])

        # Extract week
        page_visits['week'] = page_visits['timestamp'].dt.to_period('W')

        # Group by week and path, count occurrences
        weekly_summary = page_visits.groupby(['week', 'path']).size().reset_index(name='count')

        # Sort by week and count (descending within each week)
        weekly_summary = weekly_summary.sort_values(['week', 'count'], ascending=[True, False])

        # Add a blank row between weeks for readability
        formatted_weekly_summary = []
        current_week = None

        for idx, row in weekly_summary.iterrows():
            week_str = str(row['week'])

            # Add blank row between weeks (except for the first week)
            if current_week is not None and current_week != week_str:
                formatted_weekly_summary.append({'week': '', 'path': '', 'count': ''})

            formatted_weekly_summary.append({
                'week': week_str,
                'path': row['path'],
                'count': row['count']
            })

            current_week = week_str

        weekly_summary = pd.DataFrame(formatted_weekly_summary)

        print(f"\nWeekly page visit summary created with {len(weekly_summary)} rows")
    else:
        weekly_summary = pd.DataFrame(columns=['week', 'path', 'count'])
        print("\nNo page_visit events found or no timestamp column")

    return weekly_summary

def getFinalCompletionCAP(page_visits):
    if not page_visits.empty and 'timestamp' in page_visits.columns:
        # Filter for safety-check and confirmation pages
        safety_check = page_visits[page_visits['path'].str.contains('safety-check', case=False, na=False)]
        confirmation = page_visits[page_visits['path'].str.contains('confirmation', case=False, na=False)]

        # Simple method: count totals per week (for unknown IDs)
        safety_check_weekly = safety_check.groupby('week').size().reset_index(name='safety_check_visits')
        confirmation_weekly = confirmation.groupby('week').size().reset_index(name='confirmation_visits')

        # Merge and calculate simple completion rate
        weekly_completion = pd.merge(safety_check_weekly, confirmation_weekly, on='week', how='outer').fillna(0)
        weekly_completion['simple_completion_rate'] = (weekly_completion['confirmation_visits'] / weekly_completion['safety_check_visits'] * 100).round(2)
        weekly_completion['simple_completion_rate'] = weekly_completion['simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # Advanced method: unique user completion (for known IDs)
        # Get unique user_id + week combinations for safety-check
        safety_check_users = safety_check.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
        # Get unique user_id + week combinations for confirmation
        confirmation_users = confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]

        # Mark users who reached each stage
        safety_check_users['reached_safety_check'] = 1
        confirmation_users['reached_confirmation'] = 1

        # Merge to find users who reached both stages
        user_completion = pd.merge(safety_check_users, confirmation_users, on=['week', 'user_id'], how='left').fillna(0)

        # Count unique users per week
        unique_safety_check = user_completion.groupby('week')['reached_safety_check'].sum().reset_index(name='unique_users_safety_check')
        unique_completed = user_completion[user_completion['reached_confirmation'] == 1].groupby('week').size().reset_index(name='unique_users_completed')

        # Merge and calculate user-based completion rate
        user_based_completion = pd.merge(unique_safety_check, unique_completed, on='week', how='outer').fillna(0)
        user_based_completion['user_completion_rate'] = (user_based_completion['unique_users_completed'] / user_based_completion['unique_users_safety_check'] * 100).round(2)
        user_based_completion['user_completion_rate'] = user_based_completion['user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # Combine both methods
        final_completion = pd.merge(weekly_completion, user_based_completion, on='week', how='outer').fillna(0)
        final_completion['week'] = final_completion['week'].astype(str)

        print(f"\nWeekly completion rate created with {len(final_completion)} rows")

    else:
        final_completion = pd.DataFrame(columns=['week', 'safety_check_visits', 'confirmation_visits', 'simple_completion_rate', 'unique_users_safety_check', 'unique_users_completed', 'user_completion_rate'])
        print("\nNo page_visit data for completion rate")

    return final_completion

def getFinalCompletionCS(page_visits):
    if not page_visits.empty and 'timestamp' in page_visits.columns:
        # Filter for domestic abuse and confirmation pages
        domestic_abuse = page_visits[page_visits['path'].str.contains('domestic-abuse', case=False, na=False)]
        confirmation = page_visits[page_visits['path'].str.contains('confirmation', case=False, na=False)]

        # Simple method: count totals per week (for unknown IDs)
        domestic_abuse_weekly = domestic_abuse.groupby('week').size().reset_index(name='domestic_abuse_visits')
        confirmation_weekly = confirmation.groupby('week').size().reset_index(name='confirmation_visits')

        # Merge and calculate simple completion rate
        weekly_completion = pd.merge(domestic_abuse_weekly, confirmation_weekly, on='week', how='outer').fillna(0)
        weekly_completion['simple_completion_rate'] = (weekly_completion['confirmation_visits'] / weekly_completion['domestic_abuse_visits'] * 100).round(2)
        weekly_completion['simple_completion_rate'] = weekly_completion['simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # Advanced method: unique user completion (for known IDs)
        # Get unique user_id + week combinations for domestic-abuse
        domestic_check_users = domestic_abuse.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
        # Get unique user_id + week combinations for confirmation
        confirmation_users = confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]

        # Mark users who reached each stage
        domestic_check_users['reached_domestic_abuse'] = 1
        confirmation_users['reached_confirmation'] = 1

        # Merge to find users who reached both stages
        user_completion = pd.merge(domestic_check_users, confirmation_users, on=['week', 'user_id'], how='left').fillna(0)

        # Count unique users per week
        unique_safety_check = user_completion.groupby('week')['reached_domestic_abuse'].sum().reset_index(name='unique_users_domestic_abuse')
        unique_completed = user_completion[user_completion['reached_confirmation'] == 1].groupby('week').size().reset_index(name='unique_users_completed')

        # Merge and calculate user-based completion rate
        user_based_completion = pd.merge(unique_safety_check, unique_completed, on='week', how='outer').fillna(0)
        user_based_completion['user_completion_rate'] = (user_based_completion['unique_users_completed'] / user_based_completion['unique_users_domestic_abuse'] * 100).round(2)
        user_based_completion['user_completion_rate'] = user_based_completion['user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # Combine both methods
        final_completion = pd.merge(weekly_completion, user_based_completion, on='week', how='outer').fillna(0)
        final_completion['week'] = final_completion['week'].astype(str)

        print(f"\nWeekly completion rate created with {len(final_completion)} rows")

    else:
        final_completion = pd.DataFrame(columns=['week', 'domestic_abuse_visits', 'confirmation_visits', 'simple_completion_rate', 'unique_users_domestic_abuse', 'unique_users_completed', 'user_completion_rate'])
        print("\nNo page_visit data for completion rate")

    return final_completion

def getOutputFile(systemSelection):
    if int(systemSelection) == 1:
        output_filename = "Data_Aggregation_Output_CAP.xlsx"
    else:
        output_filename = "Data_Aggregation_Output_CS.xlsx"
    return os.path.join(output_dir, output_filename)

process()
