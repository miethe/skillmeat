'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { useState, useCallback, useEffect } from 'react';
import { Layers, FolderOpen, X, FolderSearch, Library, Settings } from 'lucide-react';
import { useCollectionContext, useGroup } from '@/hooks';
import { GroupArtifactGrid } from './group-artifact-grid';
import { GroupSelector } from './group-selector';
import { CollectionSwitcher } from '@/components/collection/collection-switcher';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { ManageGroupsDialog } from '@/components/collection/manage-groups-dialog';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * Groups Page Client Component
 *
 * Handles all client-side interactivity for the groups page:
 * - URL state management for selected group
 * - Collection context integration
 * - Data fetching via TanStack Query hooks
 * - Renders GroupArtifactGrid when a group is selected
 *
 * URL params:
 * - ?group={groupId} - Selected group ID
 * - ?collection={collectionId} - Selected collection ID
 */
/**
 * Empty state component with icon, title, description, and optional action
 */
function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean }>;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-muted-foreground/25 py-12 text-center">
      <Icon className="h-12 w-12 text-muted-foreground/50" aria-hidden />
      <h3 className="mt-4 text-lg font-medium">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function GroupsPageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Get selected group from URL params
  const groupId = searchParams.get('group');
  const collectionId = searchParams.get('collection');

  // Fetch group details when a group is selected
  const { data: selectedGroup } = useGroup(groupId ?? undefined);

  // Access collection context for collection-aware operations
  const { selectedCollectionId, collections, isLoadingCollections } = useCollectionContext();

  // Handler to update URL when group selection changes
  // The collection ID is maintained by the CollectionSwitcher via context
  const handleGroupSelect = useCallback(
    (newGroupId: string | null) => {
      const params = new URLSearchParams(searchParams.toString());

      if (newGroupId) {
        params.set('group', newGroupId);
      } else {
        params.delete('group');
      }

      // Ensure collection is in URL if we have one selected
      if (selectedCollectionId) {
        params.set('collection', selectedCollectionId);
      }

      router.push(`/groups?${params.toString()}`);
    },
    [searchParams, router, selectedCollectionId]
  );

  // Handler to clear selection
  const handleClearSelection = useCallback(() => {
    router.push('/groups');
  }, [router]);

  // Derive collection ID to use (URL param takes precedence, then context)
  const effectiveCollectionId = collectionId || selectedCollectionId;
  const hasCollections = collections.length > 0;

  const [manageGroupsOpen, setManageGroupsOpen] = useState(false);

  // Sync URL with collection context changes
  // When collection changes via CollectionSwitcher, update URL and clear group
  useEffect(() => {
    if (selectedCollectionId && selectedCollectionId !== collectionId) {
      const params = new URLSearchParams(searchParams.toString());
      params.set('collection', selectedCollectionId);
      // Clear group when collection changes
      params.delete('group');
      router.push(`/groups?${params.toString()}`);
    }
  }, [selectedCollectionId, collectionId, searchParams, router]);

  return (
    <div className="space-y-6">
      {/* Collection and Group Selector Toolbar */}
      <div
        className="flex flex-wrap items-center gap-4 rounded-lg border bg-card p-4"
        role="region"
        aria-label="Group selector"
      >
        {/* Collection Selector */}
        <div className="flex items-center gap-2">
          <Library className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <span className="text-sm font-medium text-muted-foreground">Collection:</span>
          {isLoadingCollections ? (
            <Skeleton className="h-9 w-48" />
          ) : hasCollections ? (
            <CollectionSwitcher className="w-48" />
          ) : (
            <span className="text-sm text-muted-foreground">No collections available</span>
          )}
        </div>

        {/* Group Selector - only show when collection is selected */}
        {effectiveCollectionId && (
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            <span className="text-sm font-medium text-muted-foreground">Group:</span>
            <GroupSelector
              collectionId={effectiveCollectionId}
              selectedGroupId={groupId}
              onGroupSelect={handleGroupSelect}
            />
          </div>
        )}

        {/* Manage Groups Link */}
        {effectiveCollectionId && (
          <div className="ml-auto">
            <Button variant="ghost" size="sm" onClick={() => setManageGroupsOpen(true)}>
              <Settings className="mr-1 h-4 w-4" aria-hidden="true" />
              Manage Groups
            </Button>
          </div>
        )}
      </div>

      {/* Content Area - conditional rendering based on state */}
      {!hasCollections && !isLoadingCollections ? (
        // No collections exist
        <EmptyState
          icon={Library}
          title="No collections yet"
          description="Create a collection first to organize your artifacts into groups."
          action={
            <Button asChild>
              <Link href="/collection">Go to Collections</Link>
            </Button>
          }
        />
      ) : !effectiveCollectionId ? (
        // No collection selected
        <EmptyState
          icon={FolderSearch}
          title="Select a collection"
          description="Choose a collection from the dropdown above to browse its groups."
        />
      ) : groupId && collectionId ? (
        // Group is selected - show artifacts
        <div className="space-y-4">
          {/* Group header with name and clear button */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-primary" aria-hidden="true" />
              <span className="font-medium">
                {selectedGroup?.name ?? (
                  <code className="rounded bg-muted px-2 py-1 text-sm">{groupId}</code>
                )}
              </span>
              {selectedGroup?.description && (
                <span className="hidden text-sm text-muted-foreground md:inline">
                  - {selectedGroup.description}
                </span>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearSelection}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Clear group selection"
            >
              <X className="mr-1 h-4 w-4" aria-hidden="true" />
              Clear
            </Button>
          </div>

          {/* Artifact grid */}
          <GroupArtifactGrid groupId={groupId} collectionId={collectionId} />
        </div>
      ) : groupId && !collectionId ? (
        // Group selected but no collection - error state
        <EmptyState
          icon={Layers}
          title="Collection not specified"
          description="Please select a collection along with the group to view its artifacts."
          action={
            <Button variant="outline" onClick={handleClearSelection}>
              Start over
            </Button>
          }
        />
      ) : (
        // Collection selected but no group
        <EmptyState
          icon={Layers}
          title="Select a group"
          description="Use the group dropdown above to browse artifacts organized by group within this collection."
          action={
            <Button variant="outline" asChild>
              <Link href={`/collection?collection=${effectiveCollectionId}`}>Go to Collection</Link>
            </Button>
          }
        />
      )}

      {effectiveCollectionId && (
        <ManageGroupsDialog
          open={manageGroupsOpen}
          onOpenChange={setManageGroupsOpen}
          collectionId={effectiveCollectionId}
        />
      )}
    </div>
  );
}
