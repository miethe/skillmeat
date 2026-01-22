# Quick Feature: Source Auto-Tags from GitHub Topics

**Status**: completed
**Started**: 2026-01-22
**Scope**: Backend API + Frontend UI

## Problem Statement

Currently, when importing artifacts from a Marketplace GitHub source:
1. Source tags (from GitHub repo topics) are being auto-propagated to imported artifacts
2. No UI exists to approve/deny GitHub repo topics as source-level tags
3. Users want source tags and artifact tags to be decoupled

## Requirements

1. **GitHub Topic Extraction**: Marketplace sources should pull topics from linked GitHub repos
2. **Source-Level Tag Approval**: UI dialog to approve/deny extracted topics as source tags
3. **No Auto-Propagation**: Source tags should NOT auto-add to imported artifacts
4. **UI Integration**: "Auto-Tags Available" button when unapproved auto-tags exist

## Implementation Plan

### Backend Changes (Python/FastAPI)

#### 1. Database Model Update
**File**: `skillmeat/cache/models.py`

Add new field to `MarketplaceSource`:
```python
auto_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
# JSON: {"extracted": [{"value": "topic", "normalized": "topic", "status": "pending|approved|rejected"}]}
```

#### 2. GitHub Topics Extraction
**Files**:
- `skillmeat/core/marketplace/scanner.py` - Extract topics during scan
- `skillmeat/core/github_metadata.py` - Already has `_fetch_repo_metadata()` returning topics

During source creation/scan, populate `auto_tags` with GitHub repo topics.

#### 3. API Endpoints
**File**: `skillmeat/api/routers/marketplace_sources.py`

Add endpoints:
- `GET /{source_id}/auto-tags` - Get auto-tag suggestions with approval status
- `PATCH /{source_id}/auto-tags` - Update approval status of an auto-tag

**Schema** (`skillmeat/api/schemas/marketplace.py`):
```python
class AutoTagSegment(BaseModel):
    value: str
    normalized: str
    status: Literal["pending", "approved", "rejected"]
    source: str = "github_topic"  # origin of the tag

class AutoTagsResponse(BaseModel):
    source_id: str
    segments: List[AutoTagSegment]
    has_pending: bool

class UpdateAutoTagRequest(BaseModel):
    value: str  # The tag value to update
    status: Literal["approved", "rejected"]
```

#### 4. Import Flow Fix
**File**: `skillmeat/api/routers/marketplace_sources.py`

At line ~2468, the import flow extracts approved tags from `path_segments` and passes them to artifacts. This is correct behavior - path-based tags ARE for artifact tagging.

The issue is elsewhere - need to verify source tags aren't being added during import.

### Frontend Changes (Next.js/React)

#### 1. Types
**File**: `skillmeat/web/types/marketplace.ts`

```typescript
export interface AutoTagSegment {
  value: string;
  normalized: string;
  status: 'pending' | 'approved' | 'rejected';
  source: string;
}

export interface AutoTagsResponse {
  source_id: string;
  segments: AutoTagSegment[];
  has_pending: boolean;
}
```

#### 2. API Hooks
**File**: `skillmeat/web/hooks/use-auto-tags.ts`

```typescript
export function useSourceAutoTags(sourceId: string)
export function useUpdateAutoTag(sourceId: string)
```

#### 3. AutoTagsDialog Component
**File**: `skillmeat/web/components/marketplace/auto-tags-dialog.tsx`

Similar to `BulkTagDialogWithHook` - shows list of extracted topics with approve/reject buttons.

#### 4. Source Detail Page Integration
**File**: `skillmeat/web/app/marketplace/sources/[id]/page.tsx`

Add "Auto-Tags Available" button near the Tags section header when `source.auto_tags` has pending items.

## Files to Modify

### Backend
1. `skillmeat/cache/models.py` - Add `auto_tags` field
2. `skillmeat/api/schemas/marketplace.py` - Add response/request schemas
3. `skillmeat/api/routers/marketplace_sources.py` - Add endpoints
4. `skillmeat/core/marketplace/scanner.py` - Populate auto_tags during scan
5. Alembic migration for new column

### Frontend
1. `skillmeat/web/types/marketplace.ts` - Add types
2. `skillmeat/web/hooks/use-auto-tags.ts` - New file
3. `skillmeat/web/components/marketplace/auto-tags-dialog.tsx` - New file
4. `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Add button
5. `skillmeat/web/lib/api/marketplace.ts` - Add API functions

## Quality Gates

- [ ] `pnpm test` passes
- [ ] `pnpm typecheck` passes
- [ ] `pnpm lint` passes
- [ ] `pnpm build` succeeds
- [ ] Manual testing of auto-tag workflow

## Out of Scope

- Searching artifacts by source tags (future feature)
- Multi-source tag deduplication
- Tag inheritance rules
