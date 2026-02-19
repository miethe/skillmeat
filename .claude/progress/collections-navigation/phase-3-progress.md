---
type: progress
prd: collections-navigation
phase: 3
title: Frontend Foundation - Types, Hooks, Context
status: pending
overall_progress: 0
total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners:
- frontend-developer
contributors:
- ui-engineer-enhanced
tasks:
- id: TASK-3.1
  name: Navigation Restructuring
  description: Add collapsible Collections parent section to sidebar navigation
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2h
  priority: high
- id: TASK-3.2
  name: TypeScript Types for Collections & Groups
  description: Define TypeScript interfaces matching API schemas
  status: pending
  assigned_to:
  - frontend-developer
  dependencies: []
  estimated_effort: 1.5h
  priority: high
- id: TASK-3.3
  name: useCollections Hook
  description: Custom hook with TanStack Query for collections CRUD
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - TASK-3.2
  estimated_effort: 2h
  priority: high
- id: TASK-3.4
  name: useGroups Hook
  description: Custom hook for group management operations
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - TASK-3.2
  estimated_effort: 2h
  priority: high
- id: TASK-3.5
  name: CollectionContext Provider
  description: Shared state provider for current collection selection
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - TASK-3.3
  - TASK-3.4
  estimated_effort: 1.5h
  priority: high
- id: TASK-3.6
  name: API Client Integration
  description: API communication layer for collections and groups
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - TASK-3.2
  estimated_effort: 1.5h
  priority: high
parallelization:
  batch_1:
  - TASK-3.1
  - TASK-3.2
  batch_2:
  - TASK-3.3
  - TASK-3.4
  - TASK-3.6
  batch_3:
  - TASK-3.5
  critical_path:
  - TASK-3.2
  - TASK-3.3
  - TASK-3.5
  estimated_total_time: 1w
blockers: []
success_criteria:
- id: SC-1
  description: Navigation sidebar includes Collections section
  status: pending
- id: SC-2
  description: TypeScript types match backend API schemas exactly
  status: pending
- id: SC-3
  description: useCollections hook provides all CRUD operations
  status: pending
- id: SC-4
  description: useGroups hook supports position/reordering
  status: pending
- id: SC-5
  description: CollectionContext provides shared state across components
  status: pending
- id: SC-6
  description: API client handles errors gracefully
  status: pending
- id: SC-7
  description: TanStack Query cache invalidation works correctly
  status: pending
files_modified: []
schema_version: 2
doc_type: progress
feature_slug: collections-navigation
---

# collections-navigation - Phase 3: Frontend Foundation

**Phase**: 3 of 6
**Status**: Pending (0% complete)
**Owner**: frontend-developer
**Contributors**: ui-engineer-enhanced
**Dependencies**: Phase 2 (Backend API)

---

## Phase Objective

Create TypeScript types, React hooks, and shared context for Collections and Groups management. This phase establishes the frontend foundation that subsequent UI components will build upon.

---

## Orchestration Quick Reference

**Batch 1** (Parallel - Foundation):
- TASK-3.1 → `ui-engineer-enhanced` (2h) - Navigation restructuring
- TASK-3.2 → `frontend-developer` (1.5h) - TypeScript types

**Batch 2** (Parallel - Hooks and API, after Batch 1):
- TASK-3.3 → `frontend-developer` (2h) - useCollections hook
- TASK-3.4 → `frontend-developer` (2h) - useGroups hook
- TASK-3.6 → `frontend-developer` (1.5h) - API client integration

**Batch 3** (Sequential - Context, after Batch 2):
- TASK-3.5 → `frontend-developer` (1.5h) - CollectionContext provider

### Task Delegation Commands

```
# Batch 1 (Parallel)
Task("ui-engineer-enhanced", "TASK-3.1: Add collapsible Collections parent section to sidebar navigation with child links for individual collections, All Collections view, and Manage Groups. Update navigation structure to show Collections at same level as Dashboard/Discover. Include expand/collapse icon and maintain state. Files: /skillmeat/web/components/layout/Sidebar.tsx or Navigation.tsx")

Task("frontend-developer", "TASK-3.2: Create TypeScript interfaces for Collection (id, name, description, group_count, artifact_count, created_at, updated_at), Group (id, collection_id, name, description, position, artifact_count, created_at, updated_at), CollectionArtifact, GroupArtifact, Deployment, DeploymentSummary. Match backend Pydantic schemas exactly. File: /skillmeat/web/lib/types/collections.ts")

# Batch 2 (Parallel, after Batch 1)
Task("frontend-developer", "TASK-3.3: Create useCollections hook using TanStack Query with: useCollections() (list all), useCollection(id) (get one), useCreateCollection(), useUpdateCollection(), useDeleteCollection(), useAddArtifactsToCollection(), useRemoveArtifactFromCollection(), useMoveArtifacts(), useCopyArtifacts(). Include optimistic updates and cache invalidation. File: /skillmeat/web/hooks/useCollections.ts")

Task("frontend-developer", "TASK-3.4: Create useGroups hook using TanStack Query with: useGroups(collectionId) (list), useGroup(id) (get one), useCreateGroup(), useUpdateGroup(), useDeleteGroup(), useReorderGroups(), useAddArtifactsToGroup(), useRemoveArtifactFromGroup(), useUpdateArtifactPosition(), useReorderArtifacts(). Include optimistic updates. File: /skillmeat/web/hooks/useGroups.ts")

Task("frontend-developer", "TASK-3.6: Create API client functions for all collections and groups endpoints using existing API client pattern. Include error handling, request/response typing, and proper HTTP methods. Files: /skillmeat/web/lib/api/collections.ts, /skillmeat/web/lib/api/groups.ts")

# Batch 3 (Sequential, after Batch 2)
Task("frontend-developer", "TASK-3.5: Create CollectionContext with CollectionProvider component and useCollectionContext hook. Provide: currentCollection (Collection | null), setCurrentCollection(), currentView ('all' | 'collection' | 'group'), groups (Group[]), isLoading. Integrate with useCollections and useGroups hooks. Files: /skillmeat/web/contexts/CollectionContext.tsx, wrap app layout")
```

---

## Task Details

### TASK-3.1: Navigation Restructuring
- **Status**: pending
- **Assigned**: ui-engineer-enhanced
- **Estimated Effort**: 2h
- **Priority**: high

**Description**: Add collapsible Collections parent section to sidebar navigation

**Acceptance Criteria**:
- [ ] Collections parent section added to sidebar at same level as Dashboard/Discover
- [ ] Expand/collapse icon (ChevronRight/ChevronDown) toggles visibility
- [ ] Child links: All Collections, individual collections (dynamic), Manage Groups
- [ ] Active collection highlighted in navigation
- [ ] Collapse state persisted in localStorage
- [ ] Smooth transition animation on expand/collapse
- [ ] Responsive design maintained

**Files**: `/skillmeat/web/components/layout/Sidebar.tsx` or `/skillmeat/web/components/layout/Navigation.tsx`

---

### TASK-3.2: TypeScript Types for Collections & Groups
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 1.5h
- **Priority**: high

**Description**: Define TypeScript interfaces matching API schemas

**Acceptance Criteria**:
- [ ] `Collection` interface with all fields from CollectionResponse
- [ ] `Group` interface with all fields from GroupResponse
- [ ] `CollectionArtifact` association type
- [ ] `GroupArtifact` association type with position
- [ ] `Deployment` interface matching backend
- [ ] `DeploymentSummary` interface for aggregations
- [ ] `CollectionCreateInput`, `CollectionUpdateInput` request types
- [ ] `GroupCreateInput`, `GroupUpdateInput` request types
- [ ] All types exported from single file

**Files**: `/skillmeat/web/lib/types/collections.ts`

---

### TASK-3.3: useCollections Hook
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 2h
- **Priority**: high
- **Dependencies**: TASK-3.2

**Description**: Custom hook with TanStack Query for collections CRUD

**Acceptance Criteria**:
- [ ] `useCollections()` - List all collections with optional search/pagination
- [ ] `useCollection(id)` - Get single collection with groups
- [ ] `useCreateCollection()` - Mutation with optimistic update
- [ ] `useUpdateCollection()` - Mutation with optimistic update
- [ ] `useDeleteCollection()` - Mutation with cache invalidation
- [ ] `useAddArtifactsToCollection()` - Add artifacts mutation
- [ ] `useRemoveArtifactFromCollection()` - Remove artifact mutation
- [ ] `useMoveArtifacts()` - Move artifacts between collections
- [ ] `useCopyArtifacts()` - Copy artifacts to another collection
- [ ] Proper error handling and loading states
- [ ] Cache invalidation on mutations

**Files**: `/skillmeat/web/hooks/useCollections.ts`

---

### TASK-3.4: useGroups Hook
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 2h
- **Priority**: high
- **Dependencies**: TASK-3.2

**Description**: Custom hook for group management operations

**Acceptance Criteria**:
- [ ] `useGroups(collectionId)` - List groups by collection (ordered by position)
- [ ] `useGroup(id)` - Get single group with artifacts
- [ ] `useCreateGroup()` - Mutation with optimistic update
- [ ] `useUpdateGroup()` - Mutation with optimistic update
- [ ] `useDeleteGroup()` - Mutation with cache invalidation
- [ ] `useReorderGroups()` - Bulk reorder mutation
- [ ] `useAddArtifactsToGroup()` - Add artifacts with position
- [ ] `useRemoveArtifactFromGroup()` - Remove artifact (auto-reorder)
- [ ] `useUpdateArtifactPosition()` - Update single artifact position
- [ ] `useReorderArtifacts()` - Bulk reorder artifacts in group
- [ ] Proper error handling and loading states

**Files**: `/skillmeat/web/hooks/useGroups.ts`

---

### TASK-3.5: CollectionContext Provider
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 1.5h
- **Priority**: high
- **Dependencies**: TASK-3.3, TASK-3.4

**Description**: Shared state provider for current collection selection

**Acceptance Criteria**:
- [ ] `CollectionProvider` component wraps app layout
- [ ] `useCollectionContext()` hook exposes context
- [ ] State: currentCollection (Collection | null)
- [ ] State: currentView ('all' | 'collection' | 'group')
- [ ] State: groups (Group[] for current collection)
- [ ] State: isLoading (boolean)
- [ ] Method: setCurrentCollection(id)
- [ ] Method: setCurrentView(view)
- [ ] Integrates with useCollections and useGroups hooks
- [ ] Persists current collection in localStorage

**Files**: `/skillmeat/web/contexts/CollectionContext.tsx`

---

### TASK-3.6: API Client Integration
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 1.5h
- **Priority**: high
- **Dependencies**: TASK-3.2

**Description**: API communication layer for collections and groups

**Acceptance Criteria**:
- [ ] Collections API client with all CRUD functions
- [ ] Groups API client with all CRUD functions
- [ ] Deployment API client for summary endpoint
- [ ] Proper typing for requests and responses
- [ ] Error handling with descriptive messages
- [ ] Request/response interceptors for auth
- [ ] Follows existing API client patterns
- [ ] Exports all functions for use in hooks

**Files**: `/skillmeat/web/lib/api/collections.ts`, `/skillmeat/web/lib/api/groups.ts`

---

## Progress Summary

**Completed**: 0/6 tasks (0%)
**In Progress**: 0/6 tasks
**Blocked**: 0/6 tasks
**Pending**: 6/6 tasks

---

## Key Implementation Patterns

### TanStack Query Integration
- Use `useQuery` for GET operations (list, get single)
- Use `useMutation` for POST/PUT/DELETE operations
- Implement optimistic updates for better UX
- Invalidate related queries on mutations

### Type Safety
- All API responses properly typed
- No `any` types except where truly necessary
- Request payloads validated with TypeScript

### Error Handling
- Display user-friendly error messages
- Log errors to console for debugging
- Retry failed requests with exponential backoff

---

## Testing Requirements

### Unit Tests
**Files**: `/skillmeat/web/hooks/__tests__/useCollections.test.ts`, `/skillmeat/web/hooks/__tests__/useGroups.test.ts`

- Hook returns correct data structure
- Mutations trigger cache invalidation
- Optimistic updates work correctly
- Error states handled properly

### Integration Tests
**File**: `/skillmeat/web/contexts/__tests__/CollectionContext.test.tsx`

- Context provides correct values
- State updates propagate to consumers
- localStorage persistence works

---

## Phase Completion Criteria

Phase 3 is complete when:

1. **Navigation**: Collections section visible in sidebar
2. **Types**: All TypeScript interfaces created and exported
3. **Hooks**: useCollections and useGroups provide all operations
4. **Context**: CollectionContext shares state across components
5. **API Client**: All API functions implemented with proper typing
6. **Error Handling**: Graceful error handling throughout
7. **Testing**: Unit tests for hooks and context
8. **Code Review**: Approved by frontend lead
