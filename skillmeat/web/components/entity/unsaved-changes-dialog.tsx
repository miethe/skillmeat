/**
 * Unsaved Changes Confirmation Dialog
 *
 * Warns users when navigating away from edited content without saving.
 * Offers options to save, discard, or cancel the navigation.
 */

'use client';

import * as React from 'react';
import { AlertTriangle, Save, Trash2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

/**
 * Props for UnsavedChangesDialog component
 */
export interface UnsavedChangesDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback to change dialog open state */
  onOpenChange: (open: boolean) => void;
  /** Current file being edited */
  currentFile?: string;
  /** File being navigated to */
  targetFile?: string;
  /** Callback when user chooses to save changes */
  onSave?: () => Promise<void>;
  /** Callback when user chooses to discard changes */
  onDiscard: () => void;
  /** Callback when user cancels navigation */
  onCancel: () => void;
  /** Whether save is in progress */
  isSaving?: boolean;
}

/**
 * UnsavedChangesDialog - Confirmation dialog for unsaved changes
 *
 * Shows when user tries to navigate away from edited content.
 * Provides three options:
 * - Save & Continue: Save changes then proceed with navigation
 * - Discard: Lose changes and proceed with navigation
 * - Cancel: Stay on current file and keep editing
 *
 * @example
 * ```tsx
 * <UnsavedChangesDialog
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   currentFile="SKILL.md"
 *   targetFile="README.md"
 *   onSave={async () => await saveFile()}
 *   onDiscard={discardAndNavigate}
 *   onCancel={() => setShowDialog(false)}
 * />
 * ```
 */
export function UnsavedChangesDialog({
  open,
  onOpenChange,
  currentFile,
  targetFile,
  onSave,
  onDiscard,
  onCancel,
  isSaving = false,
}: UnsavedChangesDialogProps) {
  const handleSave = async () => {
    if (onSave) {
      await onSave();
    }
  };

  const handleDiscard = () => {
    onDiscard();
    onOpenChange(false);
  };

  const handleCancel = () => {
    onCancel();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Unsaved Changes
          </DialogTitle>
          <DialogDescription>
            You have unsaved changes that will be lost if you continue.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          {currentFile && (
            <div className="text-sm">
              <span className="text-muted-foreground">Current file: </span>
              <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                {currentFile}
              </span>
            </div>
          )}
          {targetFile && (
            <div className="text-sm">
              <span className="text-muted-foreground">Navigating to: </span>
              <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{targetFile}</span>
            </div>
          )}
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-row">
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={isSaving}
            className="sm:order-1"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDiscard}
            disabled={isSaving}
            className="sm:order-2"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Discard
          </Button>
          {onSave && (
            <Button onClick={handleSave} disabled={isSaving} className="sm:order-3">
              {isSaving ? (
                <>
                  <Save className="mr-2 h-4 w-4 animate-pulse" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save & Continue
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
