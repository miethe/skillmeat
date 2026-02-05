/**
 * React Query hooks for marketplace data fetching
 *
 * These hooks provide data fetching, caching, and state management for marketplace operations.
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { useToast } from './use-toast';
import { ApiError, apiRequest } from '@/lib/api';
import type {
  MarketplaceListingDetail,
  MarketplaceFilters,
  ListingsPageResponse,
  BrokerInfo,
  InstallRequest,
  InstallResponse,
  PublishRequest,
  PublishResponse,
} from '@/types/marketplace';

// Query keys
const marketplaceKeys = {
  all: ['marketplace'] as const,
  listings: () => [...marketplaceKeys.all, 'listings'] as const,
  listing: (filters: MarketplaceFilters, cursor?: string) =>
    [...marketplaceKeys.listings(), filters, cursor] as const,
  details: () => [...marketplaceKeys.all, 'detail'] as const,
  detail: (id: string) => [...marketplaceKeys.details(), id] as const,
  brokers: () => [...marketplaceKeys.all, 'brokers'] as const,
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

  if (filters.broker) params.append('broker', filters.broker);
  if (filters.query) params.append('query', filters.query);
  if (filters.tags && filters.tags.length > 0) {
    params.append('tags', filters.tags.join(','));
  }
  if (filters.license) params.append('license', filters.license);
  if (filters.publisher) params.append('publisher', filters.publisher);
  if (cursor) params.append('cursor', cursor);
  params.append('limit', limit.toString());

  return apiRequest<ListingsPageResponse>(`/marketplace/listings?${params}`);
}

/**
 * Fetch single listing detail
 */
async function fetchListingDetail(listingId: string): Promise<MarketplaceListingDetail> {
  try {
    return await apiRequest<MarketplaceListingDetail>(`/marketplace/listings/${listingId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      throw new Error(`Listing not found: ${listingId}`);
    }
    throw error;
  }
}

/**
 * Fetch available brokers
 */
async function fetchBrokers(): Promise<BrokerInfo[]> {
  const data = await apiRequest<{ brokers: BrokerInfo[] }>(`/marketplace/brokers`);
  return data.brokers;
}

/**
 * Install a marketplace listing
 */
async function installListing(request: InstallRequest): Promise<InstallResponse> {
  try {
    return await apiRequest<InstallResponse>(`/marketplace/install`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  } catch (error) {
    if (error instanceof ApiError) {
      throw new Error(error.message);
    }
    throw error;
  }
}

/**
 * Publish a bundle to marketplace
 */
async function publishBundle(request: PublishRequest): Promise<PublishResponse> {
  try {
    return await apiRequest<PublishResponse>(`/marketplace/publish`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  } catch (error) {
    if (error instanceof ApiError) {
      throw new Error(error.message);
    }
    throw error;
  }
}

/**
 * Hook to fetch paginated marketplace listings
 */
export function useListings(filters: MarketplaceFilters = {}, limit: number = 50) {
  return useInfiniteQuery({
    queryKey: marketplaceKeys.listing(filters, 'infinite'),
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
      // Installed artifact appears in collection
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });

      // Show success toast
      toast({
        title: 'Installation successful',
        description: `Installed ${data.artifacts_imported.length} artifacts from ${data.listing_id}`,
      });
    },
    onError: (error: Error) => {
      // Show error toast
      toast({
        title: 'Installation failed',
        description: error.message,
        variant: 'destructive',
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
      if (data.status === 'approved') {
        toast({
          title: 'Bundle published',
          description: `Your bundle has been approved and is now live!`,
        });
      } else if (data.status === 'pending') {
        toast({
          title: 'Bundle submitted',
          description: `Your bundle is pending review. Submission ID: ${data.submission_id}`,
        });
      }
    },
    onError: (error: Error) => {
      // Show error toast
      toast({
        title: 'Publish failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}
