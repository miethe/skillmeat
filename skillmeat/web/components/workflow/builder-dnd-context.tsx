'use client';

import * as React from 'react';
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
  type Modifier,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { StageCard } from '@/components/workflow/stage-card';
import { StageConnector } from '@/components/workflow/stage-connector';
import type { WorkflowStage } from '@/types/workflow';

// ============================================================================
// Custom modifier — restrict drag movement to the vertical axis only.
// Equivalent to @dnd-kit/modifiers restrictToVerticalAxis without the package.
// ============================================================================

const restrictToVerticalAxis: Modifier = ({ transform }) => ({
  ...transform,
  x: 0,
});

// ============================================================================
// Types
// ============================================================================

export interface BuilderDndContextProps {
  /** Ordered list of workflow stages to render. */
  stages: WorkflowStage[];
  /** 0-based index of the currently selected stage, or null if none. */
  selectedIndex: number | null;
  /** Called when a drag operation completes with a new order. */
  onReorder: (fromIndex: number, toIndex: number) => void;
  /** Called when a stage card is clicked to select it. */
  onSelectStage: (index: number) => void;
  /** Called when the stage edit button is clicked. */
  onEditStage: (index: number) => void;
  /** Called when the stage delete button is clicked. */
  onDeleteStage: (index: number) => void;
  /** Called when the inline title is saved. */
  onTitleChange: (index: number, title: string) => void;
  /** Called when the "+" connector between stages is clicked. atIndex is the insertion position. */
  onAddStage: (atIndex: number) => void;
  /** Optional additional content rendered below the stage list (e.g. "Add Stage" button). */
  children?: React.ReactNode;
}

// ============================================================================
// SortableStageItem — wraps one StageCard with @dnd-kit sortable behaviour
// ============================================================================

export interface SortableStageItemProps {
  /** The stage to render. */
  stage: WorkflowStage;
  /** 0-based position in the list (used for display and connector callbacks). */
  index: number;
  /** Total number of stages (used to decide if a trailing connector is shown). */
  totalStages: number;
  /** Whether this card is currently selected. */
  isSelected: boolean;
  /** Whether to suppress rendering (true when this item is the drag ghost). */
  isDragging?: boolean;
  onSelect: (index: number) => void;
  onEdit: (index: number) => void;
  onDelete: (index: number) => void;
  onTitleChange: (index: number, title: string) => void;
  /** Insert a stage _after_ this one (passes index+1 to the parent). */
  onAddAfter: (atIndex: number) => void;
}

/**
 * SortableStageItem — a single drag-sortable stage slot.
 *
 * Registers itself with @dnd-kit's SortableContext via useSortable, passes
 * the resulting listeners/attributes as `dragHandleProps` to StageCard, and
 * renders a StageConnector below itself (except for the last item).
 */
export function SortableStageItem({
  stage,
  index,
  totalStages,
  isSelected,
  isDragging = false,
  onSelect,
  onEdit,
  onDelete,
  onTitleChange,
  onAddAfter,
}: SortableStageItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({ id: stage.id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    // Keep the original slot visible but ghosted while dragging
    opacity: isSortableDragging ? 0.4 : 1,
  };

  const dragHandleProps = { ...listeners, ...attributes };

  return (
    <div
      ref={setNodeRef}
      style={style}
      // Suppress pointer events on the ghosted slot so DragOverlay receives them
      aria-hidden={isSortableDragging ? true : undefined}
    >
      {/* Stage card */}
      <div
        role="listitem"
        onClick={() => onSelect(index)}
        // Allow keyboard activation via Enter / Space on the card itself
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSelect(index);
          }
        }}
        tabIndex={0}
        aria-label={`Stage ${index + 1}: ${stage.name}`}
        aria-selected={isSelected}
        className="cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-lg"
      >
        <StageCard
          stage={stage}
          index={index}
          mode="edit"
          isSelected={isSelected}
          onEdit={() => onEdit(index)}
          onDelete={() => onDelete(index)}
          onTitleChange={(title) => onTitleChange(index, title)}
          dragHandleProps={isDragging ? undefined : dragHandleProps}
        />
      </div>

      {/* Connector between this stage and the next */}
      {index < totalStages - 1 && (
        <StageConnector
          onAddStage={() => onAddAfter(index + 1)}
          showAddButton
          variant="sequential"
        />
      )}
    </div>
  );
}

// ============================================================================
// ARIA announcements
// ============================================================================

function buildAnnouncements(stages: WorkflowStage[]) {
  return {
    onDragStart({ active }: DragStartEvent) {
      const idx = stages.findIndex((s) => s.id === active.id);
      return idx !== -1
        ? `Picked up stage ${idx + 1}: ${stages[idx]!.name}. Use arrow keys to move, Space to drop, Escape to cancel.`
        : undefined;
    },
    onDragOver() {
      return undefined;
    },
    onDragEnd({ over }: DragEndEvent) {
      if (!over) return `Stage dropped and returned to original position.`;
      const toIdx = stages.findIndex((s) => s.id === over.id);
      return toIdx !== -1
        ? `Dropped at position ${toIdx + 1}.`
        : undefined;
    },
    onDragCancel({ active: cancelledActive }: { active: { id: string | number } }) {
      const idx = stages.findIndex((s) => s.id === cancelledActive.id);
      return idx !== -1
        ? `Drag cancelled. Stage ${idx + 1} returned to its original position.`
        : undefined;
    },
  };
}

// ============================================================================
// BuilderDndContext
// ============================================================================

/**
 * BuilderDndContext — DnD-enabled stage list for the workflow builder canvas.
 *
 * Wraps the stage list with @dnd-kit's DndContext + SortableContext so that
 * stages can be reordered by dragging. Each stage is rendered inside a
 * SortableStageItem that passes drag handle props through to StageCard.
 *
 * Drag behaviour:
 * - Mouse/touch: PointerSensor (requires 8px movement to start)
 * - Keyboard: Space → pick up, Arrow Up/Down → move, Space → drop, Escape → cancel
 * - Movement is restricted to the vertical axis via the restrictToVerticalAxis modifier
 * - A semi-transparent DragOverlay clone is shown while dragging
 *
 * ARIA:
 * - The stage list has role="list" with an accessible label
 * - Live announcements are provided for drag lifecycle events
 * - Each SortableStageItem has role="listitem" + aria-label
 */
export function BuilderDndContext({
  stages,
  selectedIndex,
  onReorder,
  onSelectStage,
  onEditStage,
  onDeleteStage,
  onTitleChange,
  onAddStage,
  children,
}: BuilderDndContextProps) {
  const [activeId, setActiveId] = React.useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      // Require a small movement to distinguish drag from click
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const stageIds = stages.map((s) => s.id);

  const activeStage = activeId != null ? stages.find((s) => s.id === activeId) ?? null : null;
  const activeIndex = activeStage ? stages.indexOf(activeStage) : -1;

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);

    if (!over || active.id === over.id) return;

    const fromIndex = stages.findIndex((s) => s.id === active.id);
    const toIndex = stages.findIndex((s) => s.id === over.id);
    if (fromIndex !== -1 && toIndex !== -1) {
      onReorder(fromIndex, toIndex);
    }
  }

  function handleDragCancel() {
    setActiveId(null);
  }

  const announcements = buildAnnouncements(stages);

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      modifiers={[restrictToVerticalAxis]}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
      accessibility={{ announcements }}
    >
      <SortableContext items={stageIds} strategy={verticalListSortingStrategy}>
        <div
          role="list"
          aria-label="Workflow stages"
          className="flex flex-col"
        >
          {stages.map((stage, index) => (
            <SortableStageItem
              key={stage.id}
              stage={stage}
              index={index}
              totalStages={stages.length}
              isSelected={selectedIndex === index}
              onSelect={onSelectStage}
              onEdit={onEditStage}
              onDelete={onDeleteStage}
              onTitleChange={onTitleChange}
              onAddAfter={onAddStage}
            />
          ))}
        </div>
      </SortableContext>

      {/* DragOverlay — renders a semi-transparent clone of the dragged card */}
      <DragOverlay modifiers={[restrictToVerticalAxis]}>
        {activeStage != null && (
          <div className="opacity-80 shadow-2xl rotate-1 scale-[1.02] pointer-events-none">
            <StageCard
              stage={activeStage}
              index={activeIndex}
              mode="edit"
              isSelected={false}
              // No drag handle props on overlay — it's purely visual
            />
          </div>
        )}
      </DragOverlay>

      {/* Additional content below the list (e.g. "Add Stage" button) */}
      {children}
    </DndContext>
  );
}
