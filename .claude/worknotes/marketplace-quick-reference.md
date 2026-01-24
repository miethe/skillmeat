# Marketplace Import/Deletion - Quick Reference

## Import Tracking Flag

**Location**: `MarketplaceCatalogEntry` model fields

```python
# Check if imported:
if entry.status == "imported" and entry.import_id is not None:
    print(f"Imported as: {entry.import_id} on {entry.import_date}")

# Valid states:
# - "new": Never imported
# - "updated": Source changed, not re-imported
# - "removed": Removed from source
# - "imported": Successfully imported
# - "excluded": Marked as "not an artifact"
```

**Key Point**: Use `status == "imported"` as the primary flag, with `import_id` and `import_date` for audit trail.

---

## Artifact Deletion Flow

### API Endpoint
```
DELETE /api/v1/artifacts/{artifact_id}?collection={name}
Status: 204 No Content
```

### Process
1. Parse ID: `"type:name"` format
2. Find artifact in collection (or search all if not specified)
3. Call `artifact_mgr.remove(name, type, collection_name)`
   - Cleans up filesystem
   - Updates manifest.toml
   - Updates lockfile

### Errors
- **400**: Invalid ID format
- **404**: Artifact or collection not found

---

## Catalog Modal Component

### Tabs
1. **Overview**: Metadata, frontmatter, confidence breakdown
2. **Contents**: File tree + content viewer (split pane)
3. **Suggested Tags**: Path-based tags for approval

### Key Props
```typescript
entry: CatalogEntry | null
open: boolean
onOpenChange: (open: boolean) => void
onImport?: (entry: CatalogEntry) => void
isImporting?: boolean
onEntryUpdated?: (entry: CatalogEntry) => void
```

### Import Button States
- Disabled if `status === "imported"` or `status === "removed"`
- Shows loading spinner when `isImporting === true`
- Only enabled for "new" and "updated" entries

---

## File Tree API

### Endpoints
```
GET /marketplace/sources/{id}/artifacts/{path}/files
GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path}
```

### Important: Path Normalization
```typescript
// Root "." must become "" in URL
const normalizedPath = artifactPath === '.' ? '' : artifactPath;
const encodedPath = encodeURIComponent(normalizedPath);
```

### Response Types
```typescript
// File tree
{ entries: [{path: string, type: "file"|"tree", size?: number}] }

// File content
{ content: string, encoding: string, size: number, sha: string, truncated?: boolean }
```

---

## Re-Import & Refresh

### Rescan Source
```
POST /marketplace/sources/{id}/rescan
```

Status transitions:
- New detected → `status = "new"`
- Already imported & still present → `status = "imported"` (unchanged)
- Was imported, now removed → `status = "removed"`
- Was new, still present → `status = "updated"`

### Restore Excluded Entry
```
DELETE /marketplace/sources/{id}/artifacts/{entry_id}/exclude
```

Removes `excluded_at` timestamp to un-exclude.

---

## Frontend Hooks

### Catalog File Hooks
```typescript
useCatalogFileTree(sourceId, artifactPath)
useCatalogFileContent(sourceId, artifactPath, filePath)
useUpdateCatalogEntryName(sourceId)
useExcludeCatalogEntry(sourceId)
```

All available from `@/hooks` barrel import.

---

## Status Badge Configuration

```typescript
const statusConfig: Record<CatalogStatus, { label: string; className: string }> = {
  new: { label: 'New', className: 'border-green-500...' },
  updated: { label: 'Updated', className: 'border-blue-500...' },
  imported: { label: 'Imported', className: 'border-gray-500...' },
  removed: { label: 'Removed', className: 'border-red-500... line-through' },
  excluded: { label: 'Excluded', className: 'border-gray-400...' },
};
```

---

## Frontmatter Extraction Order

In CatalogEntryModal, primary markdown file is selected as:
1. `SKILL.md` (exact case)
2. `README.md` (exact case)
3. First `.md` file alphabetically

Frontmatter parsed and displayed in `FrontmatterDisplay` component.

---

## Error Handling Patterns

```typescript
// Rate limit detection
const isRateLimitError = (error: Error) => {
  const msg = error.message?.toLowerCase() ?? '';
  return msg.includes('rate limit') || msg.includes('429');
};

// GitHub URL construction
function buildGitHubFileUrl(
  upstreamUrl: string,  // https://github.com/owner/repo/tree/main/path
  artifactPath: string, // path/to/artifact
  filePath: string,     // file.md
  sha?: string          // optional git sha
): string
```

---

## Key Files

### Models & Schemas
- `skillmeat/cache/models.py` - ORM models
- `skillmeat/api/schemas/marketplace.py` - Request/response DTOs

### Endpoints
- `skillmeat/api/routers/artifacts.py:2701+` - Delete
- `skillmeat/api/routers/marketplace_sources.py` - Marketplace management

### Components
- `skillmeat/web/components/CatalogEntryModal.tsx` - Main modal (890 lines)
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-list.tsx` - List view
- `skillmeat/web/components/marketplace/path-tag-review.tsx` - Tag approval

### API & Hooks
- `skillmeat/web/lib/api/catalog.ts` - File tree/content API
- `skillmeat/web/hooks/use-catalog-files.ts` - File hooks
- `skillmeat/web/hooks/` - Other marketplace hooks
