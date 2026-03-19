# Input Directory

Place your raw log files here for processing.

## Supported File Formats
- Excel files (`.xlsx`)
- CSV files (`.csv`)

## Example Files
Your log files should contain entries with the following format:
```
timestamp=2024-11-13T10:30:00Z, event_type=page_visit, user_id=user123, path=/dashboard, method=GET, status_code=200
```

## Usage
1. Copy your log export files (`.xlsx` or `.csv`) into this directory
2. Run either:
   - **Dashboard**: `streamlit run app.py`
   - **Batch Processing**: `python main.py`

## Note
The actual data files in this directory are ignored by git (see `.gitignore`) to protect sensitive information.
