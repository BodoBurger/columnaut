"""Base contract for tabular source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from columnaut.models import LoadedTable, LoadOptions, SourceInspection


class TabularAdapter(ABC):
    """Convert one or more related file extensions into a table."""

    extensions: tuple[str, ...] = ()

    def supports(self, source_name: str) -> bool:
        return Path(source_name).suffix.lower() in self.extensions

    def inspect(self, payload: bytes, source_name: str) -> SourceInspection:
        """Return lightweight metadata needed to configure a load."""

        return SourceInspection(
            source_name=source_name,
            source_format=Path(source_name).suffix.lower().lstrip("."),
        )

    @abstractmethod
    def load(
        self,
        payload: bytes,
        source_name: str,
        options: LoadOptions | None = None,
    ) -> LoadedTable:
        """Load a file payload into a normalized table."""
