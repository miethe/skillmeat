'use client';

/**
 * GroupsDisplay Component
 *
 * Displays an artifact's group membership within a specific collection.
 * Uses useArtifactGroups hook to fetch groups and handles loading/empty/error states.
 *
 * @example
 * ```tsx
 * <GroupsDisplay
 *   collectionId="collection-123"
 *   artifactId="artifact-456"
 * />
 * ```
 */

import { useArtifactGroups } from '@/hooks';
import { Skeleton } from '@/components/ui/skeleton';
import { GroupBadgeRow, type GroupInfo } from '@/components/shared/group-badge-row';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface GroupsDisplayProps {
  /** Collection ID to scope the group lookup */
  collectionId: string;
  /** Artifact ID to find groups for */
  artifactId: string;
  /** Maximum number of badges to show before overflow (default: 3) */
  maxBadges?: number;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Inline skeleton for loading state
 */
function GroupsDisplaySkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-1', className)}>
      <Skeleton className="h-5 w-16 rounded-full" />
      <Skeleton className="h-5 w-20 rounded-full" />
    </div>
  );
}

/**
 * Empty state when artifact has no groups
 */
function GroupsDisplayEmpty({ className }: { className?: string }) {
  return (
    <span className={cn('text-xs text-muted-foreground italic', className)}>
      No groups
    </span>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * GroupsDisplay - Show artifact's group membership in a collection
 *
 * Fetches groups via useArtifactGroups hook and displays them as badges.
 * Handles loading, empty, and error states gracefully.
 *
 * @param collectionId - Collection ID to scope the group lookup
 * @param artifactId - Artifact ID to find groups for
 * @param maxBadges - Maximum badges to show (default: 3)
 * @param className - Additional CSS classes for the container
 */
export function GroupsDisplay({
  collectionId,
  artifactId,
  maxBadges = 3,
  className,
}: GroupsDisplayProps) {
  const { data: groups, isLoading, error } = useArtifactGroups(artifactId, collectionId);

  // Loading state - show skeleton
  if (isLoading) {
    return <GroupsDisplaySkeleton className={className} />;
  }

  // Error state - gracefully skip render
  // The hook already logs errors and returns empty array on failure
  if (error) {
    return null;
  }

  // Empty state - show "No groups" message
  if (!groups || groups.length === 0) {
    return <GroupsDisplayEmpty className={className} />;
  }

  // Map groups to GroupInfo format for GroupBadgeRow
  const groupInfos: GroupInfo[] = groups.map((group) => ({
    id: group.id,
    name: group.name,
  }));

  // Success state - render badges using GroupBadgeRow
  return (
    <GroupBadgeRow
      groups={groupInfos}
      maxBadges={maxBadges}
      className={className}
    />
  );
}
