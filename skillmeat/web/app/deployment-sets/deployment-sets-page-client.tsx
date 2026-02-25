'use client';

import { Suspense, useState, useMemo } from 'react';
import { DeploymentSetList } from '@/components/deployment-sets/deployment-set-list';
import { DeploymentSetDetailsModal } from '@/components/deployment-sets/deployment-set-details-modal';
import { Skeleton } from '@/components/ui/skeleton';
import { useFeatureFlags, useCollections } from '@/hooks';
import { Layers3, AlertCircle } from 'lucide-react';

/**
 * DeploymentSetsPageClient - Feature-flag-gated client component
 *
 * Handles the deployment_sets_enabled feature flag check. When the flag is OFF
 * (backend disabled), renders a clear disabled state instead of a broken page.
 * When ON, renders the full deployment sets UI with search, grid, and dialogs.
 */
export function DeploymentSetsPageClient() {
  const { deploymentSetsEnabled, isLoading: flagsLoading } = useFeatureFlags();
  const [selectedSetId, setSelectedSetId] = useState<string | null>(null);

  // Resolve the user's home collection to pass into the details modal for the Groups tab.
  // Priority: id/name matches "default"/"main" > highest artifact_count > first item.
  const { data: collectionsData } = useCollections();
  const defaultCollectionId = useMemo(() => {
    const items = collectionsData?.items ?? [];
    if (items.length === 0) return undefined;
    const HOME_NAMES = ['default', 'main', 'personal', 'home'];
    const byName = items.find(
      (c) => HOME_NAMES.includes(c.id.toLowerCase()) || HOME_NAMES.includes(c.name.toLowerCase()),
    );
    if (byName) return byName.id;
    const byCount = [...items].sort((a, b) => b.artifact_count - a.artifact_count)[0];
    return byCount?.id ?? items[0]?.id;
  }, [collectionsData]);

  // Show a skeleton while feature flags load to avoid layout shift
  if (flagsLoading) {
    return (
      <div className="container mx-auto space-y-6 py-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-96" />
          </div>
        </div>
        <DeploymentSetsContentSkeleton />
      </div>
    );
  }

  // Feature flag OFF: show a clear disabled message instead of a broken page
  if (!deploymentSetsEnabled) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed bg-muted/30 py-16 text-center">
          <div className="rounded-full bg-muted p-4">
            <Layers3 className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-semibold">Deployment Sets Unavailable</h2>
            <p className="max-w-sm text-sm text-muted-foreground">
              The Deployment Sets feature is currently disabled on this server. Contact your
              administrator or set{' '}
              <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                SKILLMEAT_DEPLOYMENT_SETS_ENABLED=true
              </code>{' '}
              to enable it.
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
            <AlertCircle className="h-3.5 w-3.5" />
            <span>Feature disabled by server configuration</span>
          </div>
        </div>
      </div>
    );
  }

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
      <Suspense fallback={<DeploymentSetsContentSkeleton />}>
        <DeploymentSetList onOpen={setSelectedSetId} />
      </Suspense>

      <DeploymentSetDetailsModal
        setId={selectedSetId}
        open={selectedSetId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedSetId(null);
        }}
        collectionId={defaultCollectionId}
      />
    </div>
  );
}

/**
 * Content skeleton for the deployment sets grid
 */
function DeploymentSetsContentSkeleton() {
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
          <Skeleton key={i} className="h-52 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}
