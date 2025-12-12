# Collection Context

Shared state management for collections and groups navigation.

## Overview

The `CollectionContext` provides centralized state management for:
- Selected collection and group
- Collections list and current collection details
- Groups list for the current collection
- Loading and error states
- Refresh actions

## Usage

### Setup

The `CollectionProvider` is already configured in `components/providers.tsx`:

```tsx
<QueryClientProvider client={queryClient}>
  <CollectionProvider>
    {/* Your app */}
  </CollectionProvider>
</QueryClientProvider>
```

### Accessing Context

Use the `useCollectionContext` hook in any component:

```tsx
'use client';

import { useCollectionContext } from '@/hooks/use-collection-context';

export function MyComponent() {
  const {
    // State
    selectedCollectionId,
    selectedGroupId,

    // Data
    collections,
    currentCollection,
    currentGroups,

    // Loading states
    isLoadingCollections,
    isLoadingCollection,
    isLoadingGroups,

    // Actions
    setSelectedCollectionId,
    setSelectedGroupId,
    refreshCollections,
    refreshGroups,
  } = useCollectionContext();

  return (
    <div>
      {/* Your UI */}
    </div>
  );
}
```

## Examples

### Collection Selector

```tsx
'use client';

import { useCollectionContext } from '@/hooks/use-collection-context';

export function CollectionSelector() {
  const { collections, selectedCollectionId, setSelectedCollectionId } = useCollectionContext();

  return (
    <select
      value={selectedCollectionId ?? ''}
      onChange={(e) => setSelectedCollectionId(e.target.value || null)}
    >
      <option value="">Select a collection...</option>
      {collections.map((collection) => (
        <option key={collection.id} value={collection.id}>
          {collection.name} ({collection.artifact_count} artifacts)
        </option>
      ))}
    </select>
  );
}
```

### Group List

```tsx
'use client';

import { useCollectionContext } from '@/hooks/use-collection-context';

export function GroupList() {
  const {
    currentGroups,
    selectedGroupId,
    setSelectedGroupId,
    isLoadingGroups,
  } = useCollectionContext();

  if (isLoadingGroups) {
    return <div>Loading groups...</div>;
  }

  return (
    <ul>
      {currentGroups.map((group) => (
        <li
          key={group.id}
          onClick={() => setSelectedGroupId(group.id)}
          className={selectedGroupId === group.id ? 'selected' : ''}
        >
          {group.name} ({group.artifact_count} artifacts)
        </li>
      ))}
    </ul>
  );
}
```

### Current Collection Details

```tsx
'use client';

import { useCollectionContext } from '@/hooks/use-collection-context';

export function CollectionHeader() {
  const {
    currentCollection,
    isLoadingCollection,
    refreshCollections,
  } = useCollectionContext();

  if (isLoadingCollection) {
    return <div>Loading...</div>;
  }

  if (!currentCollection) {
    return <div>No collection selected</div>;
  }

  return (
    <header>
      <h1>{currentCollection.name}</h1>
      <p>{currentCollection.artifact_count} artifacts</p>
      <button onClick={refreshCollections}>Refresh</button>
    </header>
  );
}
```

### Error Handling

```tsx
'use client';

import { useCollectionContext } from '@/hooks/use-collection-context';

export function CollectionWithErrors() {
  const {
    collections,
    collectionsError,
    isLoadingCollections,
  } = useCollectionContext();

  if (isLoadingCollections) {
    return <div>Loading...</div>;
  }

  if (collectionsError) {
    return (
      <div className="error">
        <p>Failed to load collections</p>
        <p>{collectionsError.message}</p>
      </div>
    );
  }

  return (
    <ul>
      {collections.map((c) => (
        <li key={c.id}>{c.name}</li>
      ))}
    </ul>
  );
}
```

## Features

### Persistent Selection

The selected collection ID is automatically persisted to `localStorage` and restored on page reload:

```typescript
// Automatically saved
setSelectedCollectionId('default');

// Automatically restored on next visit
// selectedCollectionId will be 'default'
```

### Group Reset on Collection Change

When changing collections, the selected group is automatically reset:

```typescript
setSelectedCollectionId('default');
setSelectedGroupId('group-1');

// Change collection - group is automatically cleared
setSelectedCollectionId('custom');
// selectedGroupId is now null
```

### SSR-Safe

The context handles server-side rendering safely:

```typescript
// No localStorage access during SSR
const [selectedCollectionId, setSelectedCollectionIdState] = useState<string | null>(() => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(STORAGE_KEY);
});
```

### Optimized Re-renders

The context value is memoized to prevent unnecessary re-renders:

```typescript
const value = useMemo<CollectionContextValue>(
  () => ({
    // All values and callbacks
  }),
  [/* dependencies */]
);
```

## Type Safety

All types are fully typed with TypeScript:

```typescript
interface CollectionContextValue {
  selectedCollectionId: string | null;
  selectedGroupId: string | null;
  collections: Collection[];
  currentCollection: Collection | null;
  currentGroups: Group[];
  isLoadingCollections: boolean;
  isLoadingCollection: boolean;
  isLoadingGroups: boolean;
  collectionsError: Error | null;
  collectionError: Error | null;
  groupsError: Error | null;
  setSelectedCollectionId: (id: string | null) => void;
  setSelectedGroupId: (id: string | null) => void;
  refreshCollections: () => void;
  refreshGroups: () => void;
}
```

## Files

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/context/collection-context.tsx` - Context provider
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-collection-context.ts` - Hook to access context
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/providers.tsx` - Provider setup
