"""Shared helpers for working with arbitrary tabular values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
from pandas.api.types import is_scalar

_COMPARABLE_VALUE = object()


def _hashable_value(value: Any) -> Any:
    """Return a collision-safe hashable representation for a cell value."""

    if is_scalar(value) and pd.isna(value):
        return (_COMPARABLE_VALUE, "missing")
    if isinstance(value, Mapping):
        items = (
            (_hashable_value(key), _hashable_value(item))
            for key, item in value.items()
        )
        return (_COMPARABLE_VALUE, "mapping", frozenset(items))
    if isinstance(value, list):
        return (_COMPARABLE_VALUE, "list", tuple(_hashable_value(item) for item in value))
    if isinstance(value, tuple):
        return (_COMPARABLE_VALUE, "tuple", tuple(_hashable_value(item) for item in value))
    if isinstance(value, (set, frozenset)):
        items = frozenset(_hashable_value(item) for item in value)
        return (_COMPARABLE_VALUE, "set", items)

    try:
        hash(value)
    except TypeError:
        return (
            _COMPARABLE_VALUE,
            "representation",
            type(value).__qualname__,
            repr(value),
        )
    return (_COMPARABLE_VALUE, "scalar", value)


def duplicate_row_count(dataframe: pd.DataFrame) -> int:
    """Count repeated non-empty rows, including rows with unhashable cell values."""

    non_empty = dataframe.dropna(how="all")
    if non_empty.empty:
        return 0
    try:
        return int(non_empty.duplicated().sum())
    except (NotImplementedError, TypeError):
        comparable = non_empty.map(_hashable_value)
        return int(comparable.duplicated().sum())
