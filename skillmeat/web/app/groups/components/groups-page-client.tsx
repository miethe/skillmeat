'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { useState, useCallback, useEffect, useMemo } from 'react';
import { FolderSearch, Library } from 'lucide-react';
import { useCollectionContext, useGroups } from '@/hooks';
import { CollectionSwitcher } from '@/components/collection/collection-switcher';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Skeleton } from '@/components/ui/skeleton';
import { CopyGroupDialog } from '@/components/collection/copy-group-dialog';
import { GroupCard } from './group-card';
import { GroupDeleteDialog } from './group-delete-dialog';
import { GroupDetailsModal } from './group-details-modal';
import { GroupFormDialog } from './group-form-dialog';
import { GroupsToolbar, type GroupSortField } from './groups-toolbar';
import type { Group } from '@/types/groups';

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

  const collectionId = searchParams.get('collection');

  // Access collection context for collection-aware operations
  const { selectedCollectionId, collections, isLoadingCollections } = useCollectionContext();

  // Derive collection ID to use (URL param takes precedence, then context)
  const effectiveCollectionId = collectionId || selectedCollectionId;
  const hasCollections = collections.length > 0;
  const { data: groupsData, isLoading: isLoadingGroups } = useGroups(effectiveCollectionId || undefined);
  const groups = groupsData?.groups ?? [];

  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<GroupSortField>('position');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);
  const [deletingGroup, setDeletingGroup] = useState<Group | null>(null);
  const [copyingGroup, setCopyingGroup] = useState<Group | null>(null);
  const [detailsGroup, setDetailsGroup] = useState<Group | null>(null);

  // Sync URL with collection context changes
  useEffect(() => {
    if (selectedCollectionId && selectedCollectionId !== collectionId) {
      const params = new URLSearchParams(searchParams.toString());
      params.set('collection', selectedCollectionId);
      router.push(`/groups?${params.toString()}`);
    }
  }, [selectedCollectionId, collectionId, searchParams, router]);

  const availableTags = useMemo(() => {
    const tags = new Set<string>();
    for (const group of groups) {
      for (const tag of group.tags ?? []) {
        tags.add(tag);
      }
    }
    return Array.from(tags).sort();
  }, [groups]);

  const filteredGroups = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    const filtered = groups.filter((group) => {
      if (selectedTag && !(group.tags ?? []).includes(selectedTag)) {
        return false;
      }

      if (!normalizedSearch) {
        return true;
      }

      const haystack = [
        group.name,
        group.description ?? '',
        ...(group.tags ?? []),
      ]
        .join(' ')
        .toLowerCase();

      return haystack.includes(normalizedSearch);
    });

    return filtered.sort((a, b) => {
      if (sort === 'name') {
        return a.name.localeCompare(b.name);
      }
      if (sort === 'updated_at') {
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      }
      if (sort === 'artifact_count') {
        return b.artifact_count - a.artifact_count;
      }
      return a.position - b.position;
    });
  }, [groups, search, selectedTag, sort]);

  return (
    <div className="space-y-6">
      {/* Collection Selector */}
      <div
        className="flex flex-wrap items-center gap-4 rounded-lg border bg-card p-4"
        role="region"
        aria-label="Collection selector"
      >
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
      </div>

      {effectiveCollectionId && (
        <GroupsToolbar
          search={search}
          onSearchChange={setSearch}
          sort={sort}
          onSortChange={setSort}
          selectedTag={selectedTag}
          onSelectedTagChange={setSelectedTag}
          availableTags={availableTags}
          onCreate={() => setCreateOpen(true)}
          disabled={isLoadingGroups}
        />
      )}

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
      ) : (
        <div className="space-y-4">
          {isLoadingGroups ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Skeleton key={i} className="h-48 w-full rounded-lg" />
              ))}
            </div>
          ) : filteredGroups.length === 0 ? (
            <EmptyState
              icon={FolderSearch}
              title={groups.length === 0 ? 'No groups yet' : 'No matching groups'}
              description={
                groups.length === 0
                  ? 'Create your first group to organize artifacts in this collection.'
                  : 'Try adjusting search or tag filters.'
              }
              action={
                <Button onClick={() => setCreateOpen(true)} disabled={!effectiveCollectionId}>
                  New Group
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filteredGroups.map((group) => (
                <GroupCard
                  key={group.id}
                  group={group}
                  onOpenDetails={setDetailsGroup}
                  onEdit={setEditingGroup}
                  onDelete={setDeletingGroup}
                  onCopy={setCopyingGroup}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {effectiveCollectionId && (
        <GroupFormDialog
          open={createOpen}
          onOpenChange={setCreateOpen}
          collectionId={effectiveCollectionId}
          defaultPosition={groups.length}
        />
      )}

      {effectiveCollectionId && (
        <GroupFormDialog
          open={!!editingGroup}
          onOpenChange={(open) => !open && setEditingGroup(null)}
          collectionId={effectiveCollectionId}
          group={editingGroup}
        />
      )}

      <GroupDeleteDialog
        open={!!deletingGroup}
        onOpenChange={(open) => !open && setDeletingGroup(null)}
        group={deletingGroup}
      />

      {copyingGroup && (
        <CopyGroupDialog
          open={!!copyingGroup}
          onOpenChange={(open) => !open && setCopyingGroup(null)}
          group={copyingGroup}
          sourceCollectionId={copyingGroup.collection_id}
          onSuccess={() => setCopyingGroup(null)}
        />
      )}

      <GroupDetailsModal
        open={!!detailsGroup}
        onOpenChange={(open) => !open && setDetailsGroup(null)}
        group={detailsGroup}
      />
    </div>
  );
}
