/**
 * @skillmeat/content-viewer — Adapter Interface Definitions
 *
 * Adapter abstractions allow consumers to inject their own data-fetching
 * hooks without coupling content-viewer components to any specific API layer
 * (SkillMeat backend, REST, GraphQL, static JSON, etc.).
 *
 * Consumers implement these interfaces and pass them to ContentViewerProvider.
 * Components then call useContentViewerAdapter() to access the injected hooks.
 *
 * @example
 * ```tsx
 * // In your app, create an adapter that wraps your fetching hooks:
 * const myAdapter: ContentViewerAdapter = {
 *   useFileTree: (artifactId, options) => {
 *     const result = useCatalogFileTree(sourceId, artifactId, options);
 *     return { data: result.data, isLoading: result.isLoading, error: result.error };
 *   },
 *   useFileContent: (artifactId, filePath, options) => {
 *     const result = useCatalogFileContent(sourceId, artifactId, filePath, options);
 *     return { data: result.data, isLoading: result.isLoading, error: result.error };
 *   },
 * };
 *
 * // Wrap your component tree:
 * <ContentViewerProvider adapter={myAdapter}>
 *   <FileTree artifactId={id} />
 * </ContentViewerProvider>
 * ```
 */

import type { FileTreeResponse, FileContentResponse } from './index';

// ============================================================
// Shared options
// ============================================================

/**
 * Common options accepted by all adapter hooks.
 */
export interface AdapterHookOptions {
  /**
   * When false, the hook skips fetching entirely.
   * Useful for conditional/deferred data loading.
   * @default true
   */
  enabled?: boolean;
}

// ============================================================
// Hook return shapes
// ============================================================

/**
 * Normalized return shape for any data-fetching adapter hook.
 * Mirrors the TanStack Query subset that content-viewer components need.
 */
export interface AdapterQueryResult<TData> {
  /** The fetched data, or undefined while loading or on error. */
  data: TData | undefined;
  /** True while the initial fetch is in flight. */
  isLoading: boolean;
  /** Non-null when the most recent fetch failed. */
  error: Error | null;
}

// ============================================================
// File Tree Adapter
// ============================================================

/**
 * Adapter interface for fetching the directory/file tree of an artifact.
 *
 * Implementors must provide a `useFileTree` hook that accepts an artifact
 * identifier and returns loading/error/data state conforming to
 * AdapterQueryResult<FileTreeResponse>.
 */
export interface FileTreeAdapter {
  /**
   * React hook that fetches the file tree for the given artifact.
   *
   * @param artifactId - Opaque identifier for the artifact. The consumer
   *   decides how to map this to their API (e.g. sourceId + path tuple,
   *   UUID, slug, etc.).
   * @param options - Optional control flags (enabled).
   */
  useFileTree: (
    artifactId: string,
    options?: AdapterHookOptions
  ) => AdapterQueryResult<FileTreeResponse>;
}

// ============================================================
// File Content Adapter
// ============================================================

/**
 * Adapter interface for fetching the content of a single file within
 * an artifact.
 *
 * Implementors must provide a `useFileContent` hook that accepts an
 * artifact identifier plus a file path and returns normalized query state.
 */
export interface FileContentAdapter {
  /**
   * React hook that fetches the content of a specific file.
   *
   * @param artifactId - Opaque identifier for the artifact (same semantics
   *   as FileTreeAdapter.useFileTree).
   * @param filePath - Path of the file relative to the artifact root
   *   (e.g. "src/index.md").
   * @param options - Optional control flags (enabled).
   */
  useFileContent: (
    artifactId: string,
    filePath: string,
    options?: AdapterHookOptions
  ) => AdapterQueryResult<FileContentResponse>;
}

// ============================================================
// Combined Adapter
// ============================================================

/**
 * Full content-viewer adapter — combines file tree and file content fetching.
 *
 * Pass an object implementing this interface to ContentViewerProvider.
 * All content-viewer components that need data fetching will access it
 * through useContentViewerAdapter().
 */
export interface ContentViewerAdapter extends FileTreeAdapter, FileContentAdapter {}
