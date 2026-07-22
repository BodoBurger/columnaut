# Columnaut

Columnaut is a Python/Streamlit application for getting familiar with tabular data before
using it in analyses, forecasts, or predictive models.

> Explore your data before you depend on it.

Columnaut provides:

- CSV and Parquet ingestion
- Excel `.xlsx` and legacy `.xls` ingestion
- Arrow-backed pandas columns where source values have a consistent representable type
- Excel worksheet and header-row selection
- A data preview and basic dataset/column characteristics
- Warnings for duplicate or blank headers, merged cells, empty rows and columns, mixed value
  types, and duplicate rows
- A reusable adapter boundary for future data sources
- Data-type-specific statistics and distributions
- Recognition of common pseudo-missing strings and suspicious sentinel values without changing
  the source data
- Semantic type inference with explicit confidence
- Generic range and sensibility checks for non-finite numbers, IQR outliers, and implausible dates
- Structured findings with separate severity and confidence

## Run locally

Python 3.11 or newer is required.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
streamlit run app.py
```

### macOS or Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
streamlit run app.py
```

Open the URL printed by Streamlit, upload a supported file, and configure the worksheet and
header row when importing Excel.

## Run in a container

Docker builds the existing Python 3.11 and Streamlit application without changing its ingestion
or profiling behavior. The production image runs as a non-root user, listens on port `8501`, and
checks Streamlit's built-in `/_stcore/health` endpoint.

```powershell
docker build --tag columnaut:local .
docker run --rm --name columnaut -p 8501:8501 columnaut:local
```

Open `http://localhost:8501`. In another terminal, verify the health endpoint:

```powershell
Invoke-WebRequest http://localhost:8501/_stcore/health | Select-Object StatusCode, Content
docker inspect --format '{{.State.Health.Status}}' columnaut
```

The first command should return HTTP `200` with `ok`; after the health-check start period, the
container status should be `healthy`. Uploaded files are processed in memory by the existing
adapters and are not copied into the image.

### Container validation

Before publishing an image, run the application checks and exercise every supported adapter:

```powershell
pytest
ruff check app.py src tests
docker build --tag columnaut:local .
docker run --rm --name columnaut -p 8501:8501 columnaut:local
```

The adapter tests cover CSV, Parquet, `.xlsx`, and declared legacy `.xls` routing. Keep the
container running while checking `/_stcore/health` and manually uploading representative files
when a browser-level acceptance check is required.

## Deployment roadmap

Containerization is the first deployment milestone. Later milestones should be handled separately:

1. Provision Azure Container Registry and Azure Container Apps with ingress targeting port `8501`
   and HTTP health probes using `/_stcore/health`.
2. Add CI/CD that runs tests and lint, builds an immutable image, scans it, pushes it to the
   registry, and deploys a pinned image digest.
3. Add authentication at the platform boundary before exposing non-public datasets or workflows.
4. Harden production with managed identity, secrets management, resource limits, scaling rules,
   logging, monitoring, backup/retention decisions, and explicit upload-size and data-lifetime
   policies.

These later steps do not require a React migration; Streamlit remains the deployed user interface.

## Test and lint

```bash
pytest
ruff check app.py src tests
```

## Project layout

```text
app.py                         Streamlit user interface
src/columnaut/ingestion/       File adapters and import-time structural checks
src/columnaut/profiling/       Deterministic dataset and column summaries
tests/                         Adapter and profiling tests
```

The ingestion layer intentionally does not depend on Streamlit. A future API, CLI, scheduled
profiler, or different interface can reuse the same adapters and profile objects.

## Excel behavior and boundaries

Each selected worksheet is treated as one dataset. The selected header row becomes the column
names; duplicate names receive suffixes such as `Amount__2`, and blank names receive placeholders
such as `column_4`.

Excel allows mixed cell types, decorative rows, merged cells, and multiple unrelated tables in one
sheet. Columnaut retains suspicious structure and reports it instead of silently deleting it.
Legacy `.xls` reading uses `xlrd`; `.xlsx` reading and merged-cell inspection use `openpyxl`.
Imported tables use pandas' PyArrow dtype backend for consistent nullable types and efficient
interchange. Genuinely heterogeneous Excel columns remain object-backed so their source values can
be retained and reported without coercion.

## Profiling and AI boundary

Columnaut calculates profiles and findings with deterministic Python code. A future AI assistant
should interpret these structured results, explain their implications, and help users turn findings
into user-approved validation rules. It should not calculate statistics itself or receive the full
raw dataset by default.

Pseudo-missing markers and generic sensibility checks are observations, not automatic cleaning
rules. The report keeps the original values intact and uses confidence to distinguish strong facts
from interpretations that require domain context.
