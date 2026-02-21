/**
 * Entity List Component
 *
 * Displays entities in either grid or list view mode.
 * Supports multi-select and empty state.
 * Supports different card variants: "default" (EntityCard) or "operations" (ArtifactOperationsCard)
 */

'use client';

import * as React from 'react';
import { FileQuestion } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Artifact } from '@/types/artifact';
import { EntityCard, EntityCardSkeleton } from './entity-card';
import { EntityRow } from './entity-row';
import {
  ArtifactOperationsCard,
  ArtifactOperationsCardSkeleton,
} from '@/components/manage/artifact-operations-card';
import { useEntityLifecycle, useCliCopy } from '@/hooks';
import { generateBasicDeployCommand } from '@/lib/cli-commands';

const { useCallback } = React;

/**
 * Card variant determines which card component to use in grid view
 * - "default": Uses EntityCard (UnifiedCard) - general purpose
 * - "operations": Uses ArtifactOperationsCard - operations/health focused for manage page
 */
export type CardVariant = 'default' | 'operations';

/**
 * Props for EntityList component
 *
 * Controls display mode, entity data, selection capability, and lifecycle actions.
 */
export interface EntityListProps {
  /** Display mode: "grid" for card layout, "list" for table layout */
  viewMode: 'grid' | 'list';
  /** Card variant for grid view: "default" or "operations" */
  cardVariant?: CardVariant;
  /** Optional array of artifacts to display. If not provided, uses context. */
  entities?: Artifact[];
  /** Callback when an artifact is clicked (outside of action menu) */
  onEntityClick?: (artifact: Artifact) => void;
  /** Callback when opening modal with specific tab (used with operations variant) */
  onEntityClickWithTab?: (artifact: Artifact, tab: string) => void;
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
  /** Callback for manage action (used with operations variant) */
  onManage?: (artifact: Artifact) => void;
  /** Handler when a tag badge is clicked (for filtering) */
  onTagClick?: (tagName: string) => void;
}

/**
 * EntityList - Displays entities in grid or list view mode
 *
 * Renders a collection of entities using either grid layout (EntityCard or ArtifactOperationsCard)
 * or list layout (EntityRow). Integrates with EntityLifecycle context for selection management.
 * Shows empty state when no entities are available.
 *
 * @example Default variant (browse/discovery)
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
 * @example Operations variant (manage page)
 * ```tsx
 * <EntityList
 *   viewMode="grid"
 *   cardVariant="operations"
 *   entities={artifacts}
 *   selectable={bulkMode}
 *   onSync={handleSync}
 *   onDeploy={handleDeploy}
 *   onViewDiff={handleViewDiff}
 *   onManage={handleManage}
 * />
 * ```
 *
 * @param props - EntityListProps configuration
 * @returns React component displaying entities in selected view mode
 */
export function EntityList({
  viewMode,
  cardVariant = 'default',
  entities: entitiesProp,
  onEntityClick,
  onEntityClickWithTab,
  selectable = false,
  onEdit,
  onDelete,
  onDeploy,
  onSync,
  onViewDiff,
  onRollback,
  onManage,
  onTagClick,
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

  // Render EntityCard (default variant)
  const renderEntityCard = useCallback(
    (artifact: Artifact, index: number) => {
      return (
        <EntityCard
          key={artifact.uuid}
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

  // Render ArtifactOperationsCard (operations variant)
  const renderOperationsCard = useCallback(
    (artifact: Artifact, index: number) => {
      return (
        <ArtifactOperationsCard
          key={artifact.uuid}
          artifact={artifact}
          selected={selectedEntities.includes(artifact.id)}
          selectable={selectable}
          onSelect={(selected) => handleSelect(artifact, selected)}
          onClick={() => handleEntityClick(artifact)}
          onOpenWithTab={onEntityClickWithTab ? (tab) => onEntityClickWithTab(artifact, tab) : undefined}
          onSync={onSync ? () => onSync(artifact) : undefined}
          onDeploy={onDeploy ? () => onDeploy(artifact) : undefined}
          onViewDiff={onViewDiff ? () => onViewDiff(artifact) : undefined}
          onManage={onManage ? () => onManage(artifact) : undefined}
          onDelete={onDelete ? () => onDelete(artifact) : undefined}
          onTagClick={onTagClick}
        />
      );
    },
    [
      selectedEntities,
      selectable,
      handleSelect,
      handleEntityClick,
      onEntityClickWithTab,
      onSync,
      onDeploy,
      onViewDiff,
      onManage,
      onDelete,
      onTagClick,
    ]
  );

  const renderEntityRow = useCallback(
    (artifact: Artifact, index: number) => {
      return (
        <EntityRow
          key={artifact.uuid}
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
      // Choose skeleton based on card variant
      const SkeletonComponent =
        cardVariant === 'operations' ? ArtifactOperationsCardSkeleton : EntityCardSkeleton;

      return (
        <ScrollArea className="h-full">
          <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonComponent key={i} selectable={selectable} />
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

  // Grid view - choose card renderer based on variant
  if (viewMode === 'grid') {
    const renderCard = cardVariant === 'operations' ? renderOperationsCard : renderEntityCard;

    return (
      <ScrollArea className="h-full">
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {entities.map(renderCard)}
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
