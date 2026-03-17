import numpy as np
import pandas as pd
import re
import os
from functools import reduce

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

    if int(systemSelection) == 1:

        # Calculate weekly completion rate
        finalCompletionToWrite = getFinalCompletionCAP(page_visits)

        # Save to Excel with multiple sheets
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Parsed_Data', index=False)
            weeklySummaryToWrite.to_excel(writer, sheet_name='Weekly_Page_Visits', index=False)
            finalCompletionToWrite.to_excel(writer, sheet_name='Weekly_Completion_Rate', index=False)

    else:

        finalCompletionDataFrames = getFinalCompletionCS(page_visits)

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Parsed_Data', index=False)
            weeklySummaryToWrite.to_excel(writer, sheet_name='Weekly_Page_Visits', index=False)
            for sheet_name, df in finalCompletionDataFrames.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)


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
    if not page_visits.empty and 'timestamp' in page_visits.columns:
        # Filter for domestic abuse and confirmation pages
        domestic_abuse = page_visits[page_visits['path'].str.contains('domestic-abuse', case=False, na=False)]
        getting_help_confirmation = page_visits[page_visits['path'].str.contains('getting-help', case=False, na=False)]
        # parenting_plan_confirmation = page_visits[page_visits['path'].str.contains('parenting-plan', case=False, na=False)]
        # options_no_contact_confirmation = page_visits[page_visits['path'].str.contains('options-no-contact', case=False, na=False)]
        # court_order_confirmation = page_visits[page_visits['path'].str.contains('court-order', case=False, na=False)]
        # mediation_confirmation = page_visits[page_visits['path'].str.contains('mediation', case=False, na=False)]
        # confirmation = page_visits[page_visits['path'].str.contains('confirmation', case=False, na=False)]

        # Simple method: count totals per week (for unknown IDs)
        domestic_abuse_weekly = domestic_abuse.groupby('week').size().reset_index(name='domestic_abuse_visits')
        getting_help_confirmation_weekly = getting_help_confirmation.groupby('week').size().reset_index(name='getting_help_confirmation_visits')
        # parenting_plan_confirmation_weekly = parenting_plan_confirmation.groupby('week').size().reset_index(name='parenting_plan_confirmation_visits')
        # options_no_contact_confirmation_weekly = options_no_contact_confirmation.groupby('week').size().reset_index(name='options_no_contact_confirmation_visits')
        # court_order_confirmation_weekly = court_order_confirmation.groupby('week').size().reset_index(name='court_order_confirmation_visits')
        # mediation_confirmation_weekly = mediation_confirmation.groupby('week').size().reset_index(name='mediation_confirmation_visits')
        # confirmation_weekly = confirmation.groupby('week').size().reset_index(name='confirmation_visits')

        # Merge and calculate simple completion rate
        # weekly_completion = pd.merge(domestic_abuse_weekly, confirmation_weekly, on='week', how='outer').fillna(0)
        # weekly_completion['simple_completion_rate'] = (weekly_completion['confirmation_visits'] / weekly_completion['domestic_abuse_visits'] * 100).round(2)
        # weekly_completion['simple_completion_rate'] = weekly_completion['simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        getting_help_weekly_completion = pd.merge(domestic_abuse_weekly, getting_help_confirmation_weekly, on='week', how='outer').fillna(0)
        getting_help_weekly_completion['getting_help_simple_completion_rate'] = (getting_help_weekly_completion['getting_help_confirmation_visits'] / getting_help_weekly_completion['domestic_abuse_visits'] * 100).round(2)
        getting_help_weekly_completion['getting_help_simple_completion_rate'] = getting_help_weekly_completion['getting_help_simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # parenting_plan_weekly_completion = pd.merge(domestic_abuse_weekly, parenting_plan_confirmation_weekly, on='week', how='outer').fillna(0)
        # parenting_plan_weekly_completion['simple_completion_rate'] = (parenting_plan_weekly_completion['parenting_plan_confirmation_visits'] / parenting_plan_weekly_completion['domestic_abuse_visits'] * 100).round(2)
        # parenting_plan_weekly_completion['simple_completion_rate'] = parenting_plan_weekly_completion['simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # options_no_contact_weekly_completion = pd.merge(domestic_abuse_weekly, options_no_contact_confirmation_weekly, on='week', how='outer').fillna(0)
        # options_no_contact_weekly_completion['simple_completion_rate'] = (options_no_contact_weekly_completion['options_no_contact_confirmation_visits'] / options_no_contact_weekly_completion['domestic_abuse_visits'] * 100).round(2)
        # options_no_contact_weekly_completion['simple_completion_rate'] = options_no_contact_weekly_completion['simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # court_order_weekly_completion = pd.merge(domestic_abuse_weekly, court_order_confirmation_weekly, on='week', how='outer').fillna(0)
        # court_order_weekly_completion['simple_completion_rate'] = (court_order_weekly_completion['court_order_confirmation_visits'] / court_order_weekly_completion['domestic_abuse_visits'] * 100).round(2)
        # court_order_weekly_completion['simple_completion_rate'] = court_order_weekly_completion['simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # mediation_weekly_completion = pd.merge(domestic_abuse_weekly, mediation_confirmation_weekly, on='week', how='outer').fillna(0)
        # mediation_weekly_completion['simple_completion_rate'] = (mediation_weekly_completion['mediation_confirmation_visits'] / mediation_weekly_completion['domestic_abuse_visits'] * 100).round(2)
        # mediation_weekly_completion['simple_completion_rate'] = mediation_weekly_completion['simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # Advanced method: unique user completion (for known IDs)
        # Get unique user_id + week combinations for domestic-abuse
        domestic_abuse_users = domestic_abuse.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
        # Get unique user_id + week combinations for confirmation
        # confirmation_users = confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
        getting_help_confirmation_users = getting_help_confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
        # parenting_plan_confirmation_users = parenting_plan_confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
        # options_no_contact_confirmation_users = options_no_contact_confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
        # court_order_confirmation_users = court_order_confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
        # mediation_confirmation_users = mediation_confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]

        # Mark users who reached each stage
        domestic_abuse_users['reached_domestic_abuse'] = 1
        # confirmation_users['reached_confirmation'] = 1
        getting_help_confirmation_users['reached_getting_help_confirmation'] = 1
        # parenting_plan_confirmation_users['reached_parenting_plan_confirmation'] = 1
        # options_no_contact_confirmation_users['reached_options_no_contact_confirmation'] = 1
        # court_order_confirmation_users['reached_court_order_confirmation'] = 1
        # mediation_confirmation_users['reached_mediation_confirmation'] = 1

        # Merge to find users who reached both stages
        # user_completion = pd.merge(domestic_abuse_users, confirmation_users, on=['week', 'user_id'], how='left').fillna(0)
        getting_help_user_completion = pd.merge(domestic_abuse_users, getting_help_confirmation_users, on=['week', 'user_id'], how='left').fillna(0)
        # parenting_plan_user_completion = pd.merge(domestic_abuse_users, parenting_plan_confirmation_users, on=['week', 'user_id'], how='left').fillna(0)
        # options_no_contact_user_completion = pd.merge(domestic_abuse_users, options_no_contact_confirmation_users, on=['week', 'user_id'], how='left').fillna(0)
        # court_order_user_completion = pd.merge(domestic_abuse_users, court_order_confirmation_users, on=['week', 'user_id'], how='left').fillna(0)
        # mediation_user_completion = pd.merge(domestic_abuse_users, mediation_confirmation_users, on=['week', 'user_id'], how='left').fillna(0)

        # Count unique users per week
        unique_domestic_abuse = getting_help_user_completion.groupby('week')['reached_domestic_abuse'].sum().reset_index(name='unique_users_domestic_abuse')
        # unique_completed = user_completion[user_completion['reached_confirmation'] == 1].groupby('week').size().reset_index(name='unique_users_completed')
        unique_getting_help_completed = getting_help_user_completion[getting_help_user_completion['reached_getting_help_confirmation'] == 1].groupby('week').size().reset_index(name='unique_getting_help_users_completed')
        # unique_parenting_plan_completed = parenting_plan_user_completion[parenting_plan_user_completion['reached_parenting_plan_confirmation'] == 1].groupby('week').size().reset_index(name='unique_parenting_plan_users_completed')
        # unique_options_no_contact_completed = options_no_contact_user_completion[options_no_contact_user_completion['reached_options_no_contact_confirmation'] == 1].groupby('week').size().reset_index(name='unique_options_no_contact_users_completed')
        # unique_court_order_completed = court_order_user_completion[court_order_user_completion['reached_court_order_confirmation'] == 1].groupby('week').size().reset_index(name='unique_court_order_users_completed')
        # unique_mediation_completed = mediation_user_completion[mediation_user_completion['reached_mediation_confirmation'] == 1].groupby('week').size().reset_index(name='unique_mediation_users_completed')

        # Merge and calculate user-based completion rate
        # user_based_completion = pd.merge(unique_domestic_abuse, unique_completed, on='week', how='outer').fillna(0)
        # user_based_completion['user_completion_rate'] = (user_based_completion['unique_users_completed'] / user_based_completion['unique_users_domestic_abuse'] * 100).round(2)
        # user_based_completion['user_completion_rate'] = user_based_completion['user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        getting_help_user_based_completion = pd.merge(unique_domestic_abuse, unique_getting_help_completed, on='week', how='outer').fillna(0)
        getting_help_user_based_completion['getting_help_user_completion_rate'] = (getting_help_user_based_completion['unique_getting_help_users_completed'] / getting_help_user_based_completion['unique_users_domestic_abuse'] * 100).round(2)
        getting_help_user_based_completion['getting_help_user_completion_rate'] = getting_help_user_based_completion['getting_help_user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # parenting_plan_user_based_completion = pd.merge(unique_domestic_abuse, unique_parenting_plan_completed, on='week', how='outer').fillna(0)
        # parenting_plan_user_based_completion['parenting_plan_user_completion_rate'] = (parenting_plan_user_based_completion['unique_parenting_plan_users_completed'] / parenting_plan_user_based_completion['unique_users_domestic_abuse'] * 100).round(2)
        # parenting_plan_user_based_completion['parenting_plan_user_completion_rate'] = parenting_plan_user_based_completion['parenting_plan_user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # options_no_contact_user_based_completion = pd.merge(unique_domestic_abuse, unique_options_no_contact_completed, on='week', how='outer').fillna(0)
        # options_no_contact_user_based_completion['options_no_contact_user_completion_rate'] = (options_no_contact_user_based_completion['unique_options_no_contact_users_completed'] / options_no_contact_user_based_completion['unique_users_domestic_abuse'] * 100).round(2)
        # options_no_contact_user_based_completion['options_no_contact_user_completion_rate'] = options_no_contact_user_based_completion['options_no_contact_user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # court_order_user_based_completion = pd.merge(unique_domestic_abuse, unique_court_order_completed, on='week', how='outer').fillna(0)
        # court_order_user_based_completion['court_order_user_completion_rate'] = (court_order_user_based_completion['unique_court_order_users_completed'] / court_order_user_based_completion['unique_users_domestic_abuse'] * 100).round(2)
        # court_order_user_based_completion['court_order_user_completion_rate'] = court_order_user_based_completion['court_order_user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # mediation_user_based_completion = pd.merge(unique_domestic_abuse, unique_mediation_completed, on='week', how='outer').fillna(0)
        # mediation_user_based_completion['mediation_user_completion_rate'] = (mediation_user_based_completion['unique_mediation_users_completed'] / mediation_user_based_completion['unique_users_domestic_abuse'] * 100).round(2)
        # mediation_user_based_completion['mediation_user_completion_rate'] = mediation_user_based_completion['mediation_user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # Combine both methods
        # final_completion = pd.merge([weekly_completion, getting_help_weekly_completion], [user_based_completion, getting_help_user_based_completion], on='week', how='outer').fillna(0)

        # final_completion = (
        #     weekly_completion
        #     .merge(user_based_completion, on='week', how='outer')
        #     .merge(getting_help_weekly_completion, on='week', how='outer')
        #     .merge(getting_help_user_based_completion, on='week', how='outer')
        #     .merge(parenting_plan_weekly_completion, on='week', how='outer')
        #     .merge(parenting_plan_user_based_completion, on='week', how='outer')
        #     .merge(options_no_contact_weekly_completion, on='week', how='outer')
        #     .merge(options_no_contact_user_based_completion, on='week', how='outer')
        #     .merge(court_order_weekly_completion, on='week', how='outer')
        #     .merge(court_order_user_based_completion, on='week', how='outer')
        #     .merge(mediation_weekly_completion, on='week', how='outer')
        #     .merge(mediation_user_based_completion, on='week', how='outer')
        #     .fillna(0)
        # )

        all_dfs = [
            # weekly_completion,
            # user_based_completion,
            getting_help_weekly_completion,
            getting_help_user_based_completion,
            # parenting_plan_weekly_completion,
            # parenting_plan_user_based_completion,
            # options_no_contact_weekly_completion,
            # options_no_contact_user_based_completion,
            # court_order_weekly_completion,
            # court_order_user_based_completion,
            # mediation_weekly_completion,
            # mediation_user_based_completion
        ]

        final_completion = reduce(
            lambda left, right: pd.merge(left, right, on='week', how='outer'), 
            all_dfs
        ).fillna(0)

        final_completion['week'] = final_completion['week'].astype(str)

        # final_completion = pd.merge(getting_help_weekly_completion, getting_help_user_based_completion, on='week', how='outer').fillna(0)
        # final_completion['getting_help_confirmation_visits'] = final_completion['week'].astype(str)

        # final_completion = pd.merge(parenting_plan_weekly_completion, parenting_plan_user_based_completion, on='week', how='outer').fillna(0)
        # # final_completion['week'] = final_completion['week'].astype(str)

        # final_completion = pd.merge(options_no_contact_weekly_completion, options_no_contact_user_based_completion, on='week', how='outer').fillna(0)

        # final_completion = pd.merge(court_order_weekly_completion, court_order_user_based_completion, on='week', how='outer').fillna(0)

        # final_completion = pd.merge(mediation_weekly_completion, mediation_user_based_completion, on='week', how='outer').fillna(0)

        # final_completion['week'] = final_completion['week'].astype(str)

        print(f"\nWeekly completion rate created with {len(final_completion)} rows")

    else:
        final_completion = pd.DataFrame(columns=['week', 'domestic_abuse_visits', 'confirmation_visits', 'getting_help_confirmation_visits', 'parenting_plan_confirmation_visits', 'options_no_contact_confirmation_visits', 'mediation_confirmation_visits', 'simple_completion_rate', 'unique_users_domestic_abuse', 'unique_users_completed', 'user_completion_rate'])
        print("\nNo page_visit data for completion rate")

    return final_completion

def getFinalCompletionCS(page_visits):

    if not page_visits.empty and 'timestamp' in page_visits.columns:

        return {
            "Getting_Help": getGettingHelpFinalCompletionCS(page_visits),
            "Parenting_Plan": getParentingPlanFinalCompletionCS(page_visits),
            "Options_No_Contact": getOptionsNoContactFinalCompletionCS(page_visits),
            "Court_Order": getCourtOrderFinalCompletionCS(page_visits),
            "Mediation": getMediationFinalCompletionCS(page_visits)
        }

    else:

        return {
            "Getting_Help": pd.DataFrame(columns=['week']),
            "Parenting_Plan": pd.DataFrame(columns=['week']),
            "Options_No_Contact": pd.DataFrame(columns=['week']),
            "Court_Order": pd.DataFrame(columns=['week']),
            "Mediation": pd.DataFrame(columns=['week'])
        }

def getGettingHelpFinalCompletionCS(page_visits):
    return getFunnelCompletionCS(
        page_visits,
        step_name="getting_help",
        step_pattern="getting-help"
    )

def getParentingPlanFinalCompletionCS(page_visits):
    return getFunnelCompletionCS(
        page_visits,
        step_name="parenting_plan",
        step_pattern="parenting-plan"
    )

def getOptionsNoContactFinalCompletionCS(page_visits):
    return getFunnelCompletionCS(
        page_visits,
        step_name="options_no_contact",
        step_pattern="options-no-contact"
    )

def getCourtOrderFinalCompletionCS(page_visits):
    return getFunnelCompletionCS(
        page_visits,
        step_name="court_order",
        step_pattern="court-order"
    )

def getMediationFinalCompletionCS(page_visits):
    return getFunnelCompletionCS(
        page_visits,
        step_name="mediation",
        step_pattern="mediation"
    )

def getFunnelCompletionCS(page_visits, step_name, step_pattern):
    
    if page_visits.empty or 'timestamp' not in page_visits.columns:
        return pd.DataFrame(columns=[
            'week',
            'domestic_abuse_visits',
            f'{step_name}_visits',
            f'{step_name}_simple_completion_rate',
            'unique_users_domestic_abuse',
            f'unique_{step_name}_users_completed',
            f'{step_name}_user_completion_rate'
        ])

    # Precompute paths once (performance win)
    paths = page_visits['path'].str.lower()

    # Step filters
    domestic_abuse = page_visits[paths.str.contains('domestic-abuse', na=False)]
    step_df = page_visits[paths.str.contains(step_pattern, na=False)]

    # --- SIMPLE METHOD ---
    domestic_weekly = domestic_abuse.groupby('week').size().reset_index(name='domestic_abuse_visits')
    step_weekly = step_df.groupby('week').size().reset_index(name=f'{step_name}_visits')

    weekly = pd.merge(domestic_weekly, step_weekly, on='week', how='outer').fillna(0)

    weekly[f'{step_name}_simple_completion_rate'] = np.where(
        weekly['domestic_abuse_visits'] > 0,
        (weekly[f'{step_name}_visits'] / weekly['domestic_abuse_visits']) * 100,
        0
    ).round(2)

    unique_domestic = (
        domestic_abuse.groupby('week')['user_id']
        .nunique()
        .reset_index(name='unique_users_domestic_abuse')
    )

    unique_step_completed = (
        step_df.groupby('week')['user_id']
        .nunique()
        .reset_index(name=f'unique_{step_name}_users_completed')
    )

    user_completion = pd.merge(unique_domestic, unique_step_completed, on='week', how='outer').fillna(0)

    user_completion[f'{step_name}_user_completion_rate'] = np.where(
        user_completion['unique_users_domestic_abuse'] > 0,
        (user_completion[f'unique_{step_name}_users_completed'] / user_completion['unique_users_domestic_abuse']) * 100,
        0
    ).round(2)

    # --- FINAL MERGE ---
    final = pd.merge(weekly, user_completion, on='week', how='outer').fillna(0)
    final['week'] = final['week'].astype(str)

    print(f"\n{step_name} completion rate created with {len(final)} rows")

    return final
    if not page_visits.empty and 'timestamp' in page_visits.columns:
        # Filter for domestic abuse and parenting plan confirmation pages
        domestic_abuse = page_visits[page_visits['path'].str.contains('domestic-abuse', case=False, na=False)]
        parenting_plan_confirmation = page_visits[page_visits['path'].str.contains('parenting-plan', case=False, na=False)]

        # Simple method: count totals per week (for unknown IDs)
        domestic_abuse_weekly = domestic_abuse.groupby('week').size().reset_index(name='domestic_abuse_visits')
        parenting_plan_confirmation_weekly = parenting_plan_confirmation.groupby('week').size().reset_index(name='parenting_plan_confirmation_visits')

        # Merge and calculate simple completion rate
        parenting_plan_weekly_completion = pd.merge(domestic_abuse_weekly, parenting_plan_confirmation_weekly, on='week', how='outer').fillna(0)
        parenting_plan_weekly_completion['parenting_plan_simple_completion_rate'] = (parenting_plan_weekly_completion['parenting_plan_confirmation_visits'] / parenting_plan_weekly_completion['domestic_abuse_visits'] * 100).round(2)
        parenting_plan_weekly_completion['parenting_plan_simple_completion_rate'] = parenting_plan_weekly_completion['parenting_plan_simple_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # Advanced method: unique user completion (for known IDs)
        # Get unique user_id + week combinations for domestic-abuse
        domestic_abuse_users = domestic_abuse.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]
        # Get unique user_id + week combinations for getting help confirmation
        parenting_plan_confirmation_users = parenting_plan_confirmation.groupby(['week', 'user_id']).size().reset_index(name='count')[['week', 'user_id']]

        # Mark users who reached each stage
        domestic_abuse_users['reached_domestic_abuse'] = 1
        parenting_plan_confirmation_users['reached_parenting_plan_confirmation'] = 1

        # Merge to find users who reached both stages
        parenting_plan_user_completion = pd.merge(domestic_abuse_users, parenting_plan_confirmation_users, on=['week', 'user_id'], how='left').fillna(0)

        # Count unique users per week
        unique_domestic_abuse = parenting_plan_user_completion.groupby('week')['reached_domestic_abuse'].sum().reset_index(name='unique_users_domestic_abuse')
        unique_parenting_plan_completed = parenting_plan_user_completion[parenting_plan_user_completion['reached_parenting_plan_confirmation'] == 1].groupby('week').size().reset_index(name='unique_parenting_plan_users_completed')

        # Merge and calculate user-based completion rate
        parenting_plan_user_based_completion = pd.merge(unique_domestic_abuse, unique_parenting_plan_completed, on='week', how='outer').fillna(0)
        parenting_plan_user_based_completion['parenting_plan_user_completion_rate'] = (parenting_plan_user_based_completion['unique_parenting_plan_users_completed'] / parenting_plan_user_based_completion['unique_users_domestic_abuse'] * 100).round(2)
        parenting_plan_user_based_completion['parenting_plan_user_completion_rate'] = parenting_plan_user_based_completion['parenting_plan_user_completion_rate'].replace([float('inf'), float('-inf')], 0).fillna(0)

        # Combine both methods
        final_completion = pd.merge(parenting_plan_weekly_completion, parenting_plan_user_based_completion, on='week', how='outer').fillna(0)
        final_completion['week'] = final_completion['week'].astype(str)

        print(f"\nWeekly completion rate created with {len(final_completion)} rows")

    else:
        final_completion = pd.DataFrame(columns=['week', 'domestic_abuse_visits', 'confirmation_visits', 'getting_help_confirmation_visits', 'parenting_plan_confirmation_visits', 'options_no_contact_confirmation_visits', 'mediation_confirmation_visits', 'simple_completion_rate', 'unique_users_domestic_abuse', 'unique_users_completed', 'user_completion_rate'])
        print("\nNo page_visit data for completion rate")

    return final_completion

def getOutputFile(systemSelection):
    if int(systemSelection) == 1:
        output_filename = "Data_Aggregation_Output_CAP.xlsx"
    else:
        output_filename = "Data_Aggregation_Output_CS.xlsx"
    return os.path.join(output_dir, output_filename)

process()
