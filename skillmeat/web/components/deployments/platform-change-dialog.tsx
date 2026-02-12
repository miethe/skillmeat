/**
 * Platform Change Confirmation Dialog
 *
 * Provides options for handling existing field values when changing
 * deployment profile platform in edit mode.
 */

'use client';

import * as React from 'react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';

/**
 * Props for PlatformChangeDialog component
 */
export interface PlatformChangeDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback to change dialog open state */
  onOpenChange: (open: boolean) => void;
  /** Platform being changed from */
  fromPlatform: string;
  /** Platform being changed to */
  toPlatform: string;
  /** Callback when user chooses to keep all current values */
  onKeepChanges: () => void;
  /** Callback when user chooses to replace all fields with new defaults */
  onOverwrite: () => void;
  /** Callback when user chooses to append new defaults to multi-value fields */
  onAppend: () => void;
}

/**
 * Format platform identifier for display
 * Converts snake_case to Title Case (e.g., "claude_code" → "Claude Code")
 */
function formatPlatformName(platform: string): string {
  return platform
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * PlatformChangeDialog - Confirmation dialog for platform changes
 *
 * Shows when user changes the platform on an existing deployment profile.
 * Provides three options for handling existing field values:
 * - Keep Changes: Change platform only, preserve all other field values
 * - Overwrite: Replace all fields with new platform defaults
 * - Append: Add new platform defaults to multi-value fields (deduplicated)
 *
 * @example
 * ```tsx
 * <PlatformChangeDialog
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   fromPlatform="claude_code"
 *   toPlatform="cursor"
 *   onKeepChanges={() => handlePlatformChange('keep')}
 *   onOverwrite={() => handlePlatformChange('overwrite')}
 *   onAppend={() => handlePlatformChange('append')}
 * />
 * ```
 */
export function PlatformChangeDialog({
  open,
  onOpenChange,
  fromPlatform,
  toPlatform,
  onKeepChanges,
  onOverwrite,
  onAppend,
}: PlatformChangeDialogProps) {
  const fromPlatformFormatted = formatPlatformName(fromPlatform);
  const toPlatformFormatted = formatPlatformName(toPlatform);

  const handleKeepChanges = () => {
    onKeepChanges();
    onOpenChange(false);
  };

  const handleOverwrite = () => {
    onOverwrite();
    onOpenChange(false);
  };

  const handleAppend = () => {
    onAppend();
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="sm:max-w-[500px]">
        <AlertDialogHeader>
          <AlertDialogTitle>Change Platform?</AlertDialogTitle>
          <AlertDialogDescription>
            You&apos;re changing from <strong>{fromPlatformFormatted}</strong> to{' '}
            <strong>{toPlatformFormatted}</strong>. How should existing field values be handled?
          </AlertDialogDescription>
        </AlertDialogHeader>

        <AlertDialogFooter className="flex-col gap-2 sm:flex-col sm:space-x-0">
          <Button
            variant="outline"
            onClick={handleKeepChanges}
            className="w-full justify-start text-left sm:order-1"
          >
            <div className="flex w-full flex-col items-start gap-1">
              <span className="font-semibold">Keep Changes</span>
              <span className="text-xs font-normal text-muted-foreground">
                Change platform only. Keep all current field values.
              </span>
            </div>
          </Button>

          <Button
            variant="destructive"
            onClick={handleOverwrite}
            className="w-full justify-start text-left sm:order-2"
          >
            <div className="flex w-full flex-col items-start gap-1">
              <span className="font-semibold">Overwrite</span>
              <span className="text-xs font-normal text-destructive-foreground">
                Replace all fields with {toPlatformFormatted} defaults.
              </span>
            </div>
          </Button>

          <Button
            variant="default"
            onClick={handleAppend}
            className="w-full justify-start text-left sm:order-3"
          >
            <div className="flex w-full flex-col items-start gap-1">
              <span className="font-semibold">Append</span>
              <span className="text-xs font-normal opacity-90">
                Add {toPlatformFormatted} defaults to multi-value fields. Single-value fields use new
                defaults.
              </span>
            </div>
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
