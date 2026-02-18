import { Suspense } from 'react';
import { GroupsPageClient } from './components/groups-page-client';
import { Skeleton } from '@/components/ui/skeleton';

export const metadata = {
  title: 'Groups | SkillMeat',
  description: 'Manage and organize groups across your collections',
};

/**
 * Groups Page - Group management hub
 *
 * This page provides a dedicated view for managing groups, including:
 * - Creating and editing group metadata
 * - Searching and sorting groups as cards
 * - Navigating to collection view for group artifacts
 *
 * Server component wrapper with client component for interactivity.
 */
export default function GroupsPage() {
  return (
    <div className="container mx-auto space-y-6 py-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Groups</h1>
          <p className="text-muted-foreground">
            Create, organize, and manage groups within your collections
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
      {/* Toolbar skeleton */}
      <div className="flex items-center gap-4 rounded-lg border bg-card p-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-10 w-32" />
      </div>

      {/* Card grid skeleton */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="space-y-3">
            <Skeleton className="h-56 w-full rounded-lg" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ))}
      </div>
    </div>
  );
}
