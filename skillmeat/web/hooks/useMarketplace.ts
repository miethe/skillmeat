/**
 * React Query hooks for marketplace data fetching
 *
 * These hooks provide data fetching, caching, and state management for marketplace listings.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  Listing,
  ListingDetail,
  ListingsResponse,
  MarketplaceFilters,
  ListingSortOrder,
  InstallRequest,
  InstallResponse,
  PublishRequest,
  PublishResponse,
} from "@/types/marketplace";

// API base URL - will be configured via environment variable
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Query keys
const marketplaceKeys = {
  all: ["marketplace"] as const,
  listings: () => [...marketplaceKeys.all, "listings"] as const,
  listing: (filters: MarketplaceFilters, sort: ListingSortOrder, page: number) =>
    [...marketplaceKeys.listings(), filters, sort, page] as const,
  details: () => [...marketplaceKeys.all, "detail"] as const,
  detail: (id: string) => [...marketplaceKeys.details(), id] as const,
};

/**
 * Hook to fetch marketplace listings with filtering and pagination
 */
export function useMarketplaceListings(
  filters: MarketplaceFilters = {},
  sort: ListingSortOrder = "newest",
  page: number = 1,
  perPage: number = 20
) {
  return useQuery({
    queryKey: marketplaceKeys.listing(filters, sort, page),
    queryFn: async (): Promise<ListingsResponse> => {
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("per_page", perPage.toString());
      params.append("sort", sort);

      if (filters.search) params.append("search", filters.search);
      if (filters.artifact_type) params.append("artifact_type", filters.artifact_type);
      if (filters.license) params.append("license", filters.license);
      if (filters.publisher) params.append("publisher", filters.publisher);
      if (filters.free_only) params.append("free_only", "true");
      if (filters.verified_only) params.append("verified_only", "true");
      if (filters.tags) {
        filters.tags.forEach((tag) => params.append("tags", tag));
      }

      const response = await fetch(`${API_BASE}/marketplace/listings?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch listings: ${response.statusText}`);
      }

      return response.json();
    },
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
  });
}

/**
 * Hook to fetch a single listing by ID
 */
export function useMarketplaceListing(id: string) {
  return useQuery({
    queryKey: marketplaceKeys.detail(id),
    queryFn: async (): Promise<ListingDetail> => {
      const response = await fetch(`${API_BASE}/marketplace/listings/${id}`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`Listing not found: ${id}`);
        }
        throw new Error(`Failed to fetch listing: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!id,
    staleTime: 10 * 60 * 1000, // Consider data fresh for 10 minutes
  });
}

/**
 * Hook to install a marketplace listing
 */
export function useInstallListing() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: InstallRequest): Promise<InstallResponse> => {
      const response = await fetch(`${API_BASE}/marketplace/install`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // TODO: Add authentication header when auth is implemented
          // Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || "Failed to install listing");
      }

      return response.json();
    },
    onSuccess: (data) => {
      // Invalidate relevant queries after successful install
      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    },
  });
}

/**
 * Hook to publish a bundle to marketplace
 */
export function usePublishBundle() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: PublishRequest): Promise<PublishResponse> => {
      const response = await fetch(`${API_BASE}/marketplace/publish`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // TODO: Add authentication header when auth is implemented
          // Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || "Failed to publish bundle");
      }

      return response.json();
    },
    onSuccess: () => {
      // Invalidate marketplace listings after successful publish
      queryClient.invalidateQueries({ queryKey: marketplaceKeys.listings() });
    },
  });
}
