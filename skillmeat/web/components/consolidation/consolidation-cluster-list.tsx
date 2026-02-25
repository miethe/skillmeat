'use client';

import { useState } from 'react';
import { Package, Terminal, Bot, Server, Webhook, Blocks, Layers, AlertCircle, EyeOff, RotateCcw } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useConsolidationClusters, useUnignorePair } from '@/hooks';
import { ConsolidationClusterDetail } from './consolidation-cluster-detail';
import type { ConsolidationCluster } from '@/types/similarity';

// ============================================================================
// Constants
// ============================================================================

const artifactTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  skill: Package,
  command: Terminal,
  agent: Bot,
  mcp: Server,
  hook: Webhook,
  composite: Blocks,
};

const artifactTypeColors: Record<string, string> = {
  skill: 'bg-blue-500/10 text-blue-700 border-blue-500/20 dark:text-blue-400',
  command: 'bg-purple-500/10 text-purple-700 border-purple-500/20 dark:text-purple-400',
  agent: 'bg-green-500/10 text-green-700 border-green-500/20 dark:text-green-400',
  mcp: 'bg-orange-500/10 text-orange-700 border-orange-500/20 dark:text-orange-400',
  hook: 'bg-pink-500/10 text-pink-700 border-pink-500/20 dark:text-pink-400',
  composite: 'bg-indigo-500/10 text-indigo-700 border-indigo-500/20 dark:text-indigo-400',
};

const artifactTypeLabels: Record<string, string> = {
  skill: 'Skill',
  command: 'Command',
  agent: 'Agent',
  mcp: 'MCP Server',
  hook: 'Hook',
  composite: 'Plugin',
};

// ============================================================================
// Helpers
// ============================================================================

/**
 * Returns the most common artifact type across a cluster's members.
 * Falls back to "mixed" when members span multiple types.
 */
function getPrimaryType(cluster: ConsolidationCluster): string {
  const counts: Record<string, number> = {};
  for (const member of cluster.members) {
    counts[member.artifact_type] = (counts[member.artifact_type] ?? 0) + 1;
  }
  const entries = Object.entries(counts);
  if (entries.length === 0) return 'unknown';
  if (entries.length > 1) return 'mixed';
  return entries[0]?.[0] ?? 'unknown';
}

/**
 * Returns the name of the primary artifact (first member) in the cluster.
 */
function getPrimaryArtifactName(cluster: ConsolidationCluster): string {
  return cluster.members[0]?.name ?? '(unnamed)';
}

/**
 * Returns the highest pairwise score across all pairs (including ignored ones)
 * as a percentage string like "87%".
 */
function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/**
 * Determines whether a cluster is fully ignored (all pairs ignored).
 */
function isFullyIgnored(cluster: ConsolidationCluster): boolean {
  return cluster.pairs.length > 0 && cluster.pairs.every((pair) => pair.ignored);
}

/**
 * Determines whether a cluster has any ignored pairs.
 */
function hasIgnoredPairs(cluster: ConsolidationCluster): boolean {
  return cluster.pairs.some((pair) => pair.ignored);
}

/**
 * Returns the score band label and variant for a given 0–1 score.
 */
function getScoreBand(score: number): { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' } {
  if (score >= 0.8) return { label: 'high', variant: 'default' };
  if (score >= 0.55) return { label: 'partial', variant: 'secondary' };
  return { label: 'low', variant: 'outline' };
}

// ============================================================================
// Loading skeleton
// ============================================================================

function ClusterListSkeleton() {
  return (
    <div
      role="table"
      aria-label="Loading consolidation clusters"
      aria-busy="true"
      className="rounded-md border"
    >
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Artifacts</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Top Score</TableHead>
            <TableHead>Primary Artifact</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, i) => (
            <TableRow key={i}>
              <TableCell>
                <Skeleton className="h-5 w-8" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-20 rounded-full" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-12 rounded-full" />
              </TableCell>
              <TableCell>
                <div className="space-y-1.5">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ============================================================================
// Empty state
// ============================================================================

function ClusterListEmpty() {
  return (
    <div
      className="flex flex-col items-center justify-center py-16 text-center"
      role="status"
      aria-label="No consolidation clusters found"
    >
      <Layers className="mx-auto mb-4 h-12 w-12 text-muted-foreground/40" aria-hidden="true" />
      <h3 className="text-base font-semibold text-foreground">No duplicate clusters found</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        No artifacts in your collection exceed the similarity threshold. You&apos;re all set!
      </p>
    </div>
  );
}

// ============================================================================
// Type badge helper
// ============================================================================

interface TypeBadgeProps {
  type: string;
}

function TypeBadge({ type }: TypeBadgeProps) {
  const Icon = artifactTypeIcons[type];
  const colorClass = artifactTypeColors[type] ?? 'bg-gray-500/10 text-gray-700 border-gray-500/20 dark:text-gray-400';
  const label = artifactTypeLabels[type] ?? (type === 'mixed' ? 'Mixed' : type);

  return (
    <Badge
      variant="outline"
      className={`inline-flex items-center gap-1.5 text-xs ${colorClass}`}
      aria-label={`Artifact type: ${label}`}
    >
      {Icon ? (
        <Icon className="h-3 w-3" aria-hidden="true" />
      ) : (
        <Layers className="h-3 w-3" aria-hidden="true" />
      )}
      {label}
    </Badge>
  );
}

// ============================================================================
// Score badge helper
// ============================================================================

interface ScoreBadgeProps {
  score: number;
}

function ScoreBadge({ score }: ScoreBadgeProps) {
  const { label, variant } = getScoreBand(score);
  return (
    <Badge
      variant={variant}
      aria-label={`Similarity score ${formatScore(score)}, band: ${label}`}
    >
      {formatScore(score)}
    </Badge>
  );
}

// ============================================================================
// Un-ignore button for a fully-ignored cluster row
// ============================================================================

interface UnignoreClusterButtonProps {
  cluster: ConsolidationCluster;
  minScore?: number;
}

function UnignoreClusterButton({ cluster, minScore }: UnignoreClusterButtonProps) {
  const { mutate: unignorePair, isPending } = useUnignorePair();

  // Collect all ignored pair IDs in this cluster
  const ignoredPairs = cluster.pairs.filter((p) => p.ignored);

  function handleUnignore(e: React.MouseEvent) {
    // Prevent row click (which would open the detail panel)
    e.stopPropagation();
    for (const pair of ignoredPairs) {
      unignorePair({ pairId: pair.pair_id, minScore });
    }
  }

  if (ignoredPairs.length === 0) return null;

  return (
    <Button
      variant="outline"
      size="sm"
      className="h-7 gap-1.5 px-2 text-xs"
      onClick={handleUnignore}
      disabled={isPending}
      aria-label={`Un-ignore ${ignoredPairs.length === 1 ? 'ignored pair' : `all ${ignoredPairs.length} ignored pairs`} in this cluster`}
    >
      <RotateCcw className="h-3 w-3" aria-hidden="true" />
      {isPending ? 'Restoring\u2026' : 'Un-ignore'}
    </Button>
  );
}

// ============================================================================
// Main component
// ============================================================================

interface ConsolidationClusterListProps {
  /** Minimum pairwise score threshold passed through to the hook */
  minScore?: number;
}

export function ConsolidationClusterList({ minScore }: ConsolidationClusterListProps = {}) {
  const [showIgnored, setShowIgnored] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState<ConsolidationCluster | null>(null);

  const {
    clusters,
    total,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    error,
  } = useConsolidationClusters({ minScore });

  // Clusters whose every pair is ignored (fully-ignored clusters hidden by default)
  const fullyIgnoredClusters = clusters.filter(isFullyIgnored);
  const ignoredCount = fullyIgnoredClusters.length;

  // Filter clusters: when showIgnored is false, hide fully-ignored clusters.
  const visibleClusters = showIgnored
    ? clusters
    : clusters.filter((cluster) => !isFullyIgnored(cluster));

  // ---- Error state ----
  if (error) {
    return (
      <div
        className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
        role="alert"
        aria-label="Error loading consolidation clusters"
      >
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>Failed to load consolidation clusters. Please try again.</span>
      </div>
    );
  }

  // ---- Loading skeleton ----
  if (isLoading) {
    return <ClusterListSkeleton />;
  }

  // ---- Empty state (no clusters at all) ----
  if (clusters.length === 0) {
    return <ClusterListEmpty />;
  }

  return (
    <div className="space-y-4">
      {/* Toolbar: counts + ignored-pairs toggle */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {total === 1
            ? '1 cluster found'
            : `${total} clusters found`}
          {!showIgnored && ignoredCount > 0 && (
            <span className="ml-1">
              ({ignoredCount} ignored {ignoredCount === 1 ? 'cluster' : 'clusters'} hidden)
            </span>
          )}
        </p>

        <div className="flex items-center gap-2">
          <Switch
            id="show-ignored-toggle"
            checked={showIgnored}
            onCheckedChange={setShowIgnored}
            aria-label={
              showIgnored
                ? 'Hide ignored pairs'
                : ignoredCount > 0
                  ? `Show ignored pairs (${ignoredCount} hidden)`
                  : 'Show ignored pairs'
            }
          />
          <Label
            htmlFor="show-ignored-toggle"
            className="cursor-pointer select-none text-sm text-muted-foreground"
          >
            Show ignored pairs
            {!showIgnored && ignoredCount > 0 && (
              <Badge
                variant="secondary"
                className="ml-1.5 px-1.5 py-0 text-xs tabular-nums"
                aria-label={`${ignoredCount} hidden`}
              >
                {ignoredCount}
              </Badge>
            )}
          </Label>
        </div>
      </div>

      {/* Cluster detail panel */}
      {selectedCluster && (
        <ConsolidationClusterDetail
          cluster={selectedCluster}
          onClose={() => setSelectedCluster(null)}
        />
      )}

      {/* Table */}
      {visibleClusters.length === 0 ? (
        <div
          className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground"
          role="status"
          aria-label="No visible clusters"
        >
          All clusters are ignored. Toggle &quot;Show ignored pairs&quot; to view them.
        </div>
      ) : (
        <div className="rounded-md border" data-testid="cluster-list">
          <Table
            role="table"
            aria-label="Consolidation clusters"
            aria-rowcount={visibleClusters.length}
          >
            <TableHeader>
              <TableRow>
                <TableHead
                  className="w-[80px]"
                  aria-label="Number of artifacts in cluster"
                >
                  Artifacts
                </TableHead>
                <TableHead aria-label="Primary artifact type">Type</TableHead>
                <TableHead
                  className="w-[100px]"
                  aria-label="Highest similarity score in cluster"
                >
                  Top Score
                </TableHead>
                <TableHead aria-label="Primary artifact name">Primary Artifact</TableHead>
                {showIgnored && (
                  <TableHead className="w-[120px]" aria-label="Ignored cluster actions">
                    Actions
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleClusters.map((cluster, rowIndex) => {
                const primaryType = getPrimaryType(cluster);
                const primaryName = getPrimaryArtifactName(cluster);
                const isSelected = selectedCluster?.cluster_id === cluster.cluster_id;
                const fullyIgnored = isFullyIgnored(cluster);
                const clusterHasIgnored = hasIgnoredPairs(cluster);

                return (
                  <TableRow
                    key={cluster.cluster_id}
                    className={[
                      'cursor-pointer transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset',
                      fullyIgnored
                        ? 'opacity-50 hover:opacity-70 hover:bg-muted/40'
                        : 'hover:bg-muted/60',
                      isSelected ? 'bg-accent' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    role="row"
                    aria-rowindex={rowIndex + 1}
                    aria-selected={isSelected}
                    aria-label={
                      fullyIgnored
                        ? `Ignored cluster with ${cluster.members.length} artifacts, primary artifact ${primaryName}`
                        : `Cluster with ${cluster.members.length} artifacts, top score ${formatScore(cluster.max_score)}, primary artifact ${primaryName}`
                    }
                    aria-disabled={fullyIgnored ? true : undefined}
                    tabIndex={0}
                    onClick={() =>
                      setSelectedCluster(isSelected ? null : cluster)
                    }
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setSelectedCluster(isSelected ? null : cluster);
                      }
                    }}
                    data-testid="cluster-row"
                    data-ignored={fullyIgnored ? 'true' : undefined}
                  >
                    {/* Artifact count */}
                    <TableCell>
                      <span
                        className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-semibold tabular-nums"
                        aria-label={`${cluster.members.length} artifacts`}
                      >
                        {cluster.members.length}
                      </span>
                    </TableCell>

                    {/* Type badge */}
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <TypeBadge type={primaryType} />
                        {fullyIgnored ? (
                          <span
                            className="inline-flex items-center gap-1 text-xs text-muted-foreground"
                            aria-label="All pairs ignored"
                            title="All pairs in this cluster are ignored"
                          >
                            <EyeOff className="h-3 w-3" aria-hidden="true" />
                            ignored
                          </span>
                        ) : clusterHasIgnored ? (
                          <span
                            className="text-xs text-muted-foreground"
                            aria-label="Has some ignored pairs"
                            title="This cluster contains some ignored pairs"
                          >
                            (some ignored)
                          </span>
                        ) : null}
                      </div>
                    </TableCell>

                    {/* Highest score */}
                    <TableCell>
                      <span className={fullyIgnored ? 'line-through decoration-muted-foreground/50' : undefined}>
                        <ScoreBadge score={cluster.max_score} />
                      </span>
                    </TableCell>

                    {/* Primary artifact name + member count hint */}
                    <TableCell>
                      <div className="space-y-0.5">
                        <div
                          className={[
                            'text-sm font-medium leading-tight',
                            fullyIgnored ? 'line-through text-muted-foreground' : '',
                          ]
                            .filter(Boolean)
                            .join(' ')}
                        >
                          {primaryName}
                        </div>
                        {cluster.members.length > 1 && (
                          <div className="text-xs text-muted-foreground">
                            +{cluster.members.length - 1} more
                          </div>
                        )}
                      </div>
                    </TableCell>

                    {/* Un-ignore action column (only rendered when showIgnored) */}
                    {showIgnored && (
                      <TableCell>
                        {fullyIgnored && (
                          <UnignoreClusterButton
                            cluster={cluster}
                            minScore={minScore}
                          />
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Load More */}
      {hasNextPage && (
        <div className="flex justify-center pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            aria-label={isFetchingNextPage ? 'Loading more clusters' : 'Load more clusters'}
          >
            {isFetchingNextPage ? 'Loading\u2026' : 'Load more'}
          </Button>
        </div>
      )}
    </div>
  );
}
