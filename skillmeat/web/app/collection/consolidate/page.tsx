import { Suspense } from 'react';
import { Layers } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { ConsolidationClusterList } from '@/components/consolidation/consolidation-cluster-list';

export const metadata = {
  title: 'Consolidate Collection | SkillMeat',
  description: 'Review and merge duplicate or similar artifacts in your collection',
};

/**
 * Consolidate Collection Page
 *
 * Surfaces clusters of similar/duplicate artifacts so the user can review
 * and decide whether to merge, keep, or dismiss each cluster.
 *
 * Server component wrapper — interactivity is delegated to ConsolidationClusterList.
 */
export default function ConsolidateCollectionPage() {
  return (
    <div className="container mx-auto space-y-6 py-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-md bg-muted p-2">
            <Layers className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Consolidate Collection</h1>
            <p className="text-sm text-muted-foreground">
              Review similar and duplicate artifacts, then merge or dismiss each cluster.
            </p>
          </div>
        </div>
      </div>

      {/* Cluster list with Suspense boundary for loading state */}
      <Suspense fallback={<ConsolidationClusterListSkeleton />}>
        <ConsolidationClusterList />
      </Suspense>
    </div>
  );
}

/**
 * Loading skeleton shown while ConsolidationClusterList hydrates.
 */
function ConsolidationClusterListSkeleton() {
  return (
    <div className="space-y-4" aria-label="Loading consolidation clusters" role="status">
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center gap-3">
            <Skeleton className="h-5 w-5 rounded" />
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-5 w-16 ml-auto" />
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <Skeleton className="h-20 w-full rounded-md" />
            <Skeleton className="h-20 w-full rounded-md" />
            <Skeleton className="h-20 w-full rounded-md hidden lg:block" />
          </div>
        </div>
      ))}
      <span className="sr-only">Loading consolidation clusters...</span>
    </div>
  );
}
