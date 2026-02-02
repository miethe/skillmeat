---
title: "Architecture Analysis: /manage vs /collection Page Purposes and Endpoint Alignment"
description: "Analysis of page responsibilities, endpoint assignments, UX specification, and implementation guidance for the two primary artifact browsing interfaces"
audience: [developers, architects, ai-agents, product]
tags: [architecture, ux, frontend, api, analysis, implementation]
created: 2026-02-01
updated: 2026-02-01
category: "reports"
status: approved
complexity: Medium
total_effort: "16-24 hours"
related:
  - /docs/project_plans/reports/dual-collection-system-architecture-analysis.md
  - /docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md
  - /docs/design/ui-component-specs-page-refactor.md
  - /.claude/worknotes/page-separation/user-journey-analysis.md
---

# Architecture Analysis: /manage vs /collection Page Purposes

**Date**: 2026-02-01
**Author**: Claude Opus 4.5 (AI-generated)
**Discovery Context**: Investigation of endpoint usage patterns across artifact browsing pages
**Status**: Approved - Option C selected with detailed UX specification

---

## Executive Summary

SkillMeat has two primary artifact browsing interfaces (`/manage` and `/collection`) that use different API endpoints. Investigation reveals this is **architecturally correct** but **semantically confusing**:

- `/manage` page uses `/artifacts` endpoint (file-based CollectionManager system)
- `/collection` page uses `/user-collections/{id}/artifacts` endpoint (database system)

The endpoint assignments align with the [dual collection system architecture](/docs/project_plans/reports/dual-collection-system-architecture-analysis.md), but the page naming creates user confusion about their distinct purposes. This report provides three options for improving UX clarity while preserving architectural integrity.

---

## Current State Analysis

### Endpoint-to-Page Mapping

| Page | Route | Primary Endpoint | Backend System | Primary Use Case |
|------|-------|------------------|----------------|------------------|
| Manage | `/manage` | `GET /api/v1/artifacts` | CollectionManager (file-based) | Artifact lifecycle management |
| Collection | `/collection` (collection via `?collection=` and local state) | `GET /api/v1/user-collections/{id}/artifacts` | Database collections | Collection organization |

### Feature Comparison

| Feature | `/manage` Page | `/collection` Page |
|---------|---------------|-------------------|
| View all artifacts across collections | ✅ | ❌ |
| Filter by specific collection | ✅ (query param) | ✅ (query param + local state) |
| Drift detection display | ✅ | ❌ |
| Sync status | ✅ | ❌ |
| Unlinked references filter | ✅ | ❌ |
| Tags/tools filtering | ✅ | ❌ |
| Import batch filtering | ✅ | ❌ |
| Group organization | ❌ | ✅ |
| Group filtering | ❌ | ✅ |
| Lightweight summary response | ❌ (full metadata) | ✅ |
| View modes (grid/list/grouped) | Limited | ✅ |

### API Response Differences

**`/artifacts` endpoint** returns `ArtifactResponse`:
```typescript
{
  id: string;
  name: string;
  type: string;
  source: string;
  version: string;
  resolved_version: string;
  origin: string;              // 'local', 'github', 'marketplace'
  origin_source: string;
  drift_status: string;        // File-system specific
  has_local_modifications: boolean;
  upstream: UpstreamInfo;      // Version tracking
  collections: CollectionInfo[];
  tags: string[];
  metadata: ArtifactMetadata;  // Full nested metadata
  // ... 20+ fields total
}
```

**`/user-collections/{id}/artifacts` endpoint** returns `ArtifactSummary`:
```typescript
{
  id: string;
  name: string;
  type: string;
  version: string;
  source: string;
  description: string;         // Flattened from metadata
  author: string;              // Flattened from metadata
  groups?: GroupMembership[];  // Database-specific
  // ... 8-10 fields total
}
```

---

## Problem Statement

### User Confusion

Users encounter these pages without understanding their distinct purposes:

1. **"Manage" suggests CRUD operations** - but the page is actually about artifact lifecycle (sync, drift, versions)
2. **"Collection" suggests browsing a collection** - but it's actually about organizational structure (groups, hierarchy)
3. **Both pages show artifacts** - unclear when to use which
4. **Filtering overlap** - both support collection filtering, but via different mechanisms

### Developer Confusion

The dual-system architecture is not immediately obvious:

1. Endpoint names don't indicate their backend system
2. Response schemas differ significantly but serve similar display purposes
3. The `/manage` page could use the scoped endpoint when filtering by collection (performance opportunity)

### Architectural Tension

The current design reflects valid architectural decisions but creates friction:

| Decision | Rationale | Friction |
|----------|-----------|----------|
| `/artifacts` for `/manage` | Provides drift/sync data from file system | Heavy payload when user just wants to browse |
| `/user-collections/{id}/artifacts` for `/collection` | Provides group data from database | Can't show drift status for CLI-added artifacts |

---

## Recommendations

### Option A: Rename Pages for Clarity (Low Effort)

**Approach**: Keep current architecture, rename pages to reflect actual purposes.

**Changes**:

| Current | Proposed | Rationale |
|---------|----------|-----------|
| `/manage` | `/library` or `/artifacts` | Reflects "all artifacts" browsing with lifecycle features |
| `/collection` | `/organize` or `/workspace` (collection via query param) | Reflects organizational/grouping focus |

**Navigation Updates**:
```
Sidebar:
  - Library (was Manage) → Browse all artifacts, sync status, drift detection
  - Workspaces (was Collections) → Organize into groups, custom collections
```

**Pros**:
- Minimal code changes
- Clear semantic distinction
- Preserves architectural alignment

**Cons**:
- Requires user re-learning
- "Library" may not convey lifecycle management
- URL changes may break bookmarks

**Effort**: 2-4 hours

---

### Option B: Merge into Single Smart Page (Medium Effort)

**Approach**: Create unified `/artifacts` page that intelligently uses both endpoints.

**Behavior**:
```
/artifacts (no collection filter)
  → Uses /api/v1/artifacts
  → Shows all artifacts with full lifecycle data
  → Heavy payload, rich features

/artifacts?collection={id} (collection filter active)
  → Uses /api/v1/user-collections/{id}/artifacts
  → Shows collection-scoped artifacts with groups
  → Light payload, organization features
  → Can toggle to "detailed view" which fetches from /artifacts
```

**Implementation**:
```typescript
// hooks/useSmartArtifacts.ts
export function useSmartArtifacts(options: SmartArtifactOptions) {
  const { collectionId, detailedView = false } = options;

  // Use scoped endpoint when collection selected (unless detailed view requested)
  const useScoped = collectionId && !detailedView;

  const scopedQuery = useInfiniteCollectionArtifacts(
    useScoped ? collectionId : undefined,
    { enabled: useScoped }
  );

  const globalQuery = useInfiniteArtifacts({
    collection: collectionId,
    enabled: !useScoped,
  });

  return useScoped ? scopedQuery : globalQuery;
}
```

**UI Additions**:
- "Detailed View" toggle when collection is selected
- View mode selector (grid/list/grouped) always available
- Feature indicators showing what's available in current mode

**Pros**:
- Single mental model for users
- Optimal endpoint usage based on context
- Progressive disclosure of features

**Cons**:
- More complex state management
- Two response schemas to normalize
- Group features only available when collection selected

**Effort**: 8-12 hours

---

### Option C: Distinct Purpose Pages with Cross-Links (Recommended)

**Approach**: Keep both pages but clarify purposes and add contextual navigation.

**Page Purposes**:

| Page | New Tagline | Primary Actions | Secondary Actions |
|------|-------------|-----------------|-------------------|
| `/manage` | "Artifact Health & Sync" | View drift, sync artifacts, check versions | Quick deploy, view details |
| `/collection` | "Organize & Discover" | Create groups, move artifacts, browse | Quick actions on items |

**UX Improvements**:

1. **Page Headers with Purpose**:
```tsx
// /manage page
<PageHeader
  title="Artifact Health"
  description="Monitor sync status, detect local changes, and manage versions"
  icon={<ActivityIcon />}
/>

// /collection page
<PageHeader
  title="Collection: {name}"
  description="Organize artifacts into groups and discover related items"
  icon={<FolderIcon />}
/>
```

2. **Contextual Cross-Links**:
```tsx
// On /manage, when viewing an artifact
<DropdownMenuItem onClick={() => navigateToCollection(artifact.collections[0].id)}>
  <FolderIcon /> Organize in Collection
</DropdownMenuItem>

// On /collection, for artifacts with drift
<Badge variant="warning" onClick={() => navigateToManage(artifact.id)}>
  Has local changes → View in Health Dashboard
</Badge>
```

3. **Smart Entry Points**:
```tsx
// Dashboard or home page
<QuickActions>
  <ActionCard
    title="Check Artifact Health"
    description="3 artifacts have local modifications"
    href="/manage?filter=has_drift"
    icon={<AlertIcon />}
  />
  <ActionCard
    title="Organize Collection"
    description="12 ungrouped artifacts in Default"
    href="/collection?collection=default"
    icon={<FolderIcon />}
  />
</QuickActions>
```

4. **Endpoint Optimization** (Bonus):
When `/manage` page has a collection filter active, switch to scoped endpoint for performance:
```typescript
// In useEntityLifecycle or page component
const shouldUseScoped = selectedCollection && !needsLifecycleData;
```

**Navigation Structure**:
```
Sidebar:
  ├── Dashboard
  ├── Health & Sync        ← /manage (renamed in nav only)
  │     └── Shows: drift indicators, sync actions, version info
  ├── Collections          ← /collection
  │     ├── Default
  │     ├── Work Tools
  │     └── + New Collection
  └── Settings
```

**Pros**:
- Preserves both pages' unique value
- Clear user mental model
- Cross-linking enables workflow continuity
- URLs can remain stable (only nav labels change)
- Endpoint optimization opportunity included

**Cons**:
- Still two pages to maintain
- Requires thoughtful cross-link implementation
- Users must understand when to use each

**Effort**: 6-10 hours

---

## Comparison Matrix

| Criterion | Option A: Rename | Option B: Merge | Option C: Distinct + Links |
|-----------|------------------|-----------------|---------------------------|
| User clarity | Medium | High | High |
| Development effort | Low (2-4h) | High (8-12h) | Medium (6-10h) |
| Architectural alignment | Preserved | Requires normalization | Preserved + optimized |
| Feature preservation | Full | Requires compromises | Full |
| Future extensibility | Limited | Good | Excellent |
| Risk | Low | Medium | Low |

---

## Recommended Approach

**Option C: Distinct Purpose Pages with Cross-Links** is recommended because:

1. **Preserves architectural integrity** - Each page continues to use its optimal backend system
2. **Clarifies user mental model** - "Health & Sync" vs "Organize" are distinct concepts
3. **Enables workflow continuity** - Cross-links connect related tasks
4. **Includes performance optimization** - Scoped endpoint when collection filter active
5. **Low risk** - Incremental changes, no major refactoring

### Implementation Phases

**Phase 1: Navigation & Headers (2-3h)**
- Update sidebar labels ("Health & Sync", "Collections")
- Add page headers with descriptions
- No URL changes required

**Phase 2: Cross-Links (2-3h)**
- Add "Organize in Collection" action on `/manage`
- Add "View Health" link for artifacts with drift on `/collection`
- Implement smart entry points on dashboard

**Phase 3: Endpoint Optimization (2-4h)**
- Modify `/manage` to use scoped endpoint when collection filter active
- Add "detailed view" toggle to fetch full data when needed
- Measure and document performance improvement

---

## Approved Design: Detailed UX Specification

Based on stakeholder review, **Option C** has been selected with the following refinements to create truly distinct page experiences.

### Finalized Design Decisions

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| Landing page | Dashboard (`/`) with `/collection` as primary browse page | Dashboard provides overview; collection is main artifact interaction |
| Modal navigation | Dual buttons in Collections tab: "View Details" + "Manage Artifact" | Clear action distinction without confusion |
| Modal structure | Page-specific modals with cross-navigation buttons | Each page shows relevant information; users can switch contexts |
| Deploy action | Available on both pages | Core action shouldn't require page switching |
| Project filtering | `/manage` filterable by project with deployment indicators | Operations page needs project context |
| Information access | All details viewable on `/collection`, operations require `/manage` | `/collection` is comprehensive; `/manage` is action-oriented |

### Page Purpose Definitions

#### `/collection` — Browse & Discover (Primary Page)

**Mental Model**: "What artifacts do I have? What do they do?"

**Primary Features**:
| Feature | Priority | Notes |
|---------|----------|-------|
| Full metadata display | High | Users understand what artifact does |
| Description, author, license | High | Discovery-oriented information |
| Tags and tools filtering | High | Finding related artifacts |
| Groups and organization | High | Structuring the collection |
| Search | High | Finding specific artifacts |
| Usage examples/docs | Medium | Understanding how to use |
| Dependencies view | Medium | What does this artifact need? |
| Quick Deploy action | High | Don't force page switch for common action |

**Not Emphasized**: Deployment status details, sync actions, drift detection, version diffs

#### `/manage` — Operations Dashboard (Secondary Page)

**Mental Model**: "What needs attention? Deploy, sync, upgrade"

**Primary Features**:
| Feature | Priority | Notes |
|---------|----------|-------|
| Deployment status per project | High | "Where is this deployed?" |
| Version comparison | High | Current vs available version |
| Drift/modification detection | High | "Did I change this locally?" |
| Sync actions | High | "Pull latest from upstream" |
| Bulk operations | High | Deploy/sync/upgrade multiple |
| Health indicators | High | At-a-glance status |
| Project filter | High | "Show artifacts in Project X" |
| Unlinked references | Medium | "What's broken?" |

**Not Emphasized**: Full descriptions, groups, organizational features

### Modal Specifications

#### ArtifactDetailsModal (Collection Page)

**Purpose**: Deep exploration for discovery

**Tab Structure**:

| Tab | Content | Default |
|-----|---------|---------|
| Overview | Full description, metadata, tags, tools (Tools API), upstream summary | ✅ Default |
| Contents | File tree + content pane (existing data) | |
| Links | Linked artifacts + unlinked references | |
| Collections | Collection/group membership | |
| Sources | Repository/source details | |
| History | General artifact history timeline | |

**Header Actions**:
- Close button (X)
- "Manage Artifact →" navigation button (top-right)
- Deploy to Project button
- Add to Group button

#### ArtifactOperationsModal (Manage Page)

**Purpose**: Operational management and actions

**Tab Structure**:

| Tab | Content | Default |
|-----|---------|---------|
| Overview | Metadata + operational highlights | |
| Contents | File tree + content pane (existing data) | |
| Status | Detailed operational status overview | ✅ Default |
| Sync Status | Drift detection + sync actions | |
| Deployments | List of projects deployed to, deploy/undeploy actions | |
| Version History | Previous versions, changelogs, rollback options | |

**Header Actions**:
- Close button (X)
- "Collection Details →" navigation button (top-right)
- Sync button
- Deploy button

### Card Component Specifications

#### ArtifactBrowseCard (Collection Page)

```
┌──────────────────────────────────────────────────────────────┐
│ [Type Icon]  Artifact Name                    [Quick Actions]│
│              author/source                                    │
├──────────────────────────────────────────────────────────────┤
│ Description text that can span multiple lines with proper    │
│ truncation after 2-3 lines using line-clamp...               │
├──────────────────────────────────────────────────────────────┤
│ [tag1] [tag2] [tag3] [+N more]                               │
├──────────────────────────────────────────────────────────────┤
│ [Tool: Bash] [Tool: Read] [Tool: Write]         [Score: 0.9] │
└──────────────────────────────────────────────────────────────┘
```

**Quick Actions Menu**: View Details, Quick Deploy, Add to Group, Copy CLI Command
**Status Indicator**: Subtle deployed/outdated badge only when applicable (links to /manage)

#### ArtifactOperationsCard (Manage Page)

```
┌──────────────────────────────────────────────────────────────┐
│ [☐] [Type Icon]  Artifact Name              [Status Badge]   │
│                   v1.2.0 → v1.3.0           [Health Icon]    │
├──────────────────────────────────────────────────────────────┤
│ Deployed to: [Project A] [Project B] [+2]                    │
├──────────────────────────────────────────────────────────────┤
│ [Drift Badge]  [Update Available]  Last Synced: 2h ago       │
├──────────────────────────────────────────────────────────────┤
│ [Sync] [Deploy] [View Diff] [Manage...]                      │
└──────────────────────────────────────────────────────────────┘
```

**Checkbox**: For bulk operations (sync all, deploy all)
**Health Indicators**: Healthy (green), Needs Update (orange), Has Drift (yellow), Error (red)

### Cross-Navigation Patterns

#### From `/collection` to `/manage`

| Trigger | Link Text | Destination |
|---------|-----------|-------------|
| Card action menu | "Manage" | `/manage?artifact={id}` |
| Card badge (if deployed & outdated) | "Outdated" | `/manage?artifact={id}&tab=status` |
| Modal header | "Manage Artifact →" | `/manage?artifact={id}` |
| Collections tab button | "Manage Artifact" | `/manage?artifact={id}` |

#### From `/manage` to `/collection`

| Trigger | Link Text | Destination |
|---------|-----------|-------------|
| Card action menu | "Collection Details" | `/collection?artifact={id}` (optionally `&collection={collectionId}`) |
| Modal header | "Collection Details →" | `/collection?artifact={id}` (optionally `&collection={collectionId}`) |
| Sync Status tab | "What's new?" | `/collection?artifact={id}&tab=history` |
| Empty state | "Browse Collection" | `/collection` |

### Filter Components

#### ManagePageFilters

| Filter | Options | Purpose |
|--------|---------|---------|
| Project | All Projects, [project list] | Show artifacts deployed to specific project |
| Status | All, Needs Update, Has Drift, Deployed, Error | Filter by operational state |
| Type | All, Skills, Commands, Agents, MCP Servers, Hooks | Filter by artifact type |
| Search | Text input | Find by name |

#### CollectionPageFilters

| Filter | Options | Purpose |
|--------|---------|---------|
| Collection | [collection list] | Scope to collection |
| Group | All Groups, [group list] | Filter by group membership |
| Type | All, Skills, Commands, Agents, etc. | Filter by artifact type |
| Tags | Multi-select popover | Filter by tags |
| Tools | Multi-select popover | Filter by Claude tools used (Tools API PRD) |
| Search | Text input | Find by name, description |

---

## Implementation Plan

### Phase 1: Page Structure & Navigation (4-6h)

| Task | Description | Files |
|------|-------------|-------|
| 1.1 | Update sidebar navigation labels | `web/components/layout/sidebar.tsx` |
| 1.2 | Add page headers with descriptions | `web/app/manage/page.tsx`, `web/app/collection/page.tsx` |
| 1.3 | Implement deep link support (`?artifact={id}`) | Both pages |
| 1.4 | Add cross-navigation buttons to existing modals | `UnifiedEntityModal` |

### Phase 2: Card Components (4-6h)

| Task | Description | Files |
|------|-------------|-------|
| 2.1 | Create `ArtifactBrowseCard` component | `web/components/collection/artifact-browse-card.tsx` |
| 2.2 | Create `ArtifactOperationsCard` component | `web/components/manage/artifact-operations-card.tsx` |
| 2.3 | Create shared utilities (`StatusBadge`, `HealthIndicator`, `DeploymentBadgeStack`) | `web/components/shared/` |
| 2.4 | Integrate cards into respective pages | Both pages |

### Phase 3: Modal Separation (6-8h)

| Task | Description | Files |
|------|-------------|-------|
| 3.1 | Create `ArtifactDetailsModal` (collection-focused) | `web/components/collection/artifact-details-modal.tsx` |
| 3.2 | Create `ArtifactOperationsModal` (manage-focused) | `web/components/manage/artifact-operations-modal.tsx` |
| 3.3 | Extract shared modal components | `web/components/shared/` |
| 3.4 | Update `ModalCollectionsTab` with dual buttons | `web/components/entity/modal-collections-tab.tsx` |
| 3.5 | Implement cross-navigation state preservation | Both modals |

### Phase 4: Filter Components (2-4h)

| Task | Description | Files |
|------|-------------|-------|
| 4.1 | Create `ManagePageFilters` with project filter | `web/components/manage/manage-page-filters.tsx` |
| 4.2 | Update `CollectionPageFilters` with tools filter | `web/components/collection/collection-page-filters.tsx` |
| 4.3 | Add filter state to URL for bookmarkability | Both pages |

### Phase 5: Polish & Testing (2-4h)

| Task | Description | Files |
|------|-------------|-------|
| 5.1 | Add loading states and skeletons | All new components |
| 5.2 | Accessibility audit (ARIA, keyboard nav) | All new components |
| 5.3 | Unit tests for new components | `__tests__/` |
| 5.4 | E2E tests for cross-navigation flows | `tests/` |

### Migration Strategy

1. **Parallel Development**: New components alongside existing
2. **Incremental Adoption**: Migrate pages and tabs in small PRs
3. **Deprecation**: Remove old components after validation

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User understands page purpose | >85% | Usability test task completion |
| Cross-page navigation success | >90% | Users can switch contexts without confusion |
| Time to find artifact health | <10s | From landing to seeing sync status |
| Time to organize artifact | <15s | From landing to adding to group |
| Navigation clicks per task | <3 | Efficient pathfinding |

---

## Appendix A: User Journey Examples

### Journey 1: "I added a skill via CLI, want to organize it"

```
1. User runs: skillmeat add anthropics/skills/pdf
2. Server syncs to database on next startup
3. User opens web UI → sees "3 new artifacts" notification
4. Clicks notification → lands on /manage with filter
5. Sees PDF skill, clicks "Organize in Collection"
6. Lands on /collection?collection=default with PDF selected
7. Creates "Document Tools" group, adds PDF
```

### Journey 2: "I want to check if my artifacts are up to date"

```
1. User opens web UI → clicks "Health & Sync" in nav
2. Lands on /manage → sees drift indicators
3. Filters by "Has local changes"
4. Reviews modifications, decides to sync
5. Clicks "Sync All" → artifacts updated
```

### Journey 3: "I want to find all my API-related skills"

```
1. User opens web UI → clicks "Collections" → "Work Tools"
2. Lands on /collection?collection=work-tools
3. Expands "API Development" group
4. Browses skills, clicks one for details
5. Sees "Has updates available" badge
6. Clicks badge → jumps to /manage?artifact=api-skill
7. Reviews and syncs the update
```

---

## Appendix B: Related Files

### Frontend Pages
- `skillmeat/web/app/manage/page.tsx` - Current manage page
- `skillmeat/web/app/collection/page.tsx` - Current collection page (collection selection via query params)

### API Endpoints
- `skillmeat/api/routers/artifacts.py` - `/artifacts` endpoint
- `skillmeat/api/routers/user_collections.py` - `/user-collections/{id}/artifacts` endpoint

### Hooks
- `skillmeat/web/hooks/useArtifacts.ts` - `useInfiniteArtifacts()`
- `skillmeat/web/hooks/use-collections.ts` - `useInfiniteCollectionArtifacts()`
- `skillmeat/web/hooks/useEntityLifecycle.tsx` - Unified artifact management

### Related Reports
- [Dual Collection System Architecture](/docs/project_plans/reports/dual-collection-system-architecture-analysis.md)
- [Collection Data Consistency Implementation](/docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md)

---

## Appendix C: Primary User Journeys

Seven primary user journeys have been identified and documented. Key journeys:

### Journey 1: Discovery and Exploration
```
/collection → Filter/search → Click card → View modal → Read details → Deploy or Add to Group
```
**Primary page**: `/collection`

### Journey 2: Health Check and Maintenance
```
/manage → Filter by status → See indicators → Click issue → View modal → Sync/resolve
```
**Primary page**: `/manage`

### Journey 3: Deploy to New Project (Cross-Page)
```
/collection → Find artifact → Modal → "Deploy" → Select project → Success
```
**Cross-page flow**: Starts in `/collection`, may involve `/manage` for complex deployments

### Journey 4: Troubleshoot Sync Issue (Cross-Page)
```
/manage → See "outdated" → Modal → View diff → "View Details" → /collection → Read changelog → Return → Sync
```
**Cross-page flow**: Investigates in `/manage`, learns in `/collection`

### Journey 5: Bulk Operations
```
/manage → Filter outdated → Select all → "Sync All" → Progress → Complete
```
**Primary page**: `/manage`

### Journey 6: Project-Centric View
```
/manage → Filter by project → See deployed artifacts → Check status → Take action
```
**Primary page**: `/manage`

For complete journey diagrams and analysis, see: `/.claude/worknotes/page-separation/user-journey-analysis.md`

---

## Appendix D: Component Specifications Reference

Detailed TypeScript interfaces, visual layouts, and implementation notes are documented in:

**Full Specification**: `/docs/design/ui-component-specs-page-refactor.md`

Key components specified:
- `ArtifactBrowseCard` - Collection page card
- `ArtifactOperationsCard` - Manage page card
- `ArtifactDetailsModal` - Collection page modal
- `ArtifactOperationsModal` - Manage page modal
- `CollectionsTabNavigation` - Dual-button navigation
- `CrossNavigationButtons` - Modal header navigation
- `ManagePageFilters` - Operations-focused filters
- `CollectionPageFilters` - Discovery-focused filters
- `StatusBadge`, `HealthIndicator`, `DeploymentBadgeStack` - Shared utilities

---

## Appendix E: Pain Points Addressed

| Pain Point | Solution |
|------------|----------|
| Modal context mismatch | Clear "Deploy" CTA in collection modal; cross-navigation buttons |
| Sync status buried in discovery | Subtle status indicator on deployed artifact cards |
| Cross-page context loss | "Return to [origin]" button; URL state preservation |
| Project filter discovery | Prominent project dropdown in `/manage` header |
| Bulk operations hidden | Checkbox selection mode + batch action buttons |
| Unclear system boundaries | Page headers explaining purpose; consistent cross-linking |
| Deployment target friction | Project picker dropdown with recent projects |

---

**Report Version**: 2.0
**Last Updated**: 2026-02-01
**Changelog**:
- v2.0: Added approved design specification, implementation plan, user journeys, component specs
- v1.0: Initial analysis with three options
