import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMw, formatPercent, formatSignedMw } from "@/lib/format";
import type { AccuracyResponse } from "@/lib/types";

interface CutoffComparisonCardProps {
  main: AccuracyResponse;
  /** Null when the comparison cutoff equals the main cutoff. */
  compare: AccuracyResponse | null;
}

interface MetricRow {
  label: string;
  main: string;
  compare: string;
  /** Negative means the comparison cutoff is better (smaller). Null when not comparable. */
  delta: number | null;
}

function buildRows(main: AccuracyResponse, compare: AccuracyResponse): MetricRow[] {
  const a = main.overall;
  const b = compare.overall;
  if (!a || !b) return [];

  const rows: MetricRow[] = [
    {
      label: "Average error (MAE)",
      main: formatMw(a.mae_mw),
      compare: formatMw(b.mae_mw),
      delta: b.mae_mw - a.mae_mw,
    },
    {
      label: "Error as % of generation",
      main: formatPercent(a.mae_pct_of_mean_actual),
      compare: formatPercent(b.mae_pct_of_mean_actual),
      delta: b.mae_pct_of_mean_actual - a.mae_pct_of_mean_actual,
    },
    {
      label: "Bias",
      main: formatSignedMw(a.bias_mw),
      compare: formatSignedMw(b.bias_mw),
      delta: Math.abs(b.bias_mw) - Math.abs(a.bias_mw),
    },
    {
      label: "95th percentile error",
      main: formatMw(a.p95_abs_error_mw),
      compare: formatMw(b.p95_abs_error_mw),
      delta: b.p95_abs_error_mw - a.p95_abs_error_mw,
    },
  ];

  if (main.safety_buffer && compare.safety_buffer) {
    rows.push({
      label: "Safety buffer",
      main: formatMw(main.safety_buffer.shortfall_buffer_mw),
      compare: formatMw(compare.safety_buffer.shortfall_buffer_mw),
      delta: compare.safety_buffer.shortfall_buffer_mw - main.safety_buffer.shortfall_buffer_mw,
    });
  }
  return rows;
}

function DeltaText({ delta }: { delta: number | null }) {
  if (delta === null || Math.abs(delta) < 0.05) return <span className="text-muted-foreground">same</span>;
  const better = delta < 0;
  return (
    <span className={better ? "font-medium text-success" : "font-medium text-destructive"}>
      {better ? "better" : "worse"}
    </span>
  );
}

/** How much a later (or earlier) decision cutoff would change forecast quality. */
export function CutoffComparisonCard({ main, compare }: CutoffComparisonCardProps) {
  const rows = compare ? buildRows(main, compare) : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Does deciding later help?</CardTitle>
        <CardDescription>
          Same period, two decision cutoffs on the day before delivery. Later cutoffs see newer forecasts.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!compare || rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Choose a different &ldquo;Compare with cutoff&rdquo; above to see how forecast quality changes when you
            decide earlier or later.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th scope="col" className="py-2 pr-4 font-medium">
                    Metric
                  </th>
                  <th scope="col" className="py-2 pr-4 text-right font-medium">
                    {main.cutoff_time} cutoff
                  </th>
                  <th scope="col" className="py-2 pr-4 text-right font-medium">
                    {compare.cutoff_time} cutoff
                  </th>
                  <th scope="col" className="py-2 text-right font-medium">
                    {compare.cutoff_time} is
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.label} className="border-b last:border-0">
                    <th scope="row" className="py-2.5 pr-4 text-left font-normal">
                      {row.label}
                    </th>
                    <td className="py-2.5 pr-4 text-right">{row.main}</td>
                    <td className="py-2.5 pr-4 text-right">{row.compare}</td>
                    <td className="py-2.5 text-right">
                      <DeltaText delta={row.delta} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
