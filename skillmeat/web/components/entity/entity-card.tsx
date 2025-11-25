/**
 * Entity Card Component
 *
 * Card view for displaying a single entity with icon, name, type badge,
 * status indicator, tags, and actions menu.
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
import type { Entity } from "@/types/entity";
import { getEntityTypeConfig } from "@/types/entity";
import { EntityActions } from "./entity-actions";
import type { ArtifactDiffResponse } from "@/sdk";

/**
 * Props for EntityCard component
 *
 * Controls the card display, selection state, and action callbacks.
 */
export interface EntityCardProps {
  /** The entity to display in the card */
  entity: Entity;
  /** Whether the card is currently selected */
  selected?: boolean;
  /** Whether the entity can be selected (shows checkbox) */
  selectable?: boolean;
  /** Callback when selection state changes */
  onSelect?: (selected: boolean) => void;
  /** Callback when card is clicked */
  onClick?: () => void;
  /** Callback for edit action */
  onEdit?: () => void;
  /** Callback for delete action */
  onDelete?: () => void;
  /** Callback for deploy action */
  onDeploy?: () => void;
  /** Callback for sync action */
  onSync?: () => void;
  /** Callback to view diff (enabled when status is "modified") */
  onViewDiff?: () => void;
  /** Callback to rollback (enabled for "modified" or "conflict" status) */
  onRollback?: () => void;
}

/**
 * EntityCard - Grid view card for displaying a single entity
 *
 * Renders entity information in card format with icon, name, type badge, description,
 * tags, status indicator, and action menu. Used in grid view mode.
 *
 * @example
 * ```tsx
 * <EntityCard
 *   entity={skill}
 *   selected={true}
 *   selectable={true}
 *   onSelect={(checked) => updateSelection(checked)}
 *   onClick={() => openDetail(skill)}
 *   onEdit={() => startEdit(skill)}
 *   onDelete={() => deleteEntity(skill)}
 * />
 * ```
 *
 * @param props - EntityCardProps configuration
 * @returns Memoized card component with custom render comparison
 */
// Memoized component with custom comparison to prevent unnecessary re-renders
export const EntityCard = React.memo(function EntityCard({
  entity,
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
}: EntityCardProps) {
  const queryClient = useQueryClient();
  const config = getEntityTypeConfig(entity.type);
  // Type-safe icon lookup with fallback
  const IconComponent = (LucideIcons as any)[config.icon] as React.ComponentType<{ className?: string }> | undefined;
  const Icon = IconComponent || LucideIcons.FileText;

  const statusColors = {
    synced: "text-green-500",
    modified: "text-yellow-500",
    outdated: "text-orange-500",
    conflict: "text-red-500",
  };

  const statusLabels = {
    synced: "Synced",
    modified: "Modified",
    outdated: "Outdated",
    conflict: "Conflict",
  };

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
    // Prefetch diff data if entity is modified or outdated
    if ((entity.status === 'modified' || entity.status === 'outdated') && entity.projectPath) {
      queryClient.prefetchQuery({
        queryKey: ['artifact-diff', entity.id, entity.projectPath],
        queryFn: async () => {
          const params = new URLSearchParams({
            project_path: entity.projectPath!,
          });

          if (entity.collection) {
            params.set('collection', entity.collection);
          }

          return await apiRequest<ArtifactDiffResponse>(
            `/artifacts/${entity.id}/diff?${params.toString()}`
          );
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
      });
    }
  };

  // Truncate description
  const truncatedDescription =
    entity.description && entity.description.length > 100
      ? entity.description.substring(0, 100) + "..."
      : entity.description;

  // Display max 3 tags
  const displayTags = entity.tags?.slice(0, 3) || [];
  const remainingTagsCount = (entity.tags?.length || 0) - displayTags.length;

  return (
    <Card
      className={cn(
        "p-4 transition-colors cursor-pointer hover:bg-accent/50",
        selected && "ring-2 ring-primary"
      )}
      onClick={handleCardClick}
      onMouseEnter={handleMouseEnter}
    >
      {/* Header: Checkbox, Icon, Name, Actions */}
      <div className="flex items-start gap-3 mb-3">
        {selectable && (
          <Checkbox
            checked={selected}
            onCheckedChange={handleCheckboxChange}
            className="mt-1"
            aria-label={`Select ${entity.name}`}
          />
        )}

        <Icon className={cn("h-5 w-5 mt-0.5", config.color)} />

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm truncate">{entity.name}</h3>
        </div>

        <EntityActions
          entity={entity}
          onEdit={onEdit}
          onDelete={onDelete}
          onDeploy={onDeploy}
          onSync={onSync}
          onViewDiff={onViewDiff}
          onRollback={onRollback}
        />
      </div>

      {/* Type Badge */}
      <div className="mb-2">
        <Badge variant="secondary" className="text-xs">
          {config.label}
        </Badge>
      </div>

      {/* Description */}
      {truncatedDescription && (
        <p className="text-sm text-muted-foreground mb-3">{truncatedDescription}</p>
      )}

      {/* Tags */}
      {displayTags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {displayTags.map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
          {remainingTagsCount > 0 && (
            <Badge variant="outline" className="text-xs">
              +{remainingTagsCount} more
            </Badge>
          )}
        </div>
      )}

      {/* Status Indicator */}
      {entity.status && (
        <div className="flex items-center gap-2 text-sm">
          <span className={cn("inline-block w-2 h-2 rounded-full", statusColors[entity.status])} />
          <span className="text-muted-foreground">{statusLabels[entity.status]}</span>
        </div>
      )}
    </Card>
  );
}, (prevProps, nextProps) => {
  // Custom comparison function to prevent unnecessary re-renders
  // Only re-render if entity data, selected state, or selectable prop changes
  return (
    prevProps.entity.id === nextProps.entity.id &&
    prevProps.entity.name === nextProps.entity.name &&
    prevProps.entity.status === nextProps.entity.status &&
    prevProps.entity.description === nextProps.entity.description &&
    prevProps.entity.tags?.join(',') === nextProps.entity.tags?.join(',') &&
    prevProps.selected === nextProps.selected &&
    prevProps.selectable === nextProps.selectable
  );
});

/**
 * EntityCardSkeleton - Loading skeleton for entity card
 *
 * Displays a placeholder while entity data is being fetched to prevent
 * layout shift and provide visual feedback to the user.
 *
 * @example
 * ```tsx
 * {isLoading && (
 *   <div className="grid gap-4">
 *     {Array.from({ length: 6 }).map((_, i) => (
 *       <EntityCardSkeleton key={i} />
 *     ))}
 *   </div>
 * )}
 * ```
 *
 * @returns Skeleton component matching EntityCard layout
 */
export function EntityCardSkeleton() {
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3 mb-3">
        <Skeleton className="h-5 w-5 rounded" />
        <Skeleton className="h-5 flex-1" />
        <Skeleton className="h-8 w-8 rounded" />
      </div>

      <div className="mb-2">
        <Skeleton className="h-5 w-20" />
      </div>

      <Skeleton className="h-4 w-full mb-2" />
      <Skeleton className="h-4 w-3/4 mb-3" />

      <div className="flex gap-2 mb-3">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-20" />
      </div>

      <div className="flex items-center gap-2">
        <Skeleton className="h-2 w-2 rounded-full" />
        <Skeleton className="h-4 w-16" />
      </div>
    </Card>
  );
}
