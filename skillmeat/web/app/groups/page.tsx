import { Suspense } from 'react';
import { GroupsPageClient } from './components/groups-page-client';
import { Skeleton } from '@/components/ui/skeleton';

export const metadata = {
  title: 'Groups | SkillMeat',
  description: 'Browse and manage artifact groups across your collections',
};

/**
 * Groups Page - Browse artifacts organized by groups
 *
 * This page provides a dedicated view for browsing artifacts by group,
 * complementing the collection-based view. Users can:
 * - Select a group from any collection
 * - View all artifacts within that group
 * - Navigate between groups quickly
 *
 * Server component wrapper with client component for interactivity.
 */
export default function GroupsPage() {
  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Groups</h1>
          <p className="text-muted-foreground">
            Browse artifacts by group within your collections
          </p>
        </div>
      </div>
      <Suspense fallback={<GroupsPageSkeleton />}>
        <GroupsPageClient />
      </Suspense>
    </div>
  );
}

/**
 * Loading skeleton for the groups page
 * Shows placeholder content while client component hydrates
 */
function GroupsPageSkeleton() {
  return (
    <div className="space-y-6">
      {/* Group selector skeleton */}
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-10 w-64" />
      </div>

      {/* Artifact grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="space-y-3">
            <Skeleton className="h-48 w-full rounded-lg" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ))}
      </div>
    </div>
  );
}
