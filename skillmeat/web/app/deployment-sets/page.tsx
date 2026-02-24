import { Suspense } from 'react';
import { DeploymentSetList } from '@/components/deployment-sets/deployment-set-list';
import { Skeleton } from '@/components/ui/skeleton';

export const metadata = {
  title: 'Deployment Sets | SkillMeat',
  description: 'Manage named deployment sets for batch-deploying artifacts to projects',
};

/**
 * Deployment Sets Page - Batch deployment management hub
 *
 * Provides a dedicated view for managing deployment sets, including:
 * - Creating, editing, cloning, and deleting deployment sets
 * - Searching and filtering sets by name or tag
 * - Navigating to individual set detail pages
 *
 * Server component wrapper with client component for interactivity.
 */
export default function DeploymentSetsPage() {
  return (
    <div className="container mx-auto space-y-6 py-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Deployment Sets</h1>
          <p className="text-muted-foreground">
            Create and manage named sets of artifacts for one-click batch deployment
          </p>
        </div>
      </div>
      <Suspense fallback={<DeploymentSetsPageSkeleton />}>
        <DeploymentSetList />
      </Suspense>
    </div>
  );
}

/**
 * Loading skeleton shown while the client component hydrates
 */
function DeploymentSetsPageSkeleton() {
  return (
    <div className="space-y-6">
      {/* Toolbar skeleton */}
      <div className="flex items-center gap-4 rounded-lg border bg-card p-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-40" />
        <div className="ml-auto">
          <Skeleton className="h-10 w-36" />
        </div>
      </div>

      {/* Card grid skeleton */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="space-y-3">
            <Skeleton className="h-52 w-full rounded-lg" />
          </div>
        ))}
      </div>
    </div>
  );
}
