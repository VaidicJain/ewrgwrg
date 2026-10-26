"""Pure accuracy metrics on the forecast-vs-actual table. No database, no HTTP.

Sign convention (same as selection.py): error = forecast - actual.
  positive error = over-forecast  -> the buyer expected more wind than arrived and would under-buy
  negative error = under-forecast -> more wind arrived than expected (surplus)
"""

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from math import ceil, floor, sqrt
from statistics import fmean

from app.services.selection import ComparisonRow

DEFAULT_MAPE_FLOOR_MW = 1000.0


@dataclass(frozen=True)
class ErrorStats:
    n: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float
    median_abs_error_mw: float
    p90_abs_error_mw: float
    p95_abs_error_mw: float
    max_abs_error_mw: float
    mean_actual_mw: float
    mae_pct_of_mean_actual: float
    mape_pct: float | None  # None when no hour has actual >= the floor


@dataclass(frozen=True)
class GroupStats:
    label: str
    n: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float


@dataclass(frozen=True)
class SafetyBuffer:
    confidence: float
    shortfall_buffer_mw: float  # extra power to hold so that `confidence` of hours are covered
    surplus_margin_mw: float  # how much more wind than forecast arrived, at the same confidence


def quantile(values: Sequence[float], q: float) -> float:
    """Quantile with linear interpolation between ranks (same as numpy's default)."""
    if not values:
        raise ValueError("quantile of an empty sequence")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be between 0 and 1")
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low, high = floor(position), ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def compared_rows(rows: Iterable[ComparisonRow]) -> list[ComparisonRow]:
    """Only hours that have both a forecast and a complete actual can be scored."""
    return [r for r in rows if r.error_mw is not None and r.actual_mw is not None]


def compute_error_stats(
    rows: Iterable[ComparisonRow], mape_floor_mw: float = DEFAULT_MAPE_FLOOR_MW
) -> ErrorStats | None:
    scored = compared_rows(rows)
    if not scored:
        return None

    errors = [r.error_mw for r in scored]
    abs_errors = [abs(e) for e in errors]
    actuals = [r.actual_mw for r in scored]

    mae = fmean(abs_errors)
    mean_actual = fmean(actuals)

    # Percentage error is unstable when the actual is close to zero, so small actuals are skipped.
    pct_errors = [abs(r.error_mw) / r.actual_mw * 100 for r in scored if r.actual_mw >= mape_floor_mw]

    return ErrorStats(
        n=len(scored),
        mae_mw=mae,
        rmse_mw=sqrt(fmean(e * e for e in errors)),
        bias_mw=fmean(errors),
        median_abs_error_mw=quantile(abs_errors, 0.5),
        p90_abs_error_mw=quantile(abs_errors, 0.9),
        p95_abs_error_mw=quantile(abs_errors, 0.95),
        max_abs_error_mw=max(abs_errors),
        mean_actual_mw=mean_actual,
        mae_pct_of_mean_actual=(mae / mean_actual * 100) if mean_actual else 0.0,
        mape_pct=fmean(pct_errors) if pct_errors else None,
    )


def safety_buffer(rows: Iterable[ComparisonRow], confidence: float = 0.95) -> SafetyBuffer | None:
    """How much extra supply the buyer should hold to be covered in `confidence` of hours.

    The risk is over-forecast (positive error): wind came in lower than expected, so the buyer
    bought too little. The buffer is the `confidence` quantile of the signed error, floored at 0.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be strictly between 0 and 1")
    scored = compared_rows(rows)
    if not scored:
        return None

    errors = [r.error_mw for r in scored]
    return SafetyBuffer(
        confidence=confidence,
        shortfall_buffer_mw=max(0.0, quantile(errors, confidence)),
        surplus_margin_mw=max(0.0, -quantile(errors, 1.0 - confidence)),
    )


def _group(
    rows: Iterable[ComparisonRow],
    key_fn: Callable[[ComparisonRow], object],
    label_fn: Callable[[object], str],
) -> list[GroupStats]:
    buckets: dict[object, list[float]] = defaultdict(list)
    for row in compared_rows(rows):
        buckets[key_fn(row)].append(row.error_mw)

    result = []
    for key in sorted(buckets):
        errors = buckets[key]
        result.append(
            GroupStats(
                label=label_fn(key),
                n=len(errors),
                mae_mw=fmean(abs(e) for e in errors),
                rmse_mw=sqrt(fmean(e * e for e in errors)),
                bias_mw=fmean(errors),
            )
        )
    return result


def by_hour_of_day(rows: Iterable[ComparisonRow]) -> list[GroupStats]:
    return _group(rows, lambda r: r.start_time.hour, lambda k: f"{k:02d}:00")


def by_day(rows: Iterable[ComparisonRow]) -> list[GroupStats]:
    return _group(rows, lambda r: r.start_time.date(), lambda k: k.isoformat())


def by_horizon(rows: Iterable[ComparisonRow], bucket_hours: int = 6) -> list[GroupStats]:
    """Group by how long before the target hour the chosen forecast was published."""
    if bucket_hours < 1:
        raise ValueError("bucket_hours must be at least 1")

    def bucket_start(row: ComparisonRow) -> int:
        return int(row.horizon_hours // bucket_hours) * bucket_hours

    return _group(rows, bucket_start, lambda k: f"{k}-{k + bucket_hours}h")
