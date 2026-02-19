---
status: inferred_complete
schema_version: 2
doc_type: prd
feature_slug: marketplace-source-enhancements
---
# Marketplace Source Enhancements v1

**Status**: Draft
**Created**: 2025-12-31
**PRD Owner**: Product Team
**Epic ID**: MSE-001
**Target Release**: v0.4.0

---

## Executive Summary

This PRD defines three incremental enhancements to the marketplace source catalog viewing experience that improve content presentation, filtering, and data quality. These features address current UX pain points: inability to view structured frontmatter, cumbersome type filtering via dropdown, and false positive artifacts cluttering catalog views.

**Key Deliverables**:
1. **Frontmatter Display Component** - Collapsible YAML frontmatter viewer in catalog entry modal
2. **Tabbed Artifact Type Filter** - Replace dropdown with horizontal tabs (similar to /manage page)
3. **"Not an Artifact" Marking** - Allow users to mark and hide false positives

**Value Proposition**: These enhancements improve catalog browsing efficiency by 40% (estimated based on reduced clicks and improved information density) while maintaining backend compatibility and reusing proven UI patterns.

---

## Context & Background

### Current System

**Marketplace Sources** (`/marketplace/sources/[id]`):
- GitHub repositories scanned for Claude Code artifacts
- Catalog entries displayed in card grid with confidence scores
- Type filtering via Select dropdown (lines 509-530 of `page.tsx`)
- CatalogEntryModal shows Overview (metadata + confidence) and Contents (file tree + viewer)

**Existing Patterns**:
- `/manage` page uses tabbed entity type filter (EntityTabs component)
- ContentPane component renders file content with breadcrumbs
- Backend has `extract_yaml_frontmatter()` utility (used for confidence scoring)
- Skip preferences pattern exists for per-project artifact exclusion

### Problem Drivers

1. **Frontmatter Visibility**: Skills/agents with YAML frontmatter show raw content, losing structured metadata visibility
2. **Filter Ergonomics**: Dropdown requires 2 clicks to change type; tabs would reduce to 1 click
3. **False Positives**: Heuristic detection includes non-artifacts (e.g., nested docs/); no UI to exclude them

### Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Clicks to filter by type | 2 | 1 |
| Frontmatter metadata visibility | 0% | 100% |
| False positive removal | Manual editing | Self-service UI |
| Code reuse (vs. new components) | N/A | >70% |

---

## Goals & Success Metrics

### Business Goals

1. **Reduce catalog browsing friction** - Faster type filtering, clearer content structure
2. **Improve data quality** - User-driven false positive exclusion reduces noise
3. **Maintain consistency** - Reuse proven patterns from /manage page

### User Goals

1. **Power users**: Quickly scan frontmatter metadata without opening raw files
2. **Explorers**: Efficiently filter by artifact type when browsing new sources
3. **Curators**: Remove false positives to keep catalogs clean

### Technical Goals

1. Reuse existing components (EntityTabs, ContentPane) where possible
2. Minimize backend changes (leverage existing frontmatter parsing)
3. Maintain responsive design and accessibility standards

### Success Metrics

**Phase 1 (Frontmatter Display)**:
- 100% of files with frontmatter display it in structured format
- <100ms rendering overhead for frontmatter parsing

**Phase 2 (Tabbed Filter)**:
- 50% reduction in clicks to change type filter (2 → 1)
- Match /manage page tab UX (visual parity)

**Phase 3 (Not an Artifact)**:
- Users can mark entries as "not an artifact" in <3 clicks
- Marked entries excluded from catalog view (0% visibility)
- Excluded entries remain recoverable via separate list

---

## Detailed Requirements

### Feature 1: Frontmatter Display Component

#### Overview

When viewing a catalog entry's Contents tab, detect YAML frontmatter in file content and render it in a structured, collapsible section above the raw content.

#### User Stories

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| F1-1 | As a **power user**, I want to see frontmatter metadata in a structured format so that I can quickly assess artifact properties without parsing YAML manually | - Frontmatter displayed as key-value pairs<br>- Keys in bold, values as plain text<br>- Collapsible section (default: expanded) |
| F1-2 | As a **content curator**, I want frontmatter separated from content so that I can focus on documentation or code without clutter | - "Show/Hide Frontmatter" toggle button<br>- State persists during modal session<br>- Smooth expand/collapse animation |
| F1-3 | As a **future feature consumer**, I want frontmatter data available in the Overview tab so that I can see structured metadata without switching tabs | - (Phase 2 enhancement)<br>- Parse frontmatter and display in Overview metadata section<br>- Show title, description, version from frontmatter |

#### Functional Requirements

**FR1.1 - Frontmatter Detection**
- **Trigger**: User opens CatalogEntryModal, navigates to Contents tab, file content loads
- **Detection**: Check if file path ends with `.md` and content starts with `---\n`
- **Parsing**: Use regex pattern `^---\s*\n(.*?)\n---\s*\n` (same as backend `extract_yaml_frontmatter()`)
- **Validation**: Attempt YAML parse; if invalid, show warning and hide frontmatter section

**FR1.2 - Frontmatter Display (Contents Tab)**
- **Location**: Top of ContentPane, above file breadcrumb
- **Structure**:
  ```tsx
  <FrontmatterDisplay
    frontmatter={parsedData}
    collapsed={false}  // default expanded
    onToggle={(collapsed) => setFrontmatterCollapsed(collapsed)}
  />
  ```
- **Layout**:
  - Collapsible section with header: "Frontmatter" + toggle icon (ChevronDown/ChevronUp)
  - Key-value grid: `<strong>{key}</strong>: {value}` per row
  - Arrays rendered as comma-separated values
  - Nested objects rendered as indented key-value pairs (1 level deep)
  - Max height: 300px, overflow-y: auto

**FR1.3 - FrontmatterDisplay Component (Reusable)**
- **File**: `skillmeat/web/components/entity/frontmatter-display.tsx`
- **Props**:
  ```tsx
  interface FrontmatterDisplayProps {
    frontmatter: Record<string, any>;
    collapsed?: boolean;
    onToggle?: (collapsed: boolean) => void;
    variant?: 'compact' | 'full';  // for future entity modal reuse
  }
  ```
- **Dependencies**: Radix `Collapsible` component
- **Accessibility**: Keyboard-navigable toggle, aria-expanded state

**FR1.4 - Content Rendering with Frontmatter Stripped**
- When frontmatter detected, strip it from displayed content
- Show only content after `---\n---\n` delimiter
- Preserve line numbers (if implemented) by offsetting start

#### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR1.1 | **Performance** | Frontmatter parsing <50ms for typical files (<10KB) |
| NFR1.2 | **Browser Compat** | Works in Chrome 120+, Firefox 120+, Safari 17+ |
| NFR1.3 | **Accessibility** | WCAG 2.1 AA compliant (keyboard nav, ARIA labels) |
| NFR1.4 | **Error Handling** | Invalid YAML shows warning, doesn't crash modal |

#### Design Specifications

**Visual Layout** (Contents Tab):
```
┌─────────────────────────────────────────────────┐
│ Frontmatter                            ▼ Hide   │
│ ┌───────────────────────────────────────────┐   │
│ │ **title**: My Awesome Skill               │   │
│ │ **version**: 1.2.0                        │   │
│ │ **tags**: code-gen, refactoring           │   │
│ │ **description**: Refactors code snippets  │   │
│ └───────────────────────────────────────────┘   │
├─────────────────────────────────────────────────┤
│ src / README.md                                 │
│ ┌───────────────────────────────────────────┐   │
│ │ # My Awesome Skill                        │   │
│ │                                           │   │
│ │ This skill refactors code...              │   │
│ └───────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Color Scheme** (using Tailwind):
- Background: `bg-muted/30` (light gray, subtle)
- Border: `border border-border` (default border color)
- Keys: `font-semibold text-foreground`
- Values: `text-muted-foreground`

#### Future Enhancements (Phase 2)

1. **Overview Tab Integration**:
   - Parse frontmatter from first `.md` file in artifact
   - Display title, version, description in Overview metadata section
   - Link to Contents tab for full frontmatter view

2. **Confidence Scoring Enhancement**:
   - Surface frontmatter score contribution in score breakdown tooltip
   - Highlight frontmatter-detected fields (e.g., "title" detected → +10 points)

---

### Feature 2: Tabbed Artifact Type Filter

#### Overview

Replace the current "All Types" Select dropdown (lines 509-530) with horizontal tabs matching the EntityTabs pattern from `/manage` page.

#### User Stories

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| F2-1 | As a **catalog browser**, I want to filter by artifact type with one click so that I can quickly explore specific types (e.g., only Skills) | - Horizontal tab bar above catalog grid<br>- Single click to change filter<br>- Active tab visually highlighted |
| F2-2 | As a **new user**, I want to see artifact counts per type so that I know what's available before filtering | - Tab labels show counts: "Skills (12)"<br>- Counts update when filters change<br>- Zero-count types still shown (grayed out) |
| F2-3 | As a **mobile user**, I want the tabs to be usable on smaller screens so that I can filter on phone/tablet | - Tabs responsive (scroll horizontally on mobile)<br>- Touch-friendly tap targets (min 44x44px)<br>- No layout breakage <640px width |

#### Functional Requirements

**FR2.1 - Tab Configuration**
- **Tabs**: All Types (default), Skills, Agents, Commands, MCP Servers, Hooks
- **Order**: Match ENTITY_TYPES from `/manage/components/entity-tabs.tsx`
- **Icons**: Use LucideIcons matching ENTITY_TYPES config
- **Counts**: Show `(countsByType[type] || 0)` next to label

**FR2.2 - Tab Behavior**
- **Selection**: Clicking tab updates `filters.artifact_type` state
- **URL Sync**: Update `?type=skill` query param (already exists, lines 222-224)
- **Active State**: Highlight active tab with `data-[state=active]` styling (Radix Tabs)
- **"All Types" Tab**: Sets `artifact_type: undefined` (shows all types)

**FR2.3 - Component Integration**
- **Location**: Replace lines 509-530 (current Select dropdown)
- **Component**: Reuse Radix `Tabs` primitives (same as EntityTabs)
- **Props**:
  ```tsx
  <Tabs value={filters.artifact_type || 'all'} onValueChange={handleTypeChange}>
    <TabsList>
      <TabsTrigger value="all">All Types ({totalCount})</TabsTrigger>
      <TabsTrigger value="skill">Skills ({countsByType.skill || 0})</TabsTrigger>
      {/* ... */}
    </TabsList>
  </Tabs>
  ```
- **State Handling**: Use existing `filters` state and `setFilters()` setter

**FR2.4 - Responsive Design**
- **Desktop (≥1024px)**: All tabs visible in single row
- **Tablet (640-1023px)**: Tabs scroll horizontally with fade indicators
- **Mobile (<640px)**: Tabs stack or show as compact chips (fallback to Select if needed)

#### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR2.1 | **Performance** | Tab click → filter update <100ms |
| NFR2.2 | **Accessibility** | Keyboard navigation (Tab, Arrow keys), aria-selected |
| NFR2.3 | **Visual Consistency** | Match /manage page tab styling exactly |

#### Design Specifications

**Visual Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│ [Search] [All Types (45)] [Skills (12)] [Agents (8)] ...       │
│ ════════                                                        │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                         │
│ │ Skill 1  │ │ Skill 2  │ │ Skill 3  │                         │
│ └──────────┘ └──────────┘ └──────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

**Active Tab Styling** (from EntityTabs):
- Border: `border-b-2 border-primary` (blue underline)
- Background: `data-[state=active]:bg-transparent`
- Text: `data-[state=active]:text-primary`

**Tab Count Badge**:
- Color: `text-muted-foreground` (gray for inactive), `text-primary` (active)
- Font: Same size as tab label
- Zero counts: Show as "(0)", grayed out but still clickable

#### Migration Strategy

1. **Phase 1**: Add tabs ABOVE existing Select dropdown (both visible)
2. **Phase 2**: A/B test with feature flag (50/50 split)
3. **Phase 3**: Remove Select dropdown after 1 week of testing
4. **Rollback**: Keep Select code commented out for easy revert

---

### Feature 3: "Not an Artifact" Marking

#### Overview

Allow users to mark catalog entries as false positives, hiding them from the main catalog view while keeping them recoverable via a separate "Excluded" list.

#### User Stories

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| F3-1 | As a **source curator**, I want to mark false positives (e.g., nested docs/) as "not an artifact" so that they don't clutter my catalog view | - "Not an Artifact" button/link on each card<br>- Confirmation dialog before marking<br>- Marked entries disappear from grid immediately |
| F3-2 | As a **source manager**, I want to review excluded entries so that I can undo mistakes or audit exclusions | - "Excluded Artifacts" link/tab on source page<br>- List shows all marked entries with "Restore" action<br>- Restore immediately returns entry to catalog |
| F3-3 | As a **bulk importer**, I want excluded entries to skip "Select All" so that I don't accidentally import false positives | - "Select All" button skips entries with `status: excluded`<br>- Excluded count shown in filter stats<br>- Import API rejects excluded entries |

#### Functional Requirements

**FR3.1 - Backend Schema Extension**
- **New Status**: Add `excluded` to `CatalogStatus` enum (currently: new, updated, removed, imported)
- **Database**: Add column to `MarketplaceCatalogEntry` table
  ```python
  excluded_at: Optional[datetime] = None
  excluded_reason: Optional[str] = None  # future: user-provided reason
  ```
- **Migration**: Alembic migration to add columns (nullable, default NULL)

**FR3.2 - Backend API Endpoint**
- **Route**: `PATCH /marketplace/sources/{source_id}/artifacts/{entry_id}/exclude`
- **Request Body**:
  ```json
  {
    "excluded": true,
    "reason": "Not a valid artifact - documentation file"  // optional
  }
  ```
- **Response**: Updated CatalogEntryResponse with `status: "excluded"`
- **Access Control**: No auth required (future: add API key check)

**FR3.3 - Frontend UI (Catalog Card)**
- **Location**: CatalogCard component, next to "Import" button
- **Control**: Link/button: "Not an Artifact" (text-muted-foreground, hover underline)
- **Dialog**: Confirmation with message:
  ```
  Mark this as not an artifact?

  This will hide "{entry.name}" from the catalog. You can restore it later from the Excluded list.

  [Cancel] [Mark as Excluded]
  ```
- **Behavior**: On confirm, call API → update local state → remove card from grid

**FR3.4 - Frontend UI (Excluded List)**
- **Location**: New section on source detail page, below catalog grid
- **Toggle**: "Show Excluded Artifacts (N)" collapsible section (default: collapsed)
- **List**: Table with columns: Name, Path, Excluded At, Actions
- **Actions**: "Restore" button → calls `PATCH .../exclude` with `excluded: false`

**FR3.5 - Filtering Behavior**
- **Default**: Excluded entries hidden from catalog view
- **Select All**: Skip entries with `status: excluded` (already excluded from importable entries check)
- **Import API**: Reject excluded entries with error: "Entry X is excluded as not an artifact"

**FR3.6 - Status Badge**
- **Excluded Status**: Gray badge with "Excluded" label (similar to "Removed")
- **Color**: `border-gray-400 text-gray-600 bg-gray-100 dark:bg-gray-900`

#### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR3.1 | **Performance** | Mark/restore action <500ms round-trip |
| NFR3.2 | **Data Integrity** | Excluded entries remain in DB (soft delete) |
| NFR3.3 | **Recoverability** | Restore action undoes exclusion completely |
| NFR3.4 | **Audit Trail** | Track excluded_at timestamp for analytics |

#### Design Specifications

**Catalog Card Layout** (with exclusion link):
```
┌──────────────────────────────────────┐
│ [Skill] [New]           [✓]          │
│ my-awesome-skill                     │
│ src/skills/my-awesome-skill          │
│ Confidence: 85%    View on GitHub    │
│ ┌──────────────────────────────────┐ │
│ │ Import                           │ │
│ └──────────────────────────────────┘ │
│ Not an artifact                      │ ← New link
└──────────────────────────────────────┘
```

**Excluded List Section**:
```
┌─────────────────────────────────────────────────┐
│ ▼ Show Excluded Artifacts (3)                   │
│ ┌───────────────────────────────────────────┐   │
│ │ Name            │ Path        │ Excluded  │   │
│ │─────────────────┼─────────────┼──────────│   │
│ │ fake-skill      │ docs/...    │ 2d ago  │   │
│ │ [Restore]       │             │         │   │
│ └───────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

#### Future Enhancements (Phase 2)

1. **Exclusion Reasons**: Add optional textarea in confirmation dialog
2. **Bulk Exclusion**: Multi-select checkboxes → "Exclude Selected" button
3. **Per-Project Exclusions**: Sync to `.claude/.skillmeat-skip.toml` (using SkipPreferenceManager pattern)
4. **Export Exclusions**: Download excluded entries as JSON for manual review

---

## Scope

### In Scope

**Frontend**:
- Frontmatter parsing and display component (Feature 1)
- Tabbed type filter UI (Feature 2)
- Exclusion UI (card link, confirmation dialog, excluded list) (Feature 3)

**Backend**:
- Database schema update for `excluded` status (Feature 3)
- PATCH endpoint for exclusion/restoration (Feature 3)
- No changes needed for Features 1-2 (frontend-only)

**Testing**:
- Unit tests for FrontmatterDisplay component
- Integration tests for exclusion API endpoint
- E2E tests for tab filtering and exclusion workflows

### Out of Scope

**Deferred to Phase 2**:
- Frontmatter display in Overview tab (Feature 1 enhancement)
- Bulk exclusion UI (Feature 3 enhancement)
- Per-project exclusion sync (Feature 3 enhancement)
- Exclusion reason tracking (backend ready, UI deferred)

**Not Planned**:
- AI-powered false positive detection (manual user marking only)
- Confidence score adjustments based on exclusions
- Cross-source exclusion rules (exclusions are source-specific)

---

## Dependencies

### Technical Dependencies

| Dependency | Type | Purpose | Status |
|------------|------|---------|--------|
| Radix Tabs | UI Primitive | Tabbed filter (F2) | ✅ In use (EntityTabs) |
| Radix Collapsible | UI Primitive | Frontmatter toggle (F1) | ✅ Available in shadcn |
| YAML Parser | npm | Frontmatter parsing (F1) | ✅ Already used in backend |
| extract_yaml_frontmatter | Backend Util | Pattern reference (F1) | ✅ `skillmeat/utils/metadata.py` |
| TanStack Query | Data Layer | Exclusion mutations (F3) | ✅ In use for API calls |

### Data Dependencies

| Dependency | Source | Required For | Availability |
|------------|--------|--------------|--------------|
| countsByType | Backend API | Tab counts (F2) | ✅ `catalogData.pages[0].counts_by_type` |
| Frontmatter YAML | File content | Parsing (F1) | ✅ Via `useCatalogFileContent` hook |
| Catalog status enum | Backend schema | Exclusion status (F3) | ⚠️ Needs `excluded` value added |

### Integration Points

1. **Feature 1 ↔ ContentPane**: FrontmatterDisplay component integrates into existing ContentPane
2. **Feature 2 ↔ Filters State**: Tabs update existing `filters.artifact_type` state (no new state)
3. **Feature 3 ↔ Import Flow**: Excluded entries skip "Select All" (existing importable check)

---

## Risks & Mitigations

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **YAML parsing errors break modal** | Medium | High | Wrap parse in try/catch; show warning, hide frontmatter section on error |
| **Tab overflow on small screens** | Medium | Medium | Implement horizontal scroll with fade indicators; test on 375px viewport |
| **Database migration conflict** | Low | High | Use Alembic; test migration on copy of prod DB before deploy |
| **Excluded entries reappear after rescan** | Medium | Medium | Preserve `excluded` status during rescan (exclude from status updates) |

### UX Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Users accidentally exclude valid artifacts** | Medium | Medium | Confirmation dialog with clear messaging; easy Restore action |
| **Frontmatter clutters small files** | Low | Low | Default to expanded but collapsible; test with real-world artifacts |
| **Tab counts confuse users** | Low | Low | Use tooltips to explain counts (e.g., "12 skills detected in this source") |

### Migration Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Users prefer dropdown over tabs** | Low | Medium | A/B test for 1 week; keep dropdown code for rollback |
| **Breaking change to API schema** | Low | High | Make `excluded` status optional; backward-compatible with existing clients |

---

## Phased Implementation Approach

### Phase 1: Frontend-Only Features (Week 1)

**Deliverables**:
- Feature 1: Frontmatter Display Component
- Feature 2: Tabbed Artifact Type Filter

**Tasks**:
1. Create FrontmatterDisplay component (`components/entity/frontmatter-display.tsx`)
2. Integrate into ContentPane (detect `.md` files, parse frontmatter, render component)
3. Replace Select dropdown with Tabs component (reuse EntityTabs pattern)
4. Update URL sync logic for tab changes
5. Add unit tests for FrontmatterDisplay
6. E2E test: navigate to Contents tab, verify frontmatter display

**No Backend Changes**: Features 1-2 use existing APIs and data

### Phase 2: Backend Schema & API (Week 2)

**Deliverables**:
- Feature 3 (Backend): Database schema, exclusion API

**Tasks**:
1. Add `excluded` to CatalogStatus enum (`types/marketplace.ts`)
2. Alembic migration: add `excluded_at`, `excluded_reason` columns
3. Update `MarketplaceCatalogEntry` model in `cache/models.py`
4. Add PATCH `/marketplace/sources/{id}/artifacts/{entry_id}/exclude` endpoint
5. Update catalog list endpoint to filter out excluded by default (add `?include_excluded=true` param)
6. Add unit tests for exclusion repository methods
7. Add integration tests for exclusion API

### Phase 3: Frontend Exclusion UI (Week 2-3)

**Deliverables**:
- Feature 3 (Frontend): Exclusion link, dialog, excluded list

**Tasks**:
1. Add "Not an Artifact" link to CatalogCard component
2. Create ConfirmExclusionDialog component (Radix Dialog)
3. Add exclusion mutation hook (`useExcludeCatalogEntry`)
4. Update catalog grid to remove excluded cards on mutation success
5. Add "Show Excluded Artifacts" collapsible section (Table component)
6. Add "Restore" action with mutation hook (`useRestoreCatalogEntry`)
7. Update "Select All" logic to skip excluded entries
8. E2E test: mark entry as excluded, verify it disappears, restore it

### Phase 4: Polish & Release (Week 3)

**Deliverables**:
- Bug fixes, performance tuning, documentation

**Tasks**:
1. Fix any bugs found during testing
2. Performance audit: ensure <100ms tab clicks, <50ms frontmatter parsing
3. Accessibility audit: keyboard nav, ARIA labels, screen reader testing
4. Update API documentation (OpenAPI spec)
5. Update user documentation (guide to exclusion feature)
6. Release notes for v0.4.0

---

## Acceptance Criteria

### Feature 1: Frontmatter Display

- [ ] **AC1.1**: When viewing a `.md` file in Contents tab, frontmatter (if present) displays in collapsible section above content
- [ ] **AC1.2**: Frontmatter section shows "Show/Hide Frontmatter" toggle, default expanded
- [ ] **AC1.3**: Frontmatter renders as key-value pairs with bold keys
- [ ] **AC1.4**: Invalid YAML shows warning, does not crash modal
- [ ] **AC1.5**: Content displayed below frontmatter has frontmatter stripped (shows only post-`---` content)
- [ ] **AC1.6**: FrontmatterDisplay component is reusable (exported from `components/entity/`)

### Feature 2: Tabbed Artifact Type Filter

- [ ] **AC2.1**: Horizontal tabs replace Select dropdown in filters bar
- [ ] **AC2.2**: Tabs show: All Types, Skills, Agents, Commands, MCP Servers, Hooks
- [ ] **AC2.3**: Each tab label shows count: "Skills (12)"
- [ ] **AC2.4**: Active tab highlighted with blue underline (matches /manage page)
- [ ] **AC2.5**: Clicking tab updates catalog filter and URL (?type=skill)
- [ ] **AC2.6**: Tabs responsive on mobile (horizontal scroll if needed)
- [ ] **AC2.7**: Zero-count types still shown, grayed out but clickable

### Feature 3: "Not an Artifact" Marking

**Backend**:
- [ ] **AC3.1**: Database has `excluded_at` and `excluded_reason` columns (nullable)
- [ ] **AC3.2**: `PATCH /marketplace/sources/{id}/artifacts/{entry_id}/exclude` endpoint exists
- [ ] **AC3.3**: Endpoint accepts `{"excluded": true}` and updates status to `excluded`
- [ ] **AC3.4**: Endpoint accepts `{"excluded": false}` to restore entry
- [ ] **AC3.5**: Catalog list endpoint excludes `status: excluded` by default
- [ ] **AC3.6**: Rescan preserves `excluded` status (does not overwrite)

**Frontend**:
- [ ] **AC3.7**: Each catalog card shows "Not an Artifact" link next to Import button
- [ ] **AC3.8**: Clicking link opens confirmation dialog
- [ ] **AC3.9**: Confirming marks entry as excluded, card disappears from grid
- [ ] **AC3.10**: "Show Excluded Artifacts (N)" collapsible section appears below grid
- [ ] **AC3.11**: Excluded list shows Name, Path, Excluded At columns
- [ ] **AC3.12**: "Restore" button in excluded list restores entry to catalog
- [ ] **AC3.13**: "Select All" skips excluded entries
- [ ] **AC3.14**: Import API rejects excluded entries with error message

### Cross-Cutting

- [ ] **AC-X1**: All features maintain accessibility (keyboard nav, ARIA labels)
- [ ] **AC-X2**: All features work in Chrome 120+, Firefox 120+, Safari 17+
- [ ] **AC-X3**: All features maintain responsive design (<640px mobile, ≥1024px desktop)
- [ ] **AC-X4**: Unit tests cover FrontmatterDisplay, exclusion hooks, tab filtering
- [ ] **AC-X5**: E2E tests cover frontmatter display, tab clicks, exclusion workflow

---

## Appendices

### Appendix A: Reference Implementations

**EntityTabs Component** (`app/manage/components/entity-tabs.tsx`):
- Lines 29-52: TabsList with dynamic tab generation from ENTITY_TYPES
- Uses Radix Tabs with URL sync via `useSearchParams`

**ContentPane Component** (`components/entity/content-pane.tsx`):
- Lines 322-526: Main component with breadcrumb, ScrollArea, ContentDisplay
- Supports `readOnly` prop, edit mode, truncation warnings

**YAML Frontmatter Extraction** (`skillmeat/utils/metadata.py`):
- Lines 12-52: `extract_yaml_frontmatter()` function
- Regex: `^---\s*\n(.*?)\n---\s*\n` with `re.DOTALL`
- Returns `Dict[str, Any]` or `None`

**Skip Preferences** (`skillmeat/core/skip_preferences.py`):
- Pattern for per-project exclusion lists (`.claude/.skillmeat-skip.toml`)
- Provides template for future exclusion sync feature

### Appendix B: Type Definitions

**CatalogStatus Enum** (add `excluded`):
```typescript
// skillmeat/web/types/marketplace.ts
export type CatalogStatus = 'new' | 'updated' | 'removed' | 'imported' | 'excluded';
```

**Exclusion API Schema**:
```typescript
// Request
interface ExcludeEntryRequest {
  excluded: boolean;
  reason?: string;  // optional, for future use
}

// Response (same as CatalogEntryResponse with status: 'excluded')
```

### Appendix C: Database Schema

**Migration** (Alembic):
```python
# versions/YYYYMMDD_HHMM_add_exclusion_to_catalog.py
def upgrade():
    op.add_column('marketplace_catalog_entries',
        sa.Column('excluded_at', sa.DateTime(), nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('excluded_reason', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('marketplace_catalog_entries', 'excluded_reason')
    op.drop_column('marketplace_catalog_entries', 'excluded_at')
```

**Model Update**:
```python
# skillmeat/cache/models.py (MarketplaceCatalogEntry)
excluded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
excluded_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

### Appendix D: Testing Checklist

**Unit Tests**:
- [ ] FrontmatterDisplay renders key-value pairs correctly
- [ ] FrontmatterDisplay handles invalid YAML gracefully
- [ ] Tab filtering updates state and URL params
- [ ] Exclusion mutation calls API with correct payload
- [ ] Restore mutation re-enables entry

**Integration Tests**:
- [ ] PATCH /exclude endpoint updates database
- [ ] GET /catalog endpoint excludes excluded entries by default
- [ ] Rescan preserves excluded status

**E2E Tests**:
- [ ] Navigate to Contents tab → frontmatter displays
- [ ] Toggle frontmatter visibility → content adjusts
- [ ] Click tab → catalog filters, URL updates
- [ ] Mark entry as excluded → disappears from grid
- [ ] Open excluded list → entry visible, click Restore → returns to catalog

---

**End of PRD**
