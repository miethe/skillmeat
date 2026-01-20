/**
 * Collection Badge Stack Component
 *
 * Displays collection membership badges on artifact cards.
 * Filters out the default collection and shows overflow indicator for many collections.
 *
 * @example Basic usage
 * ```tsx
 * <CollectionBadgeStack
 *   collections={[
 *     { id: '1', name: 'Work', is_default: false },
 *     { id: '2', name: 'Personal', is_default: false },
 *     { id: '3', name: 'Archive', is_default: false },
 *     { id: 'default', name: 'Default', is_default: true }
 *   ]}
 * />
 * // Renders: [Work] [Personal] [+1 more...]
 * ```
 *
 * @example With custom maxBadges
 * ```tsx
 * <CollectionBadgeStack collections={collections} maxBadges={3} />
 * ```
 */

'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface CollectionInfo {
  /** Unique identifier for the collection */
  id: string;
  /** Display name of the collection */
  name: string;
  /** Whether this is the default collection (filtered out from display) */
  is_default?: boolean;
}

export interface CollectionBadgeStackProps {
  /** Array of collections the artifact belongs to */
  collections: CollectionInfo[];
  /** Maximum number of badges to display before showing overflow (default: 2) */
  maxBadges?: number;
  /** Additional CSS classes for the container */
  className?: string;
}

// ============================================================================
// Sub-components
// ============================================================================

interface CollectionBadgeProps {
  collection: CollectionInfo;
}

/**
 * Single collection badge with accessibility support.
 */
function CollectionBadge({ collection }: CollectionBadgeProps) {
  return (
    <Badge
      variant="secondary"
      className="max-w-[120px] truncate text-xs"
      aria-label={`In collection: ${collection.name}`}
      tabIndex={0}
    >
      {collection.name}
    </Badge>
  );
}

interface OverflowBadgeProps {
  /** Collections that are hidden due to overflow */
  hiddenCollections: CollectionInfo[];
}

/**
 * Overflow badge showing count of additional collections with tooltip.
 */
function OverflowBadge({ hiddenCollections }: OverflowBadgeProps) {
  const count = hiddenCollections.length;
  const collectionNames = hiddenCollections.map((c) => c.name).join(', ');

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="secondary"
            className="cursor-default text-xs"
            aria-label={`${count} more collections: ${collectionNames}`}
            tabIndex={0}
          >
            +{count} more...
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <ul className="space-y-1">
            {hiddenCollections.map((collection) => (
              <li key={collection.id} className="text-sm">
                {collection.name}
              </li>
            ))}
          </ul>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * CollectionBadgeStack - Display collection membership badges
 *
 * Shows badges for non-default collections with overflow handling.
 * Default collections (where is_default is true) are automatically filtered out.
 *
 * @param collections - Array of collection objects with id, name, and optional is_default
 * @param maxBadges - Maximum badges to show before overflow indicator (default: 2)
 * @param className - Additional CSS classes for the container
 */
export function CollectionBadgeStack({
  collections,
  maxBadges = 2,
  className,
}: CollectionBadgeStackProps) {
  // Filter out default collection and handle edge cases
  const nonDefaultCollections = React.useMemo(() => {
    if (!collections || !Array.isArray(collections)) {
      return [];
    }
    return collections.filter((c) => c && !c.is_default);
  }, [collections]);

  // Return null if no collections to display
  if (nonDefaultCollections.length === 0) {
    return null;
  }

  const visibleCollections = nonDefaultCollections.slice(0, maxBadges);
  const hiddenCollections = nonDefaultCollections.slice(maxBadges);
  const hasOverflow = hiddenCollections.length > 0;

  return (
    <div
      className={cn('inline-flex flex-wrap items-center gap-1', className)}
      role="list"
      aria-label="Collection memberships"
    >
      {visibleCollections.map((collection) => (
        <div key={collection.id} role="listitem">
          <CollectionBadge collection={collection} />
        </div>
      ))}
      {hasOverflow && (
        <div role="listitem">
          <OverflowBadge hiddenCollections={hiddenCollections} />
        </div>
      )}
    </div>
  );
}
