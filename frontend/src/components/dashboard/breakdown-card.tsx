"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { CHART_COLORS } from "@/lib/config";
import { formatMw, formatNumber, formatShortDay, formatSignedMw } from "@/lib/format";
import type { AccuracyResponse, GroupStats } from "@/lib/types";

type View = "hour" | "day" | "horizon";

const VIEWS = [
  { value: "hour", label: "Hour of day" },
  { value: "day", label: "Day" },
  { value: "horizon", label: "Forecast age" },
] as const;

const DESCRIPTIONS: Record<View, string> = {
  hour: "Which times of day the forecast struggles with most. Hours are UTC.",
  day: "Which delivery days were hardest to forecast.",
  horizon: "Error by how long before the target hour the forecast was published.",
};

const AXIS_TICK = { fill: "var(--muted-foreground)", fontSize: 12 } as const;

interface GroupTooltipProps {
  active?: boolean;
  label?: string | number;
  payload?: ReadonlyArray<{ payload?: GroupStats }>;
  view: View;
}

function GroupTooltip({ active, payload, view }: GroupTooltipProps) {
  const group = payload?.[0]?.payload;
  if (!active || !group) return null;

  const title = view === "day" ? formatShortDay(group.label) : group.label;
  return (
    <div className="min-w-52 rounded-lg border bg-card p-3 text-sm shadow-md">
      <p className="mb-2 font-medium">{title}</p>
      <dl className="space-y-1">
        <div className="flex justify-between gap-6">
          <dt className="text-muted-foreground">Average error</dt>
          <dd className="font-medium">{formatMw(group.mae_mw)}</dd>
        </div>
        <div className="flex justify-between gap-6">
          <dt className="text-muted-foreground">Bias</dt>
          <dd className="font-medium">{formatSignedMw(group.bias_mw)}</dd>
        </div>
        <div className="flex justify-between gap-6">
          <dt className="text-muted-foreground">Hours</dt>
          <dd className="font-medium">{formatNumber(group.n)}</dd>
        </div>
      </dl>
    </div>
  );
}

export function BreakdownCard({ accuracy }: { accuracy: AccuracyResponse }) {
  const [view, setView] = useState<View>("hour");

  const data: GroupStats[] =
    view === "hour" ? accuracy.by_hour_of_day : view === "day" ? accuracy.by_day : accuracy.by_horizon;
  const tick = (value: string) => (view === "day" ? formatShortDay(value) : view === "hour" ? value.slice(0, 2) : value);

  return (
    <Card>
      <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1.5">
          <CardTitle>Where the errors come from</CardTitle>
          <CardDescription>{DESCRIPTIONS[view]}</CardDescription>
        </div>
        <SegmentedControl value={view} options={VIEWS} onChange={setView} ariaLabel="Breakdown view" />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-2">
            <span className="size-2.5 rounded-sm" style={{ backgroundColor: CHART_COLORS.mae }} aria-hidden />
            Average error
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="size-2.5 rounded-sm" style={{ backgroundColor: CHART_COLORS.bias }} aria-hidden />
            Bias (positive = forecast too high)
          </span>
        </div>
        <div className="h-[300px] w-full">
          {data.length === 0 ? (
            <p className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Not enough data for this view.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={AXIS_TICK}
                  tickLine={false}
                  axisLine={{ stroke: "var(--border)" }}
                  tickFormatter={tick}
                  minTickGap={view === "day" ? 24 : 4}
                />
                <YAxis
                  tick={AXIS_TICK}
                  tickLine={false}
                  axisLine={false}
                  width={36}
                  tickFormatter={(value: number) => formatNumber(value / 1000, 0)}
                />
                <ReferenceLine y={0} stroke="var(--muted-foreground)" />
                <Tooltip
                  cursor={{ fill: "var(--muted)", opacity: 0.5 }}
                  content={<GroupTooltip view={view} />}
                />
                <Bar dataKey="mae_mw" name="Average error" fill={CHART_COLORS.mae} radius={[3, 3, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="bias_mw" name="Bias" fill={CHART_COLORS.bias} radius={[3, 3, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
        <p className="text-xs text-muted-foreground">Vertical axis in GW.</p>
      </CardContent>
    </Card>
  );
}
