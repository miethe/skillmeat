'use client';

/**
 * ArtifactContainsTab
 *
 * Renders the "Contains" tab content for composite (plugin) artifacts.
 * Shows child artifacts with name, type icon, description snippet, and
 * a clickable link to each child's detail page.
 *
 * Visibility: shown only when artifact_type === "composite" OR children.length > 0.
 *
 * WCAG 2.1 AA: semantic list markup, keyboard-navigable links (Tab/Enter),
 * descriptive link text, ARIA labels on loading/error regions.
 */

import Link from 'next/link';
import { AlertCircle, Box, ChevronRight, Layers, RefreshCcw, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import type { AssociationItemDTO } from '@/types/associations';

// ---------------------------------------------------------------------------
// Type icon mapping — maps artifact_type string to a Lucide icon component
// ---------------------------------------------------------------------------

function ArtifactTypeIcon({
  type,
  className,
}: {
  type: string;
  className?: string;
}): React.ReactElement {
  const cls = className ?? 'h-4 w-4 shrink-0';
  switch (type.toLowerCase()) {
    case 'composite':
      return <Layers className={cls} aria-hidden="true" />;
    case 'skill':
      return <Zap className={cls} aria-hidden="true" />;
    default:
      return <Box className={cls} aria-hidden="true" />;
  }
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function ContainsTabSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading child artifacts"
      className="space-y-3"
    >
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="flex items-start gap-3 rounded-lg border bg-card p-3"
        >
          <Skeleton className="mt-0.5 h-4 w-4 shrink-0 rounded" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-full max-w-xs" />
          </div>
          <Skeleton className="h-4 w-4 shrink-0" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function ContainsTabEmpty() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Layers
        className="mb-3 h-10 w-10 text-muted-foreground/40"
        aria-hidden="true"
      />
      <p className="text-sm font-medium text-muted-foreground">
        This plugin contains no artifacts
      </p>
      <p className="mt-1 text-xs text-muted-foreground/70">
        Add child artifacts to this composite plugin to see them listed here.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

function ContainsTabError({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 py-10 text-center"
    >
      <AlertCircle
        className="h-8 w-8 text-destructive/70"
        aria-hidden="true"
      />
      <div>
        <p className="text-sm font-medium text-destructive">
          Failed to load child artifacts
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          There was a problem fetching the association data.
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={onRetry}
        className="gap-1.5"
      >
        <RefreshCcw className="h-3.5 w-3.5" aria-hidden="true" />
        Try again
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single child artifact row
// ---------------------------------------------------------------------------

function ChildArtifactRow({ child }: { child: AssociationItemDTO }) {
  const href = `/artifacts/${encodeURIComponent(child.artifact_id)}`;

  // Capitalise the first letter of the type for display
  const typeLabel =
    child.artifact_type.charAt(0).toUpperCase() + child.artifact_type.slice(1);

  return (
    <li>
      <Link
        href={href}
        className="group flex items-start gap-3 rounded-lg border bg-card p-3 transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label={`View ${child.artifact_name} (${typeLabel})`}
      >
        {/* Type icon */}
        <span className="mt-0.5 text-muted-foreground group-hover:text-foreground">
          <ArtifactTypeIcon type={child.artifact_type} />
        </span>

        {/* Name + type badge */}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium leading-snug group-hover:text-foreground">
            {child.artifact_name}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">{typeLabel}</p>
        </div>

        {/* Navigate arrow */}
        <ChevronRight
          className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/40 transition-colors group-hover:text-muted-foreground"
          aria-hidden="true"
        />
      </Link>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

export interface ArtifactContainsTabProps {
  /** Child associations returned by useArtifactAssociations */
  children: AssociationItemDTO[];
  /** Whether association data is still loading */
  isLoading: boolean;
  /** Error object if association fetch failed */
  error: Error | null;
  /** Callback to trigger a refetch on error */
  onRetry: () => void;
}

export function ArtifactContainsTab({
  children,
  isLoading,
  error,
  onRetry,
}: ArtifactContainsTabProps) {
  if (isLoading) {
    return <ContainsTabSkeleton />;
  }

  if (error) {
    return <ContainsTabError onRetry={onRetry} />;
  }

  if (children.length === 0) {
    return <ContainsTabEmpty />;
  }

  return (
    <section aria-label="Child artifacts contained in this plugin" data-testid="contains-tab-content">
      <p className="mb-3 text-xs text-muted-foreground">
        {children.length} {children.length === 1 ? 'artifact' : 'artifacts'} in
        this plugin
      </p>
      <ul
        className="space-y-2"
        role="list"
        aria-label="Child artifact list"
      >
        {children.map((child) => (
          <ChildArtifactRow key={child.artifact_id} child={child} />
        ))}
      </ul>
    </section>
  );
}
