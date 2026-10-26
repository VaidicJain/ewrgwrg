import type { Filters } from "@/lib/types";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");
export const API_PREFIX = "/api/v1";

/** The assignment covers purchase decisions for January 2026. */
export const DATA_START = "2026-01-01";
export const DATA_END = "2026-01-31";

export const CUTOFF_OPTIONS: readonly string[] = Array.from(
  { length: 9 },
  (_, i) => `${String(i + 6).padStart(2, "0")}:00`,
);

export const CONFIDENCE_OPTIONS = [
  { value: 0.9, label: "90%" },
  { value: 0.95, label: "95%" },
  { value: 0.99, label: "99%" },
] as const;

export const DATE_PRESETS = [
  { id: "month", label: "January", startDate: DATA_START, endDate: DATA_END },
  { id: "week1", label: "Week 1", startDate: "2026-01-01", endDate: "2026-01-07" },
  { id: "week2", label: "Week 2", startDate: "2026-01-08", endDate: "2026-01-14" },
  { id: "week3", label: "Week 3", startDate: "2026-01-15", endDate: "2026-01-21" },
  { id: "week4", label: "Week 4", startDate: "2026-01-22", endDate: "2026-01-28" },
] as const;

export const DEFAULT_FILTERS: Filters = {
  startDate: DATA_START,
  endDate: DATA_END,
  cutoffTime: "09:00",
  compareCutoffTime: "12:00",
  confidence: 0.95,
};

/** Chart colours chosen to stay readable in light and dark mode and for colour-blind viewers. */
export const CHART_COLORS = {
  actual: "#2563eb",
  forecast: "#ea580c",
  error: "#d97706",
  mae: "#6366f1",
  bias: "#f59e0b",
} as const;
