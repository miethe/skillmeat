/**
 * Unified Card Component
 *
 * A flexible card component that works with both Entity and Artifact types.
 * Uses the ArtifactCard visual style (colored borders, metadata-rich layout) everywhere.
 *
 * Design decisions:
 * - Type guards detect Entity vs Artifact at runtime
 * - Normalizes flat (Entity) and nested (Artifact) property access
 * - Unified ArtifactCard-style appearance on all pages
 * - Conditionally renders selection features (checkboxes) when enabled
 * - Conditionally renders entity actions (edit, delete, etc.) for Entity types
 */

'use client';

import * as React from 'react';
import * as LucideIcons from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { apiRequest } from '@/lib/api';
import type { Artifact, ArtifactType, SyncStatus } from '@/types/artifact';
import { getArtifactTypeConfig } from '@/types/artifact';

// Entity is now an alias for Artifact - use Artifact directly
type Entity = Artifact;
type EntityType = ArtifactType;

// Legacy Artifact interface for backward compatibility with old API responses
interface LegacyArtifact {
  id: string;
  name: string;
  type: ArtifactType;
  version?: string;
  source?: string;
  status?: string;
  updatedAt?: string;
  metadata: {
    title?: string;
    description?: string;
    tags?: string[];
  };
  usageStats: {
    usageCount: number;
  };
  upstreamStatus: {
    isOutdated: boolean;
  };
  score?: {
    confidence?: number;
  };
}
import { UnifiedCardActions } from './unified-card-actions';
import type { ArtifactDiffResponse } from '@/sdk';
import { ScoreBadge, ScoreBadgeSkeleton } from '@/components/ScoreBadge';
import { CollectionBadgeStack, type CollectionInfo } from './collection-badge-stack';
import { GroupBadgeRow, type GroupInfo } from './group-badge-row';
import { useCollectionContext } from '@/hooks';

/**
 * Type guard to check if item is a new unified Artifact (flat structure)
 */
function isUnifiedArtifact(item: Artifact | LegacyArtifact): item is Artifact {
  // New unified artifacts have syncStatus instead of nested metadata
  return 'syncStatus' in item;
}

/**
 * Type guard to check if item is an Entity (legacy alias, now same as Artifact)
 */
function isEntity(item: Artifact | LegacyArtifact): item is Artifact {
  return isUnifiedArtifact(item);
}

/**
 * Type guard to check if item is a legacy Artifact with nested metadata
 */
function isLegacyArtifact(item: Artifact | LegacyArtifact): item is LegacyArtifact {
  return 'metadata' in item && 'usageStats' in item && !('syncStatus' in item);
}

/**
 * Normalized card data extracted from either Entity or Artifact
 */
interface NormalizedCardData {
  id: string;
  name: string;
  type: EntityType | ArtifactType;
  title?: string;
  description?: string;
  tags?: string[];
  status?: SyncStatus;
  version?: string;
  source?: string;
  updatedAt?: string;
  usageCount?: number;
  projectPath?: string;
  collection?: string;
  isOutdated?: boolean;
  confidence?: number;
}

/**
 * Extract normalized data from Entity or Artifact (supports both unified and legacy formats)
 */
function normalizeCardData(item: Artifact | LegacyArtifact): NormalizedCardData {
  if (isLegacyArtifact(item)) {
    // Legacy Artifact has nested metadata
    return {
      id: item.id,
      name: item.name,
      type: item.type,
      title: item.metadata.title,
      description: item.metadata.description,
      tags: item.metadata?.tags,
      status: item.status as SyncStatus | undefined,
      version: item.version,
      source: item.source,
      updatedAt: item.updatedAt,
      usageCount: item.usageStats.usageCount,
      isOutdated: item.upstreamStatus.isOutdated,
      confidence: item.score?.confidence,
    };
  } else {
    // Unified Artifact has flat properties (tags at top level)
    return {
      id: item.id,
      name: item.name,
      type: item.type,
      title: undefined, // Unified artifacts don't have separate title
      description: item.description,
      tags: item.tags,
      status: item.syncStatus,
      version: item.version,
      source: item.source,
      updatedAt: item.updatedAt || item.modifiedAt,
      projectPath: item.projectPath,
      collection: item.collection,
      usageCount: item.usageStats?.usageCount,
      isOutdated: item.upstream?.updateAvailable,
      confidence: item.score?.confidence,
    };
  }
}

/**
 * Props for UnifiedCard component
 */
export interface UnifiedCardProps {
  /** The item to display (Artifact - Entity is now an alias for Artifact) */
  item: Artifact | LegacyArtifact;
  /** Whether the card is currently selected (when selectable is true) */
  selected?: boolean;
  /** Whether the item can be selected (shows checkbox) */
  selectable?: boolean;
  /** Callback when selection state changes */
  onSelect?: (selected: boolean) => void;
  /** Callback when card is clicked */
  onClick?: () => void;
  /** Callback for edit action (Entity types only, shows in actions menu) */
  onEdit?: () => void;
  /** Callback for delete action (Entity types only, shows in actions menu) */
  onDelete?: () => void;
  /** Callback for deploy action (Entity types only, shows in actions menu) */
  onDeploy?: () => void;
  /** Callback for sync action (Entity types only, shows in actions menu) */
  onSync?: () => void;
  /** Callback to view diff (Entity types only, shows in actions menu) */
  onViewDiff?: () => void;
  /** Callback to rollback (Entity types only, shows in actions menu) */
  onRollback?: () => void;
  /** Callback for copying CLI command to clipboard */
  onCopyCliCommand?: () => void;
  /** @deprecated mode prop is no longer used - visual style is now unified */
  mode?: 'selection' | 'browse';
}

// Enhanced type colors for better visual differentiation
const artifactTypeBorderAccents: Record<EntityType | ArtifactType, string> = {
  skill: 'border-l-blue-500',
  command: 'border-l-purple-500',
  agent: 'border-l-green-500',
  mcp: 'border-l-orange-500',
  hook: 'border-l-pink-500',
};

const artifactTypeCardTints: Record<EntityType | ArtifactType, string> = {
  skill: 'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]',
  command: 'bg-purple-500/[0.02] dark:bg-purple-500/[0.03]',
  agent: 'bg-green-500/[0.02] dark:bg-green-500/[0.03]',
  mcp: 'bg-orange-500/[0.02] dark:bg-orange-500/[0.03]',
  hook: 'bg-pink-500/[0.02] dark:bg-pink-500/[0.03]',
};

const statusColors: Record<string, string> = {
  synced: 'text-green-500',
  modified: 'text-yellow-500',
  outdated: 'text-orange-500',
  conflict: 'text-red-500',
  active: 'bg-green-500/10 text-green-600 border-green-500/20',
  error: 'bg-red-500/10 text-red-600 border-red-500/20',
};

const statusLabels: Record<string, string> = {
  synced: 'Synced',
  modified: 'Modified',
  outdated: 'Outdated',
  conflict: 'Conflict',
  active: 'Active',
  error: 'Error',
};

/**
 * UnifiedCard - Universal card component for Entity and Artifact types
 *
 * Automatically detects the type of item and renders appropriately.
 * Uses the ArtifactCard visual style (colored borders, metadata display) everywhere.
 * Conditionally shows checkboxes and actions based on props.
 *
 * @example With selection (for /manage)
 * ```tsx
 * <UnifiedCard
 *   item={entity}
 *   selected={true}
 *   selectable={true}
 *   onSelect={(checked) => updateSelection(checked)}
 *   onClick={() => openDetail(entity)}
 *   onEdit={() => startEdit(entity)}
 * />
 * ```
 *
 * @example Without selection (for /collection)
 * ```tsx
 * <UnifiedCard
 *   item={artifact}
 *   onClick={() => openDetail(artifact)}
 * />
 * ```
 */
export const UnifiedCard = React.memo(
  function UnifiedCard({
    item,
    selected = false,
    selectable = false,
    onSelect,
    onClick,
    onEdit,
    onDelete,
    onDeploy,
    onSync,
    onViewDiff,
    onRollback,
    onCopyCliCommand,
    mode, // Deprecated but kept for backward compatibility
  }: UnifiedCardProps) {
    const queryClient = useQueryClient();
    const { selectedCollectionId } = useCollectionContext();
    const data = normalizeCardData(item);
    const config = getArtifactTypeConfig(data.type as ArtifactType);

    // Determine if we're in "All Collections" view (null or 'all')
    const isAllCollectionsView = !selectedCollectionId || selectedCollectionId === 'all';

    // Extract collections from the item for badge display
    // Both Entity and Artifact types can have collections
    const itemCollections = React.useMemo((): CollectionInfo[] => {
      if (!isAllCollectionsView) return [];

      // Check if item has collections array
      const collectionsArray = (item as Artifact).collections;
      if (!collectionsArray || !Array.isArray(collectionsArray)) return [];

      return collectionsArray.map((c) => ({
        id: c.id,
        name: c.name,
        // Mark default collection to be filtered by CollectionBadgeStack
        is_default: c.id === 'default' || c.name === 'Default',
      }));
    }, [item, isAllCollectionsView]);

    // Extract groups from the item for badge display
    // Groups are only shown when viewing a specific collection (opposite of collections)
    const itemGroups = React.useMemo((): GroupInfo[] => {
      // Only show groups in specific collection view, not "All Collections"
      if (isAllCollectionsView) return [];

      // Check if item has groups array (populated when include_groups=true from backend)
      // Groups may exist on artifact responses when viewing a specific collection
      const itemWithGroups = item as Artifact & {
        groups?: { id: string; name: string }[];
      };
      const groupsArray = itemWithGroups.groups;
      if (!groupsArray || !Array.isArray(groupsArray)) return [];

      return groupsArray.map((g) => ({
        id: g.id,
        name: g.name,
      }));
    }, [item, isAllCollectionsView]);

    // Type-safe icon lookup with fallback (config may be undefined for unknown types)
    const iconName = config?.icon ?? 'FileText';
    const IconComponent = (LucideIcons as any)[iconName] as
      | React.ComponentType<{ className?: string }>
      | undefined;
    const Icon = IconComponent || LucideIcons.FileText;

    const handleCardClick = (e: React.MouseEvent) => {
      // Don't trigger onClick if clicking on checkbox or actions menu
      const target = e.target as HTMLElement;

      // Ignore clicks on checkboxes
      if (target.closest('[role="checkbox"]')) {
        return;
      }

      // Ignore clicks on buttons (action menu, etc.)
      // This includes any button element within the card
      if (target.closest('button')) {
        return;
      }

      onClick?.();
    };

    const handleCheckboxChange = (checked: boolean) => {
      onSelect?.(checked);
    };

    // Prefetch entity data on hover for faster modal opening
    const handleMouseEnter = () => {
      if (
        isEntity(item) &&
        (item.syncStatus === 'modified' || item.syncStatus === 'outdated') &&
        item.projectPath
      ) {
        queryClient.prefetchQuery({
          queryKey: ['artifact-diff', item.id, item.projectPath],
          queryFn: async () => {
            const params = new URLSearchParams({
              project_path: item.projectPath!,
            });

            if (item.collection) {
              params.set('collection', item.collection);
            }

            return await apiRequest<ArtifactDiffResponse>(
              `/artifacts/${encodeURIComponent(item.id)}/diff?${params.toString()}`
            );
          },
          staleTime: 5 * 60 * 1000, // 5 minutes
        });
      }
    };

    // Truncate description
    const truncatedDescription =
      data.description && data.description.length > 100
        ? data.description.substring(0, 100) + '...'
        : data.description;

    // Display max 3 tags
    const displayTags = data.tags?.slice(0, 3) || [];
    const remainingTagsCount = (data.tags?.length || 0) - displayTags.length;

    // Format relative time for browse mode
    const formatRelativeTime = (dateString?: string): string => {
      if (!dateString) return 'N/A';
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return 'just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 30) return `${diffDays}d ago`;
      return date.toLocaleDateString();
    };

    // Unified ArtifactCard-style rendering for both modes
    return (
      <Card
        className={cn(
          'cursor-pointer border-l-4 transition-all hover:border-primary/50 hover:shadow-md',
          artifactTypeBorderAccents[data.type],
          artifactTypeCardTints[data.type],
          selected && 'ring-2 ring-primary'
        )}
        onClick={handleCardClick}
        onMouseEnter={handleMouseEnter}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClick?.();
          }
        }}
        aria-label={`View details for ${data.name}`}
      >
        {/* Header with icon and status badge */}
        <div className="p-4 pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex min-w-0 flex-1 items-center gap-2">
              {/* Checkbox (selection mode only) */}
              {selectable && (
                <Checkbox
                  checked={selected}
                  onCheckedChange={handleCheckboxChange}
                  className="flex-shrink-0"
                  aria-label={`Select ${data.name}`}
                />
              )}

              {/* Icon with status border */}
              <div
                className={cn(
                  'flex-shrink-0 rounded-md border p-2',
                  data.status && statusColors[data.status]
                )}
              >
                <Icon className={cn('h-4 w-4', config?.color ?? 'text-muted-foreground')} />
              </div>

              {/* Name and title */}
              <div className="min-w-0 flex-1">
                <h3 className="truncate font-semibold" title={data.name}>
                  {data.title || data.name}
                </h3>
                {data.title && (
                  <p className="truncate text-xs text-muted-foreground">{data.name}</p>
                )}
              </div>
            </div>

            {/* Status badge, score badge, and actions */}
            <div className="flex flex-shrink-0 items-center gap-2">
              {data.confidence !== undefined && (
                <ScoreBadge confidence={data.confidence} size="sm" />
              )}
              {data.status && (
                <Badge className={cn('flex-shrink-0', statusColors[data.status])} variant="outline">
                  {statusLabels[data.status] || data.status}
                </Badge>
              )}
              {isEntity(item) && (
                <UnifiedCardActions
                  artifact={item}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onDeploy={onDeploy}
                  onSync={onSync}
                  onViewDiff={onViewDiff}
                  onRollback={onRollback}
                  onCopyCliCommand={onCopyCliCommand}
                />
              )}
            </div>
          </div>

          {/* Collection badges - Only shown in "All Collections" view */}
          {isAllCollectionsView && itemCollections.length > 0 && (
            <div className="mt-2">
              <CollectionBadgeStack collections={itemCollections} maxBadges={2} />
            </div>
          )}

          {/* Group badges - Only shown when viewing a specific collection (not "All Collections") */}
          {!isAllCollectionsView && itemGroups.length > 0 && (
            <div className="mt-2">
              <GroupBadgeRow groups={itemGroups} maxBadges={2} />
            </div>
          )}
        </div>

        {/* Content - Fixed-height rows for consistent card heights */}
        <div className="flex min-h-[140px] flex-col px-4 pb-4">
          {/* Description - flex-grow to fill available space */}
          <div className="min-h-[40px] flex-grow">
            <p className="line-clamp-2 text-sm text-muted-foreground">
              {truncatedDescription || '\u00A0'}
            </p>
          </div>

          {/* Metadata row - fixed height */}
          <div className="flex h-5 items-center gap-4 text-xs text-muted-foreground">
            {data.version && (
              <div className="flex items-center gap-1" title="Version">
                <LucideIcons.Package className="h-3 w-3" />
                <span>{data.version}</span>
              </div>
            )}
            {data.updatedAt && (
              <div className="flex items-center gap-1" title="Last updated">
                <LucideIcons.Clock className="h-3 w-3" />
                <span>{formatRelativeTime(data.updatedAt)}</span>
              </div>
            )}
            {data.usageCount !== undefined && (
              <div className="flex items-center gap-1" title="Usage count">
                <LucideIcons.TrendingUp className="h-3 w-3" />
                <span>{data.usageCount}</span>
              </div>
            )}
          </div>

          {/* Tags - fixed height, always render container */}
          <div className="mt-2 flex h-6 flex-wrap items-center gap-1">
            {displayTags.length > 0 && (
              <>
                {displayTags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
                {remainingTagsCount > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    +{remainingTagsCount}
                  </Badge>
                )}
              </>
            )}
          </div>

          {/* Warnings - fixed height, always render container */}
          <div className="flex h-4 items-center">
            {data.isOutdated && (
              <div className="flex items-center gap-1 text-xs text-yellow-600">
                <LucideIcons.AlertCircle className="h-3 w-3" />
                <span>Update available</span>
              </div>
            )}
          </div>
        </div>
      </Card>
    );
  },
  (prevProps, nextProps) => {
    // Custom comparison function to prevent unnecessary re-renders
    const prevData = normalizeCardData(prevProps.item);
    const nextData = normalizeCardData(nextProps.item);

    return (
      prevData.id === nextData.id &&
      prevData.name === nextData.name &&
      prevData.status === nextData.status &&
      prevData.description === nextData.description &&
      prevData.tags?.join(',') === nextData.tags?.join(',') &&
      prevData.confidence === nextData.confidence &&
      prevProps.selected === nextProps.selected &&
      prevProps.selectable === nextProps.selectable
    );
  }
);

/**
 * UnifiedCardSkeleton - Loading skeleton for unified card
 *
 * Displays a placeholder while data is being fetched.
 * Uses the same ArtifactCard-style layout for both modes.
 *
 * @param selectable - Whether to show checkbox skeleton (selection mode)
 */
export function UnifiedCardSkeleton({ selectable = false }: { selectable?: boolean }) {
  return (
    <Card className="border-l-4">
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-1 items-center gap-2">
            {/* Checkbox skeleton (selection mode only) */}
            {selectable && <Skeleton className="h-4 w-4 flex-shrink-0 rounded" />}

            {/* Icon skeleton */}
            <Skeleton className="h-8 w-8 flex-shrink-0 rounded-md" />

            {/* Name skeleton */}
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>

          {/* Score badge, status badge, and actions skeleton */}
          <div className="flex flex-shrink-0 items-center gap-2">
            <ScoreBadgeSkeleton size="sm" />
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-8 w-8 rounded" />
          </div>
        </div>
      </div>
      {/* Content - Fixed-height rows matching UnifiedCard layout */}
      <div className="flex min-h-[140px] flex-col px-4 pb-4">
        {/* Description skeleton - flex-grow */}
        <div className="min-h-[40px] flex-grow">
          <Skeleton className="h-10 w-full" />
        </div>

        {/* Metadata skeleton - fixed height */}
        <div className="flex h-5 items-center gap-4">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-16" />
        </div>

        {/* Tags skeleton - fixed height */}
        <div className="mt-2 flex h-6 items-center gap-1">
          <Skeleton className="h-5 w-12 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>

        {/* Warnings skeleton - fixed height */}
        <div className="flex h-4 items-center">{/* Empty to match potential warning space */}</div>
      </div>
    </Card>
  );
}
