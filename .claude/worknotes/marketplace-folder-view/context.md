---
type: context
prd: marketplace-folder-view
title: Marketplace Folder View Implementation Context
status: not_started
created: 2026-01-28
updated: 2026-01-29
phase_status:
- phase: 1
  status: not_started
  title: Two-Pane Layout & Semantic Tree
  reason: null
- phase: 2
  status: not_started
  title: Folder Detail Pane & Bulk Import
  reason: Waiting for Phase 1 completion
- phase: 3
  status: not_started
  title: Accessibility & Performance Optimization
  reason: Waiting for Phase 2 completion
blockers: []
decisions:
- id: DECISION-1
  question: What layout architecture for folder view?
  decision: Two-pane master-detail layout (25% left, 75% right)
  rationale: Aligns with Gemini design spec; provides clear navigation in left pane
    and rich detail in right pane
  tradeoffs: More complex layout; responsive handling needed for smaller screens
  location: skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx
- id: DECISION-2
  question: How to filter folders in navigation tree?
  decision: Semantic filtering - exclude root folders and leaf artifact containers
  rationale: Root folders (plugins/, src/, skills/) and leaf containers (commands/,
    agents/, mcp_servers/) add noise; intermediate folders are most useful for navigation
  tradeoffs: May hide some folders users expect; semantic rules need tuning
  location: skillmeat/web/lib/tree-filter-utils.ts
- id: DECISION-3
  question: Where should tree building logic live?
  decision: Client-side only, no API changes
  rationale: Uses existing CatalogEntry.path field; avoids backend complexity
  tradeoffs: Larger catalogs may need virtualization in future
  location: skillmeat/web/lib/tree-builder.ts
- id: DECISION-4
  question: Which UI primitive for collapsible folders?
  decision: Radix Collapsible via shadcn/ui
  rationale: Consistent with existing design system; built-in accessibility
  tradeoffs: None significant
  location: skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx
- id: DECISION-5
  question: How to display folder content in right pane?
  decision: Group artifacts by type with section headers + bulk import
  rationale: Type grouping provides clear organization; bulk import enables fast collection
    building
  tradeoffs: More complex UI than simple list; type sections need styling
  location: skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx
- id: DECISION-6
  question: How to handle performance for large trees?
  decision: Lazy rendering (Phase 3) + memoization
  rationale: Collapsed folders don't render children until expanded
  tradeoffs: Initial expand may have slight delay; mitigated by memoization
  location: skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx
- id: DECISION-7
  question: Keyboard navigation pattern?
  decision: Roving tabindex with arrow key navigation + Tab between panes
  rationale: Standard tree widget pattern; matches ARIA authoring practices
  tradeoffs: Implementation complexity; handled by Phase 3
  location: skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx
- id: DECISION-8
  question: How to handle mixed-content folders (folders with both direct artifacts
    AND subfolders)?
  decision: Direct artifacts shown in type sections above Subfolders section; tree
    node badges show (N) for direct count, [M] for total descendants on hover; visual
    indicator (dot/icon) for mixed-content folders
  rationale: Clear separation between direct content and navigation to children; count
    badges provide at-a-glance information without requiring expansion; hover-for-total
    reduces visual clutter while keeping info accessible
  tradeoffs: More complex tree node rendering; two count numbers may confuse users
    initially
  location: skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx
integrations: []
gotchas: []
modified_files: []
schema_version: 2
doc_type: context
feature_slug: marketplace-folder-view
---

# Marketplace Folder View Implementation Context

**Status**: Not Started
**Last Updated**: 2026-01-29
**Purpose**: Token-efficient context for agents implementing folder view feature

## PRD Reference

**Implementation Plan**: `docs/project_plans/implementation_plans/features/marketplace-folder-view-v1.md`
**PRD**: `docs/project_plans/PRDs/features/marketplace-folder-view-v1.md`
**Design Spec**: Aligns with Gemini design spec for two-pane layout

## Feature Summary

Two-pane master-detail Folder View for marketplace source detail pages with semantic navigation tree and rich folder detail pane. The left pane (25%) shows a smart semantic navigation tree (excluding root and leaf artifact containers), while the right pane (75%) displays folder metadata, description, and all artifacts in that folder with type-based grouping.

**Key Outcomes**:
- Users discover related artifacts 2-3x faster with two-pane layout
- Semantic filtering eliminates root/leaf containers for cleaner navigation
- Folder detail pane shows rich metadata and "Import All" bulk action
- Artifacts grouped by type within each folder for clarity
- Subfolder navigation in detail pane for drilling into nested folders
- Full WCAG 2.1 AA accessibility compliance with keyboard navigation
- Tree renders 1000+ artifacts within 200ms budget via lazy rendering

## Effort Summary

| Phase | Title | Effort |
|-------|-------|--------|
| Phase 1 | Two-Pane Layout & Semantic Tree | 24 pts |
| Phase 2 | Folder Detail Pane & Bulk Import | 28 pts |
| Phase 3 | Accessibility & Performance Optimization | 17 pts |
| **Total** | | **69 pts** |

## Architecture Overview

### Two-Pane Layout Architecture

```
 SourceFolderLayout (two-pane container)
├── Left Pane (25%)
│   └── SemanticTree
│       └── TreeNode (recursive, collapsible)
│           └── TreeNode (nested folders)
└── Right Pane (75%)
    └── FolderDetailPane
        ├── FolderDetailHeader (title, chip, description, "Import All")
        ├── ArtifactTypeSection (repeated per type)
        │   └── Artifact rows
        └── SubfoldersSection (when hasSubfolders)
            └── SubfolderCard (repeated per subfolder)
```

### Component Architecture

```
Source Detail Page
├── SourceToolbar (folder toggle button)
└── SourceFolderLayout (container)
    ├── SemanticTree (left pane)
    │   └── TreeNode (recursive, filtered by semantic rules)
    │       ├── Folder icon + name
    │       ├── Direct count badge "(N)"
    │       ├── Total count on hover "[M]"
    │       └── Mixed-content indicator (dot/icon)
    └── FolderDetailPane (right pane)
        ├── FolderDetailHeader
        ├── ArtifactTypeSection (grouped by type)
        └── SubfoldersSection
            └── SubfolderCard

Utilities:
├── buildFolderTree() → converts flat paths to tree with directArtifacts/children separation
├── isSemanticFolder() → filters roots/leafs
├── filterSemanticFolders() → applies semantic filtering
├── extractFolderReadme() → extracts README content
└── useFolderSelection() → manages selection + expanded state
```

### Data Flow

```
CatalogEntry[] (flat)
    ↓ buildFolderTree(entries, maxDepth)
FolderTree (nested with directArtifacts, children, counts)
    ↓ filterSemanticFolders(tree)
SemanticTree (filtered - no roots/leafs)
    ↓ useFolderSelection(tree, entries)
{ selectedFolder, setSelectedFolder, expanded, setExpanded }
    ↓ SourceFolderLayout renders
SemanticTree (left) + FolderDetailPane (right)
    ↓ FolderDetailPane renders
ArtifactTypeSections + SubfoldersSection (if hasSubfolders)
```

### FolderTree Node Structure

```typescript
interface FolderTreeNode {
  path: string;
  name: string;
  directArtifacts: CatalogEntry[];  // Artifacts directly in this folder
  children: FolderTreeNode[];        // Subfolders
  directCount: number;               // Count of directArtifacts
  totalArtifactCount: number;        // All descendants (direct + nested)
  hasSubfolders: boolean;            // children.length > 0
  hasDirectArtifacts: boolean;       // directArtifacts.length > 0
}
```

## File Locations

### New Files (Phase 1)

| File | Purpose |
|------|---------|
| `skillmeat/web/lib/tree-builder.ts` | Tree builder utilities with mixed-content support |
| `skillmeat/web/lib/tree-filter-utils.ts` | Semantic filtering utilities |
| `skillmeat/web/lib/hooks/use-folder-selection.ts` | Folder selection state hook |
| `skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx` | Two-pane container |
| `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx` | Left pane semantic tree |
| `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx` | Individual folder item with count badges |

### New Files (Phase 2)

| File | Purpose |
|------|---------|
| `skillmeat/web/lib/folder-readme-utils.ts` | README extraction utilities |
| `skillmeat/web/lib/artifact-grouping-utils.ts` | Type grouping logic |
| `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx` | Right pane container |
| `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx` | Title, chip, description, import all |
| `skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx` | Type grouping component |
| `skillmeat/web/app/marketplace/sources/[id]/components/subfolders-section.tsx` | Subfolders grid section |
| `skillmeat/web/app/marketplace/sources/[id]/components/subfolder-card.tsx` | Clickable subfolder card |

### Modified Files

| File | Changes |
|------|---------|
| `skillmeat/web/app/marketplace/sources/[id]/page.tsx` | Add folder view conditional rendering |
| `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx` | Add folder button |

### Test Files

| File | Purpose |
|------|---------|
| `skillmeat/web/__tests__/lib/tree-builder.test.ts` | Tree builder unit tests (including mixed-content) |
| `skillmeat/web/__tests__/lib/tree-filter-utils.test.ts` | Semantic filtering unit tests |
| `skillmeat/web/tests/marketplace/folder-view.spec.ts` | E2E tests |

## Quick Reference Commands

### Phase Execution

```bash
# Execute Phase 1
/dev:execute-phase 1 --prd marketplace-folder-view

# Update task status (CLI-first)
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/marketplace-folder-view/phase-1-progress.md \
  -t MFV-1.1 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/marketplace-folder-view/phase-1-progress.md \
  --updates "MFV-1.1:completed,MFV-1.2:completed"
```

### Development

```bash
# Start dev server
cd skillmeat/web && pnpm dev

# Run tests
cd skillmeat/web && pnpm test

# Run E2E tests
cd skillmeat/web && pnpm test:e2e

# Type check
cd skillmeat/web && pnpm typecheck
```

## Dependencies

**External Systems**: None (frontend-only feature)

**Internal Dependencies**:
- `CatalogEntry` type from existing catalog hooks
- `useSourceCatalog` hook for catalog data
- Existing filter state management
- shadcn/ui components (Collapsible, Button, Badge)

## Performance Targets

| Metric | Target | Measured |
|--------|--------|----------|
| Tree render (500 items) | <300ms | Pending |
| Tree render (1000 items) | <200ms | Pending |
| Filter change | <100ms | Pending |
| DOM node reduction | 60-80% | Pending |

## Accessibility Requirements

| Requirement | Standard | Status |
|-------------|----------|--------|
| Keyboard navigation | WCAG 2.1 AA | Pending |
| Screen reader support | NVDA/JAWS/VoiceOver | Pending |
| Color contrast | >4.5:1 | Pending |
| Focus indicators | 2px visible ring | Pending |
| Pane focus management | Tab between panes | Pending |

## Semantic Filtering Rules

### Excluded Root Folders
- `plugins/`
- `src/`
- `skills/`
- `lib/`
- `packages/`
- `apps/`

### Excluded Leaf Containers
- `commands/`
- `agents/`
- `mcp_servers/`
- `hooks/`

### Included (Semantic Folders)
- Intermediate folders between roots and leafs
- Folders containing mixed content
- Named feature folders (e.g., `analytics/`, `auth/`)

## Edge Cases to Handle

| Edge Case | Handling |
|-----------|----------|
| Malformed paths | Log warning, skip invalid entries |
| Empty catalog | Show empty state |
| Deep nesting (5+ levels) | Breadcrumb or truncation |
| Filtered empty folders | Show "(No importable artifacts)" in right pane |
| Single artifact | Render without unnecessary nesting |
| No README | Fall back to AI-generated summary or generic text |
| Root-only catalog | Show empty semantic tree |
| First folder missing | Auto-select first available semantic folder |
| **Folder with ONLY direct artifacts** | Show type sections, no Subfolders section |
| **Folder with ONLY subfolders** | Show Subfolders section only, no "Import All" if no direct artifacts |
| **Empty folder with subfolders** | Show Subfolders section, "(0)" direct count in tree |
| **Mixed folder (direct + subfolders)** | Type sections ABOVE Subfolders section |

## Next Steps for Agents

1. **Phase 1 Start**: Begin with batch_1 tasks (MFV-1.1, MFV-1.2, MFV-1.4, MFV-1.6, MFV-1.7) in parallel
2. **Read existing code**: Check `skillmeat/web/app/marketplace/sources/[id]/` for patterns
3. **Follow component conventions**: See `skillmeat/web/CLAUDE.md` for React patterns
4. **Use shadcn/ui**: Install components with `pnpm dlx shadcn@latest add`

## Related Context

- **Component patterns**: `skillmeat/web/CLAUDE.md`
- **Existing catalog components**: `skillmeat/web/app/marketplace/sources/[id]/components/`
- **Design system**: shadcn/ui + Radix + Tailwind
- **Implementation plan**: `docs/project_plans/implementation_plans/features/marketplace-folder-view-v1.md`
