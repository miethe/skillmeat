# Content Viewer Extraction Report

**Date**: 2026-02-13
**Goal**: Extract the Contents tab components into a reusable UI component library
**Status**: Feasibility analysis complete

---

## 1. What We're Extracting

The "Contents" tab in artifact modals is a self-contained file browser + content viewer. It consists of:

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| **ContentPane** | `components/content-pane.tsx` | 595 | Main viewer: markdown rendering, frontmatter display, code viewing, edit mode |
| **FileTree** | `components/file-tree.tsx` | 561 | Recursive file browser with full keyboard nav + ARIA tree pattern |
| **FrontmatterDisplay** | `components/frontmatter-display.tsx` | 159 | Collapsible YAML metadata viewer |
| **SplitPreview** | `components/split-preview.tsx` | 75 | Side-by-side markdown editor + live preview |
| **MarkdownEditor** | `components/markdown-editor.tsx` | 204 | CodeMirror 6 markdown editor with theme support |
| **frontmatter.ts** | `lib/frontmatter.ts` | 397 | Pure JS frontmatter parser (detect/parse/strip) |

**Total**: ~1,991 lines of core feature code

---

## 2. Dependency Analysis

### Internal Dependencies (must ship with library)

**shadcn/UI Primitives** (6 directly used):
- Button, ScrollArea, Skeleton, Alert, Collapsible, Tabs
- Plus `cn()` utility from `lib/utils.ts`

**Utility Functions**:
- `frontmatter.ts` - Zero dependencies, pure JS YAML parser
- `tree-builder.ts` - Builds hierarchical tree from flat file lists (moderate domain coupling via `CatalogEntry` type -- needs generification)

**Custom Hooks** (2):
- `useCatalogFileTree()` - TanStack Query wrapper for file tree fetching
- `useCatalogFileContent()` - TanStack Query wrapper for file content fetching

### External npm Dependencies

| Package | Purpose | Bundle Impact |
|---------|---------|---------------|
| `react-markdown` + `remark-gfm` | Markdown rendering | ~45 KB gzip |
| `@codemirror/*` (4 packages) | Code editor | ~180 KB gzip |
| `@tailwindcss/typography` | Prose styling for markdown | Tailwind plugin |
| `lucide-react` | Icons | Tree-shakeable |
| `@radix-ui/*` (6 packages) | Accessible primitives | ~30 KB gzip |
| `class-variance-authority` | Component variants | ~2 KB gzip |
| `tailwind-merge` + `clsx` | Class merging | ~3 KB gzip |

**Estimated bundle**: ~165 KB gzip without CodeMirror, ~345 KB with it.

### Domain Coupling Assessment

| File | Coupling | Issue | Fix |
|------|----------|-------|-----|
| `frontmatter.ts` | None | Pure generic | Ship as-is |
| `file-tree.tsx` | None | Generic tree component | Ship as-is |
| `content-pane.tsx` | Low | References `truncationInfo` shape | Define generic interface |
| `frontmatter-display.tsx` | None | Pure generic | Ship as-is |
| `markdown-editor.tsx` | None | Pure generic | Ship as-is |
| `split-preview.tsx` | None | Pure generic | Ship as-is |
| `tree-builder.ts` | Moderate | Depends on `CatalogEntry` type | Generify to `{ path: string }` |
| `useCatalogFileTree` | High | Hardcoded API path | Make data-fetching injectable |
| `useCatalogFileContent` | High | Hardcoded API path | Make data-fetching injectable |

**Verdict**: Components are 90%+ generic. Hooks need abstraction to decouple from SkillMeat's API.

---

## 3. Design System Requirements

### CSS Variables (must ship)

14 color variables in HSL format + 1 radius variable. Light/dark mode via `:root` / `.dark` class toggle.

```
--background, --foreground, --primary, --secondary, --muted, --accent,
--destructive, --card, --popover, --border, --input, --ring, --radius
(+ foreground variants for each)
```

### Tailwind Configuration

Custom animations (accordion, collapsible), typography plugin, border-radius calculations. The full `tailwind.config.ts` must either ship with the library or be documented as a peer requirement.

---

## 4. Proposed Package Architecture

### Option A: Monorepo UI Package (Recommended)

```
packages/
  ui/                           # @miethe/ui (or @skillmeat/ui)
    src/
      primitives/               # shadcn/ui primitives (Button, ScrollArea, etc.)
      content-viewer/
        content-pane.tsx        # Main viewer component
        file-tree.tsx           # File browser
        frontmatter-display.tsx # Metadata viewer
        split-preview.tsx       # Editor + preview
        markdown-editor.tsx     # CodeMirror wrapper
      lib/
        frontmatter.ts          # YAML parser
        utils.ts                # cn() helper
      styles/
        globals.css             # CSS variables + base styles
      types/
        index.ts                # Shared types (FileNode, FrontmatterData, etc.)
      index.ts                  # Public API exports
    tailwind.config.ts          # Preset for consumers
    package.json
    tsconfig.json
```

### Option B: shadcn-Style Registry

Instead of a published npm package, create a private shadcn registry that other projects can `npx shadcn add` from. This is lower overhead but less portable.

### Recommendation

**Option A** is better for your stated goal of design consistency across projects. It gives you:
- Versioned releases
- Peer dependency management
- Single source of truth for design tokens
- Easy to add more components over time

---

## 5. Component API Design (Standalone Usage)

### ContentViewer (composed)

```tsx
import { ContentViewer } from '@miethe/ui/content-viewer'

// Full-featured: file tree + content pane
<ContentViewer
  files={fileTree}           // FileNode[]
  onFileSelect={handleSelect}
  renderContent={({ path, content }) => <CustomRenderer ... />}
/>

// Or use pieces independently:
import { FileTree, ContentPane, FrontmatterDisplay } from '@miethe/ui/content-viewer'

// Standalone file tree
<FileTree
  nodes={nodes}
  selectedPath={path}
  onSelect={setPath}
  onCreateFile={handleCreate}    // optional
  onDeleteFile={handleDelete}    // optional
/>

// Standalone content pane
<ContentPane
  path="README.md"
  content={markdownString}
  readOnly={false}
  onSave={handleSave}
/>

// Standalone frontmatter display
<FrontmatterDisplay data={parsedFrontmatter} defaultOpen={true} />
```

### Data Fetching Strategy

Components should NOT include data fetching. Instead, provide:
1. **Headless hooks** that accept a generic fetcher
2. **Adapter packages** for common backends (e.g., `@miethe/ui-github` for GitHub tree API)

```tsx
// Consumer provides their own data fetching
const { tree } = useFileTree({
  fetcher: () => fetch('/api/files').then(r => r.json()),
  queryKey: ['my-files'],
})

// Or use a pre-built adapter
import { useGitHubFileTree } from '@miethe/ui-github'
const { tree } = useGitHubFileTree({ owner: 'foo', repo: 'bar' })
```

---

## 6. Feasibility Assessment

### Strengths

- **Clean separation**: Components are already well-isolated with clear props interfaces
- **Zero domain logic in rendering**: All SkillMeat-specific logic lives in hooks/utils, not in JSX
- **Accessibility built-in**: Full ARIA tree pattern, keyboard navigation, roving tabindex
- **Theme-agnostic**: CSS variables mean any theme can be applied
- **Small surface area**: 6 components + 1 utility = manageable initial scope

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Tailwind config divergence across projects | Medium | Ship a Tailwind preset that consumers extend |
| CodeMirror bundle size | Medium | Make editor optional / lazy-loaded |
| Breaking changes propagating | Low | Semantic versioning + changelog |
| Maintaining two codebases | Medium | Monorepo with shared tooling |

### Effort Estimate

| Phase | Work | Estimate |
|-------|------|----------|
| 1. Package scaffolding | Monorepo setup, build config, TypeScript | 2-3 hours |
| 2. Extract + generify components | Remove domain coupling, define generic types | 4-6 hours |
| 3. Extract design system | CSS variables, Tailwind preset, primitives | 2-3 hours |
| 4. Build headless hooks | Generic fetcher pattern, TanStack Query wrappers | 2-3 hours |
| 5. Documentation + examples | Storybook or usage docs | 2-3 hours |
| 6. Integration test | Wire back into SkillMeat using the package | 2-3 hours |
| **Total** | | **14-21 hours** |

---

## 7. Recommended Approach

### Phase 1: Monorepo Setup
Convert the repo to a monorepo (or add a `packages/` directory). Set up a `@miethe/ui` package with TypeScript, Tailwind, and a build tool (tsup or unbundled for tree-shaking).

### Phase 2: Extract Content Viewer
Move the 6 component files + frontmatter utility. Generify the 2 hooks into headless patterns. Define clean public types.

### Phase 3: Extract Design System Foundation
Move CSS variables, the Tailwind preset, and the shadcn primitives used by content-viewer. This becomes the shared design foundation for all future components.

### Phase 4: Refactor SkillMeat to Consume
Replace SkillMeat's local copies with imports from the package. Verify nothing breaks.

### Phase 5: Expand
Add more components to the library as needed (the rest of the shadcn primitives, other reusable patterns from SkillMeat).

---

## 8. Files Generated by This Analysis

Detailed supporting documents in `.claude/analysis/`:
- `content-viewing-extraction-inventory.md` - Full file-by-file inventory with all exports, dependencies, coupling assessment
- `content-viewer-quick-ref.md` - Quick reference and checklists
- `CONTENT-VIEWER-README.md` - Executive summary

Design system analysis in `.claude/progress/design-system-analysis/`:
- `ui-primitives-and-design-system.md` - Deep technical reference on all UI primitives
- `design-system-architecture-diagram.md` - Visual architecture diagrams
- `quick-reference.md` - CSS variables, imports, accessibility lookup tables
