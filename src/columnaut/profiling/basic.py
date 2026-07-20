"""Basic, deterministic dataset and column characteristics."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class DatasetOverview:
    """Dataset-level counts and an in-memory size estimate for reporting."""

    rows: int
    columns: int
    missing_cells: int
    missing_percent: float
    duplicate_rows: int
    memory_bytes: int


def dataset_overview(dataframe: pd.DataFrame) -> DatasetOverview:
    """Summarize table shape, missingness, duplicates, and memory usage.

    Entirely empty rows are excluded from the duplicate count because ingestion reports them as
    a separate structural finding. The input dataframe is never modified.
    """

    total_cells = int(dataframe.shape[0] * dataframe.shape[1])
    missing_cells = int(dataframe.isna().sum().sum())
    return DatasetOverview(
        rows=int(dataframe.shape[0]),
        columns=int(dataframe.shape[1]),
        missing_cells=missing_cells,
        missing_percent=(100 * missing_cells / total_cells) if total_cells else 0.0,
        duplicate_rows=int(dataframe.dropna(how="all").duplicated().sum()),
        memory_bytes=int(dataframe.memory_usage(index=True, deep=True).sum()),
    )


def column_overview(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return one row of basic physical characteristics per dataframe column.

    Unhashable values are converted to strings only for the unique-value calculation; source
    values and the dataframe itself remain unchanged.
    """

    records: list[dict[str, object]] = []
    row_count = len(dataframe.index)
    for column in dataframe.columns:
        series = dataframe[column]
        missing = int(series.isna().sum())
        try:
            unique = int(series.nunique(dropna=True))
        except TypeError:
            unique = int(series.dropna().astype(str).nunique())
        records.append(
            {
                "column": str(column),
                "dtype": str(series.dtype),
                "non_null": row_count - missing,
                "missing": missing,
                "missing_%": round(100 * missing / row_count, 2) if row_count else 0.0,
                "unique": unique,
            }
        )
    return pd.DataFrame.from_records(records)


def format_bytes(size: int) -> str:
    """Format a byte count for display using successive powers of 1024."""

    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
