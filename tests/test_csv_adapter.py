from columnaut.ingestion.csv_adapter import CsvAdapter


def test_csv_adapter_loads_table_and_common_findings() -> None:
    payload = b"id,name,score\n1,Ada,10\n2,,20\n2,,20\n"

    loaded = CsvAdapter().load(payload, "sample.csv")

    assert loaded.dataframe.shape == (3, 3)
    assert list(loaded.dataframe.columns) == ["id", "name", "score"]
    assert loaded.dataframe["name"].isna().sum() == 2
    assert "duplicate_rows" in {warning.code for warning in loaded.warnings}


def test_csv_adapter_preserves_textual_missing_markers_for_profiling() -> None:
    payload = b"id,status\n1,N/A\n2,unknown\n3,\n"

    loaded = CsvAdapter().load(payload, "sample.csv")

    assert loaded.dataframe["status"].tolist()[:2] == ["N/A", "unknown"]
    assert loaded.dataframe["status"].isna().sum() == 1
