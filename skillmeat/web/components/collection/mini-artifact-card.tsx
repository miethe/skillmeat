/**
 * MiniArtifactCard Component
 *
 * Compact vertical artifact card for grid layouts in the two-pane groups view.
 * Shows type indicator, name, description, group badges, and tags in a
 * card designed to fit multiple per row.
 *
 * Layout:
 * +--+---------------------------+
 * |C |  ARTIFACT TYPE            |
 * |O |  Artifact Name            |
 * |L |                           |
 * |O |  Description text that    |
 * |R |  can span multiple lines  |
 * |  |  before truncating...     |
 * |B |                           |
 * |A |  [Group1] [Group2]        |
 * |R |  [tag1] [tag2] [+N more]  |
 * +--+---------------------------+
 */

'use client';

import * as React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import * as LucideIcons from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { Artifact, ArtifactType } from '@/types/artifact';
import { getArtifactTypeConfig } from '@/types/artifact';
import { ArtifactGroupBadges } from '@/components/collection/artifact-group-badges';
import { getTagColor } from '@/lib/utils/tag-colors';
import { useTags } from '@/hooks';

// ============================================================================
// Type color bar mapping
// ============================================================================

/** Left border color classes per artifact type */
const typeBarColors: Record<ArtifactType, string> = {
  skill: 'border-l-purple-500',
  command: 'border-l-blue-500',
  agent: 'border-l-green-500',
  mcp: 'border-l-orange-500',
  hook: 'border-l-pink-500',
};

// ============================================================================
// Types
// ============================================================================

export interface MiniArtifactCardProps {
  /** The artifact to display */
  artifact: Artifact;
  /** Click handler for opening detail view */
  onClick: () => void;
  /** Current group ID context (for badge scoping) */
  groupId?: string;
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
 * MiniArtifactCard - Compact vertical card for artifact display in grid layouts
 *
 * Renders a card with a colored left type bar, type label, name, description,
 * group badges, and tag badges. Designed for dense grid views where multiple
 * cards fit per row.
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
>(({ artifact, onClick, groupId, className, style, ...htmlProps }, ref) => {
  const config = getArtifactTypeConfig(artifact.type);

  // Fetch all tags to build a name->color map from DB
  const { data: allTagsResponse } = useTags(100);
  const dbTagColorMap = React.useMemo(() => {
    const map = new Map<string, string>();
    if (allTagsResponse?.items) {
      for (const tag of allTagsResponse.items) {
        if (tag.color) {
          map.set(tag.name, tag.color);
        }
      }
    }
    return map;
  }, [allTagsResponse?.items]);

  /** Resolve tag color: prefer DB color, fall back to hash-based color */
  const resolveTagColor = (tagName: string): string => {
    return dbTagColorMap.get(tagName) || getTagColor(tagName);
  };

  // Tag display: sort, limit to 3 visible, count overflow
  const displayTags = (artifact.tags ?? []).sort((a, b) => a.localeCompare(b));
  const visibleTags = displayTags.slice(0, 3);
  const remainingTagsCount = displayTags.length - visibleTags.length;

  const handleClick = (e: React.MouseEvent) => {
    // Avoid triggering click when interacting with badges or buttons
    const target = e.target as HTMLElement;
    if (target.closest('button')) {
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

  // Get the icon component from Lucide
  const iconName = config?.icon ?? 'FileText';
  const IconComponent = (
    LucideIcons as unknown as Record<string, React.ComponentType<{ className?: string }>>
  )[iconName];
  const Icon = IconComponent || LucideIcons.FileText;

  return (
    <div
      ref={ref}
      className={cn(
        'flex w-full min-h-[140px] flex-col rounded-lg border border-l-[3px] bg-card p-3',
        'cursor-grab shadow-sm transition-shadow hover:shadow-md',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
        typeBarColors[artifact.type],
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
      {/* Type icon + Artifact name (single line) */}
      <div className="flex items-center gap-1.5">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="flex-shrink-0">
                <Icon
                  className={cn('h-4 w-4', config?.color ?? 'text-muted-foreground')}
                  aria-hidden="true"
                />
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <p>{config?.label ?? artifact.type}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        <span
          className="truncate text-sm font-medium leading-tight"
          title={artifact.name}
        >
          {artifact.name}
        </span>
      </div>

      {/* Description zone - fixed height, 3-line clamp */}
      <div className="mt-1 h-[42px]">
        {artifact.description ? (
          <p
            className="line-clamp-3 text-xs leading-[14px] text-muted-foreground"
            title={artifact.description}
          >
            {artifact.description}
          </p>
        ) : (
          <p className="text-xs italic text-muted-foreground/60">
            No description
          </p>
        )}
      </div>

      {/* Spacer to push badges to bottom */}
      <div className="flex-1" />

      {/* Group badges (with names visible) */}
      <ArtifactGroupBadges
        artifactId={artifact.id}
        collectionId={artifact.collections?.[0]?.id}
        maxVisible={2}
        className="mt-1"
      />

      {/* Tag badges */}
      {displayTags.length > 0 && (
        <div
          className="mt-1 flex flex-wrap items-center gap-1"
          role="list"
          aria-label="Tags"
        >
          {visibleTags.map((tag) => (
            <Badge
              key={tag}
              colorStyle={resolveTagColor(tag)}
              className="px-1.5 py-0 text-[10px]"
              role="listitem"
            >
              {tag}
            </Badge>
          ))}
          {remainingTagsCount > 0 && (
            <Badge
              variant="secondary"
              className="px-1.5 py-0 text-[10px]"
              aria-label={`${remainingTagsCount} more tags`}
            >
              +{remainingTagsCount} more
            </Badge>
          )}
        </div>
      )}
    </div>
  );
});

MiniArtifactCard.displayName = 'MiniArtifactCard';

// ============================================================================
// DraggableMiniArtifactCard (DnD Wrapper)
// ============================================================================

/**
 * DraggableMiniArtifactCard - Drag-and-drop wrapper around MiniArtifactCard
 *
 * Uses @dnd-kit/sortable for drag-and-drop reordering and movement
 * between groups. The entire card is the drag surface (no separate handle).
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
      className={cn(
        isDragging && 'border-dashed cursor-grabbing',
        className
      )}
      {...attributes}
      {...listeners}
    />
  );
}
