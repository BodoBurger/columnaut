"""Streamlit entry point for Columnaut."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from columnaut.ingestion.registry import default_registry  # noqa: E402
from columnaut.models import LoadOptions  # noqa: E402
from columnaut.profiling.basic import (  # noqa: E402
    column_overview,
    dataset_overview,
    format_bytes,
)


@st.cache_data(show_spinner=False)
def inspect_source(payload: bytes, source_name: str):
    return default_registry.for_source(source_name).inspect(payload, source_name)


@st.cache_data(show_spinner=False)
def load_source(
    payload: bytes,
    source_name: str,
    sheet_name: str | None,
    header_row: int,
):
    return default_registry.for_source(source_name).load(
        payload,
        source_name,
        LoadOptions(sheet_name=sheet_name, header_row=header_row),
    )


st.set_page_config(page_title="Columnaut", page_icon="🧭", layout="wide")
st.title("Columnaut")
st.caption("Get familiar with a tabular dataset before you analyze or model it.")

uploaded_file = st.file_uploader(
    "Choose a CSV, Parquet, or Excel file",
    type=["csv", "parquet", "pq", "xlsx", "xls"],
)

if uploaded_file is None:
    st.info("Upload a file to create an interactive first-look report.")
    st.stop()

payload = uploaded_file.getvalue()
source_name = uploaded_file.name

try:
    adapter = default_registry.for_source(source_name)
    inspection = inspect_source(payload, source_name)
except Exception as error:
    st.error(f"The file could not be inspected: {error}")
    st.stop()

sheet_name: str | None = None
header_row = 0

if inspection.sheet_names:
    st.subheader("Excel import settings")
    settings_col, header_col = st.columns(2)
    with settings_col:
        sheet_name = st.selectbox("Worksheet", inspection.sheet_names)
    with header_col:
        header_row = (
            st.number_input(
                "Header row",
                min_value=1,
                value=1,
                step=1,
                help="One-based Excel row containing the column names.",
            )
            - 1
        )

try:
    with st.spinner("Reading and inspecting the table..."):
        loaded = load_source(payload, source_name, sheet_name, int(header_row))
except Exception as error:
    st.error(f"The table could not be loaded: {error}")
    st.stop()

dataframe = loaded.dataframe
overview = dataset_overview(dataframe)

st.subheader("Dataset overview")
metric_columns = st.columns(5)
metric_columns[0].metric("Rows", f"{overview.rows:,}")
metric_columns[1].metric("Columns", f"{overview.columns:,}")
metric_columns[2].metric(
    "Missing cells",
    f"{overview.missing_cells:,}",
    help=f"{overview.missing_percent:.2f}% of all cells",
)
metric_columns[3].metric("Duplicate rows", f"{overview.duplicate_rows:,}")
metric_columns[4].metric("Memory", format_bytes(overview.memory_bytes))

if loaded.sheet_name:
    st.caption(
        f"Source: {loaded.source_name} · Sheet: {loaded.sheet_name} · "
        f"Header row: {(loaded.header_row or 0) + 1}"
    )
else:
    st.caption(f"Source: {loaded.source_name} · Format: {loaded.source_format.upper()}")

if loaded.warnings:
    st.subheader(f"Import findings ({len(loaded.warnings)})")
    for warning in loaded.warnings:
        details: list[str] = []
        if warning.columns:
            details.append(f"Columns: {', '.join(warning.columns)}")
        if warning.row_numbers:
            details.append(f"Source rows: {', '.join(map(str, warning.row_numbers))}")
        detail_text = f"  \n{' · '.join(details)}" if details else ""
        st.warning(f"**{warning.title}** — {warning.message}{detail_text}")

preview_tab, columns_tab = st.tabs(["Data preview", "Columns"])
with preview_tab:
    st.dataframe(dataframe.head(500), use_container_width=True, height=520)
    if len(dataframe.index) > 500:
        st.caption("Showing the first 500 rows.")

with columns_tab:
    st.dataframe(column_overview(dataframe), use_container_width=True, hide_index=True)
