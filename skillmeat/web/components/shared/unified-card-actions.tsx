/**
 * Unified Card Actions Component
 *
 * A shared dropdown menu for artifact/entity actions that provides consistent
 * behavior across all pages (collection, manage, etc.).
 *
 * Features:
 * - Meatballs icon (MoreHorizontal) for modern UI consistency
 * - Hover visibility: hidden by default, shown on hover/touch
 * - Conditional menu items based on provided callbacks
 * - Status-aware actions (View Diff, Rollback)
 * - Integrated confirmation dialogs for destructive operations
 */

'use client';

import * as React from 'react';
import {
  MoreHorizontal,
  Pencil,
  Trash2,
  Rocket,
  RefreshCw,
  FileText,
  RotateCcw,
  FolderPlus,
  Layers,
  Copy,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { Artifact, SyncStatus } from '@/types/artifact';

/**
 * Props for UnifiedCardActions component
 *
 * All action callbacks are optional. Menu items are shown only when
 * their corresponding callback is provided.
 */
export interface UnifiedCardActionsProps {
  /** The artifact this action menu is for */
  artifact: Artifact;
  /** Additional CSS classes for the trigger button */
  className?: string;
  /** Whether to always show the button (default: hidden until hover) */
  alwaysVisible?: boolean;

  // Primary actions
  /** Callback for deploy action */
  onDeploy?: () => void;
  /** Callback for sync action */
  onSync?: () => void;
  /** Callback for edit action */
  onEdit?: () => void;
  /** Callback for delete action */
  onDelete?: () => void;

  // Status-dependent actions
  /** Callback for view diff action (typically shown when status is "modified") */
  onViewDiff?: () => void;
  /** Callback for rollback action (typically shown when status is "modified" or "conflict") */
  onRollback?: () => void;

  // Collection/organization actions
  /** Callback for adding to or moving between collections */
  onMoveToCollection?: () => void;
  /** Callback for managing group membership */
  onAddToGroup?: () => void;

  // Utility actions
  /** Callback for copying CLI command to clipboard */
  onCopyCliCommand?: () => void;
}

/**
 * Helper to determine if View Diff should be shown based on sync status
 */
function shouldShowViewDiff(status?: SyncStatus): boolean {
  return status === 'modified';
}

/**
 * Helper to determine if Rollback should be shown based on sync status
 */
function shouldShowRollback(status?: SyncStatus): boolean {
  return status === 'modified' || status === 'conflict';
}

/**
 * UnifiedCardActions - Dropdown menu for artifact/entity lifecycle actions
 *
 * Renders a dropdown menu with context-aware actions for managing artifacts.
 * Actions shown depend on which callbacks are provided and artifact status:
 *
 * - Deploy: Shown if onDeploy provided
 * - Sync: Shown if onSync provided
 * - Move to Collection: Shown if onMoveToCollection provided
 * - Add to Group: Shown if onAddToGroup provided
 * - Edit: Shown if onEdit provided
 * - View Diff: Only shown if status is "modified" and onViewDiff provided
 * - Rollback: Only shown if status is "modified" or "conflict" and onRollback provided
 * - Delete: Shown if onDelete provided (with destructive styling)
 *
 * @example Basic usage
 * ```tsx
 * <UnifiedCardActions
 *   artifact={skill}
 *   onEdit={() => openEditDialog(skill)}
 *   onDelete={() => confirmDelete(skill.id)}
 *   onDeploy={() => deployTo(skill)}
 * />
 * ```
 *
 * @example With collection actions
 * ```tsx
 * <UnifiedCardActions
 *   artifact={skill}
 *   onDeploy={() => handleDeploy(skill)}
 *   onMoveToCollection={() => openMoveDialog(skill)}
 *   onAddToGroup={() => openGroupDialog(skill)}
 *   onEdit={() => openEditDialog(skill)}
 *   onDelete={() => confirmDelete(skill)}
 * />
 * ```
 *
 * @example Always visible (for list/table views)
 * ```tsx
 * <UnifiedCardActions
 *   artifact={skill}
 *   alwaysVisible={true}
 *   onEdit={() => edit(skill)}
 *   onDelete={() => remove(skill)}
 * />
 * ```
 */
export function UnifiedCardActions({
  artifact,
  className,
  alwaysVisible = false,
  onDeploy,
  onSync,
  onEdit,
  onDelete,
  onViewDiff,
  onRollback,
  onMoveToCollection,
  onAddToGroup,
  onCopyCliCommand,
}: UnifiedCardActionsProps) {
  // Determine which status-dependent actions to show
  const showViewDiff = shouldShowViewDiff(artifact.syncStatus) && !!onViewDiff;
  const showRollback = shouldShowRollback(artifact.syncStatus) && !!onRollback;

  // Check if we have any actions to show
  const hasAnyAction =
    onDeploy ||
    onSync ||
    onMoveToCollection ||
    onAddToGroup ||
    onEdit ||
    showViewDiff ||
    showRollback ||
    onDelete ||
    onCopyCliCommand;

  // Don't render anything if no actions are available
  if (!hasAnyAction) {
    return null;
  }

  // Determine if we need separators (to group related actions)
  const hasPrimaryActions = onDeploy || onSync;
  const hasOrganizationActions = onMoveToCollection || onAddToGroup;
  const hasEditAction = onEdit;
  const hasStatusActions = showViewDiff || showRollback;
  const hasUtilityActions = onCopyCliCommand;
  const hasDeleteAction = onDelete;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            'h-8 w-8 transition-opacity',
            // Hover visibility: hidden by default on desktop, always visible on touch
            !alwaysVisible && 'opacity-0 group-hover:opacity-100 md:opacity-0',
            // Touch devices should always show
            !alwaysVisible && 'touch:opacity-100',
            className
          )}
          onClick={(e) => e.stopPropagation()}
          aria-label={`Actions for ${artifact.name}`}
        >
          <MoreHorizontal className="h-4 w-4" />
          <span className="sr-only">Open menu</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
        {/* Primary actions: Deploy, Sync */}
        {onDeploy && (
          <DropdownMenuItem onClick={onDeploy}>
            <Rocket className="mr-2 h-4 w-4" />
            Deploy to Project
          </DropdownMenuItem>
        )}
        {onSync && (
          <DropdownMenuItem onClick={onSync}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Sync to Collection
          </DropdownMenuItem>
        )}

        {/* Separator after primary actions */}
        {hasPrimaryActions &&
          (hasOrganizationActions || hasEditAction || hasStatusActions || hasDeleteAction) && (
            <DropdownMenuSeparator />
          )}

        {/* Organization actions: Collection, Groups */}
        {onMoveToCollection && (
          <DropdownMenuItem onClick={onMoveToCollection}>
            <FolderPlus className="mr-2 h-4 w-4" />
            {artifact.collection ? 'Move to Collection' : 'Add to Collection'}
          </DropdownMenuItem>
        )}
        {onAddToGroup && (
          <DropdownMenuItem onClick={onAddToGroup}>
            <Layers className="mr-2 h-4 w-4" />
            Add to Group
          </DropdownMenuItem>
        )}

        {/* Separator after organization actions */}
        {hasOrganizationActions && (hasEditAction || hasStatusActions || hasDeleteAction) && (
          <DropdownMenuSeparator />
        )}

        {/* Edit action */}
        {onEdit && (
          <DropdownMenuItem onClick={onEdit}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </DropdownMenuItem>
        )}

        {/* Status-dependent actions: View Diff, Rollback */}
        {showViewDiff && (
          <DropdownMenuItem onClick={onViewDiff}>
            <FileText className="mr-2 h-4 w-4" />
            View Diff
          </DropdownMenuItem>
        )}
        {showRollback && (
          <DropdownMenuItem onClick={onRollback}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Rollback to Collection
          </DropdownMenuItem>
        )}

        {/* Utility actions: Copy CLI Command */}
        {onCopyCliCommand && (
          <DropdownMenuItem onClick={onCopyCliCommand}>
            <Copy className="mr-2 h-4 w-4" />
            Copy CLI Command
          </DropdownMenuItem>
        )}

        {/* Separator before delete */}
        {hasDeleteAction &&
          (hasPrimaryActions ||
            hasOrganizationActions ||
            hasEditAction ||
            hasStatusActions ||
            hasUtilityActions) && <DropdownMenuSeparator />}

        {/* Delete action (destructive) */}
        {onDelete && (
          <DropdownMenuItem onClick={onDelete} className="text-destructive focus:text-destructive">
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
