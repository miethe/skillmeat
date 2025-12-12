---
title: "Phase 3: Frontend Foundation - Collections & Navigation Enhancement"
phase: 3
status: pending
assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
dependencies:
  - Phase 2 (Backend API)
story_points: 10
duration: 1.5 weeks
---

# Phase 3: Frontend Foundation

**Complexity**: React component structure, type definitions, context management
**Story Points**: 10 | **Duration**: 1.5 weeks | **Status**: Pending

---

## Phase Objective

Create foundational React components, TypeScript types, custom hooks, and context providers for the Collections system. This phase establishes the infrastructure for subsequent UI implementation.

---

## Task Breakdown

### 1. Navigation Restructuring (TASK-3.1)
**Description**: Restructure sidebar navigation with collapsible Collections parent section

**Acceptance Criteria**:
- [ ] Navigation updated to add parent "Collections" section (collapsible)
- [ ] Nested tabs created: Manage, Projects, MCP Servers
- [ ] Sidebar component refactored to support nested navigation items
- [ ] Collapsible state persisted to localStorage
- [ ] Active tab properly highlighted based on current route
- [ ] Responsive design maintained on mobile/tablet
- [ ] Accessibility: Keyboard navigation (arrows, Enter), screen reader labels
- [ ] Component tests pass (90%+ coverage)

**Files to Create/Modify**:
- Modify: `/skillmeat/web/components/navigation.tsx`
- Create: `/skillmeat/web/components/nav-section.tsx` (reusable collapsible section)
- Create: `/skillmeat/web/types/navigation.ts` (TypeScript types)

**Estimated Effort**: 2 points

---

### 2. TypeScript Types for Collections & Groups (TASK-3.2)
**Description**: Define TypeScript interfaces for collections, groups, and deployment data

**Acceptance Criteria**:
- [ ] `Collection` interface with id, name, description, created_at, updated_at, group_count, artifact_count
- [ ] `Group` interface with id, collection_id, name, description, position, artifact_count
- [ ] `CollectionArtifact` interface for association data
- [ ] `GroupArtifact` interface for artifact positioning
- [ ] `Deployment` interface with artifact_id, project_id, status, versions
- [ ] `DeploymentSummary` interface for aggregated data
- [ ] Enums: `DeploymentStatus` (active, inactive, error, pending)
- [ ] Full type strictness (no `any`, proper generics)
- [ ] Consistent with backend Pydantic schemas
- [ ] JSDoc comments for all types
- [ ] Re-exported from index file for convenient imports

**Files to Create/Modify**:
- Create: `/skillmeat/web/types/collections.ts`
- Create: `/skillmeat/web/types/groups.ts`
- Create: `/skillmeat/web/types/deployments.ts`
- Modify: `/skillmeat/web/types/index.ts`

**Estimated Effort**: 1.5 points

---

### 3. useCollections Hook (TASK-3.3)
**Description**: Custom React hook for collection data fetching and management

**Acceptance Criteria**:
- [ ] Hook uses TanStack Query for state management
- [ ] `useCollections()` - Fetch all collections with pagination
  - [ ] Returns: { data, isLoading, error, refetch, isRefetching }
  - [ ] Query key: ['collections', page, pageSize]
  - [ ] Stale time: 5 minutes
  - [ ] Error handling with meaningful messages
- [ ] `useCollection(id)` - Fetch single collection with groups
  - [ ] Proper loading and error states
  - [ ] Dependent query (enabled based on id)
- [ ] `useCreateCollection()` - Create collection mutation
  - [ ] Returns: { mutate, isPending, error, isSuccess }
  - [ ] Invalidates collections query on success
  - [ ] Optimistic updates (optional)
- [ ] `useUpdateCollection()` - Update collection mutation
  - [ ] Partial update support
  - [ ] Proper error handling
- [ ] `useDeleteCollection()` - Delete collection mutation
  - [ ] Confirmation handling (optional, UI concern)
  - [ ] Cascading delete awareness
- [ ] `useCollectionArtifacts(collectionId)` - Get artifacts in collection
- [ ] Hooks follow React Query best practices
- [ ] Comprehensive JSDoc comments

**Files to Create/Modify**:
- Create: `/skillmeat/web/hooks/use-collections.ts`
- Modify: `/skillmeat/web/hooks/index.ts`

**Estimated Effort**: 2 points

---

### 4. useGroups Hook (TASK-3.4)
**Description**: Custom React hook for group management

**Acceptance Criteria**:
- [ ] `useGroups(collectionId)` - Fetch groups in collection
  - [ ] Ordered by position field
  - [ ] Dependent query on collectionId
  - [ ] Returns: { data, isLoading, error, refetch }
- [ ] `useGroup(groupId)` - Fetch single group with artifacts
  - [ ] Lazy loading of artifacts
  - [ ] Proper error states
- [ ] `useCreateGroup()` - Create group mutation
  - [ ] Optimistically updates groups query
  - [ ] Validates unique name in collection
- [ ] `useUpdateGroup()` - Update group (name, description, position)
  - [ ] Handles position changes with reordering
- [ ] `useDeleteGroup()` - Delete group (keeps artifacts)
  - [ ] Cascades position updates for remaining groups
- [ ] `useReorderGroups()` - Bulk reorder groups mutation
  - [ ] Transactional: all positions updated together
- [ ] `useGroupArtifacts(groupId)` - Get artifacts in group, ordered
- [ ] Hooks properly handle loading/error/success states

**Files to Create/Modify**:
- Create: `/skillmeat/web/hooks/use-groups.ts`
- Modify: `/skillmeat/web/hooks/index.ts`

**Estimated Effort**: 2 points

---

### 5. CollectionContext Provider (TASK-3.5)
**Description**: Context provider for shared collection state and operations

**Acceptance Criteria**:
- [ ] `CollectionContext` created with:
  - [ ] `selectedCollectionId` - Currently selected collection
  - [ ] `collections` - List of available collections
  - [ ] `currentCollection` - Full collection object
  - [ ] `isLoading` - Data loading state
  - [ ] `error` - Error message if any
- [ ] `CollectionProvider` component wraps app
  - [ ] Initializes with localStorage persisted selection
  - [ ] Provides methods: setSelectedCollection(), refreshCollections()
  - [ ] Memoized to prevent unnecessary re-renders
- [ ] `useCollectionContext()` hook to access provider
  - [ ] Throws error if used outside provider
  - [ ] Properly typed return value
- [ ] Integration with TanStack Query
  - [ ] Uses hooks from TASK-3.3
  - [ ] Properly invalidates on mutations
- [ ] Error boundaries integrated
- [ ] Performance: minimal re-renders with targeted updates

**Files to Create/Modify**:
- Create: `/skillmeat/web/context/collection-context.tsx`
- Create: `/skillmeat/web/hooks/use-collection-context.ts`
- Modify: `/skillmeat/web/components/providers.tsx` - Add CollectionProvider

**Estimated Effort**: 1.5 points

---

### 6. API Client Integration (TASK-3.6)
**Description**: Set up API client for communication with backend

**Acceptance Criteria**:
- [ ] API client configured in `/skillmeat/web/lib/api.ts`
  - [ ] Base URL from environment variables
  - [ ] Authentication header management
  - [ ] Error handling wrapper
  - [ ] Request/response logging (debug mode)
- [ ] Service layer created for API calls
  - [ ] `/skillmeat/web/lib/api/collections.ts` - Collection endpoints
  - [ ] `/skillmeat/web/lib/api/groups.ts` - Group endpoints
  - [ ] `/skillmeat/web/lib/api/deployments.ts` - Deployment endpoints
  - [ ] Proper error wrapping and type safety
- [ ] Mock fallback for development
  - [ ] Mock data generated from fixtures
  - [ ] Environment flag to enable/disable mocks
- [ ] TanStack Query client configured
  - [ ] Proper staleTime, cacheTime, retry settings
  - [ ] Request deduplication enabled

**Files to Create/Modify**:
- Create: `/skillmeat/web/lib/api/collections.ts`
- Create: `/skillmeat/web/lib/api/groups.ts`
- Create: `/skillmeat/web/lib/api/deployments.ts`
- Modify: `/skillmeat/web/lib/api.ts`
- Modify: `/skillmeat/web/components/providers.tsx` - QueryClientProvider setup

**Estimated Effort**: 1.5 points

---

## Task Breakdown Table

| Task ID | Task Name | Description | Story Points | Assigned To |
|---------|-----------|-------------|--------------|-------------|
| TASK-3.1 | Navigation Restructuring | Collapsible Collections parent section | 2 | ui-engineer-enhanced |
| TASK-3.2 | TypeScript Types | Collection, Group, Deployment interfaces | 1.5 | frontend-developer |
| TASK-3.3 | useCollections Hook | Custom hook with TanStack Query | 2 | frontend-developer |
| TASK-3.4 | useGroups Hook | Custom hook for group management | 2 | frontend-developer |
| TASK-3.5 | CollectionContext | Shared state provider | 1.5 | frontend-developer |
| TASK-3.6 | API Client Integration | API communication layer | 1.5 | frontend-developer |

**Total**: 10 story points

---

## Component Hierarchy

```
RootLayout
├── Providers (QueryClientProvider, CollectionProvider)
├── Header
└── Sidebar (Navigation) - TASK-3.1
    ├── NavSection (reusable)
    │   ├── Collections (parent, collapsible)
    │   │   ├── Manage
    │   │   ├── Projects
    │   │   └── MCP Servers
    │   ├── Dashboard
    │   └── Settings
```

---

## API Integration Flow

```
React Component
    ↓
useCollectionContext() - TASK-3.5
    ↓
useCollections() / useGroups() - TASK-3.3, TASK-3.4
    ↓
TanStack Query
    ↓
API Client - TASK-3.6
    ↓
REST API (Phase 2)
    ↓
Database (Phase 1)
```

---

## Type Safety Strategy

All TypeScript types should:
- ✓ Match backend Pydantic schemas exactly
- ✓ Have no `any` types (strict mode enabled)
- ✓ Use proper generics for reusable types
- ✓ Include JSDoc comments with examples
- ✓ Export from centralized index files

Example type definition:
```typescript
/**
 * Represents a user-defined collection of artifacts.
 * @example
 * const collection: Collection = {
 *   id: 'col-123',
 *   name: 'My Skills',
 *   description: 'Collection of reusable skills',
 *   group_count: 2,
 *   artifact_count: 15,
 *   created_at: '2025-12-12T10:00:00Z',
 *   updated_at: '2025-12-12T10:00:00Z'
 * }
 */
export interface Collection {
  id: string;
  name: string;
  description?: string;
  group_count: number;
  artifact_count: number;
  created_at: string;
  updated_at: string;
}
```

---

## Testing Strategy

### Unit Tests

**File**: `/skillmeat/web/__tests__/hooks/use-collections.test.ts`

```typescript
describe('useCollections', () => {
  it('fetches collections on mount', () => {
    // Mock TanStack Query, verify query called
  });

  it('handles loading state', () => {
    // Verify isLoading=true before data loads
  });

  it('handles errors', () => {
    // Verify error state populated on failure
  });

  it('refetches on manual call', () => {
    // Verify refetch() works
  });
});
```

### Component Tests

**File**: `/skillmeat/web/__tests__/components/navigation.test.tsx`

```typescript
describe('Navigation', () => {
  it('renders Collections section', () => {
    // Verify Collections parent visible
  });

  it('toggles Collections section collapse', () => {
    // Click toggle, verify collapsed state
  });

  it('highlights active tab', () => {
    // Verify active tab has correct styling
  });

  it('persists collapsed state', () => {
    // Verify localStorage used for persistence
  });

  it('supports keyboard navigation', () => {
    // Tab through items, verify focus management
  });
});
```

---

## Quality Gates

### Type Safety Checklist
- [ ] No `any` types in codebase
- [ ] All interfaces match backend schemas
- [ ] Proper generic usage
- [ ] Union types used for enums
- [ ] JSDoc comments on all public exports

### Hook Design Checklist
- [ ] Follow React Query naming conventions
- [ ] Proper dependency arrays
- [ ] No unnecessary re-renders
- [ ] Error handling comprehensive
- [ ] Loading states properly exposed
- [ ] Memoization used where appropriate

### Context Checklist
- [ ] Provider properly memoized
- [ ] Context value stable between renders
- [ ] Custom hook validates provider usage
- [ ] localStorage integration tested
- [ ] Error boundaries work correctly

### API Integration Checklist
- [ ] All endpoints accessible from client
- [ ] Authentication headers included
- [ ] Error responses handled consistently
- [ ] Request/response types match backend
- [ ] Mock fallback functional for development

---

## Performance Considerations

1. **Context Updates**: Use `useMemo` to prevent unnecessary re-renders
2. **Query Keys**: Properly structured for efficient caching
3. **Stale Time**: Set to 5 minutes to reduce API calls
4. **Pagination**: Implemented in hooks for large datasets
5. **Code Splitting**: Dynamic imports for heavy components (future)

---

## Accessibility Requirements

1. **Navigation**: Keyboard navigable (Tab, Arrow Keys, Enter)
2. **Collapsible Sections**: ARIA attributes (aria-expanded, aria-label)
3. **Loading States**: Screen reader announcements
4. **Error States**: Accessible error messages
5. **Color Contrast**: WCAG 2.1 AA minimum

---

## Files to Create

### Type Definition Files
1. `/skillmeat/web/types/collections.ts` (~50 lines)
2. `/skillmeat/web/types/groups.ts` (~30 lines)
3. `/skillmeat/web/types/deployments.ts` (~40 lines)

### Hook Files
1. `/skillmeat/web/hooks/use-collections.ts` (~100 lines)
2. `/skillmeat/web/hooks/use-groups.ts` (~100 lines)
3. `/skillmeat/web/hooks/use-collection-context.ts` (~20 lines)

### Context Files
1. `/skillmeat/web/context/collection-context.tsx` (~120 lines)

### API Service Files
1. `/skillmeat/web/lib/api/collections.ts` (~80 lines)
2. `/skillmeat/web/lib/api/groups.ts` (~80 lines)
3. `/skillmeat/web/lib/api/deployments.ts` (~60 lines)

### Modified Files
1. `/skillmeat/web/components/navigation.tsx` - Update sidebar
2. `/skillmeat/web/components/providers.tsx` - Add CollectionProvider
3. `/skillmeat/web/lib/api.ts` - Base client config
4. Various index files for exports

---

## Dependencies

### Runtime
- React 19+ (already in project)
- @tanstack/react-query (already in project)
- TypeScript (already in project)

### Development
- @testing-library/react (for component tests)
- @testing-library/hooks (for hook tests)

---

## Effort Breakdown

| Task | Hours | Notes |
|------|-------|-------|
| Navigation Restructuring | 6 | Component changes, state management |
| TypeScript Types | 4 | Interface definitions, enums |
| useCollections Hook | 5 | Implementation, error handling |
| useGroups Hook | 5 | Implementation with positioning |
| CollectionContext | 4 | Provider setup, integration |
| API Client Integration | 4 | Service layer, error handling |
| Testing | 6 | Unit, component, integration tests |
| **Total** | **34 hours** | ~4 days actual work, ~7 business days calendar |

---

## Orchestration Quick Reference

### Task Delegation Commands

Batch 1 (Parallel):
- **TASK-3.2** → `frontend-developer` (1.5h) - TypeScript types
- **TASK-3.1** → `ui-engineer-enhanced` (2h) - Navigation restructuring

Batch 2 (Parallel, after Batch 1):
- **TASK-3.3** → `frontend-developer` (2h) - useCollections hook
- **TASK-3.4** → `frontend-developer` (2h) - useGroups hook

Batch 3 (Sequential, after Batch 2):
- **TASK-3.5** → `frontend-developer` (1.5h) - CollectionContext
- **TASK-3.6** → `frontend-developer` (1.5h) - API client integration

---

## Success Criteria

Phase 3 is complete when:

1. **Navigation**: Collapsible Collections section working
2. **Types**: All TypeScript interfaces created and exported
3. **Hooks**: Custom hooks functional with proper state management
4. **Context**: Provider properly sharing state across app
5. **API**: Client layer working with all endpoints
6. **Testing**: 85%+ coverage of new code
7. **TypeScript**: Zero `any` types, strict mode enabled
8. **Performance**: No unnecessary re-renders with Profiler verification
9. **Accessibility**: Navigation keyboard-navigable with proper ARIA labels
10. **Code Review**: Approved by ui-engineer-enhanced and frontend-developer

---

## Next Phase

Phase 4 (Collection Features) depends on Phase 3 being complete. It will:
- Build Collection page with view modes (Grid, List, Grouped)
- Create Collection switcher component
- Implement collection management dialogs
- Enhance artifact cards with actions

**Phase 3 → Phase 4 Handoff**:
- Provide types for all collection-related data
- Share hook usage patterns and examples
- Document context provider API
- Provide test fixtures and mock data
