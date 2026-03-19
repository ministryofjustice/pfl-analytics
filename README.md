# Family Justice Analytics Dashboard

A Streamlit-based analytics dashboard for analyzing user behavior and engagement metrics across Family Justice services (Care Arrangement Plan and Connecting Services).

## Project Structure

### Complete File Structure

```
care-arrangement-plan-analytics/
├── app.py                          # ⭐ Main application entry point
├── data_processor.py               # Legacy data processor (deprecated)
├── main.py                         # CLI batch processing script
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
├── input/                          # 📁 Place your data files here
│   └── .gitkeep
│
├── output/                         # 📁 Processed output files
│   └── .gitkeep
│
├── tests/                          # 🧪 Unit tests
│   ├── __init__.py
│   └── test_data_processor.py      # Data processing tests
│
└── src/                            # Modular source code
    ├── __init__.py
    │
    ├── components/                 # 🎨 UI Components
    │   ├── __init__.py
    │   ├── metrics_display.py      # Key metrics visualization
    │   ├── sidebar.py              # File selector, filters, downloads
    │   └── tabs/                   # Dashboard tabs
    │       ├── __init__.py
    │       └── all_tabs.py         # All dashboard tab components
    │
    ├── data_processing/            # 📊 Data Processing Logic
    │   ├── __init__.py
    │   ├── constants.py            # Page order, display names
    │   ├── opensearch_client.py    # OpenSearch fetch & scroll logic
    │   ├── parser.py               # Log parsing & cleaning
    │   ├── metrics.py              # Metrics calculations
    │   └── processor.py            # Main orchestration
    │
    └── utils/                      # 🔧 Utility Functions
        ├── __init__.py
        └── file_utils.py           # Excel/CSV file handling
```

### Key Files Explained

#### Entry Points
- **`app.py`** ⭐ - Main dashboard application (modular, fully functional)
- **`main.py`** - CLI script for batch processing

#### Data Processing (`src/data_processing/`)
- **`opensearch_client.py`** - Fetches events from OpenSearch using the scroll API; tags each row with a `service` column
- **`parser.py`** - Parses raw log entries, filters out assets and anonymous users
  - Extracts `path` field for page visits
  - Extracts `exit_page` field for page_exit and quick_exit events
- **`metrics.py`** - Calculates all metrics (funnel, completion rates, deduplication)
- **`constants.py`** - Defines the 12-page journey order and display names for each service
- **`processor.py`** - Orchestrates the entire data pipeline

#### UI Components (`src/components/`)
- **`metrics_display.py`** - Renders key metrics cards
- **`sidebar.py`** - File selection, per-service OpenSearch URL inputs, date filters, download buttons
- **`tabs/all_tabs.py`** - All dashboard tab components (Weekly Overview, Page Visits, Completion Rates, Link Clicks, Page Exits, Quick Exits, Downloads, Raw Data)

#### Tests (`tests/`)
- **`test_data_processor.py`** - Unit tests for deduplication and metrics

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd care-arrangement-plan-analytics
```

The `input/` and `output/` directories will be created automatically with `.gitkeep` files to maintain the folder structure.

### 2. Create Virtual Environment

```bash
python3 -m venv venv
```

### 3. Activate Virtual Environment

On macOS/Linux:
```bash
source venv/bin/activate
```

On Windows:
```bash
venv\Scripts\activate
```

### 4. Install Requirements

```bash
pip install -r requirements.txt
```

## Usage

### Running the Dashboard

```bash
streamlit run app.py
```

Your browser will open automatically at http://localhost:8501

### Using the Dashboard

The dashboard supports two data sources, selectable from the sidebar.

#### File source (local log files)

1. Place your raw log files (`.xlsx` or `.csv`) in the `input/` directory
2. Select **File** in the sidebar, choose a file, and click **Load Data**

#### OpenSearch source (live data from Cloud Platform)

The dashboard can connect to one or more OpenSearch instances simultaneously and combine their data.

**Port-forward each service's OpenSearch proxy locally before starting the dashboard:**

```bash
# CAP
kubectl port-forward -n care-arrangement-plan-dev svc/<proxy-svc> 8080:8080

# Connecting Services (when provisioned)
kubectl port-forward -n <cs-namespace> svc/<proxy-svc> 8081:8080
```

Then in the sidebar select **OpenSearch**, enter the proxy URL(s), and click **Fetch from OpenSearch**. Leave a URL blank to skip that service.

**Configuring via environment variables** (useful for hosted deployments):

| Variable | Service | Default |
|---|---|---|
| `CAP_OPENSEARCH_URL` | Care Arrangement Plan | `http://localhost:8080` |
| `CS_OPENSEARCH_URL` | Connecting Services | _(blank)_ |

```bash
export CAP_OPENSEARCH_URL=http://localhost:8080
streamlit run app.py
```

**Dashboard Features:**
- 📊 Weekly overview with interactive charts
- 🔍 Detailed page visit analysis with deduplication
- ✅ Completion rate tracking and 12-page funnel visualization
- 🔗 Link clicks, page exits, and quick exits analysis
- 📥 Download tracking by type
- 📋 Raw data viewing and CSV/Excel export
- 📅 Date range filtering
- 📈 Real-time metrics

### Running Tests

```bash
# Run all tests
python tests/test_data_processor.py

# Run with verbose output
python tests/test_data_processor.py -v

# Run specific test class
python -m unittest tests.test_data_processor.TestPageVisitDeduplication
```

## Architecture

### Key Features

- **Page Visit Deduplication**: Counts only the first visit per user-page combination globally
- **12-Page Conversion Funnel**: Tracks user progress through the entire journey
- **Event Tracking**:
  - **Page visits**: Tracked via `path` field
  - **Page exits & Quick exits**: Tracked via `exit_page` field (shows which page user left from)
  - **Link clicks**: Tracked via `path` field
  - **Downloads**: Tracked by type (PDF, HTML, etc.)
- **Weekly Analytics**: Aggregates metrics by week
- **Completion Rates**: Calculates user journey completion percentages

### Data Flow

```
Input File (CSV/Excel)              OpenSearch (one or more services)
         ↓                                        ↓
parser.py (parse_log_data)     opensearch_client.py (fetch_all_events × N)
         ↓                                        ↓
         └──────────────────┬────────────────────┘
                            ↓
                  processor.py (process_dataframe)
                            ↓
                        app.py (display)
                            ↓
                     components/* (render UI)
```

Each row fetched from OpenSearch is tagged with a `service` column (e.g. `'CAP'`, `'Connecting Services'`) so data from multiple services can be combined into one dashboard or filtered per service.

## Development

### Adding New Metrics

1. Add calculation logic to `src/data_processing/metrics.py`
2. Update `processor.py` to include the new metric
3. Create/update UI component in `src/components/`
4. Add tests in `tests/test_data_processor.py`

### Adding a New Service

1. Add an entry to the `SERVICES` list in `src/components/sidebar.py`:
   ```python
   {
       'name': 'My Service',
       'url_env': 'MY_SERVICE_OPENSEARCH_URL',
       'default_url': '',
       'index': 'my-service-analytics',
   }
   ```
2. Provision OpenSearch in the service's Cloud Platform namespace
3. Set `MY_SERVICE_OPENSEARCH_URL` in the analytics deployment (or port-forward locally)
4. Optionally add a journey page order to `src/data_processing/constants.py`

### Adding New Pages to Track

1. Define page path in `src/data_processing/constants.py`
2. Add to `PAGE_ORDER` (or the relevant service's page order list)
3. Add display name to `PAGE_NAMES` dict
4. Metrics will automatically include the new page

## Deactivating Virtual Environment

When you're done working:
```bash
deactivate
```