---
# === REQUEST LOG VIEWER - PHASE 2: FRONTEND PAGES & COMPONENTS ===
# Frontend implementation tracking for request log viewer feature
# REQUIRED FIELDS: assigned_to, dependencies for EVERY task

# Metadata: Identification and Classification
type: progress
prd: "request-log-viewer-v1"
phase: 2
title: "Frontend Pages & Components"
status: "pending"
started: null
completed: null

# Overall Progress: Status and Estimates
overall_progress: 0
completion_estimate: "5.5 days"

# Task Counts: Machine-readable task state
total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

# Ownership: Primary and secondary agents
owners: ["ui-engineer-enhanced"]
contributors: []

# === ORCHESTRATION QUICK REFERENCE ===
# All tasks with assignments and dependencies
tasks:
  - id: "TASK-2.1"
    description: "Create page structure - Setup route, layout, providers"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "0.5 days"
    priority: "high"

  - id: "TASK-2.2"
    description: "Build document list table component - TanStack Table with sorting, pagination"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.1"]
    estimated_effort: "1 day"
    priority: "high"

  - id: "TASK-2.3"
    description: "Build multi-select filter UI - Type, domain, subdomain, status filters"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.1"]
    estimated_effort: "1 day"
    priority: "high"

  - id: "TASK-2.4"
    description: "Build keyword search component - Real-time search with debouncing"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.1"]
    estimated_effort: "0.5 days"
    priority: "medium"

  - id: "TASK-2.5"
    description: "Build document detail modal - Full document display with metadata"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.1"]
    estimated_effort: "1 day"
    priority: "high"

  - id: "TASK-2.6"
    description: "Create TanStack Query hooks - useRequestLogs, useRequestLog, useFilterOptions"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "0.5 days"
    priority: "high"

  - id: "TASK-2.7"
    description: "Write frontend unit tests - Component and integration tests"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.2", "TASK-2.3", "TASK-2.4", "TASK-2.5", "TASK-2.6"]
    estimated_effort: "1 day"
    priority: "high"

# Parallelization Strategy (computed from dependencies)
parallelization:
  batch_1: ["TASK-2.1"]
  batch_2: ["TASK-2.2", "TASK-2.3", "TASK-2.4", "TASK-2.5", "TASK-2.6"]
  batch_3: ["TASK-2.7"]
  critical_path: ["TASK-2.1", "TASK-2.2", "TASK-2.7"]
  estimated_total_time: "5.5 days"

# Critical Blockers: None currently
blockers: []

# Success Criteria: Acceptance conditions for phase completion
success_criteria:
  - id: "SC-1"
    description: "All components render without errors"
    status: "pending"
    result: null
  - id: "SC-2"
    description: "Filters update table reactively"
    status: "pending"
    result: null
  - id: "SC-3"
    description: "Modal displays all item fields correctly"
    status: "pending"
    result: null
  - id: "SC-4"
    description: "Tests achieve >80% coverage"
    status: "pending"
    result: null

# Files Modified: What's being changed in this phase
files_modified:
  - "skillmeat/web/app/requests/page.tsx"
  - "skillmeat/web/components/requests/request-log-table.tsx"
  - "skillmeat/web/components/requests/request-log-filters.tsx"
  - "skillmeat/web/components/requests/request-log-search.tsx"
  - "skillmeat/web/components/requests/request-log-modal.tsx"
  - "skillmeat/web/hooks/use-request-logs.ts"
  - "skillmeat/web/hooks/use-request-log.ts"
  - "skillmeat/web/hooks/use-filter-options.ts"
  - "skillmeat/web/__tests__/components/requests/request-log-table.test.tsx"
  - "skillmeat/web/__tests__/components/requests/request-log-filters.test.tsx"
  - "skillmeat/web/__tests__/components/requests/request-log-search.test.tsx"
  - "skillmeat/web/__tests__/components/requests/request-log-modal.test.tsx"
---

# request-log-viewer-v1 - Phase 2: Frontend Pages & Components

**Phase**: 2 of 3
**Status**: Pending (0%)
**Duration**: Not Started
**Owner**: ui-engineer-enhanced
**Contributors**: None

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Sequential - Foundation):
- TASK-2.1 → `ui-engineer-enhanced` (0.5 days) - Page structure and routing

**Batch 2** (Parallel - After Batch 1):
- TASK-2.2 → `ui-engineer-enhanced` (1 day) - Document list table [needs TASK-2.1]
- TASK-2.3 → `ui-engineer-enhanced` (1 day) - Multi-select filters [needs TASK-2.1]
- TASK-2.4 → `ui-engineer-enhanced` (0.5 days) - Keyword search [needs TASK-2.1]
- TASK-2.5 → `ui-engineer-enhanced` (1 day) - Detail modal [needs TASK-2.1]
- TASK-2.6 → `ui-engineer-enhanced` (0.5 days) - TanStack Query hooks (independent)

**Batch 3** (Sequential - After Batch 2):
- TASK-2.7 → `ui-engineer-enhanced` (1 day) - Frontend tests [needs TASK-2.2-2.6]

**Critical Path**: TASK-2.1 → TASK-2.2 → TASK-2.7 (2.5 days)

### Task Delegation Commands

```python
# Batch 1 (Foundation)
Task("ui-engineer-enhanced", """TASK-2.1: Create Page Structure

Create new page at skillmeat/web/app/requests/page.tsx:

1. Setup Next.js 15 App Router page (remember params must be awaited)
2. Add TanStack Query provider wrapper
3. Create layout with:
   - Page header with title "Request Logs"
   - Filter sidebar (left)
   - Main content area (table + search)
4. Import required components (will be built in batch 2)

Structure:
- Server component wrapper
- Client component for interactivity
- Proper TypeScript types
- Responsive layout using Tailwind

Reference:
- skillmeat/web/CLAUDE.md - Next.js patterns
- .claude/rules/web/pages.md - Page conventions
- .claude/context/key-context/nextjs-patterns.md - App Router examples
""", model="opus")

# Batch 2 (Parallel - After page structure exists)
Task("ui-engineer-enhanced", """TASK-2.2: Build Document List Table Component

Create skillmeat/web/components/requests/request-log-table.tsx:

1. Use TanStack Table with shadcn Table components
2. Columns:
   - ID (sortable)
   - Type (badge)
   - Domain (badge)
   - Subdomain (badge)
   - Title (truncated with tooltip)
   - Status (badge with colors)
   - Created (formatted date, sortable)
   - Actions (view button)
3. Features:
   - Column sorting
   - Pagination (10/25/50/100 per page)
   - Row click to open modal
   - Loading/empty states
4. Integration with useRequestLogs hook

Reference:
- .claude/rules/web/components.md - Component conventions
- .claude/context/key-context/component-patterns.md - shadcn patterns
- skillmeat/web/components/ui/table.tsx - shadcn Table component
""", model="opus")

Task("ui-engineer-enhanced", """TASK-2.3: Build Multi-Select Filter UI

Create skillmeat/web/components/requests/request-log-filters.tsx:

1. Use shadcn Checkbox and Label components
2. Filter groups:
   - Type (enhancement, bug, idea, task, question)
   - Domain (multi-select)
   - Subdomain (multi-select, filtered by selected domains)
   - Status (multi-select)
3. Features:
   - "Select All" / "Clear All" per group
   - Active filter count badges
   - Collapsible sections
   - Reset all filters button
4. Integration with URL state (searchParams)
5. Fetch available options from useFilterOptions hook

Reference:
- .claude/rules/web/components.md - Component conventions
- .claude/context/key-context/component-patterns.md - Form patterns
- skillmeat/web/components/ui/checkbox.tsx - shadcn Checkbox
""", model="opus")

Task("ui-engineer-enhanced", """TASK-2.4: Build Keyword Search Component

Create skillmeat/web/components/requests/request-log-search.tsx:

1. Use shadcn Input component
2. Features:
   - Real-time search with 300ms debounce
   - Search icon prefix
   - Clear button when text present
   - Keyboard shortcuts (Cmd+K to focus)
   - Loading indicator during search
3. Integration with URL state (searchParams)
4. Search fields: title, problem, goal, notes

Reference:
- .claude/rules/web/components.md - Component conventions
- .claude/context/key-context/component-patterns.md - Input patterns
- skillmeat/web/components/ui/input.tsx - shadcn Input
""", model="opus")

Task("ui-engineer-enhanced", """TASK-2.5: Build Document Detail Modal

Create skillmeat/web/components/requests/request-log-modal.tsx:

1. Use shadcn Dialog component
2. Layout sections:
   - Header: ID, type badge, status badge
   - Metadata: Domain, subdomain, priority, created, updated
   - Content: Title, problem, goal
   - Notes: Formatted with line breaks
   - Context: JSON viewer or formatted display
3. Features:
   - Close button (X icon)
   - Escape key to close
   - Click outside to close
   - Loading state while fetching
   - Error state if load fails
4. Integration with useRequestLog hook

Reference:
- .claude/rules/web/components.md - Component conventions
- .claude/context/key-context/component-patterns.md - Dialog patterns
- skillmeat/web/components/ui/dialog.tsx - shadcn Dialog
""", model="opus")

Task("ui-engineer-enhanced", """TASK-2.6: Create TanStack Query Hooks

Create hooks in skillmeat/web/hooks/:

1. use-request-logs.ts:
   - Hook: useRequestLogs(filters: FilterState)
   - Fetches list with filters
   - Returns { data, isLoading, error, refetch }
   - Implements pagination
   - Cache key: ['requestLogs', filters]

2. use-request-log.ts:
   - Hook: useRequestLog(id: string)
   - Fetches single item
   - Returns { data, isLoading, error }
   - Cache key: ['requestLog', id]

3. use-filter-options.ts:
   - Hook: useFilterOptions()
   - Fetches available filter values
   - Returns { types, domains, subdomains, statuses }
   - Cache key: ['filterOptions']
   - Cache time: 5 minutes

All hooks:
- Use apiClient from @/lib/api-client
- Proper TypeScript types
- Error handling
- Export from @/hooks barrel

Reference:
- .claude/rules/web/components.md - Hook conventions
- .claude/context/key-context/component-patterns.md - TanStack Query patterns
- skillmeat/web/hooks/index.ts - Barrel exports
""", model="opus")

# Batch 3 (Testing - After all components)
Task("ui-engineer-enhanced", """TASK-2.7: Write Frontend Unit Tests

Create tests in skillmeat/web/__tests__/components/requests/:

1. request-log-table.test.tsx:
   - Renders table with data
   - Handles empty state
   - Sorting works correctly
   - Pagination controls work
   - Row click opens modal
   - Loading state displays

2. request-log-filters.test.tsx:
   - Renders all filter groups
   - Select all/clear all work
   - Filter selection updates URL
   - Subdomain filters based on domain
   - Reset all filters works

3. request-log-search.test.tsx:
   - Renders input
   - Debounces search input
   - Clear button works
   - Updates URL with search term
   - Keyboard shortcuts work

4. request-log-modal.test.tsx:
   - Renders all sections
   - Displays all fields correctly
   - Close button works
   - Escape key closes
   - Click outside closes
   - Loading state works

Coverage target: >80%

Reference:
- .claude/rules/web/testing.md - Testing conventions
- .claude/context/key-context/testing-patterns.md - Test templates
- skillmeat/web/__tests__/ - Existing test examples
""", model="opus")
```

---

## Overview

Build the frontend pages and components for the request log viewer feature. This phase creates the user interface for browsing, filtering, and viewing MeatyCapture request logs through a web interface.

**Why This Phase**: Phase 1 provides the API endpoints. Phase 2 builds the UI to consume them.

**Scope**:
- **IN SCOPE**: Next.js page, React components, TanStack Query hooks, component tests
- **OUT OF SCOPE**: E2E tests (Phase 3), API changes, backend logic

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | All components render without errors | Pending |
| SC-2 | Filters update table reactively | Pending |
| SC-3 | Modal displays all item fields correctly | Pending |
| SC-4 | Tests achieve >80% coverage | Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| TASK-2.1 | Create page structure | Pending | ui-engineer-enhanced | None | 0.5 days | Route setup |
| TASK-2.2 | Build document list table | Pending | ui-engineer-enhanced | TASK-2.1 | 1 day | TanStack Table |
| TASK-2.3 | Build multi-select filters | Pending | ui-engineer-enhanced | TASK-2.1 | 1 day | Type/domain/subdomain/status |
| TASK-2.4 | Build keyword search | Pending | ui-engineer-enhanced | TASK-2.1 | 0.5 days | Debounced search |
| TASK-2.5 | Build detail modal | Pending | ui-engineer-enhanced | TASK-2.1 | 1 day | Full document view |
| TASK-2.6 | Create TanStack Query hooks | Pending | ui-engineer-enhanced | None | 0.5 days | API integration |
| TASK-2.7 | Write frontend tests | Pending | ui-engineer-enhanced | TASK-2.2-2.6 | 1 day | >80% coverage |

**Status Legend**:
- `Pending` Not Started
- `In Progress` Currently being worked on
- `Complete` Done
- `Blocked` Waiting on dependency
- `At Risk` May not meet deadline

---

## Architecture Context

### Frontend Stack

**Framework**: Next.js 15 with App Router
**UI Library**: React 18 with TypeScript
**Component Library**: shadcn/ui (Radix UI primitives)
**Data Fetching**: TanStack Query v5
**Styling**: Tailwind CSS
**Testing**: Jest + React Testing Library

### Component Architecture

```
app/requests/page.tsx (Server Component)
├── RequestLogsClient (Client Component)
    ├── RequestLogFilters (sidebar)
    │   ├── TypeFilter
    │   ├── DomainFilter
    │   ├── SubdomainFilter
    │   └── StatusFilter
    ├── RequestLogSearch (header)
    └── RequestLogTable (main)
        └── RequestLogModal (triggered by row click)
```

### State Management

**URL State** (searchParams):
- Filters: `?type=bug,enhancement&domain=api`
- Search: `?q=keyword`
- Pagination: `?page=2&limit=25`
- Sorting: `?sort=created&order=desc`

**TanStack Query State**:
- Server cache for API responses
- Background refetching
- Optimistic updates (Phase 3)

### Key Files

**New Files** (Phase 2):
- `skillmeat/web/app/requests/page.tsx` - Main page route
- `skillmeat/web/components/requests/request-log-table.tsx` - Table component
- `skillmeat/web/components/requests/request-log-filters.tsx` - Filter sidebar
- `skillmeat/web/components/requests/request-log-search.tsx` - Search input
- `skillmeat/web/components/requests/request-log-modal.tsx` - Detail modal
- `skillmeat/web/hooks/use-request-logs.ts` - List query hook
- `skillmeat/web/hooks/use-request-log.ts` - Single item hook
- `skillmeat/web/hooks/use-filter-options.ts` - Filter options hook

**Dependencies** (Existing):
- `skillmeat/web/components/ui/*.tsx` - shadcn components
- `skillmeat/web/lib/api-client.ts` - API client
- `skillmeat/web/hooks/index.ts` - Hook barrel exports

---

## Implementation Details

### Technical Approach

1. **Page Structure** (TASK-2.1):
   - Create Next.js 15 page with server/client component split
   - Setup TanStack Query provider
   - Responsive layout with filter sidebar + main content

2. **Table Component** (TASK-2.2):
   - TanStack Table for sorting/pagination
   - shadcn Table UI components
   - Row click handler for modal
   - Badge components for type/status/domain

3. **Filter Components** (TASK-2.3):
   - Multi-select checkboxes for each filter type
   - URL state synchronization
   - Subdomain filtering based on selected domains
   - Active filter count badges

4. **Search Component** (TASK-2.4):
   - Debounced input (300ms)
   - URL state sync
   - Keyboard shortcuts (Cmd+K)
   - Clear button

5. **Modal Component** (TASK-2.5):
   - shadcn Dialog component
   - Sections for metadata, content, notes, context
   - Loading/error states
   - Keyboard navigation (Escape to close)

6. **TanStack Query Hooks** (TASK-2.6):
   - `useRequestLogs` - Paginated list with filters
   - `useRequestLog` - Single item by ID
   - `useFilterOptions` - Available filter values
   - Proper cache keys and stale times

7. **Testing** (TASK-2.7):
   - Jest + React Testing Library
   - Component rendering tests
   - User interaction tests
   - TanStack Query mock setup
   - Coverage >80%

---

## Session Notes

### [Date TBD]

**Completed**:
- Created Phase 2 progress tracking

**In Progress**:
- Awaiting Phase 1 completion

**Next Session**:
- Execute Batch 1 (TASK-2.1)

---

## Additional Resources

- **PRD**: `docs/project_plans/features/request-log-viewer-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/features/request-log-viewer-v1.md`
- **Frontend Rules**: `.claude/rules/web/` (components, pages, testing)
- **Component Patterns**: `.claude/context/key-context/component-patterns.md`
- **Next.js Patterns**: `.claude/context/key-context/nextjs-patterns.md`
- **Testing Patterns**: `.claude/context/key-context/testing-patterns.md`
