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

const { useCallback } = React;

/**
 * Props for EntityList component
 *
 * Controls display mode, entity data, selection capability, and lifecycle actions.
 */
export interface EntityListProps {
  /** Display mode: "grid" for card layout, "list" for table layout */
  viewMode: "grid" | "list";
  /** Optional array of entities to display. If not provided, uses context. */
  entities?: Entity[];
  /** Callback when an entity is clicked (outside of action menu) */
  onEntityClick?: (entity: Entity) => void;
  /** Whether entities can be selected via checkbox */
  selectable?: boolean;
  /** Callback for edit action on entity */
  onEdit?: (entity: Entity) => void;
  /** Callback for delete action on entity */
  onDelete?: (entity: Entity) => void;
  /** Callback for deploy action on entity */
  onDeploy?: (entity: Entity) => void;
  /** Callback for sync action on entity */
  onSync?: (entity: Entity) => void;
  /** Callback to view diff for entity */
  onViewDiff?: (entity: Entity) => void;
  /** Callback to rollback entity */
  onRollback?: (entity: Entity) => void;
}

/**
 * EntityList - Displays entities in grid or list view mode
 *
 * Renders a collection of entities using either grid layout (EntityCard) or list
 * layout (EntityRow). Integrates with EntityLifecycle context for selection management.
 * Shows empty state when no entities are available.
 *
 * @example
 * ```tsx
 * <EntityList
 *   viewMode="grid"
 *   entities={skills}
 *   selectable={true}
 *   onEdit={handleEdit}
 *   onDelete={handleDelete}
 *   onDeploy={handleDeploy}
 * />
 * ```
 *
 * @param props - EntityListProps configuration
 * @returns React component displaying entities in selected view mode
 */
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

  // Memoize handlers to prevent EntityCard/EntityRow re-renders
  const handleEntityClick = useCallback((entity: Entity) => {
    onEntityClick?.(entity);
  }, [onEntityClick]);

  const handleSelect = useCallback((entity: Entity, selected: boolean) => {
    if (selected) {
      selectEntity(entity.id);
    } else {
      deselectEntity(entity.id);
    }
  }, [selectEntity, deselectEntity]);

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

  // Memoized render functions to prevent unnecessary re-renders
  const renderEntityCard = useCallback((entity: Entity) => {
    return (
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
    );
  }, [
    selectedEntities,
    selectable,
    handleSelect,
    handleEntityClick,
    onEdit,
    onDelete,
    onDeploy,
    onSync,
    onViewDiff,
    onRollback,
  ]);

  // Grid view
  if (viewMode === "grid") {
    return (
      <ScrollArea className="h-full">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
          {entities.map(renderEntityCard)}
        </div>
      </ScrollArea>
    );
  }

  const renderEntityRow = useCallback((entity: Entity) => {
    return (
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
    );
  }, [
    selectedEntities,
    selectable,
    handleSelect,
    handleEntityClick,
    onEdit,
    onDelete,
    onDeploy,
    onSync,
    onViewDiff,
    onRollback,
  ]);

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
        {entities.map(renderEntityRow)}
      </div>
    </ScrollArea>
  );
}
