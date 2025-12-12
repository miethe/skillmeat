'use client';

import { useContext } from 'react';
import { CollectionContext } from '@/context/collection-context';

/**
 * Hook to access the CollectionContext
 *
 * Provides shared state for collections, groups, and navigation.
 * Must be used within a CollectionProvider.
 *
 * @throws Error if used outside CollectionProvider
 * @returns CollectionContextValue with collections, groups, loading states, and actions
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const {
 *     selectedCollectionId,
 *     currentGroups,
 *     setSelectedGroupId
 *   } = useCollectionContext();
 *
 *   return (
 *     <div>
 *       {currentGroups.map(group => (
 *         <GroupCard
 *           key={group.id}
 *           group={group}
 *           onClick={() => setSelectedGroupId(group.id)}
 *         />
 *       ))}
 *     </div>
 *   );
 * }
 * ```
 */
export function useCollectionContext() {
  const context = useContext(CollectionContext);

  if (!context) {
    throw new Error(
      'useCollectionContext must be used within a CollectionProvider. ' +
        'Make sure to wrap your app with <CollectionProvider>.'
    );
  }

  return context;
}
