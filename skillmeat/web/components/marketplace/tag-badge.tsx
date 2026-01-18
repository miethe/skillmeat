/**
 * Tag Badge Component
 *
 * Displays tags as colored badges with overflow handling.
 * Shows "+n more" when tags exceed maxDisplay, with tooltip revealing all tags.
 *
 * Color coding uses a deterministic hash to assign consistent colors per tag.
 */

'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface TagBadgeProps {
  /** Array of tag strings to display */
  tags: string[];
  /** Maximum number of tags to display before showing "+n more" */
  maxDisplay?: number;
  /** Callback when a tag is clicked */
  onTagClick?: (tag: string) => void;
  /** Additional CSS classes for the container */
  className?: string;
}

// ============================================================================
// Color Utilities
// ============================================================================

/**
 * Predefined color palette for tags.
 * Selected for WCAG AA contrast compliance with both light and dark text.
 */
const TAG_COLORS = [
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#d946ef', // Fuchsia
  '#ec4899', // Pink
  '#f43f5e', // Rose
  '#ef4444', // Red
  '#f97316', // Orange
  '#eab308', // Yellow
  '#84cc16', // Lime
  '#22c55e', // Green
  '#14b8a6', // Teal
  '#06b6d4', // Cyan
  '#0ea5e9', // Sky
  '#3b82f6', // Blue
] as const;

/**
 * Generate a deterministic hash from a string.
 * Used to consistently assign colors to tags.
 */
function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash);
}

/**
 * Get a consistent color for a tag based on its name.
 */
function getTagColor(tag: string): string {
  const hash = hashString(tag.toLowerCase());
  return TAG_COLORS[hash % TAG_COLORS.length];
}

// ============================================================================
// Sub-components
// ============================================================================

interface SingleTagBadgeProps {
  tag: string;
  onClick?: (tag: string) => void;
}

function SingleTagBadge({ tag, onClick }: SingleTagBadgeProps) {
  const color = getTagColor(tag);
  const isClickable = !!onClick;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClick?.(tag);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      e.stopPropagation();
      onClick?.(tag);
    }
  };

  return (
    <Badge
      colorStyle={color}
      className={cn(
        'text-xs',
        isClickable && 'cursor-pointer hover:opacity-80 transition-opacity'
      )}
      onClick={isClickable ? handleClick : undefined}
      onKeyDown={isClickable ? handleKeyDown : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      aria-label={isClickable ? `Filter by tag: ${tag}` : `Tag: ${tag}`}
    >
      {tag}
    </Badge>
  );
}

interface OverflowBadgeProps {
  hiddenTags: string[];
  onTagClick?: (tag: string) => void;
}

function OverflowBadge({ hiddenTags, onTagClick }: OverflowBadgeProps) {
  const count = hiddenTags.length;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="secondary"
            className="text-xs cursor-default"
            aria-label={`${count} more tags: ${hiddenTags.join(', ')}`}
          >
            +{count} more
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <div className="flex flex-wrap gap-1">
            {hiddenTags.map((tag) => (
              <SingleTagBadge key={tag} tag={tag} onClick={onTagClick} />
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function TagBadge({
  tags,
  maxDisplay = 3,
  onTagClick,
  className,
}: TagBadgeProps) {
  // Handle empty tags array gracefully
  if (!tags || tags.length === 0) {
    return null;
  }

  const visibleTags = tags.slice(0, maxDisplay);
  const hiddenTags = tags.slice(maxDisplay);
  const hasOverflow = hiddenTags.length > 0;

  return (
    <div
      className={cn('flex flex-wrap items-center gap-1', className)}
      role="list"
      aria-label="Tags"
    >
      {visibleTags.map((tag) => (
        <div key={tag} role="listitem">
          <SingleTagBadge tag={tag} onClick={onTagClick} />
        </div>
      ))}
      {hasOverflow && (
        <div role="listitem">
          <OverflowBadge hiddenTags={hiddenTags} onTagClick={onTagClick} />
        </div>
      )}
    </div>
  );
}
