---
title: 'PRD: Collections & Groups UX Enhancement'
description: Add visual indicators for Collections and Groups on artifact cards, implement
  Groups sidebar navigation, and add Group filtering across collection views
audience:
- ai-agents
- developers
tags:
- prd
- planning
- enhancement
- ux
- collections
- groups
- cards
- filtering
created: 2026-01-19
updated: 2026-01-19
category: product-planning
status: inferred_complete
related: []
---
# PRD: Collections & Groups UX Enhancement

**Feature Name:** Collections & Groups UX Enhancement

**Filepath Name:** `collections-groups-ux-enhancement-v1`

**Date:** 2026-01-19

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Draft

**Complexity:** Large | **Estimated Effort:** 55 story points | **Timeline:** 4-5 weeks | **Priority:** High

---

## 1. Executive Summary

The SkillMeat web application has robust Groups infrastructure (CRUD APIs, types, and management endpoints), but the UX surface is incomplete. This enhancement adds four interconnected components to expose Groups functionality and improve artifact discoverability across Collections.

**Primary Outcomes:**

1. **Collection badges on cards** — When viewing "All Collections," cards show non-default Collection membership with visual badges
2. **Group badges on cards** — When viewing a specific Collection, cards show Group membership within that collection with visual badges
3. **Groups section in modal** — The Collections tab in UnifiedEntityModal displays Groups the artifact belongs to within each collection
4. **Groups sidebar page** — New "Groups" tab under Collections navigation; displays all Groups in the selected Collection with per-Group artifact grids
5. **Group filter** — Add Group dropdown filter to /collection and /manage pages; hidden when viewing "All Collections" to prevent cross-collection group naming conflicts

**Impact:**

- Artifacts become discoverable by Collection and Group membership without modal drill-down
- Groups feature transitions from backend-only to user-facing functionality
- Reduces cognitive load for users managing large artifact collections
- Supports flexible artifact organization and filtering strategies
- Improves Information Architecture by elevating Groups to sidebar prominence

---

## 2. Context & Background

### Current State

**What Exists Today:**

1. **Backend Groups Infrastructure (Complete):**
   - Full CRUD API endpoints for Groups (`/api/v1/groups/*`)
   - Groups have: id, collection_id, name, description, position, artifact_count
   - Artifacts can belong to multiple Groups within a Collection
   - API clients support: fetch, create, update, delete, reorder, copy, add/remove artifacts
   - Backend relationships: Collection → Group → Artifact (ordered positioning)
   - **Gap:** No API to list groups containing a specific artifact (artifact → groups lookup)
   - **Gap:** `/user-collections/{collection_id}/artifacts` does not support `group_id` filter or group membership data
   - **Gap:** `GET /groups/{id}` returns artifact IDs/positions only; there is no `GET /groups/{id}/artifacts`

2. **Frontend Types & API Client (Complete):**
   - Type definitions in `/web/types/groups.ts` (Group, GroupWithArtifacts, etc.)
   - API client in `/web/lib/api/groups.ts` with full CRUD support
   - Available functions: fetchGroups, fetchGroup, addArtifactToGroup, removeArtifactFromGroup, etc.

3. **Existing Card Components:**
   - UnifiedCard at `/web/components/shared/unified-card.tsx` — renders Entity or Artifact with type color bar
   - EntityCard wrapper at `/web/components/entity/entity-card.tsx` — selection checkbox, entity actions
   - Type indicator bar (colored left border) already established design pattern
   - Cards used on /collection, /manage, and future /groups pages

4. **Existing Filter & Navigation:**
   - Filters component at `/web/components/collection/filters.tsx` — Type, Status, Scope dropdowns + Sort
   - EntityFilters at `/web/app/manage/components/entity-filters.tsx` — Similar structure for /manage page
   - Navigation sidebar at `/web/components/navigation.tsx` — Collections section with Browse, Manage, Projects, MCP Servers
   - No Groups tab currently in sidebar

5. **Modal Collections Tab (Placeholder):**
   - ModalCollectionsTab at `/web/components/entity/modal-collections-tab.tsx` — shows collections but has comment at lines 197-198: "Groups within collection - Placeholder for Phase 5"
   - Ready for Groups display enhancement

### Problem Space

**Pain Points:**

1. **Invisible Group Membership** — Users must open modal → Collections tab to see which Groups an artifact belongs to; not visible on cards
2. **No Group-Based Discovery** — Cannot browse or filter by Group from main collection views; Group feature is "hidden"
3. **Inefficient Artifact Navigation** — Large collections with many Groups require multiple modal opens to understand organization; no sidebar entry point
4. **Inconsistent Card Metadata** — Cards show Type, Status, version but not Collection or Group context (when viewing across collections)
5. **Limited Filtering** — Type/Status/Scope filters exist but no Group filter; workaround requires modal drill-down

### Architectural Context

**Frontend Stack:**
- Next.js 15 App Router with server/client components
- React 19 with hooks
- TypeScript strict mode
- Radix UI + shadcn components (Button, Badge, Select, Popover, etc.)
- TanStack Query v5 for server state and caching
- Local storage for UI state persistence

**Backend Stack:**
- FastAPI with SQLAlchemy ORM
- Groups system fully implemented (schemas, routers, managers)
- Relationship model: Collection → Group (position-ordered) → Artifact (position-ordered)
- API supports: list, get, create, update, delete, reorder, copy, artifact CRUD within group

**Design System:**
- Colored type indicators (left border bar on cards)
- Badge component for metadata (collections, groups, counts)
- Select/Popover for filters
- Icon library (lucide-react)
- Tailwind CSS with shadcn theming

---

## 3. Problem Statement

**Core Gap:** Groups infrastructure exists on backend and in frontend types, but is invisible to users in the primary UX surfaces (/collection, /manage pages). Users cannot discover artifact organization by Group from card views, cannot filter by Group, and cannot navigate to Groups as a first-class sidebar feature. The modal Collections tab has a placeholder for Groups display.

**User Stories:**

> "As a user with 50+ artifacts organized in 5 Groups within a Collection (e.g., 'Data Tools', 'AI Skills', 'Automation'), I want to see which Group each artifact belongs to on the card so I can understand organization at a glance without opening a modal."

> "As a user managing multiple collections, I want to see on the card which Collection(s) an artifact belongs to when I'm viewing 'All Collections,' so I understand scope without opening modal details."

> "As a user, I want a dedicated Groups page in the sidebar navigation where I can select a Group and see only its artifacts, organized the same way as the Collections page, so I can browse Group-specific collections."

> "As a user, I want to filter artifacts by Group on /collection and /manage pages, so I can quickly find artifacts within a specific Group without scrolling or memorizing organization."

> "As a user, I want the Collections tab in the artifact modal to show which specific Groups contain the artifact within each collection, so I understand the full organizational hierarchy without guessing."

---

## 4. Goals & Success Metrics

### Goals

| Goal | Rationale |
|------|-----------|
| **Expose Group membership on cards** | Groups become first-class UI element, not hidden behind modal drill-down |
| **Enable Group-based filtering** | Users can quickly narrow down artifact lists by Group without modal interaction |
| **Add Groups to sidebar navigation** | Elevates Groups from organizational construct to navigable feature |
| **Display Groups in modal Collections tab** | Completes organizational context visibility for each artifact |
| **Maintain visual hierarchy** | Collection/Group badges don't overwhelm card design; consistent with type indicators |

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Groups sidebar navigation adoption** | 60%+ users visit /groups within 2 weeks of rollout | GA event: "groups_page_visited" |
| **Group filter usage** | 40%+ of collection view sessions use Group filter | GA event: "group_filter_applied" |
| **Modal Groups section engagement** | 50%+ of modal opens that show Groups have user interaction (view/edit) | GA event: "modal_groups_section_viewed" |
| **Card usability (NPS)** | +15 point improvement on "Card information is clear" survey question | Post-launch user survey |
| **Performance (page load)** | <200ms added latency for Groups data fetch | Real User Monitoring (RUM) |
| **Visual clutter (accessibility)** | Zero accessibility report tickets about badge density | Issue tracker review |

---

## 5. Requirements

### 5.1 Functional Requirements

#### Component 1: Collection Badges on Cards (All Collections View)

**Feature:** When viewing /collection with "All Collections" selected, UnifiedCard displays which Collections (excluding 'default') contain the artifact.

| Requirement | Details |
|-------------|---------|
| **Artifact scope** | Entity type must have a `collections` array (Array of {id, name}) |
| **Badge rendering** | Non-default collections shown as small badges (color: secondary, text: collection name) |
| **Badge position** | Top-right corner of card OR below type indicator bar (design TBD with UI engineer) |
| **Max badges** | Show up to 2 collection names; if 3+, show "X more..." badge |
| **Hover state** | On hover, tooltip shows full list of collections |
| **Styling** | Consistent Badge component from shadcn; no inline styles |
| **Accessibility** | Each badge has aria-label; keyboard navigable if clickable |
| **API dependency** | Entity.collections must be populated (already done in artifactToEntity conversion) |
| **Conditional render** | Hide if only in 'default' collection; hide if viewing specific collection (not "All Collections") |

**Location:** UnifiedCard component, within card metadata section

---

#### Component 2: Group Badges on Cards (Specific Collection View)

**Feature:** When viewing /collection or /manage with specific Collection selected, UnifiedCard displays which Groups contain the artifact within that collection.

| Requirement | Details |
|-------------|---------|
| **Artifact scope** | When in Collection context, Entity/Artifact must have groups array (will fetch via new hook) |
| **Badge rendering** | Groups shown as small badges (color: tertiary, text: group name) |
| **Badge position** | Below type indicator OR next to collection badges (coordinate with UI engineer) |
| **Max badges** | Show up to 2 group names; if 3+, show "X more..." badge |
| **Hover state** | Tooltip shows full list of groups in collection |
| **Conditional render** | Only render when viewing specific Collection (detected by useCollectionContext) |
| **Styling** | Consistent Badge component; distinct color from collection badges |
| **API dependency** | Prefer `include_groups=true` on `/user-collections/{collection_id}/artifacts` to avoid per-card fetch; modal can use `fetchArtifactGroups(artifactId, collectionId)` |
| **Caching** | Cache group lookups; avoid per-card calls in grid views |

**Location:** UnifiedCard component, within card metadata section (below collections badges if both present)

---

#### Component 3: Groups Section in Modal Collections Tab

**Feature:** When artifact modal is open, Collections tab shows Groups the artifact belongs to within each collection.

| Requirement | Details |
|-------------|---------|
| **Groups display** | Beneath each collection header, display groups as inline badges or list |
| **Empty state** | If no groups in collection, show "No groups" or omit section |
| **Badge styling** | Same as Component 2 (tertiary color) for consistency |
| **Group count** | Show count badge: "3 groups" OR list all groups if ≤3 |
| **Interaction** | Badge clickable to navigate to Groups page (future enhancement, not MVP) |
| **Location** | In ModalCollectionsTab component at lines 197-198 (placeholder location) |
| **API integration** | Use `fetchArtifactGroups(artifactId, collectionId)` (e.g., `GET /groups?collection_id=&artifact_id=`) |
| **Loading state** | Show skeleton while fetching groups |

**Location:** `/web/components/entity/modal-collections-tab.tsx` lines 197-198

---

#### Component 4: Groups Sidebar Page

**Feature:** New /groups page under Collections sidebar navigation allowing users to browse Groups and their artifacts.

| Sub-feature | Details |
|-------------|---------|
| **Sidebar entry** | New "Groups" tab item under Collections section in Navigation sidebar |
| **URL routing** | `/groups` page (new App Router page) |
| **Group selector** | Dropdown at top of page: "Select Group" → populated from `fetchGroups(selectedCollectionId)` |
| **Artifact grid** | Same ArtifactGrid/ArtifactList components as /collection page; data via `/user-collections/{collection_id}/artifacts?group_id=` |
| **View modes** | Support Grid and List view toggle (same UX as /collection page) |
| **Filtering** | Same Filters component as /collection (Type, Status, Scope, Sort) |
| **Empty state** | "No groups in collection" if Groups list is empty OR "Select a group" if dropdown not yet selected |
| **Breadcrumb** | Show: Dashboard > Collections > Groups | [Selected Group Name] |
| **Infinite scroll** | Use `useInfiniteCollectionArtifacts` or similar for artifact loading |
| **Performance** | Preload Groups list on page mount; lazy-load artifacts on group selection |

**Navigation Item:**
```typescript
{ name: 'Groups', href: '/groups', icon: FolderTree }  // or similar icon
```

**Location:**
- Sidebar: `/web/components/navigation.tsx` (Collections section, new item)
- Page: `/web/app/groups/page.tsx` (new file)
- Components: Reuse existing ArtifactGrid, Filters, view-mode toggle from /collection

---

#### Component 5: Group Filter on Collection/Manage Pages

**Feature:** Add Group dropdown filter to Filters and EntityFilters components; hidden when viewing "All Collections."

| Requirement | Details |
|-------------|---------|
| **Display condition** | Show only when Collection context exists AND not "All Collections" |
| **Filter options** | Populated from `fetchGroups(selectedCollectionId)` API call |
| **Default value** | "All Groups" (no filter applied) |
| **Behavior** | When selected, filter artifacts to show only those in that Group |
| **Filter state** | Stored in URL query params (e.g., `?group=group-id-123`) |
| **Reset** | Clicking "All Groups" clears filter |
| **Integration points** | Update Filters component AND EntityFilters component with identical UX |
| **Styling** | Match existing Select component pattern (Type, Status, Scope) |
| **API integration** | Filter logic in hook layer: conditionally add `groupId` to query params if filter set |

**Location:**
- `/web/components/collection/filters.tsx` (new Group Select dropdown)
- `/web/app/manage/components/entity-filters.tsx` (new Group Select dropdown)

---

### 5.2 Non-Functional Requirements

| Category | Requirement | Details |
|----------|-------------|---------|
| **Performance** | Page load latency | Groups data fetch ≤200ms; card render ≤50ms per card |
| **Performance** | API call reduction | Cache group lists per collection; reuse TanStack Query caching |
| **Accessibility** | WCAG 2.1 Level AA | All badges keyboard-navigable; proper aria-labels; color not sole indicator |
| **Responsive design** | Mobile/tablet support | Badges stack vertically on small screens; dropdowns remain usable |
| **Caching** | TanStack Query stale time | Groups list: 5 minutes (match artifact stale time); card groups: 10 minutes |
| **Error handling** | Failed group fetch | Show "—" placeholder; log error; do not block card render |
| **Backwards compatibility** | Legacy entities | Gracefully handle entities without collections/groups arrays (skip badge render) |
| **Type safety** | TypeScript strict mode | All new code in strict mode; no `any` types; full type inference |
| **Testing coverage** | Unit test coverage | ≥80% coverage for new components; snapshot tests for card badge sections |

---

### 5.3 Data Model & API Contracts

**Frontend Data Structures:**

```typescript
// Already exists in types/groups.ts
interface Group {
  id: string;
  collection_id: string;
  name: string;
  description?: string;
  position: number;
  artifact_count: number;
  created_at: string;
  updated_at: string;
}

// Already exists in types/artifact.ts
interface Artifact {
  id: string;
  name: string;
  // ... other fields
  collection?: { id: string; name: string };
  groups?: Array<{ id: string; name: string; position?: number }>;  // Populated when include_groups=true
  collections?: Array<{ id: string; name: string }>;  // All collections containing this artifact
}

// Already exists in types/entity.ts
interface Entity {
  id: string;
  name: string;
  // ... other fields
  collections?: Array<{ id: string; name: string }>;  // Used by artifactToEntity conversion
}
```

**API Endpoints (Already Implemented):**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /groups?collection_id={id}` | GET | Fetch all Groups in a Collection |
| `GET /groups/{id}` | GET | Fetch single Group with artifacts |
| `POST /groups` | POST | Create Group |
| `PUT /groups/{id}` | PUT | Update Group |
| `DELETE /groups/{id}` | DELETE | Delete Group |
| `POST /groups/{id}/artifacts` | POST | Add artifact(s) to Group |
| `DELETE /groups/{id}/artifacts/{artifact_id}` | DELETE | Remove artifact from Group |
| `GET /user-collections/{id}/artifacts` | GET | Paginated artifacts in collection (no group filter yet) |

**Note:** `GET /groups/{id}` returns artifact IDs/positions, not full artifact metadata.

**Client Functions (Already Implemented in lib/api/groups.ts):**

```typescript
fetchGroups(collectionId: string): Promise<Group[]>
fetchGroup(id: string): Promise<Group>
addArtifactToGroup(groupId: string, artifactIds: string[]): Promise<GroupWithArtifacts>
removeArtifactFromGroup(groupId: string, artifactId: string): Promise<void>
// ... others
```

**New Client Functions Needed / Enhancements:**

```typescript
// Fetch which groups an artifact belongs to within a collection
// Backed by: GET /groups?collection_id={id}&artifact_id={artifactId}
fetchArtifactGroups(artifactId: string, collectionId: string): Promise<Group[]>

// Fetch collection artifacts with optional group filter and group membership inclusion
fetchCollectionArtifactsPaginated(collectionId: string, {
  group_id?: string;
  include_groups?: boolean;
}): Promise<CollectionArtifactsPaginatedResponse>
```

---

## 6. Scope & Constraints

### In Scope

- [x] Collection badges on cards (All Collections view)
- [x] Group badges on cards (specific Collection view)
- [x] Groups section in modal Collections tab (display only, no edit/add)
- [x] Groups sidebar page with group selector and artifact grid
- [x] Group filter dropdown on /collection and /manage pages
- [x] Backend API enhancements for group membership and group_id filtering
- [x] Visual styling and accessibility compliance
- [x] Unit tests for new components and filter logic
- [x] TypeScript type safety for all new code

### Out of Scope (Future Enhancements)

- [ ] Drag-and-drop group management on Groups page
- [ ] Inline group creation from card context menu
- [ ] Group analytics (usage, artifact trends)
- [ ] Group-based permissions (access control)
- [ ] Bulk move artifacts to group
- [ ] Group search/filtering
- [ ] Deprecated: none

---

## 7. Dependencies & Integration Points

### External Dependencies

| Dependency | Version | Usage |
|------------|---------|-------|
| `react` | 19+ | Component hooks and JSX |
| `next` | 15+ | App Router, dynamic routes |
| `@tanstack/react-query` | 5+ | Server state, caching, mutations |
| `lucide-react` | latest | Icons (FolderTree, FolderOpen, etc.) |
| `radix-ui/react-select` | latest | Group selector dropdown |
| `shadcn/ui` | latest | Badge, Button, Select components |

### Internal Dependencies

| Component | File | Integration |
|-----------|------|-------------|
| UnifiedCard | `/components/shared/unified-card.tsx` | Add Collection/Group badge rendering |
| Filters | `/components/collection/filters.tsx` | Add Group filter dropdown |
| EntityFilters | `/app/manage/components/entity-filters.tsx` | Add Group filter dropdown |
| ModalCollectionsTab | `/components/entity/modal-collections-tab.tsx` | Add Groups display section |
| Navigation | `/components/navigation.tsx` | Add Groups tab to sidebar |
| useCollectionContext | `/hooks/index.ts` (barrel) | Determine current collection and view mode |
| ArtifactGrid | `/components/collection/artifact-grid.tsx` | Reused on /groups page |
| ArtifactFilters (concept) | Hook integration | Pass group filter to API queries |

### Hook Dependencies (New or Enhanced)

| Hook | Status | Purpose |
|------|--------|---------|
| `useGroups(collectionId)` | New | Fetch and cache groups for collection |
| `useArtifactGroups(artifactId, collectionId)` | New | Fetch groups for specific artifact in collection context |
| `useGroupFilter()` | New | Manage group filter state in URL and component |
| `useCollectionContext()` | Existing | Already provides selectedCollectionId and mode context |
| `useInfiniteCollectionArtifacts()` | Existing | Enhance with groupId filter parameter |

---

## 8. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| **Duplicate API calls** for groups per card | Medium | 100+ cards = N+1 queries | Implement useGroups hook with TanStack Query batching; cache groups by collection_id |
| **Card visual clutter** with multiple badges | Medium | Accessibility/usability issues | Design review with UI engineer; max 2-badge display with "X more..." fallback |
| **Group filter UX confusion** (when hidden) | Low | Users don't realize filter exists | Add tooltip/help text explaining "Group filter available in specific collection views" |
| **Stale group data** after CRUD operations | Medium | Users see outdated group lists | Implement invalidateQueries on group mutations; invalidate both group list and artifact group lists |
| **Performance regression** on /collection page | Medium | Slower perceived performance | Profile before/after; lazy-load group badges; separate API call with parallel fetch strategy |
| **Scope creep** on Groups page features | High | Timeline overrun | Strictly adhere to In-Scope list; defer drag-drop, bulk ops to Phase 2 |
| **Cross-browser compatibility** with Select/Popover | Low | Broken UX on older browsers | Shadcn components tested; verify Radix UI browser support |

---

## 9. Target State

### User Experience Flow

```
1. User lands on /collection with "All Collections" view
   ├─ Cards show Collection badges for non-default collections
   └─ No Group badges visible (not in specific collection context)

2. User clicks on specific Collection (e.g., "My AI Skills")
   ├─ Cards now show Group badges (e.g., "RAG Tools", "LLM Wrappers")
   ├─ New Group filter dropdown appears in Filters
   └─ User can filter by Group, or navigate to /groups

3. User clicks "Groups" in sidebar
   ├─ Lands on /groups page
   ├─ Sees dropdown: "Select Group" (populated with groups in current collection)
   ├─ Selects group → artifact grid updates with only that group's artifacts
   └─ Same Grid/List view, sort, Type/Status/Scope filters available

4. User clicks artifact card, opens modal
   ├─ Collections tab now shows:
   │  ├─ Collection name
   │  ├─ Collection artifact count badge
   │  └─ Groups within that collection as badges
   └─ Groups badges display only (no edit/add in MVP)

5. User applies Group filter on /collection or /manage
   ├─ URL updates: ?group=<group-id>
   ├─ Grid/List updates to show only artifacts in that group
   └─ Filter state persists across page navigation
```

### Acceptance Criteria

**Component 1: Collection Badges**

- [ ] Collection badges appear on UnifiedCard when viewing "All Collections"
- [ ] Default collection is hidden; non-default collections show names
- [ ] Max 2 badge names shown; 3+ shows "X more..." with hover tooltip
- [ ] Badges styled with secondary color and consistent Badge component
- [ ] Badges disappear when viewing specific collection (not "All Collections")
- [ ] Accessibility: each badge has aria-label and is keyboard-navigable
- [ ] Unit tests: 80%+ coverage for badge render logic

**Component 2: Group Badges**

- [ ] Group badges appear on UnifiedCard when viewing specific Collection
- [ ] Group badges styled with distinct tertiary color
- [ ] Max 2 badge names shown; 3+ shows "X more..." with hover tooltip
- [ ] Badges hidden when viewing "All Collections" or outside collection context
- [ ] Groups fetched via API; TanStack Query caching applied
- [ ] Error handling: gracefully skip badge render if fetch fails
- [ ] Unit tests: 80%+ coverage for badge render and fetch logic

**Component 3: Modal Groups Section**

- [ ] Collections tab placeholder replaced with Groups display
- [ ] For each collection, groups shown as badges or comma-separated list
- [ ] "No groups" message if collection has no groups
- [ ] Groups badges styled consistently with card badges
- [ ] Groups section loads with collection data; respects modal loading state
- [ ] Accessibility: proper heading hierarchy and aria-labels
- [ ] Unit tests: snapshot tests for modal tab render

**Component 4: Groups Page**

- [ ] New /groups page renders at `/groups` URL
- [ ] Groups tab appears in sidebar under Collections section
- [ ] Group selector dropdown populated from current collection
- [ ] Artifact grid/list renders when group is selected
- [ ] Same filters (Type, Status, Scope, Sort) available and functional
- [ ] View mode toggle (Grid/List) works and persists
- [ ] Empty states: "No groups" and "Select a group" properly rendered
- [ ] Infinite scroll or pagination works for group artifacts
- [ ] Breadcrumb navigation shows: Dashboard > Collections > Groups > [Group Name]
- [ ] Performance: groups list load ≤200ms; artifact load ≤500ms
- [ ] Unit tests: 80%+ coverage for page logic; E2E test for happy path

**Component 5: Group Filter**

- [ ] Group filter dropdown appears on /collection page when in specific collection context
- [ ] Group filter dropdown appears on /manage page when in specific collection context
- [ ] Group filter hidden when viewing "All Collections"
- [ ] Filter options populated from `fetchGroups(collectionId)` API
- [ ] Default value: "All Groups" (no filter applied)
- [ ] Selecting group filters artifacts; URL updates with ?group=<id>
- [ ] Clearing filter removes ?group=<id> from URL
- [ ] Both Filters and EntityFilters components have identical Group filter UX
- [ ] Filter state persists across page navigation (via URL params)
- [ ] Unit tests: 80%+ coverage for filter state logic

**Cross-Component Criteria**

- [ ] All new code TypeScript strict mode; no `any` types
- [ ] All new components use shadcn primitives; no custom styling
- [ ] Accessibility: WCAG 2.1 Level AA compliance verified
- [ ] Performance: total added latency ≤200ms on collection page load
- [ ] Error handling: graceful fallbacks for all failed API calls
- [ ] Test coverage: ≥80% for all new functions and components
- [ ] Code review: at least one peer review before merge
- [ ] Documentation: JSDoc comments for all exported functions

---

## 10. Implementation Phases

### Phase 1: Data Layer & Hooks (Baseline)

**Duration:** 1 week | **Story Points:** 8

**Tasks:**

| Task | Scope | Notes |
|------|-------|-------|
| **Create useGroups hook** | New hook in `/hooks/groups.ts` | Fetch groups for collection with TanStack Query caching |
| **Create useArtifactGroups hook** | New hook in `/hooks/groups.ts` | Fetch groups for specific artifact/collection pair |
| **Extend ArtifactFilters type** | Update `/types/artifact.ts` | Add `groupId?: string` filter field |
| **Create fetchArtifactGroups API** | New function in `/lib/api/groups.ts` | Endpoint: `GET /groups?collection_id=X&artifact_id=Y` or similar |
| **Add barrel export** | Update `/hooks/index.ts` | Export new hooks for easy import |
| **Unit tests** | New tests in `__tests__/` | Test hook logic, caching, error handling (≥80% coverage) |

**Definition of Done:**
- [ ] Hooks exported and importable from `@/hooks`
- [ ] API client function tested end-to-end
- [ ] TanStack Query caching configured (stale time 5-10 min)
- [ ] Error handling returns sensible fallbacks
- [ ] ≥80% test coverage achieved

---

### Phase 2: Collection Badges Component (Card Enhancement)

**Duration:** 1 week | **Story Points:** 10

**Tasks:**

| Task | Scope | Notes |
|------|-------|-------|
| **Enhance UnifiedCard component** | Update `/components/shared/unified-card.tsx` | Add Collection badge rendering logic |
| **Implement badge positioning** | Design decision with UI engineer | Top-right vs. below type indicator; settled before implementation |
| **Add max-badges + tooltip logic** | New utility in component | Show ≤2 names, "X more..." badge with hover tooltip |
| **Accessibility improvements** | Update card component | aria-labels for each badge; keyboard navigation |
| **Styling** | Use shadcn Badge component | Secondary color; consistent with site design system |
| **Conditional rendering** | Add Entity.collections check | Hide if only 'default' or not in "All Collections" view |
| **Unit tests** | New tests for badge section | Snapshot tests, render logic, accessibility (≥80%) |
| **Storybook entry** | Optional: add story for component | Document badge states and variants |

**Definition of Done:**
- [ ] Collection badges render correctly in "All Collections" view
- [ ] Badges styled consistently with design system
- [ ] Accessibility verified: WCAG 2.1 Level AA
- [ ] ≥80% test coverage for new code
- [ ] Code review complete and approved

---

### Phase 3: Group Badges + Modal Enhancement

**Duration:** 1 week | **Story Points:** 9

**Tasks:**

| Task | Scope | Notes |
|------|-------|-------|
| **Enhance UnifiedCard for Group badges** | Update `/components/shared/unified-card.tsx` | Add group badge rendering in collection context |
| **Fetch groups for each card** | Use useArtifactGroups hook | Call hook in card component; handle loading/error |
| **Badge positioning & styling** | Design coordination | Distinct from collection badges; tertiary color |
| **Max-badge + tooltip logic** | Reuse collection badge pattern | ≤2 names, "X more..." fallback |
| **Enhance ModalCollectionsTab** | Update `/components/entity/modal-collections-tab.tsx` | Replace placeholder with actual Groups display |
| **Fetch groups for modal** | Use fetchGroup or groups from collection | Show groups as badges beneath each collection |
| **Styling & accessibility** | Apply consistent patterns | aria-labels, keyboard navigation |
| **Unit tests** | Card + modal badge sections | Snapshot tests, fetch logic, error handling (≥80%) |

**Definition of Done:**
- [ ] Group badges render on cards when in collection context
- [ ] Modal Collections tab shows Groups for each collection
- [ ] Both styled distinctly from collection badges
- [ ] ≥80% test coverage
- [ ] Code review complete
- [ ] No performance regression on card render

---

### Phase 4: Groups Sidebar Page

**Duration:** 1 week | **Story Points:** 12

**Tasks:**

| Task | Scope | Notes |
|------|-------|-------|
| **Add Groups nav item** | Update `/components/navigation.tsx` | New sidebar tab under Collections section |
| **Create /groups page** | New file `/app/groups/page.tsx` | Server component wrapping client components |
| **Create GroupSelector component** | New component for group dropdown | Select group from current collection |
| **Create GroupArtifactGrid** | Reuse ArtifactGrid + filter logic | Display artifacts for selected group |
| **Add view-mode toggle** | Reuse existing toggle from /collection | Grid and List views |
| **Add Filters component** | Reuse existing Filters | Type, Status, Scope, Sort (no Group filter on /groups) |
| **Implement infinite scroll/pagination** | Reuse useInfiniteCollectionArtifacts | Lazy-load artifacts for performance |
| **Empty state handling** | "No groups" and "Select a group" messages | Proper UX when collection or group is empty |
| **Breadcrumb navigation** | Add breadcrumb component | Dashboard > Collections > Groups > [Group Name] |
| **Integration with collection context** | useCollectionContext | Fetch groups from selected collection |
| **Unit tests** | Page + component tests | Happy path E2E test, edge cases (≥80%) |

**Definition of Done:**
- [ ] /groups page renders and is navigable from sidebar
- [ ] Group selector dropdown functional with API data
- [ ] Artifact grid loads and displays correctly
- [ ] Filters and view modes work
- [ ] Empty states render properly
- [ ] ≥80% test coverage
- [ ] Performance: groups load ≤200ms; artifacts ≤500ms
- [ ] Code review complete

---

### Phase 5: Group Filter Integration

**Duration:** 1 week | **Story Points:** 8

**Tasks:**

| Task | Scope | Notes |
|------|-------|-------|
| **Add Group filter to Filters component** | Update `/components/collection/filters.tsx` | New Select dropdown for groups |
| **Add Group filter to EntityFilters** | Update `/app/manage/components/entity-filters.tsx` | Identical UX as /collection filters |
| **Fetch groups for filter** | Use useGroups hook | Populate dropdown options |
| **Conditional rendering** | Hide when viewing "All Collections" | Check useCollectionContext mode |
| **Filter state management** | URL query params (e.g., ?group=id) | Persist filter across navigation |
| **Hook filter integration** | Extend useInfiniteArtifacts | Accept groupId parameter for API filtering |
| **API integration** | Pass groupId to artifact queries | Backend filters by group_id if provided |
| **UI/UX refinement** | Tooltip or help text | Explain when Group filter is available |
| **Unit tests** | Filter logic and state (≥80%) | URL param handling, hook integration |
| **Integration tests** | /collection and /manage pages | Group filter applied and grid updates |

**Definition of Done:**
- [ ] Group filter dropdown appears in Filters and EntityFilters when appropriate
- [ ] Filter hidden when viewing "All Collections"
- [ ] Dropdown populated with groups from current collection
- [ ] Selecting group filters artifacts in grid
- [ ] URL updates with ?group=<id> parameter
- [ ] Filter state persists across navigation
- [ ] ≥80% test coverage
- [ ] Code review complete

---

## 11. Testing Strategy

### Unit Testing

**Scope:** Components, hooks, utilities

| Component | Test Cases | Coverage Target |
|-----------|-----------|-----------------|
| **UnifiedCard (badges)** | Collection badge render, Group badge render, max-badge tooltip, conditional hide logic, accessibility | 85%+ |
| **useGroups hook** | Fetch success, fetch error, caching behavior, stale time, refetch trigger | 80%+ |
| **useArtifactGroups hook** | Fetch success, fetch error, artifact/collection param passing, caching | 80%+ |
| **useGroupFilter hook** | State management, URL sync, clear filter, initial state from URL | 85%+ |
| **useInfiniteCollectionArtifacts (group_id/include_groups)** | Query param mapping, response shape, caching | 80%+ |
| **Filters component (Group dropdown)** | Render, conditional display, selection change, state update | 80%+ |
| **EntityFilters (Group dropdown)** | Same as Filters component | 80%+ |
| **ModalCollectionsTab** | Groups render, empty state, badge display, accessibility | 80%+ |
| **GroupSelector** | Dropdown render, selection change, empty state, accessibility | 80%+ |

**Tools:** Jest + React Testing Library (RTL)

**Command:** `pnpm test --coverage`

---

### Integration Testing

**Scope:** Multi-component workflows

| Workflow | Test | Expected Result |
|----------|------|-----------------|
| **View All Collections + badges** | Navigate to /collection without collection selected → render cards → check Collection badges | Badges visible for non-default collections |
| **View specific collection + badges + filter** | Select collection → check Group badges → apply Group filter → grid updates | Group filter works; grid shows only filtered artifacts |
| **Navigate to /groups page** | Click Groups sidebar → select group → render artifacts | Groups page renders; selected group artifacts display |
| **Modal Collections tab** | Open modal → navigate to Collections tab → check Groups display | Groups shown as badges for each collection |
| **Filter persistence** | Apply Group filter on /collection → navigate to /manage → check if filter state available | Filter state accessible (may reset based on page context) |

**Tools:** Playwright for E2E tests (optional)

**Command:** `pnpm test:e2e` (if Playwright setup exists)

---

### Performance Testing

| Metric | Target | Tool |
|--------|--------|------|
| **Groups fetch latency** | ≤200ms per collection | Lighthouse DevTools |
| **Card render time** | ≤50ms per card with badges | React DevTools Profiler |
| **Page load added latency** | ≤200ms total for /collection with badges | Chrome DevTools Network tab |
| **TanStack Query cache hit rate** | ≥80% for repeated group fetches | React Query DevTools |

---

### Accessibility Testing

| Criterion | Test | Tool |
|-----------|------|------|
| **WCAG 2.1 Level AA** | Run axe or Lighthouse audit on all new pages/components | axe DevTools extension |
| **Keyboard navigation** | Tab through all badges and filter dropdowns | Manual testing |
| **Screen reader** | Test badge aria-labels and filter semantics | NVDA or JAWS |
| **Color contrast** | Badge text on background meets 4.5:1 ratio | Lighthouse report |

---

## 12. Rollout & Deployment

### Deployment Strategy

1. **Branch Strategy:** Feature branch `feat/collections-groups-ux-v1` off `main`
2. **Code Review:** Minimum 1 review; automated checks (lint, type, test) must pass
3. **Beta Release:** Deploy to beta environment first; smoke test all 5 components
4. **Staged Rollout:** 10% → 50% → 100% over 3 days via feature flag (optional)
5. **Monitoring:** GA events, error tracking, performance metrics
6. **Rollback Plan:** Revert feature flag or PR revert if critical issues detected

### Monitoring & Observability

**GA Events to Track:**

```typescript
// Component 1: Collection badges
gtag('event', 'collection_badge_viewed', { count: 2 });

// Component 2: Group badges
gtag('event', 'group_badge_viewed', { count: 1 });

// Component 4: Groups page
gtag('event', 'groups_page_visited', { collection_id: 'abc123' });
gtag('event', 'group_selected', { group_id: 'xyz789' });

// Component 5: Group filter
gtag('event', 'group_filter_applied', { group_id: 'xyz789' });
```

**Error Tracking:**

- Log failed group fetches to Sentry
- Track badge render errors
- Monitor API 4xx/5xx responses

**Performance Metrics:**

- Web Vitals: LCP, CLS, FID
- Custom: groups-fetch-time, card-render-time

---

## 13. Success Criteria & Rollout Gates

| Gate | Success Criteria |
|------|-----------------|
| **Code Quality** | All unit tests pass (≥80% coverage); ESLint/TypeScript checks pass; code review approved |
| **Performance** | Page load latency increase ≤200ms; card render time ≤50ms per card |
| **Accessibility** | WCAG 2.1 Level AA compliant; axe audit 0 critical issues |
| **Functionality** | All 5 components meet acceptance criteria (see Section 9) |
| **Beta Testing** | 1 week beta with no critical bugs; ≥1 successful manual user test |
| **Monitoring** | GA events firing correctly; error tracking active; dashboards up |

**Rollback Criteria:**

- Critical bug affecting ≥5% of users (e.g., cards not rendering)
- Performance regression >500ms
- Accessibility failure (WCAG Level A)
- Data integrity issue (artifact loss, group data corruption)

---

## 14. Documentation & Training

### User-Facing Documentation

- [ ] Add Groups section to web app help/docs
- [ ] Screenshot guide for Collection & Group badges
- [ ] Tutorial: "How to browse by Group"
- [ ] FAQ: "What's the difference between Collections and Groups?"

### Developer Documentation

- [ ] JSDoc comments on all new functions (already required by linting)
- [ ] Architecture decision: why Groups page uses existing ArtifactGrid
- [ ] Testing patterns: badge render tests, hook tests
- [ ] Troubleshooting: common Group fetch issues

### Internal Communication

- [ ] Changelog entry for release notes
- [ ] Slack announcement in #engineering channel
- [ ] Link to this PRD in commit messages

---

## 15. Assumptions & Open Questions

### Assumptions

1. **Collection badge positioning:** Assumed top-right corner; coordinate with UI engineer for final decision
2. **Group badge color:** Assumed tertiary color to distinguish from collections; verify with design system
3. **Max badges:** Assumed max 2 badges + "X more..." pattern; adjust if design system suggests otherwise
4. **Group filter visibility:** Assumed hidden when viewing "All Collections" to avoid cross-collection group name conflicts; confirm with PM
5. **Modal Groups display:** Assumed display-only (no edit/add in MVP); future enhancement in Phase 2
6. **Performance acceptable:** Assumed ≤200ms added latency is acceptable; adjust if RUM data conflicts
7. **Existing collections array:** Verified `/api/v1/artifacts` includes `collections` mapping; still validate in UI

### Open Questions

1. **Should Group badges be clickable?** (e.g., click badge → navigate to that group on /groups page?) → Design decision
2. **Should /groups page support sorting/filtering by artifact metadata?** → Confirm scope
3. **API batching for group fetches:** Resolved by adding `include_groups=true` on collection artifacts + `artifact_id` filter on `/groups` (Phase 0). Revisit only if backend rejects these changes.
4. **Group filter on /manage page:** Should this filter respect multi-collection context? → Clarify PM intent
5. **Future: Group-based sharing/permissions?** → Out of scope for MVP; ask in planning for Phase 2

---

## 16. Related Work & References

### Related PRDs

- `/docs/project_plans/PRDs/enhancements/collections-navigation-v1.md` — Collections restructure (completed)
- `/docs/project_plans/PRDs/enhancements/groups-all-collections-v1.md` — Groups backend (completed)

### Code References

- **Groups API:** `skillmeat/api/routers/groups.py`
- **Groups types:** `skillmeat/web/types/groups.ts`
- **Groups client:** `skillmeat/web/lib/api/groups.ts`
- **UnifiedCard:** `skillmeat/web/components/shared/unified-card.tsx`
- **Filters:** `skillmeat/web/components/collection/filters.tsx`
- **Modal Collections Tab:** `skillmeat/web/components/entity/modal-collections-tab.tsx`
- **Navigation:** `skillmeat/web/components/navigation.tsx`

### Design System & Patterns

- **Badge component:** shadcn/ui Badge with custom colors
- **Select component:** shadcn/ui Select (used in existing filters)
- **TanStack Query patterns:** Existing hooks in `web/hooks/` directory
- **Error handling patterns:** Review `.claude/context/key-context/debugging-patterns.md`

---

## Appendix A: API Contract Examples

### Example: Fetch Groups for Collection

```typescript
// Hook usage
const { data: groups, isLoading, error } = useGroups(collectionId);

// Internally calls:
const response = await fetch(`/api/v1/groups?collection_id=${collectionId}`);
const groups: Group[] = await response.json();

// TanStack Query setup:
const queryKey = ['groups', collectionId];
const staleTime = 5 * 60 * 1000; // 5 minutes
```

### Example: Fetch Groups for Specific Artifact

```typescript
// Hook usage
const { data: groups, isLoading } = useArtifactGroups(artifactId, collectionId);

// Internally calls:
const response = await fetch(`/api/v1/groups?collection_id=${collectionId}&artifact_id=${artifactId}`);
const groups: Group[] = await response.json();

// Note: Requires backend enhancement (Phase 0) to support artifact_id filter
```

### Example: Group Filter in Artifact Query

```typescript
// Before: fetch all artifacts in collection
const artifacts = await fetch(`/api/v1/user-collections/${collectionId}/artifacts`);

// After: fetch only artifacts in specific group
const artifacts = await fetch(`/api/v1/user-collections/${collectionId}/artifacts?group_id=${groupId}`);
```

### Example: Include Groups for Card Badges

```typescript
// Fetch artifacts with group memberships for badge rendering
const artifacts = await fetch(
  `/api/v1/user-collections/${collectionId}/artifacts?include_groups=true`
);
```

---

## Appendix B: Component Wireframes (Text-Based)

### Collection Badges on Card (All Collections View)

```
┌─────────────────────────────────────────┐
│ ⬛ Skill: My AI Tool          [badge: X] │  ← Collection badges (top-right)
│ <Type color bar>                         │
│                                         │
│ Description: Fast and efficient...     │
│ Tags: [ai] [rag] [llm]                 │
│ Version: v1.2.0 | Updated: 2d ago      │
│                                         │
│ [✓] Checkbox    [⋮] Actions            │
└─────────────────────────────────────────┘

Badge format: [My Skills] [AI Tools] [+ 2 more →]
```

### Group Badges on Card (Specific Collection View)

```
┌─────────────────────────────────────────┐
│ ⬛ Skill: My AI Tool                    │
│ <Type color bar>                         │
│ [My Skills] [AI Tools] [+ 2 more →]    │  ← Group badges (secondary)
│                                         │
│ Description: Fast and efficient...     │
│ Tags: [ai] [rag] [llm]                 │
│ Version: v1.2.0 | Updated: 2d ago      │
│                                         │
│ [✓] Checkbox    [⋮] Actions            │
└─────────────────────────────────────────┘
```

### Groups Page Layout

```
Dashboard / Collections / Groups

┌─────────────────────────────────────────────────┐
│ Select Group: [v AI Tools ▼]  [Grid] [List]   │  ← Group selector + view mode
│ [Search...] [Type▼] [Status▼] [Scope▼] [Sort▼]│  ← Filters
└─────────────────────────────────────────────────┘

Artifacts Grid:
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Artifact │ │ Artifact │ │ Artifact │
│   Card 1 │ │   Card 2 │ │   Card 3 │
└──────────┘ └──────────┘ └──────────┘
```

### Modal Collections Tab with Groups

```
Collections & Groups (Tab)

┌─────────────────────────────────────┐
│ Add to Collection  │  New            │
├─────────────────────────────────────┤
│ 📁 My Collection     [5 artifacts]  │
│    Groups: [RAG] [LLM] [+ 1 more]   │  ← New Groups section
│    ⋮ Remove                         │
│                                     │
│ 📁 Shared Tools      [3 artifacts]  │
│    Groups: [Utilities]              │
│    ⋮ Remove                         │
└─────────────────────────────────────┘
```

---

## Appendix C: Error Handling Strategy

### Graceful Degradation

| Error | Handling | UX Impact |
|-------|----------|-----------|
| **Group fetch fails** | Log error; skip badge render; show no badge | Card renders but missing group metadata |
| **Collection fetch fails** | Log error; skip badge render | Card renders but missing collection metadata |
| **Group filter API fails** | Reset filter; show toast "Unable to load groups" | User can still see all artifacts (unfiltered) |
| **Groups page load fails** | Show error state: "Unable to load groups" | User sees error message; can retry or navigate away |

### Logging Strategy

```typescript
// Example: log group fetch error
try {
  const groups = await fetchArtifactGroups(artifactId, collectionId);
} catch (error) {
  console.error('Failed to fetch groups for artifact', {
    artifactId,
    collectionId,
    error: error instanceof Error ? error.message : String(error),
  });
  // Sentry: captureException(error, { tags: { component: 'UnifiedCard' } })
  return null; // Skip badge render
}
```

---

**End of PRD**

**Prepared by:** Claude Code (AI Agent)

**Date:** 2026-01-19

**Status:** Ready for Implementation Review
