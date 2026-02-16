/**
 * GroupedArtifactView Component
 *
 * Displays artifacts organized by groups with drag-and-drop support using dnd-kit.
 * Features:
 * - Collapsible group sections sorted alphabetically
 * - Ungrouped artifacts section
 * - Drag-and-drop artifact reordering within groups
 * - Drag-and-drop artifact movement between groups
 * - Compact list-item rows (not cards)
 * - Keyboard accessible
 */

'use client';

import * as React from 'react';
import { useState, useMemo, useCallback } from 'react';
import * as LucideIcons from 'lucide-react';
import {
  DndContext,
  DragOverlay,
  DragOverEvent,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  UniqueIdentifier,
  useDroppable,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown, ChevronRight, GripVertical, Package } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';
import { getArtifactTypeConfig } from '@/types/artifact';
import type { Group } from '@/types/groups';
import {
  useGroups,
  useGroupArtifacts,
  useReorderArtifactsInGroup,
  useMoveArtifactToGroup,
} from '@/hooks';

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

// Drag data attached to sortable items
interface DragData {
  type: 'artifact';
  id: string;
  groupId: string; // group ID or 'ungrouped'
}

// Sortable artifact list item (compact row)
interface SortableArtifactRowProps {
  artifact: Artifact;
  groupId: string;
  onArtifactClick?: (artifact: Artifact) => void;
}

function SortableArtifactRow({
  artifact,
  groupId,
  onArtifactClick,
}: SortableArtifactRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: artifact.id,
    data: {
      type: 'artifact',
      id: artifact.id,
      groupId,
    } satisfies DragData,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  const config = getArtifactTypeConfig(artifact.type);
  const IconComponent = (LucideIcons as any)[config.icon] as
    | React.ComponentType<{ className?: string }>
    | undefined;
  const Icon = IconComponent || LucideIcons.FileText;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-3 rounded-md border px-3 py-2 transition-colors hover:bg-accent/50',
        isDragging && 'border-dashed'
      )}
    >
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
        className="flex-shrink-0 cursor-grab active:cursor-grabbing"
        aria-label={`Drag ${artifact.name} to reorder or move between groups`}
      >
        <GripVertical className="h-4 w-4 text-muted-foreground" />
      </div>

      {/* Type icon */}
      <Icon className={cn('h-4 w-4 flex-shrink-0', config.color)} />

      {/* Name (clickable) */}
      <button
        type="button"
        className="min-w-0 flex-1 truncate text-left text-sm font-medium hover:underline"
        onClick={() => onArtifactClick?.(artifact)}
      >
        {artifact.name}
      </button>

      {/* Type badge */}
      <Badge variant="secondary" className="flex-shrink-0 text-xs">
        {config.label}
      </Badge>

      {/* Description snippet */}
      {artifact.description && (
        <span className="hidden min-w-0 max-w-[200px] truncate text-xs text-muted-foreground lg:inline">
          {artifact.description}
        </span>
      )}
    </div>
  );
}

// Standalone artifact row for the drag overlay (no sortable context)
function ArtifactRowOverlay({ artifact }: { artifact: Artifact }) {
  const config = getArtifactTypeConfig(artifact.type);
  const IconComponent = (LucideIcons as any)[config.icon] as
    | React.ComponentType<{ className?: string }>
    | undefined;
  const Icon = IconComponent || LucideIcons.FileText;

  return (
    <div className="flex items-center gap-3 rounded-md border bg-card px-3 py-2 shadow-lg">
      <GripVertical className="h-4 w-4 text-muted-foreground" />
      <Icon className={cn('h-4 w-4 flex-shrink-0', config.color)} />
      <span className="truncate text-sm font-medium">{artifact.name}</span>
      <Badge variant="secondary" className="flex-shrink-0 text-xs">
        {config.label}
      </Badge>
    </div>
  );
}

// Droppable group section
interface DroppableGroupSectionProps {
  group: Group;
  artifacts: Artifact[];
  isOpen: boolean;
  onToggle: () => void;
  onArtifactClick?: (artifact: Artifact) => void;
  isDropTarget: boolean;
}

function DroppableGroupSection({
  group,
  artifacts,
  isOpen,
  onToggle,
  onArtifactClick,
  isDropTarget,
}: DroppableGroupSectionProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `droppable-group-${group.id}`,
    data: {
      type: 'group',
      groupId: group.id,
    },
  });

  const highlighted = isDropTarget || isOver;

  return (
    <div ref={setNodeRef} className="space-y-2">
      <Collapsible open={isOpen} onOpenChange={onToggle}>
        <div
          className={cn(
            'flex items-center gap-2 rounded-lg border bg-card p-3 transition-colors hover:bg-accent/50',
            highlighted && 'border-primary bg-primary/5 ring-1 ring-primary/30'
          )}
        >
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="flex-1 justify-start">
              {isOpen ? (
                <ChevronDown className="mr-2 h-4 w-4" />
              ) : (
                <ChevronRight className="mr-2 h-4 w-4" />
              )}
              <span className="font-semibold">{group.name}</span>
              <span className="ml-2 text-xs text-muted-foreground">
                ({artifacts.length} {artifacts.length === 1 ? 'artifact' : 'artifacts'})
              </span>
            </Button>
          </CollapsibleTrigger>
        </div>

        <CollapsibleContent className="mt-2 space-y-1 pl-4">
          {artifacts.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              <Package className="mx-auto mb-2 h-8 w-8 opacity-50" />
              <p>No artifacts in this group</p>
            </div>
          ) : (
            <SortableContext
              items={artifacts.map((a) => a.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-1">
                {artifacts.map((artifact) => (
                  <SortableArtifactRow
                    key={artifact.id}
                    artifact={artifact}
                    groupId={group.id}
                    onArtifactClick={onArtifactClick}
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

// Droppable ungrouped section
interface DroppableUngroupedSectionProps {
  artifacts: Artifact[];
  onArtifactClick?: (artifact: Artifact) => void;
  isDropTarget: boolean;
}

function DroppableUngroupedSection({
  artifacts,
  onArtifactClick,
  isDropTarget,
}: DroppableUngroupedSectionProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: 'droppable-group-ungrouped',
    data: {
      type: 'group',
      groupId: 'ungrouped',
    },
  });

  const highlighted = isDropTarget || isOver;

  return (
    <div ref={setNodeRef} className="space-y-2">
      <Collapsible defaultOpen>
        <div
          className={cn(
            'flex items-center gap-2 rounded-lg border bg-muted/30 p-3',
            highlighted && 'border-primary bg-primary/5 ring-1 ring-primary/30'
          )}
        >
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="flex-1 justify-start">
              <ChevronDown className="mr-2 h-4 w-4" />
              <span className="font-semibold text-muted-foreground">Ungrouped</span>
              <span className="ml-2 text-xs text-muted-foreground">
                ({artifacts.length}{' '}
                {artifacts.length === 1 ? 'artifact' : 'artifacts'})
              </span>
            </Button>
          </CollapsibleTrigger>
        </div>

        <CollapsibleContent className="mt-2 space-y-1 pl-4">
          <div className="space-y-1">
            {artifacts.map((artifact) => (
              <SortableArtifactRow
                key={artifact.id}
                artifact={artifact}
                groupId="ungrouped"
                onArtifactClick={onArtifactClick}
              />
            ))}
          </div>
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
          <div className="space-y-1 pl-4">
            <Skeleton className="h-10 w-full rounded-md" />
            <Skeleton className="h-10 w-full rounded-md" />
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
}: GroupedArtifactViewProps) {
  // Fetch groups
  const { data: groupsData, isLoading: isLoadingGroups } = useGroups(collectionId);
  const groups = groupsData?.groups || [];
  // Sort groups alphabetically (case-insensitive)
  const sortedGroups = useMemo(() => {
    return [...groups].sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }));
  }, [groups]);

  // Track open/closed state for each group
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());

  // Drag state
  const [activeId, setActiveId] = useState<UniqueIdentifier | null>(null);
  const [overGroupId, setOverGroupId] = useState<string | null>(null);

  // Mutations
  const reorderArtifactsInGroup = useReorderArtifactsInGroup();
  const moveArtifactToGroup = useMoveArtifactToGroup();

  // Sensors for drag and drop
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
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
  const toggleGroup = useCallback((groupId: string) => {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  }, []);

  // Find which group a droppable belongs to
  const resolveDropGroupId = useCallback((overId: UniqueIdentifier | undefined, overData: Record<string, any> | undefined): string | null => {
    if (!overId) return null;

    // If dropped on a droppable group container
    if (overData?.type === 'group') {
      return overData.groupId as string;
    }

    // If dropped on another artifact, find that artifact's group
    if (overData?.type === 'artifact') {
      return overData.groupId as string;
    }

    // Fallback: check the id string for droppable group prefix
    const idStr = String(overId);
    if (idStr.startsWith('droppable-group-')) {
      return idStr.replace('droppable-group-', '');
    }

    // Check if it's an artifact ID we can map
    const groupId = artifactGroupMap.get(idStr);
    if (groupId) return groupId;

    return null;
  }, [artifactGroupMap]);

  // Drag handlers
  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id);
  }, []);

  const handleDragOver = useCallback((event: DragOverEvent) => {
    const { over } = event;
    if (!over) {
      setOverGroupId(null);
      return;
    }
    const targetGroupId = resolveDropGroupId(over.id, over.data.current as Record<string, any> | undefined);
    setOverGroupId(targetGroupId);
  }, [resolveDropGroupId]);

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event;

    setActiveId(null);
    setOverGroupId(null);

    if (!over) return;

    const activeData = active.data.current as DragData | undefined;
    const overData = over.data.current as Record<string, any> | undefined;

    if (!activeData || activeData.type !== 'artifact') return;

    const sourceGroupId = activeData.groupId;
    const targetGroupId = resolveDropGroupId(over.id, overData);

    if (!targetGroupId) return;

    // Same group: reorder artifacts within group
    if (sourceGroupId === targetGroupId && sourceGroupId !== 'ungrouped') {
      // Dropped on another artifact in the same group
      if (overData?.type === 'artifact' && active.id !== over.id) {
        const groupArtifacts = artifactsByGroup.get(sourceGroupId) || [];
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
          } catch (error) {
            toast.error('Failed to reorder artifacts');
            console.error('Reorder artifacts error:', error);
          }
        }
      }
      return;
    }

    // Different group: move artifact between groups
    if (sourceGroupId !== targetGroupId && sourceGroupId !== 'ungrouped' && targetGroupId !== 'ungrouped') {
      try {
        await moveArtifactToGroup.mutateAsync({
          sourceGroupId,
          targetGroupId,
          artifactId: active.id as string,
        });
        toast.success('Artifact moved to group');
      } catch (error) {
        toast.error('Failed to move artifact');
        console.error('Move artifact error:', error);
      }
    }
  }, [resolveDropGroupId, artifactsByGroup, reorderArtifactsInGroup, moveArtifactToGroup]);

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
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="space-y-4">
        {/* Groups (alphabetically sorted) */}
        {sortedGroups.map((group) => {
          const groupArtifacts = artifactsByGroup.get(group.id) || [];
          return (
            <DroppableGroupSection
              key={group.id}
              group={group}
              artifacts={groupArtifacts}
              isOpen={openGroups.has(group.id)}
              onToggle={() => toggleGroup(group.id)}
              onArtifactClick={onArtifactClick}
              isDropTarget={overGroupId === group.id}
            />
          );
        })}

        {/* Ungrouped artifacts */}
        {ungroupedArtifacts.length > 0 && (
          <DroppableUngroupedSection
            artifacts={ungroupedArtifacts}
            onArtifactClick={onArtifactClick}
            isDropTarget={overGroupId === 'ungrouped'}
          />
        )}
      </div>

      {/* Drag overlay */}
      <DragOverlay>
        {activeId &&
          (() => {
            const artifact = artifacts.find((a) => a.id === activeId);
            return artifact ? <ArtifactRowOverlay artifact={artifact} /> : null;
          })()}
      </DragOverlay>
    </DndContext>
  );
}
