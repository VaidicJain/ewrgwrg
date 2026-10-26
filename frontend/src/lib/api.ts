import { API_BASE_URL, API_PREFIX } from "@/lib/config";
import type { AccuracyResponse, AnalysisData, ComparisonResponse, Filters } from "@/lib/types";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type QueryParams = Record<string, string | number>;

/** FastAPI errors are either {detail: "text"} or {detail: [{msg: "..."}]}. */
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => (item as { msg?: string }).msg ?? "Invalid request").join("; ");
    }
  } catch {
    // Not JSON; fall through to the generic message.
  }
  return `The API responded with status ${response.status}.`;
}

async function getJson<T>(path: string, params: QueryParams, signal?: AbortSignal): Promise<T> {
  const url = new URL(`${API_BASE_URL}${API_PREFIX}${path}`);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, String(value));
  }

  let response: Response;
  try {
    response = await fetch(url, { signal, headers: { Accept: "application/json" }, cache: "no-store" });
  } catch (error) {
    if (signal?.aborted) throw error; // the caller cancelled; not a real failure
    throw new ApiError(`Cannot reach the API at ${API_BASE_URL}. Is the backend running?`);
  }

  if (!response.ok) throw new ApiError(await readErrorMessage(response));
  return (await response.json()) as T;
}

export function fetchComparison(filters: Filters, signal?: AbortSignal): Promise<ComparisonResponse> {
  return getJson<ComparisonResponse>(
    "/analysis/forecast-vs-actual",
    {
      start_date: filters.startDate,
      end_date: filters.endDate,
      cutoff_time: filters.cutoffTime,
    },
    signal,
  );
}

export function fetchAccuracy(
  filters: Filters,
  cutoffTime: string,
  signal?: AbortSignal,
): Promise<AccuracyResponse> {
  return getJson<AccuracyResponse>(
    "/analysis/accuracy",
    {
      start_date: filters.startDate,
      end_date: filters.endDate,
      cutoff_time: cutoffTime,
      confidence: filters.confidence,
    },
    signal,
  );
}

/** Loads everything one dashboard view needs, in parallel. */
export async function loadAnalysis(filters: Filters, signal?: AbortSignal): Promise<AnalysisData> {
  const needsComparison = filters.compareCutoffTime !== filters.cutoffTime;

  const [comparison, accuracy, compareAccuracy] = await Promise.all([
    fetchComparison(filters, signal),
    fetchAccuracy(filters, filters.cutoffTime, signal),
    needsComparison ? fetchAccuracy(filters, filters.compareCutoffTime, signal) : Promise.resolve(null),
  ]);

  return { comparison, accuracy, compareAccuracy };
}
