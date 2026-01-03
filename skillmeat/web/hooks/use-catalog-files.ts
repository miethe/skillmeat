/**
 * Custom hooks for catalog file operations using TanStack Query
 *
 * Provides data fetching, caching, and state management for marketplace
 * catalog artifact files. Used in the catalog entry modal to display
 * file trees and file content.
 */

import { useQuery } from '@tanstack/react-query';
import {
  fetchCatalogFileTree,
  fetchCatalogFileContent,
  type FileTreeResponse,
  type FileContentResponse,
} from '@/lib/api/catalog';

/**
 * Query keys factory for type-safe cache management
 *
 * Hierarchical structure enables targeted cache invalidation:
 * - catalogKeys.all: All catalog-related queries
 * - catalogKeys.trees(): All file tree queries
 * - catalogKeys.tree(sourceId, artifactPath): Specific file tree
 * - catalogKeys.contents(): All file content queries
 * - catalogKeys.content(sourceId, artifactPath, filePath): Specific file content
 */
export const catalogKeys = {
  all: ['catalog'] as const,
  trees: () => [...catalogKeys.all, 'tree'] as const,
  tree: (sourceId: string, artifactPath: string) =>
    [...catalogKeys.trees(), sourceId, artifactPath] as const,
  contents: () => [...catalogKeys.all, 'content'] as const,
  content: (sourceId: string, artifactPath: string, filePath: string) =>
    [...catalogKeys.contents(), sourceId, artifactPath, filePath] as const,
};

/**
 * Fetch file tree for a catalog artifact
 *
 * Returns the directory structure of an artifact from a marketplace source.
 * Useful for displaying file browsers and selecting files to view.
 *
 * @param sourceId - Marketplace source ID (null/undefined disables query)
 * @param artifactPath - Path to the artifact within the repository (null/undefined disables query)
 * @returns Query result with file tree data
 *
 * @example
 * ```tsx
 * function FileTree({ sourceId, artifactPath }) {
 *   const { data, isLoading, error } = useCatalogFileTree(sourceId, artifactPath);
 *
 *   if (isLoading) return <Spinner />;
 *   if (error) return <Error message={error.message} />;
 *
 *   return (
 *     <ul>
 *       {data?.files.map(file => (
 *         <li key={file.path}>
 *           {file.type === 'tree' ? '📁' : '📄'} {file.path}
 *         </li>
 *       ))}
 *     </ul>
 *   );
 * }
 * ```
 */
export function useCatalogFileTree(
  sourceId: string | null | undefined,
  artifactPath: string | null | undefined
) {
  return useQuery<FileTreeResponse, Error>({
    queryKey: catalogKeys.tree(sourceId!, artifactPath!),
    queryFn: () => fetchCatalogFileTree(sourceId!, artifactPath!),
    // Only fetch when both sourceId and artifactPath are provided
    enabled: sourceId != null && artifactPath != null && artifactPath !== '',
    // File trees change less frequently but users browse them actively
    staleTime: 5 * 60 * 1000, // 5 minutes - data considered fresh
    gcTime: 30 * 60 * 1000, // 30 minutes - keep inactive data in cache
  });
}

/**
 * Fetch content of a specific file from a catalog artifact
 *
 * Returns the decoded content of a file from a marketplace artifact.
 * Used for displaying file previews in the catalog entry modal.
 *
 * @param sourceId - Marketplace source ID (null/undefined disables query)
 * @param artifactPath - Path to the artifact within the repository (null/undefined disables query)
 * @param filePath - Path to the file within the artifact (null/undefined disables query)
 * @returns Query result with file content data
 *
 * @example
 * ```tsx
 * function FileViewer({ sourceId, artifactPath, filePath }) {
 *   const { data, isLoading, error } = useCatalogFileContent(
 *     sourceId,
 *     artifactPath,
 *     filePath
 *   );
 *
 *   if (isLoading) return <Spinner />;
 *   if (error) return <Error message={error.message} />;
 *
 *   return (
 *     <pre>
 *       <code>{data?.content}</code>
 *     </pre>
 *   );
 * }
 * ```
 */
export function useCatalogFileContent(
  sourceId: string | null | undefined,
  artifactPath: string | null | undefined,
  filePath: string | null | undefined
) {
  return useQuery<FileContentResponse, Error>({
    queryKey: catalogKeys.content(sourceId!, artifactPath!, filePath!),
    queryFn: () => fetchCatalogFileContent(sourceId!, artifactPath!, filePath!),
    // Only fetch when all parameters are provided
    enabled:
      sourceId != null &&
      artifactPath != null &&
      artifactPath !== '' &&
      filePath != null &&
      filePath !== '',
    // File contents rarely change and are larger - use aggressive caching
    staleTime: 30 * 60 * 1000, // 30 minutes - data considered fresh
    gcTime: 2 * 60 * 60 * 1000, // 2 hours - keep inactive data in cache
  });
}
