/**
 * Group Badge Row Component
 *
 * Displays group membership badges on artifact cards when viewing a specific collection.
 * Shows overflow indicator with tooltip for groups exceeding maxBadges limit.
 *
 * @example Basic usage
 * ```tsx
 * <GroupBadgeRow
 *   groups={[
 *     { id: '1', name: 'Priority Tasks' },
 *     { id: '2', name: 'Review Queue' },
 *     { id: '3', name: 'Archive' }
 *   ]}
 * />
 * // Renders: [Priority Tasks] [Review Queue] [+1 more...]
 * ```
 *
 * @example With custom maxBadges
 * ```tsx
 * <GroupBadgeRow groups={groups} maxBadges={3} />
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

export interface GroupInfo {
  /** Unique identifier for the group */
  id: string;
  /** Display name of the group */
  name: string;
}

export interface GroupBadgeRowProps {
  /** Array of groups the artifact belongs to */
  groups: GroupInfo[];
  /** Maximum number of badges to display before showing overflow (default: 2) */
  maxBadges?: number;
  /** Additional CSS classes for the container */
  className?: string;
}

// ============================================================================
// Sub-components
// ============================================================================

interface GroupBadgeProps {
  group: GroupInfo;
}

/**
 * Single group badge with accessibility support.
 * Uses outline variant to distinguish from collection badges (which use secondary).
 */
function GroupBadge({ group }: GroupBadgeProps) {
  return (
    <Badge
      variant="outline"
      className="max-w-[120px] truncate text-xs"
      aria-label={`In group: ${group.name}`}
      tabIndex={0}
    >
      {group.name}
    </Badge>
  );
}

interface OverflowBadgeProps {
  /** Groups that are hidden due to overflow */
  hiddenGroups: GroupInfo[];
}

/**
 * Overflow badge showing count of additional groups with tooltip.
 */
function OverflowBadge({ hiddenGroups }: OverflowBadgeProps) {
  const count = hiddenGroups.length;
  const groupNames = hiddenGroups.map((g) => g.name).join(', ');

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className="cursor-default text-xs"
            aria-label={`${count} more groups: ${groupNames}`}
            tabIndex={0}
          >
            +{count} more...
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <ul className="space-y-1">
            {hiddenGroups.map((group) => (
              <li key={group.id} className="text-sm">
                {group.name}
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
 * GroupBadgeRow - Display group membership badges
 *
 * Shows badges for groups with overflow handling.
 * Uses outline variant to visually distinguish from collection badges.
 *
 * @param groups - Array of group objects with id and name
 * @param maxBadges - Maximum badges to show before overflow indicator (default: 2)
 * @param className - Additional CSS classes for the container
 */
export function GroupBadgeRow({
  groups,
  maxBadges = 2,
  className,
}: GroupBadgeRowProps) {
  // Handle edge cases
  const validGroups = React.useMemo(() => {
    if (!groups || !Array.isArray(groups)) {
      return [];
    }
    return groups.filter((g) => g && g.id && g.name);
  }, [groups]);

  // Return null if no groups to display
  if (validGroups.length === 0) {
    return null;
  }

  const visibleGroups = validGroups.slice(0, maxBadges);
  const hiddenGroups = validGroups.slice(maxBadges);
  const hasOverflow = hiddenGroups.length > 0;

  return (
    <div
      className={cn('inline-flex flex-wrap items-center gap-1', className)}
      role="list"
      aria-label="Group memberships"
    >
      {visibleGroups.map((group) => (
        <div key={group.id} role="listitem">
          <GroupBadge group={group} />
        </div>
      ))}
      {hasOverflow && (
        <div role="listitem">
          <OverflowBadge hiddenGroups={hiddenGroups} />
        </div>
      )}
    </div>
  );
}
