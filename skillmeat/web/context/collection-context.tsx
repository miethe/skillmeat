'use client';

import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useCollections, useCollection } from '@/hooks/use-collections';
import { useGroups } from '@/hooks/use-groups';
import type { Collection } from '@/types/collections';
import type { Group } from '@/types/groups';

interface CollectionContextValue {
  // State
  selectedCollectionId: string | null;
  selectedGroupId: string | null;

  // Derived data from hooks
  collections: Collection[];
  currentCollection: Collection | null;
  currentGroups: Group[];

  // Loading states
  isLoadingCollections: boolean;
  isLoadingCollection: boolean;
  isLoadingGroups: boolean;

  // Error states
  collectionsError: Error | null;
  collectionError: Error | null;
  groupsError: Error | null;

  // Actions
  setSelectedCollectionId: (id: string | null) => void;
  setSelectedGroupId: (id: string | null) => void;
  refreshCollections: () => void;
  refreshGroups: () => void;
}

const CollectionContext = createContext<CollectionContextValue | null>(null);

const STORAGE_KEY = 'skillmeat-selected-collection';

interface CollectionProviderProps {
  children: ReactNode;
}

export function CollectionProvider({ children }: CollectionProviderProps) {
  const [selectedCollectionId, setSelectedCollectionIdState] = useState<string | null>(null);
  const [hasMounted, setHasMounted] = useState(false);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  useEffect(() => {
    setHasMounted(true);
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          setSelectedCollectionIdState(stored);
        }
      } catch {
        // Ignore localStorage errors
      }
    }
  }, []);

  // Persist to localStorage
  const setSelectedCollectionId = useCallback((id: string | null) => {
    setSelectedCollectionIdState(id);
    setSelectedGroupId(null); // Reset group when collection changes
    if (typeof window !== 'undefined') {
      try {
        if (id) {
          localStorage.setItem(STORAGE_KEY, id);
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      } catch {
        // Ignore localStorage errors
      }
    }
  }, []);

  // Fetch collections
  const {
    data: collectionsData,
    isLoading: isLoadingCollections,
    error: collectionsError,
    refetch: refetchCollections,
  } = useCollections();

  // Fetch current collection details
  const {
    data: currentCollection,
    isLoading: isLoadingCollection,
    error: collectionError,
  } = useCollection(selectedCollectionId ?? undefined);

  // Fetch groups for current collection
  const {
    data: groupsData,
    isLoading: isLoadingGroups,
    error: groupsError,
    refetch: refetchGroups,
  } = useGroups(selectedCollectionId ?? undefined);

  const refreshCollections = useCallback(() => {
    refetchCollections();
  }, [refetchCollections]);

  const refreshGroups = useCallback(() => {
    refetchGroups();
  }, [refetchGroups]);

  // Memoize context value to prevent unnecessary re-renders
  const value = useMemo<CollectionContextValue>(
    () => ({
      selectedCollectionId,
      selectedGroupId,
      collections: collectionsData?.items ?? [],
      currentCollection: currentCollection ?? null,
      currentGroups: groupsData?.groups ?? [],
      isLoadingCollections,
      isLoadingCollection,
      isLoadingGroups,
      collectionsError: collectionsError as Error | null,
      collectionError: collectionError as Error | null,
      groupsError: groupsError as Error | null,
      setSelectedCollectionId,
      setSelectedGroupId,
      refreshCollections,
      refreshGroups,
    }),
    [
      selectedCollectionId,
      selectedGroupId,
      collectionsData,
      currentCollection,
      groupsData,
      isLoadingCollections,
      isLoadingCollection,
      isLoadingGroups,
      collectionsError,
      collectionError,
      groupsError,
      setSelectedCollectionId,
      refreshCollections,
      refreshGroups,
    ]
  );

  return <CollectionContext.Provider value={value}>{children}</CollectionContext.Provider>;
}

export { CollectionContext };
