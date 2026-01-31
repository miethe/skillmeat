/**
 * Entity List Component
 *
 * Displays entities in either grid or list view mode.
 * Supports multi-select and empty state.
 */

'use client';

import * as React from 'react';
import { FileQuestion } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Artifact } from '@/types/artifact';
import { EntityCard, EntityCardSkeleton } from './entity-card';
import { EntityRow } from './entity-row';
import { useEntityLifecycle, useCliCopy } from '@/hooks';
import { generateBasicDeployCommand } from '@/lib/cli-commands';

const { useCallback } = React;

/**
 * Props for EntityList component
 *
 * Controls display mode, entity data, selection capability, and lifecycle actions.
 */
export interface EntityListProps {
  /** Display mode: "grid" for card layout, "list" for table layout */
  viewMode: 'grid' | 'list';
  /** Optional array of artifacts to display. If not provided, uses context. */
  entities?: Artifact[];
  /** Callback when an artifact is clicked (outside of action menu) */
  onEntityClick?: (artifact: Artifact) => void;
  /** Whether artifacts can be selected via checkbox */
  selectable?: boolean;
  /** Callback for edit action on artifact */
  onEdit?: (artifact: Artifact) => void;
  /** Callback for delete action on artifact */
  onDelete?: (artifact: Artifact) => void;
  /** Callback for deploy action on artifact */
  onDeploy?: (artifact: Artifact) => void;
  /** Callback for sync action on artifact */
  onSync?: (artifact: Artifact) => void;
  /** Callback to view diff for artifact */
  onViewDiff?: (artifact: Artifact) => void;
  /** Callback to rollback artifact */
  onRollback?: (artifact: Artifact) => void;
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
  const { selectEntity, deselectEntity, isLoading } = context;
  const { copy } = useCliCopy();

  const handleCopyCliCommand = useCallback(
    (artifactName: string) => {
      const command = generateBasicDeployCommand(artifactName);
      copy(command);
    },
    [copy]
  );

  // Memoize handlers to prevent EntityCard/EntityRow re-renders
  const handleEntityClick = useCallback(
    (artifact: Artifact) => {
      onEntityClick?.(artifact);
    },
    [onEntityClick]
  );

  const handleSelect = useCallback(
    (artifact: Artifact, selected: boolean) => {
      if (selected) {
        selectEntity(artifact.id);
      } else {
        deselectEntity(artifact.id);
      }
    },
    [selectEntity, deselectEntity]
  );

  // ALL useCallback hooks must be defined BEFORE any early returns
  // to comply with React's Rules of Hooks (same order on every render)
  const renderEntityCard = useCallback(
    (artifact: Artifact) => {
      return (
        <EntityCard
          key={artifact.id}
          entity={artifact}
          selected={selectedEntities.includes(artifact.id)}
          selectable={selectable}
          onSelect={(selected) => handleSelect(artifact, selected)}
          onClick={() => handleEntityClick(artifact)}
          onEdit={onEdit ? () => onEdit(artifact) : undefined}
          onDelete={onDelete ? () => onDelete(artifact) : undefined}
          onDeploy={onDeploy ? () => onDeploy(artifact) : undefined}
          onSync={onSync ? () => onSync(artifact) : undefined}
          onViewDiff={onViewDiff ? () => onViewDiff(artifact) : undefined}
          onRollback={onRollback ? () => onRollback(artifact) : undefined}
          onCopyCliCommand={() => handleCopyCliCommand(artifact.name)}
        />
      );
    },
    [
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
      handleCopyCliCommand,
    ]
  );

  const renderEntityRow = useCallback(
    (artifact: Artifact) => {
      return (
        <EntityRow
          key={artifact.id}
          entity={artifact}
          selected={selectedEntities.includes(artifact.id)}
          selectable={selectable}
          onSelect={(selected) => handleSelect(artifact, selected)}
          onClick={() => handleEntityClick(artifact)}
          onEdit={onEdit ? () => onEdit(artifact) : undefined}
          onDelete={onDelete ? () => onDelete(artifact) : undefined}
          onDeploy={onDeploy ? () => onDeploy(artifact) : undefined}
          onSync={onSync ? () => onSync(artifact) : undefined}
          onViewDiff={onViewDiff ? () => onViewDiff(artifact) : undefined}
          onRollback={onRollback ? () => onRollback(artifact) : undefined}
          onCopyCliCommand={() => handleCopyCliCommand(artifact.name)}
        />
      );
    },
    [
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
      handleCopyCliCommand,
    ]
  );

  // Loading state - show skeletons
  if (isLoading) {
    if (viewMode === 'grid') {
      return (
        <ScrollArea className="h-full">
          <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <EntityCardSkeleton key={i} />
            ))}
          </div>
        </ScrollArea>
      );
    } else {
      return (
        <ScrollArea className="h-full">
          <div className="border-t">
            <div className="flex items-center gap-4 border-b bg-muted/50 px-4 py-2 text-xs font-medium text-muted-foreground">
              {selectable && <div className="w-4 flex-shrink-0" />}
              <div className="w-48">Name</div>
              <div className="w-24">Type</div>
              <div className="flex-1">Description</div>
              <div className="w-40">Tags</div>
              <div className="w-24">Status</div>
              <div className="w-8 flex-shrink-0">Actions</div>
            </div>
            {Array.from({ length: 6 }).map((_, i) => (
              <EntityCardSkeleton key={i} />
            ))}
          </div>
        </ScrollArea>
      );
    }
  }

  // Empty state - safe to return early now that all hooks are defined
  if (!entities || entities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileQuestion className="mb-4 h-12 w-12 text-muted-foreground" />
        <h3 className="mb-2 text-lg font-semibold">No entities found</h3>
        <p className="max-w-md text-sm text-muted-foreground">
          {selectable
            ? 'No entities match your current filters. Try adjusting your search or filters.'
            : 'Get started by adding your first entity to your collection.'}
        </p>
      </div>
    );
  }

  // Grid view
  if (viewMode === 'grid') {
    return (
      <ScrollArea className="h-full">
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {entities.map(renderEntityCard)}
        </div>
      </ScrollArea>
    );
  }

  // List view
  return (
    <ScrollArea className="h-full">
      <div className="border-t">
        {/* Header row */}
        <div className="flex items-center gap-4 border-b bg-muted/50 px-4 py-2 text-xs font-medium text-muted-foreground">
          {selectable && <div className="w-4 flex-shrink-0" />}
          <div className="w-48">Name</div>
          <div className="w-24">Type</div>
          <div className="flex-1">Description</div>
          <div className="w-40">Tags</div>
          <div className="w-24">Status</div>
          <div className="w-8 flex-shrink-0">Actions</div>
        </div>

        {/* Entity rows */}
        {entities.map(renderEntityRow)}
      </div>
    </ScrollArea>
  );
}
