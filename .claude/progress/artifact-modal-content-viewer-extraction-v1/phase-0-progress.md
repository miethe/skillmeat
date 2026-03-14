---
type: progress
schema_version: 2
doc_type: progress
prd: artifact-modal-content-viewer-extraction-v1
feature_slug: artifact-modal-content-viewer-extraction
phase: 0
phase_name: Baseline and Guardrails
prd_ref: /docs/project_plans/PRDs/refactors/artifact-modal-content-viewer-extraction-v1.md
plan_ref: /docs/project_plans/implementation_plans/refactors/artifact-modal-content-viewer-extraction-v1.md
status: in_progress
overall_progress: 0
completion_estimate: on-track
created: '2026-03-13'
updated: '2026-03-13'
started: '2026-03-13'
completed: null
tasks:
- id: BASE-001
  description: Baseline inventory lock — enumerate all components, hooks, and utilities
    in the current modal content viewer stack that are in-scope for extraction
  status: completed
  story_points: 1
  assigned_to: frontend-developer
  dependencies: []
- id: BASE-002
  description: Parity scenario matrix — document the functional parity scenarios that
    must pass after extraction, covering all content types and interaction paths
  status: completed
  story_points: 1
  assigned_to: testing specialist
  dependencies:
  - BASE-001
parallelization:
  batch_1:
  - BASE-001
  batch_2:
  - BASE-002
success_criteria:
- v1 extraction scope finalized and inventory locked
- Parity scenarios documented and approved before extraction begins
total_story_points: 2
completed_story_points: 2
total_tasks: 2
completed_tasks: 2
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

## Phase Objective

Lock the extraction scope with a precise inventory of in-scope components and produce a parity scenario matrix that will gate all subsequent phases.

## Implementation Notes

### Extraction Matrix (Locked)

Verified against source code on 2026-03-13. All paths relative to `skillmeat/web/`.

#### Items to Extract

**Components**

| Item | Source Path | Confirmed | Imports (SkillMeat-specific?) | Status |
|------|-------------|-----------|-------------------------------|--------|
| FileTree | `components/entity/file-tree.tsx` | Yes | `cn`, `Button`, `Skeleton`, lucide icons — all generic | confirmed |
| FrontmatterDisplay | `components/entity/frontmatter-display.tsx` | Yes | `cn`, `Button`, `Collapsible*`, lucide icons — all generic | confirmed |

**Utilities**

| Item | Source Path | Confirmed | Imports (SkillMeat-specific?) | Status |
|------|-------------|-----------|-------------------------------|--------|
| parseFrontmatter, stripFrontmatter, detectFrontmatter | `lib/frontmatter.ts` | Yes | No imports at all — pure functions | confirmed |
| extractFirstParagraph | `lib/folder-readme-utils.ts` | Yes | Pure function, no external imports | confirmed |
| extractFolderReadme | `lib/folder-readme-utils.ts` | Yes | Imports `CatalogEntry` from `@/types/marketplace` — NOT generic | **concern** |

**Hooks**

| Item | Source Path | Confirmed | Imports (SkillMeat-specific?) | Status |
|------|-------------|-----------|-------------------------------|--------|
| useCatalogFileTree | `hooks/use-catalog-files.ts` | Yes | `useQuery` + `@/lib/api/catalog` — generic after catalog.ts extracts | confirmed |
| useCatalogFileContent | `hooks/use-catalog-files.ts` | Yes | `useQuery` + `@/lib/api/catalog` — generic after catalog.ts extracts | confirmed |

**Types**

| Item | Source Path | Confirmed | Notes | Status |
|------|-------------|-----------|-------|--------|
| FileNode | `types/files.ts` | Yes | Has `size?: number` field; `file-tree.tsx` defines its own local `FileNode` without `size` — two divergent definitions exist | **concern** |
| FileTreeResponse | `lib/api/catalog.ts` | Yes | Generic — no SkillMeat-specific imports | confirmed |
| FileContentResponse | `lib/api/catalog.ts` | Yes | Distinct from `types/files.ts#FileContentResponse` (that one is collection-API specific, not catalog) | confirmed |

**API Clients**

| Item | Source Path | Confirmed | Notes | Status |
|------|-------------|-----------|-------|--------|
| fetchCatalogFileTree | `lib/api/catalog.ts` | Yes | Uses `NEXT_PUBLIC_API_URL` env var — portable | confirmed |
| fetchCatalogFileContent | `lib/api/catalog.ts` | Yes | Same pattern — portable | confirmed |

---

#### Items to Keep Local (Confirmed)

| Item | Source Path | Confirmed | Reason |
|------|-------------|-----------|--------|
| filterSemanticTree | `lib/tree-filter-utils.ts` | Yes | SkillMeat detection pattern coupling |
| applyFiltersToEntries | `lib/folder-filter-utils.ts` | Yes | Uses `CatalogEntry` and SkillMeat enums |
| useDetectionPatterns | `hooks/use-detection-patterns.ts` | Yes | Returns SkillMeat-specific patterns |

---

#### Phase 3 Extension Component Locations

These were not listed in the quick-ref as extraction candidates but are referenced by the content viewer stack:

| Component | Actual Path | Notes |
|-----------|-------------|-------|
| ContentPane | `components/entity/content-pane.tsx` | Imports `SplitPreview` and `FrontmatterDisplay` — composite, stays local |
| SplitPreview | `components/editor/split-preview.tsx` | Imports `MarkdownEditor` and `react-markdown` — editor path, not `components/entity/` |
| MarkdownEditor | `components/editor/markdown-editor.tsx` | Uses CodeMirror extensions — editor-specific, stays local |

---

#### Discrepancies vs Quick-Ref

1. **extractFolderReadme is NOT 100% generic.** The quick-ref marks it "Ready" with no dependencies, but the function signature accepts `CatalogEntry[]` from `@/types/marketplace`. Extraction requires either: (a) replacing the parameter type with a structural duck-type (an interface with `path` and optional `content`/`metadata` fields), or (b) extracting only `extractFirstParagraph` and keeping `extractFolderReadme` local. Recommended: duck-type the parameter — the function only reads `.path`, `.content`, and `.metadata` off entries.

2. **FileNode has two divergent definitions.** `types/files.ts` exports `FileNode` with an optional `size` field; `components/entity/file-tree.tsx` defines its own inline `FileNode` (same name, no `size` field) and does not import from `types/files.ts`. The extracted package should define one canonical `FileNode` (include `size?: number`). The inline definition in `file-tree.tsx` must be replaced with an import before extraction.

3. **Phase 3 components are in `components/editor/`, not `components/entity/`.** SplitPreview and MarkdownEditor live under `components/editor/split-preview.tsx` and `components/editor/markdown-editor.tsx`. ContentPane (`components/entity/content-pane.tsx`) composes them but is itself SkillMeat-specific (imports both SplitPreview and FrontmatterDisplay, manages edit state tied to collection file API). None of the three are extraction candidates for v1.

4. **`types/files.ts#FileContentResponse` is a different type from `lib/api/catalog.ts#FileContentResponse`.** The `types/files.ts` version is tied to the collection file API (has `artifact_id`, `collection_name` fields). The catalog version is a GitHub-backed response (has `sha`, `truncated`, `cached` fields). Only the catalog version is in scope for extraction. The quick-ref correctly identifies `lib/api/catalog.ts` as the source — no action needed, but implementers must not conflate the two.

---

## Parity Scenario Matrix

Verified against `components/CatalogEntryModal.tsx`, `components/entity/file-tree.tsx`, `components/entity/frontmatter-display.tsx`, `components/entity/content-pane.tsx`, `lib/frontmatter.ts`, `lib/folder-readme-utils.ts`, and `hooks/use-catalog-files.ts` on 2026-03-13.

**Scope**: These scenarios apply to the Contents tab of `CatalogEntryModal`. The tab renders a two-panel split: a 280px fixed-width FileTree on the left and a ContentPane on the right. The modal is always in read-only mode for the catalog context (`readOnly` prop is always `true`).

**Priority definitions**:
- P0: Extraction blocker — any regression here means the extraction failed
- P1: Important regression that must be fixed before merging
- P2: Cosmetic or edge-case regression; document and fix post-merge if needed

---

### Selection Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| SEL-001 | Selection | No file selected, file tree has loaded successfully | ContentPane shows a "Select a file" empty state with a FileText icon and instructional text. No API request for file content is initiated (`useCatalogFileContent` query is disabled because `filePath` is null). | P0 |
| SEL-002 | Selection | Auto-select on tree load — artifact has at least one `.md` file | When `fileTreeData` arrives and `selectedFilePath` is null, the first `.md` file (case-insensitive match on `.endsWith('.md')`) in the flat `entries` array is automatically selected. Content fetch begins immediately. | P0 |
| SEL-003 | Selection | Auto-select on tree load — artifact has no `.md` files | When `fileTreeData` arrives and `selectedFilePath` is null with no markdown files, the first file alphabetically by path (among entries with `type === 'file'`) is automatically selected. | P0 |
| SEL-004 | Selection | Auto-select on tree load — artifact has only directories, no files | `selectedFilePath` remains null. ContentPane shows empty state. No auto-select fires. | P1 |
| SEL-005 | Selection | User clicks a file node in the tree | `onSelect` callback fires with the file's `path`. `selectedFilePath` updates. ContentPane triggers content fetch. Previously selected file is deselected (highlight moves). | P0 |
| SEL-006 | Selection | User clicks a directory node | Directory expands or collapses (toggle). `selectedFilePath` does not change. No content fetch is triggered. | P0 |
| SEL-007 | Selection | User selects a file, then opens a different artifact entry | `selectedFilePath` resets to null. Tree and content data clear. Auto-select fires again when new tree loads. | P0 |
| SEL-008 | Selection | File at root level (no subdirectory) selected | Path stored in `selectedFilePath` contains no `/`. Content fetch URL encodes the path correctly. ContentPane displays content. | P1 |
| SEL-009 | Selection | File inside a deeply nested directory (3+ levels) selected | Path stored in `selectedFilePath` is the full relative path (e.g., `commands/advanced/nested/file.md`). Content fetch uses that full path. ContentPane displays content. | P1 |
| SEL-010 | Selection | Folder node selected via keyboard Enter/Space | Directory toggles expand/collapse; no file selection or content fetch occurs. | P0 |

---

### Loading Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| LOD-001 | Loading | File tree query is in-flight | FileTree renders `FileTreeSkeleton` (8 skeleton rows at staggered indent levels). ContentPane is not shown (right panel is present but empty/no-select state). | P0 |
| LOD-002 | Loading | File content query is in-flight after file selection | ContentPane renders its own loading skeleton (3 Skeleton lines for header + content area). FileTree remains interactive during this time. | P0 |
| LOD-003 | Loading | File tree query returns successfully | Skeleton is replaced by the rendered tree. `buildFileStructure` is called to convert flat `FileTreeEntry[]` into hierarchical `FileNode[]`. Auto-select fires (SEL-002/SEL-003). | P0 |
| LOD-004 | Loading | File content query returns successfully | ContentPane skeleton is replaced by the actual file content. FrontmatterDisplay appears above content if frontmatter is detected. | P0 |
| LOD-005 | Loading | File tree query is enabled only when `entry` is truthy | `useCatalogFileTree` is called with `sourceId: entry ? sourceId : null`. When modal first opens with no entry, both args are null and the query does not fire. | P1 |
| LOD-006 | Loading | File content query is enabled only when all three params are non-null and non-empty | `useCatalogFileContent` is disabled when `sourceId`, `artifactPath`, or `filePath` is null/empty. Disabling is tested by checking `selectedFilePath === null` keeps content query inactive. | P0 |
| LOD-007 | Loading | Empty file tree response (no entries) | `buildFileStructure([])` returns `[]`. FileTree renders the "No files found" empty state (Folder icon, "No files found" heading, "This entity does not contain any files yet" subtext). ContentPane shows select-file empty state. | P0 |
| LOD-008 | Loading | Tree response served from cache (`cached: true`) | Behavior is identical to a non-cached response from the user's perspective. No visual indicator of cache status is shown in the Contents tab. | P2 |
| LOD-009 | Loading | Switching between tabs (Contents → Overview → Contents) | On return to Contents tab, cached data is displayed immediately without re-fetching (5min staleTime for tree, 30min staleTime for content). Selected file state is preserved in local state. | P1 |

---

### File Tree Structure Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| TRE-001 | FileTree | Flat artifact with only root-level files | Tree renders all files at level 0 with no indentation (level=0, paddingLeft=8px). No directory nodes. | P0 |
| TRE-002 | FileTree | Mixed flat file list with implicit parent directories | `buildFileStructure` synthesizes intermediate directory nodes for any path containing `/`. Directories are sorted first, then alphabetically. Files within each directory are sorted alphabetically. | P0 |
| TRE-003 | FileTree | Directory node rendering — collapsed state | Directory shows `ChevronRight` icon, `Folder` icon (blue), and directory name. `aria-expanded="false"`. Children are not rendered in the DOM. | P0 |
| TRE-004 | FileTree | Directory node rendering — expanded state | Directory shows `ChevronDown` icon, `FolderOpen` icon (blue), and directory name. `aria-expanded="true"`. Children are rendered in a `role="group"` container with the label "Contents of {name}". | P0 |
| TRE-005 | FileTree | File icon selection by extension | `.md`/`.txt` → FileText icon. `.ts`/`.tsx`/`.js`/`.jsx`/`.py`/`.java`/`.cpp`/`.c`/`.go`/`.rs` → FileCode icon. `.json` → Braces icon. All other extensions → File icon. Icon color is `text-muted-foreground`. | P1 |
| TRE-006 | FileTree | Read-only mode — no delete or add buttons | When `readOnly={true}` (always the case in CatalogEntryModal), the "Add file" button header is absent, and no delete button appears on hover. `onDelete` is passed as `undefined` to TreeNode. | P0 |
| TRE-007 | FileTree | Selected file highlighting | The selected node has `bg-accent text-accent-foreground` classes applied. Exactly one node is highlighted at a time. | P0 |
| TRE-008 | FileTree | `aria-label` set on tree root | The `role="tree"` div has `aria-label` set to `"File browser for {entry.name}"` (passed as `ariaLabel` prop from CatalogEntryModal). | P1 |
| TRE-009 | FileTree | `data-testid` attributes on tree items | Each tree item has `data-testid="tree-item-{node.path}"`. The root tree div has `data-testid="file-tree"`. | P1 |
| TRE-010 | FileTree | Very long file names | Name text truncates with `truncate` class (CSS ellipsis). Container uses `min-w-0 flex-1` to allow shrinking. Layout does not break. | P2 |
| TRE-011 | FileTree | File name with special characters (spaces, brackets, parentheses) | Name renders as-is in the tree. Path is passed directly to `onSelect`. Content fetch URL-encodes the path via `encodeURIComponent`. | P1 |
| TRE-012 | FileTree | Single-file artifact (artifact path already is a `.md` file) | `fetchCatalogFileTree` is called with the full artifact path (including extension). Backend returns a single-entry list. Tree renders one file node. Auto-select fires for that file immediately. | P0 |

---

### Keyboard Navigation Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| KEY-001 | Keyboard | ArrowDown from a file node | Focus moves to the next visible node in the flattened list. If at the last node, focus stays. `setFocusedPath` is called. The focused element receives DOM focus via `useEffect` on `isFocused`. | P0 |
| KEY-002 | Keyboard | ArrowUp from a file node | Focus moves to the previous visible node in the flattened list. If at the first node, focus stays. | P0 |
| KEY-003 | Keyboard | Home key from any node | Focus jumps to the first visible node in the tree (index 0 of `flattenVisibleNodes`). | P0 |
| KEY-004 | Keyboard | End key from any node | Focus jumps to the last visible node in the flattened list. | P0 |
| KEY-005 | Keyboard | ArrowRight on a collapsed directory | Directory expands (toggle fires). Focus stays on the directory node. | P0 |
| KEY-006 | Keyboard | ArrowRight on an already-expanded directory | Focus moves to the first child of that directory. | P0 |
| KEY-007 | Keyboard | ArrowRight on a file node | No action (key is not handled for files in `handleKeyNavigation`). | P1 |
| KEY-008 | Keyboard | ArrowLeft on an expanded directory | Directory collapses (toggle fires, handled in `TreeNode.handleKeyDown`). Focus stays on directory. | P0 |
| KEY-009 | Keyboard | ArrowLeft on a collapsed directory or file node | Focus moves to the parent directory node (derived by popping the last path segment and finding the node). If no parent exists (root-level node), focus stays. | P0 |
| KEY-010 | Keyboard | Enter on a file node | `onSelect(node.path)` fires. `selectedFilePath` updates. Content fetch begins. Equivalent to a click. | P0 |
| KEY-011 | Keyboard | Space on a file node | `onSelect(node.path)` fires. Same as Enter. Default browser scroll behavior is prevented (`e.preventDefault()`). | P0 |
| KEY-012 | Keyboard | Enter on a directory node | Directory toggles expand/collapse. No file selection occurs. | P0 |
| KEY-013 | Keyboard | Space on a directory node | Directory toggles expand/collapse. Default browser scroll behavior is prevented. | P0 |
| KEY-014 | Keyboard | Roving tabindex — initial state | The node matching `selectedFilePath` (if any) or the first node gets `tabIndex={0}`. All other nodes get `tabIndex={-1}`. Only the focused node has `tabIndex={0}` at any time. | P0 |
| KEY-015 | Keyboard | Roving tabindex — after keyboard navigation | After moving focus with arrow keys, only the newly focused node has `tabIndex={0}`. DOM focus is programmatically moved via `nodeRef.current.focus()` in a `useEffect`. | P0 |
| KEY-016 | Keyboard | ArrowDown from expanded directory (last child visible before next sibling) | Focus moves to the next sibling of the expanded directory, not back into the directory. `flattenVisibleNodes` must correctly order children before siblings. | P0 |

---

### ARIA and Accessibility Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| A11Y-001 | Accessibility | Root tree element role | The outer scrollable div carries `role="tree"` and `aria-label="{ariaLabel}"`. | P0 |
| A11Y-002 | Accessibility | Tree item role | Each `TreeNode` renders a `role="treeitem"` div. The wrapper div carrying children has `role="none"` to avoid polluting the tree structure. | P0 |
| A11Y-003 | Accessibility | `aria-selected` on file nodes | Selected file node has `aria-selected={true}`. All other nodes have `aria-selected={false}`. | P0 |
| A11Y-004 | Accessibility | `aria-expanded` on directory nodes | Expanded directory has `aria-expanded={true}`. Collapsed directory has `aria-expanded={false}`. File nodes have `aria-expanded={undefined}` (prop not set). | P0 |
| A11Y-005 | Accessibility | `aria-level` reflects nesting depth | Root nodes have `aria-level={1}` (level prop 0 + 1). Each nesting level increments by 1. | P1 |
| A11Y-006 | Accessibility | `aria-setsize` and `aria-posinset` | `aria-setsize` is the total count of all currently visible nodes (from `flattenVisibleNodes`). `aria-posinset` is the 1-based index among the root items (passed as `positionInSet` from parent). Note: for child nodes this is `index + 1` within their sibling list, not the global position — this is a documented simplification. | P1 |
| A11Y-007 | Accessibility | All decorative icons have `aria-hidden="true"` | Chevron icons, folder/file icons, and the Trash2 icon all carry `aria-hidden="true"`. | P1 |
| A11Y-008 | Accessibility | Delete button accessible label | Delete button (when present in non-read-only mode) has `aria-label="Delete {node.name}"`. It is excluded from tab order (`tabIndex={-1}`) and only appears on hover or focus of the row. | P1 |
| A11Y-009 | Accessibility | Child group label | When a directory is expanded, its children are wrapped in `role="group"` with `aria-label="Contents of {node.name}"`. | P1 |
| A11Y-010 | Accessibility | FrontmatterDisplay toggle button accessible label | When expanded, the toggle button has `aria-label="Hide frontmatter"`. When collapsed, it has `aria-label="Show frontmatter"`. | P0 |
| A11Y-011 | Accessibility | ContentPane region label | ContentPane root element has `aria-label` set to its `ariaLabel` prop (default "File content viewer"). | P1 |
| A11Y-012 | Accessibility | focus-visible ring on tree items | Tree item nodes show `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1` when focused via keyboard. Mouse focus does not show the ring (focus-visible only). | P1 |

---

### Content Display Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| CON-001 | Content | Markdown file without frontmatter | ContentPane displays rendered markdown. No FrontmatterDisplay panel appears. `detectFrontmatter` returns false. | P0 |
| CON-002 | Content | Markdown file with valid YAML frontmatter | `detectFrontmatter` returns true. `parseFrontmatter` extracts the frontmatter object and clean body. FrontmatterDisplay renders above the markdown body. Body content does not include the `---` block. | P0 |
| CON-003 | Content | Markdown file where frontmatter parsing fails (malformed YAML) | `parseFrontmatter` catches the error (logs a console warning). Returns `{ frontmatter: null, content: cleanContent }`. FrontmatterDisplay does not render (null frontmatter skips it). The body content (with `---` block stripped) is still displayed. | P0 |
| CON-004 | Content | TypeScript/JavaScript code file | ContentPane uses `SplitPreview` which detects non-markdown content and renders in a code block with syntax highlighting. No FrontmatterDisplay. | P1 |
| CON-005 | Content | JSON file | Same as CON-004 — code block rendering. Braces icon in the file tree. | P1 |
| CON-006 | Content | YAML/TOML configuration file | Same as CON-004 — code block rendering. Generic File icon in tree (YAML/TOML not in the extension-to-icon map). | P1 |
| CON-007 | Content | Plain text file (`.txt`) | FileText icon in tree. ContentPane renders content. `detectFrontmatter` will return false unless the file starts with `---`. | P2 |
| CON-008 | Content | File with content exactly at the truncation boundary | `fileContentData.truncated` is false. No truncation banner shown. Full content displayed. | P1 |
| CON-009 | Content | Truncated file (`fileContentData.truncated === true`) | ContentPane receives `truncationInfo={{ truncated: true, originalSize: fileContentData.original_size, fullFileUrl: <github_url> }}`. ContentPane displays a truncation warning banner with the original file size and a "View full file" link to GitHub. | P0 |
| CON-010 | Content | Truncated file — GitHub URL construction | `buildGitHubFileUrl` parses `entry.upstream_url` to extract `owner` and `repo`. Constructs `https://github.com/{owner}/{repo}/blob/{sha}/{artifactPath}/{filePath}`. If `entry.detected_sha` is present, uses it as the ref; otherwise defaults to `HEAD`. | P1 |
| CON-011 | Content | File with empty content (0 bytes) | ContentPane receives `content=""`. `detectFrontmatter("")` returns false. No FrontmatterDisplay. ContentPane renders an empty code view or empty markdown view (no explicit empty-content state — behavior determined by SplitPreview/ContentPane internals). | P2 |
| CON-012 | Content | File whose path does not end with a known extension | Generic File icon in tree. ContentPane renders content as-is. | P2 |
| CON-013 | Content | Artifact path that is itself a file path (e.g., `commands/foo.md`) | `fetchCatalogFileContent` calls `resolveArtifactPaths` which splits into `artifactDir="commands"` and `derivedFilePath="foo.md"`. URL is constructed without double-path duplication. | P0 |
| CON-014 | Content | Artifact path that is `.` (repository root) | `fetchCatalogFileTree` and `fetchCatalogFileContent` normalize `.` to empty string before URL construction to avoid the `/artifacts/./files` routing failure. | P0 |

---

### Frontmatter Display Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| FM-001 | Frontmatter | `detectFrontmatter` — content starts with `---\n` | Returns true. The regex `/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/` must match from position 0. | P0 |
| FM-002 | Frontmatter | `detectFrontmatter` — content does not start with `---` | Returns false regardless of content. | P0 |
| FM-003 | Frontmatter | `detectFrontmatter` — empty string or non-string input | Returns false. No exception thrown. | P0 |
| FM-004 | Frontmatter | `parseFrontmatter` — string scalar values | `title: Hello World` produces `{ title: "Hello World" }`. Unquoted string returned as-is. | P0 |
| FM-005 | Frontmatter | `parseFrontmatter` — quoted string values (single and double) | `title: "Hello"` and `title: 'Hello'` both produce `{ title: "Hello" }` with quotes stripped. | P1 |
| FM-006 | Frontmatter | `parseFrontmatter` — integer values | `version: 2` produces `{ version: 2 }` (number type, not string). | P0 |
| FM-007 | Frontmatter | `parseFrontmatter` — float values | `score: 3.14` produces `{ score: 3.14 }`. | P1 |
| FM-008 | Frontmatter | `parseFrontmatter` — boolean values (`true`, `false`, `yes`, `no`, `on`, `off`) | All six produce `true` or `false` as a boolean. Case-insensitive. | P1 |
| FM-009 | Frontmatter | `parseFrontmatter` — null values (`null`, `~`) | Both produce `null`. Case-insensitive. | P1 |
| FM-010 | Frontmatter | `parseFrontmatter` — inline array `[a, b, c]` | Produces `["a", "b", "c"]` (items are parsed through `parseValue`). | P0 |
| FM-011 | Frontmatter | `parseFrontmatter` — block array (dash-item format) | Multi-line `tags:\n- react\n- typescript` produces `{ tags: ["react", "typescript"] }`. | P0 |
| FM-012 | Frontmatter | `parseFrontmatter` — nested object (indentation-based) | `author:\n  name: Alice\n  email: alice@example.com` produces `{ author: { name: "Alice", email: "alice@example.com" } }`. | P1 |
| FM-013 | Frontmatter | `parseFrontmatter` — inline object `{key: val}` | `meta: {key: val}` produces `{ meta: { key: "val" } }`. | P2 |
| FM-014 | Frontmatter | `parseFrontmatter` — clean body content | The returned `content` field has the entire `---\n...\n---\n` block removed. The body starts immediately after the closing `---`. | P0 |
| FM-015 | Frontmatter | `FrontmatterDisplay` — zero entries in frontmatter object | Component returns null and renders nothing. The parent ContentPane receives a null frontmatter and should not render FrontmatterDisplay at all. | P0 |
| FM-016 | Frontmatter | `FrontmatterDisplay` — default expanded state | `defaultCollapsed={false}` (default). On mount, `isOpen=true`. CollapsibleContent is visible. Toggle button shows "Hide" with ChevronUp icon and `aria-label="Hide frontmatter"`. | P0 |
| FM-017 | Frontmatter | `FrontmatterDisplay` — user clicks toggle to collapse | `isOpen` becomes false. CollapsibleContent animates out (`animate-collapsible-up`). Toggle button shows "Show" with ChevronDown icon and `aria-label="Show frontmatter"`. | P0 |
| FM-018 | Frontmatter | `FrontmatterDisplay` — user clicks toggle to expand after collapse | `isOpen` becomes true. CollapsibleContent animates in (`animate-collapsible-down`). Toggle button reverts to "Hide". | P0 |
| FM-019 | Frontmatter | `FrontmatterDisplay` — array value rendering | Array items are rendered as a comma-separated string (each item converted via `String()` for primitives or `JSON.stringify()` for objects). | P1 |
| FM-020 | Frontmatter | `FrontmatterDisplay` — nested object rendering | Nested object is rendered as an indented block with `ml-4 mt-1 space-y-1`. Each sub-key is bold. Deeply nested values (2+ levels) are `JSON.stringify`-ed inline. | P1 |
| FM-021 | Frontmatter | `FrontmatterDisplay` — null/undefined value rendering | Renders `<span class="italic text-muted-foreground">null</span>`. | P1 |
| FM-022 | Frontmatter | `FrontmatterDisplay` — boolean value rendering | Renders `"true"` or `"false"` as a string in `text-muted-foreground`. | P2 |
| FM-023 | Frontmatter | `FrontmatterDisplay` — max-height overflow | The key-value content area has `max-h-[300px] overflow-y-auto`. When frontmatter has many keys, the content scrolls within the component rather than overflowing the page. | P1 |

---

### Error State Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| ERR-001 | Error | File tree fetch fails — generic API error | Left panel (FileTree area) is replaced by an error state: `AlertCircle` icon, `getErrorMessage(treeError, true).title` heading, description text. Two buttons: "Try again" (calls `refetchTree()`) and "View on GitHub" (links to `entry.upstream_url`). FileTree component is not rendered. | P0 |
| ERR-002 | Error | File tree fetch fails — GitHub rate limit (HTTP 429 or message contains "rate limit") | `getErrorMessage` returns a rate-limit-specific title and description. Same error UI as ERR-001 with retry and GitHub link buttons. | P0 |
| ERR-003 | Error | File tree fetch fails — network error (message contains "network" or "fetch") | `getErrorMessage` returns a network-error-specific description. Same error UI. | P1 |
| ERR-004 | Error | File tree fetch fails — 404 Not Found (message contains "404" or "not found") | `getErrorMessage` returns a not-found-specific title and description. Same error UI. | P1 |
| ERR-005 | Error | File tree error — "Try again" button | Clicking the button calls `refetchTree()` (TanStack Query `refetch` function). The query re-fires. The error state is shown again if it fails, or replaced by the tree if it succeeds. | P0 |
| ERR-006 | Error | File tree error — "View on GitHub" link | Opens `entry.upstream_url` in a new tab (`target="_blank" rel="noopener noreferrer"`). | P1 |
| ERR-007 | Error | File content fetch fails — any error | Right panel (ContentPane area) is replaced by an error state: `AlertCircle` icon, `getErrorMessage(contentError, false).title`, description. Two buttons: "Try again" (calls `refetchContent()`) and "View on GitHub". FileTree remains interactive. | P0 |
| ERR-008 | Error | File content error — "Try again" button | Calls `refetchContent()`. Tree stays functional. If retry succeeds, ContentPane replaces the error state. | P0 |
| ERR-009 | Error | File content error — switching to a different file after an error | `selectedFilePath` changes. New `useCatalogFileContent` query fires with updated `filePath`. Previous error is cleared because the query key changes. | P0 |
| ERR-010 | Error | Both tree and content errors simultaneously | Left panel shows tree error state. Right panel shows content error state. Both error UIs are independent. | P1 |

---

### `extractFirstParagraph` Utility Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| PAR-001 | Utility | Content with frontmatter — paragraph is extracted from body only | Frontmatter block (`---\n...\n---`) is stripped before line processing. First paragraph does not include frontmatter keys. | P0 |
| PAR-002 | Utility | Content where first meaningful text is under a heading | Headings (lines starting with `#`) are skipped. First non-heading, non-empty paragraph is returned. | P1 |
| PAR-003 | Utility | Content where all text is inside code fences | Lines inside triple-backtick fences are skipped (`inCodeBlock` flag). Returns null if no paragraph found outside code. | P1 |
| PAR-004 | Utility | Content where first paragraph is shorter than 20 characters | Returns null (minimum length check fails). | P1 |
| PAR-005 | Utility | Content where first paragraph is longer than 300 characters | Returns the first 297 characters with `"..."` appended. | P1 |
| PAR-006 | Utility | Content with list items only (lines starting with `-`, `*`, `>`, `|`) | All list/blockquote/table lines are skipped. Returns null if no plain paragraph exists. | P2 |
| PAR-007 | Utility | Empty string input | Returns null immediately. No exception. | P1 |
| PAR-008 | Utility | Non-string input | Returns null immediately. No exception. | P1 |

---

### Query Cache and Stale Time Scenarios

| Scenario ID | Category | Description | Expected Behavior | Priority |
|-------------|----------|-------------|-------------------|----------|
| QRY-001 | Caching | File tree query stale time | `useCatalogFileTree` uses `staleTime: 5 * 60 * 1000` (5 minutes). Data fetched within 5 minutes is served from cache without a network request when the modal reopens. | P1 |
| QRY-002 | Caching | File tree query garbage collection time | `gcTime: 30 * 60 * 1000` (30 minutes). Inactive cache entries are retained for 30 minutes before eviction. | P2 |
| QRY-003 | Caching | File content query stale time | `useCatalogFileContent` uses `staleTime: 30 * 60 * 1000` (30 minutes). Aggressive caching because file content rarely changes. | P1 |
| QRY-004 | Caching | File content query garbage collection time | `gcTime: 2 * 60 * 60 * 1000` (2 hours). Large content blobs are held in memory for 2 hours. | P2 |
| QRY-005 | Caching | Query key structure — tree | Key is `['catalog', 'tree', sourceId, artifactPath]`. Changing either `sourceId` or `artifactPath` results in a cache miss and new fetch. | P0 |
| QRY-006 | Caching | Query key structure — content | Key is `['catalog', 'content', sourceId, artifactPath, filePath]`. Changing `filePath` (user selects a new file) triggers a new fetch while the old entry stays in cache. | P0 |
| QRY-007 | Caching | `catalogKeys` hierarchy supports targeted invalidation | `catalogKeys.all` = `['catalog']`. Invalidating this key evicts all tree and content queries. `catalogKeys.trees()` evicts only tree queries. Correct hierarchy must be preserved after extraction. | P1 |

## Completion Notes

<!-- Filled in when phase is marked complete. -->
