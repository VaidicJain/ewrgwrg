import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMw } from "@/lib/format";

interface MethodologyCardProps {
  cutoffTime: string;
  mapeFloorMw: number;
}

/** Short, honest explanation of how every number on the page was produced. */
export function MethodologyCard({ cutoffTime, mapeFloorMw }: MethodologyCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>How these numbers are calculated</CardTitle>
        <CardDescription>So you can check and trust them.</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-x-8 gap-y-4 text-sm md:grid-cols-2">
          <div>
            <dt className="font-medium">Which forecast is used</dt>
            <dd className="mt-1 text-muted-foreground">
              For each delivery hour, the most recent forecast published at or before {cutoffTime} UTC on the day
              before delivery. Later forecasts are ignored because you could not have used them when buying.
            </dd>
          </div>
          <div>
            <dt className="font-medium">Hourly values</dt>
            <dd className="mt-1 text-muted-foreground">
              Actuals and forecasts are half-hourly. Each hour is the average of its two half-hours; hours with a
              missing half-hour are skipped.
            </dd>
          </div>
          <div>
            <dt className="font-medium">Error and bias</dt>
            <dd className="mt-1 text-muted-foreground">
              Error = forecast minus actual. Positive means too much wind was expected, so you would under-buy.
              Average error (MAE) ignores the sign; bias keeps it.
            </dd>
          </div>
          <div>
            <dt className="font-medium">Safety buffer</dt>
            <dd className="mt-1 text-muted-foreground">
              The chosen percentile of the over-forecast error: the extra supply that would have covered a wind
              shortfall in that share of hours. It describes past performance, not a guarantee.
            </dd>
          </div>
          <div>
            <dt className="font-medium">Percentage error</dt>
            <dd className="mt-1 text-muted-foreground">
              Hours with actual generation below {formatMw(mapeFloorMw)} are left out of percentage error, because
              dividing by a near-zero number exaggerates it.
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
