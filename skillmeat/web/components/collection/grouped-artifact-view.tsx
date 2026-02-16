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
import { useState, useRef, useMemo, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  pointerWithin,
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
  rectSortingStrategy,
} from '@dnd-kit/sortable';
import { Package, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import type { Artifact } from '@/types/artifact';
import type { Group } from '@/types/groups';
import {
  useGroups,
  useGroupsArtifacts,
  useAddArtifactToGroup,
  useRemoveArtifactFromGroup,
  useReorderArtifactsInGroup,
  useDndAnimations,
} from '@/hooks';
import type { GroupArtifact } from '@/types/groups';
import { GroupSidebar, type PaneSelection } from './group-sidebar';
import { MiniArtifactCard, DraggableMiniArtifactCard } from './mini-artifact-card';
import { RemoveFromGroupDropZone } from './remove-from-group-zone';
import { DropIntoGroupOverlay, PoofParticles } from './dnd-animations';
import { GroupFormDialog } from '@/app/groups/components/group-form-dialog';

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
      <div className="flex-1 p-4">
        <Skeleton className="mb-3 h-8 w-48 rounded-md" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-24 w-full rounded-md" />
          ))}
        </div>
      </div>
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
  const lastDraggedArtifactRef = useRef<Artifact | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);

  // ── DnD Animations ────────────────────────────────────────────────────
  const { animState, triggerDropIntoGroup, triggerRemovePoof, reset: resetAnim } = useDndAnimations();

  // ── Queries ────────────────────────────────────────────────────────────
  const { data: groupsData, isLoading: isLoadingGroups } = useGroups(collectionId);
  const groups = groupsData?.groups ?? [];

  // Fetch artifacts for each group using useQueries (stable hook count)
  const groupIds = useMemo(() => groups.map((g) => g.id), [groups]);
  const groupArtifactResults = useGroupsArtifacts(groupIds);

  // Create lookup map from results for compatibility with existing code
  const groupArtifactQueries = useMemo(
    () =>
      groups.map((group) => {
        const result = groupArtifactResults.find((r) => r.groupId === group.id);
        return {
          group,
          query: result?.query ?? ({
            data: undefined,
            isLoading: false,
          } as { data: GroupArtifact[] | undefined; isLoading: boolean }),
        };
      }),
    [groups, groupArtifactResults]
  );

  // ── Mutations ──────────────────────────────────────────────────────────
  const addArtifactToGroup = useAddArtifactToGroup();
  const removeArtifactFromGroup = useRemoveArtifactFromGroup();
  const reorderArtifactsInGroup = useReorderArtifactsInGroup();

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
    const found = artifacts.find((a) => a.id === event.active.id);
    if (found) lastDraggedArtifactRef.current = found;
  }, [artifacts]);

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

        // Trigger drop-into animation
        const targetEl = document.querySelector(`[data-group-drop-id="${targetGroupId}"]`);
        if (targetEl) {
          const rect = targetEl.getBoundingClientRect();
          triggerDropIntoGroup(targetGroupId, rect);
        }

        try {
          await addArtifactToGroup.mutateAsync({
            groupId: targetGroupId,
            artifactId: draggedArtifactId,
          });
        } catch {
          resetAnim();
          toast.error('Failed to add to group');
        }
        return;
      }

      // ── Dropped on remove zone ───────────────────────────────────────
      if (overData?.type === 'remove-zone' && selectedGroup) {
        // Trigger poof animation
        triggerRemovePoof(selectedGroup.id);

        try {
          await removeArtifactFromGroup.mutateAsync({
            groupId: selectedGroup.id,
            artifactId: draggedArtifactId,
          });
        } catch {
          resetAnim();
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
      triggerDropIntoGroup,
      triggerRemovePoof,
      resetAnim,
    ]
  );

  // ── Create group handler ───────────────────────────────────────────────
  const handleCreateGroup = useCallback(() => {
    setCreateDialogOpen(true);
  }, []);

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
      collisionDetection={pointerWithin}
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
            animState={animState}
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

          {/* Pane header (fixed) */}
          <div className="shrink-0 px-4 pt-4">
            <div className="flex items-center gap-2 pb-3">
              <h2 className="text-lg font-semibold">{paneName}</h2>
              <span className="text-sm text-muted-foreground">
                ({paneArtifacts.length} {paneArtifacts.length === 1 ? 'artifact' : 'artifacts'})
              </span>
              {selectedGroup && (
                <Button variant="ghost" size="sm" onClick={() => setEditingGroup(selectedGroup)}>
                  <Settings className="h-4 w-4" />
                  <span className="sr-only">Manage Group</span>
                </Button>
              )}
            </div>

            {/* Remove-from-group drop zone (visible only during drag) */}
            {isSpecificGroup && selectedGroup && activeId && (
              <div className="mb-3 animate-in fade-in slide-in-from-top-1 duration-200">
                <RemoveFromGroupDropZone
                  groupName={selectedGroup.name}
                  isPoofing={animState.phase === 'dropping-remove'}
                />
              </div>
            )}
          </div>

          {/* Scrollable artifact grid */}
          <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4">
            {paneArtifacts.length === 0 ? (
              <EmptyState
                message={
                  selectedPane === 'all'
                    ? 'No artifacts in your collection yet'
                    : selectedPane === 'ungrouped'
                      ? 'All artifacts are organized into groups'
                      : 'No artifacts in this group yet. Drag artifacts here to add them.'
                }
              />
            ) : (
              <SortableContext
                items={sortableIds}
                strategy={rectSortingStrategy}
              >
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
            )}
          </div>
        </div>
      </div>

      {/* Drag overlay (portal) */}
      <DragOverlay dropAnimation={null}>
        {draggedArtifact ? (
          <div className="animate-dnd-pickup">
            <MiniArtifactCard
              artifact={draggedArtifact}
              onClick={() => {}}
              className="shadow-lg"
            />
          </div>
        ) : null}
      </DragOverlay>

      {/* Drop-into-group animation overlay */}
      {animState.phase === 'dropping-into-group' &&
        animState.targetRect &&
        lastDraggedArtifactRef.current && (
          <DropIntoGroupOverlay
            artifact={lastDraggedArtifactRef.current}
            targetRect={animState.targetRect}
          />
        )}

      {/* Poof animation overlay (centered on remove zone) */}
      {animState.phase === 'dropping-remove' && (
        <div className={cn(
          'pointer-events-none fixed inset-0 z-50',
          'flex items-center justify-center'
        )}>
          <div className="animate-dnd-poof">
            {lastDraggedArtifactRef.current && (
              <MiniArtifactCard
                artifact={lastDraggedArtifactRef.current}
                onClick={() => {}}
                className="w-40 shadow-lg"
              />
            )}
          </div>
          <PoofParticles />
        </div>
      )}
      {/* Create group dialog */}
      <GroupFormDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        collectionId={collectionId}
        defaultPosition={groups.length}
      />

      {/* Edit group dialog */}
      <GroupFormDialog
        open={!!editingGroup}
        onOpenChange={(open) => !open && setEditingGroup(null)}
        collectionId={collectionId}
        group={editingGroup}
      />
    </DndContext>
  );
}
