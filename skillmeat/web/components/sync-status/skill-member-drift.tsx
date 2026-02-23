'use client';

/**
 * SkillMemberDrift
 *
 * Renders per-member drift rows as collapsible children under a parent skill
 * row in the sync status tab.  Only rendered for skill artifacts that have
 * composite members.
 *
 * Layout per expanded row:
 *   [indent] [type icon] [member name]  [source]→[collection]→[deployed] badges
 *
 * WCAG 2.1 AA:
 * - Toggle button uses aria-expanded / aria-controls
 * - Member list uses role="list" + role="listitem"
 * - Version badges include descriptive aria-labels
 * - Loading and error regions have role="status" / role="alert"
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, Minus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { useSkillSyncDiff } from '@/hooks';
import type { VersionComparisonRow } from '@/hooks';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SkillMemberDriftProps {
  /** Artifact ID in "type:name" format (e.g. "skill:my-skill") */
  artifactId: string;
  /** Collection name (uses active collection when omitted) */
  collection?: string;
  /** Project identifier for deployed_version lookup */
  projectId?: string;
  /** Comparison scope from parent sync tab — determines which version columns to highlight */
  comparisonScope?: 'source-vs-collection' | 'collection-vs-project' | 'source-vs-project';
}

// ---------------------------------------------------------------------------
// Version drift detection helpers
// ---------------------------------------------------------------------------

/**
 * Returns true when the two version strings differ and at least one is non-null.
 */
function hasDrift(a: string | null | undefined, b: string | null | undefined): boolean {
  if (a == null && b == null) return false;
  return a !== b;
}

/**
 * Derive an overall drift indicator for a member row based on the active scope.
 */
function getMemberDriftState(
  row: VersionComparisonRow,
  scope: SkillMemberDriftProps['comparisonScope']
): 'up-to-date' | 'drifted' | 'unknown' {
  switch (scope) {
    case 'source-vs-collection':
      if (row.source_version == null && row.collection_version == null) return 'unknown';
      return hasDrift(row.source_version, row.collection_version) ? 'drifted' : 'up-to-date';
    case 'collection-vs-project':
      if (row.collection_version == null && row.deployed_version == null) return 'unknown';
      return hasDrift(row.collection_version, row.deployed_version) ? 'drifted' : 'up-to-date';
    case 'source-vs-project':
      if (row.source_version == null && row.deployed_version == null) return 'unknown';
      return hasDrift(row.source_version, row.deployed_version) ? 'drifted' : 'up-to-date';
    default:
      // Default to collection-vs-project heuristic
      if (row.collection_version == null && row.deployed_version == null) return 'unknown';
      return hasDrift(row.collection_version, row.deployed_version) ? 'drifted' : 'up-to-date';
  }
}

// ---------------------------------------------------------------------------
// Version badge
// ---------------------------------------------------------------------------

function VersionBadge({
  label,
  version,
  highlight,
}: {
  label: string;
  version: string | null;
  highlight?: boolean;
}) {
  const display = version ?? '—';
  return (
    <span
      className="inline-flex flex-col items-start gap-0.5"
      aria-label={`${label}: ${version ?? 'not available'}`}
    >
      <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/70">
        {label}
      </span>
      <Badge
        variant={highlight ? 'destructive' : 'secondary'}
        className="h-5 rounded px-1.5 py-0 font-mono text-[11px]"
      >
        {display}
      </Badge>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Member row
// ---------------------------------------------------------------------------

function MemberRow({
  row,
  scope,
}: {
  row: VersionComparisonRow;
  scope: SkillMemberDriftProps['comparisonScope'];
}) {
  const driftState = getMemberDriftState(row, scope);

  const showSource =
    scope === 'source-vs-collection' || scope === 'source-vs-project' || scope == null;
  const showCollection = scope !== 'source-vs-project';
  const showDeployed =
    scope === 'collection-vs-project' || scope === 'source-vs-project' || scope == null;

  // Determine which versions are highlighted (mismatch)
  const sourceHighlight =
    (scope === 'source-vs-collection' &&
      hasDrift(row.source_version, row.collection_version)) ||
    (scope === 'source-vs-project' && hasDrift(row.source_version, row.deployed_version));
  const collectionHighlight =
    scope === 'source-vs-collection' &&
    hasDrift(row.source_version, row.collection_version);
  const deployedHighlight =
    (scope === 'collection-vs-project' &&
      hasDrift(row.collection_version, row.deployed_version)) ||
    (scope === 'source-vs-project' && hasDrift(row.source_version, row.deployed_version));

  return (
    <li
      role="listitem"
      data-testid="member-drift-row"
      className="flex items-center gap-3 rounded border-l-2 border-l-border/40 py-2 pl-4 pr-3 transition-colors hover:bg-accent/30"
    >
      {/* Drift status icon */}
      <span className="shrink-0" aria-hidden="true">
        {driftState === 'drifted' ? (
          <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
        ) : driftState === 'up-to-date' ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
        ) : (
          <Minus className="h-3.5 w-3.5 text-muted-foreground/50" />
        )}
      </span>

      {/* Member name + type */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium leading-snug">{row.artifact_name}</p>
        <p className="text-xs capitalize text-muted-foreground">{row.artifact_type}</p>
      </div>

      {/* Version columns */}
      <div className="flex shrink-0 items-start gap-3">
        {showSource && (
          <VersionBadge label="Source" version={row.source_version} highlight={sourceHighlight} />
        )}
        {showCollection && (
          <VersionBadge
            label="Collection"
            version={row.collection_version}
            highlight={collectionHighlight}
          />
        )}
        {showDeployed && (
          <VersionBadge
            label="Deployed"
            version={row.deployed_version}
            highlight={deployedHighlight}
          />
        )}
      </div>

      {/* Screen-reader drift summary */}
      <span className="sr-only">
        {driftState === 'drifted'
          ? 'Version mismatch detected'
          : driftState === 'up-to-date'
            ? 'Up to date'
            : 'Version data unavailable'}
      </span>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function MemberRowSkeleton() {
  return (
    <li role="listitem" className="flex items-center gap-3 border-l-2 border-l-border/40 py-2 pl-4 pr-3">
      <Skeleton className="h-3.5 w-3.5 shrink-0 rounded-full" />
      <div className="flex-1 space-y-1">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-3 w-16" />
      </div>
      <div className="flex shrink-0 gap-3">
        <Skeleton className="h-8 w-16" />
        <Skeleton className="h-8 w-16" />
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

/**
 * SkillMemberDrift — collapsible member drift rows for a skill artifact.
 *
 * Shows an expand/collapse toggle on the skill row.  When expanded, renders
 * one child row per composite member with three version comparison columns
 * (source, collection, deployed).  Members with no drift show a green check;
 * drifted members show an amber warning icon.
 *
 * The expand/collapse state is local (not persisted).
 *
 * @example
 * ```tsx
 * <SkillMemberDrift
 *   artifactId="skill:my-skill"
 *   collection="default"
 *   projectId="proj-abc"
 *   comparisonScope="collection-vs-project"
 * />
 * ```
 */
export function SkillMemberDrift({
  artifactId,
  collection,
  projectId,
  comparisonScope,
}: SkillMemberDriftProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const listId = `member-drift-list-${artifactId.replace(/[^a-zA-Z0-9]/g, '-')}`;

  const { data, isLoading, error } = useSkillSyncDiff({
    artifactId,
    collection,
    projectId,
    enabled: isExpanded,
  });

  // Member rows are everything after the first element (index 0 = parent skill row)
  const memberRows = data ? data.filter((r) => r.is_member) : [];

  // If there are no members after load, render nothing (non-composite skill)
  if (!isLoading && !error && isExpanded && data && memberRows.length === 0) {
    return null;
  }

  // Count how many members have drift to show in the toggle label
  const driftedCount = memberRows.filter(
    (r) => getMemberDriftState(r, comparisonScope) === 'drifted'
  ).length;

  return (
    <div className="mt-2" data-testid="skill-member-drift">
      {/* Expand/collapse toggle */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsExpanded((v) => !v)}
        aria-expanded={isExpanded}
        aria-controls={listId}
        className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
        data-testid="member-drift-toggle"
      >
        {isExpanded ? (
          <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        {isExpanded
          ? 'Hide member versions'
          : driftedCount > 0
            ? `Show member versions (${driftedCount} drifted)`
            : 'Show member versions'}
      </Button>

      {/* Member list — rendered (with visibility toggle) so aria-controls stays valid */}
      {isExpanded && (
        <div id={listId} role="region" aria-label="Member version comparison">
          {error && (
            <div
              role="alert"
              className="mt-2 rounded border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              Failed to load member versions: {error.message}
            </div>
          )}

          {isLoading && (
            <ul
              role="list"
              aria-label="Loading member versions"
              className="mt-2 space-y-1"
              aria-live="polite"
            >
              {Array.from({ length: 3 }).map((_, i) => (
                <MemberRowSkeleton key={i} />
              ))}
            </ul>
          )}

          {!isLoading && !error && memberRows.length > 0 && (
            <ul
              role="list"
              aria-label={`Member artifacts for ${artifactId}`}
              className="mt-2 space-y-1"
              data-testid="member-drift-list"
            >
              {memberRows.map((row) => (
                <MemberRow key={row.artifact_id} row={row} scope={comparisonScope} />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
