---
prd: collections-navigation-v1
phases: [3, 4]
title: "Frontend Foundation & Collection Features"
status: in_progress
last_updated: 2025-12-12
completion: 8
total_story_points: 25

tasks:
  # Phase 3: Frontend Foundation (10 story points)
  - id: "TASK-3.1"
    title: "Navigation Restructuring"
    status: completed
    story_points: 2
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    description: "Restructure navigation to support collections/groups/all artifacts views"
    files: ["web/components/navigation.tsx", "web/components/nav-section.tsx"]
    completed_at: "2025-12-12"

  - id: "TASK-3.2"
    title: "TypeScript Types"
    status: pending
    story_points: 1.5
    assigned_to: ["frontend-developer"]
    dependencies: []
    description: "Define Collection, Group, and navigation types"
    files: ["web/src/types/collections.ts", "web/src/types/groups.ts"]

  - id: "TASK-3.3"
    title: "useCollections Hook"
    status: pending
    story_points: 2
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-3.2"]
    description: "Create React hook for collection state management"
    files: ["web/src/hooks/useCollections.ts"]

  - id: "TASK-3.4"
    title: "useGroups Hook"
    status: pending
    story_points: 2
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-3.2"]
    description: "Create React hook for group state management"
    files: ["web/src/hooks/useGroups.ts"]

  - id: "TASK-3.5"
    title: "CollectionContext Provider"
    status: pending
    story_points: 1.5
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-3.3", "TASK-3.4"]
    description: "Create context provider for collection/group state"
    files: ["web/src/contexts/CollectionContext.tsx"]

  - id: "TASK-3.6"
    title: "API Client Integration"
    status: pending
    story_points: 1.5
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-3.2"]
    description: "Add collection/group endpoints to API client"
    files: ["web/src/lib/api-client.ts"]

  # Phase 4: Collection Features (15 story points)
  - id: "TASK-4.1"
    title: "Collection Page Redesign"
    status: pending
    story_points: 3
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.5", "TASK-3.6"]
    description: "Redesign collection page with groups sidebar and artifact grid"
    files: ["web/src/app/collections/[id]/page.tsx"]

  - id: "TASK-4.2"
    title: "Collection Switcher"
    status: pending
    story_points: 2
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.5"]
    description: "Create collection switcher component for navigation"
    files: ["web/src/components/collections/CollectionSwitcher.tsx"]

  - id: "TASK-4.3"
    title: "All Collections View"
    status: pending
    story_points: 2
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.1"]
    description: "Create all collections page with grid layout"
    files: ["web/src/app/collections/page.tsx"]

  - id: "TASK-4.4"
    title: "Create/Edit Collection Dialogs"
    status: pending
    story_points: 2
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.2"]
    description: "Create dialogs for creating and editing collections"
    files: ["web/src/components/collections/CollectionDialog.tsx"]

  - id: "TASK-4.5"
    title: "Move/Copy to Collections Dialog"
    status: pending
    story_points: 1.5
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-4.3"]
    description: "Create dialog for moving/copying artifacts to collections"
    files: ["web/src/components/artifacts/MoveToCollectionDialog.tsx"]

  - id: "TASK-4.6"
    title: "Artifact Card Enhancement"
    status: pending
    story_points: 2
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-4.1"]
    description: "Enhance artifact card with collection badges and actions"
    files: ["web/src/components/artifacts/ArtifactCard.tsx"]

  - id: "TASK-4.7"
    title: "Unified Modal Collections Tab"
    status: pending
    story_points: 2
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.5", "TASK-4.6"]
    description: "Add collections tab to unified artifact modal"
    files: ["web/src/components/artifacts/ArtifactModal.tsx"]

parallelization:
  batch_1: ["TASK-3.1", "TASK-3.2"]
  batch_2: ["TASK-3.3", "TASK-3.4", "TASK-3.6"]
  batch_3: ["TASK-3.5"]
  batch_4: ["TASK-4.1", "TASK-4.2"]
  batch_5: ["TASK-4.3", "TASK-4.4"]
  batch_6: ["TASK-4.5", "TASK-4.6"]
  batch_7: ["TASK-4.7"]

estimated_completion: "2025-12-14"
---

# Phase 3-4 Progress: Frontend Foundation & Collection Features

**Status**: Pending
**Last Updated**: 2025-12-12
**Completion**: 0% (0/13 tasks)
**Story Points**: 0/25 complete

## Overview

Combined frontend implementation phases for collections navigation enhancement:
- **Phase 3**: Foundation (types, hooks, context, API integration)
- **Phase 4**: Features (UI components, collection management, artifact interactions)

## Phase 3: Frontend Foundation (10 story points)

### Batch 1: Independent Foundation (3.5 points)
- [x] **TASK-3.1**: Navigation Restructuring (2pts) ✅ 2025-12-12
  - Restructure navigation to support collections/groups/all artifacts views
  - Files: `web/components/navigation.tsx`, `web/components/nav-section.tsx`
  - Assigned: ui-engineer-enhanced
  - Implemented: Collapsible Collections and Marketplace sections with localStorage persistence, keyboard navigation, and ARIA support

- [ ] **TASK-3.2**: TypeScript Types (1.5pts)
  - Define Collection, Group, and navigation types
  - Files: `web/src/types/collections.ts`, `web/src/types/groups.ts`
  - Assigned: frontend-developer

### Batch 2: Hooks & API Client (5.5 points)
- [ ] **TASK-3.3**: useCollections Hook (2pts)
  - Create React hook for collection state management
  - Files: `web/src/hooks/useCollections.ts`
  - Dependencies: TASK-3.2
  - Assigned: frontend-developer

- [ ] **TASK-3.4**: useGroups Hook (2pts)
  - Create React hook for group state management
  - Files: `web/src/hooks/useGroups.ts`
  - Dependencies: TASK-3.2
  - Assigned: frontend-developer

- [ ] **TASK-3.6**: API Client Integration (1.5pts)
  - Add collection/group endpoints to API client
  - Files: `web/src/lib/api-client.ts`
  - Dependencies: TASK-3.2
  - Assigned: frontend-developer

### Batch 3: Context Provider (1.5 points)
- [ ] **TASK-3.5**: CollectionContext Provider (1.5pts)
  - Create context provider for collection/group state
  - Files: `web/src/contexts/CollectionContext.tsx`
  - Dependencies: TASK-3.3, TASK-3.4
  - Assigned: frontend-developer

## Phase 4: Collection Features (15 story points)

### Batch 4: Core Collection UI (5 points)
- [ ] **TASK-4.1**: Collection Page Redesign (3pts)
  - Redesign collection page with groups sidebar and artifact grid
  - Files: `web/src/app/collections/[id]/page.tsx`
  - Dependencies: TASK-3.5, TASK-3.6
  - Assigned: ui-engineer-enhanced

- [ ] **TASK-4.2**: Collection Switcher (2pts)
  - Create collection switcher component for navigation
  - Files: `web/src/components/collections/CollectionSwitcher.tsx`
  - Dependencies: TASK-3.5
  - Assigned: ui-engineer-enhanced

### Batch 5: Collection Management (4 points)
- [ ] **TASK-4.3**: All Collections View (2pts)
  - Create all collections page with grid layout
  - Files: `web/src/app/collections/page.tsx`
  - Dependencies: TASK-4.1
  - Assigned: ui-engineer-enhanced

- [ ] **TASK-4.4**: Create/Edit Collection Dialogs (2pts)
  - Create dialogs for creating and editing collections
  - Files: `web/src/components/collections/CollectionDialog.tsx`
  - Dependencies: TASK-4.2
  - Assigned: ui-engineer-enhanced

### Batch 6: Artifact Interactions (3.5 points)
- [ ] **TASK-4.5**: Move/Copy to Collections Dialog (1.5pts)
  - Create dialog for moving/copying artifacts to collections
  - Files: `web/src/components/artifacts/MoveToCollectionDialog.tsx`
  - Dependencies: TASK-4.3
  - Assigned: frontend-developer

- [ ] **TASK-4.6**: Artifact Card Enhancement (2pts)
  - Enhance artifact card with collection badges and actions
  - Files: `web/src/components/artifacts/ArtifactCard.tsx`
  - Dependencies: TASK-4.1
  - Assigned: frontend-developer

### Batch 7: Final Integration (2 points)
- [ ] **TASK-4.7**: Unified Modal Collections Tab (2pts)
  - Add collections tab to unified artifact modal
  - Files: `web/src/components/artifacts/ArtifactModal.tsx`
  - Dependencies: TASK-4.5, TASK-4.6
  - Assigned: ui-engineer-enhanced

## Orchestration Quick Reference

### Batch 1 (Parallel - 3.5pts, ~3h)
Independent foundation tasks with no dependencies:
- TASK-3.1 → `ui-engineer-enhanced` (Navigation Restructuring, 2h)
- TASK-3.2 → `frontend-developer` (TypeScript Types, 1h)

```python
# Execute in parallel
Task("ui-engineer-enhanced", """TASK-3.1: Navigation Restructuring
Restructure navigation to support collections/groups/all artifacts views.
File: web/src/components/layout/navigation.tsx
Requirements:
- Add collection switcher to top navigation
- Add "All Collections" navigation item
- Update routing for collection/group views
- Maintain existing navigation patterns
""")

Task("frontend-developer", """TASK-3.2: TypeScript Types
Define Collection, Group, and navigation types.
Files: web/src/types/collections.ts, web/src/types/groups.ts
Requirements:
- Collection type (id, name, description, created_at, updated_at)
- Group type (id, collection_id, name, color, created_at)
- Navigation state types
- API response types
- Follow existing type patterns in web/src/types/
""")
```

### Batch 2 (Parallel - 5.5pts, ~4h)
After TASK-3.2 completes:
- TASK-3.3 → `frontend-developer` (useCollections Hook, 1.5h)
- TASK-3.4 → `frontend-developer` (useGroups Hook, 1.5h)
- TASK-3.6 → `frontend-developer` (API Client Integration, 1h)

```python
# Execute in parallel after Batch 1
Task("frontend-developer", """TASK-3.3: useCollections Hook
Create React hook for collection state management.
File: web/src/hooks/useCollections.ts
Requirements:
- Fetch collections from API
- CRUD operations (create, update, delete)
- Loading/error states
- React Query integration (match existing hooks)
- Cache invalidation strategy
Dependencies: TASK-3.2 types must exist
""")

Task("frontend-developer", """TASK-3.4: useGroups Hook
Create React hook for group state management.
File: web/src/hooks/useGroups.ts
Requirements:
- Fetch groups for collection
- CRUD operations (create, update, delete, reorder)
- Loading/error states
- React Query integration
- Optimistic updates for reordering
Dependencies: TASK-3.2 types must exist
""")

Task("frontend-developer", """TASK-3.6: API Client Integration
Add collection/group endpoints to API client.
File: web/src/lib/api-client.ts
Requirements:
- GET /collections, GET /collections/:id
- POST /collections, PUT /collections/:id, DELETE /collections/:id
- GET /collections/:id/groups, POST /groups, PUT /groups/:id, DELETE /groups/:id
- PUT /groups/:id/reorder
- Follow existing API client patterns
Dependencies: TASK-3.2 types must exist
""")
```

### Batch 3 (Sequential - 1.5pts, ~1h)
After TASK-3.3 and TASK-3.4 complete:
- TASK-3.5 → `frontend-developer` (CollectionContext Provider, 1h)

```python
# Execute after Batch 2
Task("frontend-developer", """TASK-3.5: CollectionContext Provider
Create context provider for collection/group state.
File: web/src/contexts/CollectionContext.tsx
Requirements:
- Wrap useCollections and useGroups hooks
- Provide global collection/group state
- Selected collection state
- Active group filter state
- Follow existing context patterns (e.g., web/src/contexts/)
Dependencies: TASK-3.3 and TASK-3.4 hooks must exist
""")
```

### Batch 4 (Parallel - 5pts, ~4h)
After Phase 3 (TASK-3.5, TASK-3.6) completes:
- TASK-4.1 → `ui-engineer-enhanced` (Collection Page Redesign, 2.5h)
- TASK-4.2 → `ui-engineer-enhanced` (Collection Switcher, 1.5h)

```python
# Execute in parallel after Batch 3
Task("ui-engineer-enhanced", """TASK-4.1: Collection Page Redesign
Redesign collection page with groups sidebar and artifact grid.
File: web/src/app/collections/[id]/page.tsx
Requirements:
- Left sidebar: Groups list with colors, reorderable, create/edit/delete
- Main content: Artifact grid filtered by selected group
- Empty states for no groups/artifacts
- Use CollectionContext for state
- Radix UI components (Sidebar, DropdownMenu)
- Responsive design (mobile: bottom sheet)
Dependencies: TASK-3.5 context and TASK-3.6 API client
""")

Task("ui-engineer-enhanced", """TASK-4.2: Collection Switcher
Create collection switcher component for navigation.
File: web/src/components/collections/CollectionSwitcher.tsx
Requirements:
- Dropdown showing all collections
- Selected collection indicator
- Quick create new collection
- Search/filter collections
- Radix UI Select/Command components
- Use CollectionContext for state
Dependencies: TASK-3.5 context
""")
```

### Batch 5 (Parallel - 4pts, ~3h)
After TASK-4.1 and TASK-4.2 complete:
- TASK-4.3 → `ui-engineer-enhanced` (All Collections View, 1.5h)
- TASK-4.4 → `ui-engineer-enhanced` (Create/Edit Collection Dialogs, 1.5h)

```python
# Execute in parallel after Batch 4
Task("ui-engineer-enhanced", """TASK-4.3: All Collections View
Create all collections page with grid layout.
File: web/src/app/collections/page.tsx
Requirements:
- Grid of collection cards (name, description, artifact count)
- Create new collection button
- Search/filter collections
- Click card → navigate to collection page
- Empty state with create prompt
- Use CollectionContext for state
Dependencies: TASK-4.1 patterns
""")

Task("ui-engineer-enhanced", """TASK-4.4: Create/Edit Collection Dialogs
Create dialogs for creating and editing collections.
File: web/src/components/collections/CollectionDialog.tsx
Requirements:
- Form: name (required), description (optional)
- Create mode: POST /collections
- Edit mode: PUT /collections/:id
- Validation (name required, max lengths)
- Radix UI Dialog component
- Form library (React Hook Form or similar)
Dependencies: TASK-4.2 integration point
""")
```

### Batch 6 (Parallel - 3.5pts, ~3h)
After TASK-4.3 completes:
- TASK-4.5 → `frontend-developer` (Move/Copy to Collections Dialog, 1h)
- TASK-4.6 → `frontend-developer` (Artifact Card Enhancement, 2h)

```python
# Execute in parallel after Batch 5
Task("frontend-developer", """TASK-4.5: Move/Copy to Collections Dialog
Create dialog for moving/copying artifacts to collections.
File: web/src/components/artifacts/MoveToCollectionDialog.tsx
Requirements:
- Select collection from dropdown
- Select group within collection (optional)
- Move vs Copy toggle
- Batch support (multiple artifacts)
- Success/error feedback
- Radix UI Dialog + Select
Dependencies: TASK-4.3 collection list pattern
""")

Task("frontend-developer", """TASK-4.6: Artifact Card Enhancement
Enhance artifact card with collection badges and actions.
File: web/src/components/artifacts/ArtifactCard.tsx
Requirements:
- Display collection badges (clickable → navigate)
- Show group colors as dots/badges
- Context menu: Add to Collection, Move to Collection
- Update existing card component (don't replace)
- Follow existing card patterns
Dependencies: TASK-4.1 design patterns
""")
```

### Batch 7 (Sequential - 2pts, ~2h)
After TASK-4.5 and TASK-4.6 complete:
- TASK-4.7 → `ui-engineer-enhanced` (Unified Modal Collections Tab, 2h)

```python
# Execute after Batch 6
Task("ui-engineer-enhanced", """TASK-4.7: Unified Modal Collections Tab
Add collections tab to unified artifact modal.
File: web/src/components/artifacts/ArtifactModal.tsx
Requirements:
- Add "Collections" tab to existing modal
- Show all collections containing this artifact
- Show groups within each collection
- Quick add/remove from collections
- Quick change group
- Use Radix UI Tabs (match existing tabs)
Dependencies: TASK-4.5 dialog and TASK-4.6 card patterns
""")
```

## Execution Strategy

### Phase 3 (Foundation)
1. **Batch 1**: Parallel foundation (navigation + types)
2. **Batch 2**: Parallel hooks after types ready
3. **Batch 3**: Context provider after hooks ready

### Phase 4 (Features)
4. **Batch 4**: Parallel core UI after foundation
5. **Batch 5**: Parallel management UI after core
6. **Batch 6**: Parallel artifact interactions after management
7. **Batch 7**: Final integration after interactions

### Total Timeline
- **Estimated Duration**: 20 hours development time
- **Wall Clock**: 2-3 days with parallelization
- **Critical Path**: Batch 1 → Batch 2 → Batch 3 → Batch 4 → Batch 5 → Batch 6 → Batch 7

## Completion Criteria

### Phase 3 Complete When:
- [ ] All types defined and imported successfully
- [ ] Hooks fetching data from API endpoints
- [ ] Context provider managing global state
- [ ] Navigation restructured with collection switcher

### Phase 4 Complete When:
- [ ] Collection page redesigned with groups sidebar
- [ ] All collections view functional
- [ ] Create/edit collection dialogs working
- [ ] Artifacts can be moved/copied to collections
- [ ] Artifact cards show collection badges
- [ ] Unified modal has collections tab

### Testing Requirements:
- [ ] All components render without errors
- [ ] API integration working (verify with dev server)
- [ ] State management tested (create/edit/delete)
- [ ] Responsive design verified (mobile/desktop)
- [ ] Navigation flows working end-to-end

## Context for AI Agents

**Architecture**: Next.js 15 App Router, React 18, TypeScript, Radix UI, React Query
**Existing Patterns**: Check `web/src/hooks/`, `web/src/contexts/`, `web/src/components/` for patterns
**API Base**: `http://localhost:8000/api` (FastAPI backend)
**State Management**: React Query for server state, Context for UI state
**Styling**: Tailwind CSS + shadcn/ui components

**Key Files to Reference**:
- `web/src/lib/api-client.ts` - API client pattern
- `web/src/hooks/useArtifacts.ts` - Hook pattern example
- `web/src/components/artifacts/ArtifactCard.tsx` - Component pattern
- `web/src/app/artifacts/page.tsx` - Page pattern

**Backend API Ready**: Phase 1-2 complete (collections/groups endpoints working)
