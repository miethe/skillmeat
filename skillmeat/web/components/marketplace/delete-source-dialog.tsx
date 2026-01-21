/**
 * Delete Source Confirmation Dialog
 *
 * Confirms deletion of a GitHub source with warning about cascade effects.
 * Uses AlertDialog for destructive action confirmation with proper accessibility.
 */

'use client';

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
import { AlertTriangle, Loader2 } from 'lucide-react';
import { useDeleteSource } from '@/hooks';
import type { GitHubSource } from '@/types/marketplace';

interface DeleteSourceDialogProps {
  source: GitHubSource | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

/**
 * DeleteSourceDialog - Confirmation dialog for deleting GitHub sources
 *
 * Provides a warning dialog before deleting a source to prevent accidental deletions.
 * Shows the source name, artifact count, and cascade deletion warning.
 *
 * Features:
 * - Warning message with source name and artifact count
 * - Loading state during deletion
 * - Error handling via useDeleteSource hook
 * - Destructive action styling
 * - Cascade deletion warning
 *
 * @example
 * ```tsx
 * <DeleteSourceDialog
 *   source={selectedSource}
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   onSuccess={() => router.push('/marketplace')}
 * />
 * ```
 */
export function DeleteSourceDialog({
  source,
  open,
  onOpenChange,
  onSuccess,
}: DeleteSourceDialogProps) {
  const deleteSource = useDeleteSource();

  const handleDelete = async () => {
    if (!source) return;

    try {
      await deleteSource.mutateAsync(source.id);
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      // Error handled by mutation hook (shows toast)
    }
  };

  if (!source) return null;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Delete Source
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <p>
              Are you sure you want to delete{' '}
              <strong className="text-foreground">
                {source.owner}/{source.repo_name}
              </strong>
              ?
            </p>
            <p className="text-destructive">
              This will also remove {source.artifact_count} artifact
              {source.artifact_count !== 1 ? 's' : ''} from the catalog. This action cannot be
              undone.
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteSource.isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={deleteSource.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {deleteSource.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Source'
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
