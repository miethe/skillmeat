/**
 * GroupedArtifactView Component
 *
 * Displays artifacts organized by groups with drag-and-drop reordering using dnd-kit.
 * Features:
 * - Collapsible group sections
 * - Ungrouped artifacts section
 * - Drag-and-drop artifact reordering within groups
 * - Drag-and-drop group reordering
 * - Keyboard accessible
 */

'use client';

import * as React from 'react';
import { useState, useMemo } from 'react';
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
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ChevronDown, ChevronRight, GripVertical, Package } from 'lucide-react';
import { UnifiedCard, UnifiedCardSkeleton } from '@/components/shared/unified-card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import type { Artifact } from '@/types/artifact';
import type { Group } from '@/types/groups';
import {
  useGroups,
  useGroupArtifacts,
  useReorderGroups,
  useReorderArtifactsInGroup,
} from '@/hooks/use-groups';

// Props interface
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

// Drag types
type DragType = 'artifact' | 'group';

interface DragData {
  type: DragType;
  id: string;
  groupId?: string; // For artifacts, the group they belong to
}

// Sortable artifact card
interface SortableArtifactCardProps {
  artifact: Artifact;
  onArtifactClick?: (artifact: Artifact) => void;
  onMoveToCollection?: (artifact: Artifact) => void;
  onManageGroups?: (artifact: Artifact) => void;
  onEdit?: (artifact: Artifact) => void;
  onDelete?: (artifact: Artifact) => void;
}

function SortableArtifactCard({
  artifact,
  onArtifactClick,
}: SortableArtifactCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: artifact.id,
    data: {
      type: 'artifact',
      id: artifact.id,
    } satisfies DragData,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="relative">
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
        className="absolute left-2 top-1/2 -translate-y-1/2 z-10 cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-100 transition-opacity"
        aria-label="Drag to reorder"
      >
        <GripVertical className="h-5 w-5 text-muted-foreground" />
      </div>

      <div className="pl-8 group">
        <UnifiedCard
          item={artifact}
          onClick={() => onArtifactClick?.(artifact)}
        />
      </div>
    </div>
  );
}

// Sortable group section
interface SortableGroupSectionProps {
  group: Group;
  artifacts: Artifact[];
  isOpen: boolean;
  onToggle: () => void;
  onArtifactClick?: (artifact: Artifact) => void;
  onMoveToCollection?: (artifact: Artifact) => void;
  onManageGroups?: (artifact: Artifact) => void;
  onEdit?: (artifact: Artifact) => void;
  onDelete?: (artifact: Artifact) => void;
}

function SortableGroupSection({
  group,
  artifacts,
  isOpen,
  onToggle,
  onArtifactClick,
  onMoveToCollection,
  onManageGroups,
  onEdit,
  onDelete,
}: SortableGroupSectionProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: group.id,
    data: {
      type: 'group',
      id: group.id,
    } satisfies DragData,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="space-y-2">
      <Collapsible open={isOpen} onOpenChange={onToggle}>
        <div className="flex items-center gap-2 rounded-lg border bg-card p-3 hover:bg-accent/50 transition-colors">
          {/* Drag handle for group */}
          <div
            {...attributes}
            {...listeners}
            className="cursor-grab active:cursor-grabbing"
            aria-label="Drag to reorder group"
          >
            <GripVertical className="h-5 w-5 text-muted-foreground" />
          </div>

          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="flex-1 justify-start">
              {isOpen ? (
                <ChevronDown className="h-4 w-4 mr-2" />
              ) : (
                <ChevronRight className="h-4 w-4 mr-2" />
              )}
              <span className="font-semibold">{group.name}</span>
              <span className="ml-2 text-xs text-muted-foreground">
                ({artifacts.length} {artifacts.length === 1 ? 'artifact' : 'artifacts'})
              </span>
            </Button>
          </CollapsibleTrigger>
        </div>

        <CollapsibleContent className="space-y-2 mt-2 pl-4">
          {artifacts.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              <Package className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p>No artifacts in this group</p>
            </div>
          ) : (
            <SortableContext
              items={artifacts.map((a) => a.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {artifacts.map((artifact) => (
                  <SortableArtifactCard
                    key={artifact.id}
                    artifact={artifact}
                    onArtifactClick={onArtifactClick}
                    onMoveToCollection={onMoveToCollection}
                    onManageGroups={onManageGroups}
                    onEdit={onEdit}
                    onDelete={onDelete}
                  />
                ))}
              </div>
            </SortableContext>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

// Loading skeleton
function GroupedViewSkeleton() {
  return (
    <div className="space-y-4" data-testid="grouped-view-skeleton">
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-12 w-full rounded-lg" />
          <div className="pl-4 space-y-2">
            <UnifiedCardSkeleton />
            <UnifiedCardSkeleton />
          </div>
        </div>
      ))}
    </div>
  );
}

// Main component
export function GroupedArtifactView({
  collectionId,
  artifacts,
  onArtifactClick,
  onMoveToCollection,
  onManageGroups,
  onEdit,
  onDelete,
}: GroupedArtifactViewProps) {
  // Fetch groups
  const { data: groupsData, isLoading: isLoadingGroups } = useGroups(collectionId);
  const groups = groupsData?.groups || [];

  // Track open/closed state for each group
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());

  // Drag state
  const [activeId, setActiveId] = useState<UniqueIdentifier | null>(null);
  const [activeDragType, setActiveDragType] = useState<DragType | null>(null);

  // Mutations
  const reorderGroups = useReorderGroups();
  const reorderArtifactsInGroup = useReorderArtifactsInGroup();

  // Sensors for drag and drop
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement required to start drag
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Fetch artifacts for each group
  const groupArtifactQueries = groups.map((group) => ({
    group,
    // eslint-disable-next-line react-hooks/rules-of-hooks
    query: useGroupArtifacts(group.id),
  }));

  // Build artifact-to-group mapping
  const artifactGroupMap = useMemo(() => {
    const map = new Map<string, string>();
    groupArtifactQueries.forEach(({ group, query }) => {
      if (query.data) {
        query.data.forEach((groupArtifact) => {
          map.set(groupArtifact.artifact_id, group.id);
        });
      }
    });
    return map;
  }, [groupArtifactQueries]);

  // Organize artifacts by group
  const artifactsByGroup = useMemo(() => {
    const byGroup = new Map<string, Artifact[]>();

    // Initialize with empty arrays for each group
    groups.forEach((group) => {
      byGroup.set(group.id, []);
    });

    // Populate with artifacts
    artifacts.forEach((artifact) => {
      const groupId = artifactGroupMap.get(artifact.id);
      if (groupId) {
        const groupArtifacts = byGroup.get(groupId) || [];
        groupArtifacts.push(artifact);
        byGroup.set(groupId, groupArtifacts);
      }
    });

    // Sort each group's artifacts by position
    groupArtifactQueries.forEach(({ group, query }) => {
      if (query.data) {
        const sortedArtifacts = byGroup.get(group.id) || [];
        sortedArtifacts.sort((a, b) => {
          const posA = query.data!.find((ga) => ga.artifact_id === a.id)?.position ?? 0;
          const posB = query.data!.find((ga) => ga.artifact_id === b.id)?.position ?? 0;
          return posA - posB;
        });
        byGroup.set(group.id, sortedArtifacts);
      }
    });

    return byGroup;
  }, [artifacts, artifactGroupMap, groups, groupArtifactQueries]);

  // Ungrouped artifacts
  const ungroupedArtifacts = useMemo(() => {
    return artifacts.filter((artifact) => !artifactGroupMap.has(artifact.id));
  }, [artifacts, artifactGroupMap]);

  // Toggle group open/closed
  const toggleGroup = (groupId: string) => {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  // Drag handlers
  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    setActiveId(active.id);

    const data = active.data.current as DragData | undefined;
    setActiveDragType(data?.type || null);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;

    if (!over || active.id === over.id) {
      setActiveId(null);
      setActiveDragType(null);
      return;
    }

    const activeData = active.data.current as DragData | undefined;
    const overData = over.data.current as DragData | undefined;

    if (!activeData) {
      setActiveId(null);
      setActiveDragType(null);
      return;
    }

    // Reorder groups
    if (activeData.type === 'group' && overData?.type === 'group') {
      const oldIndex = groups.findIndex((g) => g.id === active.id);
      const newIndex = groups.findIndex((g) => g.id === over.id);

      if (oldIndex !== -1 && newIndex !== -1) {
        const reorderedGroups = [...groups];
        const [movedGroup] = reorderedGroups.splice(oldIndex, 1);
        if (!movedGroup) return;
        reorderedGroups.splice(newIndex, 0, movedGroup);

        try {
          await reorderGroups.mutateAsync({
            collectionId,
            groupIds: reorderedGroups.map((g) => g.id),
          });
          toast.success('Groups reordered successfully');
        } catch (error) {
          toast.error('Failed to reorder groups');
          console.error('Reorder groups error:', error);
        }
      }
    }

    // Reorder artifacts within a group
    if (activeData.type === 'artifact' && overData?.type === 'artifact') {
      // Find which group these artifacts belong to
      const activeGroupId = artifactGroupMap.get(active.id as string);
      const overGroupId = artifactGroupMap.get(over.id as string);

      if (activeGroupId && overGroupId && activeGroupId === overGroupId) {
        const groupArtifacts = artifactsByGroup.get(activeGroupId) || [];
        const oldIndex = groupArtifacts.findIndex((a) => a.id === active.id);
        const newIndex = groupArtifacts.findIndex((a) => a.id === over.id);

        if (oldIndex !== -1 && newIndex !== -1) {
          const reorderedArtifacts = [...groupArtifacts];
          const [movedArtifact] = reorderedArtifacts.splice(oldIndex, 1);
          if (!movedArtifact) return;
          reorderedArtifacts.splice(newIndex, 0, movedArtifact);

          try {
            await reorderArtifactsInGroup.mutateAsync({
              groupId: activeGroupId,
              artifactIds: reorderedArtifacts.map((a) => a.id),
            });
            toast.success('Artifacts reordered successfully');
          } catch (error) {
            toast.error('Failed to reorder artifacts');
            console.error('Reorder artifacts error:', error);
          }
        }
      }
    }

    setActiveId(null);
    setActiveDragType(null);
  };

  // Loading state
  if (isLoadingGroups) {
    return <GroupedViewSkeleton />;
  }

  // No groups
  if (groups.length === 0 && ungroupedArtifacts.length === 0) {
    return (
      <div className="py-12 text-center">
        <Package className="mx-auto h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 text-lg font-semibold">No groups or artifacts</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Create groups to organize your artifacts.
        </p>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="space-y-4">
        {/* Groups */}
        <SortableContext
          items={groups.map((g) => g.id)}
          strategy={verticalListSortingStrategy}
        >
          {groups.map((group) => {
            const groupArtifacts = artifactsByGroup.get(group.id) || [];
            return (
              <SortableGroupSection
                key={group.id}
                group={group}
                artifacts={groupArtifacts}
                isOpen={openGroups.has(group.id)}
                onToggle={() => toggleGroup(group.id)}
                onArtifactClick={onArtifactClick}
                onMoveToCollection={onMoveToCollection}
                onManageGroups={onManageGroups}
                onEdit={onEdit}
                onDelete={onDelete}
              />
            );
          })}
        </SortableContext>

        {/* Ungrouped artifacts */}
        {ungroupedArtifacts.length > 0 && (
          <div className="space-y-2">
            <Collapsible defaultOpen>
              <div className="flex items-center gap-2 rounded-lg border bg-muted/30 p-3">
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="sm" className="flex-1 justify-start">
                    <ChevronDown className="h-4 w-4 mr-2" />
                    <span className="font-semibold text-muted-foreground">Ungrouped</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      ({ungroupedArtifacts.length}{' '}
                      {ungroupedArtifacts.length === 1 ? 'artifact' : 'artifacts'})
                    </span>
                  </Button>
                </CollapsibleTrigger>
              </div>

              <CollapsibleContent className="space-y-2 mt-2 pl-4">
                <div className="space-y-2">
                  {ungroupedArtifacts.map((artifact) => (
                    <UnifiedCard
                      key={artifact.id}
                      item={artifact}
                      onClick={() => onArtifactClick?.(artifact)}
                    />
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          </div>
        )}
      </div>

      {/* Drag overlay */}
      <DragOverlay>
        {activeId && activeDragType === 'artifact' && (() => {
          const artifact = artifacts.find((a) => a.id === activeId);
          return artifact ? (
            <div className="opacity-80">
              <UnifiedCard item={artifact} />
            </div>
          ) : null;
        })()}
        {activeId && activeDragType === 'group' && (() => {
          const group = groups.find((g) => g.id === activeId);
          return group ? (
            <div className="opacity-80 rounded-lg border bg-card p-3">
              <span className="font-semibold">{group.name}</span>
            </div>
          ) : null;
        })()}
      </DragOverlay>
    </DndContext>
  );
}
