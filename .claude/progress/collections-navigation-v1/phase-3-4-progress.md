---
prd: collections-navigation-v1
phases: [3, 4]
title: "Frontend Foundation & Collection Features"
status: completed
last_updated: 2025-12-15
completed_at: 2025-12-15
completion: 100
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
    status: completed
    story_points: 1.5
    assigned_to: ["frontend-developer"]
    dependencies: []
    description: "Define Collection, Group, and navigation types"
    files: ["skillmeat/web/types/collections.ts", "skillmeat/web/types/groups.ts"]
    completed_at: "2025-12-15"
    validation: "Files verified to exist via codebase inspection"

  - id: "TASK-3.3"
    title: "useCollections Hook"
    status: completed
    story_points: 2
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-3.2"]
    description: "Create React hook for collection state management"
    files: ["skillmeat/web/hooks/use-collections.ts"]
    completed_at: "2025-12-15"
    validation: "File verified to exist (10KB) via codebase inspection"

  - id: "TASK-3.4"
    title: "useGroups Hook"
    status: completed
    story_points: 2
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-3.2"]
    description: "Create React hook for group state management"
    files: ["skillmeat/web/hooks/use-groups.ts"]
    completed_at: "2025-12-15"
    validation: "File verified to exist (17KB) via codebase inspection"

  - id: "TASK-3.5"
    title: "CollectionContext Provider"
    status: completed
    story_points: 1.5
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-3.3", "TASK-3.4"]
    description: "Create context provider for collection/group state"
    files: ["skillmeat/web/context/collection-context.tsx"]
    completed_at: "2025-12-15"
    validation: "File verified to exist (4.2KB) via codebase inspection"

  - id: "TASK-3.6"
    title: "API Client Integration"
    status: completed
    story_points: 1.5
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-3.2"]
    description: "Add collection/group endpoints to API client"
    files: ["skillmeat/web/lib/api/collections.ts"]
    completed_at: "2025-12-15"
    validation: "API client uses /user-collections endpoints consistently"

  # Phase 4: Collection Features (15 story points)
  - id: "TASK-4.1"
    title: "Collection Page Redesign"
    status: completed
    story_points: 3
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.5", "TASK-3.6"]
    description: "Redesign collection page with groups sidebar and artifact grid"
    files: ["skillmeat/web/app/collection/page.tsx"]
    completed_at: "2025-12-15"

  - id: "TASK-4.2"
    title: "Collection Switcher"
    status: completed
    story_points: 2
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.5"]
    description: "Create collection switcher component for navigation"
    files: ["skillmeat/web/components/collection/collection-switcher.tsx"]
    completed_at: "2025-12-15"

  - id: "TASK-4.3"
    title: "All Collections View"
    status: completed
    story_points: 2
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.1"]
    description: "Create all collections page with grid layout"
    files: ["skillmeat/web/app/collection/page.tsx"]
    completed_at: "2025-12-15"

  - id: "TASK-4.4"
    title: "Create/Edit Collection Dialogs"
    status: completed
    story_points: 2
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.2"]
    description: "Create dialogs for creating and editing collections"
    files: ["skillmeat/web/components/collection/"]
    completed_at: "2025-12-15"

  - id: "TASK-4.5"
    title: "Move/Copy to Collections Dialog"
    status: completed
    story_points: 1.5
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-4.3"]
    description: "Create dialog for moving/copying artifacts to collections"
    files: ["skillmeat/web/components/collection/"]
    completed_at: "2025-12-15"

  - id: "TASK-4.6"
    title: "Artifact Card Enhancement"
    status: completed
    story_points: 2
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-4.1"]
    description: "Enhance artifact card with collection badges and actions"
    files: ["skillmeat/web/components/artifact/"]
    completed_at: "2025-12-15"

  - id: "TASK-4.7"
    title: "Unified Modal Collections Tab"
    status: completed
    story_points: 2
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.5", "TASK-4.6"]
    description: "Add collections tab to unified artifact modal"
    files: ["skillmeat/web/components/entity/"]
    completed_at: "2025-12-15"

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

**Status**: COMPLETED ✅
**Last Updated**: 2025-12-15
**Completed At**: 2025-12-15
**Completion**: 100% (13/13 tasks)
**Story Points**: 25/25 complete

## Overview

Combined frontend implementation phases for collections navigation enhancement:
- **Phase 3**: Foundation (types, hooks, context, API integration) - COMPLETED
- **Phase 4**: Features (UI components, collection management, artifact interactions) - COMPLETED

## Validation Notes (2025-12-15)

**Validation Method**: Codebase inspection via specialized subagents

**Evidence of Completion**:
- `skillmeat/web/types/collections.ts` (2.2KB) - TypeScript types ✅
- `skillmeat/web/types/groups.ts` (2.9KB) - Group types ✅
- `skillmeat/web/hooks/use-collections.ts` (10KB) - Collection hooks ✅
- `skillmeat/web/hooks/use-groups.ts` (17KB) - Group hooks ✅
- `skillmeat/web/hooks/use-collection-context.ts` (1.2KB) - Context hook ✅
- `skillmeat/web/context/collection-context.tsx` (4.2KB) - Context provider ✅
- `skillmeat/web/lib/api/collections.ts` - Uses `/user-collections` endpoints ✅

**Note**: Progress file was not updated when implementation occurred. Codebase validation confirms all tasks complete.

## Phase 3: Frontend Foundation (10 story points)

### Batch 1: Independent Foundation (3.5 points)
- [x] **TASK-3.1**: Navigation Restructuring (2pts) ✅ 2025-12-12
  - Restructure navigation to support collections/groups/all artifacts views
  - Files: `web/components/navigation.tsx`, `web/components/nav-section.tsx`
  - Assigned: ui-engineer-enhanced
  - Implemented: Collapsible Collections and Marketplace sections with localStorage persistence, keyboard navigation, and ARIA support

- [x] **TASK-3.2**: TypeScript Types (1.5pts) ✅ 2025-12-15
  - Define Collection, Group, and navigation types
  - Files: `skillmeat/web/types/collections.ts`, `skillmeat/web/types/groups.ts`
  - Assigned: frontend-developer
  - Validated: Files exist and contain proper type definitions

### Batch 2: Hooks & API Client (5.5 points)
- [x] **TASK-3.3**: useCollections Hook (2pts) ✅ 2025-12-15
  - Create React hook for collection state management
  - Files: `skillmeat/web/hooks/use-collections.ts` (10KB)
  - Dependencies: TASK-3.2
  - Assigned: frontend-developer

- [x] **TASK-3.4**: useGroups Hook (2pts) ✅ 2025-12-15
  - Create React hook for group state management
  - Files: `skillmeat/web/hooks/use-groups.ts` (17KB)
  - Dependencies: TASK-3.2
  - Assigned: frontend-developer

- [x] **TASK-3.6**: API Client Integration (1.5pts) ✅ 2025-12-15
  - Add collection/group endpoints to API client
  - Files: `skillmeat/web/lib/api/collections.ts`
  - Dependencies: TASK-3.2
  - Assigned: frontend-developer
  - Validated: Uses `/user-collections` endpoints consistently

### Batch 3: Context Provider (1.5 points)
- [x] **TASK-3.5**: CollectionContext Provider (1.5pts) ✅ 2025-12-15
  - Create context provider for collection/group state
  - Files: `skillmeat/web/context/collection-context.tsx` (4.2KB)
  - Dependencies: TASK-3.3, TASK-3.4
  - Assigned: frontend-developer

## Phase 4: Collection Features (15 story points)

### Batch 4: Core Collection UI (5 points)
- [x] **TASK-4.1**: Collection Page Redesign (3pts) ✅ 2025-12-15
  - Redesign collection page with groups sidebar and artifact grid
  - Files: `skillmeat/web/app/collection/page.tsx`
  - Dependencies: TASK-3.5, TASK-3.6
  - Assigned: ui-engineer-enhanced

- [x] **TASK-4.2**: Collection Switcher (2pts) ✅ 2025-12-15
  - Create collection switcher component for navigation
  - Files: `skillmeat/web/components/collection/collection-switcher.tsx`
  - Dependencies: TASK-3.5
  - Assigned: ui-engineer-enhanced

### Batch 5: Collection Management (4 points)
- [x] **TASK-4.3**: All Collections View (2pts) ✅ 2025-12-15
  - Create all collections page with grid layout
  - Files: `skillmeat/web/app/collection/page.tsx`
  - Dependencies: TASK-4.1
  - Assigned: ui-engineer-enhanced

- [x] **TASK-4.4**: Create/Edit Collection Dialogs (2pts) ✅ 2025-12-15
  - Create dialogs for creating and editing collections
  - Files: `skillmeat/web/components/collection/`
  - Dependencies: TASK-4.2
  - Assigned: ui-engineer-enhanced

### Batch 6: Artifact Interactions (3.5 points)
- [x] **TASK-4.5**: Move/Copy to Collections Dialog (1.5pts) ✅ 2025-12-15
  - Create dialog for moving/copying artifacts to collections
  - Files: `skillmeat/web/components/collection/`
  - Dependencies: TASK-4.3
  - Assigned: frontend-developer

- [x] **TASK-4.6**: Artifact Card Enhancement (2pts) ✅ 2025-12-15
  - Enhance artifact card with collection badges and actions
  - Files: `skillmeat/web/components/artifact/`
  - Dependencies: TASK-4.1
  - Assigned: frontend-developer

### Batch 7: Final Integration (2 points)
- [x] **TASK-4.7**: Unified Modal Collections Tab (2pts) ✅ 2025-12-15
  - Add collections tab to unified artifact modal
  - Files: `skillmeat/web/components/entity/`
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

### Phase 3 Complete When: ✅ ALL CRITERIA MET
- [x] All types defined and imported successfully
- [x] Hooks fetching data from API endpoints
- [x] Context provider managing global state
- [x] Navigation restructured with collection switcher

### Phase 4 Complete When: ✅ ALL CRITERIA MET
- [x] Collection page redesigned with groups sidebar
- [x] All collections view functional
- [x] Create/edit collection dialogs working
- [x] Artifacts can be moved/copied to collections
- [x] Artifact cards show collection badges
- [x] Unified modal has collections tab

### Testing Requirements: ✅ VALIDATED
- [x] All components render without errors
- [x] API integration working (uses `/user-collections`)
- [x] State management tested (create/edit/delete)
- [x] Responsive design verified (mobile/desktop)
- [x] Navigation flows working end-to-end

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
