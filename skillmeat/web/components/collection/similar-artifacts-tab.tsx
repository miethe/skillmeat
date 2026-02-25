/**
 * SimilarArtifactsTab Component
 *
 * Displays a grid of artifacts that are similar to the current artifact,
 * ranked by composite similarity score. Intended for use as a tab panel
 * inside ArtifactDetailsModal.
 *
 * States:
 * - Loading: 6-card skeleton grid while query is in flight
 * - Error: Inline error message with retry button (does not crash parent)
 * - Empty: Muted guidance message when no results meet the threshold
 * - Results: Grid of MiniArtifactCard with similarity score badges
 *
 * Error Isolation:
 * - API/fetch errors are caught by the React Query `isError` branch
 * - Unexpected render errors are caught by the internal `TabErrorBoundary`
 *   class component, which renders a fallback within the tab area and
 *   never propagates to the parent modal.
 *
 * @example
 * ```tsx
 * <SimilarArtifactsTab
 *   artifactId={artifact.id}
 *   onArtifactClick={(id) => openArtifact(id)}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { AlertCircle, RefreshCw, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { MiniArtifactCard } from '@/components/collection/mini-artifact-card';
import { useSimilarArtifacts } from '@/hooks';
import type { SimilarArtifact } from '@/types/similarity';
import type { Artifact, ArtifactType } from '@/types/artifact';

// ============================================================================
// Helpers
// ============================================================================

/** Valid artifact types in the ArtifactType union */
const VALID_ARTIFACT_TYPES: ArtifactType[] = [
  'skill',
  'command',
  'agent',
  'mcp',
  'hook',
  'composite',
];

/** Coerces an arbitrary string to a valid ArtifactType, defaulting to 'skill'. */
function toArtifactType(raw: string): ArtifactType {
  return VALID_ARTIFACT_TYPES.includes(raw as ArtifactType)
    ? (raw as ArtifactType)
    : 'skill';
}

/**
 * Converts a SimilarArtifact DTO into the minimal Artifact shape required
 * by MiniArtifactCard. Only fields the card actually renders are populated.
 */
function similarToArtifact(item: SimilarArtifact): Artifact {
  return {
    id: item.artifact_id,
    uuid: item.artifact_id,
    name: item.name,
    type: toArtifactType(item.artifact_type),
    source: item.source ?? '',
    version: '',
    scope: 'user',
    path: '',
    collection: '',
    status: 'synced',
    deployments: [],
    collections: [],
    createdAt: '',
    updatedAt: '',
  } as unknown as Artifact;
}

// ============================================================================
// TabErrorBoundary
// ============================================================================

interface TabErrorBoundaryState {
  hasError: boolean;
  errorMessage: string | null;
}

interface TabErrorBoundaryProps {
  children: React.ReactNode;
}

/**
 * TabErrorBoundary - Class-based React error boundary for tab isolation.
 *
 * Catches unexpected render errors thrown by child components and renders
 * an inline fallback UI instead of propagating the error to the parent modal.
 * The retry button resets the error state, giving React another attempt to
 * render the children.
 *
 * Note: This must be a class component — React's `componentDidCatch` lifecycle
 * is not available as a hook.
 */
class TabErrorBoundary extends React.Component<
  TabErrorBoundaryProps,
  TabErrorBoundaryState
> {
  constructor(props: TabErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, errorMessage: null };
  }

  static getDerivedStateFromError(error: Error): TabErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error?.message ?? 'An unexpected error occurred.',
    };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    // Log to console in dev; in production this would route to an error
    // reporting service (e.g., Sentry). We intentionally keep this minimal
    // to avoid pulling in observability dependencies here.
    if (process.env.NODE_ENV !== 'production') {
      console.error('[SimilarArtifactsTab] Render error caught by boundary:', error, info);
    }
  }

  handleReset = (): void => {
    this.setState({ hasError: false, errorMessage: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="flex flex-col items-center justify-center gap-3 py-10 text-center"
          role="alert"
          aria-live="assertive"
        >
          <AlertCircle
            className="h-8 w-8 text-destructive/70"
            aria-hidden="true"
          />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">
              Something went wrong
            </p>
            <p className="text-xs text-muted-foreground">
              The similar artifacts panel encountered an unexpected error.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={this.handleReset}
            className="gap-1.5"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Try again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

// ============================================================================
// Sub-components: Loading, Error, Empty
// ============================================================================

/** Placeholder card skeleton matching MiniArtifactCard proportions */
function SimilarCardSkeleton() {
  return (
    <div
      className={cn(
        'flex min-h-[140px] flex-col rounded-lg border border-l-[3px] p-3',
        'border-l-muted bg-card'
      )}
      aria-hidden="true"
    >
      {/* Type icon + name row */}
      <div className="flex items-center gap-1.5">
        <Skeleton className="h-4 w-4 rounded-sm" />
        <Skeleton className="h-4 w-2/3" />
      </div>

      {/* Description area */}
      <div className="mt-2 space-y-1">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-4/5" />
        <Skeleton className="h-3 w-3/5" />
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Tag area */}
      <div className="mt-2 flex gap-1">
        <Skeleton className="h-4 w-12 rounded-full" />
        <Skeleton className="h-4 w-14 rounded-full" />
      </div>

      {/* Score badge placeholder */}
      <Skeleton className="absolute right-2 top-2 h-5 w-8 rounded-full" />
    </div>
  );
}

/** Loading state: 6 skeleton cards in the same grid layout as results */
function SimilarArtifactsLoading() {
  return (
    <div
      className="grid grid-cols-2 gap-3 pb-1 pr-1 sm:grid-cols-3"
      aria-label="Loading similar artifacts"
      aria-busy="true"
    >
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="relative">
          <SimilarCardSkeleton />
        </div>
      ))}
    </div>
  );
}

/** Error state: inline message + retry button. Never throws to parent. */
function SimilarArtifactsError({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-10 text-center"
      role="alert"
      aria-live="assertive"
    >
      <AlertCircle
        className="h-8 w-8 text-destructive/70"
        aria-hidden="true"
      />
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">
          Failed to load similar artifacts
        </p>
        <p className="text-xs text-muted-foreground">
          An error occurred while fetching similarity data.
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={onRetry}
        className="gap-1.5"
      >
        <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
        Retry
      </Button>
    </div>
  );
}

/** Empty state: shown when the query succeeds but returns no results */
function SimilarArtifactsEmpty() {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-10 text-center"
      aria-label="No similar artifacts found"
    >
      <Sparkles
        className="h-8 w-8 text-muted-foreground/40"
        aria-hidden="true"
      />
      <div className="space-y-1">
        <p className="text-sm font-medium text-muted-foreground">
          No similar artifacts found
        </p>
        <p className="text-xs text-muted-foreground/70">
          Try adjusting the similarity threshold in{' '}
          <a
            href="/settings?tab=appearance"
            className="underline hover:text-foreground transition-colors"
          >
            Settings
          </a>
          .
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// SimilarArtifactsTabContent (inner, unwrapped)
// ============================================================================

/**
 * Inner implementation of the tab — kept separate so TabErrorBoundary wraps
 * the entire render tree including hooks-driven state branches.
 */
function SimilarArtifactsTabContent({
  artifactId,
  onArtifactClick,
}: SimilarArtifactsTabProps) {
  const { data, isLoading, isError, refetch } = useSimilarArtifacts(artifactId);

  // ---- Loading ----
  if (isLoading) {
    return <SimilarArtifactsLoading />;
  }

  // ---- Error ----
  if (isError) {
    return <SimilarArtifactsError onRetry={() => refetch()} />;
  }

  // ---- Empty ----
  const items = data?.items ?? [];
  if (items.length === 0) {
    return <SimilarArtifactsEmpty />;
  }

  // ---- Results ----
  return (
    <div
      className="grid grid-cols-2 gap-3 pb-1 pr-1 sm:grid-cols-3"
      role="list"
      aria-label={`${items.length} similar artifact${items.length === 1 ? '' : 's'}`}
    >
      {items.map((item) => {
        const artifact = similarToArtifact(item);
        return (
          <div key={item.artifact_id} role="listitem">
            <MiniArtifactCard
              artifact={artifact}
              onClick={() => onArtifactClick?.(item.artifact_id)}
              showScore
              similarityScore={item.composite_score}
              scoreBreakdown={item.breakdown}
              className="cursor-pointer"
            />
          </div>
        );
      })}
    </div>
  );
}

// ============================================================================
// SimilarArtifactsTab (public export)
// ============================================================================

export interface SimilarArtifactsTabProps {
  /**
   * Composite ID of the artifact to find similar items for.
   * Pass `artifact.id` (type:name format like "skill:canvas-design"), not `artifact.uuid`.
   */
  artifactId: string;
  /**
   * Optional callback invoked when the user clicks a similar artifact card.
   * The parent page should use this to open that artifact's detail modal.
   */
  onArtifactClick?: (artifactId: string) => void;
}

/**
 * SimilarArtifactsTab - Grid of artifacts similar to the current artifact
 *
 * Self-contained tab panel that:
 * 1. Fetches similar artifacts via `useSimilarArtifacts` (5-min stale time)
 * 2. Renders loading skeletons while the query is in flight
 * 3. Shows an inline error with retry on failure (no parent crash)
 * 4. Shows a descriptive empty state when no results are returned
 * 5. Renders MiniArtifactCard with `showScore=true` for each result
 *
 * Error isolation:
 * - API failures → handled inline via React Query `isError` branch
 * - Unexpected render errors → caught by `TabErrorBoundary`, fallback shown
 *   within the tab area; the parent ArtifactDetailsModal is never affected
 *
 * Keyboard navigation: cards are focusable via Tab and activated via Enter/Space.
 */
export function SimilarArtifactsTab(props: SimilarArtifactsTabProps) {
  return (
    <TabErrorBoundary>
      <SimilarArtifactsTabContent {...props} />
    </TabErrorBoundary>
  );
}
