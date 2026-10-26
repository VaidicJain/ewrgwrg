"use client";

import {
  Area,
  AreaChart,
  Brush,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ForecastTooltip } from "@/components/dashboard/forecast-tooltip";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toChartPoints } from "@/lib/chart-data";
import { CHART_COLORS } from "@/lib/config";
import { formatAxisTick, formatNumber, formatShortDay, spanInDays } from "@/lib/format";
import type { ComparisonResponse } from "@/lib/types";

const AXIS_TICK = { fill: "var(--muted-foreground)", fontSize: 12 } as const;
const AXIS_LINE = { stroke: "var(--border)" } as const;
const CHART_MARGIN = { top: 8, right: 16, bottom: 0, left: 0 } as const;

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
      <span className="h-0.5 w-5 rounded-full" style={{ backgroundColor: color }} aria-hidden />
      {label}
    </span>
  );
}

export function ForecastChartCard({ comparison }: { comparison: ComparisonResponse }) {
  const points = toChartPoints(comparison.rows);
  const spanDays = spanInDays(comparison.start_date, comparison.end_date);
  const tick = (value: string) => formatAxisTick(value, spanDays);
  const gigawatts = (value: number) => formatNumber(value / 1000, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Forecast vs actual generation</CardTitle>
        <CardDescription>
          Hourly GB wind output in GW. The forecast shown is the latest one published before the{" "}
          {comparison.cutoff_time} UTC cutoff on the day before delivery. Drag the handles below the chart
          to zoom.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          <LegendItem color={CHART_COLORS.actual} label="Actual generation" />
          <LegendItem color={CHART_COLORS.forecast} label="Forecast at decision time" />
        </div>

        <div className="h-[360px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={CHART_MARGIN}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="time"
                tick={AXIS_TICK}
                tickLine={false}
                axisLine={AXIS_LINE}
                tickFormatter={tick}
                minTickGap={56}
              />
              <YAxis
                tick={AXIS_TICK}
                tickLine={false}
                axisLine={false}
                width={36}
                tickFormatter={gigawatts}
                domain={["auto", "auto"]}
              />
              <Tooltip content={<ForecastTooltip />} />
              <Line
                dataKey="actual"
                name="Actual"
                stroke={CHART_COLORS.actual}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                dataKey="forecast"
                name="Forecast"
                stroke={CHART_COLORS.forecast}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              {points.length > 24 && (
                <Brush
                  dataKey="time"
                  height={28}
                  stroke="var(--muted-foreground)"
                  fill="var(--muted)"
                  travellerWidth={10}
                  tickFormatter={(value: string) => formatShortDay(value)}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div>
          <p className="mb-1 text-sm font-medium">Forecast error</p>
          <p className="mb-2 text-sm text-muted-foreground">
            Forecast minus actual, in GW. Above zero means the forecast was too high.
          </p>
          <div className="h-[140px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={points} margin={CHART_MARGIN}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="time" hide />
                <YAxis
                  tick={AXIS_TICK}
                  tickLine={false}
                  axisLine={false}
                  width={36}
                  tickFormatter={gigawatts}
                />
                <ReferenceLine y={0} stroke="var(--muted-foreground)" />
                <Tooltip content={<ForecastTooltip />} />
                <Area
                  dataKey="error"
                  name="Error"
                  type="monotone"
                  stroke={CHART_COLORS.error}
                  fill={CHART_COLORS.error}
                  fillOpacity={0.18}
                  strokeWidth={1.5}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
