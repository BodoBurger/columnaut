import pandas as pd

from columnaut.ingestion.quality import common_table_warnings


def test_common_warnings_handle_duplicate_column_names_by_position() -> None:
    dataframe = pd.DataFrame([[1, "open"], [2, 3]], columns=["value", "value"])

    warnings = common_table_warnings(dataframe)

    mixed_type_findings = [
        finding for finding in warnings if finding.code == "mixed_value_types"
    ]
    assert len(mixed_type_findings) == 1
    assert mixed_type_findings[0].columns == ("value",)


def test_empty_row_numbers_use_positions_instead_of_index_labels() -> None:
    dataframe = pd.DataFrame(
        {"value": [1, None]},
        index=["first", "second"],
    )

    warnings = common_table_warnings(dataframe, source_row_offset=1)

    empty_rows = next(finding for finding in warnings if finding.code == "empty_rows")
    assert empty_rows.row_numbers == (2,)
