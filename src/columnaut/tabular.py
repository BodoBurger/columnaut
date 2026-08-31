"""Shared helpers for working with arbitrary tabular values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


def _hashable_value(value: Any) -> Any:
    """Return an equality-preserving representation for common unhashable values."""

    try:
        hash(value)
    except TypeError:
        if isinstance(value, Mapping):
            items = (
                (_hashable_value(key), _hashable_value(item))
                for key, item in value.items()
            )
            return ("mapping", frozenset(items))
        if isinstance(value, list):
            return ("list", tuple(_hashable_value(item) for item in value))
        if isinstance(value, tuple):
            return ("tuple", tuple(_hashable_value(item) for item in value))
        if isinstance(value, (set, frozenset)):
            return ("set", frozenset(_hashable_value(item) for item in value))
        return (type(value).__qualname__, repr(value))
    return value


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
