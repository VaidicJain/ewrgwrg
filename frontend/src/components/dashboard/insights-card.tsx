import { AlertTriangle, Info, Lightbulb, TrendingUp, type LucideIcon } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { buildInsights, type InsightTone } from "@/lib/insights";
import type { AnalysisData } from "@/lib/types";
import { cn } from "@/lib/utils";

const TONE_ICON: Record<InsightTone, LucideIcon> = {
  info: Info,
  warning: AlertTriangle,
  positive: TrendingUp,
};

const TONE_COLOR: Record<InsightTone, string> = {
  info: "text-primary",
  warning: "text-warning",
  positive: "text-success",
};

/** Plain-English takeaways, generated from the numbers on screen. */
export function InsightsCard({ data }: { data: AnalysisData }) {
  const insights = buildInsights(data);
  if (insights.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="size-4 text-warning" aria-hidden />
          What this means for your buying decision
        </CardTitle>
        <CardDescription>Summary of the period selected above.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {insights.map((insight) => {
            const Icon = TONE_ICON[insight.tone];
            return (
              <li key={insight.id} className="flex gap-3 text-sm">
                <Icon className={cn("mt-0.5 size-4 shrink-0", TONE_COLOR[insight.tone])} aria-hidden />
                <span>{insight.text}</span>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
