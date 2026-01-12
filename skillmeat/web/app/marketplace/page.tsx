'use client';

import { useState, useEffect } from 'react';
import { Loader2, Search as SearchIcon, Github } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { MarketplaceListingCard } from '@/components/marketplace/MarketplaceListingCard';
import { MarketplaceFilters } from '@/components/marketplace/MarketplaceFilters';
import { MarketplaceStats } from '@/components/marketplace/MarketplaceStats';
import { MarketplaceInstallDialog } from '@/components/marketplace/MarketplaceInstallDialog';
import { Skeleton } from '@/components/ui/skeleton';
import { useListings, useBrokers, useInstallListing } from '@/hooks';
import { useRouter } from 'next/navigation';
import type { MarketplaceListing, MarketplaceFilters as Filters } from '@/types/marketplace';

export default function MarketplacePage() {
  const router = useRouter();
  const [filters, setFilters] = useState<Filters>({});
  const [selectedListing, setSelectedListing] = useState<MarketplaceListing | null>(null);
  const [isInstallDialogOpen, setIsInstallDialogOpen] = useState(false);

  // Fetch data
  const { data, isLoading, error, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useListings(filters);
  const { data: brokersData, isLoading: brokersLoading } = useBrokers();
  const installMutation = useInstallListing();

  // Flatten paginated results
  const allListings = data?.pages.flatMap((page) => page.items) || [];
  const brokers = brokersData || [];

  const handleListingClick = (listing: MarketplaceListing) => {
    router.push(`/marketplace/${listing.listing_id}`);
  };

  const handleInstallClick = (listing: MarketplaceListing) => {
    setSelectedListing(listing);
    setIsInstallDialogOpen(true);
  };

  const handleInstallConfirm = async (strategy: 'merge' | 'fork' | 'skip') => {
    if (!selectedListing) return;

    await installMutation.mutateAsync({
      listing_id: selectedListing.listing_id,
      strategy,
    });

    setIsInstallDialogOpen(false);
    setSelectedListing(null);
  };

  const handleLoadMore = () => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Marketplace</h1>
          <p className="text-muted-foreground">
            Browse and install bundles from marketplace brokers
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/marketplace/sources">
              <Github className="mr-2 h-4 w-4" />
              GitHub Sources
            </Link>
          </Button>
          <Button onClick={() => router.push('/marketplace/publish')}>Publish Bundle</Button>
        </div>
      </div>

      {/* Stats */}
      <MarketplaceStats listings={allListings} isLoading={isLoading} />

      {/* Filters */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Filters</h2>
        <MarketplaceFilters filters={filters} onFiltersChange={setFilters} brokers={brokers} />
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {isLoading ? (
            <Skeleton className="h-6 w-32" />
          ) : error ? (
            'Error loading listings'
          ) : (
            <>
              {allListings.length} {allListings.length === 1 ? 'Listing' : 'Listings'}
            </>
          )}
        </h2>
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">
            Failed to load marketplace listings. Please try again later.
          </p>
          <p className="mt-1 text-xs text-destructive/80">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="space-y-3 rounded-lg border p-4">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-16 w-full" />
              <div className="flex gap-2">
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-16" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && allListings.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <SearchIcon className="mb-4 h-12 w-12 text-muted-foreground" />
          <h3 className="mb-2 text-lg font-semibold">No listings found</h3>
          <p className="max-w-md text-sm text-muted-foreground">
            Try adjusting your filters or search terms to find what you're looking for.
          </p>
          {Object.keys(filters).length > 0 && (
            <Button variant="outline" className="mt-4" onClick={() => setFilters({})}>
              Clear Filters
            </Button>
          )}
        </div>
      )}

      {/* Listings Grid */}
      {!isLoading && !error && allListings.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {allListings.map((listing) => (
              <MarketplaceListingCard
                key={listing.listing_id}
                listing={listing}
                onClick={handleListingClick}
              />
            ))}
          </div>

          {/* Load More */}
          {hasNextPage && (
            <div className="flex justify-center pt-6">
              <Button variant="outline" onClick={handleLoadMore} disabled={isFetchingNextPage}>
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

      {/* Install Dialog */}
      <MarketplaceInstallDialog
        listing={selectedListing}
        isOpen={isInstallDialogOpen}
        onClose={() => {
          setIsInstallDialogOpen(false);
          setSelectedListing(null);
        }}
        onConfirm={handleInstallConfirm}
        isInstalling={installMutation.isPending}
      />
    </div>
  );
}
