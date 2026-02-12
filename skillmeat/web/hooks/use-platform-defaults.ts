/**
 * React hooks for platform defaults and custom context configuration
 * using TanStack Query
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getAllPlatformDefaults,
  updatePlatformDefault,
  resetPlatformDefault,
  getCustomContextConfig,
  updateCustomContextConfig,
} from '@/lib/api/platform-defaults';
import type {
  AllPlatformDefaultsResponse,
  PlatformDefaultsResponse,
  PlatformDefaultsUpdateRequest,
  CustomContextConfig,
  CustomContextConfigUpdateRequest,
} from '@/lib/api/platform-defaults';
import { PLATFORM_DEFAULTS } from '@/lib/constants/platform-defaults';

// =============================================================================
// Query Key Factory
// =============================================================================

export const platformDefaultsKeys = {
  all: ['platform-defaults'] as const,
  lists: () => [...platformDefaultsKeys.all, 'list'] as const,
  list: () => [...platformDefaultsKeys.lists()] as const,
  details: () => [...platformDefaultsKeys.all, 'detail'] as const,
  detail: (platform: string) => [...platformDefaultsKeys.details(), platform] as const,
  customContext: () => [...platformDefaultsKeys.all, 'custom-context'] as const,
};

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Fetch all platform defaults.
 * Falls back to frontend constants (placeholderData) when API is unavailable.
 */
export function usePlatformDefaults() {
  return useQuery<AllPlatformDefaultsResponse, Error>({
    queryKey: platformDefaultsKeys.list(),
    queryFn: getAllPlatformDefaults,
    staleTime: 5 * 60 * 1000, // 5 minutes
    placeholderData: { defaults: PLATFORM_DEFAULTS },
  });
}

/**
 * Fetch custom context configuration.
 */
export function useCustomContextConfig() {
  return useQuery<CustomContextConfig, Error>({
    queryKey: platformDefaultsKeys.customContext(),
    queryFn: getCustomContextConfig,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Update a single platform's defaults.
 */
export function useUpdatePlatformDefault() {
  const queryClient = useQueryClient();

  return useMutation<
    PlatformDefaultsResponse,
    Error,
    { platform: string; data: PlatformDefaultsUpdateRequest }
  >({
    mutationFn: ({ platform, data }) => updatePlatformDefault(platform, data),
    onSuccess: (_, { platform }) => {
      queryClient.invalidateQueries({ queryKey: platformDefaultsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: platformDefaultsKeys.detail(platform) });
    },
  });
}

/**
 * Reset a platform's defaults back to built-in values.
 */
export function useResetPlatformDefault() {
  const queryClient = useQueryClient();

  return useMutation<PlatformDefaultsResponse, Error, string>({
    mutationFn: (platform: string) => resetPlatformDefault(platform),
    onSuccess: (_, platform) => {
      queryClient.invalidateQueries({ queryKey: platformDefaultsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: platformDefaultsKeys.detail(platform) });
    },
  });
}

/**
 * Update custom context configuration.
 */
export function useUpdateCustomContextConfig() {
  const queryClient = useQueryClient();

  return useMutation<CustomContextConfig, Error, CustomContextConfigUpdateRequest>({
    mutationFn: (data: CustomContextConfigUpdateRequest) => updateCustomContextConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformDefaultsKeys.customContext() });
    },
  });
}
