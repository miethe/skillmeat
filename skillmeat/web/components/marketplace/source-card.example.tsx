/**
 * SourceCard Component - Usage Examples
 *
 * This file demonstrates various usage patterns for the SourceCard component.
 * These examples can be used as reference when implementing marketplace pages.
 */

import { SourceCard, SourceCardSkeleton } from './source-card';
import type { GitHubSource } from '@/types/marketplace';

// ============================================================================
// Example Data
// ============================================================================

const exampleSource: GitHubSource = {
  id: 'src_anthropics_quickstarts',
  repo_url: 'https://github.com/anthropics/anthropic-quickstarts',
  owner: 'anthropics',
  repo_name: 'anthropic-quickstarts',
  ref: 'main',
  root_hint: 'skills',
  trust_level: 'verified',
  visibility: 'public',
  scan_status: 'success',
  artifact_count: 12,
  last_sync_at: '2025-12-06T10:30:00Z',
  created_at: '2025-12-05T09:00:00Z',
  updated_at: '2025-12-06T10:30:00Z',
};

const pendingSource: GitHubSource = {
  id: 'src_pending_repo',
  repo_url: 'https://github.com/example/new-repo',
  owner: 'example',
  repo_name: 'new-repo',
  ref: 'main',
  trust_level: 'basic',
  visibility: 'public',
  scan_status: 'pending',
  artifact_count: 0,
  created_at: '2025-12-06T12:00:00Z',
  updated_at: '2025-12-06T12:00:00Z',
};

const errorSource: GitHubSource = {
  id: 'src_error_repo',
  repo_url: 'https://github.com/example/broken-repo',
  owner: 'example',
  repo_name: 'broken-repo',
  ref: 'main',
  trust_level: 'untrusted',
  visibility: 'public',
  scan_status: 'error',
  artifact_count: 0,
  last_error: 'Failed to fetch repository: 404 Not Found',
  created_at: '2025-12-06T11:00:00Z',
  updated_at: '2025-12-06T11:30:00Z',
};

// ============================================================================
// Example 1: Basic Usage
// ============================================================================

export function BasicExample() {
  return (
    <div className="p-4">
      <h2 className="mb-4 text-2xl font-bold">Basic Source Card</h2>
      <SourceCard source={exampleSource} />
    </div>
  );
}

// ============================================================================
// Example 2: With Custom Click Handler
// ============================================================================

export function CustomClickExample() {
  const handleClick = () => {
    console.log('Source card clicked:', exampleSource.id);
    // Custom navigation or modal opening logic
  };

  return (
    <div className="p-4">
      <h2 className="mb-4 text-2xl font-bold">Custom Click Handler</h2>
      <SourceCard source={exampleSource} onClick={handleClick} />
    </div>
  );
}

// ============================================================================
// Example 3: With Rescan Action
// ============================================================================

export function RescanExample() {
  const handleRescan = async (sourceId: string) => {
    console.log('Rescanning source:', sourceId);
    // Trigger API call to rescan
    // await rescanSource(sourceId);
  };

  return (
    <div className="p-4">
      <h2 className="mb-4 text-2xl font-bold">With Rescan Action</h2>
      <SourceCard source={exampleSource} onRescan={handleRescan} />
    </div>
  );
}

// ============================================================================
// Example 4: Different States
// ============================================================================

export function StateVariantsExample() {
  return (
    <div className="space-y-4 p-4">
      <h2 className="mb-4 text-2xl font-bold">Different States</h2>

      <div>
        <h3 className="mb-2 text-lg font-semibold">Success State</h3>
        <SourceCard source={exampleSource} />
      </div>

      <div>
        <h3 className="mb-2 text-lg font-semibold">Pending State</h3>
        <SourceCard source={pendingSource} />
      </div>

      <div>
        <h3 className="mb-2 text-lg font-semibold">Error State</h3>
        <SourceCard source={errorSource} />
      </div>

      <div>
        <h3 className="mb-2 text-lg font-semibold">Scanning State</h3>
        <SourceCard source={{ ...exampleSource, scan_status: 'scanning' }} isRescanning />
      </div>
    </div>
  );
}

// ============================================================================
// Example 5: Loading Skeleton
// ============================================================================

export function LoadingExample() {
  return (
    <div className="p-4">
      <h2 className="mb-4 text-2xl font-bold">Loading State</h2>
      <div className="space-y-4">
        <SourceCardSkeleton />
        <SourceCardSkeleton />
        <SourceCardSkeleton />
      </div>
    </div>
  );
}

// ============================================================================
// Example 6: Grid Layout
// ============================================================================

export function GridLayoutExample() {
  const sources = [exampleSource, pendingSource, errorSource];

  return (
    <div className="p-4">
      <h2 className="mb-4 text-2xl font-bold">Grid Layout</h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {sources.map((source) => (
          <SourceCard key={source.id} source={source} />
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Example 7: Integration with TanStack Query
// ============================================================================

export function QueryIntegrationExample() {
  // Example hook (not implemented yet)
  /*
  const { data, isLoading, error } = useMarketplaceSources();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <SourceCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return <div>Error loading sources: {error.message}</div>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {data?.items.map((source) => (
        <SourceCard key={source.id} source={source} />
      ))}
    </div>
  );
  */

  return (
    <div className="p-4">
      <h2 className="mb-4 text-2xl font-bold">TanStack Query Integration</h2>
      <p className="text-muted-foreground">See commented code for integration pattern</p>
    </div>
  );
}
