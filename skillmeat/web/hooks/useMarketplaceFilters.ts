/**
 * Hook for managing marketplace filter state
 *
 * Provides centralized state management for marketplace filters with URL sync
 */

import { useState, useCallback, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type { MarketplaceFilters, ListingSortOrder, ArtifactCategory } from "@/types/marketplace";

interface UseMarketplaceFiltersReturn {
  filters: MarketplaceFilters;
  sort: ListingSortOrder;
  page: number;
  setFilters: (filters: Partial<MarketplaceFilters>) => void;
  setSort: (sort: ListingSortOrder) => void;
  setPage: (page: number) => void;
  resetFilters: () => void;
  clearSearch: () => void;
}

const DEFAULT_FILTERS: MarketplaceFilters = {
  search: "",
  tags: [],
  free_only: false,
  verified_only: false,
};

const DEFAULT_SORT: ListingSortOrder = "newest";
const DEFAULT_PAGE = 1;

/**
 * Hook to manage marketplace filters with URL synchronization
 */
export function useMarketplaceFilters(): UseMarketplaceFiltersReturn {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Initialize state from URL params
  const [filters, setFiltersState] = useState<MarketplaceFilters>(() => {
    const search = searchParams.get("search") || "";
    const tags = searchParams.getAll("tags");
    const license = searchParams.get("license") || undefined;
    const publisher = searchParams.get("publisher") || undefined;
    const artifact_type = searchParams.get("type") as ArtifactCategory | undefined;
    const free_only = searchParams.get("free") === "true";
    const verified_only = searchParams.get("verified") === "true";

    return {
      search,
      tags: tags.length > 0 ? tags : undefined,
      license,
      publisher,
      artifact_type,
      free_only,
      verified_only,
    };
  });

  const [sort, setSortState] = useState<ListingSortOrder>(
    () => (searchParams.get("sort") as ListingSortOrder) || DEFAULT_SORT
  );

  const [page, setPageState] = useState<number>(() => {
    const pageParam = searchParams.get("page");
    return pageParam ? parseInt(pageParam, 10) : DEFAULT_PAGE;
  });

  // Update URL when filters change
  const updateURL = useCallback(
    (newFilters: MarketplaceFilters, newSort: ListingSortOrder, newPage: number) => {
      const params = new URLSearchParams();

      if (newFilters.search) params.set("search", newFilters.search);
      if (newFilters.license) params.set("license", newFilters.license);
      if (newFilters.publisher) params.set("publisher", newFilters.publisher);
      if (newFilters.artifact_type) params.set("type", newFilters.artifact_type);
      if (newFilters.free_only) params.set("free", "true");
      if (newFilters.verified_only) params.set("verified", "true");
      if (newFilters.tags && newFilters.tags.length > 0) {
        newFilters.tags.forEach((tag) => params.append("tags", tag));
      }
      if (newSort !== DEFAULT_SORT) params.set("sort", newSort);
      if (newPage !== DEFAULT_PAGE) params.set("page", newPage.toString());

      router.push(`/marketplace?${params.toString()}`, { scroll: false });
    },
    [router]
  );

  const setFilters = useCallback(
    (newFilters: Partial<MarketplaceFilters>) => {
      const updated = { ...filters, ...newFilters };
      setFiltersState(updated);
      setPageState(1); // Reset to first page on filter change
      updateURL(updated, sort, 1);
    },
    [filters, sort, updateURL]
  );

  const setSort = useCallback(
    (newSort: ListingSortOrder) => {
      setSortState(newSort);
      setPageState(1); // Reset to first page on sort change
      updateURL(filters, newSort, 1);
    },
    [filters, updateURL]
  );

  const setPage = useCallback(
    (newPage: number) => {
      setPageState(newPage);
      updateURL(filters, sort, newPage);
    },
    [filters, sort, updateURL]
  );

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_FILTERS);
    setSortState(DEFAULT_SORT);
    setPageState(DEFAULT_PAGE);
    router.push("/marketplace");
  }, [router]);

  const clearSearch = useCallback(() => {
    setFilters({ search: "" });
  }, [setFilters]);

  return {
    filters,
    sort,
    page,
    setFilters,
    setSort,
    setPage,
    resetFilters,
    clearSearch,
  };
}
