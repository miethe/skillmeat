/**
 * ConfirmActionDialog Component (UI-3.5)
 *
 * A confirmation dialog for destructive triage actions such as reject,
 * deprecate, or delete. Uses shadcn AlertDialog for accessible modal
 * behavior with focus trapping and Escape dismissal.
 */

'use client';

import * as React from 'react';
import { Loader2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from '@/components/ui/alert-dialog';
import { cn } from '@/lib/utils';
import { buttonVariants } from '@/components/ui/button';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ConfirmActionDialogProps {
  /** Whether the dialog is open. */
  open: boolean;
  /** Callback to control open state. */
  onOpenChange: (open: boolean) => void;
  /** Title displayed at the top of the dialog. */
  title: string;
  /** Descriptive text explaining the action and consequences. */
  description: string;
  /** Label for the confirm button. Defaults to "Confirm". */
  confirmLabel?: string;
  /** Visual variant for the confirm button. Defaults to "default". */
  confirmVariant?: 'default' | 'destructive';
  /** Callback executed when the user confirms the action. */
  onConfirm: () => void;
  /** Whether the confirm action is in progress (shows spinner). */
  isLoading?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * ConfirmActionDialog -- accessible confirmation for destructive actions.
 *
 * Uses Radix AlertDialog which prevents closing on overlay click and
 * requires explicit user action (confirm or cancel).
 *
 * @example
 * ```tsx
 * <ConfirmActionDialog
 *   open={showConfirm}
 *   onOpenChange={setShowConfirm}
 *   title="Reject Memory?"
 *   description="This will deprecate the memory item. It can be restored later."
 *   confirmLabel="Reject"
 *   confirmVariant="destructive"
 *   onConfirm={handleReject}
 *   isLoading={isRejecting}
 * />
 * ```
 */
export function ConfirmActionDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirm',
  confirmVariant = 'default',
  onConfirm,
  isLoading = false,
}: ConfirmActionDialogProps) {
  const handleConfirm = (e: React.MouseEvent) => {
    e.preventDefault();
    onConfirm();
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isLoading}
            aria-busy={isLoading}
            className={cn(
              confirmVariant === 'destructive' &&
                buttonVariants({ variant: 'destructive' })
            )}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
