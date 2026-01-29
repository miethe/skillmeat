/**
 * Entity Actions Component
 *
 * Dropdown menu with entity lifecycle actions (edit, delete, deploy, sync, view diff).
 * Handles confirmation dialogs for destructive operations.
 *
 * @deprecated Use UnifiedCardActions from '@/components/shared/unified-card-actions' for new code.
 * This component is maintained for backward compatibility and adds dialog handling for
 * delete and rollback operations.
 */

'use client';

import * as React from 'react';
import { MoreHorizontal, Pencil, Trash2, Rocket, RefreshCw, FileText, RotateCcw } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { RollbackDialog } from './rollback-dialog';
import { ArtifactDeletionDialog } from './artifact-deletion-dialog';
import type { Artifact } from '@/types/artifact';

/**
 * Props for EntityActions component
 *
 * Controls which actions are available and callbacks for each action.
 */
export interface EntityActionsProps {
  /** The artifact this action menu is for (entity is deprecated alias) */
  entity: Artifact;
  /** Additional CSS classes for the trigger button */
  className?: string;
  /** Whether to always show the button (default: hidden until hover) */
  alwaysVisible?: boolean;
  /** Callback for edit action */
  onEdit?: () => void;
  /** Callback for delete action - shows confirmation dialog */
  onDelete?: () => void;
  /** Callback for deploy action */
  onDeploy?: () => void;
  /** Callback for sync action */
  onSync?: () => void;
  /** Callback for view diff action - only shown when status is "modified" */
  onViewDiff?: () => void;
  /** Callback for rollback action - only shown when status is "modified" or "conflict" */
  onRollback?: () => void;
}

/**
 * EntityActions - Dropdown menu for entity lifecycle actions
 *
 * Renders a dropdown menu with context-aware actions for managing entities.
 * Actions shown depend on entity status and available callbacks:
 * - Edit: Always shown if onEdit provided
 * - Deploy: Shown if onDeploy provided
 * - Sync: Shown if onSync provided
 * - View Diff: Only shown if status is "modified" and onViewDiff provided
 * - Rollback: Only shown if status is "modified" or "conflict" and onRollback provided
 * - Delete: Always shown if onDelete provided (with warning icon)
 *
 * Includes confirmation dialogs for destructive operations (delete, rollback).
 *
 * Features:
 * - Meatballs icon (MoreHorizontal) for modern UI consistency
 * - Hover visibility: hidden by default, shown on hover/touch
 * - Integrated confirmation dialogs for delete and rollback
 *
 * @example
 * ```tsx
 * <EntityActions
 *   entity={skill}
 *   onEdit={() => openEditDialog(skill)}
 *   onDelete={() => deleteEntity(skill.id)}
 *   onDeploy={() => deployTo(skill)}
 *   onViewDiff={() => showDiff(skill)}
 * />
 * ```
 *
 * @param props - EntityActionsProps configuration
 * @returns Dropdown menu component with entity action options
 */
export function EntityActions({
  entity,
  className,
  alwaysVisible = false,
  onEdit,
  onDelete,
  onDeploy,
  onSync,
  onViewDiff,
  onRollback,
}: EntityActionsProps) {
  const [showDeletionDialog, setShowDeletionDialog] = React.useState(false);
  const [showRollbackDialog, setShowRollbackDialog] = React.useState(false);

  const handleRollback = async () => {
    if (!onRollback) return;
    await onRollback();
  };

  const showViewDiff = entity.syncStatus === 'modified' && onViewDiff;
  const showRollback = (entity.syncStatus === 'modified' || entity.syncStatus === 'conflict') && onRollback;

  // Determine which actions are available to show
  const hasPrimaryActions = onDeploy || onSync;
  const hasEditAction = onEdit;
  const hasStatusActions = showViewDiff || showRollback;
  const hasDeleteAction = onDelete;
  const hasAnyAction = hasPrimaryActions || hasEditAction || hasStatusActions || hasDeleteAction;

  // Don't render if no actions
  if (!hasAnyAction) {
    return null;
  }

  return (
    <>
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
            aria-label={`Actions for ${entity.name}`}
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
          {hasPrimaryActions && (hasEditAction || hasStatusActions || hasDeleteAction) && (
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
            <DropdownMenuItem onClick={() => setShowRollbackDialog(true)}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Rollback to Collection
            </DropdownMenuItem>
          )}

          {/* Separator before delete */}
          {hasDeleteAction && (hasPrimaryActions || hasEditAction || hasStatusActions) && (
            <DropdownMenuSeparator />
          )}

          {/* Delete action (destructive) */}
          {onDelete && (
            <DropdownMenuItem
              onClick={() => setShowDeletionDialog(true)}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Artifact Deletion Dialog */}
      <ArtifactDeletionDialog
        artifact={entity as any}
        open={showDeletionDialog}
        onOpenChange={setShowDeletionDialog}
        context={entity.projectPath ? 'project' : 'collection'}
        projectPath={entity.projectPath}
        onSuccess={() => {
          onDelete?.();
          setShowDeletionDialog(false);
        }}
      />

      {/* Rollback Confirmation Dialog */}
      <RollbackDialog
        entity={entity}
        open={showRollbackDialog}
        onOpenChange={setShowRollbackDialog}
        onConfirm={handleRollback}
      />
    </>
  );
}
