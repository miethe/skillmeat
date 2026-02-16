'use client';

import { useDroppable } from '@dnd-kit/core';
import { Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface RemoveFromGroupDropZoneProps {
  /** Name of the current group, displayed in the drop zone label */
  groupName: string;
  /** Whether the poof animation is playing (post-drop visual feedback) */
  isPoofing?: boolean;
}

/**
 * Drop zone that appears at the top of the artifact pane when viewing a specific group.
 * Dragging an artifact onto it removes the artifact from that group.
 */
export function RemoveFromGroupDropZone({ groupName, isPoofing }: RemoveFromGroupDropZoneProps) {
  const { isOver, setNodeRef } = useDroppable({
    id: 'remove-from-group',
    data: { type: 'remove-zone' },
  });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'flex h-12 w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed transition-all',
        isOver
          ? 'scale-[1.02] border-destructive bg-destructive/10 text-destructive'
          : isPoofing
            ? 'border-destructive/50 bg-destructive/5 text-destructive'
            : 'border-muted-foreground/25 text-muted-foreground'
      )}
    >
      <Trash2
        className={cn('h-4 w-4 transition-transform', isOver && 'scale-110')}
        aria-hidden="true"
      />
      <span className="text-sm font-medium">
        Remove from {groupName}
      </span>
    </div>
  );
}
