"""Parquet ingestion adapter."""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from columnaut.ingestion.base import TabularAdapter
from columnaut.ingestion.quality import common_table_warnings
from columnaut.models import LoadedTable, LoadOptions


class ParquetAdapter(TabularAdapter):
    extensions = (".parquet", ".pq")

    def load(
        self,
        payload: bytes,
        source_name: str,
        options: LoadOptions | None = None,
    ) -> LoadedTable:
        del options
        dataframe = pd.read_parquet(BytesIO(payload))
        return LoadedTable(
            dataframe=dataframe,
            source_name=source_name,
            source_format="parquet",
            warnings=common_table_warnings(dataframe, source_row_offset=1),
        )
