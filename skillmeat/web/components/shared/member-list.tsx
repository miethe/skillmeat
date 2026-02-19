'use client';

/**
 * MemberList — Sortable member list for composite plugin management.
 *
 * Renders an ordered list of artifact members with drag-to-reorder
 * (via @dnd-kit/sortable), keyboard Up/Down arrow reordering, and
 * per-item remove actions.  Used in CreatePluginDialog and PluginMembersTab.
 *
 * Accessibility (WCAG 2.1 AA):
 * - Role="listbox" / role="option" for the reorderable list
 * - aria-roledescription="sortable" on each item
 * - Live region announces reorder and remove operations
 * - Full keyboard support: ArrowUp / ArrowDown to move, Delete to remove
 * - Drag handle with visible focus ring
 *
 * @example
 * ```tsx
 * <MemberList
 *   members={members}
 *   onReorder={setMembers}
 *   onRemove={(id) => setMembers((m) => m.filter((a) => a.id !== id))}
 * />
 * ```
 */

import React, { useCallback, useId, useRef, useState } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Bot,
  Blocks,
  GripVertical,
  Server,
  Sparkles,
  Terminal,
  Webhook,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Artifact, ArtifactType } from '@/types/artifact';

// ---------------------------------------------------------------------------
// Visual constants (match MemberSearchInput)
// ---------------------------------------------------------------------------

const ARTIFACT_ICONS: Record<ArtifactType, React.ElementType> = {
  skill: Sparkles,
  command: Terminal,
  agent: Bot,
  mcp: Server,
  hook: Webhook,
  composite: Blocks,
};

const ARTIFACT_TYPE_LABELS: Record<ArtifactType, string> = {
  skill: 'Skill',
  command: 'Command',
  agent: 'Agent',
  mcp: 'MCP',
  hook: 'Hook',
  composite: 'Plugin',
};

const TYPE_COLORS: Record<ArtifactType, string> = {
  skill: 'text-purple-500',
  command: 'text-blue-500',
  agent: 'text-green-500',
  mcp: 'text-orange-500',
  hook: 'text-pink-500',
  composite: 'text-indigo-500',
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MemberListProps {
  /** Ordered list of member artifacts. */
  members: Artifact[];
  /** Called with the full re-ordered array after a drag or keyboard move. */
  onReorder: (members: Artifact[]) => void;
  /** Called with the artifact ID when the user removes a member. */
  onRemove: (artifactId: string) => void;
  /** Additional class names applied to the root wrapper. */
  className?: string;
  /** Disable all interactions (drag, keyboard, remove). */
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// SortableItem sub-component
// ---------------------------------------------------------------------------

interface SortableItemProps {
  artifact: Artifact;
  index: number;
  total: number;
  isFocused: boolean;
  onFocus: (id: string) => void;
  onBlur: () => void;
  onKeyDown: (e: React.KeyboardEvent, id: string) => void;
  onRemove: (id: string) => void;
  disabled: boolean;
  listId: string;
}

function SortableItem({
  artifact,
  index,
  total,
  isFocused,
  onFocus,
  onBlur,
  onKeyDown,
  onRemove,
  disabled,
  listId,
}: SortableItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: artifact.id, disabled });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const Icon = ARTIFACT_ICONS[artifact.type] ?? Sparkles;
  const colorClass = TYPE_COLORS[artifact.type] ?? 'text-muted-foreground';
  const typeLabel = ARTIFACT_TYPE_LABELS[artifact.type] ?? artifact.type;

  return (
    <li
      ref={setNodeRef}
      style={style}
      id={`${listId}-item-${artifact.id}`}
      role="option"
      aria-selected={isFocused}
      aria-roledescription="sortable item"
      aria-label={`${artifact.name}, ${typeLabel}, position ${index + 1} of ${total}`}
      aria-setsize={total}
      aria-posinset={index + 1}
      className={cn(
        'group flex items-center gap-2.5 rounded-md border px-3 py-2',
        'text-sm transition-all duration-150',
        isDragging
          ? 'border-indigo-400 bg-accent/80 opacity-50 shadow-sm'
          : isFocused
          ? 'border-indigo-400 bg-accent/60 ring-1 ring-indigo-400/50'
          : 'border-border bg-card hover:border-border/80 hover:bg-accent/40',
        disabled && 'pointer-events-none opacity-60'
      )}
      onFocus={() => onFocus(artifact.id)}
      onBlur={onBlur}
      onKeyDown={(e) => onKeyDown(e, artifact.id)}
      tabIndex={disabled ? -1 : 0}
    >
      {/* Drag handle */}
      <button
        type="button"
        {...attributes}
        {...listeners}
        disabled={disabled}
        aria-label={`Drag to reorder ${artifact.name}`}
        tabIndex={-1}
        className={cn(
          'flex h-5 w-5 shrink-0 cursor-grab items-center justify-center rounded',
          'text-muted-foreground/40 transition-colors',
          'hover:text-muted-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'active:cursor-grabbing',
          disabled && 'cursor-default'
        )}
      >
        <GripVertical className="h-4 w-4" aria-hidden="true" />
      </button>

      {/* Position indicator */}
      <span
        className="w-5 shrink-0 text-center text-xs font-mono text-muted-foreground/60 select-none"
        aria-hidden="true"
      >
        {index + 1}
      </span>

      {/* Type icon */}
      <Icon
        className={cn('h-3.5 w-3.5 shrink-0', colorClass)}
        aria-hidden="true"
      />

      {/* Name */}
      <span className="flex-1 truncate font-medium">{artifact.name}</span>

      {/* Type badge */}
      <span
        className={cn(
          'shrink-0 rounded px-1.5 py-0.5 text-xs font-medium',
          'bg-muted text-muted-foreground'
        )}
        aria-hidden="true"
      >
        {typeLabel}
      </span>

      {/* Remove button */}
      <button
        type="button"
        disabled={disabled}
        aria-label={`Remove ${artifact.name} from plugin`}
        onClick={(e) => {
          e.stopPropagation();
          onRemove(artifact.id);
        }}
        className={cn(
          'flex h-5 w-5 shrink-0 items-center justify-center rounded',
          'text-muted-foreground/40 opacity-0 transition-all duration-150',
          'group-hover:opacity-100 group-focus-within:opacity-100',
          isFocused && 'opacity-100',
          'hover:bg-destructive/10 hover:text-destructive',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:opacity-100',
          disabled && 'pointer-events-none'
        )}
      >
        <X className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </li>
  );
}

// ---------------------------------------------------------------------------
// DragOverlayItem — ghost rendered while dragging
// ---------------------------------------------------------------------------

function DragOverlayItem({ artifact }: { artifact: Artifact }) {
  const Icon = ARTIFACT_ICONS[artifact.type] ?? Sparkles;
  const colorClass = TYPE_COLORS[artifact.type] ?? 'text-muted-foreground';
  const typeLabel = ARTIFACT_TYPE_LABELS[artifact.type] ?? artifact.type;

  return (
    <li
      aria-hidden="true"
      className={cn(
        'flex items-center gap-2.5 rounded-md border px-3 py-2',
        'border-indigo-400 bg-card text-sm shadow-lg ring-1 ring-indigo-400/40',
        'cursor-grabbing'
      )}
      style={{ listStyle: 'none' }}
    >
      <span className="flex h-5 w-5 shrink-0 items-center justify-center text-muted-foreground">
        <GripVertical className="h-4 w-4" aria-hidden="true" />
      </span>
      <span className="w-5 shrink-0 text-center text-xs font-mono text-muted-foreground/60 select-none" />
      <Icon className={cn('h-3.5 w-3.5 shrink-0', colorClass)} aria-hidden="true" />
      <span className="flex-1 truncate font-medium">{artifact.name}</span>
      <span className="shrink-0 rounded px-1.5 py-0.5 text-xs font-medium bg-muted text-muted-foreground">
        {typeLabel}
      </span>
    </li>
  );
}

// ---------------------------------------------------------------------------
// MemberList
// ---------------------------------------------------------------------------

export function MemberList({
  members,
  onReorder,
  onRemove,
  className,
  disabled = false,
}: MemberListProps) {
  const listId = useId();
  const announcerId = useId();

  // Keyboard focus tracking
  const [focusedId, setFocusedId] = useState<string | null>(null);

  // Active drag item
  const [activeDragId, setActiveDragId] = useState<string | null>(null);
  const activeDragArtifact = activeDragId
    ? members.find((m) => m.id === activeDragId) ?? null
    : null;

  // Live region announcement text
  const [announcement, setAnnouncement] = useState('');
  const announcementTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const announce = useCallback((message: string) => {
    setAnnouncement(message);
    if (announcementTimer.current) clearTimeout(announcementTimer.current);
    announcementTimer.current = setTimeout(() => setAnnouncement(''), 2000);
  }, []);

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // ---------------------------------------------------------------------------
  // DnD handlers
  // ---------------------------------------------------------------------------

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveDragId(String(event.active.id));
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveDragId(null);
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIndex = members.findIndex((m) => m.id === active.id);
      const newIndex = members.findIndex((m) => m.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      // oldIndex / newIndex were already validated above — non-null safe
      const moved = members[oldIndex]!;
      const reordered = arrayMove(members, oldIndex, newIndex);
      onReorder(reordered);
      announce(
        `${moved.name} moved from position ${oldIndex + 1} to ${newIndex + 1}`
      );
    },
    [members, onReorder, announce]
  );

  // ---------------------------------------------------------------------------
  // Keyboard reorder handler
  // ---------------------------------------------------------------------------

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, artifactId: string) => {
      const index = members.findIndex((m) => m.id === artifactId);
      if (index === -1) return;

      // index was already validated — non-null safe for all member lookups below
      const currentArtifact = members[index]!;

      if (e.key === 'ArrowUp' && index > 0) {
        e.preventDefault();
        const reordered = arrayMove(members, index, index - 1);
        onReorder(reordered);
        announce(`${currentArtifact.name} moved up to position ${index}`);
        // Keep focus on moved item after re-render
        setFocusedId(artifactId);
      } else if (e.key === 'ArrowDown' && index < members.length - 1) {
        e.preventDefault();
        const reordered = arrayMove(members, index, index + 1);
        onReorder(reordered);
        announce(`${currentArtifact.name} moved down to position ${index + 2}`);
        setFocusedId(artifactId);
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        onRemove(artifactId);
        announce(`${currentArtifact.name} removed from plugin`);
        // Move focus to next remaining item
        const nextFocus = members[index + 1] ?? members[index - 1];
        setFocusedId(nextFocus?.id ?? null);
      }
    },
    [members, onReorder, onRemove, announce]
  );

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const itemIds = members.map((m) => m.id);

  if (members.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center rounded-md border border-dashed',
          'border-border/60 px-4 py-8 text-center',
          className
        )}
        role="status"
        aria-label="Member list empty"
      >
        <Blocks
          className="mb-2 h-8 w-8 text-indigo-500/40"
          aria-hidden="true"
        />
        <p className="text-sm text-muted-foreground">No members added yet</p>
        <p className="mt-0.5 text-xs text-muted-foreground/60">
          Search for artifacts above to add them
        </p>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {/* Live region for screen-reader announcements */}
      <div
        id={announcerId}
        role="status"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      >
        {announcement}
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
          <ul
            id={listId}
            role="listbox"
            aria-label="Plugin members"
            aria-multiselectable="false"
            aria-orientation="vertical"
            className="flex flex-col gap-1"
          >
            {members.map((artifact, index) => (
              <SortableItem
                key={artifact.id}
                artifact={artifact}
                index={index}
                total={members.length}
                isFocused={focusedId === artifact.id}
                onFocus={setFocusedId}
                onBlur={() => setFocusedId(null)}
                onKeyDown={handleKeyDown}
                onRemove={onRemove}
                disabled={disabled}
                listId={listId}
              />
            ))}
          </ul>
        </SortableContext>

        {/* Drag overlay — rendered at document root, never affects layout */}
        <DragOverlay>
          {activeDragArtifact ? (
            <DragOverlayItem artifact={activeDragArtifact} />
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Helper text */}
      {!disabled && members.length > 1 && (
        <p className="mt-0.5 text-xs text-muted-foreground/50" aria-hidden="true">
          Drag or use arrow keys to reorder
        </p>
      )}
    </div>
  );
}
