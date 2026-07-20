import pandas as pd

from columnaut.models import FindingConfidence, FindingSeverity
from columnaut.profiling.advanced import (
    SemanticType,
    column_profile_frame,
    profile_column,
    profile_table,
    pseudo_missing_mask,
)


def finding_codes(profile) -> set[str]:
    return {finding.code for finding in profile.findings}


def test_pseudo_missing_values_are_counted_without_changing_the_series() -> None:
    series = pd.Series([None, " ", "N/A", "unknown", -999, "-9999", "valid"])
    original = series.copy()

    mask = pseudo_missing_mask(series)
    profile = profile_column(series, "status")

    assert mask.tolist() == [False, True, True, True, True, True, False]
    assert profile.missing == 1
    assert profile.pseudo_missing == 5
    assert profile.effective_missing_percent == 85.71
    pd.testing.assert_series_equal(series, original)

    finding = next(item for item in profile.findings if item.code == "pseudo_missing_values")
    assert finding.severity == FindingSeverity.WARNING
    assert finding.confidence == FindingConfidence.MEDIUM
    assert finding.affected_count == 5


def test_numeric_strings_with_one_exception_report_inference_uncertainty() -> None:
    series = pd.Series([str(number) for number in range(1, 10)] + ["oops"])

    profile = profile_column(series, "amount")

    assert profile.semantic_type == SemanticType.NUMERIC
    assert profile.semantic_confidence == FindingConfidence.MEDIUM
    assert ("Minimum", "1") in profile.statistics
    assert ("Maximum", "9") in profile.statistics
    assert "semantic_type_exceptions" in finding_codes(profile)


def test_numeric_profile_has_distribution_statistics_and_sensibility_finding() -> None:
    profile = profile_column(pd.Series([10, 11, 12, 13, 1000]), "amount")

    assert profile.semantic_type == SemanticType.NUMERIC
    assert ("Median", "12") in profile.statistics
    assert sum(bucket.count for bucket in profile.distribution) == 5
    assert "iqr_outliers" in finding_codes(profile)


def test_datetime_profile_reports_implausible_generic_range() -> None:
    profile = profile_column(
        pd.Series(["2024-01-01", "2024-02-01", "2201-01-01"]),
        "event_date",
    )

    assert profile.semantic_type == SemanticType.DATETIME
    assert profile.semantic_confidence == FindingConfidence.HIGH
    assert "implausible_datetime_range" in finding_codes(profile)
    assert dict(profile.statistics)["Span"] == "64,648 days"


def test_identifier_and_free_text_receive_different_semantic_types() -> None:
    identifier = profile_column(pd.Series(range(20)), "customer_id")
    notes = profile_column(
        pd.Series(
            [
                f"Description number {number} with distinct narrative text"
                for number in range(20)
            ]
        ),
        "notes",
    )

    assert identifier.semantic_type == SemanticType.IDENTIFIER
    assert notes.semantic_type == SemanticType.TEXT
    assert "Average length" in dict(notes.statistics)


def test_table_profile_flattens_column_findings_for_downstream_consumers() -> None:
    dataframe = pd.DataFrame(
        {
            "status": ["unknown", "ready", "ready"],
            "constant": [1, 1, 1],
        }
    )

    profile = profile_table(dataframe)

    assert len(profile.columns) == 2
    assert {finding.code for finding in profile.findings} == {
        "constant_column",
        "pseudo_missing_values",
    }


def test_table_profile_handles_duplicate_dataframe_column_names_by_position() -> None:
    dataframe = pd.DataFrame([[1, "open"], [2, "closed"]], columns=["value", "value"])

    profile = profile_table(dataframe)

    assert [column.semantic_type for column in profile.columns] == [
        SemanticType.NUMERIC,
        SemanticType.CATEGORICAL,
    ]


def test_table_profile_supports_arrow_backed_pandas_columns() -> None:
    dataframe = pd.DataFrame(
        {
            "customer_id": [1, 2, 3],
            "amount": [10.0, None, 30.0],
            "status": ["open", "unknown", "closed"],
        }
    ).convert_dtypes(dtype_backend="pyarrow")

    profile = profile_table(dataframe)

    assert [column.semantic_type for column in profile.columns] == [
        SemanticType.IDENTIFIER,
        SemanticType.NUMERIC,
        SemanticType.CATEGORICAL,
    ]
    assert profile.columns[1].missing == 1
    assert profile.columns[2].pseudo_missing == 1
    assert all("[pyarrow]" in column.physical_type for column in profile.columns)

    overview = column_profile_frame(profile)
    assert overview["exact dtype"].tolist() == [
        "int64[pyarrow]",
        "int64[pyarrow]",
        "string[pyarrow]",
    ]
