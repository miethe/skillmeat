/**
 * SkillMeat concrete adapter for @skillmeat/content-viewer
 *
 * Bridges the generic ContentViewerAdapter interface to SkillMeat's catalog
 * hooks (useCatalogFileTree / useCatalogFileContent), which require a
 * (sourceId, artifactPath) pair rather than a single opaque artifactId.
 *
 * Encoding convention
 * -------------------
 * The adapter encodes the two-part catalog identity into the single
 * `artifactId` string using a "::" delimiter:
 *
 *   artifactId = `${sourceId}::${artifactPath}`
 *
 * Use the exported `makeCatalogArtifactId` helper to produce a correctly
 * formed id, and `parseCatalogArtifactId` when you need to inspect the
 * constituent parts.
 *
 * @example
 * ```tsx
 * import { skillmeatContentViewerAdapter, makeCatalogArtifactId } from '@/lib/content-viewer-adapter';
 * import { ContentViewerProvider, FileTree } from '@skillmeat/content-viewer';
 *
 * const artifactId = makeCatalogArtifactId(source.id, entry.path);
 *
 * <ContentViewerProvider adapter={skillmeatContentViewerAdapter}>
 *   <FileTree artifactId={artifactId} />
 * </ContentViewerProvider>
 * ```
 */

import type { ContentViewerAdapter, AdapterHookOptions } from '@skillmeat/content-viewer';
import { useCatalogFileTree, useCatalogFileContent } from '@/hooks';

// ============================================================
// Encoding helpers
// ============================================================

/** Separator that is safe for both numeric source IDs and unix-style paths. */
const SEPARATOR = '::';

/**
 * Encode a (sourceId, artifactPath) pair into the opaque artifactId string
 * expected by content-viewer components.
 */
export function makeCatalogArtifactId(sourceId: string, artifactPath: string): string {
  return `${sourceId}${SEPARATOR}${artifactPath}`;
}

/**
 * Decode an artifactId produced by `makeCatalogArtifactId` back to its
 * constituent parts. Returns `null` when the id is malformed.
 */
export function parseCatalogArtifactId(
  artifactId: string
): { sourceId: string; artifactPath: string } | null {
  const idx = artifactId.indexOf(SEPARATOR);
  if (idx === -1) return null;
  return {
    sourceId: artifactId.slice(0, idx),
    artifactPath: artifactId.slice(idx + SEPARATOR.length),
  };
}

// ============================================================
// Adapter implementation
// ============================================================

/**
 * SkillMeat-specific ContentViewerAdapter.
 *
 * Wire this into a <ContentViewerProvider adapter={skillmeatContentViewerAdapter}>
 * at the root of any subtree that uses content-viewer components.
 */
export const skillmeatContentViewerAdapter: ContentViewerAdapter = {
  /**
   * Wraps useCatalogFileTree.
   *
   * Decodes artifactId into (sourceId, artifactPath). If the id is malformed
   * the query is disabled and isLoading stays false.
   */
  useFileTree(artifactId: string, options?: AdapterHookOptions) {
    const parsed = parseCatalogArtifactId(artifactId);
    const enabled = options?.enabled !== false && parsed !== null;

    const result = useCatalogFileTree(
      parsed?.sourceId ?? null,
      parsed?.artifactPath ?? null
    );

    // useCatalogFileTree already gates on null inputs, but we additionally
    // gate via the `enabled` option forwarded from the caller.
    if (!enabled) {
      return { data: undefined, isLoading: false, error: null };
    }

    return {
      data: result.data,
      isLoading: result.isLoading,
      error: result.error,
    };
  },

  /**
   * Wraps useCatalogFileContent.
   *
   * Decodes artifactId into (sourceId, artifactPath). filePath is passed
   * through directly. If the id is malformed the query is disabled.
   */
  useFileContent(artifactId: string, filePath: string, options?: AdapterHookOptions) {
    const parsed = parseCatalogArtifactId(artifactId);
    const enabled = options?.enabled !== false && parsed !== null;

    const result = useCatalogFileContent(
      parsed?.sourceId ?? null,
      parsed?.artifactPath ?? null,
      filePath
    );

    if (!enabled) {
      return { data: undefined, isLoading: false, error: null };
    }

    return {
      data: result.data,
      isLoading: result.isLoading,
      error: result.error,
    };
  },
};
