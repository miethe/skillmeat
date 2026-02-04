'use client';

import { useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface TagDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => Promise<void>;
  tagName: string | null;
  artifactCount: number;
}

/**
 * TagDeleteDialog - Confirmation dialog for deleting tags
 *
 * Provides a warning dialog before deleting a tag to prevent accidental deletions.
 * Shows the tag name, artifact count, and requires user confirmation.
 *
 * Features:
 * - Warning message with tag name
 * - Artifact count impact notice
 * - Loading state during deletion
 * - Error handling
 * - Destructive action styling
 *
 * @example
 * ```tsx
 * <TagDeleteDialog
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   onConfirm={handleDeleteTag}
 *   tagName={selectedTag}
 *   artifactCount={3}
 * />
 * ```
 */
export function TagDeleteDialog({
  open,
  onOpenChange,
  onConfirm,
  tagName,
  artifactCount,
}: TagDeleteDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setIsDeleting(true);
    setError(null);

    try {
      await onConfirm();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete tag');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!isDeleting) {
      setError(null);
      onOpenChange(open);
    }
  };

  if (!tagName) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            Delete Tag
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this tag? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <Alert variant="destructive" className="border-red-500/20 bg-red-500/10">
            <AlertDescription className="text-sm">
              <span className="font-medium">Tag to delete:</span>
              <br />
              <code className="mt-1 inline-block rounded bg-red-500/20 px-2 py-1 text-xs">
                {tagName}
              </code>
              <br />
              <span className="mt-2 inline-block text-xs text-muted-foreground">
                {artifactCount > 0
                  ? `This will remove the tag from ${artifactCount} artifact(s). This action cannot be undone.`
                  : 'This tag is not applied to any artifacts.'}
              </span>
            </AlertDescription>
          </Alert>

          {error && (
            <Alert variant="destructive">
              <AlertDescription className="text-sm">{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isDeleting}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleConfirm} disabled={isDeleting}>
            {isDeleting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Tag'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
