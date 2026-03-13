'use client';

/**
 * ContentViewerProvider — React context provider for the content-viewer adapter.
 *
 * Decouples content-viewer components from any specific data-fetching
 * implementation. Consumers supply a ContentViewerAdapter that components
 * access via useContentViewerAdapter().
 *
 * @example
 * ```tsx
 * import {
 *   ContentViewerProvider,
 *   type ContentViewerAdapter,
 * } from '@skillmeat/content-viewer';
 *
 * // Build an adapter that wraps your application's hooks:
 * const adapter: ContentViewerAdapter = {
 *   useFileTree: (artifactId, options) => {
 *     const { data, isLoading, error } = useCatalogFileTree(
 *       mySourceId,
 *       artifactId,
 *       { enabled: options?.enabled }
 *     );
 *     return { data, isLoading, error: error ?? null };
 *   },
 *   useFileContent: (artifactId, filePath, options) => {
 *     const { data, isLoading, error } = useCatalogFileContent(
 *       mySourceId,
 *       artifactId,
 *       filePath,
 *       { enabled: options?.enabled }
 *     );
 *     return { data, isLoading, error: error ?? null };
 *   },
 * };
 *
 * function App() {
 *   return (
 *     <ContentViewerProvider adapter={adapter}>
 *       <YourContentViewerTree />
 *     </ContentViewerProvider>
 *   );
 * }
 * ```
 */

import React, { createContext, useContext } from 'react';
import type { ContentViewerAdapter } from '../types/adapters';

// ============================================================
// Context
// ============================================================

/**
 * Internal context value type. Undefined means the provider has not been
 * mounted — components use this to detect misconfiguration early.
 */
type ContentViewerContextValue = ContentViewerAdapter | undefined;

const ContentViewerContext = createContext<ContentViewerContextValue>(undefined);

ContentViewerContext.displayName = 'ContentViewerContext';

// ============================================================
// Provider
// ============================================================

export interface ContentViewerProviderProps {
  /**
   * An object implementing ContentViewerAdapter. Components rendered
   * inside this provider call useContentViewerAdapter() to access it.
   */
  adapter: ContentViewerAdapter;
  children: React.ReactNode;
}

/**
 * Wrap your component tree with ContentViewerProvider to supply a
 * data-fetching adapter to all content-viewer components.
 *
 * You must mount exactly one provider per logical content-viewer subtree.
 * Nesting is allowed — inner providers shadow outer ones for their subtrees.
 */
export function ContentViewerProvider({
  adapter,
  children,
}: ContentViewerProviderProps): React.JSX.Element {
  return (
    <ContentViewerContext.Provider value={adapter}>
      {children}
    </ContentViewerContext.Provider>
  );
}

// ============================================================
// Consumer Hook
// ============================================================

/**
 * Returns the ContentViewerAdapter injected by the nearest
 * ContentViewerProvider ancestor.
 *
 * Throws a descriptive error when called outside a ContentViewerProvider
 * so misconfiguration is caught at runtime rather than producing silent
 * undefined behaviour.
 *
 * @throws {Error} When called outside a ContentViewerProvider.
 *
 * @example
 * ```tsx
 * function MyFileTree({ artifactId }: { artifactId: string }) {
 *   const { useFileTree } = useContentViewerAdapter();
 *   const { data, isLoading, error } = useFileTree(artifactId);
 *   // ...
 * }
 * ```
 */
export function useContentViewerAdapter(): ContentViewerAdapter {
  const ctx = useContext(ContentViewerContext);

  if (ctx === undefined) {
    throw new Error(
      '[content-viewer] useContentViewerAdapter() was called outside of a ' +
        '<ContentViewerProvider>. ' +
        'Wrap the component tree that uses content-viewer components with ' +
        '<ContentViewerProvider adapter={...}> and supply a ContentViewerAdapter.'
    );
  }

  return ctx;
}
