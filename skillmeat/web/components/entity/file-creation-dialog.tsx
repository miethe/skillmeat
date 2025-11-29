'use client';

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface FileCreationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (fileName: string) => Promise<void>;
}

/**
 * FileCreationDialog - Dialog for creating new files in an entity
 *
 * Provides a simple input form for entering a new file name/path.
 * Supports nested paths (e.g., "docs/guide.md") for creating files in subdirectories.
 *
 * Features:
 * - Input validation for file names
 * - Loading state during creation
 * - Error handling
 * - Enter key to submit
 *
 * @example
 * ```tsx
 * <FileCreationDialog
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   onConfirm={handleCreateFile}
 * />
 * ```
 */
export function FileCreationDialog({ open, onOpenChange, onConfirm }: FileCreationDialogProps) {
  const [fileName, setFileName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    // Validate file name
    if (!fileName.trim()) {
      setError('File name cannot be empty');
      return;
    }

    // Basic validation for invalid characters
    const invalidChars = /[<>:"|?*\x00-\x1f]/;
    if (invalidChars.test(fileName)) {
      setError('File name contains invalid characters');
      return;
    }

    // Prevent absolute paths
    if (fileName.startsWith('/') || fileName.startsWith('\\')) {
      setError('File name cannot be an absolute path');
      return;
    }

    // Prevent path traversal
    if (fileName.includes('..')) {
      setError('File name cannot contain ".."');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      await onConfirm(fileName.trim());
      // Reset form on success
      setFileName('');
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create file');
    } finally {
      setIsCreating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isCreating) {
      e.preventDefault();
      handleConfirm();
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!isCreating) {
      setFileName('');
      setError(null);
      onOpenChange(open);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create New File</DialogTitle>
          <DialogDescription>
            Enter a file name or path (e.g., "README.md" or "docs/guide.md"). Parent directories
            will be created automatically.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="file-name">File Name / Path</Label>
            <Input
              id="file-name"
              placeholder="example.md"
              value={fileName}
              onChange={(e) => {
                setFileName(e.target.value);
                setError(null);
              }}
              onKeyDown={handleKeyDown}
              disabled={isCreating}
              autoFocus
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isCreating}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={isCreating || !fileName.trim()}>
            {isCreating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create File'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
