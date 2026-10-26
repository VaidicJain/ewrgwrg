"use client";

import { useEffect, useState } from "react";

import { loadAnalysis } from "@/lib/api";
import type { AnalysisData, Filters } from "@/lib/types";

interface State {
  /** Which request produced this state. Differs from the current key while a new one is loading. */
  key: string;
  data: AnalysisData | null;
  error: string | null;
}

interface UseAnalysisResult {
  data: AnalysisData | null;
  error: string | null;
  isLoading: boolean;
}

/**
 * Loads dashboard data whenever the filters (or the reload token) change.
 * The previous result stays available while the next one loads, so the page never flashes empty.
 */
export function useAnalysis(filters: Filters, reloadToken: number): UseAnalysisResult {
  const { startDate, endDate, cutoffTime, compareCutoffTime, confidence } = filters;
  const key = [startDate, endDate, cutoffTime, compareCutoffTime, confidence, reloadToken].join("|");

  const [state, setState] = useState<State>({ key: "", data: null, error: null });

  useEffect(() => {
    const controller = new AbortController();
    const requested: Filters = { startDate, endDate, cutoffTime, compareCutoffTime, confidence };

    loadAnalysis(requested, controller.signal)
      .then((data) => setState({ key, data, error: null }))
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return; // superseded by a newer request
        const message = caught instanceof Error ? caught.message : "Something went wrong.";
        setState((previous) => ({ key, data: previous.data, error: message }));
      });

    return () => controller.abort();
  }, [key, startDate, endDate, cutoffTime, compareCutoffTime, confidence]);

  const isCurrent = state.key === key;
  return { data: state.data, error: isCurrent ? state.error : null, isLoading: !isCurrent };
}
