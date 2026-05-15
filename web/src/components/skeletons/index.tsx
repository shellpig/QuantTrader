import type { CSSProperties } from "react";
import { cn } from "@/lib/utils";

function Skeleton({
  className,
  style,
  testId,
}: {
  className?: string;
  style?: CSSProperties;
  testId?: string;
}) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      style={style}
      data-testid={testId}
    />
  );
}

export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("space-y-2 rounded-lg border p-3", className)}
      data-testid="card-skeleton"
    >
      <Skeleton className="h-3 w-16" />
      <Skeleton className="h-7 w-24" />
    </div>
  );
}

export function ChartSkeleton({
  height = 400,
  className,
}: {
  height?: number;
  className?: string;
}) {
  return (
    <Skeleton
      className={cn("w-full", className)}
      style={{ height }}
      testId="chart-skeleton"
    />
  );
}

export function TableSkeleton({
  rows = 5,
  columns = 4,
  className,
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)} data-testid="table-skeleton">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="grid gap-2"
          style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
          data-testid="table-skeleton-row"
        >
          {Array.from({ length: columns }).map((__, colIndex) => (
            <Skeleton key={colIndex} className="h-6" testId="table-skeleton-cell" />
          ))}
        </div>
      ))}
    </div>
  );
}
