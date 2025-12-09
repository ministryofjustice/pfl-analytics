# care-arrangement-plan-analytics
POC for analytics dashboard for CAP

## Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
```

### 2. Activate Virtual Environment

On macOS/Linux:
```bash
source venv/bin/activate
```

On Windows:
```bash
venv\Scripts\activate
```

### 3. Install Requirements

```bash
pip install -r requirements.txt
```

## Usage

1. Place your raw log files (`.xlsx` or `.csv`) in the `input/` directory
2. Run the script:
   ```bash
   python main.py
   ```
3. When prompted, enter the name of your input file (e.g., `report.xlsx`)
4. The processed output will be saved to `output/Data_Aggregation_Output.xlsx`

## Deactivating Virtual Environment

When you're done working:
```bash
deactivate
```