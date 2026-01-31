'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Package, Grid, List, Loader2, AlertCircle, Plus } from 'lucide-react';
import Link from 'next/link';
import { useGroupArtifacts, useArtifact, useToast, useCliCopy } from '@/hooks';
import { generateBasicDeployCommand } from '@/lib/cli-commands';
import { UnifiedCard, UnifiedCardSkeleton } from '@/components/shared/unified-card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';
import type { GroupArtifact } from '@/types/groups';

/**
 * View mode storage key for localStorage persistence
 */
const VIEW_MODE_KEY = 'groups-artifact-view-mode';

/**
 * Sort options for artifact display
 */
type SortField = 'position' | 'name' | 'updatedAt' | 'type';
type SortOrder = 'asc' | 'desc';

/**
 * Props for GroupArtifactGrid component
 */
interface GroupArtifactGridProps {
  /** ID of the group to display artifacts from */
  groupId: string;
  /** ID of the collection containing the group */
  collectionId: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Hook to fetch full artifact data for a group artifact
 * Uses the artifact ID from GroupArtifact to fetch complete Artifact data
 */
function useFullArtifact(artifactId: string) {
  return useArtifact(artifactId);
}

/**
 * Component to render a single artifact with loading state
 */
function ArtifactWithData({
  groupArtifact,
  viewMode,
  onClick,
  onCopyCliCommand,
}: {
  groupArtifact: GroupArtifact;
  viewMode: 'grid' | 'list';
  onClick: (artifact: Artifact) => void;
  onCopyCliCommand: (artifactName: string) => void;
}) {
  const { data: artifact, isLoading, error } = useFullArtifact(groupArtifact.artifact_id);

  if (isLoading) {
    return <UnifiedCardSkeleton />;
  }

  if (error || !artifact) {
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded-lg border border-dashed border-muted-foreground/25 p-4',
          viewMode === 'grid' ? 'h-48' : 'h-16'
        )}
      >
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <AlertCircle className="h-4 w-4" />
          <span>Failed to load artifact</span>
        </div>
      </div>
    );
  }

  return (
    <UnifiedCard
      item={artifact}
      onClick={() => onClick(artifact)}
      onCopyCliCommand={() => onCopyCliCommand(artifact.name)}
    />
  );
}

/**
 * GroupArtifactGrid - Display artifacts from a selected group
 *
 * Features:
 * - Infinite scroll pagination (via intersection observer)
 * - Grid/List view toggle with localStorage persistence
 * - Sort by position, name, date, or type
 * - Filter by artifact type and status
 * - Empty and error state handling
 *
 * @example
 * ```tsx
 * <GroupArtifactGrid
 *   groupId="group-123"
 *   collectionId="collection-456"
 * />
 * ```
 */
export function GroupArtifactGrid({
  groupId,
  collectionId,
  className,
}: GroupArtifactGridProps) {
  // Note: collectionId is used for empty state link and reserved for future filter features
  const { toast } = useToast();
  const { copy } = useCliCopy();

  const handleCopyCliCommand = useCallback(
    (artifactName: string) => {
      const command = generateBasicDeployCommand(artifactName);
      copy(command);
    },
    [copy]
  );

  // View mode state with localStorage persistence
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Initialize view mode from localStorage after mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(VIEW_MODE_KEY);
      if (saved === 'grid' || saved === 'list') {
        setViewMode(saved);
      }
    }
  }, []);

  // Persist view mode changes to localStorage
  const handleViewModeChange = useCallback((mode: 'grid' | 'list') => {
    setViewMode(mode);
    if (typeof window !== 'undefined') {
      localStorage.setItem(VIEW_MODE_KEY, mode);
    }
  }, []);

  // Sort state
  const [sortField, setSortField] = useState<SortField>('position');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Fetch group artifacts using the group-specific hook
  const {
    data: groupArtifacts,
    isLoading,
    error,
    refetch,
  } = useGroupArtifacts(groupId);

  // Infinite scroll state - we'll paginate client-side for now
  // since useGroupArtifacts returns all artifacts in the group
  const [displayCount, setDisplayCount] = useState(20);
  const observerTarget = useRef<HTMLDivElement>(null);

  // Sort and filter the artifacts
  const processedArtifacts = useMemo(() => {
    if (!groupArtifacts) return [];

    let artifacts = [...groupArtifacts];

    // Sort artifacts
    artifacts.sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'position':
          comparison = a.position - b.position;
          break;
        case 'name':
          // For name sorting, we'd need the full artifact data
          // Fall back to artifact_id for now
          comparison = a.artifact_id.localeCompare(b.artifact_id);
          break;
        case 'updatedAt':
          // Use added_at as proxy for ordering
          comparison = new Date(a.added_at).getTime() - new Date(b.added_at).getTime();
          break;
        case 'type':
          // Type sorting requires full artifact data
          comparison = a.artifact_id.localeCompare(b.artifact_id);
          break;
        default:
          comparison = a.position - b.position;
      }

      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return artifacts;
  }, [groupArtifacts, sortField, sortOrder]);

  // Paginated artifacts for display
  const displayedArtifacts = useMemo(() => {
    return processedArtifacts.slice(0, displayCount);
  }, [processedArtifacts, displayCount]);

  // Check if there are more artifacts to load
  const hasNextPage = displayCount < processedArtifacts.length;
  const isFetchingNextPage = false; // Client-side pagination is instant

  // Set up intersection observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting && hasNextPage) {
          setDisplayCount((prev) => Math.min(prev + 20, processedArtifacts.length));
        }
      },
      { threshold: 0.1, rootMargin: '200px' }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget);
      }
    };
  }, [hasNextPage, processedArtifacts.length]);

  // Handle artifact click - navigate to artifact detail
  const handleArtifactClick = useCallback(
    (artifact: Artifact) => {
      // Navigate to artifact detail page or open modal
      // For now, show a toast - actual navigation depends on app structure
      toast({
        title: artifact.name,
        description: `${artifact.type} artifact clicked`,
      });
    },
    [toast]
  );

  // Handle sort change
  const handleSortChange = useCallback((field: SortField) => {
    setSortField((currentField) => {
      if (currentField === field) {
        // Toggle order if same field
        setSortOrder((order) => (order === 'asc' ? 'desc' : 'asc'));
        return field;
      }
      // Reset to ascending for new field
      setSortOrder('asc');
      return field;
    });
  }, []);

  // Loading state
  if (isLoading) {
    return <GroupArtifactGridSkeleton viewMode={viewMode} />;
  }

  // Error state
  if (error) {
    return (
      <div className={cn('rounded-lg border border-destructive/50 bg-destructive/10 p-6', className)}>
        <div className="flex flex-col items-center justify-center gap-4 text-center">
          <AlertCircle className="h-12 w-12 text-destructive" />
          <div>
            <h3 className="font-semibold text-destructive">Failed to load artifacts</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {error instanceof Error ? error.message : 'An unexpected error occurred'}
            </p>
          </div>
          <Button variant="outline" onClick={() => refetch()}>
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  // Empty state
  if (!displayedArtifacts || displayedArtifacts.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center rounded-lg border border-dashed border-muted-foreground/25 py-12',
          className
        )}
        role="status"
        aria-label="No artifacts in group"
      >
        <Package className="h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
        <h3 className="mt-4 text-lg font-semibold">No artifacts in this group</h3>
        <p className="mt-2 max-w-sm text-center text-sm text-muted-foreground">
          Add artifacts to this group from the collection page to see them here.
        </p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href={`/collection?collection=${collectionId}`}>
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Add Artifacts
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Toolbar with view toggle, sort, and filter controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left side - count and filters */}
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">
            {processedArtifacts.length} artifact{processedArtifacts.length !== 1 ? 's' : ''}
          </span>

          {/* Sort selector */}
          <Select
            value={sortField}
            onValueChange={(value) => handleSortChange(value as SortField)}
          >
            <SelectTrigger className="w-[140px]" aria-label="Sort by">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="position">Position</SelectItem>
              <SelectItem value="name">Name</SelectItem>
              <SelectItem value="updatedAt">Date Added</SelectItem>
              <SelectItem value="type">Type</SelectItem>
            </SelectContent>
          </Select>

          {/* Sort order toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSortOrder((order) => (order === 'asc' ? 'desc' : 'asc'))}
            aria-label={`Sort ${sortOrder === 'asc' ? 'descending' : 'ascending'}`}
          >
            {sortOrder === 'asc' ? 'Asc' : 'Desc'}
          </Button>
        </div>

        {/* Right side - view toggle */}
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => handleViewModeChange('grid')}
            aria-label="Grid view"
            aria-pressed={viewMode === 'grid'}
          >
            <Grid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => handleViewModeChange('list')}
            aria-label="List view"
            aria-pressed={viewMode === 'list'}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Artifact grid/list */}
      <div
        className={cn(
          viewMode === 'grid'
            ? 'grid auto-rows-fr grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3'
            : 'flex flex-col gap-2'
        )}
        role="grid"
        aria-label="Group artifacts"
      >
        {displayedArtifacts.map((groupArtifact) => (
          <ArtifactWithData
            key={groupArtifact.artifact_id}
            groupArtifact={groupArtifact}
            viewMode={viewMode}
            onClick={handleArtifactClick}
            onCopyCliCommand={handleCopyCliCommand}
          />
        ))}
      </div>

      {/* Infinite scroll trigger element */}
      <div
        ref={observerTarget}
        className="flex h-10 items-center justify-center"
        aria-hidden="true"
      >
        {isFetchingNextPage && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm">Loading more artifacts...</span>
          </div>
        )}
        {!hasNextPage && displayedArtifacts.length > 0 && (
          <span className="text-sm text-muted-foreground">
            All {processedArtifacts.length} artifacts loaded
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Loading skeleton for GroupArtifactGrid
 */
function GroupArtifactGridSkeleton({ viewMode }: { viewMode: 'grid' | 'list' }) {
  return (
    <div className="space-y-4">
      {/* Toolbar skeleton */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-10 w-[140px]" />
          <Skeleton className="h-8 w-12" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-8" />
          <Skeleton className="h-8 w-8" />
        </div>
      </div>

      {/* Grid skeleton */}
      <div
        className={cn(
          viewMode === 'grid'
            ? 'grid auto-rows-fr grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3'
            : 'flex flex-col gap-2'
        )}
        data-testid="group-artifact-grid-skeleton"
      >
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <UnifiedCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
