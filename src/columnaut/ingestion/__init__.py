"""Adapters that convert tabular files to a common in-memory representation."""

from columnaut.ingestion.registry import AdapterRegistry, default_registry

__all__ = ["AdapterRegistry", "default_registry"]
