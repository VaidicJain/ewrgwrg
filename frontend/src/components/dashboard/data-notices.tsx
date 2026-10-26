import { AlertTriangle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { formatNumber } from "@/lib/format";
import type { Coverage } from "@/lib/types";

interface DataNoticesProps {
  warnings: readonly string[];
  coverage: Coverage;
}

/** Surfaces missing-data warnings from the API so the buyer knows how complete the numbers are. */
export function DataNotices({ warnings, coverage }: DataNoticesProps) {
  if (warnings.length === 0) return null;

  return (
    <Alert variant="warning">
      <AlertTriangle aria-hidden />
      <div>
        <AlertTitle>Some data is missing for this period</AlertTitle>
        <AlertDescription>
          <ul className="list-disc space-y-0.5 pl-4">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
          <p className="mt-2">
            Metrics use the {formatNumber(coverage.compared)} hours that have both values.
          </p>
        </AlertDescription>
      </div>
    </Alert>
  );
}
