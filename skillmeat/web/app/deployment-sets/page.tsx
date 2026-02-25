import { Suspense } from 'react';
import { DeploymentSetsPageClient } from './deployment-sets-page-client';
import { Skeleton } from '@/components/ui/skeleton';

export const metadata = {
  title: 'Deployment Sets | SkillMeat',
  description: 'Manage named deployment sets for batch-deploying artifacts to projects',
};

/**
 * Deployment Sets Page - Server component wrapper
 *
 * Exports static metadata for SEO and delegates all interactivity (including
 * feature-flag gating) to the client component. This pattern is required by
 * Next.js App Router: `metadata` cannot be exported from a Client Component.
 */
export default function DeploymentSetsPage() {
  return (
    <Suspense fallback={<DeploymentSetsPageSkeleton />}>
      <DeploymentSetsPageClient />
    </Suspense>
  );
}

/**
 * Loading skeleton shown during hydration
 */
function DeploymentSetsPageSkeleton() {
  return (
    <div className="container mx-auto space-y-6 py-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-96" />
        </div>
      </div>
      <div className="space-y-6">
        <div className="flex items-center gap-4 rounded-lg border bg-card p-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-40" />
          <div className="ml-auto">
            <Skeleton className="h-10 w-36" />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-52 w-full rounded-lg" />
          ))}
        </div>
      </div>
    </div>
  );
}
