/**
 * Entity Row Component
 *
 * Table row view for displaying a single entity with all data in horizontal layout.
 * Used in list view mode.
 */

'use client';

import * as React from 'react';
import * as LucideIcons from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';
import { getArtifactTypeConfig } from '@/types/artifact';
import { UnifiedCardActions } from '@/components/shared/unified-card-actions';

/**
 * Props for EntityRow component
 *
 * Controls the row display, selection state, and action callbacks.
 */
export interface EntityRowProps {
  /** The entity to display in the row */
  entity: Artifact;
  /** Whether the row is currently selected */
  selected?: boolean;
  /** Whether the entity can be selected (shows checkbox) */
  selectable?: boolean;
  /** Callback when selection state changes */
  onSelect?: (selected: boolean) => void;
  /** Callback when row is clicked */
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
  /** Callback for copying CLI command to clipboard */
  onCopyCliCommand?: () => void;
}

/**
 * EntityRow - Table row view for displaying a single entity
 *
 * Renders entity information in a horizontal row format with columns for name,
 * type, description, tags, status, and actions. Used in list view mode. All columns
 * are displayed with fixed widths for consistent alignment.
 *
 * @example
 * ```tsx
 * <EntityRow
 *   entity={artifact}
 *   selected={false}
 *   selectable={true}
 *   onSelect={(checked) => handleSelect(artifact.id, checked)}
 *   onClick={() => showDetails(artifact)}
 *   onEdit={() => openForm(artifact)}
 * />
 * ```
 *
 * @param props - EntityRowProps configuration
 * @returns Memoized row component with custom render comparison
 */
// Memoized component with custom comparison to prevent unnecessary re-renders
export const EntityRow = React.memo(
  function EntityRow({
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
    onCopyCliCommand,
  }: EntityRowProps) {
    const config = getArtifactTypeConfig(entity.type);
    // Type-safe icon lookup with fallback
    const IconComponent = (LucideIcons as any)[config.icon] as
      | React.ComponentType<{ className?: string }>
      | undefined;
    const Icon = IconComponent || LucideIcons.FileText;

    const statusColors: Record<string, string> = {
      synced: 'text-green-500',
      modified: 'text-yellow-500',
      outdated: 'text-orange-500',
      conflict: 'text-red-500',
      error: 'text-red-500',
    };

    const statusLabels: Record<string, string> = {
      synced: 'Synced',
      modified: 'Modified',
      outdated: 'Outdated',
      conflict: 'Conflict',
      error: 'Error',
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
        ? entity.description.substring(0, 60) + '...'
        : entity.description;

    // Display max 2 tags in row view
    const displayTags = entity.tags?.slice(0, 2) || [];
    const remainingTagsCount = (entity.tags?.length || 0) - displayTags.length;

    return (
      <div
        className={cn(
          'flex cursor-pointer items-center gap-4 border-b px-4 py-3 transition-colors hover:bg-accent/50',
          selected && 'bg-accent'
        )}
        onClick={handleRowClick}
      >
        {/* Checkbox */}
        {selectable && (
          <div className="flex-shrink-0">
            <Checkbox
              checked={selected}
              onCheckedChange={handleCheckboxChange}
              aria-label={`Select ${entity.name}`}
            />
          </div>
        )}

        {/* Icon & Name */}
        <div className="flex w-48 min-w-0 items-center gap-2">
          <Icon className={cn('h-4 w-4 flex-shrink-0', config.color)} />
          <span className="truncate text-sm font-medium">{entity.name}</span>
        </div>

        {/* Type Badge */}
        <div className="w-24 flex-shrink-0">
          <Badge variant="secondary" className="text-xs">
            {config.label}
          </Badge>
        </div>

        {/* Description */}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm text-muted-foreground">{truncatedDescription || '-'}</p>
        </div>

        {/* Tags */}
        <div className="w-40 flex-shrink-0">
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
            {displayTags.length === 0 && <span className="text-xs text-muted-foreground">-</span>}
          </div>
        </div>

        {/* Status */}
        <div className="w-24 flex-shrink-0">
          {entity.syncStatus ? (
            <div className="flex items-center gap-2">
              <span
                className={cn('inline-block h-2 w-2 rounded-full', statusColors[entity.syncStatus])}
              />
              <span className="text-sm text-muted-foreground">
                {statusLabels[entity.syncStatus]}
              </span>
            </div>
          ) : (
            <span className="text-sm text-muted-foreground">-</span>
          )}
        </div>

        {/* Actions */}
        <div className="flex-shrink-0">
          <UnifiedCardActions
            artifact={entity}
            alwaysVisible={true}
            onEdit={onEdit}
            onDelete={onDelete}
            onDeploy={onDeploy}
            onSync={onSync}
            onViewDiff={onViewDiff}
            onRollback={onRollback}
            onCopyCliCommand={onCopyCliCommand}
          />
        </div>
      </div>
    );
  },
  (prevProps, nextProps) => {
    // Custom comparison function to prevent unnecessary re-renders
    // Only re-render if entity data, selected state, or selectable prop changes
    return (
      prevProps.entity.id === nextProps.entity.id &&
      prevProps.entity.name === nextProps.entity.name &&
      prevProps.entity.syncStatus === nextProps.entity.syncStatus &&
      prevProps.entity.description === nextProps.entity.description &&
      prevProps.entity.tags?.join(',') === nextProps.entity.tags?.join(',') &&
      prevProps.selected === nextProps.selected &&
      prevProps.selectable === nextProps.selectable
    );
  }
);
