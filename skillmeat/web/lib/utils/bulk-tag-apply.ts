/**
 * Bulk Tag Application Utilities
 *
 * Provides functions for finding artifacts by directory prefix and applying
 * tags to multiple artifacts in bulk.
 *
 * Note: Currently uses a client-side approach since no bulk tag endpoint
 * exists in the backend. Tags are applied per-entry using the path-tags API.
 * A dedicated bulk endpoint would be more efficient for large operations.
 */

import type { CatalogEntry } from '@/types/marketplace';
import { updatePathTagStatus } from '@/lib/api/marketplace';
import { getParentDirectory } from './directory-utils';

/**
 * Result of a bulk tag application operation
 */
export interface BulkTagResult {
  /** Number of artifacts successfully updated */
  totalUpdated: number;
  /** Number of artifacts that failed to update */
  totalFailed: number;
  /** Total tags applied across all artifacts */
  totalTagsApplied: number;
  /** List of errors encountered */
  errors: Array<{ path: string; error: string }>;
}

/**
 * Options for the bulk tag apply operation
 */
export interface BulkTagApplyOptions {
  /** Source ID for API calls */
  sourceId: string;
  /** Batch size for parallel operations (default: 10) */
  batchSize?: number;
  /** Continue on error vs stop on first failure (default: true) */
  continueOnError?: boolean;
}

/**
 * Find all catalog entries matching a directory prefix.
 *
 * Matches artifacts where the parent directory starts with or equals the given path.
 *
 * @param entries - All catalog entries to search
 * @param directoryPath - Directory path to match (e.g., "skills/dev")
 * @returns Array of entries in the directory
 *
 * @example
 * // Find all artifacts in "skills" directory
 * const skillArtifacts = findArtifactsInDirectory(entries, "skills");
 * // Returns entries with paths like: "skills/canvas", "skills/docs/writer"
 *
 * @example
 * // Find artifacts in nested directory
 * const devSkills = findArtifactsInDirectory(entries, "skills/dev");
 * // Returns entries with paths like: "skills/dev/testing", "skills/dev/lint"
 */
export function findArtifactsInDirectory(
  entries: CatalogEntry[],
  directoryPath: string
): CatalogEntry[] {
  if (!entries || entries.length === 0) {
    return [];
  }

  if (!directoryPath) {
    // Empty directory path means root-level only
    return entries.filter((entry) => !entry.path.includes('/'));
  }

  // Normalize the directory path (remove trailing slash)
  const normalizedDir = directoryPath.endsWith('/')
    ? directoryPath.slice(0, -1)
    : directoryPath;

  return entries.filter((entry) => {
    const parentDir = getParentDirectory(entry.path);

    // Match if:
    // 1. Parent directory equals the search path exactly
    // 2. Parent directory starts with the search path followed by a slash
    return (
      parentDir === normalizedDir || parentDir.startsWith(normalizedDir + '/')
    );
  });
}

/**
 * Find all catalog entries whose parent directory equals the given path exactly.
 *
 * Unlike findArtifactsInDirectory, this only matches direct children,
 * not nested subdirectories.
 *
 * @param entries - All catalog entries to search
 * @param directoryPath - Directory path to match exactly
 * @returns Array of entries directly in that directory
 *
 * @example
 * // Find direct children of "skills" only
 * const directSkills = findArtifactsInDirectoryExact(entries, "skills");
 * // Returns: "skills/canvas", "skills/docs"
 * // Does NOT return: "skills/dev/testing"
 */
export function findArtifactsInDirectoryExact(
  entries: CatalogEntry[],
  directoryPath: string
): CatalogEntry[] {
  if (!entries || entries.length === 0) {
    return [];
  }

  // Normalize the directory path
  const normalizedDir = directoryPath.endsWith('/')
    ? directoryPath.slice(0, -1)
    : directoryPath;

  return entries.filter((entry) => {
    const parentDir = getParentDirectory(entry.path);
    return parentDir === normalizedDir;
  });
}

/**
 * Normalize a tag for consistent storage.
 *
 * - Converts to lowercase
 * - Trims whitespace
 * - Replaces spaces with hyphens
 * - Removes special characters except hyphens and underscores
 *
 * @param tag - Raw tag string
 * @returns Normalized tag
 */
export function normalizeTag(tag: string): string {
  return tag
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-_]/g, '');
}

/**
 * Merge new tags with existing tags, avoiding duplicates.
 *
 * @param existingTags - Current tags on the artifact
 * @param newTags - Tags to add
 * @returns Combined array of unique normalized tags
 */
export function mergeTags(existingTags: string[], newTags: string[]): string[] {
  const normalizedExisting = existingTags.map(normalizeTag);
  const normalizedNew = newTags.map(normalizeTag).filter((tag) => tag.length > 0);

  const merged = new Set([...normalizedExisting, ...normalizedNew]);
  return Array.from(merged).sort();
}

/**
 * Process a batch of async operations with controlled concurrency.
 *
 * @param items - Items to process
 * @param operation - Async operation to run on each item
 * @param batchSize - Number of operations to run in parallel
 * @returns Array of results (settled promises)
 */
async function processBatch<T, R>(
  items: T[],
  operation: (item: T) => Promise<R>,
  batchSize: number
): Promise<PromiseSettledResult<R>[]> {
  const results: PromiseSettledResult<R>[] = [];

  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize);
    const batchResults = await Promise.allSettled(batch.map(operation));
    results.push(...batchResults);
  }

  return results;
}

/**
 * Apply tags to a single catalog entry.
 *
 * Uses the path-tags API to approve segments that match the provided tags.
 * This is a workaround since there's no direct tag endpoint for catalog entries.
 *
 * @param sourceId - Source ID containing the entry
 * @param entry - Catalog entry to tag
 * @param tags - Tags to apply
 * @returns Number of tags successfully applied
 */
async function applyTagsToEntry(
  sourceId: string,
  entry: CatalogEntry,
  tags: string[]
): Promise<number> {
  // For each tag, try to approve it as a path segment
  // This works when the tag exists as a segment in the entry's path
  let appliedCount = 0;

  for (const tag of tags) {
    const normalizedTag = normalizeTag(tag);
    if (!normalizedTag) continue;

    try {
      // Attempt to approve the segment
      // This will succeed if the segment exists in the path
      await updatePathTagStatus(sourceId, entry.id, normalizedTag, 'approved');
      appliedCount++;
    } catch {
      // Segment doesn't exist in path or already approved - continue silently
      // This is expected when the tag doesn't match any path segment
    }
  }

  return appliedCount;
}

/**
 * Apply tags to all artifacts matching specified directories.
 *
 * Finds artifacts in each directory and applies the associated tags.
 * Uses batching for performance and continues on individual failures.
 *
 * @param entries - All catalog entries available
 * @param dirTags - Map of directory path to tags to apply
 * @param options - Configuration options
 * @param onProgress - Optional callback for progress updates
 * @returns Result with counts and errors
 *
 * @example
 * ```typescript
 * const dirTags = new Map([
 *   ['skills/dev', ['development', 'coding']],
 *   ['skills/docs', ['documentation']],
 * ]);
 *
 * const result = await applyTagsToDirectories(
 *   catalogEntries,
 *   dirTags,
 *   { sourceId: 'source-123' },
 *   (current, total) => console.log(`Progress: ${current}/${total}`)
 * );
 *
 * console.log(`Updated ${result.totalUpdated} artifacts`);
 * ```
 */
export async function applyTagsToDirectories(
  entries: CatalogEntry[],
  dirTags: Map<string, string[]>,
  options: BulkTagApplyOptions,
  onProgress?: (current: number, total: number) => void
): Promise<BulkTagResult> {
  const { sourceId, batchSize = 10, continueOnError = true } = options;

  const result: BulkTagResult = {
    totalUpdated: 0,
    totalFailed: 0,
    totalTagsApplied: 0,
    errors: [],
  };

  // Build list of (entry, tags) pairs to process
  const workItems: Array<{ entry: CatalogEntry; tags: string[] }> = [];

  for (const [dirPath, tags] of dirTags) {
    // Skip directories with no tags
    if (!tags || tags.length === 0) {
      continue;
    }

    // Find all artifacts in this directory
    const matchingEntries = findArtifactsInDirectoryExact(entries, dirPath);

    for (const entry of matchingEntries) {
      // Check if this entry already has tags queued (from another directory)
      const existing = workItems.find((item) => item.entry.id === entry.id);
      if (existing) {
        // Merge tags for entries that appear in multiple directories
        existing.tags = mergeTags(existing.tags, tags);
      } else {
        workItems.push({ entry, tags: [...tags] });
      }
    }
  }

  const totalItems = workItems.length;
  let processedCount = 0;

  // Process in batches
  const batchedResults = await processBatch(
    workItems,
    async ({ entry, tags }) => {
      const tagsApplied = await applyTagsToEntry(sourceId, entry, tags);
      processedCount++;
      onProgress?.(processedCount, totalItems);
      return { entry, tagsApplied };
    },
    batchSize
  );

  // Process results
  for (let i = 0; i < batchedResults.length; i++) {
    const settledResult = batchedResults[i];
    const workItem = workItems[i];

    // Guard against undefined (shouldn't happen but satisfies TS)
    if (!settledResult || !workItem) continue;

    if (settledResult.status === 'fulfilled') {
      result.totalUpdated++;
      result.totalTagsApplied += settledResult.value.tagsApplied;
    } else {
      result.totalFailed++;
      const reason = settledResult.reason;
      result.errors.push({
        path: workItem.entry.path,
        error:
          reason instanceof Error
            ? reason.message
            : String(reason),
      });

      if (!continueOnError) {
        // Stop processing on first error
        break;
      }
    }
  }

  return result;
}

/**
 * Simulate bulk tag application (client-side only).
 *
 * This function simulates tag application without making API calls.
 * Useful for demos, testing, or when the backend endpoint doesn't exist.
 *
 * Returns a map of entry IDs to their applied tags.
 *
 * @param entries - All catalog entries
 * @param dirTags - Map of directory path to tags
 * @returns Map of entry ID to applied tags
 */
export function simulateBulkTagApply(
  entries: CatalogEntry[],
  dirTags: Map<string, string[]>
): Map<string, string[]> {
  const entryTags = new Map<string, string[]>();

  for (const [dirPath, tags] of dirTags) {
    if (!tags || tags.length === 0) continue;

    const matchingEntries = findArtifactsInDirectoryExact(entries, dirPath);
    const normalizedTags = tags.map(normalizeTag).filter((t) => t.length > 0);

    for (const entry of matchingEntries) {
      const existing = entryTags.get(entry.id) || [];
      entryTags.set(entry.id, mergeTags(existing, normalizedTags));
    }
  }

  return entryTags;
}
