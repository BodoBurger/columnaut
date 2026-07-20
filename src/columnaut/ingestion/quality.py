"""Checks that are useful immediately after tabular ingestion."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime, time
from numbers import Number
from typing import Any

import pandas as pd

from columnaut.models import IngestionWarning


def _is_missing(value: Any) -> bool:
    try:
        result = pd.isna(value)
        return bool(result) if not hasattr(result, "__len__") else False
    except (TypeError, ValueError):
        return False


def value_family(value: Any) -> str:
    """Return a compact, user-facing physical type family."""

    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (datetime, date, time, pd.Timestamp)):
        return "datetime"
    if isinstance(value, Number):
        return "number"
    if isinstance(value, str):
        return "text"
    return type(value).__name__


def make_unique_headers(values: Iterable[Any]) -> tuple[list[str], list[str], list[int]]:
    """Create stable column names while recording duplicate and blank headers."""

    counts: Counter[str] = Counter()
    headers: list[str] = []
    duplicates: list[str] = []
    blank_positions: list[int] = []

    for position, value in enumerate(values, start=1):
        if _is_missing(value) or not str(value).strip():
            base = f"column_{position}"
            blank_positions.append(position)
        else:
            base = str(value).strip()

        key = base.casefold()
        counts[key] += 1
        if counts[key] > 1:
            duplicates.append(base)
            headers.append(f"{base}__{counts[key]}")
        else:
            headers.append(base)

    return headers, duplicates, blank_positions


def common_table_warnings(
    dataframe: pd.DataFrame,
    *,
    source_row_offset: int = 0,
) -> list[IngestionWarning]:
    """Find structural issues without imposing domain-specific expectations."""

    warnings: list[IngestionWarning] = []

    empty_rows = dataframe.index[dataframe.isna().all(axis=1)].tolist()
    if empty_rows:
        displayed_rows = tuple(int(index) + source_row_offset for index in empty_rows[:20])
        warnings.append(
            IngestionWarning(
                code="empty_rows",
                title="Entirely empty rows",
                message=(
                    f"Found {len(empty_rows)} entirely empty row(s). "
                    "They are retained so the source can be inspected faithfully."
                ),
                row_numbers=displayed_rows,
            )
        )

    empty_columns = tuple(str(column) for column in dataframe.columns[dataframe.isna().all()])
    if empty_columns:
        warnings.append(
            IngestionWarning(
                code="empty_columns",
                title="Entirely empty columns",
                message=f"Found {len(empty_columns)} column(s) without any values.",
                columns=empty_columns,
            )
        )

    for column in dataframe.columns:
        families = {
            value_family(value)
            for value in dataframe[column].tolist()
            if not _is_missing(value)
        }
        if len(families) > 1:
            warnings.append(
                IngestionWarning(
                    code="mixed_value_types",
                    title="Mixed value types",
                    message=(
                        f"Column '{column}' contains multiple physical value types: "
                        f"{', '.join(sorted(families))}."
                    ),
                    columns=(str(column),),
                )
            )

    non_empty = dataframe.dropna(how="all")
    duplicate_count = int(non_empty.duplicated().sum()) if not non_empty.empty else 0
    if duplicate_count:
        warnings.append(
            IngestionWarning(
                code="duplicate_rows",
                title="Duplicate rows",
                message=f"Found {duplicate_count} row(s) that duplicate an earlier row.",
            )
        )

    return warnings
