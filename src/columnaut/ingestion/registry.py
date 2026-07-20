"""Adapter selection by filename."""

from __future__ import annotations

from collections.abc import Iterable

from columnaut.ingestion.base import TabularAdapter
from columnaut.ingestion.csv_adapter import CsvAdapter
from columnaut.ingestion.excel_adapter import ExcelAdapter
from columnaut.ingestion.parquet_adapter import ParquetAdapter


class AdapterRegistry:
    """Resolve a source filename to the first registered adapter that supports it."""

    def __init__(self, adapters: Iterable[TabularAdapter]) -> None:
        self._adapters = tuple(adapters)

    def for_source(self, source_name: str) -> TabularAdapter:
        """Return the matching adapter or raise an error listing supported extensions."""

        for adapter in self._adapters:
            if adapter.supports(source_name):
                return adapter
        supported = ", ".join(
            sorted(extension for adapter in self._adapters for extension in adapter.extensions)
        )
        raise ValueError(f"Unsupported file type. Supported extensions: {supported}.")


default_registry = AdapterRegistry([CsvAdapter(), ParquetAdapter(), ExcelAdapter()])
