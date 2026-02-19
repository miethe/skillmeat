'use client';

/**
 * Artifact Detail Page
 *
 * Displays detailed information about a single artifact, including:
 *   - Overview tab (metadata, source, tags, timestamps)
 *   - Contains tab (composite/plugin child artifacts) — shown when applicable
 *   - "Part of" sidebar section (parent plugins) — shown when parents exist
 *
 * Uses the useArtifactAssociations hook to fetch parent/child relationship data.
 *
 * Next.js 15: params must be awaited in async server components.
 * This is a client component because it uses interactive tabs and React Query.
 */

import { use } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Calendar,
  GitBranch,
  Layers,
  Tag,
} from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { useArtifact, useArtifactAssociations } from '@/hooks';
import type { Artifact } from '@/types/artifact';
import { ARTIFACT_TYPES } from '@/types/artifact';
import { ArtifactContainsTab } from '@/components/artifact/artifact-contains-tab';
import { ArtifactPartOfSection } from '@/components/artifact/artifact-part-of-section';

// ---------------------------------------------------------------------------
// Loading skeleton for the full page
// ---------------------------------------------------------------------------

function ArtifactDetailSkeleton() {
  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6" aria-busy="true" aria-label="Loading artifact detail">
      <Skeleton className="h-5 w-24" />
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Skeleton className="h-10 w-full" />
      <div className="space-y-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

function ArtifactDetailError({ id }: { id: string }) {
  return (
    <div className="mx-auto max-w-4xl p-6">
      <Link href="/manage">
        <Button variant="ghost" size="sm" className="mb-6 gap-1.5">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back
        </Button>
      </Link>
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-8 text-center">
        <p className="text-sm font-medium text-destructive">
          Failed to load artifact
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Could not find artifact with ID: <code className="font-mono">{id}</code>
        </p>
        <Link href="/manage">
          <Button variant="outline" size="sm" className="mt-4">
            Go to collection
          </Button>
        </Link>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overview tab content
// ---------------------------------------------------------------------------

function OverviewTab({ artifact }: { artifact: Artifact }) {
  return (
    <div className="space-y-6 py-4">
      {/* Description */}
      {artifact.description && (
        <section>
          <h3 className="mb-1.5 text-sm font-medium">Description</h3>
          <p className="text-sm text-muted-foreground">{artifact.description}</p>
        </section>
      )}

      {/* Source */}
      <section>
        <h3 className="mb-1.5 flex items-center gap-2 text-sm font-medium">
          <GitBranch className="h-4 w-4" aria-hidden="true" />
          Source
        </h3>
        <p className="rounded-md bg-muted px-3 py-2 font-mono text-sm">
          {artifact.source ?? 'Unknown'}
        </p>
      </section>

      {/* Version */}
      {artifact.version && (
        <section>
          <h3 className="mb-1.5 text-sm font-medium">Version</h3>
          <p className="text-sm text-muted-foreground">{artifact.version}</p>
        </section>
      )}

      {/* Tags */}
      {artifact.tags && artifact.tags.length > 0 && (
        <section>
          <h3 className="mb-1.5 flex items-center gap-2 text-sm font-medium">
            <Tag className="h-4 w-4" aria-hidden="true" />
            Tags
          </h3>
          <div className="flex flex-wrap gap-2" role="list" aria-label="Artifact tags">
            {artifact.tags.map((tag) => (
              <Badge key={tag} variant="outline" role="listitem">
                {tag}
              </Badge>
            ))}
          </div>
        </section>
      )}

      {/* Timestamps */}
      <section>
        <h3 className="mb-1.5 flex items-center gap-2 text-sm font-medium">
          <Calendar className="h-4 w-4" aria-hidden="true" />
          Timestamps
        </h3>
        <dl className="space-y-1 text-sm text-muted-foreground">
          {artifact.createdAt && (
            <div className="flex justify-between">
              <dt>Created</dt>
              <dd>
                <time dateTime={artifact.createdAt}>
                  {new Date(artifact.createdAt).toLocaleDateString()}
                </time>
              </dd>
            </div>
          )}
          {artifact.updatedAt && (
            <div className="flex justify-between">
              <dt>Updated</dt>
              <dd>
                <time dateTime={artifact.updatedAt}>
                  {new Date(artifact.updatedAt).toLocaleDateString()}
                </time>
              </dd>
            </div>
          )}
        </dl>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

interface ArtifactDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function ArtifactDetailPage({ params }: ArtifactDetailPageProps) {
  // Next.js 15: unwrap the async params with `use()`
  const { id } = use(params);

  // Decode in case the ID was URL-encoded (e.g., "composite%3Amy-plugin")
  const artifactId = decodeURIComponent(id);

  const {
    data: artifact,
    isLoading: isArtifactLoading,
    error: artifactError,
  } = useArtifact(artifactId);

  const {
    data: associations,
    isLoading: isAssocLoading,
    error: assocError,
    refetch: refetchAssociations,
  } = useArtifactAssociations(artifactId);

  // Show full-page skeleton while loading
  if (isArtifactLoading) {
    return <ArtifactDetailSkeleton />;
  }

  // Show error state if artifact couldn't be loaded
  if (artifactError || !artifact) {
    return <ArtifactDetailError id={artifactId} />;
  }

  // Resolve type icon from ARTIFACT_TYPES config
  const typeConfig = ARTIFACT_TYPES[artifact.type];
  const IconComponent = typeConfig
    ? ((LucideIcons as Record<string, unknown>)[typeConfig.icon] as LucideIcon)
    : null;

  // Determine whether to show the "Contains" tab:
  // Show when artifact is composite OR when children were fetched and non-empty
  const isComposite = artifact.type === ('composite' as string);
  const hasChildren = (associations?.children?.length ?? 0) > 0;
  const showContainsTab = isComposite || hasChildren;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      {/* Back navigation */}
      <nav aria-label="Breadcrumb" className="mb-6">
        <Link href="/manage">
          <Button variant="ghost" size="sm" className="gap-1.5 pl-0">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to collection
          </Button>
        </Link>
      </nav>

      <div className="flex flex-col gap-6 lg:flex-row lg:gap-8">
        {/* Main content */}
        <main className="flex-1 min-w-0" aria-label="Artifact detail">
          {/* Artifact header */}
          <header className="mb-6 flex items-start gap-3">
            {IconComponent && (
              <span
                className={`mt-1 ${typeConfig.color}`}
                aria-hidden="true"
              >
                <IconComponent className="h-6 w-6" />
              </span>
            )}
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-2xl font-bold tracking-tight">
                  {artifact.name}
                </h1>
                {typeConfig && (
                  <Badge variant="outline" className="shrink-0">
                    {typeConfig.label}
                  </Badge>
                )}
                {isComposite && (
                  <Badge
                    variant="secondary"
                    className="shrink-0 gap-1"
                    aria-label="Composite plugin"
                  >
                    <Layers className="h-3 w-3" aria-hidden="true" />
                    Plugin
                  </Badge>
                )}
              </div>
              {artifact.description && (
                <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                  {artifact.description}
                </p>
              )}
            </div>
          </header>

          {/* Tab navigation */}
          <Tabs defaultValue="overview">
            <TabsList
              className={showContainsTab ? 'grid w-full grid-cols-2' : 'grid w-full grid-cols-1'}
              aria-label="Artifact sections"
            >
              <TabsTrigger value="overview">Overview</TabsTrigger>
              {showContainsTab && (
                <TabsTrigger value="contains">
                  Contains
                  {hasChildren && (
                    <span
                      className="ml-1.5 rounded-full bg-primary/10 px-1.5 py-0.5 text-xs font-semibold tabular-nums text-primary"
                      aria-label={`${associations!.children.length} children`}
                    >
                      {associations!.children.length}
                    </span>
                  )}
                </TabsTrigger>
              )}
            </TabsList>

            {/* Overview tab content */}
            <TabsContent value="overview">
              <ScrollArea className="max-h-[60vh]">
                <OverviewTab artifact={artifact} />
              </ScrollArea>
            </TabsContent>

            {/* Contains tab content — only mounted when showContainsTab */}
            {showContainsTab && (
              <TabsContent value="contains">
                <ScrollArea className="max-h-[60vh]">
                  <div className="py-4">
                    <ArtifactContainsTab
                      children={associations?.children ?? []}
                      isLoading={isAssocLoading}
                      error={assocError}
                      onRetry={refetchAssociations}
                    />
                  </div>
                </ScrollArea>
              </TabsContent>
            )}
          </Tabs>
        </main>

        {/* Sidebar */}
        <aside
          className="w-full shrink-0 space-y-6 lg:w-64"
          aria-label="Artifact metadata sidebar"
        >
          {/* "Part of" section — self-hides when no parents */}
          <ArtifactPartOfSection
            parents={associations?.parents ?? []}
            isLoading={isAssocLoading}
          />

          {/* Author / License metadata */}
          {(artifact.author || artifact.license) && (
            <section className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Info
              </h3>
              {artifact.author && (
                <div className="text-sm">
                  <span className="text-muted-foreground">Author: </span>
                  <span className="font-medium">{artifact.author}</span>
                </div>
              )}
              {artifact.license && (
                <div className="text-sm">
                  <span className="text-muted-foreground">License: </span>
                  <span className="font-medium">{artifact.license}</span>
                </div>
              )}
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
