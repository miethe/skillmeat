'use client';

import * as React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { Plus, Layers, FolderOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { resolveColorHex, ICON_MAP } from '@/lib/group-constants';
import type { Group } from '@/types/groups';
import type { DndAnimState } from '@/hooks';
import { SuccessCheckmark } from './dnd-animations';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PaneSelection = 'all' | 'ungrouped' | string;

export interface GroupSidebarProps {
  groups: Group[];
  selectedPane: PaneSelection;
  onSelectPane: (pane: PaneSelection) => void;
  artifactCount: number;
  ungroupedCount: number;
  onCreateGroup: () => void;
  /** Animation state from useDndAnimations for badge/checkmark feedback */
  animState?: DndAnimState;
}

// ---------------------------------------------------------------------------
// DroppableGroupItem (sub-component)
// ---------------------------------------------------------------------------

interface DroppableGroupItemProps {
  group: Group;
  isSelected: boolean;
  onSelect: () => void;
  animState?: DndAnimState;
}

function DroppableGroupItem({ group, isSelected, onSelect, animState }: DroppableGroupItemProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `group-drop-${group.id}`,
    data: {
      type: 'group-sidebar',
      groupId: group.id,
    },
  });

  const colorHex = resolveColorHex(group.color ?? 'slate');
  const iconKey = group.icon ?? 'layers';
  const IconComponent = ICON_MAP[iconKey] ?? ICON_MAP.layers;

  // Determine badge animation class based on animation state
  const isTargetForAdd =
    animState?.phase === 'success-feedback' && animState.targetGroupId === group.id;
  const isSourceForRemove =
    animState?.phase === 'remove-feedback' && animState.sourceGroupId === group.id;

  return (
    <button
      ref={setNodeRef}
      type="button"
      data-group-drop-id={group.id}
      onClick={onSelect}
      className={cn(
        'flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm',
        'transition-all duration-200 ease-out',
        'hover:bg-accent/50',
        isSelected && 'bg-accent font-medium',
        // Enhanced drop target: scale up, stronger background, pulsing glow
        isOver && 'scale-[1.03] bg-primary/10 ring-2 ring-primary/60 animate-dnd-drop-target-pulse',
        isOver && !isSelected && 'font-medium',
      )}
    >
      <span
        className={cn(
          'shrink-0 transition-transform duration-200',
          isOver && 'scale-110',
        )}
        style={{ color: colorHex }}
      >
        <IconComponent className="h-4 w-4" />
      </span>
      <span className="min-w-0 flex-1 truncate">{group.name}</span>
      <span
        className={cn(
          'relative shrink-0 text-xs text-muted-foreground',
          isTargetForAdd && 'animate-dnd-badge-pop',
          isSourceForRemove && 'animate-dnd-badge-shrink'
        )}
      >
        {group.artifact_count}
        {isTargetForAdd && <SuccessCheckmark />}
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// GroupSidebar
// ---------------------------------------------------------------------------

export function GroupSidebar({
  groups,
  selectedPane,
  onSelectPane,
  artifactCount,
  ungroupedCount,
  onCreateGroup,
  animState,
}: GroupSidebarProps) {
  return (
    <div className="flex h-full w-[280px] shrink-0 flex-col border-r bg-background">
      {/* Fixed items: All Artifacts + Ungrouped */}
      <div className="space-y-1 p-3">
        <button
          type="button"
          onClick={() => onSelectPane('all')}
          className={cn(
            'flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors',
            'hover:bg-accent/50',
            selectedPane === 'all' && 'bg-accent font-medium'
          )}
        >
          <Layers className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="min-w-0 flex-1 truncate">All Artifacts</span>
          <span className="shrink-0 text-xs text-muted-foreground">
            {artifactCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => onSelectPane('ungrouped')}
          className={cn(
            'flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors',
            'hover:bg-accent/50',
            selectedPane === 'ungrouped' && 'bg-accent font-medium'
          )}
        >
          <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="min-w-0 flex-1 truncate">Ungrouped</span>
          <span className="shrink-0 text-xs text-muted-foreground">
            {ungroupedCount}
          </span>
        </button>
      </div>

      <Separator />

      {/* Scrollable group list */}
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-1 p-3">
          {groups.map((group) => (
            <DroppableGroupItem
              key={group.id}
              group={group}
              isSelected={selectedPane === group.id}
              onSelect={() => onSelectPane(group.id)}
              animState={animState}
            />
          ))}

          {groups.length === 0 && (
            <p className="px-3 py-4 text-center text-xs text-muted-foreground">
              No groups yet
            </p>
          )}
        </div>
      </ScrollArea>

      {/* Create Group button */}
      <div className="border-t p-3">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={onCreateGroup}
        >
          <Plus className="h-4 w-4" />
          Create Group
        </Button>
      </div>
    </div>
  );
}
