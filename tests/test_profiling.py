import pandas as pd

from columnaut.profiling.basic import column_overview, dataset_overview


def test_basic_profile_is_deterministic() -> None:
    dataframe = pd.DataFrame({"id": [1, 1, 2], "value": [10.0, 10.0, None]})

    overview = dataset_overview(dataframe)
    columns = column_overview(dataframe).set_index("column")

    assert overview.rows == 3
    assert overview.columns == 2
    assert overview.missing_cells == 1
    assert overview.duplicate_rows == 1
    assert columns.loc["value", "unique"] == 1
    assert columns.loc["value", "missing"] == 1


def test_column_overview_handles_duplicate_column_names_by_position() -> None:
    dataframe = pd.DataFrame([[1, "open"], [2, "closed"]], columns=["value", "value"])

    overview = column_overview(dataframe)

    assert overview["column"].tolist() == ["value", "value"]
    assert overview["unique"].tolist() == [2, 2]
