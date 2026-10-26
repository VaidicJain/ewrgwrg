"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { useState } from "react";

import { AppHeader } from "@/components/dashboard/app-header";
import { BreakdownCard } from "@/components/dashboard/breakdown-card";
import { CutoffComparisonCard } from "@/components/dashboard/cutoff-comparison-card";
import { DashboardSkeleton } from "@/components/dashboard/dashboard-skeleton";
import { DataNotices } from "@/components/dashboard/data-notices";
import { FiltersBar } from "@/components/dashboard/filters-bar";
import { ForecastChartCard } from "@/components/dashboard/forecast-chart-card";
import { InsightsCard } from "@/components/dashboard/insights-card";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { MethodologyCard } from "@/components/dashboard/methodology-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useAnalysis } from "@/hooks/use-analysis";
import { DEFAULT_FILTERS } from "@/lib/config";
import type { Filters } from "@/lib/types";

export function Dashboard() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [reloadToken, setReloadToken] = useState(0);
  const { data, error, isLoading } = useAnalysis(filters, reloadToken);

  const retry = () => setReloadToken((token) => token + 1);

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <AppHeader />

      <main className="mx-auto w-full max-w-7xl flex-1 space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        <FiltersBar initial={filters} isLoading={isLoading} onApply={setFilters} />

        {error && (
          <Alert variant="destructive">
            <AlertTriangle aria-hidden />
            <div className="flex-1">
              <AlertTitle>Could not load the analysis</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </div>
            <Button variant="outline" size="sm" onClick={retry}>
              <RefreshCw />
              Retry
            </Button>
          </Alert>
        )}

        {!data && !error && <DashboardSkeleton />}

        {data && (
          <div
            className={isLoading ? "space-y-6 opacity-60 transition-opacity" : "space-y-6 transition-opacity"}
            aria-busy={isLoading}
          >
            <DataNotices warnings={data.accuracy.warnings} coverage={data.accuracy.coverage} />

            {data.accuracy.overall ? (
              <>
                <KpiCards accuracy={data.accuracy} />
                <InsightsCard data={data} />
                <ForecastChartCard comparison={data.comparison} />
                <div className="grid gap-6 lg:grid-cols-2">
                  <BreakdownCard accuracy={data.accuracy} />
                  <CutoffComparisonCard main={data.accuracy} compare={data.compareAccuracy} />
                </div>
              </>
            ) : (
              <Alert variant="warning">
                <AlertTriangle aria-hidden />
                <div>
                  <AlertTitle>Nothing to score for this period</AlertTitle>
                  <AlertDescription>
                    No hours have both a forecast published before the cutoff and a complete actual. Try a
                    different period or cutoff.
                  </AlertDescription>
                </div>
              </Alert>
            )}

            <MethodologyCard cutoffTime={data.accuracy.cutoff_time} mapeFloorMw={data.accuracy.mape_floor_mw} />
          </div>
        )}
      </main>

      <footer className="border-t py-4 text-center text-xs text-muted-foreground">
        Data: Elexon BMRS (FUELHH actuals, WINDFOR forecasts), GB national wind. All times UTC.
      </footer>
    </div>
  );
}
