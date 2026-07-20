"""Streamlit entry point for Columnaut."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from columnaut.ingestion.registry import default_registry  # noqa: E402
from columnaut.models import Finding, FindingSeverity, LoadOptions  # noqa: E402
from columnaut.profiling.advanced import (  # noqa: E402
    TableProfile,
    column_profile_frame,
    profile_table,
)
from columnaut.profiling.basic import dataset_overview, format_bytes  # noqa: E402


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


@st.cache_data(show_spinner=False)
def build_profile(dataframe: pd.DataFrame) -> TableProfile:
    return profile_table(dataframe)


def finding_text(finding: Finding) -> str:
    details = [
        f"Severity: {finding.severity.value}",
        f"Confidence: {finding.confidence.value}",
    ]
    if finding.affected_count is not None:
        details.append(f"Affected: {finding.affected_count:,}")
    if finding.examples:
        details.append(f"Examples: {', '.join(finding.examples)}")
    if finding.columns:
        details.append(f"Columns: {', '.join(finding.columns)}")
    if finding.row_numbers:
        details.append(f"Source rows: {', '.join(map(str, finding.row_numbers))}")
    return f"**{finding.title}** — {finding.message}  \n{' · '.join(details)}"


def show_finding(finding: Finding) -> None:
    text = finding_text(finding)
    if finding.severity == FindingSeverity.ERROR:
        st.error(text)
    elif finding.severity == FindingSeverity.WARNING:
        st.warning(text)
    else:
        st.info(text)


st.set_page_config(page_title="Columnaut", page_icon="🧭", layout="wide")
st.title("Columnaut")
st.caption("Explore your data before you depend on it.")

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
table_profile = build_profile(dataframe)

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
    for finding in loaded.warnings:
        show_finding(finding)

if table_profile.findings:
    st.subheader(f"Profile findings ({len(table_profile.findings)})")
    st.caption(
        "Severity describes potential impact; confidence describes how certain the "
        "interpretation is. Columnaut does not change the source data."
    )
    for finding in table_profile.findings:
        show_finding(finding)
else:
    st.success("No generic profile findings were detected.")

preview_tab, columns_tab, detail_tab = st.tabs(
    ["Data preview", "Column overview", "Column details"]
)
with preview_tab:
    st.dataframe(dataframe.head(500), width="stretch", height=520)
    if len(dataframe.index) > 500:
        st.caption("Showing the first 500 rows.")

with columns_tab:
    st.dataframe(
        column_profile_frame(table_profile),
        width="stretch",
        hide_index=True,
    )

with detail_tab:
    if not table_profile.columns:
        st.info("This dataset has no columns to profile.")
    else:
        selected_index = st.selectbox(
            "Column",
            options=range(len(table_profile.columns)),
            format_func=lambda index: table_profile.columns[index].column,
        )
        selected = table_profile.columns[selected_index]
        detail_metrics = st.columns(5)
        detail_metrics[0].metric("Semantic type", selected.semantic_type.value)
        detail_metrics[1].metric("Confidence", selected.semantic_confidence.value)
        detail_metrics[2].metric("Unique", f"{selected.unique:,}")
        detail_metrics[3].metric("Missing", f"{selected.missing:,}")
        detail_metrics[4].metric("Pseudo-missing", f"{selected.pseudo_missing:,}")
        st.caption(
            f"Physical type: {selected.physical_type} · Effective missingness: "
            f"{selected.effective_missing_percent:.2f}%"
        )

        statistics_column, distribution_column = st.columns(2)
        with statistics_column:
            st.markdown("#### Type-specific statistics")
            if selected.statistics:
                st.dataframe(
                    pd.DataFrame(selected.statistics, columns=["Statistic", "Value"]),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.caption("No additional statistics apply to this column.")
        with distribution_column:
            st.markdown("#### Distribution")
            if selected.distribution:
                distribution = pd.DataFrame(
                    [
                        {"Bucket or value": bucket.label, "Count": bucket.count}
                        for bucket in selected.distribution
                    ]
                ).set_index("Bucket or value")
                st.bar_chart(distribution)
            else:
                st.caption("No non-missing values are available for a distribution.")
