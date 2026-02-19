---
type: quick-feature-plan
feature_slug: marketplace-import-cache-sync
request_log_id: null
status: completed
created: 2026-02-10
completed_at: 2026-02-10
estimated_scope: medium
schema_version: 2
doc_type: quick_feature
---

# Marketplace Import Cache Sync Refactor

## Scope
Extract shared DB upsert service function, create import-specific helper, refactor both import endpoints
to use them, and keep `refresh_single_artifact_cache()` for periodic/manual cache sync only.

## Affected Files
- `skillmeat/api/services/artifact_cache_service.py`: Add `create_or_update_collection_artifact()` + `populate_collection_artifact_from_import()`, refactor `refresh_single_artifact_cache()` to use shared upsert
- `skillmeat/api/routers/marketplace_sources.py`: Refactor batch import (~L3716) and reimport (~L4046) endpoints to use new service functions

## Implementation Steps
1. Add shared `create_or_update_collection_artifact()` to artifact_cache_service.py → @python-backend-engineer
2. Refactor `refresh_single_artifact_cache()` to delegate DB upsert to shared function → @python-backend-engineer
3. Add `populate_collection_artifact_from_import()` import-specific helper → @python-backend-engineer
4. Refactor batch import endpoint to use `populate_collection_artifact_from_import()` (remove bare row + refresh pattern) → @python-backend-engineer
5. Fix reimport endpoint to use `populate_collection_artifact_from_import()` → @python-backend-engineer

## Testing
- Python type check passes
- Manual verification: import + reimport both populate description, source, origin fields

## Completion Criteria
- [x] `create_or_update_collection_artifact()` extracted and working
- [x] `refresh_single_artifact_cache()` refactored to use shared upsert
- [x] `populate_collection_artifact_from_import()` created
- [x] Batch import endpoint uses new service (single DB op per artifact)
- [x] Reimport endpoint uses new service (fixes regression)
- [x] Quality gates pass
