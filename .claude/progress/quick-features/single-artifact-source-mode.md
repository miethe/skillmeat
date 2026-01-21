# Quick Feature: Single Artifact Source Mode

**Status**: completed
**Started**: 2026-01-20

## Summary

When adding a Marketplace Source for a GitHub repo that is itself a single artifact (e.g., a skill with SKILL.md at repo root), the detection algorithm doesn't find it. This adds an optional toggle to mark a source as a single artifact, with manual type selection.

## Changes

### 1. API Schema (`skillmeat/api/schemas/marketplace.py`)
- Add `single_artifact_mode: bool = False` to `CreateSourceRequest`
- Add `single_artifact_type: Optional[ArtifactType]` (required when mode=True)

### 2. Marketplace Service/Scanner
- When `single_artifact_mode=True`, skip standard detection
- Treat entire repo (or root_hint dir) as one artifact of specified type
- Set confidence to 100% (manual override)

### 3. Frontend (`skillmeat/web/components/marketplace/add-source-modal.tsx`)
- Add "Treat as single artifact" toggle in Settings section
- When enabled, show artifact type selector (skill, command, agent, etc.)
- Pass `single_artifact_mode` and `single_artifact_type` to API

### 4. SDK Regeneration
- Run `pnpm generate-sdk` to pick up new API fields

## Files Modified

- `skillmeat/api/schemas/marketplace.py` - Added `single_artifact_mode` and `single_artifact_type` fields to CreateSourceRequest and SourceResponse
- `skillmeat/api/routers/marketplace_sources.py` - Updated `create_source` and `_perform_scan` to handle single artifact mode
- `skillmeat/cache/models.py` - Added columns to MarketplaceSource model
- `skillmeat/cache/migrations/versions/20260120_1000_add_single_artifact_mode_to_marketplace_sources.py` - New Alembic migration
- `skillmeat/web/components/marketplace/add-source-modal.tsx` - Added toggle and type selector UI
- `skillmeat/web/types/marketplace.ts` - Updated CreateSourceRequest and GitHubSource interfaces
- `skillmeat/web/sdk/models/CreateSourceRequest.ts` (generated)
- `skillmeat/api/openapi.json` (regenerated)
