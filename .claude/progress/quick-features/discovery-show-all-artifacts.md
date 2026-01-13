---
type: quick-feature-plan
feature_slug: discovery-show-all-artifacts
request_log_id: null
status: completed
completed_at: 2026-01-13T12:30:00Z
created: 2026-01-13T12:00:00Z
estimated_scope: medium
---

# Discovery Tab: Show All Detected Artifacts

## Scope

Modify the Discovery flow to return ALL detected artifacts from a Project (not just importable ones), with appropriate `collection_match` metadata so the UI can:
1. Display artifacts already in Collection under "Exact Matches" section
2. Display new/unmatched artifacts under "New Artifacts" section for import
3. Link detected artifacts to their matching Collection artifacts

## Current Behavior

- `discovery.py` lines 466-504: Filters out artifacts where `location == "both"` (exists in both Collection and Project)
- Only "importable" artifacts are returned in the `artifacts` field
- Artifacts matching Collection entries are silently excluded

## Desired Behavior

- Return ALL detected artifacts in the response
- Add `collection_match` field populated for each artifact showing:
  - `type: "exact" | "hash"` for artifacts already in Collection
  - `type: "none"` for new artifacts not in Collection
  - `matched_artifact_id` linking to the Collection artifact
- UI groups and displays them appropriately:
  - "Exact Matches" (Already in Collection): Shows artifacts with `collection_match.type` = "exact" or "hash"
  - "New Artifacts" (Ready to Import): Shows artifacts with `collection_match.type` = "none"

## Affected Files

- `skillmeat/core/discovery.py`: Remove filtering, populate collection_match for all artifacts
- `skillmeat/api/schemas/discovery.py`: Ensure DiscoveryResult includes all artifacts
- `skillmeat/web/components/discovery/DiscoveryTab.tsx`: Already handles grouping by collection_match
- `skillmeat/web/hooks/useProjectDiscovery.ts`: May need minor updates

## Implementation Steps

1. Modify `discover_artifacts()` in discovery.py → @python-backend-engineer
   - Remove the filter at lines 483-490 that excludes `location == "both"`
   - Instead, populate `collection_match` field for all discovered artifacts
   - Keep the count distinction: `discovered_count` = all, `importable_count` = new only

2. Verify UI already handles this → @ui-engineer-enhanced
   - DiscoveryTab.tsx has `groupArtifacts()` that splits by match_type
   - Verify "Exact Matches" section correctly shows already-imported artifacts

## Testing

- Run discovery on project with skills in both Collection and Project
- Verify all artifacts appear in response
- Verify UI shows proper grouping

## Completion Criteria

- [x] All detected artifacts returned (not filtered)
- [x] collection_match populated correctly
- [x] UI shows "Exact Matches" for already-imported
- [x] UI shows "New Artifacts" for importable
- [x] Tests pass
- [x] Build succeeds

## Changes Made

### 1. discovery.py - Return ALL artifacts with collection_match

**Lines 466-527**: Changed from filtering to population
- Removed filtering logic that excluded artifacts where `location == "both"`
- Now returns ALL discovered artifacts in `artifacts` list
- `importable_count` still tracks only new artifacts (not in Collection)
- `collection_match` populated for all artifacts:
  - `type="exact"` for artifacts in Collection (with full confidence)
  - `type="name_type"` for fuzzy matches (85% confidence, possible duplicates)
  - `type="none"` for new artifacts (not in Collection)

### 2. discovery.py - Fix Collection path bug

**Line 1447-1450**: Fixed incorrect collection path
- Was: `collection_base / "artifacts" / f"{artifact_type}s"`
- Now: `collection_base / f"{artifact_type}s"`
- The actual Collection structure is `~/.skillmeat/collections/{name}/{type}s/` NOT nested under `artifacts/`

### 3. test_discovery_prescan.py - Updated test fixtures

**Lines 23-40**: Fixed collection_base fixture
- Removed `artifacts/` subdirectory from test setup to match actual Collection structure
- Updated all artifact path references to use direct type directories
