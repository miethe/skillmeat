---
title: Marketplace Re-import Fix
status: completed
created: 2025-01-23
completed: 2025-01-23
feature_type: bug_fix_with_enhancement
complexity: medium
files_affected: 5
schema_version: 2
doc_type: quick_feature
feature_slug: marketplace-reimport-fix
---

# Marketplace Re-import Fix

## Problem Statement

When a user deletes an artifact from their collection that was imported from a Marketplace Source:
1. The catalog entry's `status` field is NOT reset from "imported" back to "new"
2. The `import_id` and `import_date` fields are NOT cleared
3. This makes it impossible to re-import the artifact since it still shows as "imported"

Additionally, there's no "force re-import" option for marketplace artifacts that:
- Allows updating an existing imported artifact
- Maintains deployments optionally
- Works even if the imported artifact is broken/missing

## Solution

### Part 1: Fix Artifact Deletion Flow (Bug Fix)

**Backend** (`skillmeat/api/routers/artifacts.py`):
- In `delete_artifact()` endpoint, after successful deletion:
- Check if artifact has an associated marketplace catalog entry (via `import_id` in metadata)
- If found, reset the catalog entry: `status="new"`, clear `import_id`, clear `import_date`

**New API Endpoint** (`skillmeat/api/routers/marketplace_sources.py`):
- Add `POST /sources/{source_id}/entries/{entry_id}/reimport` endpoint
- Parameters:
  - `keep_deployments: bool = False` - Whether to preserve existing deployments
- Logic:
  1. Find existing artifact in collection by `import_id` (if any)
  2. If `keep_deployments=true` and artifact exists:
     - Save deployment records
     - Delete artifact content only
     - Re-import from upstream
     - Restore deployment records
  3. If `keep_deployments=false` or artifact missing:
     - Full fresh import (same as normal import)
  4. Update catalog entry status

### Part 2: Add Re-import UI (Enhancement)

**Frontend** (`skillmeat/web/components/CatalogEntryModal.tsx`):
- Add kebab menu (DropdownMenu) next to the close 'x' button in header
- Menu items:
  - "Force Re-import" (visible only when `status === "imported"`)
- Clicking opens a confirmation dialog:
  - Title: "Force Re-import Artifact"
  - Description: Explains what re-import does
  - Toggle: "Keep existing deployments" (default: false)
  - Buttons: "Cancel" / "Re-import"

**New React Hook** (`skillmeat/web/hooks/useReimportCatalogEntry.ts`):
- Mutation hook for the new reimport endpoint
- Invalidates relevant query caches on success

## Implementation Tasks

1. [x] **Backend: Add reimport endpoint** - `marketplace_sources.py`
2. [x] **Backend: Update artifact deletion** - `artifacts.py` to reset catalog entry
3. [x] **Backend: Add schema** - `ReimportRequest`, `ReimportResponse` in schemas
4. [x] **Backend: Add repository methods** - `reset_import_status`, `find_by_import_id`, `find_by_artifact_name_and_type`
5. [x] **Frontend: Add kebab menu** - `CatalogEntryModal.tsx` header
6. [x] **Frontend: Add confirmation dialog** - AlertDialog with keep_deployments toggle
7. [x] **Frontend: Add reimport hook** - `useReimportCatalogEntry.ts`
8. [ ] **Tests: Unit tests** - Backend endpoint tests (future work)
9. [ ] **Tests: E2E or integration** - Full flow test (future work)

## Technical Notes

### Catalog Entry Fields (from models)
```python
status: str  # "new" | "updated" | "removed" | "imported" | "excluded"
import_date: Optional[datetime]  # When imported
import_id: str  # Reference to artifact in collection (stored in metadata)
```

### Import Context Method (from repositories.py)
```python
def mark_imported(self, entry_ids: List[str], import_id: str) -> int:
    entry.status = "imported"
    entry.import_date = now
    # import_id stored in metadata dict
```

### Reset Pattern (to implement)
```python
def reset_import_status(self, entry_id: str) -> bool:
    entry.status = "new"
    entry.import_date = None
    # Clear import_id from metadata
```

## Quality Gates

- [x] `pnpm type-check` passes (no errors in new code)
- [x] `pnpm lint` passes (no errors in new code)
- [x] `flake8` passes (no Python errors)
- [x] Backend imports verified
- [ ] Manual test: Delete imported artifact, verify can re-import
- [ ] Manual test: Force re-import with keep_deployments=true

## Files Modified

| File | Changes |
|------|---------|
| `skillmeat/cache/repositories.py` | Added `reset_import_status`, `find_by_import_id`, `find_by_artifact_name_and_type` methods |
| `skillmeat/api/schemas/marketplace.py` | Added `ReimportRequest`, `ReimportResponse` schemas |
| `skillmeat/api/routers/marketplace_sources.py` | Added `POST /{source_id}/entries/{entry_id}/reimport` endpoint |
| `skillmeat/api/routers/artifacts.py` | Updated `delete_artifact` to reset catalog entry status |
| `skillmeat/web/hooks/useReimportCatalogEntry.ts` | New mutation hook for reimport |
| `skillmeat/web/hooks/index.ts` | Added export for new hook |
| `skillmeat/web/components/CatalogEntryModal.tsx` | Added kebab menu and reimport dialog UI |
