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

"use client";

import * as React from "react";
import * as LucideIcons from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/api";
import type { Entity, EntityType } from "@/types/entity";
import type { Artifact, ArtifactType } from "@/types/artifact";
import { getEntityTypeConfig } from "@/types/entity";
import { EntityActions } from "@/components/entity/entity-actions";
import type { ArtifactDiffResponse } from "@/sdk";

/**
 * Type guard to check if item is an Entity
 */
function isEntity(item: Entity | Artifact): item is Entity {
  return "projectPath" in item || !("metadata" in item);
}

/**
 * Type guard to check if item is an Artifact
 */
function isArtifact(item: Entity | Artifact): item is Artifact {
  return "metadata" in item && "usageStats" in item;
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
  status?: string;
  version?: string;
  source?: string;
  updatedAt?: string;
  usageCount?: number;
  projectPath?: string;
  collection?: string;
  isOutdated?: boolean;
}

/**
 * Extract normalized data from Entity or Artifact
 */
function normalizeCardData(item: Entity | Artifact): NormalizedCardData {
  if (isArtifact(item)) {
    // Artifact has nested metadata
    return {
      id: item.id,
      name: item.name,
      type: item.type,
      title: item.metadata.title,
      description: item.metadata.description,
      tags: item.metadata.tags,
      status: item.status,
      version: item.version,
      source: item.source,
      updatedAt: item.updatedAt,
      usageCount: item.usageStats.usageCount,
      isOutdated: item.upstreamStatus.isOutdated,
    };
  } else {
    // Entity has flat properties
    return {
      id: item.id,
      name: item.name,
      type: item.type,
      title: undefined, // Entities don't have separate title
      description: item.description,
      tags: item.tags,
      status: item.status,
      version: item.version,
      source: item.source,
      updatedAt: item.modifiedAt,
      projectPath: item.projectPath,
      collection: item.collection,
    };
  }
}

/**
 * Props for UnifiedCard component
 */
export interface UnifiedCardProps {
  /** The item to display (Entity or Artifact) */
  item: Entity | Artifact;
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
  /** @deprecated mode prop is no longer used - visual style is now unified */
  mode?: "selection" | "browse";
}

// Enhanced type colors for better visual differentiation
const artifactTypeBorderAccents: Record<EntityType | ArtifactType, string> = {
  skill: "border-l-blue-500",
  command: "border-l-purple-500",
  agent: "border-l-green-500",
  mcp: "border-l-orange-500",
  hook: "border-l-pink-500",
};

const artifactTypeCardTints: Record<EntityType | ArtifactType, string> = {
  skill: "bg-blue-500/[0.02] dark:bg-blue-500/[0.03]",
  command: "bg-purple-500/[0.02] dark:bg-purple-500/[0.03]",
  agent: "bg-green-500/[0.02] dark:bg-green-500/[0.03]",
  mcp: "bg-orange-500/[0.02] dark:bg-orange-500/[0.03]",
  hook: "bg-pink-500/[0.02] dark:bg-pink-500/[0.03]",
};

const statusColors: Record<string, string> = {
  synced: "text-green-500",
  modified: "text-yellow-500",
  outdated: "text-orange-500",
  conflict: "text-red-500",
  active: "bg-green-500/10 text-green-600 border-green-500/20",
  error: "bg-red-500/10 text-red-600 border-red-500/20",
};

const statusLabels: Record<string, string> = {
  synced: "Synced",
  modified: "Modified",
  outdated: "Outdated",
  conflict: "Conflict",
  active: "Active",
  error: "Error",
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
export const UnifiedCard = React.memo(function UnifiedCard({
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
  mode, // Deprecated but kept for backward compatibility
}: UnifiedCardProps) {
  const queryClient = useQueryClient();
  const data = normalizeCardData(item);
  const config = getEntityTypeConfig(data.type as EntityType);

  // Type-safe icon lookup with fallback
  const IconComponent = (LucideIcons as any)[config.icon] as
    | React.ComponentType<{ className?: string }>
    | undefined;
  const Icon = IconComponent || LucideIcons.FileText;

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't trigger onClick if clicking on checkbox or actions menu
    if (
      (e.target as HTMLElement).closest('[role="checkbox"]') ||
      (e.target as HTMLElement).closest('[role="button"]')
    ) {
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
      (item.status === "modified" || item.status === "outdated") &&
      item.projectPath
    ) {
      queryClient.prefetchQuery({
        queryKey: ["artifact-diff", item.id, item.projectPath],
        queryFn: async () => {
          const params = new URLSearchParams({
            project_path: item.projectPath!,
          });

          if (item.collection) {
            params.set("collection", item.collection);
          }

          return await apiRequest<ArtifactDiffResponse>(
            `/artifacts/${item.id}/diff?${params.toString()}`
          );
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
      });
    }
  };

  // Truncate description
  const truncatedDescription =
    data.description && data.description.length > 100
      ? data.description.substring(0, 100) + "..."
      : data.description;

  // Display max 3 tags
  const displayTags = data.tags?.slice(0, 3) || [];
  const remainingTagsCount = (data.tags?.length || 0) - displayTags.length;

  // Format relative time for browse mode
  const formatRelativeTime = (dateString?: string): string => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  // Unified ArtifactCard-style rendering for both modes
  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:shadow-md hover:border-primary/50 border-l-4",
        artifactTypeBorderAccents[data.type],
        artifactTypeCardTints[data.type],
        selected && "ring-2 ring-primary"
      )}
      onClick={handleCardClick}
      onMouseEnter={handleMouseEnter}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
      aria-label={`View details for ${data.name}`}
    >
      {/* Header with icon and status badge */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0 flex-1">
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
                "flex-shrink-0 p-2 rounded-md border",
                data.status && statusColors[data.status]
              )}
            >
              <Icon className={cn("h-4 w-4", config.color)} />
            </div>

            {/* Name and title */}
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold truncate" title={data.name}>
                {data.title || data.name}
              </h3>
              {data.title && (
                <p className="text-xs text-muted-foreground truncate">
                  {data.name}
                </p>
              )}
            </div>
          </div>

          {/* Status badge and actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {data.status && (
              <Badge
                className={cn("flex-shrink-0", statusColors[data.status])}
                variant="outline"
              >
                {statusLabels[data.status] || data.status}
              </Badge>
            )}
            {isEntity(item) && (
              <EntityActions
                entity={item}
                onEdit={onEdit}
                onDelete={onDelete}
                onDeploy={onDeploy}
                onSync={onSync}
                onViewDiff={onViewDiff}
                onRollback={onRollback}
              />
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-4 pb-4 space-y-3">
        {/* Description */}
        {truncatedDescription && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {truncatedDescription}
          </p>
        )}

        {/* Metadata row */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
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

        {/* Tags */}
        {displayTags.length > 0 && (
          <div className="flex flex-wrap gap-1">
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
          </div>
        )}

        {/* Warnings */}
        {data.isOutdated && (
          <div className="flex items-center gap-1 text-xs text-yellow-600">
            <LucideIcons.AlertCircle className="h-3 w-3" />
            <span>Update available</span>
          </div>
        )}
      </div>
    </Card>
  );
}, (prevProps, nextProps) => {
  // Custom comparison function to prevent unnecessary re-renders
  const prevData = normalizeCardData(prevProps.item);
  const nextData = normalizeCardData(nextProps.item);

  return (
    prevData.id === nextData.id &&
    prevData.name === nextData.name &&
    prevData.status === nextData.status &&
    prevData.description === nextData.description &&
    prevData.tags?.join(",") === nextData.tags?.join(",") &&
    prevProps.selected === nextProps.selected &&
    prevProps.selectable === nextProps.selectable
  );
});

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
          <div className="flex items-center gap-2 flex-1">
            {/* Checkbox skeleton (selection mode only) */}
            {selectable && <Skeleton className="h-4 w-4 flex-shrink-0 rounded" />}

            {/* Icon skeleton */}
            <Skeleton className="h-8 w-8 rounded-md flex-shrink-0" />

            {/* Name skeleton */}
            <div className="space-y-2 flex-1">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>

          {/* Status badge and actions skeleton */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-8 w-8 rounded" />
          </div>
        </div>
      </div>
      <div className="px-4 pb-4 space-y-3">
        {/* Description skeleton */}
        <Skeleton className="h-10 w-full" />

        {/* Metadata skeleton */}
        <div className="flex gap-4">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-16" />
        </div>

        {/* Tags skeleton */}
        <div className="flex gap-1">
          <Skeleton className="h-5 w-12 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
      </div>
    </Card>
  );
}
