/**
 * React Query hook for fetching similar artifacts.
 *
 * Calls GET /api/v1/artifacts/{id}/similar and returns a ranked list of
 * artifacts that share content, structure, metadata, or semantic similarity
 * with the queried artifact.
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useSimilarArtifacts(artifact.uuid, {
 *   limit: 10,
 *   minScore: 0.5,
 *   source: 'collection',
 * });
 *
 * if (isLoading) return <Spinner />;
 * return data?.items.map(item => <SimilarArtifactCard key={item.artifact_id} {...item} />);
 * ```
 */

import { useQuery } from '@tanstack/react-query';
import * as React from 'react';
import { apiRequest } from '@/lib/api';
import type {
  SimilarArtifactsResponse,
  SimilarArtifactsOptions,
  SimilaritySource,
} from '@/types/similarity';

// ============================================================================
// Query Keys Factory
// ============================================================================

export const similarArtifactKeys = {
  all: ['similar-artifacts'] as const,
  lists: () => [...similarArtifactKeys.all, 'list'] as const,
  list: (
    artifactId: string,
    limit?: number,
    minScore?: number,
    source?: SimilaritySource
  ) => [...similarArtifactKeys.lists(), artifactId, limit, minScore, source] as const,
};

// ============================================================================
// Viewport Entry Debounce Registry
// ============================================================================

/**
 * Module-level debounce registry for viewport-triggered similarity queries.
 *
 * Batching strategy: client-side debounce + React Query deduplication
 * ─────────────────────────────────────────────────────────────────────
 * When multiple SourceCards enter the viewport simultaneously (rapid scroll,
 * initial render of a dense grid), each card calls `registerViewportEntry(id)`
 * which schedules that card's `enabled` flag to flip after a 200ms debounce
 * window. Cards entering within the same 200ms window are coalesced: their
 * `enabled` flags all flip on the same React render cycle, causing React Query
 * to dispatch all of their requests concurrently in one batch rather than as a
 * scattered sequence of individual renders.
 *
 * React Query's built-in per-query deduplication layer means that if the same
 * artifact UUID appears in multiple views (e.g., pinned + list), only one
 * network request fires regardless of how many components subscribe.
 *
 * The timer is reset on every new entry, so a user slowly scrolling through a
 * long list (entry every ~300ms) gets individual requests — the debounce only
 * fires when entries cluster within 200ms (typical of virtual list mount or
 * fast scroll).
 *
 * Network tab expectation:
 *   - Slow scroll: one request fires ~200ms after each card enters view.
 *   - Fast scroll / initial render burst: requests fire together ~200ms after
 *     the last card in the burst enters the viewport.
 *   - Re-scroll over seen cards: no requests (sticky `inView` + staleTime).
 */

type DebounceCallback = () => void;

interface DebounceEntry {
  callbacks: Set<DebounceCallback>;
  timerId: ReturnType<typeof setTimeout> | null;
}

// One registry per (minScore, source, limit) tuple so that cards with different
// query parameters don't share a debounce window that would collapse different
// query keys into a single delayed burst incorrectly.
const debounceRegistries = new Map<string, DebounceEntry>();

const VIEWPORT_DEBOUNCE_MS = 200;

/**
 * Returns a stable cache key for the debounce registry bucket.
 * Cards sharing the same query parameters share the same debounce window.
 */
function debounceKey(limit: number, minScore: number | undefined, source: SimilaritySource | undefined): string {
  return `${limit}:${minScore ?? ''}:${source ?? ''}`;
}

/**
 * Registers a viewport-entry callback in the debounce queue.
 *
 * The callback will be called after VIEWPORT_DEBOUNCE_MS from the last
 * registration in the same bucket, or immediately if `immediate` is true
 * (used for programmatic / non-scroll triggers).
 *
 * Returns a cleanup function that removes the callback from the queue,
 * useful if the component unmounts before the debounce fires.
 */
function registerViewportEntry(
  bucketKey: string,
  callback: DebounceCallback
): () => void {
  let entry = debounceRegistries.get(bucketKey);
  if (!entry) {
    entry = { callbacks: new Set(), timerId: null };
    debounceRegistries.set(bucketKey, entry);
  }

  entry.callbacks.add(callback);

  // Reset the debounce window on every new entry
  if (entry.timerId !== null) {
    clearTimeout(entry.timerId);
  }

  entry.timerId = setTimeout(() => {
    const current = debounceRegistries.get(bucketKey);
    if (!current) return;

    // Fire all accumulated callbacks in one synchronous pass so they all
    // trigger setState inside the same React render cycle (batched by React 18+).
    current.callbacks.forEach((cb) => cb());
    current.callbacks.clear();
    current.timerId = null;
  }, VIEWPORT_DEBOUNCE_MS);

  return () => {
    const current = debounceRegistries.get(bucketKey);
    if (current) {
      current.callbacks.delete(callback);
    }
  };
}

// ============================================================================
// API Functions
// ============================================================================

async function fetchSimilarArtifacts(
  artifactId: string,
  options: Required<Omit<SimilarArtifactsOptions, 'enabled'>>
): Promise<SimilarArtifactsResponse> {
  const params = new URLSearchParams();

  params.append('limit', String(options.limit));

  if (options.minScore !== undefined) {
    params.append('min_score', String(options.minScore));
  }

  if (options.source !== undefined) {
    params.append('source', options.source);
  }

  return apiRequest<SimilarArtifactsResponse>(
    `/artifacts/${encodeURIComponent(artifactId)}/similar?${params.toString()}`
  );
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Fetch similar artifacts for a given artifact ID.
 *
 * The query is disabled when `artifactId` is undefined or empty. Pass
 * `options.enabled = false` to suppress the query even when an ID is present.
 *
 * Query param mapping:
 *   options.minScore  → min_score  (snake_case in API)
 *   options.source    → source
 *   options.limit     → limit
 *
 * Stale time: 5 minutes (browsing tier per data-flow-patterns).
 * React Query deduplicates requests sharing the same query key, so components
 * subscribed to the same artifactId never issue duplicate network calls.
 */
export function useSimilarArtifacts(
  artifactId: string | undefined,
  options: SimilarArtifactsOptions = {}
) {
  const { limit = 10, minScore, source, enabled } = options;

  return useQuery({
    queryKey: similarArtifactKeys.list(artifactId ?? '', limit, minScore, source),
    queryFn: () =>
      fetchSimilarArtifacts(artifactId!, {
        limit,
        minScore: minScore as number,
        source: source as SimilaritySource,
      }),
    enabled: !!artifactId && enabled !== false,
    staleTime: 5 * 60 * 1000, // 5 minutes — browsing tier
  });
}

// ============================================================================
// Debounced viewport hook
// ============================================================================

/**
 * Wraps `useSimilarArtifacts` with a 200ms debounce gate for viewport-triggered
 * fetches (e.g., SourceCard IntersectionObserver callbacks).
 *
 * Usage in source-card.tsx:
 * ```tsx
 * const [cardRef, inView] = useInView(0.1);
 * const { data } = useDebouncedSimilarArtifacts(artifactId, inView, {
 *   limit: 1,
 *   minScore: thresholds.floor,
 *   source: 'collection',
 * });
 * ```
 *
 * Batching guarantee:
 * - Cards entering within the same 200ms window share one debounce timer.
 * - All their `enabled` flags flip in the same React render cycle.
 * - React Query dispatches their fetches in one concurrent batch.
 * - React Query deduplication prevents duplicate requests for repeated IDs.
 * - Once `gated` is true it never resets, so re-scrolling never re-fetches
 *   within the staleTime window (5 min).
 */
export function useDebouncedSimilarArtifacts(
  artifactId: string | undefined,
  inView: boolean,
  options: SimilarArtifactsOptions = {}
) {
  const { limit = 10, minScore, source } = options;

  // `gated` is the debounce-controlled flag that permits the query.
  // It starts false and only flips to true after the 200ms debounce fires.
  // Once true it is sticky (never resets) to prevent re-fetching on re-scroll.
  const [gated, setGated] = React.useState(false);

  const bucketKey = debounceKey(limit, minScore, source);

  React.useEffect(() => {
    // Only register when the card has entered the viewport and has a valid ID.
    // Already-gated cards skip registration entirely (sticky optimization).
    if (!inView || !artifactId || gated) return;

    const cleanup = registerViewportEntry(bucketKey, () => {
      setGated(true);
    });

    return cleanup;
  }, [inView, artifactId, gated, bucketKey]);

  return useSimilarArtifacts(artifactId, {
    ...options,
    enabled: gated && !!artifactId && options.enabled !== false,
  });
}
