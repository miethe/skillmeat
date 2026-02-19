'use client';

/**
 * ArtifactPartOfSection
 *
 * Sidebar / detail section that lists parent composite (plugin) artifacts
 * that contain this artifact as a member.
 *
 * Visibility: rendered ONLY when parents.length > 0. Callers should gate
 * rendering on that condition (or pass the whole parents array and let this
 * component return null when empty).
 *
 * WCAG 2.1 AA: semantic list, descriptive link text, screen-reader labels,
 * keyboard-navigable links (Tab / Enter).
 */

import Link from 'next/link';
import { ChevronRight, Layers } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import type { AssociationItemDTO } from '@/types/associations';

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function PartOfSectionSkeleton() {
  return (
    <div role="status" aria-label="Loading parent plugins" className="space-y-2">
      {[1, 2].map((i) => (
        <Skeleton key={i} className="h-10 w-full rounded-lg" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single parent plugin row
// ---------------------------------------------------------------------------

function ParentPluginRow({ parent }: { parent: AssociationItemDTO }) {
  const href = `/artifacts/${encodeURIComponent(parent.artifact_id)}`;
  const typeLabel =
    parent.artifact_type.charAt(0).toUpperCase() + parent.artifact_type.slice(1);

  return (
    <li>
      <Link
        href={href}
        className="group flex items-center gap-2.5 rounded-lg border bg-card px-3 py-2.5 transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label={`Open ${parent.artifact_name} plugin detail page`}
      >
        {/* Plugin icon */}
        <Layers
          className="h-3.5 w-3.5 shrink-0 text-muted-foreground group-hover:text-foreground"
          aria-hidden="true"
        />

        {/* Name */}
        <span className="min-w-0 flex-1 truncate text-sm font-medium group-hover:text-foreground">
          {parent.artifact_name}
        </span>

        {/* Type label */}
        <span className="shrink-0 text-xs text-muted-foreground">{typeLabel}</span>

        {/* Navigate arrow */}
        <ChevronRight
          className="h-3.5 w-3.5 shrink-0 text-muted-foreground/40 transition-colors group-hover:text-muted-foreground"
          aria-hidden="true"
        />
      </Link>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

export interface ArtifactPartOfSectionProps {
  /** Parent associations returned by useArtifactAssociations */
  parents: AssociationItemDTO[];
  /** Whether association data is still loading */
  isLoading: boolean;
}

/**
 * Renders a "Part of" section listing parent plugins.
 *
 * Returns null when not loading AND there are no parents — callers can render
 * this unconditionally; the component self-hides when irrelevant.
 */
export function ArtifactPartOfSection({
  parents,
  isLoading,
}: ArtifactPartOfSectionProps) {
  // Show skeleton while loading (user may have parents we haven't fetched yet)
  if (isLoading) {
    return (
      <section aria-label="Part of plugins" className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Part of
        </h3>
        <PartOfSectionSkeleton />
      </section>
    );
  }

  // Hide entirely when there are no parents
  if (parents.length === 0) {
    return null;
  }

  return (
    <section aria-label="Parent plugins that contain this artifact" className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Part of
      </h3>
      <ul
        className="space-y-1.5"
        role="list"
        aria-label="Parent plugin list"
      >
        {parents.map((parent) => (
          <ParentPluginRow key={parent.artifact_id} parent={parent} />
        ))}
      </ul>
    </section>
  );
}
