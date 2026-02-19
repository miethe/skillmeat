---
title: 'PRD: Marketplace Folder View'
description: 'Two-pane master-detail layout for marketplace sources: semantic tree
  navigation + folder detail view'
audience:
- ai-agents
- developers
tags:
- prd
- planning
- feature
- marketplace
created: 2026-01-28
updated: '2026-02-07'
category: product-planning
status: completed
related:
- REQ-20260123-skillmeat
- marketplace-source-detection-improvements-v1
schema_version: 2
doc_type: prd
feature_slug: marketplace-folder-view
---

# Feature Brief & Metadata

**Feature Name:**
> Marketplace Folder View (Two-Pane Master-Detail)

**Filepath Name:**
> `marketplace-folder-view-v1`

**Author:**
> Claude Opus 4.5 (AI Agent Orchestrator)

**Related Epic(s)/PRD ID(s):**
> REQ-20260123-skillmeat

**Design Reference:**
> Gemini design spec: `/docs/project_plans/design-specs/marketplace-folder-view-v1.md`

---

## 1. Executive Summary

This feature replaces the collapsible in-place tree view with a **two-pane master-detail layout** for marketplace source exploration. The left pane shows a semantically-filtered tree (hiding root folders and artifact containers), and the right pane displays folder context, metadata, artifacts grouped by type, and a prominent "Import All" bulk action. Users navigate folders on the left; the right pane updates to show that folder's contents and metadata. This design reduces navigation complexity, surfaces bulk import actions, and provides a clear information hierarchy for exploring large repositories.

**New in this version**: Support for folders that contain BOTH direct artifacts AND subfolders, with visual indicators and subfolders section in detail pane.

**Priority:** HIGH

**Key Outcomes:**
- Users navigate by semantic categories (e.g., "Productivity Tools") instead of raw directory paths
- Bulk import ("Import All in Folder") reduces multi-artifact imports from 10+ clicks to 1
- Discovery time for large sources reduced 40-60% via master-detail clarity
- Existing filters, URL state, and view mode preferences fully integrated
- Mixed-content folders (with both direct artifacts and subfolders) clearly identified and fully usable

---

## 2. Context & Background

### Current State
- Marketplace source detail page displays artifacts in grid, list, or folder view
- Folder view uses expandable tree with explicit depth controls
- Each artifact has `path` field (e.g., `skills/dev/frontend-dev`)
- View mode persists to localStorage
- Rich filtering: type, confidence, status, search

### Problem Space
1. **Cognitive load**: Expanded in-place tree forces users to mentally track hierarchy while viewing items
2. **Inefficient bulk actions**: Importing related artifacts requires individual clicks
3. **No folder context**: Users can't see descriptions or metadata for folders/suites
4. **Deep nesting**: 4+ levels of expansion create visual clutter and scrolling fatigue
5. **Semantic confusion**: Raw paths (e.g., `src/main/plugins/productivity`) lack domain meaning
6. **Mixed-content confusion**: Folders with both direct artifacts and subfolders lack clear visual distinction

### Design Inspiration
- GitHub code browser (master-detail repo navigation)
- VS Code file explorer with sidebar
- Design system component library trees (Radix UI patterns)
- npm package browser (semantic categories)

---

## 3. Problem Statement

**User Story Format:**
> "As a developer exploring a marketplace source with 200+ artifacts organized across 10+ folders, I want to see a clear folder hierarchy on the left and detailed folder contents on the right, including the ability to navigate subfolders and import artifacts directly from parent folders, so I can quickly navigate to related artifacts and import entire suites without repetitive clicks."

---

## 4. Goals & Success Metrics

### Primary Goals

**Goal 1: Semantic Navigation**
- Left tree hides root containers and artifact type folders
- Shows only intermediate meaningful directories (e.g., "Productivity", "Vibe Guide")
- First folder auto-selects on load; right pane populates immediately

**Goal 2: Efficient Bulk Actions**
- "Import All in [Folder]" button enables one-click suite imports
- Reduces import overhead from 10+ individual clicks to 1 + confirmation
- Visible, accessible button in folder detail header

**Goal 3: Clear Information Hierarchy**
- Folder metadata (parent category, description from README or AI summary) displayed
- Artifacts grouped by type (Agents, Commands, MCP Servers, etc.)
- Existing filters apply to right pane contents
- URL state and localStorage preferences maintained

**Goal 4: Intuitive Mixed-Content Handling**
- Folders with both direct artifacts and subfolders clearly identified
- Users see both artifact count (direct) and descendant count at a glance
- Subfolders section in detail pane enables nested exploration without tree navigation
- Natural progression from viewing folder artifacts to exploring subfolders

### Success Metrics

| Metric | Baseline | Target | Method |
|--------|----------|--------|--------|
| **Avg. clicks to import suite** | 12 | 2 | User testing; task completion |
| **Discovery time** | ~45s (flat search) | ~12s (master-detail nav) | Time to locate 3 related artifacts |
| **Adoption rate** | 0% | 40% | Analytics; view mode toggle events |
| **Performance** (right pane render) | N/A | <200ms | DevTools profiling |
| **Mixed-folder clarity** | 0% | 85% user understands content | User testing; task success rate |

---

## 5. Requirements

### 5.1 Functional Requirements

| ID | Requirement | Priority | Notes |
| :-: | ----------- | :------: | ----- |
| FR-1 | Two-pane layout: left tree (~25%) + right detail (~75%) | Must | Master-detail pattern; responsive on mobile |
| FR-2 | Semantic tree filters roots and leaf containers | Must | Exclude: `plugins/`, `src/`; `commands/`, `agents/` |
| FR-3 | Tree shows intermediate directories (meaningful categories) | Must | E.g., "Productivity", "Vibe Guide", domain-specific folders |
| FR-4 | First folder auto-selects on page load | Must | Right pane populates with first valid folder's contents |
| FR-5 | Folder detail header displays title + parent chip + description | Must | Description from README or AI summary; parent category chip |
| FR-6 | "Import All in [Folder]" bulk import button | Must | Prominent button; imports all artifacts in current folder at once |
| FR-7 | Artifacts grouped by type (Agents, Commands, MCP Servers, etc.) | Must | Section headers per type; existing card component for each |
| FR-8 | Existing filters apply to right pane artifacts | Must | Type, confidence, search filters reduce shown artifacts |
| FR-9 | Clicking artifact card body opens detail modal | Must | Import button separate from card navigation |
| FR-10 | Tree states: Default, Hover (light gray), Selected (purple/blue), Expanded/Collapsed | Must | Keyboard nav support; ARIA labels |
| FR-11 | Persist folder view mode + selected folder to localStorage | Must | Return users see same folder selected |
| FR-12 | Depth configuration (Auto, Top Level, 1/2/3 Levels) as fallback | Should | For edge cases; not primary UI control |
| **FR-NEW-1** | **Tree Node Badge with Direct + Total Counts** | **Must** | **Display "(N)" badge for direct artifact count; "[M]" badge for total descendants (hover-only to reduce clutter); Example: "Productivity (2) [10]"** |
| **FR-NEW-2** | **Visual Indicator for Mixed Folders** | **Must** | **Show subtle indicator (dot or modified icon) on folders with BOTH direct artifacts AND subfolders; enables quick visual scan; Example: "📁• Productivity"** |
| **FR-NEW-3** | **Subfolders Section in Detail Pane** | **Must** | **When selected folder contains subfolders, add "Subfolders" section at bottom of detail pane; display subfolder cards with folder icon, name, artifact count, "Click to explore" affordance; clicking navigates tree and updates pane** |

### 5.2 Non-Functional Requirements

**Performance:**
- Right pane renders <200ms for 1000 artifacts
- Lazy render tree nodes (no full tree DOM until expanded)

**Accessibility:**
- WCAG 2.1 AA compliance
- Full keyboard nav: Tab, Arrow keys (Up/Down within tree, Left/Right to collapse/expand)
- ARIA labels on folders (e.g., "Folder: Productivity, 45 artifacts, selected, expanded")
- Focus indicators; roving tabindex for tree navigation

**Reliability:**
- Graceful handling of malformed paths, missing READMEs
- Fallback to flat view if tree building fails
- No console errors

**Security:**
- No new API endpoints; uses existing catalog data
- Path parsing client-side only; no injection vectors

---

## 6. Scope

### In Scope
- **Two-pane layout**: Master (semantic tree) + Detail (folder contents)
- **Semantic tree component**: Smart filtering rules (exclude roots/leafs)
- **Folder detail header**: Title, parent chip, description, bulk import button
- **Artifact grouping**: Type-based section headers with existing card component
- **Mixed-content handling**: Direct count badges, total descendant count badges, mixed-folder indicator
- **Subfolders section**: Clickable subfolder cards in detail pane for nested exploration
- **Filter integration**: All existing filters apply to right pane
- **localStorage persistence**: Folder selection + view mode retained
- **Keyboard navigation & ARIA**: Full accessibility support
- **Responsive design**: Works on mobile (stacked panes) and desktop

### Out of Scope
- **API changes**: Uses existing catalog data
- **AI summary generation backend**: Descriptions come from existing README or manual entry
- **Per-folder sorting**: Sort only works across all artifacts
- **Virtualization**: Implement only if performance issues arise
- **URL state for folder selection**: Could add in future (e.g., `?folder=productivity`)

---

## 7. Dependencies & Assumptions

### External Dependencies
- Radix UI: Collapsible, Select primitives (in shadcn/ui)
- shadcn/ui: Button, Badge, Card, Chip components
- Lucide React: ChevronRight, Folder, File, FolderOpen icons

### Internal Dependencies
- CatalogEntry type (has `path` field)
- Existing artifact card component
- useSourceCatalog hook (provides filtered data)
- useViewMode hook (view preference persistence)

### Assumptions
- Repository paths use forward slashes (`/`) as separator
- Semantic category names appear between root and leaf folders
- Root folders: `plugins/`, `src/`, `dist/`, similar conventional roots
- Leaf artifact containers: `commands/`, `agents/`, `prompts/`, `tools/`
- Users tolerate 4-5 nesting levels in tree; deeper trees use breadcrumbs
- Folders have optional `README.md` in directory; else show AI summary placeholder
- Folders can contain BOTH direct artifacts (files at that level) AND subfolders simultaneously
- Artifact count badges do not impact accessibility (ARIA labels sufficient for screen readers)

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
| ----- | :----: | ---------- |
| **Semantic filtering errors** (wrong roots/leafs hidden) | High | Validate rules against 5+ sample repos before Phase 1; add config override per source |
| **Right pane re-render on filter change** (jank) | Medium | Lazy render collapsed tree nodes; memoize artifact lists; Phase 3 optimize |
| **Auto-select first folder fails** (edge case repos) | Low | Fallback to flat view with user notice; manual folder config per source |
| **Description missing (no README)** | Low | Show placeholder "No description"; Phase 2 add AI summary backend |
| **Mobile layout breaks** (both panes too wide) | Medium | Stack panes vertically on <1024px; toggle sidebar with menu button |
| **Mixed-folder visual indicator unclear** | Medium | User testing Phase 1; iterate on icon choice based on feedback |
| **Subfolders section not discoverable** | Medium | Placement at bottom of detail pane; highlight with subtle color or border |

---

## 9. Target State (Post-Implementation)

### User Experience
1. User navigates to source detail page
2. Folder view renders: left tree with semantic categories, right pane shows first folder's contents
3. Folder title, parent chip, and description appear at top of right pane
4. Tree nodes show badge: folder name (N) or folder name (N) [M] for mixed content
5. Folders with both artifacts and subfolders show visual indicator (dot or icon)
6. Artifacts grouped by type (Agents, Commands, etc.) with "Import All in [Folder]" button prominent
7. If folder has subfolders, "Subfolders" section appears at bottom with clickable folder cards
8. User clicks subfolder card → left tree expands and navigates, right pane updates
9. User can apply filters; right pane re-renders showing only matching artifacts
10. Click artifact card → opens detail modal; click Import button → imports individual artifact
11. View returns to same folder next visit (localStorage)

### Component Hierarchy
```
 SourceDetailPage (server component)
├── SourceToolbar
│   ├── ViewModeToggle (add 'folder' mode)
│   └── [existing filters...]
└── SourceContent (client component)
    ├── SemanticTree (left pane)
    │   └── FolderNode[] (recursive)
    │       ├── Chevron + Folder icon + Name + Badge(s)
    │       ├── Visual indicator (mixed-content dot)
    │       └── [expanded children]
    └── FolderDetailPane (right pane)
        ├── FolderDetailHeader
        │   ├── Title
        │   ├── Parent metadata chip
        │   ├── Description
        │   └── "Import All" button
        ├── ArtifactGroups
        │   └── ArtifactTypeSection[] (Agents, Commands, etc.)
        │       └── ArtifactCard[]
        └── SubfoldersSection (if applicable)
            └── SubfolderCard[] (folder icon, name, count, click handler)
```

---

## 10. Overall Acceptance Criteria (Definition of Done)

### Functional Acceptance
- [ ] Two-pane layout renders correctly (left ~25%, right ~75%)
- [ ] Semantic tree filters roots and leaf containers correctly
- [ ] First folder auto-selects and right pane populates
- [ ] Tree nodes show direct artifact count badge (N)
- [ ] Tree nodes show total descendant count badge [M] on hover (or hidden by default)
- [ ] Mixed-content folders (direct + subfolders) show visual indicator
- [ ] Folder detail header shows title, parent chip, description, bulk import button
- [ ] "Import All in [Folder]" imports all artifacts in folder
- [ ] Artifacts grouped by type with section headers
- [ ] Existing filters apply to right pane artifacts
- [ ] Clicking artifact card → opens detail modal
- [ ] Folder selection persisted to localStorage
- [ ] View mode toggle includes "folder" option
- [ ] Subfolders section appears when folder has subfolders
- [ ] Subfolder cards are clickable; clicking navigates tree and updates detail pane
- [ ] All existing filters (type, confidence, search) work seamlessly

### Technical Acceptance
- [ ] No API changes; uses existing CatalogEntry.path field
- [ ] Follows Next.js 15 App Router patterns
- [ ] Component conventions (shadcn/ui, Radix primitives, named exports)
- [ ] TypeScript fully typed; no `any` types
- [ ] Tree builder unit tests >80% coverage
- [ ] Performance: right pane renders <200ms for 1000 artifacts
- [ ] Lazy rendering for tree nodes (collapsed content not in DOM)
- [ ] Direct artifacts properly separated from subfolders in tree structure

### Quality Acceptance
- [ ] Unit tests: tree builder, semantic filter logic, count calculations
- [ ] Component tests: tree navigation, artifact grouping, filter application, subfolders section
- [ ] E2E tests: folder selection → right pane update → subfolder navigation → filter → import
- [ ] Accessibility: WCAG 2.1 AA (keyboard nav, ARIA, focus indicators)
- [ ] No performance regressions in source page load or filter responsiveness
- [ ] Visual consistency with existing card/button styling
- [ ] Mixed-folder indicator clear and not visually cluttered

---

## 11. Implementation Phases

### Phase 1: Two-Pane Layout + Semantic Tree (4 days)
- Two-pane layout component with responsive breakpoints
- Semantic tree builder (filter roots/leafs; show intermediates)
- FolderNode component with expand/collapse
- **NEW**: Direct count badges + total count badges (hidden by default)
- **NEW**: Mixed-folder visual indicator
- First folder auto-select
- Tree keyboard navigation (arrow keys, expand/collapse)
- Unit tests for tree builder + semantic filters

### Phase 2: Folder Detail Pane + Bulk Import + Subfolders (3 days)
- FolderDetailHeader (title, parent chip, description)
- "Import All in [Folder]" button with confirmation modal
- ArtifactTypeSection with grouping logic
- Artifacts displayed via existing card component
- Filter application to right pane
- **NEW**: Subfolders section component
- **NEW**: Subfolder card component (folder icon, name, count, click handler)
- localStorage persistence for folder selection
- E2E tests for complete workflow including subfolder navigation

### Phase 3: Accessibility & Polish (2 days)
- Full keyboard nav (Tab, Arrow keys, Enter, Space)
- ARIA labels (folder state, item count, parent context)
- **NEW**: ARIA labels for badge counts and mixed-folder indicator
- **NEW**: Semantic roles for subfolders section
- Focus management and roving tabindex
- Screen reader testing (NVDA, JAWS, VoiceOver)
- Accessibility audit (automated + manual)
- Visual refinement (spacing, colors, responsive tweaks)
- Performance profiling (render time, filter responsiveness)

---

## 12. Files to Create

- `/skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx` - Left pane tree navigation
- `/skillmeat/web/app/marketplace/sources/[id]/components/folder-node.tsx` - Tree node component
- `/skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx` - Right pane container
- `/skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx` - Title, parent chip, description, bulk import
- `/skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx` - Type grouping with section header
- `/skillmeat/web/app/marketplace/sources/[id]/components/subfolders-section.tsx` - **NEW**: Subfolders grid/list section
- `/skillmeat/web/app/marketplace/sources/[id]/components/subfolder-card.tsx` - **NEW**: Individual subfolder card
- `/skillmeat/web/lib/tree-filter-utils.ts` - Semantic filtering (exclude roots/leafs)
- `/skillmeat/web/lib/tree-builder.ts` - Tree structure creation from paths

## Files to Modify

- `/skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Two-pane layout
- `/skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx` - Folder view toggle
- `/skillmeat/web/CLAUDE.md` - Document new patterns

---

## 13. User Stories & Estimates

| Story ID | Title | Acceptance Criteria | Est. |
|----------|-------|-------------------|------|
| **FEAT-FV-1.1** | Two-pane layout | Layout renders; responsive; ~25/75 split | 3 pts |
| **FEAT-FV-1.2** | Semantic tree builder | Filters roots/leafs; shows intermediates; unit tests | 3 pts |
| **FEAT-FV-1.3** | FolderNode component with badges | Expand/collapse; chevron; count badges; ARIA | 3 pts |
| **FEAT-FV-1.4** | First folder auto-select | Right pane populates on load | 1 pt |
| **FEAT-FV-1.5** | **Mixed-folder visual indicator** | **Folder with direct + subfolders shows dot/icon; keyboard accessible** | **2 pts** |
| **FEAT-FV-2.1** | FolderDetailHeader | Title, parent chip, description, bulk import button | 3 pts |
| **FEAT-FV-2.2** | Artifact grouping by type | ArtifactTypeSection; existing card component | 2 pts |
| **FEAT-FV-2.3** | "Import All" action | Bulk import all artifacts in folder; confirmation | 3 pts |
| **FEAT-FV-2.4** | Filter integration | Filters apply to right pane artifacts | 2 pts |
| **FEAT-FV-2.5** | localStorage persistence | Folder selection + view mode retained | 1 pt |
| **FEAT-FV-2.6** | **Subfolders section component** | **Renders subfolder cards; positioned at bottom of detail pane; responsive grid** | **2 pts** |
| **FEAT-FV-2.7** | **Subfolder card component** | **Folder icon, name, artifact count, click handler; navigates tree and updates pane** | **2 pts** |
| **FEAT-FV-3.1** | Full keyboard nav | Arrow keys, Tab, Enter/Space; tree navigation | 2 pts |
| **FEAT-FV-3.2** | ARIA labels & roles | Semantic labels for folders, item counts, badge context | 2 pts |
| **FEAT-FV-3.3** | Accessibility audit | WCAG 2.1 AA; screen reader testing | 2 pts |
| **TEST-FV-1** | Tree builder tests | Path parsing, semantic filter logic, count calculations; >80% coverage | 2 pts |
| **TEST-FV-2** | Component integration tests | Folder select, filter apply, grouping, subfolders section | 2 pts |
| **TEST-FV-3** | E2E tests | Full workflow (navigate, filter, subfolder nav, import) | 3 pts |

---

**Progress Tracking:** See `.claude/progress/marketplace-folder-view-v1/`

---

## 14. Key Technical Decisions

1. **Two-pane master-detail layout** (not expandable in-place tree) for clearer information hierarchy
2. **Semantic filtering rules** to exclude roots and leaf containers; show only meaningful categories
3. **First folder auto-select** to populate right pane immediately on load
4. **Existing card component** for artifacts (no new card design needed)
5. **localStorage for folder selection** to return users to last viewed folder
6. **Lazy tree rendering** (collapsed nodes not in DOM) for performance
7. **All filters apply to right pane** (type, confidence, search reduce artifact lists)
8. **Direct vs total counts**: Direct count always shown in badge (N); total count shown on hover [M] to avoid clutter
9. **Mixed-folder indicator**: Subtle dot or icon to identify folders with both direct artifacts and subfolders
10. **Subfolders section**: Placed at bottom of detail pane after artifact groups; scrollable independently if needed
11. **Subfolder navigation**: Click subfolder card → expand tree node and select folder (maintains tree state for back-navigation)

---

## 15. Edge Cases & Details

### Mixed-Content Folder Handling

**Case 1: Folder with ONLY direct artifacts (no subfolders)**
- Show artifact groups in detail pane
- No subfolders section
- "(N)" badge shown; no [M] badge

**Case 2: Folder with ONLY subfolders (no direct artifacts)**
- Show subfolders section with folder cards
- No artifact groups or empty message
- "(0)" badge or no direct count badge
- "Import All" button may be disabled or show warning (no direct artifacts)

**Case 3: Folder with BOTH direct artifacts AND subfolders (mixed)**
- Show artifact groups first
- Show subfolders section at bottom
- "(N) [M]" badges shown; mixed-folder indicator visible
- "Import All" button imports only direct artifacts, not descendants

**Case 4: Empty folder with subfolders**
- Show only subfolders section
- No artifact groups
- "(0)" or no direct count badge
- Clear affordance to explore subfolders

### Count Badge Visibility

- **(N)**: Always shown if directCount > 0
- **[M]**: Shown on hover or in ARIA label; hidden by default to reduce visual clutter
- **Fallback**: If no direct artifacts, don't show (N); show only [M] if applicable
- **ARIA**: Always include full context in aria-label: "Folder: productivity, 2 direct artifacts, 10 total descendants"

### Performance Considerations

- Tree builder calculates directCount (files at folder level) and totalCount (all descendants) once during build
- Badge rendering is cheap (simple text); no performance impact
- Mixed-folder detection (hasDirectArtifacts && hasSubfolders) computed at build time
- Subfolders section lazy-renders only when folder selected and has subfolders

---

Use this PRD as the blueprint for agent-driven implementation. Reference acceptance criteria and user stories for incremental development.
