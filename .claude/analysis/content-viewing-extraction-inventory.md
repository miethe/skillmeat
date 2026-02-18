# Content Viewing & File Browsing Components: Extraction Inventory

**Purpose**: Document all custom hooks, utilities, and types required to extract content viewing/file browsing components into a standalone package.

**Scope**: SkillMeat web UI - `skillmeat/web/` artifacts that support file trees, markdown content viewing, and frontmatter parsing.

**Last Updated**: 2026-02-13
**Task**: Identify what would be needed to extract UI components + supporting logic into `@skillmeat/content-viewer` or similar package.

---

## Executive Summary

The content viewing infrastructure in SkillMeat consists of:

1. **Core Utilities** (Generic, reusable) - 5 files
   - Frontmatter parsing with YAML support
   - Folder tree building and filtering
   - README extraction from markdown
   - Filter application for catalog entries

2. **Custom Hooks** (TanStack Query + SSR-aware) - 2 hooks
   - Catalog file tree fetching
   - File content fetching with caching

3. **React Components** (Radix UI + shadcn based) - 3 components
   - FileTree with keyboard navigation and accessibility
   - FrontmatterDisplay with collapsible sections
   - (Marketplace integration components not included here)

4. **Type Definitions** (Domain-specific) - 1 primary type set
   - CatalogEntry (marketplace-specific)
   - File node types (generic)
   - Filter types (domain-specific)

5. **API Clients** (Backend communication) - 1 service
   - Catalog file fetch functions (marketplace API)

---

## Category 1: Core Utility Functions

### 1. `/lib/frontmatter.ts`

**Exports**:
- `detectFrontmatter(content: string): boolean`
- `parseFrontmatter(content: string): { frontmatter, content }`
- `stripFrontmatter(content: string): string`
- Internal: `parseYaml()`, `parseValue()`, `parseInlineArray()`, `parseInlineObject()`

**External Dependencies**:
- None (pure JavaScript)

**Internal Dependencies**:
- None

**Domain Coupling**: Generic - No SkillMeat-specific logic
- Simple YAML parser for common frontmatter patterns
- Handles quoted strings, booleans, numbers, null values, arrays, nested objects
- Note: Comment suggests use of `yaml` or `js-yaml` package for production

**Use Cases**:
- Parsing YAML frontmatter from markdown files
- Extracting metadata from artifact documentation
- Content viewing in any markdown-based system

**Extraction Readiness**: ✅ High - Completely generic, zero dependencies

---

### 2. `/lib/tree-builder.ts`

**Exports**:
```ts
interface FolderNode {
  name, fullPath, directArtifacts, totalArtifactCount, directCount,
  children, hasSubfolders, hasDirectArtifacts
}
type FolderTree = Record<string, FolderNode>
buildFolderTree(entries: CatalogEntry[], maxDepth: number): FolderTree
getNodeAtPath() [internal]
updateTreeMetadata() [internal]
```

**External Dependencies**:
- `@/types/marketplace` → `CatalogEntry` type

**Internal Dependencies**:
- None (tree logic is pure)

**Domain Coupling**: Moderate - Depends on `CatalogEntry` interface
- Generic tree-building algorithm (O(n*d) complexity, benchmarked)
- Heavily documented with performance metrics
- Could be adapted to work with any entry type with `path` field

**Use Cases**:
- Building hierarchical folder structures from flat artifact lists
- Navigation tree construction for marketplace browsing
- Folder-based organization of any artifacts

**Extraction Readiness**: 🟡 Medium - Generic algorithm but tied to CatalogEntry type
- Could be made generic with `<T extends { path: string }>` parameter
- No actual SkillMeat business logic

**Performance Notes**:
- 500 entries: ~1ms, 1000 entries: ~2ms, 2000 entries: ~7ms
- Memory: ~30% as many folder nodes as input entries

---

### 3. `/lib/tree-filter-utils.ts`

**Exports**:
```ts
interface SemanticFilterConfig {
  leafContainers?: string[]
  rootExclusions?: string[]
}
isSemanticFolder(path, depth, config?): boolean
filterSemanticTree(tree, depth?, config?): FolderTree
countSemanticFolders(tree): number
getSemanticFolderPaths(tree, prefix?): string[]
[+ internal: isRootExclusion(), isLeafContainer()]
```

**External Dependencies**:
- `@/lib/tree-builder` → `FolderTree`, `FolderNode` types
- `@/types/marketplace` → `CatalogEntry` type
- `@/hooks/use-detection-patterns` → `DEFAULT_LEAF_CONTAINERS`, `DEFAULT_ROOT_EXCLUSIONS`

**Internal Dependencies**:
- Depends on `tree-builder.ts` types

**Domain Coupling**: High - Designed specifically for SkillMeat's folder structure
- Filters folders based on artifact container names (skills, commands, etc.)
- Promotes content from leaf containers to parent
- Excludes root-level navigation folders (src, lib, etc.)
- Tightly coupled to detection pattern configuration

**Use Cases**:
- Semantic navigation tree filtering for marketplace
- Hiding implementation folders from user view
- Promoting artifact leaf containers to parent level

**Extraction Readiness**: 🔴 Low - Highly domain-specific
- Logic is generic (tree filtering) but configuration is SkillMeat-specific
- Would need extracted constants to be configurable
- Useful for SkillMeat package but not for generic content viewing

**Configuration Dependency**:
```ts
// Uses centralized patterns:
- DEFAULT_LEAF_CONTAINERS (from hook)
- DEFAULT_ROOT_EXCLUSIONS (from hook)
// Could be extracted to enum/const but currently pattern-driven
```

---

### 4. `/lib/folder-readme-utils.ts`

**Exports**:
```ts
extractFolderReadme(folderPath: string, entries: CatalogEntry[]): string | null
extractFirstParagraph(content: string): string | null
```

**External Dependencies**:
- `@/types/marketplace` → `CatalogEntry` type

**Internal Dependencies**:
- None

**Domain Coupling**: Generic - Treats content as plain markdown
- Strips frontmatter (uses regex, not the parser from frontmatter.ts)
- Extracts first meaningful paragraph
- Handles code blocks and special markdown syntax
- Works with any catalog entries

**Use Cases**:
- Extracting summary/description from folder READMEs
- Generating folder preview text
- Content summarization for any markdown files

**Extraction Readiness**: ✅ High - Generic markdown logic
- Only ties to CatalogEntry by convention (doesn't import types)
- Could easily work with any `{ path, content? }` object

**Quirk**:
- Uses `(readmeEntry as any).content` and `(readmeEntry as any).metadata` - assumes runtime property injection
- Fallback logic for metadata.description field

---

### 5. `/lib/folder-filter-utils.ts`

**Exports**:
```ts
applyFiltersToEntries(entries, filters): CatalogEntry[]
hasActiveFilters(filters): boolean
getFilterSummary(filters): string | null
groupByType(entries): Record<ArtifactType, CatalogEntry[]>
getCountsByStatus(entries): Record<CatalogStatus, number>
getCountsByType(entries): Record<ArtifactType, number>
getDisplayArtifactsForFolder(catalog, folderPath, leafContainers?): CatalogEntry[]
```

**External Dependencies**:
- `@/types/marketplace` → `CatalogEntry`, `CatalogFilters`, `ArtifactType`, `CatalogStatus`
- `@/hooks/use-detection-patterns` → `DEFAULT_LEAF_CONTAINERS`

**Internal Dependencies**:
- None

**Domain Coupling**: High - Works with CatalogEntry and SkillMeat enums
- Filters by artifact type, status, confidence score, search term
- Groups and counts artifacts by type/status
- Promotion logic for leaf container artifacts
- Case-insensitive search across name and path fields

**Use Cases**:
- Filtering folder view results
- Displaying filtered artifact counts
- Managing promoted artifacts from leaf containers

**Extraction Readiness**: 🟡 Medium - Generic filtering logic but SkillMeat-specific filter types
- Algorithm is generic
- Enum values (ArtifactType, CatalogStatus) are SkillMeat-specific
- Leaf container logic ties to marketplace

---

## Category 2: Custom React Hooks

### 1. `/hooks/use-catalog-files.ts`

**Exports**:
```ts
const catalogKeys = { all, trees(), tree(), contents(), content() }
useCatalogFileTree(sourceId, artifactPath)
useCatalogFileContent(sourceId, artifactPath, filePath)
```

**External Dependencies**:
- `@tanstack/react-query` → `useQuery`
- `@/lib/api/catalog` → `fetchCatalogFileTree`, `fetchCatalogFileContent`, response types

**Internal Dependencies**:
- `lib/api/catalog.ts` (API client functions)

**Domain Coupling**: None - Pure query hook pattern
- Generic TanStack Query hook structure
- Stale times: 5min for trees, 30min for content (configurable)
- Query enablement based on parameter presence
- Standard React hook patterns

**Use Cases**:
- Fetching file trees for marketplace artifacts
- Loading file content for preview/editing
- Cache management for file operations

**Extraction Readiness**: ✅ High - Generic hook, depends only on API functions
- Standard TanStack Query pattern
- Works with any API client following the interface
- Could work standalone with API client as dependency

**Cache Strategy**:
- Trees: 5min stale, 30min garbage collection
- Content: 30min stale, 2hr garbage collection
- Rationale: Content is larger and more stable

---

## Category 3: React Components

### 1. `/components/entity/file-tree.tsx`

**Props Interface**:
```ts
interface FileTreeProps {
  entityId: string                          // Unused parameter
  files: FileNode[]                          // Tree structure
  selectedPath: string | null                // Currently selected file
  onSelect: (path: string) => void           // Selection callback
  onAddFile?: () => void                     // Create file handler
  onDeleteFile?: (path: string) => void      // Delete file handler
  isLoading?: boolean                        // Loading skeleton state
  readOnly?: boolean                         // Hide create/delete buttons
  ariaLabel?: string                         // Accessibility label
}

type FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
}
```

**Exports**:
- `FileTree` component
- `FileNode` and `FileTreeProps` types

**External Dependencies**:
- `react` → `useState`, `useCallback`, `useRef`, `useEffect`
- `lucide-react` → Icon components (ChevronRight, ChevronDown, Folder, FileText, etc.)
- `@/lib/utils` → `cn()` (classname utility)
- `@/components/ui/button` → Button primitive
- `@/components/ui/skeleton` → Skeleton loader primitive

**Internal Dependencies**:
- None (types defined in component file)

**Domain Coupling**: None - Generic file tree component
- Works with any `FileNode` structure
- File type icons based on extension (md, ts, tsx, js, py, json, etc.)
- No SkillMeat-specific logic

**Features**:
- ✅ Recursive rendering of nested directories
- ✅ Expandable/collapsible folders with chevron icons
- ✅ File type icons (markdown, code, JSON, generic)
- ✅ Selected file highlighting
- ✅ Full keyboard navigation (Arrow keys, Enter, Space, Home, End)
- ✅ ARIA tree pattern for accessibility (role="tree", aria-expanded, aria-level, aria-setsize)
- ✅ Roving tabindex for efficient keyboard focus
- ✅ Optional delete actions
- ✅ Loading skeleton state
- ✅ Read-only mode (hides buttons)
- ✅ Empty state message

**Keyboard Support**:
- ↑/↓: Navigate visible items
- →: Expand folder or move to first child
- ←: Collapse folder or move to parent
- Enter/Space: Select file or toggle folder
- Home/End: First/last visible item

**Accessibility**:
- ARIA tree role
- Proper level indicators
- Screen reader position indicators (aria-posinset, aria-setsize)
- Focus management with roving tabindex
- Semantic keyboard navigation

**Extraction Readiness**: ✅ High - Completely generic
- No SkillMeat types or logic
- Only depends on shadcn primitives and lucide icons
- Works with any flat or nested file structure

**Styling**:
- Uses Tailwind CSS + shadcn color scheme
- Responsive spacing and sizing
- Smooth transitions
- Hover states for actions

---

### 2. `/components/entity/frontmatter-display.tsx`

**Props Interface**:
```ts
interface FrontmatterDisplayProps {
  frontmatter: Record<string, unknown>      // Parsed YAML object
  defaultCollapsed?: boolean                // Initial state
  className?: string                        // Extra CSS classes
}
```

**Exports**:
- `FrontmatterDisplay` component
- `FrontmatterDisplayProps` interface

**External Dependencies**:
- `react` → `useState`
- `lucide-react` → `ChevronDown`, `ChevronUp` icons
- `@/lib/utils` → `cn()` classname utility
- `@/components/ui/button` → Button primitive
- `@/components/ui/collapsible` → Collapsible + CollapsibleContent + CollapsibleTrigger

**Internal Dependencies**:
- None

**Domain Coupling**: None - Generic frontmatter display
- Works with any Record<string, unknown> object
- Renders values based on type (string, number, boolean, null, array, object)

**Features**:
- ✅ Collapsible section with expand/collapse button
- ✅ Type-aware rendering (strings, numbers, booleans, null, arrays, nested objects)
- ✅ Array values rendered as comma-separated strings
- ✅ Nested objects rendered as indented key-value pairs (1 level only)
- ✅ Max height with scrollable content (300px)
- ✅ Smooth animations
- ✅ Semantic key-value presentation

**Value Rendering**:
- `null/undefined`: "null" (italic, muted)
- `boolean`: "true"/"false" (muted)
- `number`: Direct render
- `string`: Direct render
- `array`: Comma-separated values
- `object`: Indented key-value pairs (1 level), nested objects as JSON

**Extraction Readiness**: ✅ High - Completely generic
- No domain-specific logic
- Only depends on shadcn primitives
- Works with any frontmatter object
- Component state management is isolated

**Use Cases**:
- Display YAML frontmatter from markdown files
- Show metadata from any structured data
- Content preview in editors

---

### 3. (Implied but not listed explicitly)

Note: The inventory mentions that marketplace integration components exist (`CatalogEntryModal`, etc.) but are not core to the content viewing package. Those would remain domain-specific.

---

## Category 4: Type Definitions

### 1. `/types/files.ts`

**Exports**:
```ts
interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  size?: number
  children?: FileNode[]
}

interface FileListResponse {
  artifact_id: string
  artifact_name: string
  artifact_type: string
  collection_name: string
  files: FileNode[]
}

interface FileContentResponse {
  artifact_id: string
  artifact_name: string
  artifact_type: string
  collection_name: string
  path: string
  content: string
  size: number
  mime_type?: string
}

interface FileUpdateRequest {
  content: string
}
```

**Domain Coupling**: Moderate - Contains SkillMeat API response structure
- `FileNode` is generic
- Response wrappers contain artifact_id, collection_name (SkillMeat-specific)
- Could be split: generic FileNode + SkillMeat response wrappers

**Use Cases**:
- API response typing
- File tree component props
- Content viewer integration

**Extraction Readiness**: 🟡 Medium
- Extract `FileNode` as core type
- Keep response types with domain logic

---

### 2. `/types/marketplace.ts` (CatalogEntry)

**Relevant Exports**:
```ts
interface CatalogEntry {
  id, source_id, artifact_type, name, path,
  upstream_url, detected_version, detected_sha, detected_at,
  confidence_score, status, import_date, import_id,
  excluded_at, excluded_reason, raw_score, score_breakdown,
  is_duplicate?, duplicate_reason?, duplicate_of?,
  in_collection?
}

interface CatalogFilters {
  artifact_type?: ArtifactType
  status?: CatalogStatus
  min_confidence?: number
  max_confidence?: number
  include_below_threshold?: boolean
  search?: string
  sort_by?: 'confidence' | 'name' | 'date'
  sort_order?: 'asc' | 'desc'
}

type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook'
type CatalogStatus = 'new' | 'imported' | 'excluded' | ...
```

**Domain Coupling**: High - Marketplace-specific
- Fields specific to artifact discovery and import
- Status values tie to marketplace workflow
- Confidence scoring for artifact detection

**Use Cases**:
- Catalog browsing and filtering
- Source integration

**Extraction Readiness**: 🔴 Low - Marketplace-specific types
- Would need abstracted if creating generic content viewer
- Could define base interface for content browsing utilities

---

## Category 5: API Client

### `/lib/api/catalog.ts`

**Exports**:
```ts
interface FileTreeEntry {
  path: string
  type: 'file' | 'tree'
  size?: number
}

interface FileTreeResponse {
  entries: FileTreeEntry[]
  cached: boolean
  cache_age_seconds?: number
}

interface FileContentResponse {
  content: string
  encoding: string
  size: number
  sha: string
  truncated?: boolean
  original_size?: number
  cached: boolean
  cache_age_seconds?: number
}

fetchCatalogFileTree(sourceId, artifactPath): Promise<FileTreeResponse>
fetchCatalogFileContent(sourceId, artifactPath, filePath): Promise<FileContentResponse>
```

**External Dependencies**:
- Built-in `fetch()` API
- Environment variables: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_API_VERSION`

**Internal Dependencies**:
- None

**Domain Coupling**: None - Generic HTTP client pattern
- Calls marketplace API endpoints
- Path parameter normalization (handles "." for root)
- URL encoding for safety
- Generic error handling

**Features**:
- ✅ Environment-aware URL building
- ✅ URL-safe path encoding
- ✅ Error extraction from responses
- ✅ Cache metadata in responses
- ✅ Truncation detection for large files

**Extraction Readiness**: ✅ High - Generic API client
- Follows standard fetch patterns
- Could be adapted to any API endpoint
- No business logic

---

## Category 6: Configuration & Constants

### Detection Patterns Hook (`use-detection-patterns.ts`)

**Exports**:
```ts
DEFAULT_LEAF_CONTAINERS = [
  'skills', 'commands', 'agents', 'hooks', 'mcp'
]
DEFAULT_ROOT_EXCLUSIONS = [
  'src', 'lib', 'dist', 'build', 'tests', '__tests__'
]
DEFAULT_CANONICAL_CONTAINERS = { /* mapping */ }
DEFAULT_CONTAINER_ALIASES = { /* mapping */ }

useDetectionPatterns(): DetectionPatternsResponse
```

**Domain Coupling**: High - SkillMeat artifact organization
- Defines what folders are "container" folders
- Defines root-level navigation exclusions
- Tied to SkillMeat's repository structure conventions

**Use Cases**:
- Configuring semantic folder filtering
- Artifact type detection

**Extraction Readiness**: 🟡 Medium - Pattern-specific but configurable
- Constants are SkillMeat-specific
- Hook pattern is generic
- Could be extracted as configuration object

---

## Summary Table: Extraction Readiness by Category

| Category | Component | Readiness | Notes |
|----------|-----------|-----------|-------|
| **Utilities** | frontmatter.ts | ✅ High | Generic YAML parser, no deps |
| | tree-builder.ts | 🟡 Medium | Generic algorithm, tied to CatalogEntry |
| | tree-filter-utils.ts | 🔴 Low | Highly domain-specific |
| | folder-readme-utils.ts | ✅ High | Generic markdown extraction |
| | folder-filter-utils.ts | 🟡 Medium | Generic filtering, SkillMeat enums |
| **Hooks** | use-catalog-files.ts | ✅ High | Generic TanStack Query pattern |
| **Components** | FileTree | ✅ High | Completely generic |
| | FrontmatterDisplay | ✅ High | Completely generic |
| **Types** | files.ts | 🟡 Medium | Generic + SkillMeat wrappers |
| | marketplace.ts | 🔴 Low | Marketplace-specific |
| **API** | catalog.ts | ✅ High | Generic HTTP client pattern |
| **Config** | Detection patterns | 🟡 Medium | Pattern-specific but configurable |

---

## Recommended Extraction Strategy

### Tier 1: Core Generic Package (`@skillmeat/content-viewer`)

**Include**:
- ✅ `frontmatter.ts` (pure YAML parsing)
- ✅ `folder-readme-utils.ts` (markdown extraction)
- ✅ `FileTree` component
- ✅ `FrontmatterDisplay` component
- ✅ `use-catalog-files` hook (with generic API client interface)
- ✅ `FileNode` type definition
- ✅ Generic API client pattern

**External Dependencies**:
- `@tanstack/react-query`
- `@radix-ui/primitives` (via shadcn)
- `lucide-react`
- `tailwindcss`

**No Dependencies On**:
- CatalogEntry type
- SkillMeat enums (ArtifactType, CatalogStatus)
- Detection patterns
- Marketplace APIs

---

### Tier 2: SkillMeat Integration Layer

**Include**:
- `tree-builder.ts` (adapt to be generic with type parameter)
- `tree-filter-utils.ts` (as configuration-driven filtering)
- `folder-filter-utils.ts` (filtering + grouping)
- `CatalogEntry` and related marketplace types
- Detection patterns constants
- Marketplace API client functions

**Dependencies On**:
- Tier 1 components
- Marketplace domain types

---

### Tier 3: SkillMeat App Features

**Include**:
- Catalog browsing pages
- Integration with SkillMeat-specific features
- Collection management UI
- Deployment workflows

---

## Files by Extraction Tier

### Tier 1 - Extract to Standalone Package

```
@skillmeat/content-viewer/
├── src/
│   ├── lib/
│   │   ├── frontmatter.ts         ← /lib/frontmatter.ts
│   │   ├── readme-utils.ts         ← /lib/folder-readme-utils.ts
│   │   └── api-client.ts           ← Generic API pattern from /lib/api/catalog.ts
│   ├── components/
│   │   ├── FileTree.tsx            ← /components/entity/file-tree.tsx
│   │   └── FrontmatterDisplay.tsx  ← /components/entity/frontmatter-display.tsx
│   ├── hooks/
│   │   └── useFileContent.ts       ← Adapted /hooks/use-catalog-files.ts
│   └── types/
│       └── index.ts                ← FileNode type
└── package.json
```

### Tier 2 - Keep in SkillMeat App (Market-aware)

```
skillmeat/web/
├── lib/
│   ├── tree-builder.ts            ← Adapt to be generic
│   ├── tree-filter-utils.ts        ← Keep SkillMeat-specific
│   ├── folder-filter-utils.ts      ← Keep SkillMeat-specific
│   └── api/
│       └── catalog.ts              ← Keep marketplace integration
├── hooks/
│   └── use-detection-patterns.ts   ← Configuration constants
└── types/
    └── marketplace.ts              ← SkillMeat domain types
```

---

## Dependencies & Compatibility Matrix

### Standalone Package Would Require

```
Dependencies:
- react ^18.0
- @tanstack/react-query ^5.0
- @radix-ui/react-collapsible ^1.0
- lucide-react ^0.400
- tailwindcss ^3.0
- tailwind-merge ^2.0 (for cn() utility)

Peer Dependencies:
- @radix-ui/react-primitive (via shadcn)

Dev Dependencies:
- typescript
- jsx support (react/jsx-runtime)
```

### SkillMeat Integration Layer Requires

```
Additional Dependencies on:
- @/types/marketplace (CatalogEntry)
- @/hooks/use-detection-patterns
- Detection pattern constants
```

---

## Component Integration Points

### FileTree Component Usage Pattern

```tsx
// Generic - works with any FileNode[]
<FileTree
  entityId="id"
  files={files}
  selectedPath={selectedPath}
  onSelect={handleSelect}
  readOnly={false}
/>

// With API integration
const { data: fileTree } = useCatalogFileTree(sourceId, artifactPath);
<FileTree files={fileTree?.entries || []} ... />
```

### FrontmatterDisplay Usage Pattern

```tsx
// Generic - works with any parsed YAML object
const { frontmatter } = parseFrontmatter(content);
<FrontmatterDisplay frontmatter={frontmatter} />
```

### Hook Integration Pattern

```tsx
// Core hook pattern (generic)
const { data, isLoading, error } = useCatalogFileTree(sourceId, path);

// With custom API client
const customHook = (id, path) => useQuery({
  queryKey: ['custom', id, path],
  queryFn: () => myCustomApiClient.fetchTree(id, path),
  staleTime: 5 * 60 * 1000,
});
```

---

## Known Limitations & Gotchas

### Tree Building

- Assumes `path` field on entries for hierarchy
- O(n*d) complexity (n=entries, d=depth) - acceptable for typical use
- Root-level artifacts (no path) are skipped

### Frontmatter Parsing

- Comment suggests using `yaml` or `js-yaml` package for production use
- Current parser handles common cases but may fail on complex YAML

### File Tree Navigation

- `entityId` prop is unused (could be removed in extraction)
- Focus management uses direct DOM focus() calls
- ArrowRight navigation doesn't auto-expand - TreeNode handles expansion

### Filter Utils

- `getDisplayArtifactsForFolder` has complex promotion logic tied to leaf containers
- Assumes CatalogEntry with `.path` property

### Catalog Files Hook

- `enablement` based on parameter nullness - disables query automatically
- Different stale times for trees (5min) vs content (30min)
- `gcTime` (formerly cacheTime) set to 30min and 2hr respectively

---

## Testing Considerations

### Units to Test

1. **Frontmatter parsing**: YAML strings with various data types
2. **Tree building**: Flat arrays with various path structures
3. **Tree filtering**: Semantic filtering with different leaf container configs
4. **File icons**: Extension-to-icon mapping
5. **Keyboard navigation**: All keyboard commands
6. **Accessibility**: ARIA attributes and focus management

### Example Test Cases

```typescript
// Frontmatter
test('parses YAML with nested objects')
test('handles quoted strings')
test('parses inline arrays')
test('strips frontmatter from content')

// Tree Building
test('builds folder hierarchy from flat paths')
test('calculates counts correctly')
test('respects maxDepth parameter')

// Filtering
test('filters semantic folders')
test('promotes leaf container artifacts')
test('excludes root exclusions')

// FileTree
test('keyboard navigation works')
test('aria attributes present')
test('file icons display correctly')

// Frontmatter Display
test('renders all value types')
test('collapses/expands correctly')
test('handles nested objects')
```

---

## Migration Path

### For Existing SkillMeat UI

If extracting to package, migration would be:

1. Create `@skillmeat/content-viewer` package with Tier 1 components
2. Update imports: `@/components/entity/file-tree` → `@skillmeat/content-viewer`
3. Create adapter layer in SkillMeat for marketplace-specific functionality
4. Keep tree-filter-utils and folder-filter-utils in main app

### Benefits of Extraction

- ✅ Reusable in other projects
- ✅ Clearer separation of concerns
- ✅ Easier testing in isolation
- ✅ Potential open-source opportunity
- ✅ Generic component library for content viewing

### Risks & Considerations

- ⚠️ Version management across packages
- ⚠️ Tailwind CSS configuration needs to be compatible
- ⚠️ Radix UI peer dependency requirements
- ⚠️ shadcn components path resolution
- ⚠️ Tree-filter-utils would need to stay in SkillMeat (domain-specific)

---

## Files Summary Table

| File Path | Type | Lines | Exports | Deps | Coupling | Extract |
|-----------|------|-------|---------|------|----------|---------|
| frontmatter.ts | Util | 398 | 3 funcs | None | Generic | ✅ Tier 1 |
| tree-builder.ts | Util | 189 | 1 func + types | CatalogEntry | Moderate | 🟡 Adapt |
| tree-filter-utils.ts | Util | 261 | 4 funcs | patterns | High | 🔴 Tier 2 |
| folder-readme-utils.ts | Util | 188 | 2 funcs | CatalogEntry | Generic | ✅ Tier 1 |
| folder-filter-utils.ts | Util | 333 | 7 funcs | enums | High | 🔴 Tier 2 |
| use-catalog-files.ts | Hook | 133 | 2 hooks | API | Generic | ✅ Tier 1 |
| file-tree.tsx | Component | 562 | 1 comp + types | lucide,button | Generic | ✅ Tier 1 |
| frontmatter-display.tsx | Component | 160 | 1 comp + types | lucide,button | Generic | ✅ Tier 1 |
| catalog.ts | API | 142 | 2 funcs + types | fetch | Generic | ✅ Tier 1 |
| files.ts | Types | 37 | 4 interfaces | - | Moderate | 🟡 Adapt |
| marketplace.ts | Types | 100+ | CatalogEntry + | - | High | 🔴 Tier 2 |

---

## Conclusion

The SkillMeat content viewing infrastructure has strong potential for extraction into a standalone, generic package. The core components (FileTree, FrontmatterDisplay) and utilities (frontmatter parsing, file fetching) are completely free of domain logic.

**Immediate extraction candidates**:
- Frontmatter parser
- Folder README extraction
- FileTree component
- FrontmatterDisplay component
- Generic file content hooks
- File API client pattern

**Keep with SkillMeat**:
- Tree filtering with detection patterns
- Catalog-specific filtering
- Marketplace type system
- Integration with SkillMeat workflows

This creates a clean layering where generic content viewing can be independent while marketplace/collection features remain in the main application.
