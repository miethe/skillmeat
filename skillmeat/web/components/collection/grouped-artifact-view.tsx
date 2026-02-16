/**
 * GroupedArtifactView Component
 *
 * Two-pane layout for browsing artifacts organized by groups.
 * - Left pane: GroupSidebar (fixed 280px, hidden below md)
 * - Right pane: Artifact list for the selected group/view
 *
 * Features:
 * - Drag-and-drop artifacts onto sidebar groups to add
 * - Drag-and-drop reordering within a group
 * - Remove-from-group drop zone when viewing a specific group
 * - Responsive: collapses to dropdown + full-width list below md
 */

'use client';

import * as React from 'react';
import { useState, useMemo, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  UniqueIdentifier,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { Package } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import type { Artifact } from '@/types/artifact';
import type { Group } from '@/types/groups';
import {
  useGroups,
  useGroupArtifacts,
  useAddArtifactToGroup,
  useRemoveArtifactFromGroup,
  useReorderArtifactsInGroup,
  useCreateGroup,
} from '@/hooks';
import { GroupSidebar, type PaneSelection } from './group-sidebar';
import { MiniArtifactCard, DraggableMiniArtifactCard } from './mini-artifact-card';
import { RemoveFromGroupDropZone } from './remove-from-group-zone';

// ---------------------------------------------------------------------------
// Props interface (preserved for parent compatibility)
// ---------------------------------------------------------------------------

export interface GroupedArtifactViewProps {
  /** Collection ID to fetch groups for */
  collectionId: string;
  /** All artifacts to display */
  artifacts: Artifact[];
  /** Click handler for artifacts */
  onArtifactClick?: (artifact: Artifact) => void;
  /** Move to collection handler */
  onMoveToCollection?: (artifact: Artifact) => void;
  /** Manage groups handler */
  onManageGroups?: (artifact: Artifact) => void;
  /** Edit artifact handler */
  onEdit?: (artifact: Artifact) => void;
  /** Delete artifact handler */
  onDelete?: (artifact: Artifact) => void;
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function GroupedViewSkeleton() {
  return (
    <div className="flex h-full gap-0" data-testid="grouped-view-skeleton">
      {/* Sidebar skeleton */}
      <div className="hidden w-[280px] shrink-0 border-r p-3 md:block">
        <Skeleton className="mb-2 h-9 w-full rounded-md" />
        <Skeleton className="mb-2 h-9 w-full rounded-md" />
        <div className="my-3 h-px bg-border" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="mb-2 h-9 w-full rounded-md" />
        ))}
      </div>
      {/* Content skeleton */}
      <div className="flex-1 space-y-2 p-4">
        <Skeleton className="h-8 w-48 rounded-md" />
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-12 w-full rounded-md" />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PaneHeader
// ---------------------------------------------------------------------------

interface PaneHeaderProps {
  title: string;
  count: number;
}

function PaneHeader({ title, count }: PaneHeaderProps) {
  return (
    <div className="flex items-center gap-2 pb-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      <span className="text-sm text-muted-foreground">
        ({count} {count === 1 ? 'artifact' : 'artifacts'})
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// EmptyState
// ---------------------------------------------------------------------------

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Package className="mb-3 h-10 w-10 text-muted-foreground/50" aria-hidden="true" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function GroupedArtifactView({
  collectionId,
  artifacts,
  onArtifactClick,
}: GroupedArtifactViewProps) {
  // ── State ──────────────────────────────────────────────────────────────
  const [selectedPane, setSelectedPane] = useState<PaneSelection>('all');
  const [activeId, setActiveId] = useState<UniqueIdentifier | null>(null);

  // ── Queries ────────────────────────────────────────────────────────────
  const { data: groupsData, isLoading: isLoadingGroups } = useGroups(collectionId);
  const groups = groupsData?.groups ?? [];

  // Fetch artifacts for each group (hooks called in stable order based on groups array)
  const groupArtifactQueries = groups.map((group) => ({
    group,
    // eslint-disable-next-line react-hooks/rules-of-hooks
    query: useGroupArtifacts(group.id),
  }));

  // ── Mutations ──────────────────────────────────────────────────────────
  const addArtifactToGroup = useAddArtifactToGroup();
  const removeArtifactFromGroup = useRemoveArtifactFromGroup();
  const reorderArtifactsInGroup = useReorderArtifactsInGroup();
  const createGroup = useCreateGroup();

  // ── Derived data ───────────────────────────────────────────────────────

  // Map artifact ID -> set of group IDs it belongs to
  const artifactGroupMembership = useMemo(() => {
    const map = new Map<string, Set<string>>();
    groupArtifactQueries.forEach(({ group, query }) => {
      if (query.data) {
        query.data.forEach((ga) => {
          if (!map.has(ga.artifact_id)) {
            map.set(ga.artifact_id, new Set());
          }
          map.get(ga.artifact_id)!.add(group.id);
        });
      }
    });
    return map;
  }, [groupArtifactQueries]);

  // Artifacts organized by group (position-sorted)
  const artifactsByGroup = useMemo(() => {
    const byGroup = new Map<string, Artifact[]>();
    groups.forEach((group) => byGroup.set(group.id, []));

    artifacts.forEach((artifact) => {
      const memberGroups = artifactGroupMembership.get(artifact.id);
      if (memberGroups) {
        memberGroups.forEach((groupId) => {
          const arr = byGroup.get(groupId);
          if (arr) arr.push(artifact);
        });
      }
    });

    // Sort by position within each group
    groupArtifactQueries.forEach(({ group, query }) => {
      if (query.data) {
        const arr = byGroup.get(group.id);
        if (arr) {
          arr.sort((a, b) => {
            const posA = query.data!.find((ga) => ga.artifact_id === a.id)?.position ?? 0;
            const posB = query.data!.find((ga) => ga.artifact_id === b.id)?.position ?? 0;
            return posA - posB;
          });
        }
      }
    });

    return byGroup;
  }, [artifacts, artifactGroupMembership, groups, groupArtifactQueries]);

  // Ungrouped artifacts
  const ungroupedArtifacts = useMemo(
    () => artifacts.filter((a) => !artifactGroupMembership.has(a.id)),
    [artifacts, artifactGroupMembership]
  );

  // Resolve what to show in the right pane
  const selectedGroup: Group | undefined = useMemo(
    () => groups.find((g) => g.id === selectedPane),
    [groups, selectedPane]
  );

  const paneArtifacts: Artifact[] = useMemo(() => {
    if (selectedPane === 'all') return artifacts;
    if (selectedPane === 'ungrouped') return ungroupedArtifacts;
    return artifactsByGroup.get(selectedPane) ?? [];
  }, [selectedPane, artifacts, ungroupedArtifacts, artifactsByGroup]);

  const paneName = useMemo(() => {
    if (selectedPane === 'all') return 'All Artifacts';
    if (selectedPane === 'ungrouped') return 'Ungrouped';
    return selectedGroup?.name ?? 'Group';
  }, [selectedPane, selectedGroup]);

  // If selected pane points to a deleted group, reset to 'all'
  React.useEffect(() => {
    if (
      selectedPane !== 'all' &&
      selectedPane !== 'ungrouped' &&
      !groups.find((g) => g.id === selectedPane)
    ) {
      setSelectedPane('all');
    }
  }, [groups, selectedPane]);

  // ── DnD setup ──────────────────────────────────────────────────────────
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id);
  }, []);

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveId(null);

      if (!over) return;

      const activeData = active.data.current as
        | { type: string; artifactId?: string; groupId?: string }
        | undefined;
      const overData = over.data.current as
        | { type: string; groupId?: string; artifactId?: string }
        | undefined;

      if (!activeData || activeData.type !== 'artifact') return;

      const draggedArtifactId = (activeData.artifactId ?? active.id) as string;
      const sourceGroupId = activeData.groupId; // group ID or 'all'/'ungrouped'

      // ── Dropped on a sidebar group ───────────────────────────────────
      if (overData?.type === 'group-sidebar' && overData.groupId) {
        const targetGroupId = overData.groupId;
        const targetGroup = groups.find((g) => g.id === targetGroupId);
        const targetName = targetGroup?.name ?? 'group';

        // Check if already in that group
        const membership = artifactGroupMembership.get(draggedArtifactId);
        if (membership?.has(targetGroupId)) {
          toast.info(`Already in ${targetName}`);
          return;
        }

        try {
          await addArtifactToGroup.mutateAsync({
            groupId: targetGroupId,
            artifactId: draggedArtifactId,
          });
          toast.success(`Added to ${targetName}`);
        } catch {
          toast.error('Failed to add to group');
        }
        return;
      }

      // ── Dropped on remove zone ───────────────────────────────────────
      if (overData?.type === 'remove-zone' && selectedGroup) {
        try {
          await removeArtifactFromGroup.mutateAsync({
            groupId: selectedGroup.id,
            artifactId: draggedArtifactId,
          });
          toast.success(`Removed from ${selectedGroup.name}`);
        } catch {
          toast.error('Failed to remove from group');
        }
        return;
      }

      // ── Dropped on another artifact (reorder within same group) ──────
      if (
        overData?.type === 'artifact' &&
        sourceGroupId &&
        sourceGroupId === overData.groupId &&
        sourceGroupId !== 'all' &&
        sourceGroupId !== 'ungrouped' &&
        active.id !== over.id
      ) {
        const groupArtifacts = artifactsByGroup.get(sourceGroupId) ?? [];
        const oldIndex = groupArtifacts.findIndex((a) => a.id === active.id);
        const newIndex = groupArtifacts.findIndex((a) => a.id === over.id);

        if (oldIndex !== -1 && newIndex !== -1) {
          const reordered = [...groupArtifacts];
          const [moved] = reordered.splice(oldIndex, 1);
          if (!moved) return;
          reordered.splice(newIndex, 0, moved);

          try {
            await reorderArtifactsInGroup.mutateAsync({
              groupId: sourceGroupId,
              artifactIds: reordered.map((a) => a.id),
            });
            toast.success('Artifacts reordered');
          } catch {
            toast.error('Failed to reorder artifacts');
          }
        }
      }
    },
    [
      groups,
      selectedGroup,
      artifactGroupMembership,
      artifactsByGroup,
      addArtifactToGroup,
      removeArtifactFromGroup,
      reorderArtifactsInGroup,
    ]
  );

  // ── Create group handler ───────────────────────────────────────────────
  const handleCreateGroup = useCallback(async () => {
    // Simple inline creation -- prompt-free, creates with default name
    // A more complete dialog can be added later
    const name = `New Group ${groups.length + 1}`;
    try {
      const created = await createGroup.mutateAsync({
        collection_id: collectionId,
        name,
        position: groups.length,
      });
      setSelectedPane(created.id);
      toast.success(`Created "${name}"`);
    } catch {
      toast.error('Failed to create group');
    }
  }, [collectionId, createGroup, groups.length]);

  // ── Drag overlay artifact ──────────────────────────────────────────────
  const draggedArtifact = useMemo(
    () => (activeId ? artifacts.find((a) => a.id === activeId) : undefined),
    [activeId, artifacts]
  );

  // ── Loading state ──────────────────────────────────────────────────────
  if (isLoadingGroups) {
    return <GroupedViewSkeleton />;
  }

  // ── Determine sort context ─────────────────────────────────────────────
  // Only wrap in SortableContext when viewing a specific group (not all / ungrouped)
  const isSpecificGroup = selectedPane !== 'all' && selectedPane !== 'ungrouped';
  const sortableIds = isSpecificGroup ? paneArtifacts.map((a) => a.id) : [];

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-full">
        {/* ── Left pane: sidebar (hidden below md) ─────────────────────── */}
        <div className="hidden md:block">
          <GroupSidebar
            groups={groups}
            selectedPane={selectedPane}
            onSelectPane={setSelectedPane}
            artifactCount={artifacts.length}
            ungroupedCount={ungroupedArtifacts.length}
            onCreateGroup={handleCreateGroup}
          />
        </div>

        {/* ── Right pane ───────────────────────────────────────────────── */}
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {/* Mobile dropdown (shown below md) */}
          <div className="block p-4 pb-0 md:hidden">
            <Select
              value={selectedPane}
              onValueChange={(value: string) => setSelectedPane(value as PaneSelection)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select view" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">
                  All Artifacts ({artifacts.length})
                </SelectItem>
                <SelectItem value="ungrouped">
                  Ungrouped ({ungroupedArtifacts.length})
                </SelectItem>
                {groups.map((group) => (
                  <SelectItem key={group.id} value={group.id}>
                    {group.name} ({group.artifact_count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Pane content */}
          <div className="flex flex-1 flex-col overflow-hidden p-4">
            <PaneHeader title={paneName} count={paneArtifacts.length} />

            {/* Remove-from-group drop zone */}
            {isSpecificGroup && selectedGroup && (
              <div className="mb-3">
                <RemoveFromGroupDropZone groupName={selectedGroup.name} />
              </div>
            )}

            {/* Artifact list */}
            {paneArtifacts.length === 0 ? (
              <EmptyState
                message={
                  selectedPane === 'all'
                    ? 'No artifacts in this collection'
                    : selectedPane === 'ungrouped'
                      ? 'All artifacts are assigned to groups'
                      : 'No artifacts in this group. Drag artifacts here to add them.'
                }
              />
            ) : (
              <ScrollArea className="flex-1">
                <SortableContext
                  items={sortableIds}
                  strategy={verticalListSortingStrategy}
                >
                  <div className="space-y-1 pr-2">
                    {paneArtifacts.map((artifact) => (
                      <DraggableMiniArtifactCard
                        key={artifact.id}
                        artifact={artifact}
                        groupId={isSpecificGroup ? selectedPane : 'all'}
                        onClick={() => onArtifactClick?.(artifact)}
                      />
                    ))}
                  </div>
                </SortableContext>
              </ScrollArea>
            )}
          </div>
        </div>
      </div>

      {/* Drag overlay (portal) */}
      <DragOverlay>
        {draggedArtifact ? (
          <MiniArtifactCard
            artifact={draggedArtifact}
            onClick={() => {}}
            className="shadow-lg"
          />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
