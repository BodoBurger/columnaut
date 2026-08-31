from io import BytesIO

import pandas as pd

from columnaut.ingestion.parquet_adapter import ParquetAdapter


def test_parquet_adapter_loads_table() -> None:
    source = pd.DataFrame({"id": [1, 2], "amount": [1.5, 2.5]})
    buffer = BytesIO()
    source.to_parquet(buffer, index=False)

    loaded = ParquetAdapter().load(buffer.getvalue(), "sample.parquet")

    expected = source.convert_dtypes(dtype_backend="pyarrow")
    pd.testing.assert_frame_equal(loaded.dataframe, expected)
    assert all(isinstance(dtype, pd.ArrowDtype) for dtype in loaded.dataframe.dtypes)
    assert loaded.source_format == "parquet"


def test_parquet_adapter_counts_duplicate_rows_with_list_values() -> None:
    source = pd.DataFrame({"items": [[1, 2], [1, 2], [3]]})
    buffer = BytesIO()
    source.to_parquet(buffer, index=False)

    loaded = ParquetAdapter().load(buffer.getvalue(), "sample.parquet")

    duplicate_rows = next(
        finding for finding in loaded.warnings if finding.code == "duplicate_rows"
    )
    assert duplicate_rows.message == "Found 1 row(s) that duplicate an earlier row."
