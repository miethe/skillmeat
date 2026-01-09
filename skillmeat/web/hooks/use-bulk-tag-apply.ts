/**
 * Custom hook for bulk tag application using TanStack Query
 *
 * Provides mutation for applying tags to multiple catalog entries
 * organized by directory. Handles progress tracking, error reporting,
 * and cache invalidation.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback } from 'react';
import { useToast } from './use-toast';
import {
  applyTagsToDirectories,
  simulateBulkTagApply,
  type BulkTagResult,
  type BulkTagApplyOptions,
} from '@/lib/utils/bulk-tag-apply';
import { sourceKeys } from './useMarketplaceSources';
import type { CatalogEntry } from '@/types/marketplace';

/**
 * Options for useBulkTagApply hook
 */
export interface UseBulkTagApplyOptions {
  /** All catalog entries to search and tag */
  entries: CatalogEntry[];
  /** Source ID for API calls */
  sourceId: string;
  /** Callback when operation succeeds */
  onSuccess?: (result: BulkTagResult) => void;
  /** Callback when operation fails */
  onError?: (error: Error) => void;
  /** Use simulation mode (no API calls) - useful for demos */
  simulationMode?: boolean;
}

/**
 * Progress state for bulk tag operation
 */
export interface BulkTagProgress {
  /** Current item being processed */
  current: number;
  /** Total items to process */
  total: number;
  /** Percentage complete (0-100) */
  percentage: number;
}

/**
 * Hook for bulk tag application to catalog entries by directory
 *
 * Provides a mutation function to apply tags to all artifacts in specified
 * directories. Includes progress tracking and error handling.
 *
 * @param options - Configuration options
 * @returns Mutation object with progress state
 *
 * @example
 * ```tsx
 * const { mutate, isPending, progress, reset } = useBulkTagApply({
 *   entries: catalogEntries,
 *   sourceId: 'source-123',
 *   onSuccess: (result) => {
 *     console.log(`Applied tags to ${result.totalUpdated} artifacts`);
 *   },
 * });
 *
 * // Apply tags
 * const dirTags = new Map([
 *   ['skills/dev', ['development', 'coding']],
 * ]);
 * mutate(dirTags);
 *
 * // Show progress
 * if (isPending) {
 *   console.log(`Progress: ${progress.percentage}%`);
 * }
 * ```
 */
export function useBulkTagApply(options: UseBulkTagApplyOptions) {
  const {
    entries,
    sourceId,
    onSuccess,
    onError,
    simulationMode = false,
  } = options;

  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Track progress state
  const [progress, setProgress] = useState<BulkTagProgress>({
    current: 0,
    total: 0,
    percentage: 0,
  });

  // Progress callback
  const handleProgress = useCallback((current: number, total: number) => {
    setProgress({
      current,
      total,
      percentage: total > 0 ? Math.round((current / total) * 100) : 0,
    });
  }, []);

  // Reset progress
  const resetProgress = useCallback(() => {
    setProgress({ current: 0, total: 0, percentage: 0 });
  }, []);

  const mutation = useMutation({
    mutationFn: async (dirTags: Map<string, string[]>): Promise<BulkTagResult> => {
      resetProgress();

      // Count total work items for progress
      let totalEntries = 0;
      for (const [, tags] of dirTags) {
        if (tags && tags.length > 0) {
          // Approximate count - will be refined during operation
          totalEntries++;
        }
      }

      if (simulationMode) {
        // Simulation mode - no API calls
        const entryTags = simulateBulkTagApply(entries, dirTags);
        const totalUpdated = entryTags.size;
        let totalTagsApplied = 0;
        for (const tags of entryTags.values()) {
          totalTagsApplied += tags.length;
        }

        // Simulate progress
        handleProgress(totalUpdated, totalUpdated);

        return {
          totalUpdated,
          totalFailed: 0,
          totalTagsApplied,
          errors: [],
        };
      }

      // Real API mode
      const apiOptions: BulkTagApplyOptions = {
        sourceId,
        batchSize: 10,
        continueOnError: true,
      };

      return applyTagsToDirectories(entries, dirTags, apiOptions, handleProgress);
    },
    onSuccess: (result) => {
      // Invalidate catalog cache to refresh data
      queryClient.invalidateQueries({
        queryKey: sourceKeys.catalog(sourceId),
      });

      // Show success toast
      if (result.totalUpdated > 0) {
        const message = result.totalFailed > 0
          ? `Applied tags to ${result.totalUpdated} artifacts (${result.totalFailed} failed)`
          : `Applied tags to ${result.totalUpdated} artifacts`;

        toast({
          title: 'Tags applied',
          description: message,
          variant: result.totalFailed > 0 ? 'destructive' : 'default',
        });
      } else if (result.totalFailed > 0) {
        toast({
          title: 'Tag application failed',
          description: `Failed to apply tags to ${result.totalFailed} artifacts`,
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'No changes',
          description: 'No artifacts were found in the selected directories',
        });
      }

      onSuccess?.(result);
    },
    onError: (error: Error) => {
      toast({
        title: 'Tag application failed',
        description: error.message,
        variant: 'destructive',
      });

      onError?.(error);
    },
    onSettled: () => {
      // Keep progress visible briefly after completion
      setTimeout(resetProgress, 2000);
    },
  });

  return {
    ...mutation,
    progress,
    resetProgress,
  };
}

/**
 * Query keys for bulk tag operations
 *
 * Used for cache management and invalidation
 */
export const bulkTagKeys = {
  all: ['bulk-tags'] as const,
  history: () => [...bulkTagKeys.all, 'history'] as const,
};
