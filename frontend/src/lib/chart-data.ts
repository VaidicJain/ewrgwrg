import type { ChartPoint, ComparisonRow } from "@/lib/types";

/** Reshape API rows into what the charts need. Missing values stay null so lines show gaps. */
export function toChartPoints(rows: readonly ComparisonRow[]): ChartPoint[] {
  return rows.map((row) => ({
    time: row.start_time,
    actual: row.actual_mw,
    forecast: row.forecast_mw,
    error: row.error_mw,
    publishTime: row.forecast_publish_time,
    horizonHours: row.horizon_hours,
  }));
}

/** Distinct delivery days (YYYY-MM-DD) present in the rows, in order. */
export function listDays(rows: readonly ComparisonRow[]): string[] {
  return [...new Set(rows.map((row) => row.start_time.slice(0, 10)))];
}
