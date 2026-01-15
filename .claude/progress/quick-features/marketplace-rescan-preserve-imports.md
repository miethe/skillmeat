# Quick Feature: Preserve Imported Artifact Metadata During Marketplace Rescan

**Status**: completed
**Created**: 2025-01-15
**Estimated Scope**: Medium (5-7 files, ~300 lines)

## Problem Statement

When a Marketplace Source is rescanned:
1. The current `replace_catalog_entries()` method wipes ALL catalog entries
2. This loses import metadata (status="imported", import_date, import_id)
3. Users have no way to know if upstream has updates for imported artifacts
4. No bulk sync mechanism exists for marketplace sources

## Solution Overview

### Backend Changes

**1. Preserve imported metadata during rescan** (`skillmeat/cache/repositories.py`)
- Add `merge_catalog_entries()` method to `ScanUpdateContext`
- Instead of full replace, match entries by `upstream_url` or `path`
- Preserve: `status`, `import_date`, `import_id`, `excluded_at`, `excluded_reason`
- Update: `detected_sha`, `confidence_score`, other detection metadata

**2. Detect updates to imported artifacts** (`skillmeat/api/routers/marketplace_sources.py`)
- After scan, compare `detected_sha` with collection artifact's `resolved_sha`
- Return list of imported artifacts with upstream changes in `ScanResultDTO`

**3. Bulk sync endpoint** (`skillmeat/api/routers/marketplace_sources.py`)
- `POST /marketplace/sources/{source_id}/sync-imported`
- Request body: `{ artifact_ids: string[], conflict_strategy: "skip" | "overwrite" | "prompt" }`
- Uses existing artifact sync logic from `/artifacts/{id}/sync`
- Returns per-artifact sync results with conflict info

### Frontend Changes

**4. Post-rescan dialog** (`skillmeat/web/components/marketplace/rescan-updates-dialog.tsx`)
- Shows after successful rescan if any imported artifacts have updates
- Lists each updated artifact with:
  - Name, type
  - Current SHA vs detected SHA (short)
  - Has conflicts checkbox (auto-checked if no local changes)
- "Sync Selected" button triggers bulk sync
- Conflict items link to artifact modal Sync Status tab

**5. Wire into existing rescan flow** (`skillmeat/web/components/marketplace/source-detail-panel.tsx`)
- Capture scan result with updated imports list
- Show `RescanUpdatesDialog` if updates detected
- Invalidate queries on sync completion

## File Changes

| File | Change Type | Lines |
|------|-------------|-------|
| `skillmeat/cache/repositories.py` | Add `merge_catalog_entries()` | ~60 |
| `skillmeat/api/routers/marketplace_sources.py` | Modify `_perform_scan()`, add bulk sync | ~100 |
| `skillmeat/api/schemas/discovery.py` | Add `ScanResultDTO.updated_imports`, bulk sync schemas | ~40 |
| `skillmeat/web/components/marketplace/rescan-updates-dialog.tsx` | New component | ~150 |
| `skillmeat/web/components/marketplace/source-detail-panel.tsx` | Wire dialog | ~30 |

## Implementation Order

1. **Backend: merge_catalog_entries()** - Core metadata preservation
2. **Backend: Detect updates** - Compare SHAs after scan
3. **Backend: Bulk sync endpoint** - Reuse artifact sync logic
4. **Frontend: Dialog component** - UI for selecting updates
5. **Frontend: Integration** - Wire into rescan flow

## Quality Gates

```bash
pytest tests/api/test_marketplace_sources.py -v
pytest tests/cache/test_repositories.py -v
pnpm --filter web test
pnpm --filter web typecheck
pnpm --filter web lint
pnpm --filter web build
```

## References

- Existing sync: `/artifacts/{id}/sync` endpoint
- Sync Status Tab: `web/components/sync-status/sync-status-tab.tsx`
- Catalog entry model: `cache/models.py:1368` (MarketplaceCatalogEntry)
- Replace entries: `cache/repositories.py:378` (current full replacement)
