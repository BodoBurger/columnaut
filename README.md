# Columnaut

Columnaut is a Python/Streamlit application for getting familiar with tabular data before
using it in analyses, forecasts, or predictive models.

Milestone 1 provides:

- CSV and Parquet ingestion
- Excel `.xlsx` and legacy `.xls` ingestion
- Excel worksheet and header-row selection
- A data preview and basic dataset/column characteristics
- Warnings for duplicate or blank headers, merged cells, empty rows and columns, mixed value
  types, and duplicate rows
- A reusable adapter boundary for future data sources

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

## Next milestone

Milestone 2 should add data-type-specific profiles, pseudo-missing string detection, semantic type
inference, value distributions, range checks, and a structured finding model.
