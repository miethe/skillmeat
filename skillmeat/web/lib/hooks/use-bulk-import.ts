/**
 * Bulk import hook for marketplace folder view
 *
 * Manages bulk import of catalog entries from a selected folder.
 * Imports items sequentially to avoid rate limiting and provides
 * progress tracking with success/error counts.
 *
 * @example
 * ```tsx
 * const { importAll, isImporting, progress, successCount, errorCount } = useBulkImport({
 *   sourceId: 'source-123',
 *   onSuccess: () => console.log('Import complete'),
 * });
 *
 * // Import all entries in a folder
 * await importAll(folderEntries);
 *
 * // Progress is tracked as percentage (0-100)
 * console.log(`Progress: ${progress}%`);
 * ```
 */

import { useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/hooks';
import { apiRequest } from '@/lib/api';
import { sourceKeys } from '@/hooks';
import type { CatalogEntry, ImportRequest, ImportResult } from '@/types/marketplace';

/**
 * Options for useBulkImport hook
 */
export interface UseBulkImportOptions {
  /** Source ID for the catalog entries */
  sourceId: string;
  /** Conflict resolution strategy when artifact already exists */
  conflictStrategy?: ImportRequest['conflict_strategy'];
  /** Callback on successful import of all items */
  onSuccess?: () => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

/**
 * Result returned by useBulkImport hook
 */
export interface UseBulkImportResult {
  /** Whether import is in progress */
  isImporting: boolean;
  /** Progress percentage (0-100) */
  progress: number;
  /** Number of successfully imported items */
  successCount: number;
  /** Number of failed items */
  errorCount: number;
  /** Number of skipped items (already exist with skip strategy) */
  skippedCount: number;
  /** Execute bulk import for given entries */
  importAll: (entries: CatalogEntry[]) => Promise<void>;
  /** Reset state to initial values */
  reset: () => void;
}

/**
 * Internal state for bulk import progress
 */
interface BulkImportState {
  isImporting: boolean;
  progress: number;
  successCount: number;
  errorCount: number;
  skippedCount: number;
}

const INITIAL_STATE: BulkImportState = {
  isImporting: false,
  progress: 0,
  successCount: 0,
  errorCount: 0,
  skippedCount: 0,
};

/**
 * Import a single catalog entry
 *
 * @param sourceId - Source ID for the catalog entry
 * @param entryId - Catalog entry ID to import
 * @param conflictStrategy - How to handle conflicts
 * @returns Import result for the single entry
 */
async function importSingleEntry(
  sourceId: string,
  entryId: string,
  conflictStrategy: ImportRequest['conflict_strategy']
): Promise<ImportResult> {
  return apiRequest<ImportResult>(`/marketplace/sources/${sourceId}/import`, {
    method: 'POST',
    body: JSON.stringify({
      entry_ids: [entryId],
      conflict_strategy: conflictStrategy,
    } satisfies ImportRequest),
  });
}

/**
 * Hook for bulk importing catalog entries with progress tracking
 *
 * Imports items sequentially to avoid rate limiting issues and provides
 * real-time progress updates. Individual failures do not abort the entire
 * batch - errors are accumulated and reported at the end.
 *
 * @param options - Configuration options
 * @returns Bulk import controls and state
 */
export function useBulkImport(options: UseBulkImportOptions): UseBulkImportResult {
  const { sourceId, conflictStrategy = 'skip', onSuccess, onError } = options;

  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [state, setState] = useState<BulkImportState>(INITIAL_STATE);

  /**
   * Reset state to initial values
   */
  const reset = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  /**
   * Execute bulk import for all provided entries
   *
   * Imports entries sequentially, tracking progress and accumulating
   * success/error counts. Does not abort on individual failures.
   */
  const importAll = useCallback(
    async (entries: CatalogEntry[]): Promise<void> => {
      if (entries.length === 0) {
        toast({
          title: 'No artifacts to import',
          description: 'The selected folder contains no artifacts',
        });
        return;
      }

      // Filter to only importable entries (new or updated status)
      const importableEntries = entries.filter(
        (entry) => entry.status === 'new' || entry.status === 'updated'
      );

      if (importableEntries.length === 0) {
        toast({
          title: 'No artifacts to import',
          description: 'All artifacts in the folder have already been imported',
        });
        return;
      }

      // Initialize import state
      setState({
        isImporting: true,
        progress: 0,
        successCount: 0,
        errorCount: 0,
        skippedCount: 0,
      });

      const total = importableEntries.length;
      let successCount = 0;
      let errorCount = 0;
      let skippedCount = 0;

      try {
        // Import entries sequentially to avoid rate limiting
        for (let i = 0; i < importableEntries.length; i++) {
          const entry = importableEntries[i];

          if (!entry) {
            continue;
          }

          try {
            const result = await importSingleEntry(sourceId, entry.id, conflictStrategy);

            // Accumulate counts from result
            successCount += result.imported_count;
            skippedCount += result.skipped_count;
            errorCount += result.error_count;
          } catch {
            // Individual failure - count as error but continue
            errorCount += 1;
          }

          // Update progress after each item
          const progress = Math.round(((i + 1) / total) * 100);
          setState({
            isImporting: true,
            progress,
            successCount,
            errorCount,
            skippedCount,
          });
        }

        // Invalidate relevant queries to refresh UI
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: sourceKeys.catalogs() }),
          queryClient.invalidateQueries({ queryKey: ['artifacts'] }),
          queryClient.invalidateQueries({ queryKey: ['collections'] }),
        ]);

        // Build summary message
        const parts: string[] = [];
        if (successCount > 0) {
          parts.push(`${successCount} imported`);
        }
        if (skippedCount > 0) {
          parts.push(`${skippedCount} skipped`);
        }
        if (errorCount > 0) {
          parts.push(`${errorCount} failed`);
        }

        const description = parts.length > 0 ? parts.join(', ') : 'No artifacts were processed';

        // Show completion toast
        toast({
          title: 'Bulk import complete',
          description,
          variant: errorCount > 0 ? 'destructive' : 'default',
        });

        // Update final state
        setState({
          isImporting: false,
          progress: 100,
          successCount,
          errorCount,
          skippedCount,
        });

        // Call success callback (even if some failed)
        onSuccess?.();
      } catch (error) {
        // Catastrophic failure (not individual item failure)
        const err = error instanceof Error ? error : new Error('Bulk import failed');

        toast({
          title: 'Import failed',
          description: err.message,
          variant: 'destructive',
        });

        setState((prev) => ({
          ...prev,
          isImporting: false,
        }));

        onError?.(err);
      }
    },
    [sourceId, conflictStrategy, queryClient, toast, onSuccess, onError]
  );

  return {
    isImporting: state.isImporting,
    progress: state.progress,
    successCount: state.successCount,
    errorCount: state.errorCount,
    skippedCount: state.skippedCount,
    importAll,
    reset,
  };
}
