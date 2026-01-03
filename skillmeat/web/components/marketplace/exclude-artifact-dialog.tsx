/**
 * Exclude Artifact Confirmation Dialog
 *
 * Confirms marking a catalog entry as excluded (not a valid artifact).
 * Uses AlertDialog for proper accessibility and focus management.
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
import { Loader2 } from 'lucide-react';
import type { CatalogEntry } from '@/types/marketplace';

interface ExcludeArtifactDialogProps {
  entry: CatalogEntry | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isLoading?: boolean;
}

/**
 * ExcludeArtifactDialog - Confirmation dialog for marking artifacts as excluded
 *
 * Provides a confirmation dialog before excluding a catalog entry from the catalog.
 * Excluded entries are hidden from the main view but can be restored from the
 * Excluded Artifacts list.
 *
 * Features:
 * - Shows entry name for confirmation
 * - Loading state during exclusion operation
 * - Destructive action styling
 * - Restoration path mentioned in description
 * - Full accessibility support via AlertDialog
 *
 * @example
 * ```tsx
 * <ExcludeArtifactDialog
 *   entry={selectedEntry}
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   onConfirm={handleExclude}
 *   isLoading={isExcluding}
 * />
 * ```
 */
export function ExcludeArtifactDialog({
  entry,
  open,
  onOpenChange,
  onConfirm,
  isLoading = false,
}: ExcludeArtifactDialogProps) {
  if (!entry) return null;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent onCloseAutoFocus={(e) => e.preventDefault()}>
        <AlertDialogHeader>
          <AlertDialogTitle>Mark as Not an Artifact?</AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <span className="block">
              Are you sure you want to mark{' '}
              <strong className="text-foreground">{entry.name}</strong> as
              excluded?
            </span>
            <span className="block">
              This will hide it from the catalog. You can restore it later from
              the Excluded Artifacts list.
            </span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onConfirm();
            }}
            disabled={isLoading}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Excluding...
              </>
            ) : (
              'Mark as Excluded'
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
