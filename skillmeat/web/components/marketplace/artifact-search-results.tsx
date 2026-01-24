/**
 * Artifact Search Results Component
 *
 * Displays search results grouped by source using an accordion.
 * Each source section contains clickable result cards with artifact details
 * and FTS5 snippet highlighting.
 */

'use client';

import * as React from 'react';
import Link from 'next/link';
import { GitBranch, FileCode, Search } from 'lucide-react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import type { ArtifactSearchResult } from '@/hooks';

// ============================================================================
// Types
// ============================================================================

export interface ArtifactSearchResultsProps {
  /** Search results to display */
  results: ArtifactSearchResult[];
  /** Additional CSS classes */
  className?: string;
}

interface GroupedResults {
  sourceId: string;
  sourceName: string;
  results: ArtifactSearchResult[];
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Group search results by source ID.
 */
function groupResultsBySource(results: ArtifactSearchResult[]): GroupedResults[] {
  const groups = new Map<string, GroupedResults>();

  for (const result of results) {
    const sourceId = result.source.id;
    const sourceName = `${result.source.owner}/${result.source.repo_name}`;

    if (!groups.has(sourceId)) {
      groups.set(sourceId, {
        sourceId,
        sourceName,
        results: [],
      });
    }

    groups.get(sourceId)!.results.push(result);
  }

  // Sort groups by number of results (descending)
  return Array.from(groups.values()).sort((a, b) => b.results.length - a.results.length);
}

/**
 * Format artifact type for display.
 */
function formatArtifactType(type: string): string {
  return type
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Get badge variant based on artifact type.
 */
function getTypeVariant(type: string): 'default' | 'secondary' | 'outline' {
  switch (type.toLowerCase()) {
    case 'skill':
      return 'default';
    case 'command':
      return 'secondary';
    default:
      return 'outline';
  }
}

/**
 * Format confidence score as percentage.
 */
function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}

// ============================================================================
// Sub-components
// ============================================================================

interface ResultCardProps {
  result: ArtifactSearchResult;
}

function ResultCard({ result }: ResultCardProps) {
  const href = `/marketplace/sources/${result.source.id}/catalog/${encodeURIComponent(result.artifact_path)}`;

  return (
    <Link
      href={href}
      className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      <Card
        className={cn(
          'p-4 transition-all duration-200',
          'hover:bg-muted/50 hover:shadow-sm',
          'border-l-2 border-l-transparent hover:border-l-primary'
        )}
      >
        {/* Header: Name + Type + Confidence */}
        <div className="mb-2 flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <FileCode className="h-4 w-4 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
              <h4 className="truncate font-medium">{result.name}</h4>
            </div>
            {result.title && result.title !== result.name && (
              <p className="mt-0.5 truncate text-sm text-muted-foreground">{result.title}</p>
            )}
          </div>
          <div className="flex flex-shrink-0 items-center gap-2">
            <Badge variant={getTypeVariant(result.artifact_type)} className="text-xs">
              {formatArtifactType(result.artifact_type)}
            </Badge>
            <Badge variant="outline" className="text-xs tabular-nums">
              {formatConfidence(result.confidence_score)}
            </Badge>
          </div>
        </div>

        {/* Description */}
        {result.description && (
          <p className="mb-2 line-clamp-2 text-sm text-muted-foreground">{result.description}</p>
        )}

        {/* Snippet with FTS5 highlights */}
        {result.snippet && (
          <div
            className={cn(
              'mt-2 rounded-md bg-muted/50 p-2 text-sm',
              '[&_mark]:rounded [&_mark]:bg-yellow-200 [&_mark]:px-0.5 [&_mark]:text-foreground',
              'dark:[&_mark]:bg-yellow-900/50 dark:[&_mark]:text-yellow-200'
            )}
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{ __html: result.snippet }}
            aria-label="Search result snippet with highlighted matches"
          />
        )}

        {/* Tags */}
        {result.search_tags && result.search_tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {result.search_tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {result.search_tags.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{result.search_tags.length - 3}
              </Badge>
            )}
          </div>
        )}
      </Card>
    </Link>
  );
}

interface SourceGroupProps {
  group: GroupedResults;
  value: string;
}

function SourceGroup({ group, value }: SourceGroupProps) {
  return (
    <AccordionItem value={value} className="border-b last:border-b-0">
      <AccordionTrigger
        className={cn(
          'px-4 py-3 hover:no-underline',
          'hover:bg-muted/50 [&[data-state=open]]:bg-muted/30'
        )}
      >
        <div className="flex items-center gap-3">
          <GitBranch className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <span className="font-medium">{group.sourceName}</span>
          <Badge variant="secondary" className="ml-1 tabular-nums">
            {group.results.length}
          </Badge>
        </div>
      </AccordionTrigger>
      <AccordionContent className="px-4 pb-4">
        <div className="space-y-3">
          {group.results.map((result) => (
            <ResultCard key={result.id} result={result} />
          ))}
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ArtifactSearchResults({ results, className }: ArtifactSearchResultsProps) {
  // Handle empty state
  if (results.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center py-12 text-center',
          className
        )}
        role="status"
        aria-live="polite"
      >
        <Search className="mb-4 h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
        <h3 className="mb-2 text-lg font-medium text-muted-foreground">No results found</h3>
        <p className="text-sm text-muted-foreground/80">
          Try adjusting your search terms or filters
        </p>
      </div>
    );
  }

  const groupedResults = groupResultsBySource(results);

  // Default to first source expanded
  const firstGroup = groupedResults[0];
  const defaultValue = firstGroup ? [firstGroup.sourceId] : [];

  return (
    <Accordion
      type="multiple"
      defaultValue={defaultValue}
      className={cn('rounded-lg border', className)}
    >
      {groupedResults.map((group) => (
        <SourceGroup key={group.sourceId} group={group} value={group.sourceId} />
      ))}
    </Accordion>
  );
}

// ============================================================================
// Skeleton
// ============================================================================

/**
 * Skeleton result card for loading states.
 */
function SkeletonResultCard() {
  return (
    <Card className="p-4">
      {/* Header: Icon + Name + Type + Confidence */}
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 flex-shrink-0" />
            <Skeleton className="h-5 w-48" />
          </div>
          <Skeleton className="mt-1 h-4 w-32" />
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-12" />
        </div>
      </div>

      {/* Description */}
      <Skeleton className="mb-2 h-4 w-full" />
      <Skeleton className="mb-2 h-4 w-3/4" />

      {/* Snippet */}
      <div className="mt-2 rounded-md bg-muted/50 p-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="mt-1 h-3 w-5/6" />
      </div>

      {/* Tags */}
      <div className="mt-2 flex flex-wrap gap-1">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-14" />
      </div>
    </Card>
  );
}

/**
 * Skeleton accordion item for loading states.
 */
function SkeletonSourceGroup() {
  return (
    <div className="border-b last:border-b-0">
      {/* Accordion trigger skeleton */}
      <div className="flex items-center gap-3 px-4 py-3">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-5 w-8 rounded-full" />
      </div>
      {/* Accordion content skeleton - 3 result cards */}
      <div className="space-y-3 px-4 pb-4">
        <SkeletonResultCard />
        <SkeletonResultCard />
        <SkeletonResultCard />
      </div>
    </div>
  );
}

/**
 * Loading skeleton for artifact search results.
 * Shows 3 skeleton accordion items, each with skeleton source name/count and 3 skeleton result cards.
 */
export function ArtifactSearchResultsSkeleton() {
  return (
    <div className="rounded-lg border" role="status" aria-label="Loading search results">
      <SkeletonSourceGroup />
      <SkeletonSourceGroup />
      <SkeletonSourceGroup />
    </div>
  );
}
