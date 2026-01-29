'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { Toaster } from '@/components/ui/toaster';
import { NotificationProvider } from '@/lib/notification-store';
import { CollectionProvider } from '@/context/collection-context';
import { useSources } from '@/hooks';

/**
 * Prefetches commonly needed data at app initialization to eliminate
 * delays when opening modals (e.g., Sources tab).
 *
 * This component renders nothing but triggers TanStack Query hooks
 * that populate the cache for immediate access later.
 */
function DataPrefetcher({ children }: { children: React.ReactNode }) {
  // Prefetch sources data - eliminates 2-5s delay when opening Sources tab in modals
  useSources(50);

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
