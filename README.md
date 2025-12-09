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

There are two ways to use this project:

### Option 1: Interactive Dashboard (Recommended)

1. Place your raw log files (`.xlsx` or `.csv`) in the `input/` directory
2. Launch the Streamlit dashboard:
   ```bash
   streamlit run dashboard.py
   ```
3. Your browser will open automatically to the dashboard (usually at http://localhost:8501)
4. Select a file from the sidebar dropdown and click "Load Data"
5. Explore the interactive visualizations and analytics

**Dashboard Features:**
- 📊 Weekly overview with interactive charts
- 🔍 Detailed page visit analysis
- ✅ Completion rate tracking and funnel visualization
- 📋 Raw data viewing and CSV export
- 📅 Date range filtering
- 📈 Real-time metrics

### Option 2: Command-Line Batch Processing

1. Place your raw log files (`.xlsx` or `.csv`) in the `input/` directory
2. Run the script:
   ```bash
   python main.py
   ```
3. Select a file from the numbered list
4. The processed output will be saved to `output/Data_Aggregation_Output.xlsx`

## Deactivating Virtual Environment

When you're done working:
```bash
deactivate
```