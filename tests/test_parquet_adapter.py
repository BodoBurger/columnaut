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
