import { Gauge, Scale, ShieldCheck, Target, type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatMw, formatNumber, formatPercent, formatSignedMw } from "@/lib/format";
import type { AccuracyResponse } from "@/lib/types";

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  hint: string;
}

function StatCard({ icon: Icon, label, value, hint }: StatCardProps) {
  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <div className="flex size-8 items-center justify-center rounded-md bg-accent text-accent-foreground">
            <Icon className="size-4" aria-hidden />
          </div>
        </div>
        <p className="text-3xl font-semibold tracking-tight">{value}</p>
        <p className="text-sm text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}

export function KpiCards({ accuracy }: { accuracy: AccuracyResponse }) {
  const { overall, safety_buffer: buffer, coverage } = accuracy;
  if (!overall) return null;

  const biasHint =
    overall.bias_mw > 0
      ? "Forecasts run higher than actual generation"
      : overall.bias_mw < 0
        ? "Forecasts run lower than actual generation"
        : "No systematic over- or under-forecasting";

  return (
    <section aria-label="Forecast accuracy summary" className="space-y-2">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={Target}
          label="Average error (MAE)"
          value={formatMw(overall.mae_mw)}
          hint={`${formatPercent(overall.mae_pct_of_mean_actual)} of average generation`}
        />
        <StatCard
          icon={Scale}
          label="Forecast bias"
          value={formatSignedMw(overall.bias_mw)}
          hint={biasHint}
        />
        <StatCard
          icon={Gauge}
          label="95th percentile error"
          value={formatMw(overall.p95_abs_error_mw)}
          hint="95% of hours were within this error"
        />
        <StatCard
          icon={ShieldCheck}
          label={`Safety buffer (${buffer ? formatNumber(buffer.confidence * 100) : "-"}%)`}
          value={buffer ? formatMw(buffer.shortfall_buffer_mw) : "n/a"}
          hint="Extra supply to cover a wind shortfall"
        />
      </div>
      <p className="px-1 text-xs text-muted-foreground">
        Based on {formatNumber(coverage.compared)} of {formatNumber(coverage.total_hours)} hours that have both
        a forecast and an actual. Error = forecast minus actual.
      </p>
    </section>
  );
}
