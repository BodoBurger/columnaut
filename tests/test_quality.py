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
