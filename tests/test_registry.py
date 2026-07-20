import pytest

from columnaut.ingestion.excel_adapter import ExcelAdapter
from columnaut.ingestion.registry import default_registry


def test_registry_selects_excel_adapter_for_both_excel_extensions() -> None:
    assert isinstance(default_registry.for_source("book.xlsx"), ExcelAdapter)
    assert isinstance(default_registry.for_source("BOOK.XLS"), ExcelAdapter)


def test_registry_rejects_unknown_extension() -> None:
    with pytest.raises(ValueError, match="Unsupported file type"):
        default_registry.for_source("notes.txt")
