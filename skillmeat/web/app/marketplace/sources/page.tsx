/**
 * Marketplace Sources Page
 *
 * Displays all GitHub repository sources that can be scanned for artifacts.
 * Provides add, rescan, and manage functionality.
 */

'use client';

import { useState, useMemo } from 'react';
import { Plus, RefreshCw, Search as SearchIcon, Loader2, Github } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { SourceCard, SourceCardSkeleton } from '@/components/marketplace/source-card';
import { AddSourceModal } from '@/components/marketplace/add-source-modal';
import { useSources, useRescanSource } from '@/hooks/useMarketplaceSources';

export default function MarketplaceSourcesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [addModalOpen, setAddModalOpen] = useState(false);

  // Fetch sources
  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
  } = useSources();

  // Flatten pages
  const allSources = useMemo(() => {
    return data?.pages.flatMap((page) => page.items) || [];
  }, [data]);

  // Filter by search
  const filteredSources = useMemo(() => {
    if (!searchQuery.trim()) return allSources;
    const query = searchQuery.toLowerCase();
    return allSources.filter(
      (source) =>
        source.owner.toLowerCase().includes(query) ||
        source.repo_name.toLowerCase().includes(query)
    );
  }, [allSources, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">GitHub Sources</h1>
          <p className="text-muted-foreground">
            Add and manage GitHub repositories to discover Claude Code artifacts
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={() => setAddModalOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Source
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search repositories..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Stats Summary */}
      {!isLoading && !error && allSources.length > 0 && (
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>{filteredSources.length} sources</span>
          <span>•</span>
          <span>
            {filteredSources.reduce((sum, s) => sum + s.artifact_count, 0)} total artifacts
          </span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">
            Failed to load sources. Please try again later.
          </p>
          <p className="mt-1 text-xs text-destructive/80">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => refetch()}
          >
            Retry
          </Button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <SourceCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredSources.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Github className="mb-4 h-12 w-12 text-muted-foreground" />
          {allSources.length === 0 ? (
            <>
              <h3 className="mb-2 text-lg font-semibold">No sources added yet</h3>
              <p className="max-w-md text-sm text-muted-foreground">
                Add a GitHub repository to start discovering Claude Code artifacts like
                skills, commands, agents, and more.
              </p>
              <Button className="mt-4" onClick={() => setAddModalOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Your First Source
              </Button>
            </>
          ) : (
            <>
              <h3 className="mb-2 text-lg font-semibold">No matching sources</h3>
              <p className="max-w-md text-sm text-muted-foreground">
                Try adjusting your search term.
              </p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setSearchQuery('')}
              >
                Clear Search
              </Button>
            </>
          )}
        </div>
      )}

      {/* Sources Grid */}
      {!isLoading && !error && filteredSources.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredSources.map((source) => (
              <SourceCard
                key={source.id}
                source={source}
              />
            ))}
          </div>

          {/* Load More */}
          {hasNextPage && (
            <div className="flex justify-center pt-6">
              <Button
                variant="outline"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  'Load More'
                )}
              </Button>
            </div>
          )}
        </>
      )}

      {/* Add Source Modal */}
      <AddSourceModal
        open={addModalOpen}
        onOpenChange={setAddModalOpen}
        onSuccess={() => {
          setAddModalOpen(false);
          refetch();
        }}
      />
    </div>
  );
}
