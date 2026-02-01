'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { Toaster } from '@/components/ui/toaster';
import { NotificationProvider } from '@/lib/notification-store';
import { CollectionProvider } from '@/context/collection-context';
import { useSources, useCollections } from '@/hooks';

/**
 * DataPrefetcher - Background data preloading at app initialization.
 *
 * ## Purpose
 * Prefetches commonly needed data at app initialization to eliminate delays
 * when navigating to pages or opening modals that need this data.
 *
 * ## Prefetch Strategy
 * We prefetch high-value, low-cost data that's accessed frequently across the app:
 *
 * - **Sources** (`useSources`): Marketplace sources list used in import modals.
 *   Without prefetch: 2-5s delay when opening Sources tab in modals.
 *
 * - **Collections** (`useCollections`): User collections for badge display and
 *   collection management. Used on artifact cards across collection and project pages.
 *
 * ## Cache Configuration
 * Both hooks configure `staleTime: 5 minutes` to match backend cache TTL.
 * This means:
 * - Data is considered fresh for 5 minutes after fetch
 * - No duplicate requests on navigation within that window
 * - Automatic background refresh after staleTime expires
 *
 * ## Performance Characteristics
 * - Non-blocking: Does not prevent initial render
 * - Silent: No loading indicators (background operation)
 * - Cost: ~100-500ms added to app initialization (parallel fetches)
 * - Benefit: Eliminates 2-5s perceived delay on first modal/page access
 *
 * @see IMPL-2026-01-30-COLLECTION-DATA-CONSISTENCY Phase 5
 */
function DataPrefetcher({ children }: { children: React.ReactNode }) {
  // Prefetch sources data - eliminates 2-5s delay when opening Sources tab in modals
  useSources(50);

  // Prefetch collections data - available immediately on navigation
  // Used for collection badges on artifact cards and collection management pages
  useCollections();

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <DataPrefetcher>
        <CollectionProvider>
          <NotificationProvider>
            {children}
            <Toaster />
          </NotificationProvider>
        </CollectionProvider>
      </DataPrefetcher>
    </QueryClientProvider>
  );
}
