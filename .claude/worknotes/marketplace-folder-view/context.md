---
type: context
prd: "marketplace-folder-view"
title: "Marketplace Folder View Implementation Context"
status: not_started
created: 2026-01-28
updated: 2026-01-28

phase_status:
  - phase: 1
    status: not_started
    title: "Core Folder View Component & Tree Building"
    reason: null
  - phase: 2
    status: not_started
    title: "Depth Configuration & Polish"
    reason: "Waiting for Phase 1 completion"
  - phase: 3
    status: not_started
    title: "Accessibility & Performance Optimization"
    reason: "Waiting for Phase 2 completion"

blockers: []

decisions:
  - id: "DECISION-1"
    question: "Where should tree building logic live?"
    decision: "Client-side only, no API changes"
    rationale: "Uses existing CatalogEntry.path field; avoids backend complexity"
    tradeoffs: "Larger catalogs may need virtualization in future"
    location: "skillmeat/web/lib/folder-tree.ts"

  - id: "DECISION-2"
    question: "Which UI primitive for collapsible folders?"
    decision: "Radix Collapsible via shadcn/ui"
    rationale: "Consistent with existing design system; built-in accessibility"
    tradeoffs: "None significant"
    location: "skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx"

  - id: "DECISION-3"
    question: "How to handle performance for large trees?"
    decision: "Lazy rendering (Phase 3) + memoization"
    rationale: "Collapsed folders don't render children until expanded"
    tradeoffs: "Initial expand may have slight delay; mitigated by memoization"
    location: "skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx"

  - id: "DECISION-4"
    question: "Keyboard navigation pattern?"
    decision: "Roving tabindex with arrow key navigation"
    rationale: "Standard tree widget pattern; matches ARIA authoring practices"
    tradeoffs: "Implementation complexity; handled by Phase 3"
    location: "skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx"

integrations: []

gotchas: []

modified_files: []
---

# Marketplace Folder View Implementation Context

**Status**: Not Started
**Last Updated**: 2026-01-28
**Purpose**: Token-efficient context for agents implementing folder view feature

## PRD Reference

**Implementation Plan**: `docs/project_plans/implementation_plans/features/marketplace-folder-view-v1.md`
**PRD**: `docs/project_plans/PRDs/features/marketplace-folder-view-v1.md`

## Feature Summary

Tree-based folder view for marketplace source detail pages, enabling users to navigate 100+ artifact repositories by directory structure instead of flat lists.

**Key Outcomes**:
- Users discover related artifacts 2-3x faster in large repositories
- Folder view integrates alongside existing grid/list modes
- Full WCAG 2.1 AA accessibility compliance
- Tree renders 1000+ artifacts within 200ms

## Architecture Overview

### Component Architecture

```
CatalogFolder (container)
├── DirectoryNode (collapsible folder)
│   ├── DirectoryNode (nested)
│   └── ArtifactRowFolder (leaf)
└── FolderDepthControls (toolbar dropdown)

Utilities:
├── buildFolderTree() → converts flat paths to tree
├── calculateAutoDepth() → auto-detects optimal depth
└── useFolderTree() → manages tree state
```

### Data Flow

```
CatalogEntry[] (flat)
    ↓ buildFolderTree(entries, maxDepth)
FolderTree (nested)
    ↓ useFolderTree(tree, filters)
{ tree, expanded, setExpanded, depth, setDepth }
    ↓ CatalogFolder renders
DirectoryNode + ArtifactRowFolder components
```

## File Locations

### New Files (Phase 1-2)

| File | Purpose |
|------|---------|
| `skillmeat/web/lib/folder-tree.ts` | Tree builder utilities |
| `skillmeat/web/lib/hooks/use-folder-tree.ts` | Tree state management hook |
| `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx` | Main tree container |
| `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx` | Collapsible folder component |
| `skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx` | Artifact row in tree |
| `skillmeat/web/app/marketplace/sources/[id]/components/folder-depth-controls.tsx` | Depth dropdown |

### Modified Files

| File | Changes |
|------|---------|
| `skillmeat/web/app/marketplace/sources/[id]/page.tsx` | Add folder view conditional rendering |
| `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx` | Add folder button + depth controls |

### Test Files

| File | Purpose |
|------|---------|
| `skillmeat/web/__tests__/lib/folder-tree.test.ts` | Tree builder unit tests |
| `skillmeat/web/tests/marketplace/folder-view.spec.ts` | E2E tests |
| `skillmeat/web/tests/marketplace/folder-view-performance.spec.ts` | Performance E2E tests |

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
- shadcn/ui components (Collapsible, Button, DropdownMenu)

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

## Edge Cases to Handle

| Edge Case | Handling |
|-----------|----------|
| Malformed paths | Log warning, skip invalid entries |
| Empty catalog | Show empty state |
| Deep nesting (5+ levels) | Breadcrumb or truncation |
| Filtered empty folders | Show "(No importable artifacts)" |
| Single artifact | Render without unnecessary nesting |

## Next Steps for Agents

1. **Phase 1 Start**: Begin with MFV-1.1 and MFV-1.2 (tree utilities) in parallel
2. **Read existing code**: Check `skillmeat/web/app/marketplace/sources/[id]/` for patterns
3. **Follow component conventions**: See `skillmeat/web/CLAUDE.md` for React patterns
4. **Use shadcn/ui**: Install components with `pnpm dlx shadcn@latest add`

## Related Context

- **Component patterns**: `skillmeat/web/CLAUDE.md`
- **Existing catalog components**: `skillmeat/web/app/marketplace/sources/[id]/components/`
- **Design system**: shadcn/ui + Radix + Tailwind
