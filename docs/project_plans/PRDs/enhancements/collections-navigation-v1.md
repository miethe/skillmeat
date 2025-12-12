---
title: "PRD: Collections & Site Navigation Enhancement"
description: "Restructure navigation and artifact management with Collections-centric UX, custom grouping, and deployment dashboard"
audience: [ai-agents, developers]
tags: [prd, planning, enhancement, navigation, collections, groups, deployment, ux]
created: 2025-12-12
updated: 2025-12-12
category: "product-planning"
status: draft
related:
  - /docs/project_plans/implementation_plans/enhancements/collections-navigation-v1.md
---

# PRD: Collections & Site Navigation Enhancement

**Feature Name:** Collections & Site Navigation Enhancement

**Filepath Name:** `collections-navigation-v1`

**Date:** 2025-12-12

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Draft

**Complexity:** Large | **Estimated Effort:** 65 story points | **Timeline:** 6 weeks | **Priority:** High

---

## 1. Executive Summary

The SkillMeat web UI currently suffers from navigation confusion due to overlapping functionality between `/collection` and `/manage` pages. This enhancement restructures the entire navigation model to create a Collections-centric experience with clear, distinct purposes for each page.

**Primary Outcomes:**
- Single "Collections" parent navigation item with nested tabs (Manage, Projects, MCP Servers)
- Collections page becomes the unified artifact browsing interface with filtering, search, and custom grouping
- Groups system allows users to organize artifacts flexibly within collections
- /manage page repurposed as Deployment Dashboard for cross-project artifact deployment visibility
- Local artifact caching reduces API load and improves responsiveness
- Unified artifact modal enhanced with Collections/Groups and Deployments tabs

**Impact:**
- Eliminates navigation confusion
- Supports flexible artifact organization at scale
- Provides visibility into artifact deployment status
- Improves performance through intelligent caching

---

## 2. Context & Background

### Current State

**What Exists Today:**

1. **Dual Pages Problem:**
   - `/collection` page: Displays artifacts with Grid/List view modes
   - `/manage` page: Also displays artifacts with nearly identical functionality
   - Users unsure which page to use for browsing vs. managing
   - Overlap causes confusion and duplicated feature requests

2. **Navigation Structure:**
   - Sidebar tabs: Dashboard, Collections, Manage, Projects, MCP Servers
   - "Collections" tab leads to `/collection` page
   - "Manage" tab leads to `/manage` page
   - No hierarchical relationship between related pages

3. **Artifact Organization:**
   - Artifacts stored in user's collection (manifest-based)
   - No support for custom grouping within collections
   - No cross-collection organization view
   - Difficult to organize large artifact sets

4. **Deployment Visibility:**
   - No dedicated view for deployment status
   - Artifacts lack deployment information
   - Users cannot easily see which projects have which artifacts deployed

5. **Caching:**
   - No local artifact cache
   - All requests hit API
   - Slow load times for large collections
   - No offline capability

### Problem Space

**Pain Points:**

1. **Navigation Confusion**
   - "Collections" vs. "Manage" pages serve similar purposes
   - Users don't know which to use
   - Support requests for clarification

2. **Poor Organization**
   - No way to group artifacts within a collection
   - Large collections become unnavigable
   - No metadata-based filtering or grouping

3. **Missing Deployment Context**
   - Cannot see deployment status in collection view
   - Unclear which projects have which artifacts
   - No unified deployment management interface

4. **Performance**
   - No caching leads to slow page loads
   - Repeated API calls for same data
   - Poor UX on slower connections

### Architectural Context

**Frontend Stack:**
- Next.js 15 App Router
- React 19 with hooks
- TypeScript strict mode
- Radix UI + shadcn components
- TanStack Query v5 for server state
- Local storage for client persistence

**Backend Stack:**
- FastAPI with SQLAlchemy ORM
- SQLite database with WAL mode
- Alembic for migrations
- Pydantic for schema validation

**Existing API Surface:**
- `/api/v1/artifacts` - Artifact CRUD
- `/api/v1/artifacts/discover` - Discovery endpoints
- Deployment data currently scattered (CLI-focused)

---

## 3. Problem Statement

**Core Gap:** Users experience navigation confusion due to overlapping `/collection` and `/manage` page functionality, lack artifact organization tools, and no visibility into deployment status. There is also no support for managing multiple collections or intelligent caching.

**User Stories:**

> "As a user with 100+ artifacts, I want to create custom groups within my collection (e.g., 'AI Skills', 'Data Tools', 'Automation') so I can navigate and organize artifacts by functionality rather than scrolling through a flat list."

> "As a user managing multiple projects, I want to see which artifacts are deployed to which projects, their deployment status, and latest version info from a single Deployment Dashboard, so I can quickly identify version mismatches and updates needed."

> "As a user new to SkillMeat, I want a clear navigation structure where 'Collections' is the main entry point with sub-sections for different concerns (Manage, Projects, MCP Servers), so I'm not confused about where to go for different tasks."

> "As a user with a slow internet connection, I want artifacts cached locally on startup so the app loads quickly, and I want a manual refresh button to sync changes without waiting for a background refresh."

---

## 4. Goals & Success Metrics

### Goals

**G1: Clear Navigation Structure**
- Single "Collections" parent item in sidebar with nested tabs
- Each tab has distinct, non-overlapping purpose
- Users understand which page to use for each task

**G2: Flexible Artifact Organization**
- Users can create, rename, delete groups within collections
- Artifacts can belong to multiple groups
- Drag-and-drop reordering between groups
- "Grouped View" option on collection page

**G3: Multi-Collection Support**
- Users can create, manage, and switch between collections
- Move/copy artifacts between collections easily
- "All Collections" view to see artifacts across all collections

**G4: Deployment Visibility**
- Dedicated Deployment Dashboard (/manage repurposed)
- Quick overview of deployment status per artifact
- Per-project deployment details in unified modal
- Filter deployments by status, project, version

**G5: Performance & Responsiveness**
- Collection page loads < 1 second (with cache)
- Background refresh completes in < 5 seconds
- No blocking UI during cache operations
- Persistent cache across app restarts

**G6: User Experience**
- Unified artifact modal with Collections/Groups and Deployments tabs
- Artifact card ellipsis menu with key actions
- No confusion between page purposes
- Intuitive drag-and-drop for group organization

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Page Load Time (Collection) | < 1s (cached) | Lighthouse, browser DevTools |
| API Call Reduction | 80% fewer calls | Network tab comparison |
| Feature Adoption | 90% within 2 weeks | Analytics, usage tracking |
| User Satisfaction | > 4/5 stars | Post-launch survey |
| Test Coverage | > 85% backend, > 80% frontend | Coverage reports |
| Critical Bugs | 0 in first week | Bug tracking system |

---

## 5. User Stories

### Epic 1: Navigation Restructuring (Phase 1)

| ID | Title | Acceptance Criteria |
|---|---|---|
| US-1.1 | Restructure sidebar with Collections parent | Parent "Collections" item collapses/expands; nested tabs (Manage, Projects, MCP) properly indented; state persists across page reloads |
| US-1.2 | Update routes for nested navigation | Routes properly scoped; back button works correctly; deep linking to /collections/manage supported |

### Epic 2: Collection Page Enhancement (Phase 2)

| ID | Title | Acceptance Criteria |
|---|---|---|
| US-2.1 | Collection switcher dropdown | Dropdown shows all user collections; can switch between collections; "Add Collection" button opens create dialog; "All Collections" option shows aggregated view |
| US-2.2 | View mode toggle (Grid/List/Grouped) | All three modes functional; toggle persists user preference; switching modes doesn't lose filters |
| US-2.3 | Filtering and search | Text search works across artifact name/description; filter by artifact type; combine multiple filters; clear all filters button |

### Epic 3: Custom Groups (Phase 3)

| ID | Title | Acceptance Criteria |
|---|---|---|
| US-3.1 | Create/rename/delete groups | "Manage Groups" dialog opens from card or modal; can add new group; can rename group; can delete group; confirmation required for delete |
| US-3.2 | Grouped view | Grouped view mode shows artifacts organized by groups; empty groups shown; drag-drop artifacts between groups; drop feedback (hover, highlighting) clear |
| US-3.3 | Artifact-group membership | Artifact can belong to 0+ groups; checkboxes in Manage Groups dialog; changes save to backend; UI updates optimistically |

### Epic 4: Deployment Dashboard (Phase 4)

| ID | Title | Acceptance Criteria |
|---|---|---|
| US-4.1 | Repurpose /manage as Deployment Dashboard | /manage page shows deployment-focused view; deployment status prominent; version mismatch alerts visible |
| US-4.2 | Deployment cards with quick actions | Cards show deployment count, active/inactive status; "Deploy to New Project" quick action; "View Deployments" opens modal; filters work (status, project, version) |
| US-4.3 | Deployments tab in unified modal | New "Deployments" tab shows all projects artifact is deployed to; per-project version info; deployment status; last updated timestamp |

### Epic 5: Multiple Collections (Phase 5)

| ID | Title | Acceptance Criteria |
|---|---|---|
| US-5.1 | Collection CRUD operations | Users can create new collection (dialog); rename collection (inline or dialog); delete collection (confirmation); validation on name (required, unique) |
| US-5.2 | Move/copy artifacts between collections | Dialog shows checkboxes for target collections; "Move" button moves artifact; "Copy" button duplicates artifact; confirmation dialog with summary |
| US-5.3 | Bulk operations | Multi-select artifacts; bulk move/copy to collection; bulk delete with confirmation |

### Epic 6: Artifact Card Enhancements (Phase 5)

| ID | Title | Acceptance Criteria |
|---|---|---|
| US-6.1 | Ellipsis menu on hover | Menu appears on card hover (bottom right); contains 4 options; each option functional; closes on click-outside |
| US-6.2 | Menu actions | "Move/Copy to Collections" opens dialog; "Manage Groups" opens dialog; "Edit" opens modal to Edit Parameters tab; "Delete" opens confirmation dialog |

### Epic 7: Unified Modal Enhancement (Phase 5)

| ID | Title | Acceptance Criteria |
|---|---|---|
| US-7.1 | Collections/Groups tab | New tab shows hierarchical view: Collections → Groups; empty state if no groups; "Manage Groups" and "Move/Copy" buttons present |
| US-7.2 | Tab integration | Tabs switch cleanly; no data loss; modal state preserved when switching tabs |

### Epic 8: Caching & Performance (Phase 6)

| ID | Title | Acceptance Criteria |
|---|---|---|
| US-8.1 | Local artifact cache | On app startup, artifacts pulled and cached; SQLite cache persists data; manual "Refresh" button triggers sync; cache survives app restart |
| US-8.2 | Background refresh | Periodic background refresh every 5-10 minutes; doesn't block UI; shows subtle "Syncing..." indicator; updates UI when new data arrives |
| US-8.3 | Cache invalidation | Mutations (create, update, delete) invalidate cache immediately; UI updates optimistically; no stale data shown |

---

## 6. Functional Requirements

### 6.1 Navigation Restructuring

**FR-NAV-1: Sidebar Structure**
- Parent item "Collections" (always visible) expands to show 3 nested tabs: Manage, Projects, MCP Servers
- State persists in localStorage as `sidebar.collections_expanded`
- Nested items indented 20px from parent
- Active tab highlighted with sidebar color

**FR-NAV-2: Routing**
- `/collections` → Collection page (default view)
- `/collections/manage` → Deployment Dashboard
- `/collections/projects` → Projects page
- `/collections/mcp-servers` → MCP Servers page
- Back button and breadcrumbs work correctly throughout

**FR-NAV-3: Mobile Responsiveness**
- Sidebar collapses to icon-only on screens < 768px
- Nested tabs hidden when collapsed
- Toggle to expand/collapse available

### 6.2 Collection Page Enhancement

**FR-COLL-1: Collection Switcher**
- Dropdown at page top, inline with title
- Shows: [Current Collection ▼]
- On click, shows list of all collections (alphabetically sorted)
- Each option clickable to switch
- "All Collections" option at bottom (aggregates all artifacts)
- "Add Collection" option with plus icon at bottom

**FR-COLL-2: View Modes**
- Three toggle options: Grid | List | Grouped
- Default: Grid
- User preference persisted in localStorage as `ui.collection_view_mode`
- Switching modes doesn't lose current filters or search

**FR-COLL-3: Filtering & Search**
- Search box: text input, real-time filter on artifact name/description
- Filter buttons: by artifact type (Skill, Command, Agent, MCP, Hook)
- Applied filters shown as removable chips
- "Clear all" button to reset
- No more than 500ms filter latency

**FR-COLL-4: Artifact Display**
- Grid view: 3-column responsive layout, cards 300px wide
- List view: full-width table with name, type, created date, last modified
- Grouped view: sections by group name, cards within each group
- All views support drag-select for multi-select
- Sort options: name (A-Z), recently modified, type

**FR-COLL-5: Artifact Cards**
- Display: artifact name, type badge, description (truncated), creation date
- Ellipsis menu (⋯) bottom-right corner, appears on hover
- Ellipsis menu options: Move/Copy to Collections | Manage Groups | Edit | Delete
- Click card to open unified artifact modal
- Show group membership as small tags on card

### 6.3 Custom Groups

**FR-GRP-1: Group CRUD**
- "Manage Groups" button on collection header or via card/modal menu
- Dialog shows list of existing groups with delete (trash icon) for each
- "Add Group" button to create new group
- Input validation: group name required, unique within collection, max 50 chars
- Confirmation before delete: "Delete group 'X'? Artifacts remain in collection."

**FR-GRP-2: Grouped View**
- Displays groups as collapsible sections (title as header)
- Each section shows artifacts as cards
- Empty groups shown with "No artifacts in this group" message
- Groups can be reordered via drag-drop on header
- Total artifact count shown in group header

**FR-GRP-3: Artifact-Group Assignment**
- "Manage Groups" dialog shows checkboxes for all groups
- Checkboxes pre-filled based on current membership
- Artifacts can belong to 0 or multiple groups
- Changes save immediately on toggle
- Optimistic UI update (checkbox immediately changes)

**FR-GRP-4: Drag-and-Drop**
- Grouped view supports drag artifact between groups
- Drag feedback: visual highlight on group header (drop zone)
- Smooth drag animation (use Radix/Framer Motion)
- Keyboard accessible: Tab to group, Enter to toggle open/close, arrow keys to reorder

### 6.4 Deployment Dashboard

**FR-DEPLOY-1: /manage Page Repurposing**
- /manage route now shows Deployment Dashboard (not generic manage page)
- Header: "Deployment Dashboard"
- Description: "Cross-project deployment status and version information"
- Accessible via sidebar "Manage" tab under Collections

**FR-DEPLOY-2: Deployment View**
- Cards layout (similar to collection page) showing artifacts
- Each card displays:
  - Artifact name, type, description
  - Deployment count (e.g., "Deployed to 3 projects")
  - Status indicator: Active | Inactive | Version Mismatch (color-coded)
  - Quick action buttons: "Deploy to New Project" | "View Deployments"
- Filter by: Status (Active/Inactive/Mismatch), Project, Version

**FR-DEPLOY-3: Quick Actions**
- "Deploy to New Project": Opens project selector dialog, shows available projects, selects target, creates deployment
- "View Deployments": Opens unified modal to "Deployments" tab showing all projects
- Actions maintain consistent styling with artifact card menu

**FR-DEPLOY-4: Deployment Modal Tab**
- New "Deployments" tab in unified artifact modal
- Shows table: Project | Deployed Version | Latest Version | Status | Last Updated
- Status column: Active (green) | Inactive (gray) | Update Available (yellow)
- Click row to view detailed deployment info
- Quick action: Update to Latest button for mismatches

### 6.5 Multiple Collections Management

**FR-MCOLL-1: Collection CRUD**
- Collection creation: "Add Collection" button → dialog with name input (required, unique, max 50 chars)
- Collection rename: Right-click collection in switcher dropdown → "Rename" or pencil icon
- Collection delete: Right-click → "Delete" with confirmation (warns if artifacts in collection)
- Default collection created on first use (name: "My Collection")

**FR-MCOLL-2: Move/Copy Artifacts**
- Dialog title: "Move/Copy Artifact to Collections"
- Shows checkboxes for all available collections
- Buttons at bottom: "Move" | "Copy" | "Cancel"
- "Move": Removes from current, adds to selected collections
- "Copy": Adds to selected (keeps in current)
- Confirmation summary: "Moving 'Skill X' to 2 collections"

**FR-MCOLL-3: Bulk Operations**
- Multi-select artifacts via checkboxes (left side of cards)
- Bulk action bar shows selected count: "5 artifacts selected"
- Bulk move/copy option in action bar
- Same dialog as single artifact but applies to all selected

**FR-MCOLL-4: All Collections View**
- Switcher option "All Collections" shows artifacts from all collections
- Sorting and filtering still available
- Drag-to-move artifacts between collections (visual feedback shows target collection)
- Artifact card shows which collection(s) it belongs to

### 6.6 Artifact Card Enhancements

**FR-CARD-1: Ellipsis Menu**
- Menu icon (⋯) positioned bottom-right of card
- Visible on card hover (desktop) or always visible (mobile)
- Menu items: Move/Copy to Collections | Manage Groups | Edit | Delete
- Menu dismisses on click-outside or Escape key
- Dark background with smooth open animation

**FR-CARD-2: Menu Actions**
- Move/Copy: Opens dialog (FR-MCOLL-2)
- Manage Groups: Opens dialog (FR-GRP-1)
- Edit: Opens unified modal to "Edit Parameters" tab
- Delete: Opens confirmation dialog "Delete 'Artifact X'?" with destructive button styling

**FR-CARD-3: Group Membership Display**
- If artifact in groups, show small group tag(s) below artifact description
- Tags show first 2 groups, "+X more" if more than 2
- Tags not clickable but show full list on hover tooltip

### 6.7 Unified Artifact Modal Enhancement

**FR-MODAL-1: Collections/Groups Tab**
- New tab "Collections/Groups" alongside existing tabs
- Hierarchical display:
  - Collection name (header)
    - Group 1, Group 2, ... (list or tags)
    - "Not in any group" if no groups
  - Collection name (header)
    - Groups...
- Show "Manage Groups" button for each collection
- Show "Move/Copy to Collections" button at bottom of modal

**FR-MODAL-2: Tab Integration**
- No data loss when switching tabs
- Modal scrolls to top when tab changes (unless user scrolled)
- Tab icons: Overview | Collections/Groups | Deployments | Parameters
- All existing tabs continue to work unchanged

### 6.8 Caching & Performance

**FR-CACHE-1: Startup Cache**
- On app mount (RootLayout or AppProvider), call `useCacheArtifacts()`
- Fetch all artifacts from API and manifest
- Store in SQLite local cache (table: `artifacts_cache`)
- Schema: id, name, type, description, source, created_at, updated_at, created_by, cached_at
- Display skeleton loaders while fetching (max 2-3 seconds)

**FR-CACHE-2: Background Refresh**
- Setup periodic refresh every 5-10 minutes using `useEffect` cleanup
- Refresh silently in background (no blocking)
- Show subtle "Syncing..." indicator in header (small spinner icon)
- On completion, silently update cache and UI (no toast unless error)
- Fallback: Show toast only if refresh fails

**FR-CACHE-3: Manual Refresh**
- "Refresh" button on collection page header (sync icon)
- On click: Button shows loading state (spinner)
- Fetches latest from API, updates cache
- Shows toast on success: "Collection refreshed"
- Shows error toast on failure with retry option

**FR-CACHE-4: Cache Persistence**
- SQLite database at `~/.skillmeat/web_cache.db`
- Schema versioning (migrations on startup)
- Cache survives app restarts
- Manual cache clear option in settings (Advanced section)

**FR-CACHE-5: Cache Invalidation**
- On artifact mutation (create, update, delete): immediately invalidate cache entry
- Optimistic UI updates (assume mutation succeeds)
- Rollback UI if mutation fails
- TanStack Query handles invalidation coordination

---

## 7. Non-Functional Requirements

### NFR-PERF-1: Performance

| Requirement | Target |
|---|---|
| Collection page initial load | < 1 second (with cache) |
| Grouped view rendering | < 500ms for 1000 artifacts |
| Drag-drop smoothness | 60 fps animations |
| Filter/search latency | < 300ms |
| Background refresh | < 5 seconds (non-blocking) |
| Cache size | < 50MB for 10K artifacts |

### NFR-ACCESS-1: Accessibility

- WCAG 2.1 AA compliance for all new components
- Drag-and-drop has keyboard alternative (arrow keys, Enter)
- Menu items keyboard accessible (Tab, Enter)
- Color not sole indicator of status (use icons + labels)
- Screen reader text for ellipsis menu button

### NFR-COMPAT-1: Browser Compatibility

- Chrome/Edge 120+
- Firefox 121+
- Safari 17+
- Mobile Safari iOS 17+
- No IE11 support

### NFR-MOBILE-1: Mobile Responsiveness

- Sidebar collapses on screens < 768px
- Cards responsive: 1 column on mobile, 2 on tablet, 3+ on desktop
- Touch-friendly targets: min 44px × 44px
- Modals full-screen on mobile
- Drag-drop not supported on mobile (fallback to checkbox multi-select)

### NFR-TYPE-1: Type Safety

- TypeScript strict mode throughout (no `any`)
- Pydantic models for all API requests/responses
- TanStack Query typed queries with `useQuery<T>`
- Zod schemas for runtime validation

### NFR-TEST-1: Testing

- Unit tests: > 85% backend, > 80% frontend
- Integration tests for each API endpoint
- E2E tests for critical user flows (5-10 tests minimum)
- Accessibility automated tests (axe-core)

### NFR-DOC-1: Documentation

- Inline code comments for complex logic
- JSDoc for React components and hooks
- OpenAPI/Swagger docs for new API endpoints
- User guide for collection management (Wiki or help docs)

---

## 8. Out of Scope

The following features are explicitly out of scope for v1.0 and may be addressed in future phases:

| Item | Reason |
|---|---|
| Artifact linting status indicators | Future phase (requires linter integration) |
| Shared collections (multi-user) | Requires user/permission system redesign |
| Collection templates | Can be added as enhancement after v1 stabilization |
| Smart grouping (auto-group by metadata) | Requires ML/tagging system |
| Collection versioning/snapshots | Requires additional storage architecture |
| Deployment scheduling | Requires job queue system |
| Collection export/import | Defer to post-launch improvement |
| Dark mode enhancement for Deployment Dashboard | Use existing theme system |

---

## 9. Implementation Approach

### Phased Rollout (6 Weeks, 65 Story Points)

**Phase 1: Database Layer (Week 1, 8 SP)**
- SQLAlchemy models: Collection, Group, CollectionArtifact, GroupArtifact
- Alembic migrations with forward/backward compatibility
- Indexes on frequently queried columns
- Assigned to: python-backend-engineer, data-layer-expert

**Phase 2: Backend API (Week 1.5, 12 SP)**
- FastAPI routers: /api/v1/collections, /api/v1/groups, /api/v1/deployments
- CRUD endpoints with proper error handling
- Association endpoints for artifact-collection and artifact-group links
- Assigned to: python-backend-engineer, backend-architect

**Phase 3: Frontend Foundation (Week 1.5, 10 SP)**
- TypeScript types for Collection, Group, Deployment
- Navigation restructuring (sidebar components)
- useCollections, useGroups, useDeployments hooks
- CollectionContext provider for shared state
- Assigned to: ui-engineer-enhanced, frontend-developer

**Phase 4: Collection Features (Week 1.5, 15 SP)**
- Collection page redesign with view modes and filters
- Collection switcher dropdown component
- Artifact cards with ellipsis menu
- Move/Copy Collections dialog
- Assigned to: ui-engineer-enhanced, frontend-developer

**Phase 5: Groups & Deployment (Week 1.5, 12 SP)**
- Grouped view implementation with drag-drop
- Manage Groups dialog
- Deployment Dashboard (/manage repurpose)
- Deployments tab in unified modal
- Collections/Groups tab in unified modal
- Assigned to: ui-engineer-enhanced, frontend-developer

**Phase 6: Caching & Polish (Week 1, 8 SP)**
- SQLite cache setup and migrations
- Startup artifact fetch and cache
- Background refresh logic (5-10 min intervals)
- Manual refresh button and UX
- Testing suite, documentation
- Assigned to: python-backend-engineer, ui-engineer-enhanced, testing-specialist

### Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Complex state management bugs | High | High | Implement CollectionContext early; thorough testing in Phase 3 |
| Database migration issues | Medium | High | Test migrations with sample data; rollback scripts prepared |
| UI/UX complexity | Medium | Medium | Iterative stakeholder validation; A/B test if needed |
| Performance degradation | Low | Medium | Pagination, indexing, caching from start; load testing |
| Drag-drop accessibility issues | Low | Medium | Keyboard alternative in Phase 5; axe testing |

---

## 10. Acceptance Criteria

### Global Acceptance Criteria (All Phases)

1. All user stories in Section 5 accepted by product manager
2. All functional requirements in Section 6 implemented and verified
3. All non-functional requirements in Section 7 met (performance, accessibility, type safety)
4. Code review approved by architects (backend-architect, ui-designer)
5. Test coverage: > 85% backend, > 80% frontend
6. Zero critical bugs in QA environment
7. Documentation complete (API docs, component stories, user guide)
8. E2E tests pass on Chrome, Firefox, Safari
9. Accessibility audit passes (WCAG 2.1 AA)
10. Stakeholder sign-off obtained

### Phase-Specific Acceptance Criteria

**Phase 1 (Database)**
- Models defined with proper relationships
- Migrations up/down tested with sample data
- Foreign key constraints enforced
- Indexes present on foreign keys and query columns
- No N+1 query issues in existing code

**Phase 2 (API)**
- All endpoints follow REST conventions
- Request/response schemas validated with Pydantic
- Error responses consistent (400, 404, 422, 500)
- CORS and auth middleware applied
- OpenAPI docs auto-generated and accurate

**Phase 3 (Frontend Foundation)**
- Sidebar navigation restructured
- TypeScript types strict (no `any`)
- Hooks properly implement React patterns
- Context provider memoized for performance
- TanStack Query configured with proper invalidation

**Phase 4 (Collection Features)**
- All view modes (Grid, List) functional
- Filtering and search < 300ms latency
- Collection switcher dropdown works across app
- Modals handle loading/error states properly
- Card menus accessible (keyboard + mouse)

**Phase 5 (Groups & Deployment)**
- Grouped view renders smoothly (60 fps)
- Drag-drop accessible (keyboard alternative)
- Deployment Dashboard shows accurate status
- Quick actions properly validated
- Modal tabs seamlessly integrated

**Phase 6 (Caching & Polish)**
- Cache startup data persists across restarts
- Background refresh doesn't block UI
- Manual refresh button reliable
- All tests pass (unit, integration, E2E)
- Documentation complete and reviewed

---

## 11. Dependencies & Prerequisites

### Technology Stack

| Component | Version | Purpose |
|---|---|---|
| FastAPI | 0.100+ | Backend API framework |
| SQLAlchemy | 2.0+ | ORM and query builder |
| Alembic | 1.12+ | Database migrations |
| Pydantic | 2.0+ | Schema validation |
| Next.js | 15+ | Frontend framework |
| React | 19+ | UI library |
| TypeScript | 5.3+ | Type safety |
| TanStack Query | 5.0+ | Server state management |
| Radix UI | 1.0+ | Component library |
| Tailwind CSS | 3.3+ | Styling |

### External Dependencies

- GitHub API (for future deployment status)
- SQLite 3.40+ (for local caching)

### Team Skills Required

- Full-stack TypeScript/Python expertise (at minimum one developer)
- React hook patterns and state management
- Database design and SQL optimization
- API design and REST conventions
- E2E testing with Playwright

### Prerequisites Met

- SkillMeat repo set up with development environment
- CI/CD pipeline working (GitHub Actions)
- Design system (Radix + shadcn) established
- Testing infrastructure (Jest, Playwright) in place
- Type safety standards enforced (TypeScript strict, mypy)

---

## 12. Success Metrics & Measurement Plan

### Functional Success

| Metric | Target | How to Measure |
|---|---|---|
| All 8 enhancement areas implemented | 100% | Feature checklist |
| User stories accepted | 100% of 15+ stories | Story sign-off |
| Acceptance criteria met | 100% | QA test matrix |
| Critical bugs in production | 0 | Bug tracking (first week) |
| Regression tests passing | 100% | Test report |

### Performance Success

| Metric | Target | How to Measure |
|---|---|---|
| Collection page load time | < 1s (cached) | Lighthouse, DevTools |
| API call reduction | 80% fewer | Network tab before/after |
| Drag-drop smoothness | 60 fps | Chrome DevTools Performance |
| Background refresh latency | < 5s | Browser console timings |
| Mobile responsiveness | 95+ Lighthouse score | Lighthouse audit |

### User Success

| Metric | Target | How to Measure |
|---|---|---|
| Feature adoption | 90% within 2 weeks | Google Analytics events |
| User satisfaction | > 4/5 stars | Post-launch survey |
| Support tickets (navigation) | 90% reduction | Support ticket analysis |
| Time-to-deploy artifacts | 30% faster | Usage analytics |
| Collection abandonment | < 5% | Feature engagement |

### Code Quality

| Metric | Target | How to Measure |
|---|---|---|
| Test coverage (backend) | > 85% | Coverage reports |
| Test coverage (frontend) | > 80% | Coverage reports |
| Accessibility score | 95+ (Lighthouse) | Accessibility audit |
| Type safety | 100% strict | TypeScript compiler |
| Code review approval | 2+ reviewers | GitHub PR reviews |

---

## 13. Assumptions & Open Questions

### Assumptions

1. **Database**: SQLite with WAL mode sufficient for local caching; no PostgreSQL needed for MVP
2. **Artifacts**: All artifacts from manifest and API can fit in SQLite cache (< 50MB for typical usage)
3. **Deployments**: Deployment data can be derived from existing project/artifact relationship in backend
4. **Groups**: No permission system needed; all groups visible to user who owns collection
5. **Collections**: Single user per app instance (no multi-user sharing in v1)
6. **Caching**: 5-10 minute background refresh cadence is acceptable (not real-time)
7. **Mobile**: Drag-drop not required on mobile (checkbox alternative sufficient)

### Open Questions

1. **Collection Ownership**: Should collections have per-collection permissions or are all collections visible to the current user?
   - *Answer to clarify with stakeholders*

2. **Deployment Data Source**: Should deployment status pull from CLI deployments (manifest), GitHub repos, or a separate deployment table?
   - *Answer to clarify with backend team*

3. **Artifact Metadata**: Should groups support description/color tagging for organization hierarchy?
   - *Answer: Defer to v1.1; use simple text groups for v1*

4. **Caching Strategy**: Should we implement push-based cache invalidation (WebSocket) or stick with periodic polling?
   - *Answer: Polling for v1 (simpler); WebSocket in v2 if needed*

5. **Mobile Drag-Drop**: Should we implement touch gesture for group reordering or checkbox-only for v1?
   - *Answer: Checkbox-only for v1; touch gestures in v1.1*

---

## 14. Documentation Plan

### For Developers

- **API Documentation**: OpenAPI/Swagger auto-generated from FastAPI; include example requests/responses
- **Database Schema**: Entity-relationship diagram (ERD) in docs with table descriptions
- **React Components**: Storybook stories for Card, Modal, Sidebar components (optional but recommended)
- **Hooks & Utilities**: JSDoc comments with usage examples

### For Users

- **User Guide**: "Managing Collections & Groups" section in help docs
- **Video Tutorial**: 3-5 minute screen recording (optional for launch)
- **Migration Guide**: How to transition from old /collection → /manage flow

### For Operations

- **Deployment Checklist**: Steps to deploy phases (database migration, API rollout, frontend rollout)
- **Troubleshooting**: Common issues (cache corruption, migration rollback)
- **Performance Tuning**: Database indexing, cache optimization

---

## 15. Related Documents

- [Implementation Plan](collections-navigation-v1.md) - Detailed phased breakdown
- [Collections Navigation Enhancement Ideas](../ideas/enhancements-12-12-Collections-Nav.md) - Original enhancement brief
- [SkillMeat Architecture](../../architecture/overview.md) - System architecture
- [Design System & Tokens](../../design/design-tokens.md) - Radix + shadcn guidance
- [API Documentation](../../../api/docs/openapi.json) - Current API surface

---

## 16. Change Log

| Date | Author | Change |
|---|---|---|
| 2025-12-12 | Claude Code (AI Agent) | Initial PRD created from enhancement doc and implementation plan |

---

## 17. Appendix: Detailed Acceptance Criteria by Area

### Area 1: Navigation Restructuring

**AC-1.1:** Sidebar shows "Collections" parent item
- [ ] Parent item labeled "Collections"
- [ ] Expands/collapses with arrow icon
- [ ] Expansion state persists in localStorage
- [ ] Nested items visible when expanded

**AC-1.2:** Nested tabs functional
- [ ] Manage tab routes to `/collections/manage`
- [ ] Projects tab routes to `/collections/projects`
- [ ] MCP Servers tab routes to `/collections/mcp-servers`
- [ ] Active tab highlighted
- [ ] All pages load correctly

**AC-1.3:** Navigation doesn't confuse users
- [ ] Sidebar hierarchy clear (parent → children)
- [ ] Each tab has distinct heading
- [ ] Back button works throughout
- [ ] Deep linking supported (share URLs)

### Area 2: Collection Page Enhancement

**AC-2.1:** Collection switcher operational
- [ ] Dropdown shows all user's collections
- [ ] Clicking collection switches view
- [ ] "All Collections" option shows aggregated artifacts
- [ ] "Add Collection" button opens create dialog
- [ ] Current collection persists in localStorage

**AC-2.2:** View modes work
- [ ] Grid view: 3-column responsive layout
- [ ] List view: table with sortable columns
- [ ] Grouped view: sections by group
- [ ] Switching modes preserves filters/search
- [ ] User preference persists

**AC-2.3:** Filtering functional
- [ ] Text search filters artifacts in < 300ms
- [ ] Type filter works (Skill, Command, Agent, MCP, Hook)
- [ ] Applied filters shown as removable chips
- [ ] "Clear all" button resets
- [ ] Filters persist in URL (optional: improve UX)

### Area 3: Custom Groups

**AC-3.1:** Groups CRUD works
- [ ] "Manage Groups" dialog opens from card/modal
- [ ] Can create group (input, validation, submit)
- [ ] Can rename group (edit, validation, save)
- [ ] Can delete group (confirmation)
- [ ] Changes persist in database

**AC-3.2:** Grouped view renders
- [ ] Groups shown as collapsible sections
- [ ] Artifacts displayed as cards within groups
- [ ] Empty groups shown with placeholder
- [ ] Group count/artifact count shown
- [ ] Scrolling works smoothly

**AC-3.3:** Drag-drop between groups works
- [ ] Can drag artifact card between groups
- [ ] Drop zone highlights on drag-over
- [ ] On drop, artifact moves to target group
- [ ] Database updates immediately
- [ ] UI updates optimistically

### Area 4: Deployment Dashboard

**AC-4.1:** /manage repurposed correctly
- [ ] /manage route shows deployment-focused view
- [ ] Page title is "Deployment Dashboard"
- [ ] Deployment info prominent on cards
- [ ] Sidebar "Manage" tab active

**AC-4.2:** Cards show deployment status
- [ ] Each artifact card shows deployment count
- [ ] Status indicator (Active/Inactive/Mismatch) visible
- [ ] Quick action buttons present
- [ ] Filtering works (status, project, version)

**AC-4.3:** Quick actions functional
- [ ] "Deploy to New Project" button opens dialog
- [ ] "View Deployments" button opens modal
- [ ] Dialog/modal shows deployment details
- [ ] Actions save to database

### Area 5: Multiple Collections

**AC-5.1:** Collection management works
- [ ] Create collection: dialog, validation, persists
- [ ] Rename collection: in-place or dialog, validation, persists
- [ ] Delete collection: confirmation, persists
- [ ] Default collection created on first use

**AC-5.2:** Move/copy functional
- [ ] Dialog shows checkboxes for collections
- [ ] "Move" button moves artifact
- [ ] "Copy" button duplicates artifact
- [ ] Confirmation summary accurate
- [ ] Database updates correctly

### Area 6: Artifact Card Enhancements

**AC-6.1:** Ellipsis menu appears
- [ ] Menu icon visible on card hover (desktop)
- [ ] Menu icon visible on mobile
- [ ] Click opens menu
- [ ] Menu closes on click-outside
- [ ] Menu items correct (4 options)

**AC-6.2:** Menu actions work
- [ ] "Move/Copy to Collections" → opens dialog
- [ ] "Manage Groups" → opens dialog
- [ ] "Edit" → opens modal to Edit Parameters
- [ ] "Delete" → opens confirmation dialog

### Area 7: Unified Modal Enhancement

**AC-7.1:** Collections/Groups tab present
- [ ] Tab exists and is labeled correctly
- [ ] Tab shows Collections → Groups hierarchy
- [ ] Tab shows "Manage Groups" button
- [ ] Tab shows "Move/Copy" button
- [ ] Tab content updates when modal opens

**AC-7.2:** Tab integration smooth
- [ ] Tabs switch without data loss
- [ ] Modal state (scroll, form data) preserved
- [ ] Close/save buttons work correctly
- [ ] All existing tabs continue to function

### Area 8: Caching

**AC-8.1:** Startup cache functional
- [ ] On app startup, artifacts fetched
- [ ] Data cached in SQLite
- [ ] Cache persists across restarts
- [ ] Collection page loads < 1s with cache
- [ ] Manual refresh syncs latest

**AC-8.2:** Background refresh works
- [ ] Refresh occurs every 5-10 minutes
- [ ] Doesn't block UI
- [ ] Shows subtle "Syncing..." indicator
- [ ] Updates UI with new data
- [ ] Only shows toast on error

**AC-8.3:** Cache invalidation correct
- [ ] Mutations invalidate cache
- [ ] UI updates optimistically
- [ ] No stale data displayed
- [ ] Rollback on API error

---

**Document Status:** Ready for development team handoff

**Next Steps:**
1. Schedule kickoff with Phase 1 team (database layer experts)
2. Create phase-specific task breakdowns
3. Set up progress tracking (artifact-tracker)
4. Establish code review process per phase
