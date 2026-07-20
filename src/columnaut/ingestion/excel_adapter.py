"""Excel workbook ingestion with sheet and header selection."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from columnaut.ingestion.base import TabularAdapter
from columnaut.ingestion.quality import common_table_warnings, make_unique_headers
from columnaut.models import Finding, LoadedTable, LoadOptions, SourceInspection


class ExcelAdapter(TabularAdapter):
    extensions = (".xlsx", ".xls")

    def inspect(self, payload: bytes, source_name: str) -> SourceInspection:
        with pd.ExcelFile(BytesIO(payload)) as workbook:
            sheet_names = tuple(workbook.sheet_names)
        return SourceInspection(
            source_name=source_name,
            source_format=Path(source_name).suffix.lower().lstrip("."),
            sheet_names=sheet_names,
        )

    def load(
        self,
        payload: bytes,
        source_name: str,
        options: LoadOptions | None = None,
    ) -> LoadedTable:
        options = options or LoadOptions()
        if options.header_row < 0:
            raise ValueError("The header row must be zero or greater.")

        source_format = Path(source_name).suffix.lower().lstrip(".")
        with pd.ExcelFile(BytesIO(payload)) as workbook:
            available_sheets = tuple(workbook.sheet_names)
            sheet_name = options.sheet_name or available_sheets[0]
            if sheet_name not in available_sheets:
                raise ValueError(f"Sheet '{sheet_name}' does not exist in this workbook.")
            raw = workbook.parse(
                sheet_name=sheet_name,
                header=None,
                keep_default_na=False,
                na_values=[""],
            )

        if raw.empty:
            return LoadedTable(
                dataframe=pd.DataFrame(),
                source_name=source_name,
                source_format=source_format,
                sheet_name=sheet_name,
                header_row=options.header_row,
                warnings=[
                    Finding(
                        code="empty_sheet",
                        title="Empty sheet",
                        message=f"Sheet '{sheet_name}' does not contain tabular data.",
                    )
                ],
                metadata={"available_sheets": available_sheets},
            )

        if options.header_row >= len(raw.index):
            raise ValueError(
                f"Header row {options.header_row + 1} is outside the sheet, "
                f"which has {len(raw.index)} detected row(s)."
            )

        headers, duplicate_headers, blank_positions = make_unique_headers(
            raw.iloc[options.header_row].tolist()
        )
        dataframe = raw.iloc[options.header_row + 1 :].copy()
        dataframe.columns = headers
        dataframe = dataframe.reset_index(drop=True).infer_objects().convert_dtypes(
            dtype_backend="pyarrow"
        )

        warnings: list[Finding] = []
        if duplicate_headers:
            unique_duplicates = tuple(dict.fromkeys(duplicate_headers))
            warnings.append(
                Finding(
                    code="duplicate_headers",
                    title="Duplicate column headers",
                    message=(
                        "Duplicate headers were renamed with a numeric suffix: "
                        f"{', '.join(unique_duplicates)}."
                    ),
                    columns=unique_duplicates,
                )
            )

        if blank_positions:
            warnings.append(
                Finding(
                    code="header_gaps",
                    title="Blank cells in the header row",
                    message=(
                        "The selected header contains blank cells at Excel column position(s) "
                        f"{', '.join(map(str, blank_positions))}. This can be caused by merged "
                        "cells or a header row that starts elsewhere. Placeholder names were added."
                    ),
                )
            )

        warnings.extend(self._merged_cell_warnings(payload, source_name, sheet_name))
        warnings.extend(
            common_table_warnings(
                dataframe,
                source_row_offset=options.header_row + 2,
            )
        )

        return LoadedTable(
            dataframe=dataframe,
            source_name=source_name,
            source_format=source_format,
            sheet_name=sheet_name,
            header_row=options.header_row,
            warnings=warnings,
            metadata={"available_sheets": available_sheets},
        )

    @staticmethod
    def _merged_cell_warnings(
        payload: bytes,
        source_name: str,
        sheet_name: str,
    ) -> list[Finding]:
        if Path(source_name).suffix.lower() != ".xlsx":
            return []

        from openpyxl import load_workbook

        workbook = load_workbook(BytesIO(payload), read_only=False, data_only=True)
        try:
            ranges = tuple(
                str(cell_range) for cell_range in workbook[sheet_name].merged_cells.ranges
            )
        finally:
            workbook.close()

        if not ranges:
            return []
        examples = ", ".join(ranges[:5])
        suffix = "" if len(ranges) <= 5 else f" and {len(ranges) - 5} more"
        return [
            Finding(
                code="merged_cells",
                title="Merged cells",
                message=(
                    f"The sheet contains {len(ranges)} merged range(s): {examples}{suffix}. "
                    "Merged cells can create blanks or ambiguous column structure when imported."
                ),
            )
        ]
