/**
 * Entity Row Component
 *
 * Table row view for displaying a single entity with all data in horizontal layout.
 * Used in list view mode.
 */

"use client";

import * as React from "react";
import * as LucideIcons from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import type { Entity } from "@/types/entity";
import { getEntityTypeConfig } from "@/types/entity";
import { EntityActions } from "./entity-actions";

export interface EntityRowProps {
  entity: Entity;
  selected?: boolean;
  selectable?: boolean;
  onSelect?: (selected: boolean) => void;
  onClick?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onDeploy?: () => void;
  onSync?: () => void;
  onViewDiff?: () => void;
}

export function EntityRow({
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
}: EntityRowProps) {
  const config = getEntityTypeConfig(entity.type);
  const Icon = (LucideIcons as any)[config.icon] || LucideIcons.FileText;

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

  const handleRowClick = (e: React.MouseEvent) => {
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

  // Truncate description
  const truncatedDescription =
    entity.description && entity.description.length > 60
      ? entity.description.substring(0, 60) + "..."
      : entity.description;

  // Display max 2 tags in row view
  const displayTags = entity.tags?.slice(0, 2) || [];
  const remainingTagsCount = (entity.tags?.length || 0) - displayTags.length;

  return (
    <div
      className={cn(
        "flex items-center gap-4 px-4 py-3 border-b transition-colors cursor-pointer hover:bg-accent/50",
        selected && "bg-accent"
      )}
      onClick={handleRowClick}
    >
      {/* Checkbox */}
      {selectable && (
        <div className="flex-shrink-0">
          <Checkbox checked={selected} onCheckedChange={handleCheckboxChange} />
        </div>
      )}

      {/* Icon & Name */}
      <div className="flex items-center gap-2 min-w-0 w-48">
        <Icon className={cn("h-4 w-4 flex-shrink-0", config.color)} />
        <span className="font-medium text-sm truncate">{entity.name}</span>
      </div>

      {/* Type Badge */}
      <div className="flex-shrink-0 w-24">
        <Badge variant="secondary" className="text-xs">
          {config.label}
        </Badge>
      </div>

      {/* Description */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-muted-foreground truncate">
          {truncatedDescription || "-"}
        </p>
      </div>

      {/* Tags */}
      <div className="flex-shrink-0 w-40">
        <div className="flex flex-wrap gap-1">
          {displayTags.map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
          {remainingTagsCount > 0 && (
            <Badge variant="outline" className="text-xs">
              +{remainingTagsCount}
            </Badge>
          )}
          {displayTags.length === 0 && (
            <span className="text-xs text-muted-foreground">-</span>
          )}
        </div>
      </div>

      {/* Status */}
      <div className="flex-shrink-0 w-24">
        {entity.status ? (
          <div className="flex items-center gap-2">
            <span
              className={cn("inline-block w-2 h-2 rounded-full", statusColors[entity.status])}
            />
            <span className="text-sm text-muted-foreground">{statusLabels[entity.status]}</span>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">-</span>
        )}
      </div>

      {/* Actions */}
      <div className="flex-shrink-0">
        <EntityActions
          entity={entity}
          onEdit={onEdit}
          onDelete={onDelete}
          onDeploy={onDeploy}
          onSync={onSync}
          onViewDiff={onViewDiff}
        />
      </div>
    </div>
  );
}
