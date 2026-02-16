/**
 * MiniArtifactCard Component
 *
 * Compact horizontal artifact card for the two-pane groups view.
 * Shows essential artifact info in a single row with drag-and-drop support.
 *
 * Layout: [drag-handle] [type-icon] [name | description] [group-badges] [type-badge]
 */

'use client';

import * as React from 'react';
import * as LucideIcons from 'lucide-react';
import { GripVertical } from 'lucide-react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';
import { getArtifactTypeConfig } from '@/types/artifact';
import { ArtifactGroupBadges } from '@/components/collection/artifact-group-badges';

// ============================================================================
// Types
// ============================================================================

/** Props passed to the drag handle element when used in a sortable context */
interface DragHandleProps {
  attributes: React.HTMLAttributes<HTMLDivElement>;
  listeners: Record<string, Function> | undefined;
}

export interface MiniArtifactCardProps {
  /** The artifact to display */
  artifact: Artifact;
  /** Click handler for opening detail view */
  onClick: () => void;
  /** Current group ID context (for badge scoping) */
  groupId?: string;
  /** Props for making the drag handle functional (provided by DraggableMiniArtifactCard) */
  dragHandleProps?: DragHandleProps;
  /** Additional CSS classes */
  className?: string;
}

export interface DraggableMiniArtifactCardProps {
  /** The artifact to display */
  artifact: Artifact;
  /** Click handler for opening detail view */
  onClick: () => void;
  /** Group ID used in sortable drag data */
  groupId: string;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// MiniArtifactCard (Presentational)
// ============================================================================

/**
 * MiniArtifactCard - Compact horizontal card for artifact display
 *
 * Renders a single-row card with type icon, name, truncated description,
 * group badges, and a type badge. Designed for dense list views.
 *
 * @example
 * ```tsx
 * <MiniArtifactCard
 *   artifact={artifact}
 *   onClick={() => openDetail(artifact)}
 *   groupId="group-123"
 * />
 * ```
 */
export const MiniArtifactCard = React.forwardRef<
  HTMLDivElement,
  MiniArtifactCardProps & Omit<React.HTMLAttributes<HTMLDivElement>, 'onClick'>
>(({ artifact, onClick, groupId, dragHandleProps, className, style, ...htmlProps }, ref) => {
    const config = getArtifactTypeConfig(artifact.type);

    // Resolve icon from lucide-react
    const iconName = config?.icon ?? 'FileText';
    const IconComponent = (
      LucideIcons as unknown as Record<string, React.ComponentType<{ className?: string }>>
    )[iconName];
    const Icon = IconComponent || LucideIcons.FileText;

    const handleClick = (e: React.MouseEvent) => {
      // Avoid triggering click when interacting with drag handle or badges
      const target = e.target as HTMLElement;
      if (target.closest('[data-drag-handle]') || target.closest('button')) {
        return;
      }
      onClick();
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick();
      }
    };

    return (
      <div
        ref={ref}
        className={cn(
          'flex items-center gap-2 rounded-md border bg-card px-3 py-2',
          'cursor-pointer transition-colors hover:bg-accent/50',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
          className
        )}
        style={style}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-label={`${artifact.name}, ${config?.label ?? artifact.type} artifact`}
        {...htmlProps}
      >
        {/* Drag handle */}
        <div
          data-drag-handle
          className={cn(
            'flex-shrink-0 text-muted-foreground',
            dragHandleProps && 'cursor-grab active:cursor-grabbing'
          )}
          aria-label={
            dragHandleProps
              ? `Drag ${artifact.name} to reorder or move between groups`
              : undefined
          }
          aria-hidden={!dragHandleProps}
          {...(dragHandleProps?.attributes ?? {})}
          {...(dragHandleProps?.listeners ?? {})}
        >
          <GripVertical className="h-4 w-4" />
        </div>

        {/* Type icon */}
        <Icon
          className={cn('h-4 w-4 flex-shrink-0', config?.color ?? 'text-muted-foreground')}
          aria-hidden="true"
        />

        {/* Name */}
        <span
          className="min-w-0 flex-shrink-0 truncate text-sm font-medium"
          title={artifact.name}
        >
          {artifact.name}
        </span>

        {/* Description */}
        {artifact.description && (
          <span
            className="hidden min-w-0 flex-1 truncate text-xs text-muted-foreground sm:inline"
            title={artifact.description}
          >
            {artifact.description}
          </span>
        )}

        {/* Spacer when no description visible */}
        <div className="flex-1 sm:hidden" />

        {/* Group badges (compact mode) */}
        <ArtifactGroupBadges
          artifactId={artifact.id}
          collectionId={artifact.collections?.[0]?.id}
          maxVisible={2}
          compact
          className="flex-shrink-0"
        />

        {/* Type badge */}
        <Badge variant="secondary" className="flex-shrink-0 text-[11px]">
          {config?.label ?? artifact.type}
        </Badge>
      </div>
    );
  }
);

MiniArtifactCard.displayName = 'MiniArtifactCard';

// ============================================================================
// DraggableMiniArtifactCard (DnD Wrapper)
// ============================================================================

/**
 * DraggableMiniArtifactCard - Drag-and-drop wrapper around MiniArtifactCard
 *
 * Uses @dnd-kit/sortable for drag-and-drop reordering and movement
 * between groups. Attaches sortable data for group context and passes
 * drag handle props to MiniArtifactCard.
 *
 * @example
 * ```tsx
 * <SortableContext items={artifactIds} strategy={verticalListSortingStrategy}>
 *   {artifacts.map((artifact) => (
 *     <DraggableMiniArtifactCard
 *       key={artifact.id}
 *       artifact={artifact}
 *       groupId="group-123"
 *       onClick={() => openDetail(artifact)}
 *     />
 *   ))}
 * </SortableContext>
 * ```
 */
export function DraggableMiniArtifactCard({
  artifact,
  groupId,
  onClick,
  className,
}: DraggableMiniArtifactCardProps) {
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
      artifactId: artifact.id,
      groupId,
    },
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  return (
    <MiniArtifactCard
      ref={setNodeRef}
      style={style}
      artifact={artifact}
      onClick={onClick}
      groupId={groupId}
      dragHandleProps={{ attributes, listeners }}
      className={cn(isDragging && 'border-dashed', className)}
    />
  );
}
