"use client";

import { useState } from "react";
import { MarketplaceSearch } from "./MarketplaceSearch";
import { MarketplaceFilters } from "./MarketplaceFilters";
import { MarketplaceListingCard } from "./MarketplaceListingCard";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Select } from "@/components/ui/select";
import { useMarketplaceListings } from "@/hooks/useMarketplace";
import { useMarketplaceFilters } from "@/hooks/useMarketplaceFilters";
import type { ListingSortOrder } from "@/types/marketplace";
import { ChevronLeft, ChevronRight, Filter } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

const SORT_OPTIONS: { value: ListingSortOrder; label: string }[] = [
  { value: "newest", label: "Newest" },
  { value: "popular", label: "Most Popular" },
  { value: "updated", label: "Recently Updated" },
  { value: "downloads", label: "Most Downloads" },
  { value: "name", label: "Name (A-Z)" },
];

const PER_PAGE = 20;

export function MarketplaceListingCatalog() {
  const { filters, sort, page, setFilters, setSort, setPage, resetFilters, clearSearch } =
    useMarketplaceFilters();

  const { data, isLoading, error } = useMarketplaceListings(filters, sort, page, PER_PAGE);

  const handleSearchChange = (value: string) => {
    setFilters({ search: value });
  };

  const handleSortChange = (value: string) => {
    setSort(value as ListingSortOrder);
  };

  const totalPages = data ? Math.ceil(data.page_info.total_count / PER_PAGE) : 0;

  return (
    <div className="space-y-6">
      {/* Header & Search */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex-1">
          <MarketplaceSearch
            value={filters.search || ""}
            onChange={handleSearchChange}
            onClear={clearSearch}
          />
        </div>
        <div className="flex items-center gap-2">
          {/* Mobile Filter Button */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" className="sm:hidden">
                <Filter className="mr-2 h-4 w-4" />
                Filters
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80">
              <SheetHeader>
                <SheetTitle>Filters</SheetTitle>
              </SheetHeader>
              <div className="mt-4">
                <MarketplaceFilters
                  filters={filters}
                  onChange={setFilters}
                  onReset={resetFilters}
                />
              </div>
            </SheetContent>
          </Sheet>

          {/* Sort Dropdown */}
          <select
            value={sort}
            onChange={(e) => handleSortChange(e.target.value)}
            className="flex h-10 items-center rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Sort listings"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex gap-6">
        {/* Desktop Filters Sidebar */}
        <aside className="hidden w-64 shrink-0 sm:block">
          <MarketplaceFilters filters={filters} onChange={setFilters} onReset={resetFilters} />
        </aside>

        {/* Listings Grid */}
        <div className="flex-1">
          {/* Results Count */}
          {data && (
            <div className="mb-4 text-sm text-muted-foreground">
              {data.page_info.total_count} {data.page_info.total_count === 1 ? "result" : "results"}
              {filters.search && (
                <span>
                  {" "}
                  for &quot;<strong>{filters.search}</strong>&quot;
                </span>
              )}
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="space-y-3">
                  <Skeleton className="h-48 w-full" />
                </div>
              ))}
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="flex flex-col items-center justify-center rounded-lg border border-destructive/50 bg-destructive/10 p-8 text-center">
              <p className="text-lg font-semibold text-destructive">Failed to load listings</p>
              <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
              <Button onClick={() => window.location.reload()} className="mt-4">
                Retry
              </Button>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && data && data.items.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center">
              <p className="text-lg font-semibold">No listings found</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Try adjusting your filters or search query
              </p>
              <Button onClick={resetFilters} variant="outline" className="mt-4">
                Clear Filters
              </Button>
            </div>
          )}

          {/* Listings Grid */}
          {!isLoading && !error && data && data.items.length > 0 && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {data.items.map((listing) => (
                  <MarketplaceListingCard key={listing.listing_id} listing={listing} />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-8 flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={!data.page_info.has_previous_page}
                      aria-label="Previous page"
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={!data.page_info.has_next_page}
                      aria-label="Next page"
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
