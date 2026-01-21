/**
 * DeploymentActions Component
 *
 * Dropdown menu with deployment lifecycle actions (update, remove, view source, view diff).
 * Handles confirmation dialogs for destructive operations.
 */

'use client';

import * as React from 'react';
import { MoreVertical, RefreshCw, Trash2, Eye, FileText, Copy, CheckCircle2 } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import type { Deployment } from './deployment-card';

/**
 * Props for DeploymentActions component
 */
export interface DeploymentActionsProps {
  /** The deployment this action menu is for */
  deployment: Deployment;
  /** Callback to update deployment to latest version */
  onUpdate?: () => void;
  /** Callback to remove deployment from project */
  onRemove?: (removeFiles: boolean) => void;
  /** Callback to view source artifact in collection */
  onViewSource?: () => void;
  /** Callback to view diff between deployed and collection version */
  onViewDiff?: () => void;
  /** Callback to copy deployment path to clipboard */
  onCopyPath?: () => void;
}

/**
 * DeploymentActions - Dropdown menu for deployment lifecycle actions
 *
 * Renders a dropdown menu with context-aware actions for managing deployments.
 * Actions shown depend on deployment status and available callbacks:
 * - Update: Shown if deployment is outdated and onUpdate provided
 * - View Diff: Shown if local modifications exist and onViewDiff provided
 * - View Source: Always shown if onViewSource provided
 * - Copy Path: Always shown if onCopyPath provided
 * - Remove: Always shown if onRemove provided (with confirmation dialog)
 *
 * @example
 * ```tsx
 * <DeploymentActions
 *   deployment={deployment}
 *   onUpdate={() => updateDeployment(deployment.id)}
 *   onRemove={() => removeDeployment(deployment.id)}
 *   onViewSource={() => navigateToArtifact(deployment.artifact_name)}
 *   onViewDiff={() => showDiff(deployment)}
 *   onCopyPath={() => copyToClipboard(deployment.artifact_path)}
 * />
 * ```
 */
export function DeploymentActions({
  deployment,
  onUpdate,
  onRemove,
  onViewSource,
  onViewDiff,
  onCopyPath,
}: DeploymentActionsProps) {
  const [showRemoveDialog, setShowRemoveDialog] = React.useState(false);
  const [isRemoving, setIsRemoving] = React.useState(false);
  const [pathCopied, setPathCopied] = React.useState(false);
  const [removeFiles, setRemoveFiles] = React.useState(true);

  const handleRemove = async () => {
    if (!onRemove) return;

    setIsRemoving(true);
    try {
      await onRemove(removeFiles);
      setShowRemoveDialog(false);
    } catch (error) {
      console.error('Failed to remove deployment:', error);
    } finally {
      setIsRemoving(false);
    }
  };

  const handleCopyPath = async () => {
    if (!onCopyPath) return;

    await onCopyPath();
    setPathCopied(true);

    // Reset copied state after 2 seconds
    setTimeout(() => {
      setPathCopied(false);
    }, 2000);
  };

  // Determine which actions to show
  const showUpdate = deployment.status === 'outdated' && onUpdate;
  const showViewDiff = deployment.local_modifications && onViewDiff;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreVertical className="h-4 w-4" />
            <span className="sr-only">Open menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {/* Update to latest version (only if outdated) */}
          {showUpdate && (
            <>
              <DropdownMenuItem onClick={onUpdate}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Update to Latest
              </DropdownMenuItem>
              <DropdownMenuSeparator />
            </>
          )}

          {/* View diff (only if local modifications) */}
          {showViewDiff && (
            <DropdownMenuItem onClick={onViewDiff}>
              <FileText className="mr-2 h-4 w-4" />
              View Diff
            </DropdownMenuItem>
          )}

          {/* View source artifact */}
          {onViewSource && (
            <DropdownMenuItem onClick={onViewSource}>
              <Eye className="mr-2 h-4 w-4" />
              View in Collection
            </DropdownMenuItem>
          )}

          {/* Copy deployment path */}
          {onCopyPath && (
            <DropdownMenuItem onClick={handleCopyPath}>
              {pathCopied ? (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4 text-green-600" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="mr-2 h-4 w-4" />
                  Copy Path
                </>
              )}
            </DropdownMenuItem>
          )}

          {/* Remove deployment (destructive action) */}
          {onRemove && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => setShowRemoveDialog(true)}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Remove
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Remove Confirmation Dialog */}
      <AlertDialog open={showRemoveDialog} onOpenChange={setShowRemoveDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Deployment?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove "{deployment.artifact_name}" from the project at{' '}
              <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                {deployment.artifact_path}
              </code>
              . This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="flex items-center space-x-2 px-6 pb-4">
            <Checkbox
              id="remove-files"
              checked={removeFiles}
              onCheckedChange={(checked) => setRemoveFiles(checked === true)}
              disabled={isRemoving}
            />
            <label
              htmlFor="remove-files"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Remove files from local filesystem at project path
            </label>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={isRemoving}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRemove}
              disabled={isRemoving}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isRemoving ? 'Removing...' : 'Remove'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
