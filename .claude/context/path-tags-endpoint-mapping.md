---
title: Path Tags Endpoint Mapping
description: Complete reference for path-tags API endpoints - GET and PATCH operations
status: complete
last_verified: 2026-01-05
references:
  - skillmeat/api/routers/marketplace_sources.py
  - skillmeat/api/schemas/marketplace.py
  - skillmeat/web/hooks/use-path-tags.ts
  - skillmeat/web/lib/api/marketplace.ts
  - skillmeat/api/server.py
---

# Path Tags Endpoint Mapping

Complete reference for path-based tag extraction and approval API endpoints.

## Quick Reference

| Operation | Method | Endpoint | Status | Files |
|-----------|--------|----------|--------|-------|
| **Get path tags** | GET | `/api/v1/marketplace-sources/{source_id}/catalog/{entry_id}/path-tags` | ✅ Implemented | Router: `marketplace_sources.py:1670-1815` |
| **Update tag status** | PATCH | `/api/v1/marketplace-sources/{source_id}/catalog/{entry_id}/path-tags` | ✅ Implemented | Router: `marketplace_sources.py:1817-2009` |

---

## GET Path Tags

**Endpoint**: `GET /api/v1/marketplace-sources/{source_id}/catalog/{entry_id}/path-tags`

### Handler Location

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/marketplace_sources.py`

Lines: 1670-1815

Function: `async def get_path_tags(source_id: str, entry_id: str) -> PathSegmentsResponse`

### Path Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `source_id` | string | Marketplace source identifier | `src-123` |
| `entry_id` | string | Catalog entry identifier | `cat-456` |

### Response Schema

**Type**: `PathSegmentsResponse`

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py:1825-1871`

```python
class PathSegmentsResponse(BaseModel):
    entry_id: str
    raw_path: str
    extracted: list[ExtractedSegmentResponse]
    extracted_at: datetime

class ExtractedSegmentResponse(BaseModel):
    segment: str                                              # Original segment
    normalized: str                                          # Normalized value
    status: Literal["pending", "approved", "rejected", "excluded"]
    reason: Optional[str]                                   # Reason if excluded
```

### Response Example

```json
{
  "entry_id": "cat-456",
  "raw_path": "skills/ui-ux/canvas-design",
  "extracted": [
    {
      "segment": "ui-ux",
      "normalized": "ui-ux",
      "status": "pending",
      "reason": null
    },
    {
      "segment": "canvas-design",
      "normalized": "canvas-design",
      "status": "pending",
      "reason": null
    }
  ],
  "extracted_at": "2025-12-07T14:30:00Z"
}
```

### Error Responses

| Status | Condition | Detail |
|--------|-----------|--------|
| 404 | Source not found | `Source with ID '{source_id}' not found` |
| 404 | Catalog entry not found | `Catalog entry '{entry_id}' not found in source '{source_id}'` |
| 400 | No path segments extracted | `Entry '{entry_id}' has no path_segments (not extracted yet)` |
| 500 | Malformed JSON | `Internal error parsing path_segments` |

### Implementation Notes

- **Database**: Queries `MarketplaceCatalogEntry.path_segments` (JSON field)
- **Parsing**: Deserializes JSON to extract raw_path and segments array
- **Session**: Uses `catalog_repo._get_session()` for database access
- **Error Handling**:
  - Logs warnings for not-found conditions
  - Logs errors for JSON parsing failures
  - Rolls back on exception (if called within transaction context)

---

## PATCH Update Path Tag Status

**Endpoint**: `PATCH /api/v1/marketplace-sources/{source_id}/catalog/{entry_id}/path-tags`

### Handler Location

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/marketplace_sources.py`

Lines: 1817-2009

Function: `async def update_path_tag_status(source_id: str, entry_id: str, request: UpdateSegmentStatusRequest) -> UpdateSegmentStatusResponse`

### Path Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `source_id` | string | Marketplace source identifier | `src-123` |
| `entry_id` | string | Catalog entry identifier | `cat-456` |

### Request Schema

**Type**: `UpdateSegmentStatusRequest`

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py:1874-1898`

```python
class UpdateSegmentStatusRequest(BaseModel):
    segment: str                                    # Original segment value
    status: Literal["approved", "rejected"]         # New status
```

### Request Example

```json
{
  "segment": "ui-ux",
  "status": "approved"
}
```

### Response Schema

**Type**: `UpdateSegmentStatusResponse`

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py:1901-1946`

```python
class UpdateSegmentStatusResponse(BaseModel):
    entry_id: str
    raw_path: str
    extracted: list[ExtractedSegmentResponse]      # Updated segments
    updated_at: datetime
```

### Response Example

```json
{
  "entry_id": "cat-456",
  "raw_path": "skills/ui-ux/canvas-design",
  "extracted": [
    {
      "segment": "ui-ux",
      "normalized": "ui-ux",
      "status": "approved",
      "reason": null
    },
    {
      "segment": "canvas-design",
      "normalized": "canvas-design",
      "status": "pending",
      "reason": null
    }
  ],
  "updated_at": "2025-12-07T15:00:00Z"
}
```

### Error Responses

| Status | Condition | Detail |
|--------|-----------|--------|
| 404 | Source not found | `Source with ID '{source_id}' not found` |
| 404 | Catalog entry not found | `Catalog entry '{entry_id}' not found in source '{source_id}'` |
| 404 | Segment not found | `Segment '{segment}' not found in entry '{entry_id}'` |
| 400 | No path segments extracted | `Entry '{entry_id}' has no path_segments (not extracted yet)` |
| 409 | Excluded segment | `Cannot change status of excluded segment '{segment}'` |
| 409 | Already approved/rejected | `Segment '{segment}' already has status '{current_status}'` |
| 500 | Malformed JSON | `Internal error: malformed path_segments JSON` |

### Status Values

| Status | Meaning | Can Change? | Purpose |
|--------|---------|-------------|---------|
| `pending` | Awaiting approval | ✅ Yes | Initial state, can approve/reject |
| `approved` | Will be applied as tag | ❌ No | Final state, used during import |
| `rejected` | Will not be applied | ❌ No | Final state, skipped during import |
| `excluded` | Filtered by rules | ❌ No | System state, cannot change |

### Implementation Notes

- **Database**: Updates `MarketplaceCatalogEntry.path_segments` (JSON field)
- **Atomic**: Uses session commit/rollback for atomic updates
- **Validation**:
  - Rejects changes to "excluded" segments (409 Conflict)
  - Prevents double-approval (409 Conflict)
  - Requires exact segment match
- **Session**: Uses `catalog_repo._get_session()` for database access with cleanup
- **Error Handling**:
  - Logs info for successful updates
  - Logs warnings for validation failures
  - Rolls back transaction on any error

---

## Frontend Integration

### API Client Functions

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/marketplace.ts`

#### Get Path Tags

```typescript
export async function getPathTags(
  sourceId: string,
  entryId: string
): Promise<PathSegmentsResponse> {
  const response = await fetch(
    buildUrl(`/marketplace-sources/${sourceId}/catalog/${entryId}/path-tags`)
  );
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to get path tags: ${response.statusText}`);
  }
  return response.json();
}
```

#### Update Path Tag Status

```typescript
export async function updatePathTagStatus(
  sourceId: string,
  entryId: string,
  segment: string,
  status: 'approved' | 'rejected'
): Promise<PathSegmentsResponse> {
  const response = await fetch(
    buildUrl(`/marketplace-sources/${sourceId}/catalog/${entryId}/path-tags`),
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ segment, status }),
    }
  );
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to update path tag status: ${response.statusText}`);
  }
  return response.json();
}
```

### Custom Hooks

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-path-tags.ts`

#### usePathTags

```typescript
export function usePathTags(sourceId: string, entryId: string) {
  return useQuery({
    queryKey: pathTagKeys.detail(sourceId, entryId),
    queryFn: async (): Promise<PathSegmentsResponse> => {
      return getPathTags(sourceId, entryId);
    },
    enabled: !!sourceId && !!entryId,
    staleTime: 5 * 60 * 1000,
  });
}
```

#### useUpdatePathTagStatus

```typescript
export function useUpdatePathTagStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sourceId,
      entryId,
      segment,
      status,
    }: {
      sourceId: string;
      entryId: string;
      segment: string;
      status: 'approved' | 'rejected';
    }): Promise<PathSegmentsResponse> => {
      return updatePathTagStatus(sourceId, entryId, segment, status);
    },
    onSuccess: (_, { sourceId, entryId }) => {
      queryClient.invalidateQueries({
        queryKey: pathTagKeys.detail(sourceId, entryId),
      });
    },
  });
}
```

### Frontend Types

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/path-tags.ts`

```typescript
export interface ExtractedSegment {
  segment: string;
  normalized: string;
  status: 'pending' | 'approved' | 'rejected' | 'excluded';
  reason?: string;
}

export interface PathSegmentsResponse {
  entry_id: string;
  raw_path: string;
  extracted: ExtractedSegment[];
  extracted_at: string;
}
```

---

## Server Registration

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/server.py:257`

```python
app.include_router(
    marketplace_sources.router,
    prefix=settings.api_prefix,  # "/api/v1"
    tags=["marketplace-sources"]
)
```

The marketplace_sources router is registered with:
- Prefix: `/api/v1` (from `settings.api_prefix`)
- Tag: `marketplace-sources` (for OpenAPI documentation)
- Full path: `/api/v1/marketplace-sources/{source_id}/catalog/{entry_id}/path-tags`

---

## Data Flow

### Getting Path Tags

```
Frontend (React)
  ↓
  usePathTags(sourceId, entryId)
  ↓
  TanStack Query
  ↓
  getPathTags(sourceId, entryId)
  ↓
  fetch("/api/v1/marketplace-sources/{sourceId}/catalog/{entryId}/path-tags")
  ↓
Backend (FastAPI)
  ↓
  get_path_tags(source_id, entry_id)
  ↓
  MarketplaceSourceRepository.get_by_id(source_id)
  ↓
  MarketplaceCatalogRepository.query(entry_id)
  ↓
  Parse entry.path_segments JSON
  ↓
  Return PathSegmentsResponse
  ↓
Response
```

### Updating Path Tag Status

```
Frontend (React)
  ↓
  useUpdatePathTagStatus().mutateAsync({...})
  ↓
  updatePathTagStatus(sourceId, entryId, segment, status)
  ↓
  fetch("PATCH /api/v1/marketplace-sources/{sourceId}/catalog/{entryId}/path-tags")
  ↓
Backend (FastAPI)
  ↓
  update_path_tag_status(source_id, entry_id, request)
  ↓
  Load entry.path_segments JSON
  ↓
  Find segment in extracted array
  ↓
  Validate: not "excluded", not already approved/rejected
  ↓
  Update segment.status
  ↓
  Save entry.path_segments back to DB
  ↓
  commit()
  ↓
  Return UpdateSegmentStatusResponse
  ↓
Response
```

---

## Testing References

### Backend Integration Tests

File: `/Users/miethe/dev/homelab/development/skillmeat/tests/api/routers/test_marketplace_path_tags.py`

Tests for GET and PATCH endpoints

### Backend Unit Tests

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/tests/test_path_tag_import_integration.py`

Path tag import integration tests

### Frontend E2E Tests

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/e2e/path-tags-import.spec.ts`

E2E tests for path tags import checkbox and approval workflow

File: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/e2e/path-tag-review.spec.ts`

E2E tests for path tag review component

---

## Related Files

### Core Business Logic

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/path_tags.py` - PathSegmentExtractor, PathTagConfig
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/importer.py` - BulkImportArtifactData with apply_path_tags

### Database Models

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py` - MarketplaceCatalogEntry model
- Migration: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/migrations/versions/20260104_1000_add_path_based_tag_extraction.py`

### Frontend Components

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/marketplace/path-tag-review.tsx` - Path tag review UI
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/discovery/BulkImportModal.tsx` - Bulk import with path tags

### Documentation

- `/Users/miethe/dev/homelab/development/skillmeat/docs/dev/api/marketplace-sources.md` - API documentation
- `/Users/miethe/dev/homelab/development/skillmeat/docs/dev/architecture/path-based-tags.md` - Architecture overview

---

## Key Insights

1. **Endpoint Registration**: Both GET and PATCH are registered under the marketplace-sources router with correct prefixes

2. **Database Persistence**: Path segments stored as JSON in `MarketplaceCatalogEntry.path_segments` field

3. **Status Management**:
   - Only "pending" segments can transition to "approved" or "rejected"
   - "excluded" segments are immutable (system-determined by extraction rules)
   - Cannot change status of already approved/rejected segments

4. **Frontend Integration**:
   - Fully integrated with TanStack Query for caching and invalidation
   - API client functions follow standard error handling patterns
   - Custom hooks provide clean interface for React components

5. **Atomic Operations**: PATCH endpoint uses database transaction with commit/rollback

6. **Error Handling**: Comprehensive error responses with appropriate HTTP status codes

---

## Common Issues & Solutions

### Issue: "Entry has no path_segments"

**Cause**: Entry was scanned before path extraction was enabled or extraction failed

**Solution**: Re-scan the marketplace source with path extraction enabled

**Endpoint Response**: 400 Bad Request

### Issue: "Cannot change status of excluded segment"

**Cause**: Attempting to approve/reject a segment that was filtered by extraction rules

**Solution**: Only approve/reject "pending" segments; excluded ones are system-determined

**Endpoint Response**: 409 Conflict

### Issue: "Segment already has status"

**Cause**: Attempting to approve a segment that was already approved (or reject a rejected one)

**Solution**: Check current status in response before updating

**Endpoint Response**: 409 Conflict

---

## Quick Implementation Reference

### Using Path Tags in Frontend

```typescript
// Get path tags for an entry
const { data: pathTags, isLoading } = usePathTags(sourceId, entryId);

// Approve a segment
const updateStatus = useUpdatePathTagStatus();
await updateStatus.mutateAsync({
  sourceId,
  entryId,
  segment: 'ui-ux',
  status: 'approved',
});

// Handle errors
if (updateStatus.error instanceof Error) {
  console.error(`Failed: ${updateStatus.error.message}`);
}
```

### Using Path Tags in Backend

```python
# Get extracted segments
from skillmeat.cache.repositories import MarketplaceCatalogRepository

repo = MarketplaceCatalogRepository()
entry = repo.get_by_id(entry_id)
if entry.path_segments:
    data = json.loads(entry.path_segments)
    for segment in data['extracted']:
        print(f"{segment['segment']} ({segment['status']})")
```

