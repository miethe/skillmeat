/**
 * Entity Card Component
 *
 * Card view for displaying a single entity with icon, name, type badge,
 * status indicator, tags, and actions menu.
 */

"use client";

import * as React from "react";
import * as LucideIcons from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import type { Entity } from "@/types/entity";
import { getEntityTypeConfig } from "@/types/entity";
import { EntityActions } from "./entity-actions";

export interface EntityCardProps {
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

export function EntityCard({
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
}: EntityCardProps) {
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
    >
      {/* Header: Checkbox, Icon, Name, Actions */}
      <div className="flex items-start gap-3 mb-3">
        {selectable && (
          <Checkbox
            checked={selected}
            onCheckedChange={handleCheckboxChange}
            className="mt-1"
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
}
