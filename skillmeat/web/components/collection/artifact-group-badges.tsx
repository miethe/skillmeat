/**
 * ArtifactGroupBadges Component
 *
 * Displays group membership badges for an artifact in the collection grid view.
 * Shows colored badges with group icons, with overflow handling and tooltips.
 *
 * @example Basic usage
 * ```tsx
 * <ArtifactGroupBadges
 *   artifactId="skill:canvas-design"
 *   collectionId="abc-123"
 *   maxVisible={3}
 * />
 * ```
 *
 * @example Compact mode (icon-only with tooltips)
 * ```tsx
 * <ArtifactGroupBadges
 *   artifactId="skill:canvas-design"
 *   collectionId="abc-123"
 *   compact
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { Plus } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useArtifactGroups } from '@/hooks';
import { resolveColorHex, ICON_MAP, COLOR_HEX_BY_TOKEN } from '@/lib/group-constants';
import type { GroupIcon } from '@/lib/group-constants';
import type { Group } from '@/types/groups';

// ============================================================================
// Types
// ============================================================================

export interface ArtifactGroupBadgesProps {
  /** Artifact ID to fetch groups for */
  artifactId: string;
  /** Collection ID to scope the group query */
  collectionId: string | undefined;
  /** Maximum number of badges to display before overflow (default: 3) */
  maxVisible?: number;
  /** Icon-only mode with name shown in tooltip (default: false) */
  compact?: boolean;
  /** When provided, renders a '+' button after the badges to add to a group */
  onAddToGroup?: () => void;
  /** Handler when a group badge is clicked (for filtering) */
  onGroupClick?: (groupId: string) => void;
  /** Additional CSS classes for the container */
  className?: string;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_COLOR_HEX = COLOR_HEX_BY_TOKEN.slate;
const ICON_SIZE = 'h-3 w-3';

// ============================================================================
// Sub-components
// ============================================================================

interface GroupBadgeItemProps {
  group: Group;
  compact: boolean;
  onClick?: (groupId: string) => void;
}

/**
 * Single group badge with color, icon, and optional tooltip for compact mode.
 */
function GroupBadgeItem({ group, compact, onClick }: GroupBadgeItemProps) {
  const colorHex = group.color ? resolveColorHex(group.color) : DEFAULT_COLOR_HEX;
  const IconComponent = group.icon ? ICON_MAP[group.icon as GroupIcon] : null;

  const badge = (
    <Badge
      colorStyle={colorHex}
      className={cn(
        'px-1.5 py-0 text-[11px]',
        onClick && 'cursor-pointer hover:ring-2 hover:ring-ring hover:ring-offset-1 transition-all'
      )}
      aria-label={`Group: ${group.name}`}
      onClick={onClick ? (e) => {
        e.stopPropagation();
        onClick(group.id);
      } : undefined}
    >
      {IconComponent && <IconComponent className={cn(ICON_SIZE, !compact && 'mr-1')} aria-hidden="true" />}
      {!compact && <span className="truncate">{group.name}</span>}
    </Badge>
  );

  if (compact) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{badge}</TooltipTrigger>
          <TooltipContent>
            <p className="text-sm">{group.name}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return badge;
}

interface OverflowBadgeProps {
  groups: Group[];
}

/**
 * Overflow indicator badge showing count of additional groups with tooltip.
 */
function OverflowBadge({ groups }: OverflowBadgeProps) {
  const count = groups.length;
  const groupNames = groups.map((g) => g.name).join(', ');

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className="cursor-default px-1.5 py-0 text-[11px]"
            aria-label={`${count} more groups: ${groupNames}`}
          >
            +{count}
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <ul className="space-y-1">
            {groups.map((group) => (
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
 * ArtifactGroupBadges - Display group membership badges for an artifact
 *
 * Fetches groups for the given artifact and renders colored badges with icons.
 * Returns null when there are no groups or data is still loading.
 *
 * @param artifactId - The artifact to show groups for
 * @param collectionId - The collection to scope group queries
 * @param maxVisible - Maximum badges before overflow indicator (default: 3)
 * @param compact - Icon-only mode with tooltips (default: false)
 * @param className - Additional CSS classes
 */
export function ArtifactGroupBadges({
  artifactId,
  collectionId,
  maxVisible = 3,
  compact = false,
  onAddToGroup,
  onGroupClick,
  className,
}: ArtifactGroupBadgesProps) {
  const { data: groups, isLoading } = useArtifactGroups(artifactId, collectionId);

  // Render nothing when loading or no groups (unless we have the add button)
  if (isLoading || (!groups || groups.length === 0)) {
    if (!onAddToGroup) return null;
    // Show just the add button when no groups exist
    return (
      <div className={cn('flex items-center gap-1 overflow-hidden', className)}>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5 rounded-full"
                onClick={(e) => {
                  e.stopPropagation();
                  onAddToGroup();
                }}
                aria-label="Add to group"
              >
                <Plus className="h-3 w-3" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Add to Group</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    );
  }

  const visibleGroups = groups.slice(0, maxVisible);
  const overflowGroups = groups.slice(maxVisible);

  return (
    <div
      className={cn('flex items-center gap-1 overflow-hidden py-0.5', className)}
      role="list"
      aria-label="Group memberships"
    >
      {visibleGroups.map((group) => (
        <div key={group.id} role="listitem" className="flex-shrink-0">
          <GroupBadgeItem group={group} compact={compact} onClick={onGroupClick} />
        </div>
      ))}
      {overflowGroups.length > 0 && (
        <div role="listitem" className="flex-shrink-0">
          <OverflowBadge groups={overflowGroups} />
        </div>
      )}
      {onAddToGroup && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5 flex-shrink-0 rounded-full"
                onClick={(e) => {
                  e.stopPropagation();
                  onAddToGroup();
                }}
                aria-label="Add to group"
              >
                <Plus className="h-3 w-3" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Add to Group</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}
