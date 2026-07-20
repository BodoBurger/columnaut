"""Deterministic, data-type-aware profiles for Milestone 2."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

import numpy as np
import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
)

from columnaut.models import Finding, FindingConfidence, FindingSeverity

PSEUDO_MISSING_STRINGS = frozenset(
    {
        "",
        "-",
        "--",
        "?",
        "missing",
        "n/a",
        "na",
        "none",
        "not available",
        "null",
        "unknown",
    }
)
SUSPICIOUS_NUMERIC_SENTINELS = frozenset({-999, -9999, -99999, 9999, 99999, 999999})
SUSPICIOUS_SENTINEL_STRINGS = frozenset(str(value) for value in SUSPICIOUS_NUMERIC_SENTINELS)
BOOLEAN_STRINGS = frozenset({"true", "false", "yes", "no", "y", "n"})
IDENTIFIER_NAME_PATTERN = re.compile(r"(^id$|_id$|^id_|identifier|(^|_)key$|(^|_)code$)", re.I)


class SemanticType(StrEnum):
    """A practical interpretation of the values in a column."""

    EMPTY = "empty"
    BOOLEAN = "boolean"
    NUMERIC = "numeric"
    DATETIME = "datetime"
    IDENTIFIER = "identifier"
    CATEGORICAL = "categorical"
    TEXT = "text"


@dataclass(frozen=True, slots=True)
class DistributionBucket:
    """One display-ready bucket in a column distribution."""

    label: str
    count: int
    percent: float


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    """Facts, inferred meaning, and findings for one column."""

    column: str
    physical_type: str
    semantic_type: SemanticType
    semantic_confidence: FindingConfidence
    rows: int
    non_missing: int
    missing: int
    pseudo_missing: int
    effective_missing_percent: float
    unique: int
    duplicates: int
    statistics: tuple[tuple[str, str], ...]
    distribution: tuple[DistributionBucket, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True, slots=True)
class TableProfile:
    """A complete deterministic profile suitable for UI or AI interpretation."""

    columns: tuple[ColumnProfile, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True, slots=True)
class SemanticInference:
    semantic_type: SemanticType
    confidence: FindingConfidence
    converted: pd.Series
    invalid_count: int = 0


def _normalized_strings(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.casefold()


def pseudo_missing_mask(series: pd.Series) -> pd.Series:
    """Identify common placeholders while leaving the original values untouched."""

    mask = pd.Series(False, index=series.index, dtype=bool)
    present = series.notna()
    if not present.any():
        return mask

    values = series.loc[present]
    string_values = values.map(lambda value: isinstance(value, str))
    if string_values.any():
        normalized = _normalized_strings(values.loc[string_values])
        mask.loc[normalized.index] = normalized.isin(
            PSEUDO_MISSING_STRINGS | SUSPICIOUS_SENTINEL_STRINGS
        )

    numeric_values = values.map(
        lambda value: isinstance(value, (int, float, np.integer, np.floating))
        and not isinstance(value, (bool, np.bool_))
    )
    if numeric_values.any():
        numeric = pd.to_numeric(values.loc[numeric_values], errors="coerce")
        mask.loc[numeric.index] = numeric.isin(SUSPICIOUS_NUMERIC_SENTINELS)

    return mask


def _identifier_likelihood(column: str, series: pd.Series) -> bool:
    if series.empty:
        return False
    uniqueness = series.nunique(dropna=True) / len(series.index)
    return bool(IDENTIFIER_NAME_PATTERN.search(column)) and uniqueness >= 0.9


def infer_semantic_type(
    series: pd.Series,
    column: str,
    *,
    pseudo_mask: pd.Series | None = None,
) -> SemanticInference:
    """Infer a useful semantic type and expose uncertainty explicitly."""

    pseudo_mask = pseudo_mask if pseudo_mask is not None else pseudo_missing_mask(series)
    usable = series.loc[series.notna() & ~pseudo_mask]
    if usable.empty:
        return SemanticInference(
            SemanticType.EMPTY,
            FindingConfidence.HIGH,
            usable,
        )

    if is_bool_dtype(usable.dtype):
        return SemanticInference(SemanticType.BOOLEAN, FindingConfidence.HIGH, usable)
    if is_datetime64_any_dtype(usable.dtype):
        return SemanticInference(SemanticType.DATETIME, FindingConfidence.HIGH, usable)
    if is_numeric_dtype(usable.dtype):
        semantic_type = (
            SemanticType.IDENTIFIER
            if _identifier_likelihood(column, usable)
            else SemanticType.NUMERIC
        )
        return SemanticInference(semantic_type, FindingConfidence.HIGH, usable)

    normalized = _normalized_strings(usable)
    if normalized.isin(BOOLEAN_STRINGS).all():
        return SemanticInference(SemanticType.BOOLEAN, FindingConfidence.HIGH, normalized)

    numeric = pd.to_numeric(normalized.str.replace(",", "", regex=False), errors="coerce")
    numeric_ratio = float(numeric.notna().mean())
    if numeric_ratio >= 0.9:
        semantic_type = (
            SemanticType.IDENTIFIER
            if _identifier_likelihood(column, normalized)
            else SemanticType.NUMERIC
        )
        return SemanticInference(
            semantic_type,
            FindingConfidence.HIGH if numeric_ratio == 1 else FindingConfidence.MEDIUM,
            numeric.dropna(),
            invalid_count=int(numeric.isna().sum()),
        )

    datetimes = pd.to_datetime(normalized, errors="coerce", format="mixed")
    datetime_ratio = float(datetimes.notna().mean())
    if datetime_ratio >= 0.9:
        return SemanticInference(
            SemanticType.DATETIME,
            FindingConfidence.HIGH if datetime_ratio == 1 else FindingConfidence.MEDIUM,
            datetimes.dropna(),
            invalid_count=int(datetimes.isna().sum()),
        )

    unique = int(normalized.nunique(dropna=True))
    categorical_limit = min(50, max(10, round(len(normalized.index) * 0.2)))
    if unique <= categorical_limit:
        return SemanticInference(SemanticType.CATEGORICAL, FindingConfidence.MEDIUM, usable)
    return SemanticInference(SemanticType.TEXT, FindingConfidence.MEDIUM, usable)


def _format_number(value: float) -> str:
    if not isfinite(value):
        return str(value)
    return f"{value:,.4g}"


def _value_distribution(series: pd.Series, *, limit: int = 10) -> tuple[DistributionBucket, ...]:
    if series.empty:
        return ()
    counts = series.astype("string").value_counts(dropna=False).head(limit)
    total = len(series.index)
    return tuple(
        DistributionBucket(
            label=str(value),
            count=int(count),
            percent=round(100 * int(count) / total, 2),
        )
        for value, count in counts.items()
    )


def _numeric_distribution(series: pd.Series, *, bins: int = 10) -> tuple[DistributionBucket, ...]:
    numeric = pd.to_numeric(series, errors="coerce")
    finite = numeric[np.isfinite(numeric)]
    if finite.empty:
        return ()
    if finite.nunique() == 1:
        return (
            DistributionBucket(
                label=_format_number(float(finite.iloc[0])),
                count=len(finite.index),
                percent=100.0,
            ),
        )

    counts, edges = np.histogram(finite.to_numpy(dtype=float), bins=min(bins, finite.nunique()))
    total = int(counts.sum())
    return tuple(
        DistributionBucket(
            label=(
                f"{_format_number(float(edges[index]))} – "
                f"{_format_number(float(edges[index + 1]))}"
            ),
            count=int(count),
            percent=round(100 * int(count) / total, 2),
        )
        for index, count in enumerate(counts)
        if count
    )


def _numeric_statistics(series: pd.Series) -> tuple[tuple[str, str], ...]:
    numeric = pd.to_numeric(series, errors="coerce")
    finite = numeric[np.isfinite(numeric)]
    if finite.empty:
        return ()
    return (
        ("Minimum", _format_number(float(finite.min()))),
        ("25th percentile", _format_number(float(finite.quantile(0.25)))),
        ("Median", _format_number(float(finite.median()))),
        ("Mean", _format_number(float(finite.mean()))),
        ("75th percentile", _format_number(float(finite.quantile(0.75)))),
        ("Maximum", _format_number(float(finite.max()))),
        (
            "Standard deviation",
            _format_number(float(finite.std(ddof=1))) if len(finite) > 1 else "—",
        ),
        ("Zero values", f"{int(finite.eq(0).sum()):,}"),
        ("Negative values", f"{int(finite.lt(0).sum()):,}"),
    )


def _datetime_statistics(series: pd.Series) -> tuple[tuple[str, str], ...]:
    datetimes = pd.to_datetime(series, errors="coerce")
    datetimes = datetimes.dropna()
    if datetimes.empty:
        return ()
    earliest = datetimes.min()
    latest = datetimes.max()
    return (
        ("Earliest", earliest.isoformat()),
        ("Latest", latest.isoformat()),
        ("Span", f"{(latest - earliest).days:,} days"),
    )


def _text_statistics(series: pd.Series) -> tuple[tuple[str, str], ...]:
    lengths = series.astype("string").str.len().dropna()
    if lengths.empty:
        return ()
    return (
        ("Shortest length", f"{int(lengths.min()):,}"),
        ("Average length", f"{float(lengths.mean()):,.1f}"),
        ("Longest length", f"{int(lengths.max()):,}"),
    )


def _column_findings(
    column: str,
    series: pd.Series,
    inference: SemanticInference,
    pseudo_mask: pd.Series,
) -> list[Finding]:
    findings: list[Finding] = []
    row_count = len(series.index)
    missing_count = int(series.isna().sum())
    pseudo_count = int(pseudo_mask.sum())
    effective_missing = missing_count + pseudo_count
    effective_percent = 100 * effective_missing / row_count if row_count else 0.0

    if pseudo_count:
        examples = tuple(
            dict.fromkeys(str(value) for value in series.loc[pseudo_mask].tolist())
        )[:5]
        contains_suspicious_sentinel = any(
            (
                isinstance(value, (int, float, np.integer, np.floating))
                and not isinstance(value, (bool, np.bool_))
                and value in SUSPICIOUS_NUMERIC_SENTINELS
            )
            or (isinstance(value, str) and value.strip() in SUSPICIOUS_SENTINEL_STRINGS)
            for value in series.loc[pseudo_mask].tolist()
        )
        findings.append(
            Finding(
                code="pseudo_missing_values",
                title="Possible missing-value placeholders",
                message=(
                    f"Column '{column}' contains {pseudo_count:,} value(s) that look like "
                    "missing-value placeholders. They remain unchanged in the data."
                ),
                severity=FindingSeverity.WARNING,
                confidence=(
                    FindingConfidence.MEDIUM
                    if contains_suspicious_sentinel
                    else FindingConfidence.HIGH
                ),
                category="completeness",
                columns=(column,),
                affected_count=pseudo_count,
                affected_percent=round(100 * pseudo_count / row_count, 2) if row_count else 0.0,
                examples=examples,
            )
        )

    if effective_percent >= 50:
        findings.append(
            Finding(
                code="high_missingness",
                title="High effective missingness",
                message=(
                    f"Column '{column}' is {effective_percent:.1f}% missing when recognized "
                    "placeholders are included."
                ),
                severity=FindingSeverity.WARNING,
                confidence=FindingConfidence.HIGH,
                category="completeness",
                columns=(column,),
                affected_count=effective_missing,
                affected_percent=round(effective_percent, 2),
            )
        )

    usable = series.loc[series.notna() & ~pseudo_mask]
    if len(usable.index) > 1 and usable.nunique(dropna=True) == 1:
        findings.append(
            Finding(
                code="constant_column",
                title="Constant column",
                message=f"Column '{column}' has only one distinct non-missing value.",
                severity=FindingSeverity.INFO,
                confidence=FindingConfidence.HIGH,
                category="distribution",
                columns=(column,),
                affected_count=len(usable.index),
            )
        )

    if inference.invalid_count:
        findings.append(
            Finding(
                code="semantic_type_exceptions",
                title="Values do not match the inferred type",
                message=(
                    f"Column '{column}' looks like {inference.semantic_type.value} data, but "
                    f"{inference.invalid_count:,} value(s) could not be interpreted that way."
                ),
                severity=FindingSeverity.WARNING,
                confidence=FindingConfidence.MEDIUM,
                category="validity",
                columns=(column,),
                affected_count=inference.invalid_count,
                affected_percent=(
                    round(100 * inference.invalid_count / len(usable.index), 2)
                    if len(usable.index)
                    else 0.0
                ),
            )
        )

    if inference.semantic_type == SemanticType.NUMERIC:
        numeric = pd.to_numeric(inference.converted, errors="coerce")
        infinite_count = int(np.isinf(numeric).sum())
        if infinite_count:
            findings.append(
                Finding(
                    code="non_finite_numeric_values",
                    title="Non-finite numeric values",
                    message=f"Column '{column}' contains {infinite_count:,} infinite value(s).",
                    severity=FindingSeverity.ERROR,
                    confidence=FindingConfidence.HIGH,
                    category="validity",
                    columns=(column,),
                    affected_count=infinite_count,
                )
            )

        finite = numeric[np.isfinite(numeric)]
        if len(finite.index) >= 4 and finite.nunique() > 1:
            lower_quartile = float(finite.quantile(0.25))
            upper_quartile = float(finite.quantile(0.75))
            iqr = upper_quartile - lower_quartile
            if iqr > 0:
                lower = lower_quartile - 1.5 * iqr
                upper = upper_quartile + 1.5 * iqr
                outlier_count = int(((finite < lower) | (finite > upper)).sum())
                if outlier_count:
                    findings.append(
                        Finding(
                            code="iqr_outliers",
                            title="Values outside the typical range",
                            message=(
                                f"Column '{column}' has {outlier_count:,} value(s) outside the "
                                f"1.5×IQR range ({_format_number(lower)} to "
                                f"{_format_number(upper)}). These may be valid extremes."
                            ),
                            severity=FindingSeverity.INFO,
                            confidence=FindingConfidence.MEDIUM,
                            category="sensibility",
                            columns=(column,),
                            affected_count=outlier_count,
                            affected_percent=round(100 * outlier_count / len(finite.index), 2),
                        )
                    )

    if inference.semantic_type == SemanticType.DATETIME:
        datetimes = pd.to_datetime(inference.converted, errors="coerce").dropna()
        implausible = datetimes[(datetimes.dt.year < 1900) | (datetimes.dt.year > 2100)]
        if not implausible.empty:
            findings.append(
                Finding(
                    code="implausible_datetime_range",
                    title="Dates outside a common range",
                    message=(
                        f"Column '{column}' contains {len(implausible.index):,} date(s) before "
                        "1900 or after 2100. Confirm that the date format and values are intended."
                    ),
                    severity=FindingSeverity.WARNING,
                    confidence=FindingConfidence.MEDIUM,
                    category="sensibility",
                    columns=(column,),
                    affected_count=len(implausible.index),
                )
            )

    return findings


def profile_column(series: pd.Series, column: str | None = None) -> ColumnProfile:
    """Build a deterministic, data-type-aware profile for one series."""

    column = str(column if column is not None else series.name)
    pseudo_mask = pseudo_missing_mask(series)
    inference = infer_semantic_type(series, column, pseudo_mask=pseudo_mask)
    findings = _column_findings(column, series, inference, pseudo_mask)
    usable = series.loc[series.notna() & ~pseudo_mask]
    row_count = len(series.index)
    missing_count = int(series.isna().sum())
    pseudo_count = int(pseudo_mask.sum())

    if inference.semantic_type == SemanticType.NUMERIC:
        statistics = _numeric_statistics(inference.converted)
        distribution = _numeric_distribution(inference.converted)
    elif inference.semantic_type == SemanticType.DATETIME:
        statistics = _datetime_statistics(inference.converted)
        distribution = _value_distribution(
            pd.to_datetime(inference.converted, errors="coerce").dropna().dt.date
        )
    elif inference.semantic_type in {SemanticType.TEXT, SemanticType.IDENTIFIER}:
        statistics = _text_statistics(usable)
        distribution = _value_distribution(usable)
    else:
        statistics = ()
        distribution = _value_distribution(usable)

    try:
        unique = int(usable.nunique(dropna=True))
    except TypeError:
        unique = int(usable.astype("string").nunique(dropna=True))

    return ColumnProfile(
        column=column,
        physical_type=str(series.dtype),
        semantic_type=inference.semantic_type,
        semantic_confidence=inference.confidence,
        rows=row_count,
        non_missing=row_count - missing_count,
        missing=missing_count,
        pseudo_missing=pseudo_count,
        effective_missing_percent=(
            round(100 * (missing_count + pseudo_count) / row_count, 2) if row_count else 0.0
        ),
        unique=unique,
        duplicates=len(usable.index) - unique,
        statistics=statistics,
        distribution=distribution,
        findings=tuple(findings),
    )


def profile_table(dataframe: pd.DataFrame) -> TableProfile:
    """Profile all columns and flatten their findings for downstream consumers."""

    profiles = tuple(
        profile_column(dataframe.iloc[:, position], str(column))
        for position, column in enumerate(dataframe.columns)
    )
    findings = tuple(finding for profile in profiles for finding in profile.findings)
    return TableProfile(columns=profiles, findings=findings)


def column_profile_frame(profile: TableProfile) -> pd.DataFrame:
    """Create a compact UI-ready overview without losing the structured profiles."""

    return pd.DataFrame.from_records(
        [
            {
                "column": column.column,
                "exact dtype": column.physical_type,
                "inferred semantic type": column.semantic_type.value,
                "inference confidence": column.semantic_confidence.value,
                "non-missing": column.non_missing,
                "missing": column.missing,
                "pseudo-missing": column.pseudo_missing,
                "effective missing %": column.effective_missing_percent,
                "unique": column.unique,
            }
            for column in profile.columns
        ]
    )
