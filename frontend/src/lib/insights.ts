import { formatMw, formatNumber, formatPercent, formatShortDay, formatSignedMw } from "@/lib/format";
import type { AccuracyResponse, ComparisonResponse } from "@/lib/types";

export type InsightTone = "info" | "warning" | "positive";

export interface Insight {
  id: string;
  tone: InsightTone;
  text: string;
}

interface InsightInput {
  comparison: ComparisonResponse;
  accuracy: AccuracyResponse;
  compareAccuracy: AccuracyResponse | null;
}

/** Share of days where every scored hour was over-forecast, plus the number of scored days. */
function countAllHighDays(comparison: ComparisonResponse): { allHigh: number; days: number } {
  const byDay = new Map<string, boolean>();
  for (const row of comparison.rows) {
    if (row.error_mw === null) continue;
    const day = row.start_time.slice(0, 10);
    byDay.set(day, (byDay.get(day) ?? true) && row.error_mw > 0);
  }
  const flags = [...byDay.values()];
  return { allHigh: flags.filter(Boolean).length, days: flags.length };
}

/** Plain-English takeaways for a buyer, derived only from the numbers on screen. */
export function buildInsights({ comparison, accuracy, compareAccuracy }: InsightInput): Insight[] {
  const overall = accuracy.overall;
  if (!overall) return [];

  const insights: Insight[] = [];
  const scored = comparison.rows.filter((row) => row.error_mw !== null);

  if (scored.length > 0) {
    const overShare = (scored.filter((row) => (row.error_mw ?? 0) > 0).length / scored.length) * 100;
    const direction = overall.bias_mw >= 0 ? "higher" : "lower";
    insights.push({
      id: "direction",
      tone: Math.abs(overall.bias_mw) > overall.mae_mw * 0.5 ? "warning" : "info",
      text: `Forecasts were ${direction} than actual generation in ${formatPercent(
        overShare,
        0,
      )} of hours, on average by ${formatSignedMw(overall.bias_mw)}.`,
    });
  }

  insights.push({
    id: "typical-error",
    tone: "info",
    text: `The typical hour is off by ${formatMw(overall.median_abs_error_mw)}, but 1 hour in 10 is off by more than ${formatMw(
      overall.p90_abs_error_mw,
    )}.`,
  });

  if (accuracy.safety_buffer) {
    const { confidence, shortfall_buffer_mw } = accuracy.safety_buffer;
    insights.push({
      id: "buffer",
      tone: "warning",
      text: `To be covered against a wind shortfall in ${formatPercent(
        confidence * 100,
        0,
      )} of hours, hold about ${formatMw(shortfall_buffer_mw)} of additional supply beyond the forecast.`,
    });
  }

  const { allHigh, days } = countAllHighDays(comparison);
  if (days > 0 && allHigh / days >= 0.25) {
    insights.push({
      id: "clustering",
      tone: "warning",
      text: `On ${allHigh} of ${days} days the forecast was too high in every hour. Misses cluster, so plan for bad days rather than isolated bad hours.`,
    });
  }

  const worstDay = [...accuracy.by_day].sort((a, b) => b.mae_mw - a.mae_mw)[0];
  if (worstDay && accuracy.by_day.length > 1) {
    insights.push({
      id: "worst-day",
      tone: "info",
      text: `The largest misses were on ${formatShortDay(worstDay.label)}, with an average error of ${formatMw(worstDay.mae_mw)}.`,
    });
  }

  const compare = compareAccuracy?.overall;
  if (compare && compareAccuracy) {
    const maeDelta = overall.mae_mw - compare.mae_mw;
    const bufferDelta =
      accuracy.safety_buffer && compareAccuracy.safety_buffer
        ? accuracy.safety_buffer.shortfall_buffer_mw - compareAccuracy.safety_buffer.shortfall_buffer_mw
        : null;
    const pct = overall.mae_mw > 0 ? (Math.abs(maeDelta) / overall.mae_mw) * 100 : 0;
    const bufferText =
      bufferDelta === null
        ? ""
        : bufferDelta >= 0
          ? ` and the safety buffer by ${formatMw(bufferDelta)}`
          : ` but the safety buffer would grow by ${formatMw(-bufferDelta)}`;

    insights.push({
      id: "cutoff",
      tone: maeDelta > 0 ? "positive" : "info",
      text:
        maeDelta > 0
          ? `Deciding at ${compareAccuracy.cutoff_time} instead of ${accuracy.cutoff_time} would cut the average error by ${formatNumber(
              maeDelta,
            )} MW (${formatPercent(pct, 0)})${bufferText}.`
          : `Deciding at ${compareAccuracy.cutoff_time} instead of ${accuracy.cutoff_time} would not improve the average error (${formatSignedMw(
              -maeDelta,
            )}).`,
    });
  }

  return insights;
}
