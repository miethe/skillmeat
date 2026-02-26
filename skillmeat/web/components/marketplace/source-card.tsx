/**
 * Source Card Component
 *
 * Displays a GitHub repository source with artifact counts, status badges,
 * and quick actions (rescan, view details).
 *
 * Visual design follows the unified card style with colored left border accents.
 *
 * Similarity badge integration:
 * When `artifactId` is provided (a collection artifact UUID mapped from this
 * source's primary artifact), the card uses IntersectionObserver to defer
 * the similarity query until the card enters the viewport. This avoids
 * firing N concurrent requests for off-screen cards in a long list.
 */

'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  Github,
  RefreshCw,
  ExternalLink,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Shield,
  ShieldCheck,
  Star,
  Loader2,
  Pencil,
  Trash2,
  Search,
  SearchCheck,
  SearchX,
  Blocks,
  Sparkles,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { GitHubSource, TrustLevel, ScanStatus } from '@/types/marketplace';
import { useDebouncedSimilarArtifacts, useSimilaritySettings } from '@/hooks';
import { SimilarityBadge } from './similarity-badge';
import { TagBadge } from './tag-badge';
import { CountBadge } from './count-badge';

// ============================================================================
// Lazy similarity loader (IntersectionObserver-based)
// ============================================================================

/**
 * Returns `true` once the referenced element has been seen in the viewport.
 * Uses a single shared IntersectionObserver per threshold value for efficiency.
 * The "seen" state is sticky — scrolling the card out of view never resets it,
 * which prevents badge flicker and keeps the query cache warm.
 */
function useInView(threshold = 0.1): [React.RefObject<HTMLDivElement | null>, boolean] {
  const ref = React.useRef<HTMLDivElement | null>(null);
  const [inView, setInView] = React.useState(false);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Once seen, no need to keep observing
    if (inView) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setInView(true);
            observer.disconnect();
          }
        }
      },
      { threshold }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [inView, threshold]);

  return [ref, inView];
}

/**
 * Fetches the top similarity score for a given collection artifact UUID,
 * but only after the card has entered the viewport. Returns `null` when
 * no similar artifacts exist above the floor threshold.
 *
 * Batching strategy (SA-P4-007):
 * Delegates to `useDebouncedSimilarArtifacts`, which coalesces viewport-entry
 * events that arrive within a 200ms window into a single React render cycle.
 * All cards entering the viewport together have their React Query fetches
 * dispatched concurrently rather than as scattered sequential renders.
 * React Query's built-in per-key deduplication prevents duplicate network
 * requests when the same artifact UUID appears across multiple card instances.
 *
 * Network tab expectation:
 *   - Dense initial render / fast scroll: requests fire in one concurrent burst
 *     ~200ms after the last card in the burst becomes visible.
 *   - Slow scroll: one request fires ~200ms after each card individually.
 *   - Re-scroll over already-seen cards: no requests (sticky inView + 5min staleTime).
 */
function useLazySimilarity(artifactId: string | undefined, inView: boolean) {
  const { thresholds, colors } = useSimilaritySettings();

  // useDebouncedSimilarArtifacts manages the debounce gate internally.
  // We pass `inView` as the trigger signal; the hook's `gated` state only
  // flips to true after the 200ms debounce window clears.
  const { data } = useDebouncedSimilarArtifacts(artifactId, inView, {
    limit: 1,
    minScore: thresholds.floor,
    source: 'collection',
  });

  const topScore = data?.items[0]?.composite_score ?? null;

  return { topScore, thresholds, colors };
}

// ============================================================================
// Sub-components
// ============================================================================

interface TrustBadgeProps {
  level: TrustLevel;
}

function TrustBadge({ level }: TrustBadgeProps) {
  const config = {
    untrusted: {
      icon: Shield,
      label: 'Untrusted',
      description: 'This source has not been verified',
      className: 'border-gray-300 text-gray-600 bg-gray-50 dark:bg-gray-900',
    },
    basic: {
      icon: Shield,
      label: 'Basic',
      description: 'This source has basic trust verification',
      className: 'border-gray-400 text-gray-700 bg-gray-100 dark:bg-gray-800',
    },
    verified: {
      icon: ShieldCheck,
      label: 'Verified',
      description: 'This source has been verified as trustworthy',
      className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950',
    },
    official: {
      icon: Star,
      label: 'Official',
      description: 'This is an official Anthropic source',
      className: 'border-purple-500 text-purple-700 bg-purple-50 dark:bg-purple-950',
    },
  }[level];

  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'flex h-6 w-6 items-center justify-center rounded-md border',
              config.className
            )}
            aria-label={`Trust level: ${config.label}. ${config.description}`}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p className="font-medium">Trust: {config.label}</p>
          <p className="text-xs text-muted-foreground">{config.description}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface StatusBadgeProps {
  status: ScanStatus;
  errorMessage?: string;
  lastSyncAt?: string;
}

/**
 * Formats a timestamp into a friendly display format.
 * Returns "Jan 25, 2026 at 2:30 PM" style or relative time for recent dates.
 */
function formatTimestamp(timestamp: string | undefined): string {
  if (!timestamp) return 'Never';

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  // Use relative time for recent timestamps (within 24 hours)
  if (diffHours < 1) {
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    if (diffMinutes < 1) return 'Just now';
    return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
  }
  if (diffHours < 24) {
    const hours = Math.floor(diffHours);
    return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  }

  // Use absolute format for older timestamps
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function StatusBadge({ status, errorMessage, lastSyncAt }: StatusBadgeProps) {
  const config = {
    pending: {
      icon: Clock,
      label: 'Pending',
      description: 'Scan is pending',
      className: 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950',
    },
    scanning: {
      icon: Loader2,
      label: 'Scanning',
      description: 'Currently scanning for artifacts',
      className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950 animate-pulse',
      iconClassName: 'animate-spin',
    },
    success: {
      icon: CheckCircle2,
      label: 'Synced',
      description: 'Successfully synced with repository',
      className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
    },
    error: {
      icon: AlertTriangle,
      label: 'Error',
      description: 'An error occurred during scan',
      className: 'border-red-500 text-red-700 bg-red-50 dark:bg-red-950',
    },
  }[status];

  const Icon = config.icon;
  const ariaLabel =
    status === 'error' && errorMessage
      ? `Scan status: ${config.label}. ${errorMessage}`
      : `Scan status: ${config.label}. ${config.description}`;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'flex h-6 w-6 items-center justify-center rounded-md border',
              config.className
            )}
            aria-label={ariaLabel}
          >
            <Icon
              className={cn('h-3.5 w-3.5', 'iconClassName' in config && config.iconClassName)}
              aria-hidden="true"
            />
          </div>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="font-medium">Sync: {config.label}</p>
          <p className="text-xs text-muted-foreground">
            {status === 'error' && errorMessage ? errorMessage : config.description}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Last synced: {formatTimestamp(lastSyncAt)}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface IndexingBadgeProps {
  indexingEnabled: boolean | null;
  deepIndexingEnabled: boolean | null;
  lastIndexedTreeSha?: string | null;
  lastIndexedAt?: string | null;
}

/**
 * Custom icon: Search with a plus sign inside the magnifying glass
 */
function SearchPlus({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {/* Magnifying glass circle */}
      <circle cx="11" cy="11" r="8" />
      {/* Handle */}
      <path d="m21 21-4.3-4.3" />
      {/* Plus sign inside */}
      <path d="M11 8v6" />
      <path d="M8 11h6" />
    </svg>
  );
}

function IndexingBadge({
  indexingEnabled,
  deepIndexingEnabled,
  lastIndexedTreeSha,
  lastIndexedAt,
}: IndexingBadgeProps) {
  // Determine indexing state
  let state: 'disabled' | 'pending' | 'indexed' | 'deep_indexed' | 'default';
  if (indexingEnabled === false) {
    state = 'disabled';
  } else if (indexingEnabled === true && !lastIndexedTreeSha) {
    state = 'pending';
  } else if (indexingEnabled === true && lastIndexedTreeSha && deepIndexingEnabled === true) {
    state = 'deep_indexed';
  } else if (indexingEnabled === true && lastIndexedTreeSha) {
    state = 'indexed';
  } else {
    state = 'default';
  }

  const config = {
    disabled: {
      icon: SearchX,
      label: 'Disabled',
      description: 'Search indexing is disabled for this source',
      className: 'border-gray-300 text-gray-500 bg-gray-50 dark:bg-gray-900',
    },
    pending: {
      icon: Search,
      label: 'Pending',
      description: 'Source has not been indexed yet',
      className: 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950',
    },
    indexed: {
      icon: SearchCheck,
      label: 'Active',
      description: 'Search index is active',
      className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
    },
    deep_indexed: {
      icon: SearchPlus,
      label: 'Deep Search',
      description: 'Deep content indexing is active',
      className: 'border-purple-500 text-purple-700 bg-purple-50 dark:bg-purple-950',
    },
    default: {
      icon: Search,
      label: 'Default',
      description: 'Using default indexing settings',
      className: 'border-gray-200 text-gray-400 bg-gray-50/50 dark:bg-gray-900/50',
    },
  }[state];

  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'flex h-6 w-6 items-center justify-center rounded-md border',
              config.className
            )}
            aria-label={`Search Index: ${config.label}. ${config.description}`}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          </div>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="font-medium">Search Index: {config.label}</p>
          <p className="text-xs text-muted-foreground">{config.description}</p>
          {state === 'indexed' && lastIndexedAt && (
            <p className="mt-1 text-xs text-muted-foreground">
              Last indexed: {formatTimestamp(lastIndexedAt)}
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export interface SourceCardProps {
  /** GitHub source data */
  source: GitHubSource;
  /**
   * UUID of the corresponding collection artifact, when this source has been
   * imported as a single artifact into the user's collection.
   *
   * When provided, the card will display a SimilarityBadge after the card
   * enters the viewport. When absent (unimported / multi-artifact source),
   * no badge is shown.
   */
  artifactId?: string;
  /** Callback when rescan button is clicked */
  onRescan?: (sourceId: string) => void;
  /** Whether rescan is in progress */
  isRescanning?: boolean;
  /** Custom click handler (default: navigate to detail page) */
  onClick?: () => void;
  /** Callback when edit button is clicked */
  onEdit?: (source: GitHubSource) => void;
  /** Callback when delete button is clicked */
  onDelete?: (source: GitHubSource) => void;
  /** Callback when a tag is clicked (for filtering) */
  onTagClick?: (tag: string) => void;
}

export function SourceCard({
  source,
  artifactId,
  onRescan,
  isRescanning = false,
  onClick,
  onEdit,
  onDelete,
  onTagClick,
}: SourceCardProps) {
  const router = useRouter();

  // IntersectionObserver-based lazy loading for the similarity badge.
  // The ref is attached to the Card element so the query fires as soon as
  // any part of the card enters the viewport.
  const [cardRef, inView] = useInView(0.1);
  const { topScore, thresholds, colors } = useLazySimilarity(artifactId, inView);

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      router.push(`/marketplace/sources/${source.id}`);
    }
  };

  const handleRescan = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRescan?.(source.id);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(source);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(source);
  };

  const handleSourceClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const githubUrl = `https://github.com/${source.owner}/${source.repo_name}`;
    window.open(githubUrl, '_blank', 'noopener,noreferrer');
  };

  // Use counts_by_type if available, otherwise fallback to legacy artifact_count
  const countsByType = source.counts_by_type ?? { skill: source.artifact_count };

  // Description with fallback to repo_description
  const displayDescription = source.description || source.repo_description;

  // Format last sync time
  const lastSyncFormatted = source.last_sync_at
    ? new Date(source.last_sync_at).toLocaleString()
    : 'Never synced';

  return (
    <Card
      ref={cardRef}
      className={cn(
        'group relative cursor-pointer border-l-4 border-l-blue-500',
        'transition-shadow duration-200 hover:shadow-md',
        'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]'
      )}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`View source: ${source.owner}/${source.repo_name}`}
    >
      <div className="flex flex-col gap-3 p-4">
        {/* Zone 1: Header — Repo name + badges */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Github className="h-5 w-5 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
            <div className="min-w-0">
              <h3 className="truncate font-semibold">
                {source.owner}/{source.repo_name}
              </h3>
              <p className="text-xs text-muted-foreground">
                {source.ref}
                {source.root_hint && ` • ${source.root_hint}`}
              </p>
            </div>
          </div>
          <div className="flex flex-shrink-0 items-center gap-1">
            {/* Similarity badge — only shown when artifactId is provided and score
                is above the floor threshold; appears within ~200ms of viewport entry */}
            {artifactId && topScore !== null && (
              <SimilarityBadge
                score={topScore}
                thresholds={thresholds}
                colors={colors}
                className="mr-0.5"
              />
            )}
            <StatusBadge
              status={source.scan_status}
              errorMessage={source.last_error}
              lastSyncAt={source.last_sync_at}
            />
            <TrustBadge level={source.trust_level} />
            <IndexingBadge
              indexingEnabled={source.indexing_enabled ?? null}
              deepIndexingEnabled={source.deep_indexing_enabled ?? null}
              lastIndexedTreeSha={source.last_indexed_tree_sha}
              lastIndexedAt={source.last_indexed_at}
            />
          </div>
        </div>

        {/* Zone 2: Metrics Row — New/Updated badges + artifact count */}
        <div className="flex min-h-[24px] items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            {(source.new_artifact_count ?? 0) > 0 && (
              <Badge
                variant="outline"
                className="flex items-center gap-1 border-emerald-200 bg-emerald-50 text-xs font-medium text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400"
                aria-label={`${source.new_artifact_count} new artifacts`}
              >
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                {source.new_artifact_count} New
              </Badge>
            )}
            {(source.updated_artifact_count ?? 0) > 0 && (
              <Badge
                variant="outline"
                className="flex items-center gap-1 border-amber-200 bg-amber-50 text-xs font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400"
                aria-label={`${source.updated_artifact_count} updated artifacts`}
              >
                <RefreshCw className="h-3 w-3" aria-hidden="true" />
                {source.updated_artifact_count} Updated
              </Badge>
            )}
          </div>
          <CountBadge countsByType={countsByType} />
        </div>

        {/* Zone 3: Description — bounded height, consistent across cards */}
        <div className="min-h-[40px]">
          <p className="line-clamp-2 text-sm text-muted-foreground">
            {displayDescription || '\u00A0'}
          </p>
          {/* Plugin member count badge (CUX-P2-04) and member type breakdown (CUX-P2-05) */}
          {source.composite_member_count != null && source.composite_member_count > 0 && (
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              <div
                className="flex items-center gap-1 rounded-md border border-indigo-300 bg-indigo-50 px-1.5 py-0.5 text-xs font-medium text-indigo-700 dark:border-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
                aria-label={`Plugin contains ${source.composite_member_count} artifacts`}
              >
                <Blocks className="h-3 w-3" aria-hidden="true" />
                <span>{source.composite_member_count} artifact{source.composite_member_count !== 1 ? 's' : ''}</span>
              </div>
              {source.composite_child_types && source.composite_child_types.length > 0 && (
                <div
                  className="flex flex-wrap items-center gap-1"
                  aria-label={`Plugin member types: ${source.composite_child_types.join(', ')}`}
                >
                  {source.composite_child_types.map((childType) => (
                    <span
                      key={childType}
                      className="rounded bg-indigo-100 px-1 py-0.5 text-xs capitalize text-indigo-600 dark:bg-indigo-900 dark:text-indigo-300"
                    >
                      {childType}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Zone 4: Tags — bounded height, consistent across cards */}
        <div className="min-h-[28px] flex items-center">
          <TagBadge tags={source.tags ?? []} maxDisplay={3} onTagClick={onTagClick} />
        </div>

        {/* Zone 5: Import Progress — only shown when imported_count and artifact_count are both > 0 */}
        {(source.imported_count ?? 0) > 0 && source.artifact_count > 0 && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Imported</span>
              <span className="tabular-nums">
                {source.imported_count}/{source.artifact_count}
              </span>
            </div>
            <Progress
              value={((source.imported_count ?? 0) / source.artifact_count) * 100}
              className="h-1.5"
            />
          </div>
        )}

        {/* Zone 6: Actions footer */}
        <div className="flex items-center justify-between border-t pt-2">
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" aria-hidden="true" />
            <span aria-label={`Last synced: ${lastSyncFormatted}`}>{lastSyncFormatted}</span>
          </span>
          <div className="flex items-center gap-1">
            {onEdit && (
              <Button variant="ghost" size="sm" onClick={handleEdit} aria-label="Edit source">
                <Pencil className="h-4 w-4" />
                <span className="sr-only">Edit</span>
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={handleDelete}
                aria-label="Delete source"
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Delete</span>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRescan}
              disabled={isRescanning || source.scan_status === 'scanning'}
              aria-label="Rescan repository"
            >
              <RefreshCw
                className={cn(
                  'h-4 w-4',
                  (isRescanning || source.scan_status === 'scanning') && 'animate-spin'
                )}
              />
              <span className="sr-only">Rescan</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSourceClick}
              aria-label="Open GitHub repository"
            >
              <span className="text-xs">Source</span>
              <ExternalLink className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ============================================================================
// Skeleton
// ============================================================================

export function SourceCardSkeleton() {
  return (
    <Card className="border-l-4 border-l-muted">
      <div className="flex flex-col gap-3 p-4">
        {/* Zone 1: Header skeleton */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5 rounded" />
            <div className="space-y-1">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
          <div className="flex gap-1">
            <Skeleton className="h-6 w-6 rounded-md" />
            <Skeleton className="h-6 w-6 rounded-md" />
            <Skeleton className="h-6 w-6 rounded-md" />
          </div>
        </div>

        {/* Zone 2: Metrics row skeleton */}
        <div className="flex min-h-[24px] items-center justify-between gap-2">
          <div className="flex gap-1.5">
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <Skeleton className="h-5 w-8 rounded-full" />
        </div>

        {/* Zone 3: Description skeleton */}
        <div className="min-h-[40px] space-y-1">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>

        {/* Zone 4: Tags skeleton */}
        <div className="flex min-h-[28px] items-center gap-1">
          <Skeleton className="h-5 w-14 rounded-full" />
          <Skeleton className="h-5 w-12 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>

        {/* Zone 6: Footer skeleton */}
        <div className="flex items-center justify-between border-t pt-2">
          <Skeleton className="h-4 w-32" />
          <div className="flex gap-1">
            <Skeleton className="h-8 w-8 rounded-md" />
            <Skeleton className="h-8 w-16 rounded-md" />
          </div>
        </div>
      </div>
    </Card>
  );
}
