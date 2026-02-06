import { Skeleton } from '@/components/ui/skeleton';

export function MemoryPageSkeleton() {
  return (
    <div className="flex h-screen flex-col">
      {/* Header skeleton */}
      <div className="border-b px-6 pb-4 pt-6">
        {/* Breadcrumb */}
        <div className="mb-3 flex items-center gap-1.5">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-3.5 w-3.5" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-3.5 w-3.5" />
          <Skeleton className="h-4 w-16" />
        </div>
        {/* Title row */}
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-32" />
            <Skeleton className="mt-1 h-4 w-80" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-8 w-32" />
          </div>
        </div>
      </div>

      {/* Type tabs skeleton */}
      <div className="border-b px-6 py-2">
        <div className="flex items-center gap-1">
          {Array.from({ length: 7 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-24 rounded-md" />
          ))}
        </div>
      </div>

      {/* Filter bar skeleton */}
      <div className="flex items-center gap-3 border-b px-6 py-2">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-8 w-28" />
        <div className="flex-1" />
        <Skeleton className="h-8 w-64" />
      </div>

      {/* Content area skeleton */}
      <div className="flex flex-1 overflow-hidden">
        {/* List area */}
        <div className="flex-1 divide-y">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 px-6 py-3">
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-full w-[3px] self-stretch" />
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-5 w-20 rounded-md" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
                <div className="flex items-center gap-3">
                  <Skeleton className="h-3 w-8" />
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-3 w-14" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Loading() {
  return <MemoryPageSkeleton />;
}
