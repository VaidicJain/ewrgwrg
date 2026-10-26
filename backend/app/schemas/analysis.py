from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ComparisonRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_time: datetime = Field(description="Start of the target hour (UTC)")
    cutoff_time: datetime = Field(description="Decision cutoff used for this hour")
    actual_mw: float | None = Field(description="Mean of the two half-hourly actuals; null if incomplete")
    actual_halfhours: int = Field(description="How many half-hour actuals were found (2 = complete)")
    forecast_mw: float | None = Field(description="Latest forecast published at or before the cutoff")
    forecast_publish_time: datetime | None
    horizon_hours: float | None = Field(description="Target hour minus forecast publish time, in hours")
    error_mw: float | None = Field(description="forecast - actual; positive means over-forecast")


class CoverageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_hours: int
    with_forecast: int
    with_actual: int
    compared: int = Field(description="Hours that have both a forecast and an actual")
    missing_forecast: int
    missing_actual: int


class ErrorStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    n: int = Field(description="Hours scored (have both forecast and actual)")
    mae_mw: float = Field(description="Mean absolute error")
    rmse_mw: float = Field(description="Root mean squared error; punishes big misses more than MAE")
    bias_mw: float = Field(description="Mean signed error; positive = forecasts run high")
    median_abs_error_mw: float
    p90_abs_error_mw: float = Field(description="90% of hours had an absolute error at or below this")
    p95_abs_error_mw: float = Field(description="95% of hours had an absolute error at or below this")
    max_abs_error_mw: float
    mean_actual_mw: float
    mae_pct_of_mean_actual: float = Field(description="MAE as % of mean actual generation")
    mape_pct: float | None = Field(description="Mean absolute % error over hours with actual >= mape_floor_mw")


class GroupStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    n: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float


class SafetyBufferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    confidence: float
    shortfall_buffer_mw: float = Field(
        description="Extra MW to hold so that `confidence` of hours are covered against a wind shortfall"
    )
    surplus_margin_mw: float = Field(
        description="At the same confidence, wind exceeded the forecast by at most this many MW"
    )


class AccuracyResponse(BaseModel):
    start_date: date
    end_date: date
    cutoff_time: str
    days_before: int
    resolution: str = "hourly"
    mape_floor_mw: float
    coverage: CoverageRead
    warnings: list[str]
    overall: ErrorStatsRead | None
    safety_buffer: SafetyBufferRead | None
    by_hour_of_day: list[GroupStatsRead]
    by_day: list[GroupStatsRead]
    by_horizon: list[GroupStatsRead]


class ComparisonResponse(BaseModel):
    start_date: date
    end_date: date
    cutoff_time: str
    days_before: int
    resolution: str = "hourly"
    coverage: CoverageRead
    warnings: list[str]
    rows: list[ComparisonRowRead]
