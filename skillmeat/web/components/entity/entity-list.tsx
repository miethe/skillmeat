/**
 * Entity List Component
 *
 * Displays entities in either grid or list view mode.
 * Supports multi-select and empty state.
 */

"use client";

import * as React from "react";
import { FileQuestion } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Entity } from "@/types/entity";
import { EntityCard } from "./entity-card";
import { EntityRow } from "./entity-row";
import { useEntityLifecycle } from "@/hooks/useEntityLifecycle";

export interface EntityListProps {
  viewMode: "grid" | "list";
  entities?: Entity[];
  onEntityClick?: (entity: Entity) => void;
  selectable?: boolean;
  onEdit?: (entity: Entity) => void;
  onDelete?: (entity: Entity) => void;
  onDeploy?: (entity: Entity) => void;
  onSync?: (entity: Entity) => void;
  onViewDiff?: (entity: Entity) => void;
  onRollback?: (entity: Entity) => void;
}

export function EntityList({
  viewMode,
  entities: entitiesProp,
  onEntityClick,
  selectable = false,
  onEdit,
  onDelete,
  onDeploy,
  onSync,
  onViewDiff,
  onRollback,
}: EntityListProps) {
  // Use entities from context if not provided
  const context = useEntityLifecycle();
  const entities = entitiesProp ?? context.entities;
  const selectedEntities = context.selectedEntities;
  const { selectEntity, deselectEntity } = context;

  const handleEntityClick = (entity: Entity) => {
    onEntityClick?.(entity);
  };

  const handleSelect = (entity: Entity, selected: boolean) => {
    if (selected) {
      selectEntity(entity.id);
    } else {
      deselectEntity(entity.id);
    }
  };

  // Empty state
  if (!entities || entities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileQuestion className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No entities found</h3>
        <p className="text-sm text-muted-foreground max-w-md">
          {selectable
            ? "No entities match your current filters. Try adjusting your search or filters."
            : "Get started by adding your first entity to your collection."}
        </p>
      </div>
    );
  }

  // Grid view
  if (viewMode === "grid") {
    return (
      <ScrollArea className="h-full">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
          {entities.map((entity) => (
            <EntityCard
              key={entity.id}
              entity={entity}
              selected={selectedEntities.includes(entity.id)}
              selectable={selectable}
              onSelect={(selected) => handleSelect(entity, selected)}
              onClick={() => handleEntityClick(entity)}
              onEdit={onEdit ? () => onEdit(entity) : undefined}
              onDelete={onDelete ? () => onDelete(entity) : undefined}
              onDeploy={onDeploy ? () => onDeploy(entity) : undefined}
              onSync={onSync ? () => onSync(entity) : undefined}
              onViewDiff={onViewDiff ? () => onViewDiff(entity) : undefined}
              onRollback={onRollback ? () => onRollback(entity) : undefined}
            />
          ))}
        </div>
      </ScrollArea>
    );
  }

  // List view
  return (
    <ScrollArea className="h-full">
      <div className="border-t">
        {/* Header row */}
        <div className="flex items-center gap-4 px-4 py-2 border-b bg-muted/50 text-xs font-medium text-muted-foreground">
          {selectable && <div className="flex-shrink-0 w-4" />}
          <div className="w-48">Name</div>
          <div className="w-24">Type</div>
          <div className="flex-1">Description</div>
          <div className="w-40">Tags</div>
          <div className="w-24">Status</div>
          <div className="flex-shrink-0 w-8">Actions</div>
        </div>

        {/* Entity rows */}
        {entities.map((entity) => (
          <EntityRow
            key={entity.id}
            entity={entity}
            selected={selectedEntities.includes(entity.id)}
            selectable={selectable}
            onSelect={(selected) => handleSelect(entity, selected)}
            onClick={() => handleEntityClick(entity)}
            onEdit={onEdit ? () => onEdit(entity) : undefined}
            onDelete={onDelete ? () => onDelete(entity) : undefined}
            onDeploy={onDeploy ? () => onDeploy(entity) : undefined}
            onSync={onSync ? () => onSync(entity) : undefined}
            onViewDiff={onViewDiff ? () => onViewDiff(entity) : undefined}
            onRollback={onRollback ? () => onRollback(entity) : undefined}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
