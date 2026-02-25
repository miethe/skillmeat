/**
 * Custom hooks for icon pack management using TanStack Query
 *
 * Provides data fetching, caching, and mutation state for icon packs.
 * Uses the live API (/api/v1/settings/icon-packs) with proper cache
 * invalidation.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchIconPacks,
  patchIconPacks,
  installIconPackFromUrl,
  installIconPackFromFile,
  deleteIconPack,
  type IconPackPatchEntry,
} from '@/lib/api/icon-packs';
import type { IconPack } from '@/lib/icon-constants';

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

/**
 * Query key factory for type-safe icon pack cache management
 */
export const iconPackKeys = {
  all: ['icon-packs'] as const,
  lists: () => [...iconPackKeys.all, 'list'] as const,
  list: () => [...iconPackKeys.lists()] as const,
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/**
 * Fetch all icon packs with their current enabled state
 *
 * Uses a 5-minute stale time because icon pack configuration changes
 * infrequently (browsing-tier freshness).
 *
 * @returns Query result with the list of icon packs
 *
 * @example
 * ```tsx
 * const { data: iconPacks, isLoading } = useIconPacks();
 * const enabledPacks = iconPacks?.filter((p) => p.enabled) ?? [];
 * ```
 */
export function useIconPacks() {
  return useQuery({
    queryKey: iconPackKeys.list(),
    queryFn: fetchIconPacks,
    staleTime: 5 * 60 * 1000, // 5 minutes - config doesn't change often
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/**
 * Patch icon pack enabled states
 *
 * Accepts an array of `{ pack_id, enabled }` objects so one or many packs can
 * be toggled in a single request.
 *
 * @returns Mutation function for patching icon pack settings
 *
 * @example
 * ```tsx
 * const patchPacks = usePatchIconPacks();
 * await patchPacks.mutateAsync([{ pack_id: 'lucide-default', enabled: false }]);
 * ```
 */
export function usePatchIconPacks() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (entries: IconPackPatchEntry[]): Promise<IconPack[]> => patchIconPacks(entries),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: iconPackKeys.all });
    },
  });
}

export function useInstallIconPackFromUrl() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (url: string) => installIconPackFromUrl(url),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: iconPackKeys.all }); },
  });
}

export function useInstallIconPackFromFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => installIconPackFromFile(file),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: iconPackKeys.all }); },
  });
}

export function useDeleteIconPack() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (packId: string) => deleteIconPack(packId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: iconPackKeys.all }); },
  });
}
