/**
 * Merge result toast notification
 */
'use client';

import { useEffect } from 'react';
import { useToast } from '@/hooks';
import type { MergeExecuteResponse } from '@/types/merge';

interface MergeResultToastProps {
  result: MergeExecuteResponse | null;
  onDismiss?: () => void;
}

export function MergeResultToast({
  result,
  onDismiss,
}: MergeResultToastProps) {
  const { toast } = useToast();

  useEffect(() => {
    if (!result) return;

    if (result.success) {
      // Success with no remaining conflicts
      if (result.conflicts.length === 0) {
        toast({
          title: 'Merge Completed Successfully',
          description: `${result.filesMerged.length} file(s) merged successfully`,
          variant: 'default',
        });
      }
      // Success but with conflicts
      else {
        toast({
          title: 'Merge Completed with Conflicts',
          description: `${result.filesMerged.length} file(s) merged, ${result.conflicts.length} conflict(s) remaining`,
          variant: 'default',
        });
      }
    } else {
      // Failure
      toast({
        title: 'Merge Failed',
        description: result.error || 'An error occurred during the merge',
        variant: 'destructive',
      });
    }

    onDismiss?.();
  }, [result, toast, onDismiss]);

  return null;
}

/**
 * Hook to show merge result toast
 */
export function useMergeResultToast() {
  const { toast } = useToast();

  const showSuccess = (filesMerged: number, conflicts?: number) => {
    if (!conflicts || conflicts === 0) {
      toast({
        title: 'Merge Completed Successfully',
        description: `${filesMerged} file(s) merged successfully`,
        variant: 'default',
      });
    } else {
      toast({
        title: 'Merge Completed with Conflicts',
        description: `${filesMerged} file(s) merged, ${conflicts} conflict(s) remaining`,
        variant: 'default',
      });
    }
  };

  const showError = (error: string) => {
    toast({
      title: 'Merge Failed',
      description: error,
      variant: 'destructive',
    });
  };

  const showConflictResolved = (filePath: string) => {
    toast({
      title: 'Conflict Resolved',
      description: filePath,
      variant: 'default',
    });
  };

  return {
    showSuccess,
    showError,
    showConflictResolved,
  };
}
