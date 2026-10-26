/** Shapes returned by the FastAPI backend (see backend/app/schemas/analysis.py). */

export interface Coverage {
  total_hours: number;
  with_forecast: number;
  with_actual: number;
  compared: number;
  missing_forecast: number;
  missing_actual: number;
}

export interface ComparisonRow {
  start_time: string;
  cutoff_time: string;
  actual_mw: number | null;
  actual_halfhours: number;
  forecast_mw: number | null;
  forecast_publish_time: string | null;
  horizon_hours: number | null;
  /** forecast - actual; positive means the forecast was too high. */
  error_mw: number | null;
}

export interface ComparisonResponse {
  start_date: string;
  end_date: string;
  cutoff_time: string;
  days_before: number;
  resolution: string;
  coverage: Coverage;
  warnings: string[];
  rows: ComparisonRow[];
}

export interface ErrorStats {
  n: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
  median_abs_error_mw: number;
  p90_abs_error_mw: number;
  p95_abs_error_mw: number;
  max_abs_error_mw: number;
  mean_actual_mw: number;
  mae_pct_of_mean_actual: number;
  mape_pct: number | null;
}

export interface GroupStats {
  label: string;
  n: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
}

export interface SafetyBuffer {
  confidence: number;
  shortfall_buffer_mw: number;
  surplus_margin_mw: number;
}

export interface AccuracyResponse {
  start_date: string;
  end_date: string;
  cutoff_time: string;
  days_before: number;
  resolution: string;
  mape_floor_mw: number;
  coverage: Coverage;
  warnings: string[];
  overall: ErrorStats | null;
  safety_buffer: SafetyBuffer | null;
  by_hour_of_day: GroupStats[];
  by_day: GroupStats[];
  by_horizon: GroupStats[];
}

/** What the user picks in the filter bar. */
export interface Filters {
  startDate: string;
  endDate: string;
  cutoffTime: string;
  compareCutoffTime: string;
  confidence: number;
}

/** Everything the dashboard needs for one set of filters. */
export interface AnalysisData {
  comparison: ComparisonResponse;
  accuracy: AccuracyResponse;
  /** Accuracy at the comparison cutoff; null when it equals the main cutoff. */
  compareAccuracy: AccuracyResponse | null;
}

/** One hour on the forecast chart. */
export interface ChartPoint {
  time: string;
  actual: number | null;
  forecast: number | null;
  error: number | null;
  publishTime: string | null;
  horizonHours: number | null;
}
