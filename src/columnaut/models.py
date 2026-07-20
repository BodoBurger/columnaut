"""Shared data structures used by ingestion and reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class IngestionWarning:
    """A non-fatal issue discovered while a source is loaded."""

    code: str
    title: str
    message: str
    columns: tuple[str, ...] = ()
    row_numbers: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class LoadOptions:
    """Options that affect conversion of a source to a table."""

    sheet_name: str | None = None
    header_row: int = 0


@dataclass(frozen=True, slots=True)
class SourceInspection:
    """Metadata that can be read before a complete table is loaded."""

    source_name: str
    source_format: str
    sheet_names: tuple[str, ...] = ()


@dataclass(slots=True)
class LoadedTable:
    """A normalized table together with source and ingestion information."""

    dataframe: pd.DataFrame
    source_name: str
    source_format: str
    sheet_name: str | None = None
    header_row: int | None = None
    warnings: list[IngestionWarning] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
