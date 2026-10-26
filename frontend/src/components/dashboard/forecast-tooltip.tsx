import { CHART_COLORS } from "@/lib/config";
import { formatDayTime, formatMw, formatSignedMw } from "@/lib/format";
import type { ChartPoint } from "@/lib/types";

interface ForecastTooltipProps {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: ChartPoint }>;
}

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between gap-6">
      <dt className="flex items-center gap-2 text-muted-foreground">
        {color && <span className="size-2 rounded-full" style={{ backgroundColor: color }} aria-hidden />}
        {label}
      </dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

/** Hover card for the forecast chart. Recharts injects active/payload when it renders this element. */
export function ForecastTooltip({ active, payload }: ForecastTooltipProps) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;

  return (
    <div className="min-w-56 rounded-lg border bg-card p-3 text-sm shadow-md">
      <p className="mb-2 font-medium">{formatDayTime(point.time)} UTC</p>
      <dl className="space-y-1">
        <Row
          color={CHART_COLORS.actual}
          label="Actual"
          value={point.actual === null ? "n/a" : formatMw(point.actual)}
        />
        <Row
          color={CHART_COLORS.forecast}
          label="Forecast"
          value={point.forecast === null ? "n/a" : formatMw(point.forecast)}
        />
        <Row label="Error" value={point.error === null ? "n/a" : formatSignedMw(point.error)} />
      </dl>
      {point.publishTime && (
        <p className="mt-2 border-t pt-2 text-xs text-muted-foreground">
          Forecast published {formatDayTime(point.publishTime)} UTC
          {point.horizonHours !== null && ` (${point.horizonHours.toFixed(1)} h ahead)`}
        </p>
      )}
    </div>
  );
}
