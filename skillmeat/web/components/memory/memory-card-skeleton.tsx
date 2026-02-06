/**
 * MemoryCardSkeleton Component
 *
 * Loading placeholder that mirrors the MemoryCard layout with pulsing
 * muted blocks. Designed to be rendered in a divide-y container (6 rows
 * recommended for initial load).
 *
 * Design spec reference: section 3.7 Loading / Skeleton
 */

import * as React from 'react';

/**
 * MemoryCardSkeleton -- single skeleton row matching MemoryCard dimensions.
 *
 * @example
 * ```tsx
 * <div className="divide-y">
 *   {Array.from({ length: 6 }).map((_, i) => (
 *     <MemoryCardSkeleton key={i} />
 *   ))}
 * </div>
 * ```
 */
export function MemoryCardSkeleton() {
  return (
    <div className="flex items-stretch gap-3 px-6 py-3 animate-pulse" aria-hidden="true">
      {/* Checkbox placeholder */}
      <div className="h-4 w-4 rounded bg-muted mt-1" />

      {/* Confidence bar placeholder */}
      <div className="w-[3px] self-stretch rounded-full bg-muted" />

      {/* Content area placeholder */}
      <div className="flex-1 space-y-2">
        {/* First row: badge + content line */}
        <div className="flex items-center gap-2">
          <div className="h-4 w-16 rounded bg-muted" />
          <div className="h-4 w-3/4 rounded bg-muted" />
        </div>

        {/* Second row: metadata segments */}
        <div className="flex gap-3">
          <div className="h-3 w-8 rounded bg-muted" />
          <div className="h-3 w-16 rounded bg-muted" />
          <div className="h-3 w-12 rounded bg-muted" />
        </div>
      </div>
    </div>
  );
}
