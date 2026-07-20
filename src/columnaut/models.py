"""Shared data structures used by ingestion and reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import pandas as pd


class FindingSeverity(StrEnum):
    """How strongly a finding can affect confidence in the dataset."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingConfidence(StrEnum):
    """How certain Columnaut is that the finding has the stated meaning."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Finding:
    """Structured evidence about a dataset without applying a validation rule."""

    code: str
    title: str
    message: str
    severity: FindingSeverity = FindingSeverity.WARNING
    confidence: FindingConfidence = FindingConfidence.HIGH
    category: str = "quality"
    columns: tuple[str, ...] = ()
    row_numbers: tuple[int, ...] = ()
    affected_count: int | None = None
    affected_percent: float | None = None
    examples: tuple[str, ...] = ()


# Kept as a compatibility name for callers that imported the Milestone 1 model.
IngestionWarning = Finding


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
    warnings: list[Finding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
