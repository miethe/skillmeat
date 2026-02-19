---
title: 'Implementation Plan: Artifact Metadata Lookup Service'
description: Implement fallback lookup sequence for missing artifact metadata in collection
  endpoints
audience:
- ai-agents
- developers
tags:
- implementation
- backend
- collections
- artifacts
created: 2025-12-22
updated: 2025-12-22
category: product-planning
status: inferred_complete
related:
- skillmeat/api/routers/user_collections.py (lines 668-688)
- skillmeat/cache/models.py (Artifact, MarketplaceCatalogEntry models)
schema_version: 2
doc_type: implementation_plan
feature_slug: artifact-metadata-lookup
prd_ref: null
---
# Implementation Plan: Artifact Metadata Lookup Service

**Complexity:** Small (S) | **Track:** Fast Track

**Estimated Effort:** 4-6 hours | **Story Points:** 5

**Scope:** Single backend enhancement to `/user-collections/{id}/artifacts` endpoint

---

## Executive Summary

The `/user-collections/{id}/artifacts` endpoint returns placeholder metadata when artifacts aren't found in the cache table. This plan implements a fallback lookup sequence that attempts to fetch artifact metadata from marketplace catalog entries before returning minimal fallback data. This enables proper display of artifacts sourced from external marketplaces.

---

## Current State Analysis

| Component | Status | Notes |
|-----------|--------|-------|
| **Artifact Query** | Working | Successfully queries `Artifact` cache table |
| **Metadata Fallback** | Placeholder | Returns minimal data with artifact_id as name |
| **TODO Location** | Line 681 | `skillmeat/api/routers/user_collections.py` |
| **ArtifactSummary Schema** | Defined | 4 fields: name, type, version, source |
| **MarketplaceCatalogEntry** | Available | Has: name, artifact_type, detected_version, upstream_url |

**Problem:** Artifacts from marketplace or GitHub sources aren't in the cache table yet, so users see `{name: "artifact-id", type: "unknown"}`.

---

## Implementation Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assigned To |
|----|----|-------------|------------------|----------|------------|
| AML-1 | Create artifact lookup utility | Add `get_artifact_metadata()` function in service layer to implement fallback sequence | Function queries cache → marketplace → fallback in correct order; returns ArtifactSummary | 1h | python-backend-engineer |
| AML-2 | Implement cache table lookup | Query `Artifact` table by ID; return metadata if found | Returns name, type, version, source when artifact exists | 30m | python-backend-engineer |
| AML-3 | Implement marketplace catalog fallback | Query `MarketplaceCatalogEntry` table; map to ArtifactSummary fields | Returns name, artifact_type, detected_version, upstream_url when in catalog | 1h | python-backend-engineer |
| AML-4 | Implement minimal fallback response | Return ArtifactSummary with artifact_id as name when not found anywhere | Returns {name: artifact_id, type: "unknown", version: None, source: artifact_id} | 30m | python-backend-engineer |
| AML-5 | Update router endpoint | Replace TODO with call to new lookup utility | Line 681 calls lookup function instead of inline placeholder logic | 30m | python-backend-engineer |
| AML-6 | Write comprehensive tests | Add pytest cases for all three lookup paths | Tests cover: cache hit, marketplace hit, fallback case; includes parameterized test | 1.5h | python-pro |

**Total Effort:** 5 hours (within 4-6 hour estimate)

---

## Technical Details

### Lookup Sequence

```
1. Query Artifact cache table by artifact_id
   ├─ FOUND: Return {name, type, version, source}
   └─ NOT FOUND: Continue to step 2

2. Query MarketplaceCatalogEntry by source_id or path match
   ├─ FOUND: Return {name, artifact_type as type, detected_version as version, upstream_url as source}
   └─ NOT FOUND: Continue to step 3

3. Return minimal fallback
   └─ Return {name: artifact_id, type: "unknown", version: None, source: artifact_id}
```

### Modified Files

**File:** `skillmeat/api/routers/user_collections.py`
- **Current:** Lines 668-688 (inline placeholder logic)
- **Change:** Replace lines 681-688 with call to `get_artifact_metadata(session, assoc.artifact_id)`

**File:** `skillmeat/api/services/artifact_metadata_service.py` (NEW)
- **Add:** `get_artifact_metadata(session: Session, artifact_id: str) -> ArtifactSummary`
- **Add:** `_lookup_in_cache(session, artifact_id) -> Optional[Artifact]`
- **Add:** `_lookup_in_marketplace(session, artifact_id) -> Optional[MarketplaceCatalogEntry]`

---

## Quality Gates

| Gate | Requirement | How to Test |
|------|------------|------------|
| **Cache Hit** | Returns full metadata when artifact in cache | `test_get_artifact_metadata_from_cache()` |
| **Marketplace Hit** | Returns mapped metadata when in marketplace catalog | `test_get_artifact_metadata_from_marketplace()` |
| **Fallback** | Returns minimal data with artifact_id when not found | `test_get_artifact_metadata_fallback()` |
| **Type Safety** | All returned ArtifactSummary instances are valid Pydantic models | Implicit in pytest (Pydantic validation) |
| **No Breaking Changes** | Existing cache path still works identically | Compare with current implementation for regression |
| **Integration** | Router endpoint works with updated logic | Integration test via test client |

**Test Coverage Target:** 100% of lookup logic paths

---

## Rollout Plan

**Single Release:** No phasing required

1. **Implement artifact lookup utility** (AML-1 through AML-5)
2. **Write tests** (AML-6)
3. **Manual verification** via API client: fetch collection artifacts, verify metadata populates correctly
4. **Merge & deploy** to main branch

No feature flags or gradual rollout needed - this is a pure enhancement with no behavioral changes to cached artifacts.

---

## Success Criteria

- [ ] All 6 tasks completed and merged
- [ ] All tests pass (100% code coverage for lookup paths)
- [ ] TODO comment at line 681 removed
- [ ] Router returns proper ArtifactSummary for all three lookup scenarios
- [ ] No regression in existing cache lookup behavior
- [ ] API documentation updated if endpoint behavior changes
