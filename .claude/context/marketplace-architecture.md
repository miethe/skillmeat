# Marketplace Architecture Overview

## Layer Stack

```
┌─────────────────────────────────────────────────────────┐
│ Frontend (Next.js React)                                 │
│ ├─ CatalogEntryModal component                           │
│ ├─ CatalogList component                                 │
│ └─ File tree/content hooks                              │
└─────────────┬───────────────────────────────────────────┘
              │ API calls (fetch)
              ↓
┌─────────────────────────────────────────────────────────┐
│ API Layer (FastAPI)                                      │
│ ├─ /marketplace/sources/* endpoints                      │
│ ├─ /artifacts/{id} delete endpoint                       │
│ └─ Error handling & validation                          │
└─────────────┬───────────────────────────────────────────┘
              │ ORM queries
              ↓
┌─────────────────────────────────────────────────────────┐
│ Database Layer (SQLite)                                  │
│ ├─ MarketplaceSource table                              │
│ ├─ MarketplaceCatalogEntry table                        │
│ ├─ Artifact table                                        │
│ └─ Collection associations                              │
└─────────────────────────────────────────────────────────┘
```

---

## Data Models

### Relationship Diagram

```
MarketplaceSource (1)
    ↓ 1:N (entries relationship)
MarketplaceCatalogEntry (N)
    ├─ status: "new"|"updated"|"removed"|"imported"|"excluded"
    ├─ import_id: References artifact ID (if imported)
    └─ import_date: When imported (if status="imported")

Artifact
    ├─ id (composite from type:name)
    ├─ collections (M:N via CollectionArtifact)
    └─ artifact_metadata (1:1)
```

### Status State Machine

```
                    ┌─────────────────────────┐
                    │       "excluded"        │
                    │  (marked as not artifact)│
                    └─────────────────────────┘
                              ↑ ↓
                        (exclude/restore)

"new" ────────┐                                  ┌───── "imported"
              ↓ (import)                         ↑ (import)
         (artifact enters system)           (imported into collection)
              │                             import_id + import_date set
              └─────────────────────────────┘

"updated" ────────┐
                  ↓ (rescan finds update, not re-imported)
           (source changed, user hasn't re-imported)

"removed" ────────┐
                  ↓ (rescan finds deletion)
           (artifact gone from source)
           import_id/date preserved if previously imported
```

---

## Import Tracking Pattern

### Why Three Fields?

```python
# Check if imported:
if entry.status == "imported" and entry.import_id:
    # It's definitely imported
    artifact = collection_mgr.get_artifact(entry.import_id)

# Import history preserved even after removal:
if entry.status == "removed" and entry.import_id:
    # We know it WAS imported as this artifact
    # User might want to re-import or check history
```

### Atomicity

All three fields are updated together in a transaction:
```python
entry.status = "imported"
entry.import_date = datetime.utcnow()
entry.import_id = imported_artifact_id
# All committed atomically
```

---

## Deletion Flow Diagram

```
DELETE /api/v1/artifacts/{type:name}
         │
         ↓
Parse artifact_id ("skill:pdf-processor")
         │
         ↓
Find artifact in collection(s)
  - If collection param: search that collection
  - Else: search all collections
         │
         ↓ (found)
Call artifact_mgr.remove(name, type, collection)
  ├─ Delete artifact files from filesystem
  ├─ Update manifest.toml (remove from collection)
  ├─ Update lock file
  └─ Update any indexes/caches
         │
         ↓
Return 204 No Content
```

---

## Catalog Modal Data Flow

### Initial Load

```
Modal opens
├─ Fetch file tree: GET /marketplace/sources/{id}/artifacts/{path}/files
│  └─ Response: flat list of {path, type, size}
│     └─ Frontend transforms to hierarchical FileNode structure
│
├─ Auto-select first .md file (or first file)
│
└─ Fetch frontmatter: GET /marketplace/sources/{id}/artifacts/{path}/files/{primary.md}
   └─ Parse YAML frontmatter (if present)
```

### User Action: Import

```
Click Import button
├─ Check entry.status != "imported" & entry.status != "removed"
├─ Call onImport(entry) callback
├─ Parent component calls import API
│  └─ POST /marketplace/sources/{id}/import with entry.id
│
├─ Backend updates catalog entry:
│  ├─ status = "imported"
│  ├─ import_date = now
│  ├─ import_id = new artifact ID
│  └─ Copies artifact to collection
│
└─ Frontend: button disabled, entry shows "Imported" badge
```

### User Action: Edit Name

```
Click pencil icon
├─ Enter edit mode with text input
├─ User types new name
├─ Click Save
│  └─ PATCH /marketplace/sources/{id}/artifacts/{entry_id}
│     └─ Updates entry.name in database
│
├─ onEntryUpdated(updatedEntry) callback
└─ Modal updates to reflect new name
```

---

## File Tree Rendering Algorithm

### Problem
API returns flat structure:
```json
{
  "entries": [
    {"path": "src/index.ts", "type": "file"},
    {"path": "src/utils/helper.ts", "type": "file"},
    {"path": "README.md", "type": "file"}
  ]
}
```

### Solution
`buildFileStructure()` creates hierarchy:

```
Step 1: Parse all paths, create nodes
- src/index.ts → create "src" (dir) and "index.ts" (file)
- src/utils/helper.ts → create "src", "utils" (dir), "helper.ts"
- README.md → create "README.md" (file)

Step 2: Build parent-child relationships
- "src" contains ["index.ts", "utils"]
- "utils" contains ["helper.ts"]
- root contains ["src", "README.md"]

Step 3: Return root nodes only
[
  {name: "src", type: "directory", children: [...]},
  {name: "README.md", type: "file"}
]
```

---

## Re-Import & Refresh Scenarios

### Scenario 1: New artifacts in source

```
Source: meatyprompts/skills
  Before rescan: skill1, skill2
  After rescan:  skill1, skill2, skill3

Database:
  skill1: status="imported" (unchanged)
  skill2: status="imported" (unchanged)
  skill3: status="new" (new entry inserted)
```

### Scenario 2: Artifact removed from source

```
Source: meatyprompts/skills
  Before: skill1, skill2
  After:  skill1

Database:
  skill1: status="imported" (unchanged)
  skill2: status="removed" (import_id preserved!)
```

### Scenario 3: Artifact updated in source

```
Source: meatyprompts/skills
  Before: skill1 v1.0
  After:  skill1 v1.1

If not re-imported:
  skill1: status="updated"

If user imports again:
  skill1: status="imported"
         import_date=now
         (new artifact version replaces old)
```

---

## Error Scenarios & Handling

### Rate Limiting
```
API returns 429 or message contains "rate limit"
→ Modal shows: "GitHub rate limit reached"
→ Retry button available
→ Fallback: Link to view on GitHub directly
```

### Network Error
```
Fetch fails (connection error)
→ Modal shows: "Failed to load file tree"
→ Retry button available
→ Fallback: Link to view on GitHub directly
```

### File Not Found (404)
```
File deleted between requests
→ Modal shows: "File not found"
→ Provides context about what's happening
→ Fallback: Other files still available or GitHub link
```

---

## Performance Considerations

### Caching

File tree and content are cached at two levels:

1. **Browser caching**: TanStack Query default stale time = 5 minutes
2. **Backend caching**: GitHub API responses cached (TTL in code: 300 seconds default)

Cache headers returned: `cached: true`, `cache_age_seconds: 123`

### Why Two Cache Levels?

1. Reduce API calls to GitHub (strict rate limits)
2. Reduce round-trips for modal interactions
3. Manual refresh available via "Try again" button

### File Size Limits

Large files are truncated with indicator:
```
If file > limit:
  truncated: true
  original_size: 50000 (bytes)

Modal shows:
  "File truncated (50 KB of 50 KB shown)"
  "View full file on GitHub"
```

---

## API Contract

### Request/Response Examples

**Get catalog entries**
```
GET /api/v1/marketplace/sources/{id}/artifacts?status=new,updated&page=1&page_size=50

Response 200:
{
  "entries": [CatalogEntry, ...],
  "total": 42,
  "page": 1,
  "page_size": 50
}
```

**Import artifact**
```
POST /api/v1/marketplace/sources/{id}/import
Body: { "entry_ids": ["cat-123", "cat-456"] }

Response 200:
{
  "results": [
    {
      "entry_id": "cat-123",
      "success": true,
      "artifact_id": "skill:pdf-processor",
      "import_date": "2026-01-23T..."
    },
    ...
  ]
}
```

**Delete artifact**
```
DELETE /api/v1/artifacts/skill:pdf-processor?collection=default

Response 204 No Content
```

---

## Type Safety

### TypeScript Types

```typescript
interface CatalogEntry {
  id: string;
  source_id: string;
  artifact_type: ArtifactType;
  name: string;
  path: string;
  upstream_url: string;
  status: CatalogStatus;  // "new" | "updated" | "removed" | "imported" | "excluded"
  import_date?: string;
  import_id?: string;
  confidence_score: number;
  score_breakdown?: Record<string, unknown>;
  detected_version?: string;
  detected_sha?: string;
  detected_at: string;
}

type ArtifactType = "skill" | "command" | "agent" | "mcp_server" | "hook";
type CatalogStatus = "new" | "updated" | "removed" | "imported" | "excluded";
```

All types generated from OpenAPI schema via `pnpm generate-sdk`.

---

## Testing Strategy

### Unit Tests
- Modal prop behavior
- File structure building
- Date formatting
- Error message selection

### E2E Tests
- Full import flow
- File tree navigation
- Tab switching
- Name editing
- Pagination

### Coverage
- `skillmeat/web/__tests__/app/marketplace/components/catalog-tabs.test.tsx`
- `skillmeat/web/tests/e2e/catalog-*.spec.ts`

---

## Migration Notes

If modifying import tracking:

1. **Always update all three fields together** (status, import_date, import_id)
2. **Preserve import_id when status changes** (e.g., new→imported or imported→removed)
3. **Index on (source_id, status)** for filtering performance
4. **Unique on (source_id, upstream_url)** for deduplication
5. **Cascade delete** MarketplaceCatalogEntry when MarketplaceSource deleted

---

## Key Conventions

1. **Status is authoritative**: Always check `status` field first
2. **Import ID is context**: Use `import_id` only after confirming `status == "imported"`
3. **Three-field atomicity**: Update all three fields or none
4. **Preserve deletion history**: Keep import_id even after removal
5. **Frontend reflects backend**: Don't maintain separate import state on frontend
