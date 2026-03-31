# CAP Analytics Dashboard

A Streamlit-based analytics dashboard for analyzing Care Arrangement Plan user behavior and engagement metrics.

## Project Structure

### Complete File Structure

```
care-arrangement-plan-analytics/
├── app.py                          # ⭐ Main application entry point
├── main.py                         # CLI batch processing script
├── config.py                       # Service configuration
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
    │   ├── metrics_display.py      # Key metrics cards
    │   ├── sidebar.py              # Data source selector, filters, downloads
    │   └── tabs/                   # Dashboard tabs (one file per tab)
    │       ├── __init__.py
    │       ├── all_tabs.py         # Tab orchestrator
    │       ├── weekly_overview.py
    │       ├── page_visits.py
    │       ├── completion_rates.py
    │       ├── link_clicks.py
    │       ├── page_exits.py
    │       ├── quick_exits.py
    │       ├── downloads.py
    │       └── raw_data.py
    │
    ├── data_processing/            # 📊 Data Processing Logic
    │   ├── __init__.py
    │   ├── constants.py            # Page order, display names, excluded paths
    │   ├── parser.py               # Log parsing & cleaning
    │   ├── metrics.py              # Metrics calculations
    │   ├── processor.py            # Pipeline orchestration
    │   └── opensearch_client.py    # OpenSearch API client
    │
    └── utils/                      # 🔧 Utility Functions
        ├── __init__.py
        ├── file_utils.py           # File validation & Excel generation
        └── audit_log.py            # Structured audit logging
```

### Key Files Explained

#### Entry Points
- **`app.py`** ⭐ - Main dashboard application (modular, fully functional)
- **`main.py`** - CLI script for batch processing

#### Data Processing (`src/data_processing/`)
- **`parser.py`** - Parses raw log entries, filters out assets and anonymous users
  - Extracts `path` field for page visits
  - Extracts `exit_page` field for page_exit and quick_exit events
- **`metrics.py`** - Calculates all metrics (funnel, completion rates, deduplication)
- **`constants.py`** - Defines the 12-page journey order and display names
- **`processor.py`** - Orchestrates the entire data pipeline

#### UI Components (`src/components/`)
- **`metrics_display.py`** - Renders key metrics cards
- **`sidebar.py`** - Data source selector, date filters, download buttons
- **`tabs/`** - One module per tab: Weekly Overview, Page Visits, Completion Rates, Link Clicks, Page Exits, Quick Exits, Downloads, Raw Data

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

## Environment Variables

Copy `.env.example` to `.env` and adjust the values for your setup:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `ALLOW_FILE_UPLOAD` | unset | Set to `true` locally to enable the File source option. Leave unset in production. |
| `CAP_PROXY_URL` | `http://localhost:8080` | URL for the CAP OpenSearch proxy |
| `CS_PROXY_URL` | `http://localhost:8081` | URL for the Connecting Services OpenSearch proxy |

**Local development** (file upload enabled):
```bash
ALLOW_FILE_UPLOAD=true streamlit run app.py
```

**Production** (OpenSearch only — no file option shown to users):
```bash
streamlit run app.py
```

> `.env` is gitignored. Never commit real URLs or secrets.

## Usage

### Running the Dashboard

```bash
streamlit run app.py
```

Your browser will open automatically at http://localhost:8501

### Using the Dashboard

1. Place your raw log files (`.xlsx` or `.csv`) in the `input/` directory
2. Launch the dashboard with `streamlit run app.py`
3. Your browser will open automatically at http://localhost:8501
4. Select a file from the sidebar dropdown and click "Load Data"
5. Explore the interactive visualizations and analytics across all tabs

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

### Linting

Install dev dependencies first:

```bash
pip install -r requirements-dev.txt
```

Run ruff:

```bash
ruff check src/ app.py config.py
```

Auto-fix where possible:

```bash
ruff check --fix src/ app.py config.py
```

Linting also runs automatically on every pull request via GitHub Actions.

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
Input File (CSV/Excel)
    ↓
parser.py (parse_log_data)
    ↓
metrics.py (calculate_*)
    ↓
processor.py (orchestrate)
    ↓
app.py (display)
    ↓
components/* (render UI)
```

## Development

### Adding New Metrics

1. Add calculation logic to `src/data_processing/metrics.py`
2. Update `processor.py` to include the new metric
3. Create/update UI component in `src/components/`
4. Add tests in `tests/test_data_processor.py`

### Adding New Pages to Track

1. Define page path in `src/data_processing/constants.py`
2. Add to `PAGE_ORDER` list
3. Add display name to `PAGE_NAMES` dict
4. Metrics will automatically include the new page

## Deactivating Virtual Environment

When you're done working:
```bash
deactivate
```

---

## Deployment (Cloud Platform)

The dashboard is hosted on [Ministry of Justice Cloud Platform](https://user-guide.cloud-platform.service.justice.gov.uk) using Kubernetes. Authentication is handled by [oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy) in front of Streamlit, using Microsoft Entra ID via the [IDAM team](https://user-guide.staff-identity.service.justice.gov.uk) as the identity provider.

### Infrastructure overview

Three repositories are involved:

| Repo | Purpose |
|---|---|
| `pfl-analytics` (this repo) | App code, Docker image, Kubernetes manifests, CI/CD pipeline |
| `cloud-platform-environments` | Kubernetes namespace definitions, ECR, service accounts |
| `staff-identity-idam-entra-infra` | Azure Entra ID app registration (OAuth2 client) |

### How authentication works

```
User → Ingress → oauth2-proxy → (if authenticated) → Streamlit
                      ↕
               Microsoft Entra ID
               (MoJ External tenant)
```

oauth2-proxy intercepts all traffic. Unauthenticated users are redirected to Microsoft login. Only `justice.gov.uk` and `digital.justice.gov.uk` email addresses are permitted.

### Deployment pipeline

On every push to `main`:

1. `build-push-image.yml` — builds the Docker image and pushes to ECR (prod namespace)
2. `deploy.yml` — runs `envsubst` on `deploy/development/*.tpl.yml` to inject secrets/config, then applies manifests to the cluster
