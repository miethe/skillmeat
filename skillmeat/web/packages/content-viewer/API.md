# @skillmeat/content-viewer — Public API Contract

**Contract version**: v0.0.1
**Package version**: 0.0.1
**Status**: Pre-extraction (Phase 1 complete — inventory locked)

This document is the approved export map for `@skillmeat/content-viewer`. It is the authoritative reference for what will be exported, in which phase, and under what signature.

---

## Export Map

### Components

| Export | Phase | Source file |
|--------|-------|-------------|
| `FileTree` | 2 | `components/entity/file-tree.tsx` |
| `FileTreeProps` | 2 | `components/entity/file-tree.tsx` |
| `FrontmatterDisplay` | 2 | `components/entity/frontmatter-display.tsx` |
| `FrontmatterDisplayProps` | 2 | `components/entity/frontmatter-display.tsx` |

**FileTree**

A file browser tree component for navigating artifact directory structures.

```typescript
interface FileTreeProps {
  entityId: string;
  files: FileNode[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onAddFile?: () => void;
  onDeleteFile?: (path: string) => void;
  isLoading?: boolean;
  readOnly?: boolean;
}
```

**FrontmatterDisplay**

Renders parsed YAML frontmatter as a collapsible key/value display.

```typescript
interface FrontmatterDisplayProps {
  frontmatter: Record<string, unknown>;
  defaultCollapsed?: boolean;
  className?: string;
}
```

---

### Utilities

| Export | Phase | Source file |
|--------|-------|-------------|
| `parseFrontmatter` | 2 | `lib/frontmatter.ts` |
| `stripFrontmatter` | 2 | `lib/frontmatter.ts` |
| `detectFrontmatter` | 2 | `lib/frontmatter.ts` |
| `extractFirstParagraph` | 2 | `lib/folder-readme-utils.ts` |
| `extractFolderReadme` | 2 | `lib/folder-readme-utils.ts` |

```typescript
function detectFrontmatter(content: string): boolean;

function parseFrontmatter(content: string): {
  frontmatter: Record<string, unknown>;
  content: string;
};

function stripFrontmatter(content: string): string;

function extractFirstParagraph(content: string): string | null;

// NOTE: signature will be genericized before export — see Discrepancies section
function extractFolderReadme(
  folderPath: string,
  entries: { path: string; content?: string }[]
): string | null;
```

---

### Types

| Export | Phase | Canonical source |
|--------|-------|-----------------|
| `FileNode` | 2 | `types/files.ts` |
| `FileTreeResponse` | 2 | `lib/api/catalog.ts` |
| `FileContentResponse` | 2 | `lib/api/catalog.ts` |

```typescript
// FileNode — canonical version from types/files.ts (includes optional `size`)
interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  children?: FileNode[];
}

// FileTreeResponse — catalog variant (marketplace/GitHub-backed)
interface FileTreeResponse {
  entries: FileTreeEntry[];
  cached: boolean;
  cache_age_seconds?: number;
}

interface FileTreeEntry {
  path: string;
  type: 'file' | 'tree';
  size?: number;
}

// FileContentResponse — catalog variant (marketplace/GitHub-backed)
interface FileContentResponse {
  content: string;
  encoding: string;
  size: number;
  sha: string;
  truncated?: boolean;
  original_size?: number;
  cached: boolean;
  cache_age_seconds?: number;
}
```

---

### Hooks

| Export | Phase | Source file |
|--------|-------|-------------|
| `useCatalogFileTree` | 3 | `hooks/use-catalog-files.ts` |
| `useCatalogFileContent` | 3 | `hooks/use-catalog-files.ts` |
| `catalogKeys` | 3 | `hooks/use-catalog-files.ts` |

Phase 3 hooks require an adapter abstraction layer so that the package is not hard-wired to a specific TanStack Query `QueryClient` instance or a `NEXT_PUBLIC_API_URL` environment variable. The adapter contract will be defined at the start of Phase 3.

```typescript
function useCatalogFileTree(
  sourceId: string | null,
  artifactPath: string | null
): UseQueryResult<FileTreeResponse, Error>;

function useCatalogFileContent(
  sourceId: string | null,
  artifactPath: string | null,
  filePath: string | null
): UseQueryResult<FileContentResponse, Error>;
```

---

### API Client Functions

| Export | Phase | Source file |
|--------|-------|-------------|
| `fetchCatalogFileTree` | 3 | `lib/api/catalog.ts` |
| `fetchCatalogFileContent` | 3 | `lib/api/catalog.ts` |

Phase 3 API client functions require an adapter for the base URL so the package is not coupled to `NEXT_PUBLIC_API_URL`.

```typescript
function fetchCatalogFileTree(
  sourceId: string,
  artifactPath: string
): Promise<FileTreeResponse>;

function fetchCatalogFileContent(
  sourceId: string,
  artifactPath: string,
  filePath: string
): Promise<FileContentResponse>;
```

---

## Discrepancies Found During Phase 0

The following conflicts were discovered during inventory and must be resolved before or during extraction.

### 1. FileNode dual definition

`FileNode` is defined in two places with slightly different shapes:

| Location | `size` field | `type` values |
|----------|-------------|---------------|
| `types/files.ts` | `size?: number` (present) | `'file' \| 'directory'` |
| `components/entity/file-tree.tsx` | absent | `'file' \| 'directory'` |

**Resolution**: The exported `FileNode` will use the `types/files.ts` definition (the more complete shape). The in-component definition in `file-tree.tsx` will be removed and the component will import from the package's `./types` module during Phase 2 extraction.

### 2. extractFolderReadme — CatalogEntry coupling

`extractFolderReadme` in `lib/folder-readme-utils.ts` accepts `CatalogEntry[]` (from `@/types/marketplace`). Exporting it as-is would pull the entire marketplace type graph into the package's public API, which is inappropriate for a general-purpose content viewer.

**Resolution**: Before export, the parameter type will be genericized to a duck-typed interface:

```typescript
interface ReadmeSearchEntry {
  path: string;
  content?: string;
  name?: string;
}
```

`CatalogEntry` satisfies this interface structurally, so no call sites need to change. This change will be made during Phase 2 extraction.

### 3. FileTreeResponse — three competing definitions

Three definitions of `FileTreeResponse` exist in the codebase:

| Location | Shape |
|----------|-------|
| `lib/api/catalog.ts` | `{ entries: FileTreeEntry[], cached: boolean, cache_age_seconds?: number }` |
| `sdk/models/FileTreeResponse.ts` (generated) | `{ entries: FileTreeEntry[], artifact_path: string, source_id: string }` |
| `types/files.ts` | Does not define `FileTreeResponse` — only `FileListResponse` (collection endpoint) |

The SDK type is auto-generated from OpenAPI and should not be re-exported as the package's public type; it may drift as the backend evolves. The `lib/api/catalog.ts` definition is the hand-authored, stable shape that hooks actually use.

**Resolution**: The exported `FileTreeResponse` will be the `lib/api/catalog.ts` version. The package will not re-export from `sdk/`.

### 4. FileContentResponse — catalog vs. collection variants

Two `FileContentResponse` shapes exist for different backend endpoints:

| Location | Endpoint | Fields |
|----------|----------|--------|
| `lib/api/catalog.ts` | Marketplace/GitHub catalog (`/marketplace/sources/…`) | `content`, `encoding`, `size`, `sha`, `truncated?`, `cached` |
| `types/files.ts` | Collection files (`/collections/…/files/…`) | `artifact_id`, `artifact_name`, `artifact_type`, `collection_name`, `path`, `content`, `size`, `mime_type?` |

These are responses from different APIs and are not interchangeable.

**Resolution**: The exported `FileContentResponse` will be the catalog variant from `lib/api/catalog.ts`, as the hooks being exported (`useCatalogFileContent`, `fetchCatalogFileContent`) use that endpoint. The collection variant in `types/files.ts` is out of scope for this package and will not be exported.

---

## Out of Scope

The following were considered and explicitly excluded:

- `FileListResponse` (`types/files.ts`) — collection-endpoint response, not catalog
- `FileUpdateRequest` (`types/files.ts`) — mutation type, this package is read-only
- `FileTreeEntry` — internal shape used by `FileTreeResponse`; may be exported as a companion type if consumers need it (deferred to Phase 2)
- `catalogKeys` query key factory — may be exported alongside hooks in Phase 3 if consumers need to perform cache invalidation externally
