import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder with the same rough layout as the loaded dashboard, so nothing jumps when data arrives. */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading analysis">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-32 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-40 rounded-xl" />
      <Skeleton className="h-[560px] rounded-xl" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-[430px] rounded-xl" />
        <Skeleton className="h-[430px] rounded-xl" />
      </div>
    </div>
  );
}
