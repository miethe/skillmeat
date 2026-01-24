# Marketplace Artifact Import & Deletion Patterns

**Date**: 2026-01-23
**Context**: Understanding import tracking, deletion flow, and artifact catalog modal structure
**Status**: Exploration Complete

---

## 1. Import Tracking Mechanism

### MarketplaceCatalogEntry Model (Database)

**File**: `skillmeat/cache/models.py:1501-1632`

The `MarketplaceCatalogEntry` model tracks import status with the following key fields:

```python
class MarketplaceCatalogEntry(Base):
    # Core identification
    id: str                          # Unique catalog entry ID (PK)
    source_id: str                   # Foreign key to MarketplaceSource
    artifact_type: str               # skill, command, agent, mcp_server, hook
    name: str                        # Artifact name
    path: str                        # Path within repository
    upstream_url: str                # Full GitHub URL to artifact

    # Import tracking fields
    status: str                      # "new" | "updated" | "removed" | "imported" | "excluded"
    import_date: Optional[datetime]  # When artifact was imported to collection
    import_id: Optional[str]         # Reference to imported artifact ID

    # Exclusion tracking
    excluded_at: Optional[datetime]  # Timestamp when marked as "not an artifact"
    excluded_reason: Optional[str]   # User-provided reason (max 500 chars)

    # Quality metrics
    confidence_score: int            # 0-100 heuristic confidence
    raw_score: Optional[int]         # Score before normalization
    score_breakdown: Optional[dict]  # JSON breakdown of scoring

    # Detection metadata
    detected_version: Optional[str]  # Extracted version if available
    detected_sha: Optional[str]      # Git commit SHA at detection
    detected_at: datetime            # When artifact was detected

    # Path-based tags (for frontmatter support)
    path_segments: Optional[str]     # JSON array of extracted path segments
    metadata_json: Optional[str]     # Additional detection metadata
```

### Status Values

The catalog entry `status` field has five states:

| Status    | Meaning                                    | import_date | import_id       |
|-----------|--------------------------------------------|-----------|--------------------|
| `new`     | Newly detected, never imported             | NULL      | NULL               |
| `updated` | Source updated but not re-imported         | NULL      | NULL               |
| `removed` | Deleted from source repository             | (varies)  | (if previously imported) |
| `imported`| Successfully imported to collection        | SET       | SET (artifact ID) |
| `excluded`| Marked as "not an artifact" by user        | NULL      | NULL               |

### Import Flag Pattern

The "imported flag" is the combination of:
- `status == "imported"` (boolean check)
- `import_id` (reference to which artifact it was imported as)
- `import_date` (timestamp of import)

**Key Pattern**: When marketplace artifact is imported, ALL THREE fields are populated atomically.

---

## 2. Artifact Deletion Flow

### API Endpoint

**File**: `skillmeat/api/routers/artifacts.py:2701-2780`

```python
@router.delete(
    "/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_artifact(
    artifact_id: str,                    # Format: "type:name"
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(...),
) -> None:
```

### Deletion Process

1. **Parse artifact ID** (format: `"skill:pdf-processor"`)
   - Split on `:` to extract type and name
   - Validate against ArtifactType enum

2. **Locate artifact** in collection(s)
   - If `collection` param provided: search only that collection
   - Otherwise: search all collections until found
   - Raises 404 if not found in any collection

3. **Remove artifact**
   - Calls `artifact_mgr.remove(name, type, collection_name)`
   - This handles:
     - Filesystem cleanup (removes artifact files)
     - Collection update (removes from manifest.toml)
     - Lock file update (updates lockfile to reflect removal)

4. **Response**: Returns 204 No Content (successful deletion)

### Error Handling

| Error Scenario | Status | Detail |
|---|---|---|
| Invalid ID format | 400 | "Invalid artifact ID format. Expected 'type:name'" |
| Collection not found | 404 | "Collection '{collection}' not found" |
| Artifact not found | 404 | "Artifact '{artifact_id}' not found" |
| Removal error | 500 | Error message from artifact_mgr |

---

## 3. Artifact Catalog Modal Structure

### Frontend Component

**File**: `skillmeat/web/components/CatalogEntryModal.tsx`

The modal displays detailed information about a marketplace catalog entry with import capability.

#### Props Interface

```typescript
interface CatalogEntryModalProps {
  entry: CatalogEntry | null;           // Catalog entry to display (or null if closed)
  open: boolean;                         // Modal visibility
  onOpenChange: (open: boolean) => void; // Handle open/close
  onImport?: (entry: CatalogEntry) => void;  // Optional import callback
  isImporting?: boolean;                 // Import in progress flag
  onEntryUpdated?: (entry: CatalogEntry) => void;  // Entry updated (name changed)
}
```

#### Tab Structure (3 Tabs)

**1. Overview Tab** (Default)
- Artifact name (editable with pencil icon)
- Type and status badges
- Confidence score with breakdown visualization
- Frontmatter metadata (from SKILL.md, README.md, or first .md file)
- Full score breakdown with heuristic components
- Metadata section:
  - Path (code block)
  - Upstream URL (clickable GitHub link)
  - Detected version (if available)
  - Git SHA (shortened to 7 chars)
  - Detection timestamp

**2. Contents Tab**
- Split pane layout:
  - **Left (280px fixed)**: FileTree component
    - Hierarchical file browser
    - Auto-selects first .md file or first file alphabetically
    - Error handling with retry button
  - **Right (flex)**: ContentPane component
    - Displays selected file content
    - Shows file truncation info if >limit
    - Provides link to view full file on GitHub
    - Error handling with retry and GitHub link

**3. Suggested Tags Tab**
- PathTagReview component
- Shows path-based tag extraction
- Users can approve/reject tags before import
- Tags applied during import if approved

#### Import State

The import button is disabled when:
- `entry.status === "imported"` (already imported)
- `entry.status === "removed"` (artifact no longer exists)
- `isImporting === true` (import in progress)

#### Name Editing

- Click pencil icon to edit name
- Validates non-empty trimmed name
- Shows error messages inline
- Cancels on Escape key
- Auto-focuses input for UX

#### Key Methods

```typescript
buildFileStructure(files: FileTreeEntry[]): FileNode[]
// Transforms flat API response to hierarchical tree

buildGitHubFileUrl(upstreamUrl, artifactPath, filePath, sha): string
// Constructs correct GitHub blob URL with correct repo/owner

formatDate(isoDate: string): string
// Formats ISO dates to: "Jan 23, 2026, 10:30 AM"

shortenSha(sha: string): string
// Git SHA shortened to first 7 chars
```

#### Frontmatter Extraction

Priority order for primary markdown file:
1. `SKILL.md` (exact case match)
2. `README.md` (exact case match)
3. First `.md` file alphabetically

Uses `parseFrontmatter()` to extract YAML frontmatter, displayed in `FrontmatterDisplay` component.

---

## 4. Marketplace Source Model

**File**: `skillmeat/cache/models.py:1182-1499`

The `MarketplaceSource` represents a GitHub repository scanned for artifacts.

### Key Fields

```python
class MarketplaceSource(Base):
    # Repository identification
    id: str                              # Unique source ID
    repo_url: str                        # Full GitHub URL (UNIQUE)
    owner: str                           # Repository owner/org
    repo_name: str                       # Repository name
    ref: str = "main"                    # Branch/tag/SHA to scan
    root_hint: Optional[str]             # Optional subdirectory

    # Sync tracking
    last_sync_at: Optional[datetime]     # Last successful scan
    last_error: Optional[str]            # Error message if failed
    scan_status: str                     # "pending" | "scanning" | "success" | "error"
    artifact_count: int                  # Cached count of discovered artifacts
    counts_by_type: Optional[str]        # JSON: {"skill": 5, "command": 3}

    # Configuration
    trust_level: str = "basic"           # "untrusted" | "basic" | "verified" | "official"
    visibility: str = "public"           # "private" | "internal" | "public"

    # Artifact detection settings
    enable_frontmatter_detection: bool = False  # Parse markdown frontmatter
    single_artifact_mode: bool = False         # Treat repo as single artifact
    single_artifact_type: Optional[str]        # Type when single_artifact_mode=True

    # Relationships
    entries: List[MarketplaceCatalogEntry]  # Discovered artifacts
```

### Sync Status Flow

```
pending → scanning → success (or error)
```

---

## 5. Re-Import & Refresh Functionality

### Rescan Endpoint

**File**: `skillmeat/api/routers/marketplace_sources.py:12-23` (endpoint list)

```
POST /marketplace/sources/{id}/rescan - Trigger rescan
```

Triggers GitHub scanner to re-scan source repository and update catalog entries.

### Status Transitions During Rescan

When a source is rescanned:
1. New artifacts detected → `status = "new"`
2. Previously imported artifact still present → `status = "imported"` (unchanged)
3. Previously imported artifact removed → `status = "removed"`
4. Previously "new" artifact still present → `status = "updated"`

### Exclusion Restoration

**File**: `skillmeat/api/routers/marketplace_sources.py:18` (endpoint list)

```
DELETE /marketplace/sources/{id}/artifacts/{entry_id}/exclude - Restore excluded artifact
```

Removes the `excluded_at` timestamp to restore entry to its previous status state.

---

## 6. File Tree API

### Endpoints

**Get file tree** (for Contents tab):
```
GET /marketplace/sources/{id}/artifacts/{path}/files
```

Returns flat list of files and directories:
```typescript
interface FileTreeResponse {
  entries: {
    path: string;           // Relative path within artifact
    type: "file" | "tree";  // File or directory
    size?: number;          // Size in bytes (files only)
  }[];
  cached: boolean;
  cache_age_seconds?: number;
}
```

**Get file content**:
```
GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path}
```

Returns decoded file content:
```typescript
interface FileContentResponse {
  content: string;         // Decoded file content
  encoding: string;        // UTF-8 after decoding
  size: number;           // File size
  sha: string;            // Git blob SHA
  truncated?: boolean;    // Content was truncated
  original_size?: number; // Size if truncated
  cached: boolean;
  cache_age_seconds?: number;
}
```

### Artifact Path Normalization

Important pattern: Repository root (".") is normalized to empty string in URLs
```typescript
// In fetchCatalogFileTree:
const normalizedPath = artifactPath === '.' ? '' : artifactPath;
const encodedPath = encodeURIComponent(normalizedPath);
const response = await fetch(
  buildUrl(`/marketplace/sources/${sourceId}/artifacts/${encodedPath}/files`)
);
```

---

## 7. API Client Layer

**File**: `skillmeat/web/lib/api/catalog.ts`

Provides type-safe API functions for frontend:

```typescript
// Fetch file tree for a catalog artifact
async function fetchCatalogFileTree(
  sourceId: string,
  artifactPath: string
): Promise<FileTreeResponse>

// Fetch content of specific file
async function fetchCatalogFileContent(
  sourceId: string,
  artifactPath: string,
  filePath: string
): Promise<FileContentResponse>
```

### Usage in Modal

The `CatalogEntryModal` uses hooks:
```typescript
const { data: fileTreeData, isLoading, error, refetch } =
  useCatalogFileTree(sourceId, artifactPath);

const { data: fileContentData, isLoading, error, refetch } =
  useCatalogFileContent(sourceId, artifactPath, selectedFilePath);
```

---

## 8. Path-Based Tags Feature

### Storage

Path segments stored as JSON in `MarketplaceCatalogEntry.path_segments`:
```json
[
  {
    "value": "canvas",
    "normalized": "canvas",
    "status": "approved",
    "source": "path"
  },
  {
    "value": "design",
    "normalized": "design",
    "status": "pending",
    "source": "path"
  }
]
```

### Update Endpoint

```
PATCH /marketplace/sources/{id}/catalog/{entry_id}/path-tags - Update path segment approval status
```

Allows users to approve/reject path-based tag suggestions before import.

---

## Key Patterns & Conventions

### 1. Import Tracking
- Use `status == "imported"` to check if imported (not just `import_id`)
- `import_date` and `import_id` are populated atomically when importing
- Always check both fields together

### 2. File Tree Rendering
- Flatten API response using `buildFileStructure()`
- Auto-select first .md file for better UX
- Sort: directories first, then alphabetically

### 3. Artifact Paths
- Always normalize "." (root) to "" before URL encoding
- Encode paths with `encodeURIComponent()`
- Use GitHub API to construct proper blob URLs

### 4. Error Handling
- Rate limit detection: check for "429", "rate limit", or "too many requests"
- Network errors: check message for "network" or "fetch"
- 404 errors: check message for "not found"

### 5. Modal State Management
- Reset file selection when modal closes
- Auto-select default tab on open (Overview)
- Clear editing state when modal closes
- Track name edit state separately from modal state

---

## Files to Reference

### Backend Models
- `/skillmeat/cache/models.py` - MarketplaceSource, MarketplaceCatalogEntry models
- `/skillmeat/api/routers/marketplace_sources.py` - Source management endpoints
- `/skillmeat/api/routers/artifacts.py:2701+` - Delete artifact endpoint

### Frontend Components
- `/skillmeat/web/components/CatalogEntryModal.tsx` - Main catalog modal
- `/skillmeat/web/app/marketplace/sources/[id]/components/catalog-list.tsx` - Catalog list view
- `/skillmeat/web/lib/api/catalog.ts` - File tree/content API client

### Hooks
- `/skillmeat/web/hooks/use-catalog-files.ts` - Catalog file fetching hooks
- `/skillmeat/web/hooks/use-*.ts` - Other relevant hooks

---

## Implementation Readiness

All patterns are:
- Actively used in production code
- Well-documented in models and components
- Type-safe with TypeScript
- Tested with E2E tests in `tests/e2e/catalog-*.spec.ts`

Ready to implement marketplace import/deletion enhancements.
