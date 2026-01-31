# Implementation Plan: MeatyCapture Request-Log Viewer

**Complexity Level**: Medium (M) | **Track**: Standard Track
**Estimated Total Effort**: 10-12 days | **Estimated Timeline**: 2.5-3 weeks
**Related PRD**: `docs/project_plans/PRDs/features/request-log-viewer-v1.md`

---

## Executive Summary

This implementation plan breaks down the MeatyCapture Request-Log Viewer feature into four phases with specific, actionable tasks. The feature enables users to browse, search, and filter captured request logs (bugs, enhancements, ideas, tasks, questions) directly within the SkillMeat web UI, eliminating the need to switch to the terminal.

**Key Deliverables**:
- Backend API with 3 endpoints (list, detail, search)
- Frontend viewer page with modal detail view
- Multi-select filters and keyword search
- Full test coverage (>80%) for both backend and frontend
- OpenAPI documentation and user guide

**Success Metrics**:
- API list endpoint <500ms latency
- Search endpoint <1000ms latency
- Frontend test coverage >80%
- API integration test pass rate 100%

---

## Architecture Overview

### Backend Architecture

```
skillmeat/api/routers/request_logs.py (NEW)
  └── GET /api/v1/projects/{project_id}/request-logs
  └── GET /api/v1/projects/{project_id}/request-logs/{document_id}
  └── GET /api/v1/projects/{project_id}/request-logs/search

skillmeat/core/request_log_manager.py (NEW)
  └── RequestLogManager class
      ├── list_documents() → subprocess to meatycapture list --json
      ├── get_document() → subprocess to meatycapture view --json
      └── search_documents() → client-side filtering + CLI integration

skillmeat/api/schemas/request_logs.py (NEW)
  └── Pydantic DTOs for all request/response models
```

### Frontend Architecture

```
skillmeat/web/app/projects/[id]/request-logs/ (NEW)
  ├── page.tsx (Server component)
  ├── layout.tsx (Page layout)
  └── components/
      ├── request-log-list.tsx (Client component with TanStack Query)
      ├── request-log-filters.tsx (Multi-select filters)
      ├── request-log-search.tsx (Keyword search)
      ├── request-log-table.tsx (Document list table)
      └── request-log-modal.tsx (Detail view modal)

skillmeat/web/hooks/ (NEW)
  └── useRequestLogs.ts (TanStack Query hook)
```

### Data Flow

```
1. User navigates to /projects/{id}/request-logs
   ↓
2. Server component fetches initial documents (GET /api/v1/projects/{id}/request-logs)
   ↓
3. Client renders RequestLogList with filters/search
   ↓
4. User applies filters/search
   ↓
5. TanStack Query hook updates with new query params (GET /api/v1/projects/{id}/request-logs/search)
   ↓
6. User clicks document row
   ↓
7. Modal opens, shows cached or fresh details (GET /api/v1/projects/{id}/request-logs/{doc_id})
   ↓
8. User closes modal or navigates away
```

---

## Phase 1: Backend API Foundation (3-4 days)

### TASK-1.1: RequestLogManager Implementation

**Assigned To**: python-backend-engineer (Opus)
**Effort**: 2 days
**Story Points**: 5

**Description**:
Create core RequestLogManager class that handles subprocess integration with MeatyCapture CLI. This manager will be responsible for all interactions with the meatycapture command-line tool, including error handling, JSON parsing, and DTO generation.

**Acceptance Criteria**:
- [ ] RequestLogManager class exists at `skillmeat/core/request_log_manager.py`
- [ ] `list_documents(project_path)` method calls `meatycapture log list --json` and returns structured RequestLogDocument DTOs
- [ ] `get_document(project_path, document_id)` method calls `meatycapture log view --json` and returns RequestLogDocumentDetail DTO
- [ ] `search_documents(project_path, query, filters)` method performs client-side filtering on CLI results
- [ ] All subprocess calls have 5-second timeout limit
- [ ] Graceful error handling for missing CLI, invalid JSON, subprocess errors
- [ ] Debug logging for each CLI invocation with command, output size, execution time
- [ ] No exceptions raised to caller; errors returned as structured ErrorResponse

**Implementation Notes**:
- Use subprocess.run() with timeout=5 and capture_output=True
- Parse --json output with json.loads(); validate against expected schema
- Cache subprocess results in memory for <5 minute window (defer to TanStack Query for actual caching)
- Handle cases: CLI not found, project has no request logs, invalid JSON output
- Log structured JSON: {timestamp, command, project_id, duration_ms, success, error_code}

**Definition of Done**:
- Unit tests cover all three methods with mocked subprocess calls
- Error handling tests for CLI missing, timeout, invalid JSON
- Code follows skillmeat.core patterns (logging, error handling, type hints)

---

### TASK-1.2: Request-Log Schemas (DTOs)

**Assigned To**: python-backend-engineer (Opus)
**Effort**: 1 day
**Story Points**: 3

**Description**:
Create Pydantic models for all request-log API requests and responses. These schemas define the contract between frontend and backend, ensuring type safety and validation.

**Acceptance Criteria**:
- [ ] File created: `skillmeat/api/schemas/request_logs.py`
- [ ] RequestLogDocumentSummary DTO with fields: id, name, path, created_at, updated_at, item_count, type_counts, status_distribution
- [ ] RequestLogItem DTO with fields: id, type, title, domain, status, priority, problem, goal, context, notes, created_at
- [ ] RequestLogDocumentDetail DTO with fields: id, name, created_at, updated_at, items[]
- [ ] RequestLogListResponse DTO with documents[] and PageInfo
- [ ] RequestLogDetailResponse DTO with single document
- [ ] RequestLogSearchResponse DTO with results[] (document_id, document_name, items[]) and PageInfo
- [ ] PageInfo DTO with fields: page, page_size, total, has_next, has_prev
- [ ] ErrorResponse DTO with fields: code, message, trace_id (reuse existing if available)
- [ ] All enums for Type, Domain, Status, Priority match MeatyCapture CLI values

**Implementation Notes**:
- Reuse existing PageInfo and ErrorResponse from skillmeat.api.schemas.common if available
- Use Enum classes for Type, Domain, Status, Priority to maintain type safety
- Add Pydantic validators for optional fields (graceful handling if missing)
- Make optional fields truly optional (Optional[str] = None) for schema flexibility
- Include datetime with timezone info (UTC)

**Definition of Done**:
- All schemas defined and importable from module
- Pydantic validation tests pass (valid data accepted, invalid data rejected)
- Schema examples match API contract examples from PRD

---

### TASK-1.3: List Request-Logs API Endpoint

**Assigned To**: python-backend-engineer (Opus)
**Effort**: 1 day
**Story Points**: 3

**Description**:
Implement GET /api/v1/projects/{project_id}/request-logs endpoint. This endpoint returns a paginated list of request-log documents for a given project, including metadata about each document.

**Acceptance Criteria**:
- [ ] Router exists at `skillmeat/api/routers/request_logs.py`
- [ ] Endpoint: `GET /api/v1/projects/{project_id}/request-logs`
- [ ] Query parameters: page (default=1), page_size (default=50, max=100), sort_by (default=name), sort_order (default=asc)
- [ ] Response: RequestLogListResponse with documents[] and PageInfo
- [ ] Pagination implemented correctly (offset/limit logic)
- [ ] 200 status code on success
- [ ] 404 status code if project not found
- [ ] 500 status code with helpful error message if CLI fails (e.g., "MeatyCapture CLI not found or project has no request logs")
- [ ] OpenAPI schema auto-generated correctly
- [ ] Execution time <500ms for typical projects (50-100 documents)

**Implementation Notes**:
- Use existing project_registry to resolve project_path from project_id
- Call RequestLogManager.list_documents(project_path)
- Apply pagination to results in-memory (sort, slice)
- Logging: include project_id, document_count, duration in structured logs
- Follow FastAPI router patterns: async handler, proper type hints, Depends() for managers

**Definition of Done**:
- Integration test passes (list returns valid response format)
- Error cases tested (missing project, CLI not found, empty results)
- Latency benchmark confirms <500ms

---

### TASK-1.4: Document Detail API Endpoint

**Assigned To**: python-backend-engineer (Opus)
**Effort**: 1 day
**Story Points**: 3

**Description**:
Implement GET /api/v1/projects/{project_id}/request-logs/{document_id} endpoint. This endpoint returns full details for a single request-log document, including all items with expanded fields.

**Acceptance Criteria**:
- [ ] Endpoint: `GET /api/v1/projects/{project_id}/request-logs/{document_id}`
- [ ] Response: RequestLogDetailResponse with document (id, name, created_at, updated_at, items[])
- [ ] Items include all fields: id, type, title, domain, status, priority, problem, goal, context, notes, created_at
- [ ] 200 status code on success
- [ ] 404 status code if document not found
- [ ] 500 status code if CLI fails
- [ ] OpenAPI schema auto-generated

**Implementation Notes**:
- Call RequestLogManager.get_document(project_path, document_id)
- Validate document_id format (expected: req-{timestamp}-{project} or similar)
- Return all item fields; no truncation

**Definition of Done**:
- Integration test fetches document and validates all fields present
- 404 test for non-existent document_id
- Response schema matches RequestLogDetailResponse exactly

---

### TASK-1.5: Search & Filter API Endpoint

**Assigned To**: python-backend-engineer (Opus)
**Effort**: 1 day
**Story Points**: 4

**Description**:
Implement GET /api/v1/projects/{project_id}/request-logs/search endpoint. This endpoint performs keyword search and multi-field filtering across all request-log documents for a project.

**Acceptance Criteria**:
- [ ] Endpoint: `GET /api/v1/projects/{project_id}/request-logs/search`
- [ ] Query parameters: q (required), type (optional, comma-separated), domain (optional, comma-separated), status (optional, comma-separated), priority (optional, comma-separated), page, page_size
- [ ] Response: RequestLogSearchResponse with results[] (document_id, document_name, items[]) and PageInfo
- [ ] Keyword search across: title, problem, goal, notes (case-insensitive)
- [ ] Filter logic: AND semantics within filters (e.g., type=bug AND status=open), OR within comma-separated values
- [ ] Results returned with matching document and matching items only
- [ ] Pagination applied to result set
- [ ] 200 status code on success
- [ ] 400 status code if query parameter 'q' missing
- [ ] 500 status code if CLI fails
- [ ] Execution time <1000ms for typical projects

**Implementation Notes**:
- Implement search in RequestLogManager.search_documents() using Python string matching
- Fetch all documents from CLI (meatycapture log list --json)
- Filter in-memory: iterate documents, filter items by criteria, keep only non-empty results
- Consider performance: with 100 documents × 10 items each, should complete <1000ms
- Case-insensitive search using str.lower()

**Definition of Done**:
- Integration test with keyword search returns matching items only
- Filter test: type=bug returns only bugs
- Combined test: q=modal AND type=bug AND status=open returns intersection
- Pagination test: page=2 returns next page of results
- Error test: missing 'q' parameter returns 400

---

### TASK-1.6: API Integration Tests

**Assigned To**: python-backend-engineer (Opus)
**Effort**: 1.5 days
**Story Points**: 4

**Description**:
Write comprehensive integration tests for all three request-log API endpoints. Tests should cover happy paths, error cases, edge cases, and performance.

**Acceptance Criteria**:
- [ ] Test file created: `skillmeat/api/tests/test_request_logs_routes.py`
- [ ] List endpoint tests: success, pagination, sorting, empty results, missing project, CLI error
- [ ] Detail endpoint tests: success, missing document, invalid document_id, CLI error
- [ ] Search endpoint tests: keyword search, filters (type, domain, status, priority), combined filters, pagination, missing 'q' param
- [ ] All tests use mocked RequestLogManager (not actual CLI calls)
- [ ] Test coverage >80%
- [ ] Fixtures for mock documents and items
- [ ] Performance assertions: list <500ms, search <1000ms
- [ ] Error response format validated (ErrorResponse schema)

**Implementation Notes**:
- Use pytest + TestClient(app)
- Mock RequestLogManager using monkeypatch or dependency override
- Create realistic mock data matching MeatyCapture JSON structure
- Test both success and failure paths for each endpoint
- Use parametrize for testing multiple filter combinations
- Assert response status codes, schema validation, pagination logic

**Definition of Done**:
- All tests pass: `pytest skillmeat/api/tests/test_request_logs_routes.py -v`
- Coverage report shows >80%: `pytest --cov=skillmeat.api.routers.request_logs --cov-report=term`
- No test warnings or errors

---

## Phase 2: Frontend Pages & Components (3-4 days)

### TASK-2.1: Request-Logs Page Structure

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Create the base page structure for the request-logs viewer at /projects/[id]/request-logs. This includes page layout, loading states, and error handling.

**Acceptance Criteria**:
- [ ] Page file created: `skillmeat/web/app/projects/[id]/request-logs/page.tsx`
- [ ] Server component that accepts params (Next.js 15 pattern: params as Promise)
- [ ] Fetches initial document list from API
- [ ] Renders RequestLogList client component
- [ ] Page title shows: "Request Logs for [Project Name]"
- [ ] Loading skeleton/placeholder displayed while fetching
- [ ] Error state with user-friendly message if API fails
- [ ] Empty state message if project has no request logs
- [ ] Layout file: `skillmeat/web/app/projects/[id]/request-logs/layout.tsx`

**Implementation Notes**:
- Use Next.js 15 App Router patterns
- Server component by default (no 'use client')
- Fetch with error handling: try/catch, log errors, return error state to client component
- Reuse existing project context resolution from URL params
- Follow existing page structure patterns (e.g., /projects/[id]/manage/page.tsx)

**Definition of Done**:
- Page renders without errors
- TypeScript compilation passes
- ESLint checks pass

---

### TASK-2.2: Request-Log Document List Table

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 1 day
**Story Points**: 3

**Description**:
Build the RequestLogTable component that displays request-log documents in a sortable, clickable table. This is the main UI for browsing documents.

**Acceptance Criteria**:
- [ ] Component created: `skillmeat/web/components/request-logs/request-log-table.tsx`
- [ ] Displays table with columns: Name, Item Count, Type Distribution, Status, Actions
- [ ] Type Distribution shows badge counts: bug, enhancement, idea, task, question
- [ ] Status column shows distribution: open, in-progress, closed
- [ ] Rows are clickable (onClick event)
- [ ] Hover effect on rows to indicate interactivity
- [ ] Accessible: table headers have scope attribute, rows have role=row
- [ ] Sorting indicators (▲▼) for sortable columns
- [ ] Copy-to-clipboard button for document name
- [ ] No inline styles; all Tailwind classes
- [ ] Responsive: stacks on mobile, full layout on desktop

**Implementation Notes**:
- Use shadcn/ui Table component (or create with basic HTML + Tailwind)
- Row onClick callbacks passed as prop from parent (RequestLogList)
- Type distribution as inline badges (different colors per type)
- Use existing Badge component from shadcn/ui
- Status distribution as stacked text or small badges
- Keyboard accessible: Tab through rows, Enter to open modal

**Definition of Done**:
- Component renders without errors
- All columns display correctly
- Clicking row fires onClick callback
- No TypeScript errors
- ESLint passes

---

### TASK-2.3: Multi-Select Filter UI Component

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 1 day
**Story Points**: 3

**Description**:
Build the RequestLogFilters component with multi-select dropdowns for Type, Domain, Status, and Priority. Filters should update the URL query parameters and trigger API queries.

**Acceptance Criteria**:
- [ ] Component created: `skillmeat/web/components/request-logs/request-log-filters.tsx`
- [ ] Client component ('use client')
- [ ] Dropdowns for: Type (bug, enhancement, idea, task, question), Domain (dynamic), Status (open, in-progress, closed), Priority (critical, high, medium, low)
- [ ] Multi-select capability: checkboxes within dropdown
- [ ] Selected values displayed as pills/badges below dropdowns
- [ ] Clear all filters button
- [ ] Clicking X on pill removes single filter
- [ ] Filter state synchronized with URL query parameters
- [ ] onChange callback triggers parent update via TanStack Query
- [ ] Accessible: ARIA labels, keyboard navigation (Tab, Space, Enter)
- [ ] Responsive: stacks on mobile

**Implementation Notes**:
- Use shadcn/ui Popover + Checkbox components
- State managed via URL search params (not local state) for shareability
- useSearchParams and useRouter from 'next/navigation'
- onChange updates URL: router.push(`?${new URLSearchParams(...).toString()}`)
- Extract domain list dynamically from loaded documents
- Use cn() for conditional classes

**Definition of Done**:
- Component renders without errors
- Filter selections update URL params
- Parent component receives filter updates
- No TypeScript errors
- ESLint passes

---

### TASK-2.4: Keyword Search Component

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Build the RequestLogSearch component with a text input for keyword search. Search should be debounced and update URL query parameters.

**Acceptance Criteria**:
- [ ] Component created: `skillmeat/web/components/request-logs/request-log-search.tsx`
- [ ] Client component ('use client')
- [ ] Text input with placeholder: "Search by keyword..."
- [ ] Debounce search input (300ms delay before API call)
- [ ] Clear button (X) to reset search
- [ ] Search query added to URL: ?q=search%20term
- [ ] onChange callback triggers TanStack Query refetch
- [ ] Accessible: label, ARIA label on input
- [ ] Responsive: full width on mobile, fixed width on desktop

**Implementation Notes**:
- Use debounce utility from lodash or custom implementation
- Update URL params on debounced search
- Call parent callback with search query
- Keep input value in local state; URL param is source of truth for API calls

**Definition of Done**:
- Input accepts text and updates state
- Debounce prevents excessive API calls
- Clear button resets search
- No TypeScript errors

---

### TASK-2.5: Request-Log Detail Modal Component

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 1 day
**Story Points**: 3

**Description**:
Build the RequestLogModal component that displays document details in an expandable modal. Users can view individual item details with full context.

**Acceptance Criteria**:
- [ ] Component created: `skillmeat/web/components/request-logs/request-log-modal.tsx`
- [ ] Client component ('use client')
- [ ] Uses shadcn/ui Dialog component for modal
- [ ] Displays document name as title
- [ ] Lists all items in document
- [ ] Each item row shows: type badge, domain tag, status indicator, priority, title
- [ ] Items are clickable/expandable to show: problem, goal, context, notes
- [ ] Expanded item shows all fields in readable format
- [ ] Copy-to-clipboard button for each item
- [ ] Keyboard navigation: Esc to close, Arrow Up/Down to navigate items, Enter to toggle expand
- [ ] Accessible: ARIA labels, focus trap within modal, semantic HTML
- [ ] Close button and Esc key close modal
- [ ] Modal scrollable if many items
- [ ] Uses Tailwind classes only; no inline styles

**Implementation Notes**:
- Use shadcn/ui Dialog, Button, Badge components
- Local state for expanded item index
- useEffect to handle keyboard events (Esc, Arrow keys)
- Copy functionality using navigator.clipboard.writeText()
- Item cards with expandable details using Collapsible or custom expand logic
- Type badges in different colors per type

**Definition of Done**:
- Modal opens on prop change
- Modal closes on Esc or close button
- Items expand/collapse on click
- Copy button works
- Keyboard navigation functions
- No TypeScript errors

---

### TASK-2.6: Custom TanStack Query Hook

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Create custom TanStack Query hooks for request-log data fetching. These hooks encapsulate API interaction and caching logic.

**Acceptance Criteria**:
- [ ] Hook file created: `skillmeat/web/hooks/useRequestLogs.ts`
- [ ] `useRequestLogs()` hook returns useQuery for list endpoint
- [ ] `useRequestLogSearch()` hook returns useQuery for search endpoint
- [ ] `useRequestLogDetail()` hook returns useQuery for detail endpoint
- [ ] Cache TTL set to 5 minutes
- [ ] Retry logic: 1 retry on network failure, no retry on 400/404
- [ ] Handles loading, error, and success states
- [ ] Error messages user-friendly
- [ ] Hooks accept project_id and relevant query params
- [ ] TypeScript types properly defined

**Implementation Notes**:
- Use @tanstack/react-query v5+
- Set staleTime: 5 * 60 * 1000 for cache duration
- Use useQueryClient for manual invalidation if needed
- Handle auth headers automatically (via existing API client)
- Define types for response data

**Definition of Done**:
- Hooks can be imported and used in components
- No TypeScript errors
- Hooks return proper query state (data, isLoading, error)

---

### TASK-2.7: Frontend Unit Tests

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 1 day
**Story Points**: 3

**Description**:
Write unit tests for all frontend components and hooks. Tests should cover rendering, user interactions, data fetching, and error states.

**Acceptance Criteria**:
- [ ] Test file: `skillmeat/web/__tests__/request-logs.test.tsx`
- [ ] RequestLogTable: renders rows, click fires callback, sorting works
- [ ] RequestLogFilters: filter selection updates URL, pills display correctly
- [ ] RequestLogSearch: debounced search, clear button works
- [ ] RequestLogModal: opens/closes, items expand, copy button works, keyboard nav works
- [ ] useRequestLogs hook: queries API, handles loading/error states
- [ ] useRequestLogSearch hook: queries with filters, pagination
- [ ] Test coverage >80%
- [ ] All tests pass

**Implementation Notes**:
- Use Jest + React Testing Library (RTL)
- Mock useSearchParams, useRouter from next/navigation
- Mock TanStack Query using QueryClientProvider with test client (retry: false)
- Mock API responses
- Use userEvent.setup() for interactions (not fireEvent)
- Render components with necessary providers (QueryClientProvider, etc.)
- Use getByRole, getByLabelText queries (in that priority order)

**Definition of Done**:
- All tests pass: `pnpm test request-logs`
- Coverage report shows >80%
- No test warnings or errors

---

## Phase 3: Integration & Polish (2-3 days)

### TASK-3.1: End-to-End Integration Testing

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 1 day
**Story Points**: 3

**Description**:
Write Playwright E2E tests covering the complete user flow from viewing the request-log list to opening a document detail modal.

**Acceptance Criteria**:
- [ ] Test file: `skillmeat/web/tests/request-logs-e2e.spec.ts`
- [ ] Test: Navigate to request-logs page, list loads successfully
- [ ] Test: Apply filter (e.g., type=bug), table updates
- [ ] Test: Enter search query, results update
- [ ] Test: Click document row, modal opens
- [ ] Test: Expand item in modal, details visible
- [ ] Test: Close modal with Esc key
- [ ] Test: Navigation back to list after modal close
- [ ] All tests pass in headless mode
- [ ] No console errors or warnings

**Implementation Notes**:
- Use Playwright with fixtures from existing test setup
- Start with API mocking or real test data
- Test against local dev server
- Include checks for accessibility (Tab navigation works)
- Verify modal closes properly on Esc

**Definition of Done**:
- All E2E tests pass: `pnpm test:e2e request-logs`
- No test flakiness or timeouts

---

### TASK-3.2: URL State Persistence

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Ensure filter and search state persist in URL query parameters, allowing users to bookmark and share filter states.

**Acceptance Criteria**:
- [ ] URL updates when filters change: `?type=bug&domain=web&status=open`
- [ ] URL updates when search query changes: `?q=search%20term`
- [ ] Combined params work: `?type=bug&q=modal&page=2`
- [ ] Page refresh preserves filter state
- [ ] URL can be bookmarked and shared
- [ ] Back/forward browser buttons work correctly
- [ ] Search params validated (unknown params ignored)

**Implementation Notes**:
- Use useSearchParams and useRouter from next/navigation
- Encode search query properly with URLSearchParams
- Validate query params before API call
- Ensure TanStack Query respects URL params as query key

**Definition of Done**:
- Manual testing: apply filters, refresh page, filters still present
- URL parameter validation test
- Browser back/forward navigation works

---

### TASK-3.3: Performance Optimization

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Optimize API and frontend performance to meet latency targets: list <500ms, search <1000ms.

**Acceptance Criteria**:
- [ ] List endpoint consistently <500ms (benchmark against production load)
- [ ] Search endpoint consistently <1000ms
- [ ] Frontend renders table in <200ms after data arrives
- [ ] Modal opens smoothly without lag
- [ ] No unnecessary API calls (proper query key setup)
- [ ] Pagination applied to reduce data transfer for large result sets
- [ ] Images/icons lazy-loaded if any
- [ ] Browser DevTools shows good performance metrics (LCP, FID, CLS)

**Implementation Notes**:
- Use React DevTools Profiler to measure component render times
- Check Network tab for API timing
- Verify TanStack Query is not making duplicate requests
- Consider request deduplication if filters change rapidly
- Profile with Chrome DevTools

**Definition of Done**:
- Performance benchmarks documented
- No noticeable lag in UI interactions
- API latency targets met in testing

---

### TASK-3.4: Accessibility Audit

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Audit the request-log viewer for WCAG 2.1 AA compliance. Ensure keyboard navigation, screen reader support, and color contrast all pass standards.

**Acceptance Criteria**:
- [ ] Keyboard navigation: Tab through filters, search, table rows, modal items
- [ ] Screen reader testing: All interactive elements announced correctly
- [ ] Color contrast: Text >4.5:1 ratio against background
- [ ] ARIA labels: All buttons and form inputs have meaningful labels
- [ ] Focus management: Focus visible on all interactive elements
- [ ] Modal focus trap: Focus stays within modal when open
- [ ] Semantic HTML: Use <button>, <input>, <table> correctly (not <div role="button">)
- [ ] No automatic focus traps that prevent navigation

**Implementation Notes**:
- Use axe-core or similar tool to scan for violations
- Manual keyboard testing: Tab through entire UI, verify all features accessible
- Test with screen reader (NVDA on Windows, VoiceOver on macOS)
- Use WebAIM color contrast checker for colors
- Ensure :focus-visible CSS is applied (use Tailwind focus-visible class)

**Definition of Done**:
- axe scan shows zero violations
- Manual keyboard navigation successful
- Screen reader test successful
- WCAG 2.1 AA compliance confirmed

---

### TASK-3.5: Error Handling & User Feedback

**Assigned To**: ui-engineer-enhanced (Opus)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Implement comprehensive error handling and user feedback for all failure scenarios. Users should understand what went wrong and how to recover.

**Acceptance Criteria**:
- [ ] API error (500): Display "An error occurred. Please try again later."
- [ ] Missing CLI: Display "MeatyCapture not found. Please ensure meatycapture CLI is installed."
- [ ] No request logs: Display "This project has no request logs yet. Use meatycapture CLI to capture requests."
- [ ] Network timeout: Display "Request timed out. Please check your connection and try again."
- [ ] Invalid filter: Display "Invalid filter. Please refresh and try again."
- [ ] Errors logged to console with trace_id for debugging
- [ ] Toast or alert component for user-facing messages
- [ ] Retry button on error states

**Implementation Notes**:
- Handle error states from TanStack Query
- Parse API error responses and extract meaningful messages
- Use existing toast/alert components if available
- Include helpful next steps in error messages
- Log errors with request context for debugging

**Definition of Done**:
- Manual testing: trigger each error scenario, verify message displays
- No unhandled promise rejections in console
- User can recover from errors (retry or navigate away)

---

## Phase 4: Documentation & Deployment (1-2 days)

### TASK-4.1: API Documentation & OpenAPI

**Assigned To**: documentation-writer (Sonnet)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Ensure OpenAPI documentation is auto-generated and accurate for all request-log endpoints. Create API documentation in docs/ directory.

**Acceptance Criteria**:
- [ ] OpenAPI schema generated at `/docs` (Swagger UI) for all 3 endpoints
- [ ] All endpoint descriptions, query params, response schemas documented
- [ ] Example requests and responses included
- [ ] Error response codes documented (400, 404, 500)
- [ ] Authentication requirements documented
- [ ] File: `docs/api/request-logs-endpoints.md` with detailed endpoint specs
- [ ] README updated with feature description (if applicable)

**Implementation Notes**:
- OpenAPI auto-generated from FastAPI route docstrings and type hints
- Add detailed docstrings to route handlers if needed
- Use example/schema in Pydantic models for OpenAPI examples
- Verify /docs endpoint shows all endpoints and schemas correctly
- Can export OpenAPI JSON: `python -m skillmeat.api.server --export-openapi > openapi.json`

**Definition of Done**:
- Visit http://localhost:8000/docs, verify all endpoints documented
- Example requests can be executed from Swagger UI
- OpenAPI schema is valid JSON

---

### TASK-4.2: Architecture Decision Record (ADR)

**Assigned To**: documentation-writer (Sonnet)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Document the architectural decisions made for request-log viewer, particularly the subprocess integration with MeatyCapture CLI.

**Acceptance Criteria**:
- [ ] File: `.claude/context/adrs/request-log-viewer-subprocess-integration.md`
- [ ] Sections: Problem, Decision, Rationale, Alternatives Considered, Consequences, Validation
- [ ] Explains why subprocess + CLI is appropriate (vs. embedding meatycapture as library)
- [ ] Documents error handling strategy
- [ ] Documents caching strategy (5-minute TTL via TanStack Query)
- [ ] Documents performance assumptions (acceptable latency with current approach)
- [ ] Lists potential future optimizations if performance becomes issue
- [ ] Documents security considerations (read-only, no cross-project leaks)

**Implementation Notes**:
- Use existing ADR template if available in repository
- Reference PRD requirements and design decisions
- Include timestamp and authors
- Link to related documentation

**Definition of Done**:
- ADR file written and reviewed
- Explains key design decisions clearly
- Can be referenced for future maintenance

---

### TASK-4.3: Feature Flag Implementation

**Assigned To**: python-backend-engineer (Sonnet)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Implement feature flag to enable/disable request-log viewer feature. Allows gradual rollout and quick disable if issues arise.

**Acceptance Criteria**:
- [ ] Config setting: `request_log_viewer_enabled` (default: false)
- [ ] Frontend: Check feature flag before rendering page; show coming-soon if disabled
- [ ] Backend: Return 404 or 503 if feature disabled
- [ ] Admin interface: Can toggle flag via config (if applicable)
- [ ] Logging: Log feature flag state at startup
- [ ] Documentation: How to enable/disable feature in deployment docs

**Implementation Notes**:
- Add to APISettings class or ConfigManager
- Use environment variable: SKILLMEAT_REQUEST_LOG_VIEWER_ENABLED
- Frontend can check flag via API endpoint or hardcoded for now
- Consider using gradual rollout percentage (10%, 50%, 100%) if desired

**Definition of Done**:
- Feature flag controls endpoint availability
- Feature disabled shows appropriate message to users
- Can be toggled without restart (if using dynamic config)

---

### TASK-4.4: User Guide & README

**Assigned To**: documentation-writer (Sonnet)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Create user-facing documentation explaining how to use the request-log viewer.

**Acceptance Criteria**:
- [ ] File: `docs/features/request-log-viewer.md`
- [ ] Sections: Overview, Getting Started, Filtering, Searching, Viewing Details, Tips
- [ ] Screenshots/GIFs showing key workflows
- [ ] Keyboard shortcuts documented (Esc, Arrow keys, Tab)
- [ ] Link to MeatyCapture CLI for capturing requests
- [ ] FAQ: "Can I create requests from web UI?" (Answer: No, use CLI)
- [ ] Troubleshooting: Common issues and solutions
- [ ] Updated main README with feature mention

**Implementation Notes**:
- Include concrete examples and use cases
- Use friendly, non-technical language
- Provide keyboard navigation reference
- Link to related tools and documentation

**Definition of Done**:
- Documentation complete and reviewed
- Screenshots/GIFs show feature in action
- Covers all key user workflows

---

### TASK-4.5: Beta Release & Monitoring

**Assigned To**: python-backend-engineer (Sonnet)
**Effort**: 0.5 days
**Story Points**: 2

**Description**:
Prepare feature for beta release. Set up monitoring, define rollout strategy, and document rollback procedure.

**Acceptance Criteria**:
- [ ] Feature flag set to 10% or 25% initially
- [ ] Monitoring setup: Log errors, track API latency, count API calls
- [ ] Analytics: Track feature_opened, filter_applied, search_executed events
- [ ] Rollback plan documented: Steps to disable if critical issues
- [ ] Known issues documented (if any)
- [ ] Canary testing: Feature tested with select users/projects first
- [ ] Success criteria for promoting from beta to general availability

**Implementation Notes**:
- Gradually increase feature flag percentage over 1-2 weeks
- Monitor error rates and latency closely
- Collect user feedback via analytics and support channels
- Be ready to rollback if performance issues or critical bugs discovered

**Definition of Done**:
- Feature flag at initial rollout percentage
- Monitoring dashboards active
- Team aware of rollback procedure
- Ready for beta user feedback

---

## Task Dependencies & Sequencing

### Dependency Graph

```
Phase 1 (Backend):
  ├─ TASK-1.1 (RequestLogManager)
  │   ├─ TASK-1.2 (Schemas) ← depends on 1.1
  │   ├─ TASK-1.3 (List endpoint) ← depends on 1.1, 1.2
  │   ├─ TASK-1.4 (Detail endpoint) ← depends on 1.1, 1.2
  │   └─ TASK-1.5 (Search endpoint) ← depends on 1.1, 1.2
  └─ TASK-1.6 (API tests) ← depends on 1.3, 1.4, 1.5

Phase 2 (Frontend):
  ├─ TASK-2.1 (Page structure) ← can start after Phase 1 complete
  ├─ TASK-2.2 (Table) ← depends on 2.1
  ├─ TASK-2.3 (Filters) ← depends on 2.1
  ├─ TASK-2.4 (Search) ← depends on 2.1
  ├─ TASK-2.5 (Modal) ← depends on 2.1
  ├─ TASK-2.6 (Hooks) ← depends on Phase 1 APIs
  └─ TASK-2.7 (Frontend tests) ← depends on 2.2, 2.3, 2.4, 2.5, 2.6

Phase 3 (Integration):
  ├─ TASK-3.1 (E2E tests) ← depends on Phase 1 + 2 complete
  ├─ TASK-3.2 (URL state) ← depends on 2.3, 2.4
  ├─ TASK-3.3 (Performance) ← depends on Phase 1 + 2 complete
  ├─ TASK-3.4 (Accessibility) ← depends on Phase 2 complete
  └─ TASK-3.5 (Error handling) ← depends on Phase 1 + 2 complete

Phase 4 (Documentation):
  ├─ TASK-4.1 (OpenAPI) ← depends on Phase 1 complete
  ├─ TASK-4.2 (ADR) ← depends on Phase 1 + design finalized
  ├─ TASK-4.3 (Feature flag) ← can start after Phase 1 begin
  ├─ TASK-4.4 (User guide) ← depends on Phase 1 + 2 complete
  └─ TASK-4.5 (Beta release) ← depends on Phase 1 + 2 + 3 complete
```

### Recommended Parallelization

**Week 1 (Days 1-4)**:
- TASK-1.1 (RequestLogManager) in parallel with TASK-1.2 (Schemas)
- Once 1.1 & 1.2 done, parallelize TASK-1.3, 1.4, 1.5 (three endpoints)
- TASK-1.6 (API tests) starts once endpoints have basic implementation

**Week 1-2 (Days 5-8)**:
- Phase 2 frontend tasks can start after Phase 1 APIs reach basic stability
- Parallelize TASK-2.2, 2.3, 2.4, 2.5 (table, filters, search, modal)
- TASK-2.6 (hooks) can start early once API contracts finalized
- TASK-2.7 (tests) starts mid-phase

**Week 2-3 (Days 9-12)**:
- Phase 3 integration tasks (TASK-3.1 through 3.5) once Phase 2 largely complete
- Parallelize TASK-3.3 (performance), 3.4 (accessibility), 3.5 (error handling)
- Phase 4 documentation tasks can start anytime; particularly 4.1 (OpenAPI), 4.3 (feature flag)
- TASK-4.5 (beta release) is final task

---

## Success Criteria & Acceptance

### Phase 1 Success Criteria
- [ ] All 3 API endpoints implemented and working
- [ ] API integration tests pass with >80% coverage
- [ ] Latency benchmarks achieved (<500ms list, <1000ms search)
- [ ] Error handling comprehensive (all error scenarios covered)
- [ ] OpenAPI schema correct and complete

### Phase 2 Success Criteria
- [ ] All 5 UI components render without errors
- [ ] User can perform complete workflow: navigate → filter → search → open modal → view details
- [ ] Frontend unit tests pass with >80% coverage
- [ ] Keyboard navigation works (Tab, Esc, Arrow keys)
- [ ] No TypeScript or ESLint errors

### Phase 3 Success Criteria
- [ ] E2E tests pass in headless mode
- [ ] URL state persistence working
- [ ] Performance targets met
- [ ] WCAG 2.1 AA compliance confirmed
- [ ] Error scenarios handled gracefully with user-friendly messages

### Phase 4 Success Criteria
- [ ] OpenAPI documentation complete and accurate
- [ ] ADR documented
- [ ] Feature flag implementation working
- [ ] User guide complete with examples
- [ ] Beta release plan defined and monitoring active

### Overall Feature Success
- Feature releases to users without critical bugs
- >50% of users adopt feature within 2 weeks
- >80% of requests use filters or search
- <30 seconds average modal interaction time
- API latency stays <500ms under production load

---

## Risk Mitigation Summary

| Risk | Mitigation |
|------|-----------|
| MeatyCapture CLI missing | Graceful error message, clear fallback, document requirement |
| Subprocess blocks API | Timeout limits (5s), async execution, worker pool if needed |
| Large documents slow | Pagination, caching, potential full-text index in future |
| Search latency | Client-side filtering fast, consider indexing if >10K items |
| Users expect write ops | Clear "read-only" label, link to CLI, FAQ in docs |
| Feature causes API degradation | Feature flag for quick disable, monitoring, gradual rollout |

---

## Effort Estimate Breakdown

| Phase | Task | Estimate | Notes |
|-------|------|----------|-------|
| Phase 1 | 1.1 RequestLogManager | 2d | Core subprocess integration |
| | 1.2 Schemas | 1d | Pydantic DTOs |
| | 1.3 List endpoint | 1d | GET /request-logs |
| | 1.4 Detail endpoint | 1d | GET /request-logs/{id} |
| | 1.5 Search endpoint | 1d | GET /request-logs/search |
| | 1.6 API tests | 1.5d | >80% coverage |
| | **Phase 1 Total** | **7.5d** | |
| Phase 2 | 2.1 Page structure | 0.5d | Basic layout |
| | 2.2 Document table | 1d | Sortable, clickable |
| | 2.3 Filters | 1d | Multi-select UI |
| | 2.4 Search | 0.5d | Debounced input |
| | 2.5 Modal | 1d | Expandable items |
| | 2.6 TanStack Query hooks | 0.5d | Custom hooks |
| | 2.7 Frontend tests | 1d | >80% coverage |
| | **Phase 2 Total** | **5.5d** | |
| Phase 3 | 3.1 E2E tests | 1d | Full flow testing |
| | 3.2 URL state | 0.5d | Persistence |
| | 3.3 Performance | 0.5d | Latency targets |
| | 3.4 Accessibility | 0.5d | WCAG 2.1 AA |
| | 3.5 Error handling | 0.5d | User feedback |
| | **Phase 3 Total** | **3d** | |
| Phase 4 | 4.1 OpenAPI docs | 0.5d | Auto-generated |
| | 4.2 ADR | 0.5d | Architecture decisions |
| | 4.3 Feature flag | 0.5d | Gradual rollout |
| | 4.4 User guide | 0.5d | Documentation |
| | 4.5 Beta release | 0.5d | Monitoring setup |
| | **Phase 4 Total** | **2.5d** | |
| **GRAND TOTAL** | **18.5 days** | ~3-4 weeks with buffer | |

---

## Quality Gate Checklists

### Backend Quality Gates (Phase 1)

- [ ] No Python syntax errors
- [ ] No type hints errors (mypy passes)
- [ ] No import errors or circular dependencies
- [ ] All unit tests pass
- [ ] API integration tests >80% coverage
- [ ] All error cases tested (happy path + 5+ error scenarios)
- [ ] Logging structured and consistent
- [ ] Code follows skillmeat style (black formatted, flake8 clean)
- [ ] API responses match schema exactly
- [ ] Subprocess calls have timeouts and error handling
- [ ] OpenAPI schema generated without errors

### Frontend Quality Gates (Phase 2)

- [ ] No TypeScript errors (tsc passes)
- [ ] No ESLint warnings
- [ ] All unit tests pass
- [ ] Test coverage >80%
- [ ] No console errors or warnings
- [ ] Components render without React warnings
- [ ] Tailwind classes properly formatted
- [ ] No inline styles
- [ ] Responsive design tested (mobile, tablet, desktop)
- [ ] Dark mode support (if applicable)

### Integration Quality Gates (Phase 3)

- [ ] E2E tests pass in headless mode
- [ ] No flaky tests (run multiple times)
- [ ] Performance benchmarks achieved
- [ ] Accessibility audit passes (axe scan)
- [ ] Manual keyboard navigation successful
- [ ] Error scenarios tested end-to-end
- [ ] URL state persists across refresh
- [ ] Browser back/forward works correctly

### Documentation Quality Gates (Phase 4)

- [ ] All endpoints documented in OpenAPI
- [ ] Example requests/responses valid and testable
- [ ] User guide covers all features
- [ ] Keyboard shortcuts documented
- [ ] README updated
- [ ] ADR approved and archived
- [ ] No broken links in documentation
- [ ] Screenshots/GIFs show actual feature

---

## Deployment Checklist

- [ ] Feature flag: request_log_viewer_enabled = false (initially)
- [ ] Environment variables documented
- [ ] Database migrations (if any) applied
- [ ] API tests pass in staging
- [ ] Frontend E2E tests pass in staging
- [ ] Performance benchmarks met in staging
- [ ] Monitoring/alerting configured
- [ ] Rollback procedure documented and tested
- [ ] Team trained on feature and support process
- [ ] Beta user group identified
- [ ] Launch communication sent to users

---

## File References

### Backend Files Created
- `skillmeat/core/request_log_manager.py` (RequestLogManager class)
- `skillmeat/api/routers/request_logs.py` (API endpoints)
- `skillmeat/api/schemas/request_logs.py` (Pydantic DTOs)
- `skillmeat/api/tests/test_request_logs_routes.py` (API tests)

### Frontend Files Created
- `skillmeat/web/app/projects/[id]/request-logs/page.tsx` (Server component)
- `skillmeat/web/app/projects/[id]/request-logs/layout.tsx` (Layout)
- `skillmeat/web/components/request-logs/request-log-table.tsx` (Table component)
- `skillmeat/web/components/request-logs/request-log-filters.tsx` (Filters component)
- `skillmeat/web/components/request-logs/request-log-search.tsx` (Search component)
- `skillmeat/web/components/request-logs/request-log-modal.tsx` (Modal component)
- `skillmeat/web/hooks/useRequestLogs.ts` (Custom TanStack Query hooks)
- `skillmeat/web/__tests__/request-logs.test.tsx` (Unit tests)
- `skillmeat/web/tests/request-logs-e2e.spec.ts` (E2E tests)

### Documentation Files Created
- `docs/features/request-log-viewer.md` (User guide)
- `docs/api/request-logs-endpoints.md` (API documentation)
- `.claude/context/adrs/request-log-viewer-subprocess-integration.md` (ADR)

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-01-30
**Status**: Ready for Execution
**Track**: Standard (Haiku + Sonnet agents with Opus for complex tasks)
