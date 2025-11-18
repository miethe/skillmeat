/**
 * React Query hooks for marketplace data fetching
 *
 * These hooks provide data fetching, caching, and state management for marketplace operations.
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from "@tanstack/react-query";
import { useToast } from "./use-toast";
import type {
  MarketplaceListing,
  MarketplaceListingDetail,
  MarketplaceFilters,
  ListingsPageResponse,
  BrokerInfo,
  InstallRequest,
  InstallResponse,
  PublishRequest,
  PublishResponse,
} from "@/types/marketplace";

// API base URL - adjust based on environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// Query keys
const marketplaceKeys = {
  all: ["marketplace"] as const,
  listings: () => [...marketplaceKeys.all, "listings"] as const,
  listing: (filters: MarketplaceFilters, cursor?: string) =>
    [...marketplaceKeys.listings(), filters, cursor] as const,
  details: () => [...marketplaceKeys.all, "detail"] as const,
  detail: (id: string) => [...marketplaceKeys.details(), id] as const,
  brokers: () => [...marketplaceKeys.all, "brokers"] as const,
};

/**
 * Fetch listings from marketplace API
 */
async function fetchListings(
  filters: MarketplaceFilters = {},
  cursor?: string,
  limit: number = 50
): Promise<ListingsPageResponse> {
  const params = new URLSearchParams();

  if (filters.broker) params.append("broker", filters.broker);
  if (filters.query) params.append("query", filters.query);
  if (filters.tags && filters.tags.length > 0) {
    params.append("tags", filters.tags.join(","));
  }
  if (filters.license) params.append("license", filters.license);
  if (filters.publisher) params.append("publisher", filters.publisher);
  if (cursor) params.append("cursor", cursor);
  params.append("limit", limit.toString());

  const response = await fetch(`${API_BASE_URL}/marketplace/listings?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch listings: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch single listing detail
 */
async function fetchListingDetail(listingId: string): Promise<MarketplaceListingDetail> {
  const response = await fetch(`${API_BASE_URL}/marketplace/listings/${listingId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Listing not found: ${listingId}`);
    }
    throw new Error(`Failed to fetch listing: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch available brokers
 */
async function fetchBrokers(): Promise<BrokerInfo[]> {
  const response = await fetch(`${API_BASE_URL}/marketplace/brokers`);

  if (!response.ok) {
    throw new Error(`Failed to fetch brokers: ${response.statusText}`);
  }

  const data = await response.json();
  return data.brokers;
}

/**
 * Install a marketplace listing
 */
async function installListing(request: InstallRequest): Promise<InstallResponse> {
  const response = await fetch(`${API_BASE_URL}/marketplace/install`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to install listing: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Publish a bundle to marketplace
 */
async function publishBundle(request: PublishRequest): Promise<PublishResponse> {
  const response = await fetch(`${API_BASE_URL}/marketplace/publish`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to publish bundle: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Hook to fetch paginated marketplace listings
 */
export function useListings(filters: MarketplaceFilters = {}, limit: number = 50) {
  return useInfiniteQuery({
    queryKey: marketplaceKeys.listing(filters, "infinite"),
    queryFn: ({ pageParam }) => fetchListings(filters, pageParam, limit),
    getNextPageParam: (lastPage) =>
      lastPage.page_info.has_next_page ? lastPage.page_info.end_cursor : undefined,
    getPreviousPageParam: (firstPage) =>
      firstPage.page_info.has_previous_page ? firstPage.page_info.start_cursor : undefined,
    staleTime: 60000, // Consider data fresh for 1 minute
    initialPageParam: undefined as string | undefined,
  });
}

/**
 * Hook to fetch a single listing detail
 */
export function useListing(listingId: string) {
  return useQuery({
    queryKey: marketplaceKeys.detail(listingId),
    queryFn: () => fetchListingDetail(listingId),
    enabled: !!listingId,
    staleTime: 300000, // Consider data fresh for 5 minutes
  });
}

/**
 * Hook to fetch available brokers
 */
export function useBrokers() {
  return useQuery({
    queryKey: marketplaceKeys.brokers(),
    queryFn: fetchBrokers,
    staleTime: 300000, // Consider data fresh for 5 minutes
  });
}

/**
 * Hook to install a marketplace listing
 */
export function useInstallListing() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: installListing,
    onSuccess: (data) => {
      // Invalidate listings cache
      queryClient.invalidateQueries({ queryKey: marketplaceKeys.listings() });

      // Show success toast
      toast({
        title: "Installation successful",
        description: `Installed ${data.artifacts_imported.length} artifacts from ${data.listing_id}`,
      });
    },
    onError: (error: Error) => {
      // Show error toast
      toast({
        title: "Installation failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to publish a bundle to marketplace
 */
export function usePublishBundle() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: publishBundle,
    onSuccess: (data) => {
      // Invalidate listings cache
      queryClient.invalidateQueries({ queryKey: marketplaceKeys.listings() });

      // Show success toast based on status
      if (data.status === "approved") {
        toast({
          title: "Bundle published",
          description: `Your bundle has been approved and is now live!`,
        });
      } else if (data.status === "pending") {
        toast({
          title: "Bundle submitted",
          description: `Your bundle is pending review. Submission ID: ${data.submission_id}`,
        });
      }
    },
    onError: (error: Error) => {
      // Show error toast
      toast({
        title: "Publish failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
