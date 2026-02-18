# Content Viewer Package: Quick Reference

**Package Candidate**: `@skillmeat/content-viewer`
**Status**: Ready for extraction (Tier 1 components identified)
**Created**: 2026-02-13

---

## What to Extract

### Components (100% Generic)

| Component | File | Props | Dependencies | Status |
|-----------|------|-------|--------------|--------|
| **FileTree** | `entity/file-tree.tsx` | `FileNode[]`, `selectedPath`, `onSelect` | lucide, button, skeleton | ✅ Ready |
| **FrontmatterDisplay** | `entity/frontmatter-display.tsx` | `Record<string, unknown>` | lucide, button, collapsible | ✅ Ready |

### Utilities (100% Generic)

| Utility | File | Purpose | Dependencies | Status |
|---------|------|---------|--------------|--------|
| **parseFrontmatter()** | `lib/frontmatter.ts` | YAML parsing | None | ✅ Ready |
| **stripFrontmatter()** | `lib/frontmatter.ts` | Remove frontmatter | None | ✅ Ready |
| **detectFrontmatter()** | `lib/frontmatter.ts` | Check for frontmatter | None | ✅ Ready |
| **extractFirstParagraph()** | `lib/folder-readme-utils.ts` | Extract summary text | None | ✅ Ready |
| **extractFolderReadme()** | `lib/folder-readme-utils.ts` | Find README in entries | None | ✅ Ready |

### Hooks (100% Generic)

| Hook | File | Returns | Parameters | Status |
|------|------|---------|------------|--------|
| **useCatalogFileTree()** | `hooks/use-catalog-files.ts` | Query<FileTreeResponse> | sourceId, artifactPath | ✅ Ready |
| **useCatalogFileContent()** | `hooks/use-catalog-files.ts` | Query<FileContentResponse> | sourceId, artifactPath, filePath | ✅ Ready |

### Types

| Type | File | Generic? | Status |
|------|------|----------|--------|
| **FileNode** | `types/files.ts` | ✅ Yes | ✅ Ready |
| **FileTreeResponse** | `lib/api/catalog.ts` | ✅ Yes | ✅ Ready |
| **FileContentResponse** | `lib/api/catalog.ts` | ✅ Yes | ✅ Ready |

### API Clients

| Function | File | Generic? | Status |
|----------|------|----------|--------|
| **fetchCatalogFileTree()** | `lib/api/catalog.ts` | ✅ Yes | ✅ Ready |
| **fetchCatalogFileContent()** | `lib/api/catalog.ts` | ✅ Yes | ✅ Ready |

---

## What to Keep in SkillMeat

### Domain-Specific Utilities

| Utility | File | Reason | Status |
|---------|------|--------|--------|
| **filterSemanticTree()** | `lib/tree-filter-utils.ts` | Uses detection patterns | 🔴 Keep |
| **applyFiltersToEntries()** | `lib/folder-filter-utils.ts` | Uses CatalogEntry, enums | 🔴 Keep |
| **buildFolderTree()** | `lib/tree-builder.ts` | Could extract but uses CatalogEntry | 🟡 Keep |

### Types

| Type | File | Reason | Status |
|------|------|--------|--------|
| **CatalogEntry** | `types/marketplace.ts` | Marketplace-specific | 🔴 Keep |
| **CatalogFilters** | `types/marketplace.ts` | Marketplace-specific | 🔴 Keep |
| **ArtifactType** | `types/marketplace.ts` | Enum (skill/command/agent/mcp/hook) | 🔴 Keep |

### Hooks

| Hook | File | Reason | Status |
|------|------|--------|--------|
| **useDetectionPatterns()** | `hooks/use-detection-patterns.ts` | Returns SkillMeat patterns | 🔴 Keep |

---

## Package Structure

```
@skillmeat/content-viewer/
├── src/
│   ├── components/
│   │   ├── FileTree.tsx              # File browser component
│   │   └── FrontmatterDisplay.tsx    # YAML metadata display
│   ├── hooks/
│   │   └── useFileContent.ts         # TanStack Query hooks
│   ├── lib/
│   │   ├── frontmatter.ts            # YAML parsing
│   │   ├── readme-utils.ts           # Markdown extraction
│   │   └── api.ts                    # HTTP client functions
│   ├── types/
│   │   └── index.ts                  # FileNode, responses
│   └── index.ts                      # Main exports
├── package.json
├── tsconfig.json
├── README.md
└── CHANGELOG.md
```

---

## Dependencies

### Runtime
```json
{
  "react": "^18.0",
  "@tanstack/react-query": "^5.0",
  "@radix-ui/react-collapsible": "^1.0",
  "lucide-react": "^0.400",
  "tailwindcss": "^3.0",
  "tailwind-merge": "^2.0"
}
```

### Peer
```json
{
  "react": "^18.0",
  "react-dom": "^18.0"
}
```

---

## Import Examples

### After Extraction

```tsx
import {
  FileTree,
  FrontmatterDisplay,
  parseFrontmatter,
  extractFirstParagraph,
  useCatalogFileTree,
  useCatalogFileContent,
} from '@skillmeat/content-viewer';

import type { FileNode, FileTreeResponse } from '@skillmeat/content-viewer';
```

### In SkillMeat App

```tsx
// Still import marketplace-specific utilities from local
import { filterSemanticTree, buildFolderTree } from '@/lib/tree-filter-utils';
import { applyFiltersToEntries } from '@/lib/folder-filter-utils';

// Import extracted components from package
import { FileTree, FrontmatterDisplay } from '@skillmeat/content-viewer';
```

---

## Migration Checklist

- [ ] Create package.json and tsconfig.json
- [ ] Extract FileTree component
- [ ] Extract FrontmatterDisplay component
- [ ] Extract frontmatter utilities
- [ ] Extract readme utilities
- [ ] Extract API client functions
- [ ] Export FileNode and response types
- [ ] Add comprehensive README with examples
- [ ] Set up tests for all utilities
- [ ] Create CHANGELOG
- [ ] Publish to npm
- [ ] Update SkillMeat imports to use package
- [ ] Remove extracted files from SkillMeat repo

---

## Feature Checklist

### FileTree Component
- [x] Expandable/collapsible folders
- [x] File type icons
- [x] Selected state
- [x] Keyboard navigation (↑↓←→ Home End Enter Space)
- [x] ARIA accessibility (tree role, levels, positions)
- [x] Roving tabindex for focus
- [x] Optional delete actions
- [x] Optional create actions
- [x] Loading skeleton
- [x] Read-only mode
- [x] Empty state
- [x] Recursive rendering

### FrontmatterDisplay Component
- [x] Collapsible section
- [x] Type-aware rendering
- [x] Arrays (comma-separated)
- [x] Nested objects (1 level)
- [x] Scrollable content
- [x] Smooth animations
- [x] Accessible expand/collapse

### Frontmatter Utilities
- [x] Detect frontmatter presence
- [x] Parse YAML structure
- [x] Strip frontmatter from content
- [x] Handle quoted strings
- [x] Handle booleans
- [x] Handle numbers
- [x] Handle null/undefined
- [x] Handle arrays
- [x] Handle nested objects
- [x] Handle inline arrays
- [x] Handle inline objects

### README Utilities
- [x] Extract first paragraph
- [x] Skip headings and special markdown
- [x] Handle code blocks
- [x] Truncate long paragraphs
- [x] Find README files in catalog

### File Content Hooks
- [x] File tree fetching
- [x] File content fetching
- [x] Proper cache stale times
- [x] Query enablement gating
- [x] Error handling
- [x] Query key factories

---

## Potential Enhancements

These could be added post-launch:

- [ ] Syntax highlighting for code files (via react-syntax-highlighter)
- [ ] Markdown rendering (via react-markdown)
- [ ] Search/filter within file tree
- [ ] File preview pane
- [ ] Breadcrumb navigation
- [ ] File size display
- [ ] Last modified dates
- [ ] Git blame integration
- [ ] Copy file path to clipboard
- [ ] Collapsible tree with expand-all/collapse-all buttons

---

## Testing Coverage Needed

### Utilities
```
frontmatter.ts
  - detectFrontmatter() with/without FM
  - parseFrontmatter() with various data types
  - stripFrontmatter() content removal
  - Edge cases: malformed YAML, quoted strings

readme-utils.ts
  - extractFirstParagraph() with headers, code, lists
  - extractFolderReadme() with multiple files
  - Truncation at 300 chars
  - Minimum 20 char requirement
```

### Components
```
FileTree
  - Render hierarchical structure
  - Keyboard navigation (all keys)
  - Focus management
  - ARIA attributes present
  - Icon mapping for extensions
  - Selection and callbacks
  - Delete button visibility
  - Read-only mode
  - Loading skeleton
  - Empty state

FrontmatterDisplay
  - Type-aware rendering
  - Arrays as comma-separated
  - Objects as indented pairs
  - Collapse/expand toggle
  - Scrollable content
  - CSS classes applied
```

### Hooks
```
useCatalogFileTree
  - Query enabled/disabled correctly
  - Stale times applied (5min)
  - GC time set (30min)
  - Error handling

useCatalogFileContent
  - Query enabled/disabled correctly
  - Stale times applied (30min)
  - GC time set (2hr)
  - Truncation detection
```

---

## Performance Notes

### FileTree
- Flattens tree once for keyboard navigation
- Updates expanded state efficiently with Set
- Roving tabindex avoids rendering all nodes in DOM

### Frontmatter Parser
- Single-pass line iteration
- Stack-based for nested objects
- Handles deep nesting without recursion issues

### Tree Builder
- Benchmarked: 1000 entries ~2ms
- O(n*d) complexity acceptable for typical repos
- Metadata updates bottom-up

---

## Backward Compatibility

SkillMeat will continue to work with extracted package:

```tsx
// Old way (still works)
import { FileTree } from '@/components/entity/file-tree';

// New way (after extraction)
import { FileTree } from '@skillmeat/content-viewer';
```

Gradual migration possible - both can coexist during transition.

---

## Versioning Strategy

```
@skillmeat/content-viewer@1.0.0
  ├── Major: Breaking changes to component APIs
  ├── Minor: New features, new utilities
  └── Patch: Bug fixes, docs updates
```

Start at 1.0.0 since extracted from stable codebase.

---

## Documentation TODOs

- [ ] Component prop documentation with examples
- [ ] Utility function examples
- [ ] Hook usage patterns
- [ ] Type definitions guide
- [ ] Accessibility guide (keyboard nav, ARIA)
- [ ] Styling customization (Tailwind, CSS variables)
- [ ] Performance optimization tips
- [ ] Migration guide from SkillMeat
- [ ] Changelog entries for v1.0.0
