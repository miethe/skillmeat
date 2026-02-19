---
title: 'Implementation Plan: Tag Storage Consolidation'
description: Eliminate dual file-based tag storage (Artifact.tags vs ArtifactMetadata.tags)
  by consolidating to a single Artifact.tags field as the source of truth
audience:
- ai-agents
- developers
tags:
- implementation
- refactor
- tags
- data-model
- consolidation
created: 2026-02-03
updated: 2026-02-03
category: refactors
status: inferred_complete
complexity: Medium
total_effort: 6-10 hours
related:
- /docs/project_plans/implementation_plans/enhancements/tags-refactor-v1.md
- /docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md
---
# Implementation Plan: Tag Storage Consolidation

**Plan ID**: `IMPL-2026-02-03-TAG-STORAGE-CONSOLIDATION`
**Date**: 2026-02-03
**Author**: Claude Opus 4.5 (AI-generated)
**Related Documents**:
- **Tags Refactor V1**: `/docs/project_plans/implementation_plans/enhancements/tags-refactor-v1.md` (Phases 0-6 implemented)
- **Metadata Cache V1**: `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md` (completed)

**Complexity**: Medium
**Total Estimated Effort**: 6-10 hours (1-2 days)
**Target Timeline**: Single PR, co-deployed frontend + backend

---

## Executive Summary

Tags for file-based artifacts are stored in two independent locations on the `Artifact` dataclass: `Artifact.tags` (top-level) and `Artifact.metadata.tags` (nested in `ArtifactMetadata`). These two fields are populated by different code paths, read by different consumers, and never automatically merged -- requiring ad-hoc merge logic at 15+ integration points across Python backend, API layer, cache sync, and frontend mappers.

This refactor consolidates to a single `Artifact.tags` field by:
1. Auto-merging `metadata.tags` into `Artifact.tags` at construction time (`__post_init__`)
2. Removing `tags` from TOML serialization of metadata
3. Simplifying all consumer code to read from one location
4. Preserving backward compatibility with existing `collection.toml` files

The ORM-based `Tag`/`ArtifactTag` database system (from tags-refactor-v1) is unaffected -- it continues syncing from `Artifact.tags`.

---

## Problem Statement

### Current Architecture: Three Tag Storage Systems

| # | Location | Type | Populated By | Read By |
|---|----------|------|---|---|
| 1 | `Artifact.tags` | `List[str]` on dataclass | CLI `--tags`, `PUT /tags`, path-based import, marketplace import | Tag filtering (`list_artifacts`), TOML manifest, `PUT /tags` cache sync |
| 2 | `ArtifactMetadata.tags` | `List[str]` on dataclass | Frontmatter parsing (`metadata.py`) | CLI display, search indexing, vault filtering, cache miss fallback |
| 3 | ORM `Tag`/`ArtifactTag` | Database junction table | `TagService.sync_artifact_tags()` | `/tags` API endpoints, metadata service |

### Identified Bugs and Inconsistencies

1. **`list_artifacts()` tag filter** (`artifact.py:740`): Checks ONLY `Artifact.tags` -- artifacts with frontmatter-only tags are invisible to filtering
2. **`PUT /artifacts/{id}/tags` cache update** (`artifacts.py:6435`): Writes ONLY `request.tags` to `CollectionArtifact.tags_json` -- drops `metadata.tags` from cache
3. **Cache miss fallback** (`user_collections.py:1560-1564`): Reads ONLY `metadata.tags` -- drops `Artifact.tags`
4. **CLI display** (`cli.py:259`): Reads ONLY `metadata.tags` -- misses user-applied tags
5. **Search indexing** (`search.py:249,953,1280`): Indexes ONLY `metadata.tags` -- user/path tags not searchable
6. **Frontend merge band-aid**: Both `mappers.ts` and `entity-mapper.ts` contain `[...new Set([...topLevelTags, ...metadataTags])]` merge logic
7. **`unified-card.tsx:119`**: Reads ONLY `item.metadata.tags` -- misses top-level tags entirely

### Root Cause

The original design intended `metadata.tags` as "intrinsic/author tags from frontmatter" and `Artifact.tags` as "user-applied tags." But:
- No UI or API distinguishes between them
- The frontend always merges them
- Each consumer arbitrarily chooses one source
- Updates write to one location, reads check a different one

---

## Solution Design

### Key Decision: Transient Parsing Field

**Keep `ArtifactMetadata.tags` as a field for frontmatter parsing** but make it transient:

1. `metadata.py` continues populating `ArtifactMetadata.tags` from frontmatter (zero parsing changes)
2. `Artifact.__post_init__()` auto-merges `metadata.tags` into `Artifact.tags` and clears `metadata.tags`
3. `ArtifactMetadata.to_dict()` stops serializing tags (never persisted to TOML metadata section)
4. `Artifact.from_dict()` automatically merges legacy TOML `[metadata].tags` via `__post_init__`
5. API response removes `tags` from `ArtifactMetadataResponse` schema

### Why This Approach

| Alternative | Problem |
|---|---|
| Remove `ArtifactMetadata.tags` field entirely | Requires rewriting `metadata.py` parsing pipeline and `FetchResult` contracts |
| Return tags separately from metadata parser | Changes function signatures across 4+ callers |
| **Keep field, merge at construction** | Zero parsing changes, backward compatible, automatic merge |

### Tag Priority Order

When `__post_init__` merges, user-provided tags come first (preserving user intent), then frontmatter tags:

```python
self.tags = list(dict.fromkeys(self.tags + self.metadata.tags))
#                               ^^^^ user/path tags first  ^^^^ frontmatter tags appended
```

`dict.fromkeys` deduplicates while preserving insertion order (Python 3.7+).

### Out of Scope

- **`BundleMetadata.tags`**: Separate dataclass in `skillmeat/core/sharing/bundle.py` -- different concern
- **`metadata.py` frontmatter parsing**: Continues populating `metadata.tags` as transit data
- **ORM `Tag`/`ArtifactTag` system**: Unchanged, continues syncing from `Artifact.tags` via `TagService`
- **Standalone `ArtifactMetadata` display**: CLI pre-add preview still shows parsed frontmatter tags

---

## Implementation Strategy

### Architecture Sequence

1. **Core Model** -- `__post_init__` merge + serialization change (foundation)
2. **Backend Consumers** -- Simplify all dual-source reads (cache sync, API response, search, CLI)
3. **API Schema** -- Remove `tags` from `ArtifactMetadataResponse`
4. **Frontend** -- Remove merge logic from mappers, fix legacy paths
5. **Tests** -- Update assertions, add merge/backward-compat tests
6. **Verification** -- Full test suite + manual validation

### Deployment Strategy

**Single PR, co-deployed.** The API schema change (removing `metadata.tags` from response) requires simultaneous frontend and backend deployment. Since both are in this monorepo, this is the standard approach.

---

## Phase 1: Core Model Consolidation

**Priority**: CRITICAL (foundation for all other phases)
**Dependencies**: None
**Assigned Subagent(s)**: `python-backend-engineer`

| Task ID | Task Name | Description | Acceptance Criteria | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|-------------|--------------|
| TASK-1.1 | Add merge logic to `Artifact.__post_init__()` | After existing validation, merge `metadata.tags` into `self.tags` with dedup, then clear `metadata.tags` | New artifacts have all tags in `Artifact.tags`; `metadata.tags` is `[]` after construction | python-backend-engineer | None |
| TASK-1.2 | Remove tags from `ArtifactMetadata.to_dict()` | Remove the `if self.tags: result["tags"] = self.tags` block | TOML output has no `[metadata].tags` section; tags only at top level | python-backend-engineer | TASK-1.1 |

### Implementation Details

**TASK-1.1: Merge logic in `__post_init__()`**

File: `skillmeat/core/artifact.py` (line 289, after existing validation)

```python
# Consolidate: merge metadata.tags into top-level tags (single source of truth)
if self.metadata and self.metadata.tags:
    self.tags = list(dict.fromkeys(self.tags + self.metadata.tags))
    self.metadata.tags = []
```

**Backward compatibility**: `Artifact.from_dict()` (line 332) already reads `metadata.tags` from TOML metadata section and passes it to `ArtifactMetadata.from_dict()`. The resulting `Artifact()` constructor triggers `__post_init__()` which merges legacy tags automatically.

**TASK-1.2: Remove from `ArtifactMetadata.to_dict()`**

File: `skillmeat/core/artifact.py` (lines 75-76)

Remove:
```python
if self.tags:
    result["tags"] = self.tags
```

No changes needed to:
- `ArtifactMetadata.from_dict()` (line 120) -- still reads `tags` for backward compat
- `Artifact.from_dict()` (line 361) -- `__post_init__` handles merge
- `metadata.py` frontmatter parsing -- continues populating `metadata.tags` as transit

### Phase 1 Quality Gates

- [ ] `Artifact` constructed with both `tags=["user"]` and `metadata.tags=["frontmatter"]` results in `artifact.tags == ["user", "frontmatter"]` and `artifact.metadata.tags == []`
- [ ] Duplicate tags are deduplicated: `tags=["shared"]` + `metadata.tags=["shared", "other"]` yields `["shared", "other"]`
- [ ] `Artifact.to_dict()` outputs tags only at top level, not in metadata section
- [ ] `Artifact.from_dict()` with legacy TOML (tags in metadata section) correctly merges into `artifact.tags`
- [ ] Existing artifact tests pass

---

## Phase 2: Backend Consumer Updates

**Priority**: HIGH
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: `python-backend-engineer`

| Task ID | Task Name | Description | Acceptance Criteria | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|-------------|--------------|
| TASK-2.1 | Simplify `artifact_cache_service.py` | Replace merge expression with single-source read | Cache reads only `file_artifact.tags` | python-backend-engineer | TASK-1.1 |
| TASK-2.2 | Simplify `user_collections.py` (4 locations) | Replace all 4 merge patterns with single-source reads | No `metadata.tags` references in cache sync code | python-backend-engineer | TASK-1.1 |
| TASK-2.3 | Stop serializing `metadata.tags` in API response | Remove `tags=artifact.metadata.tags` from `ArtifactMetadataResponse` construction | API response has tags only at top level | python-backend-engineer | TASK-1.1 |
| TASK-2.4 | Fix `update_artifact()` dual write | Change `artifact.metadata.tags = ...` to `artifact.tags = ...` | Tag updates write to single location | python-backend-engineer | TASK-1.1 |
| TASK-2.5 | Fix `search.py` tag reads (3 locations) | Switch from `metadata.tags` to `artifact.tags` for search scoring | Search finds user-applied and path-based tags | python-backend-engineer | TASK-1.1 |
| TASK-2.6 | Fix CLI tag display | Change `artifact.metadata.tags` to `artifact.tags` at line 259 | CLI shows all tags including user-applied | python-backend-engineer | TASK-1.1 |

### Implementation Details

**TASK-2.1: Simplify `artifact_cache_service.py`**

File: `skillmeat/api/services/artifact_cache_service.py` (lines 83-89)

```python
# BEFORE (merge expression):
"tags_json": (
    json.dumps(list(dict.fromkeys(
        (file_artifact.tags or []) +
        (file_artifact.metadata.tags if file_artifact.metadata else [])
    )))
    if (file_artifact.tags or (file_artifact.metadata and file_artifact.metadata.tags))
    else None
),

# AFTER:
"tags_json": json.dumps(file_artifact.tags) if file_artifact.tags else None,
```

**TASK-2.2: Simplify `user_collections.py` (4 locations)**

File: `skillmeat/api/routers/user_collections.py`

| Location | Lines | Before | After |
|---|---|---|---|
| `_sync_default_collection_cache()` | 419-423 | `all_tags = (artifact.tags or []) + (metadata.tags ...)` | `tags_json = json.dumps(artifact.tags) if artifact.tags else None` |
| `refresh_single_artifact_cache()` | 735-739 | Same merge pattern | Same simplification |
| `_rebuild_metadata_cache()` | 2294-2298 | Same merge pattern | Same simplification |
| Cache miss fallback | 1560-1564 | `tags=(file_artifact.metadata.tags if ...)` | `tags=file_artifact.tags or None` |

**TASK-2.3: Stop serializing `metadata.tags` in API response**

File: `skillmeat/api/routers/artifacts.py` (line 526)

Remove `tags=artifact.metadata.tags` from the `ArtifactMetadataResponse()` constructor. After Phase 3 removes the field from the schema, this line must not be present.

**TASK-2.4: Fix `update_artifact()` dual write**

File: `skillmeat/api/routers/artifacts.py` (lines 2401-2402)

```python
# BEFORE:
if metadata_updates.tags is not None:
    artifact.metadata.tags = metadata_updates.tags

# AFTER:
if metadata_updates.tags is not None:
    artifact.tags = metadata_updates.tags
```

**TASK-2.5: Fix `search.py` tag reads**

File: `skillmeat/core/search.py`

Lines 249-253 (`_search_metadata`): The `metadata` variable is a freshly parsed `ArtifactMetadata` from `extract_artifact_metadata()`, so it still has `metadata.tags`. But we should use `artifact.tags` (the merged set) for completeness:
```python
artifact_tags = artifact.tags if hasattr(artifact, 'tags') and artifact.tags else (metadata.tags or [])
if artifact_tags:
    for tag in artifact_tags:
```

Lines 953-954 (`_search_project_metadata`): Context is `artifact["metadata"]` dict from scanned project artifacts:
```python
artifact_tags = artifact.get("tags", metadata.tags or [])
```

Line 1280 (`_build_fingerprint`): Same dict context:
```python
tags=artifact.get("tags", metadata.tags or []),
```

**TASK-2.6: Fix CLI tag display**

File: `skillmeat/cli.py` (line 259)

```python
# BEFORE:
", ".join(artifact.metadata.tags) if artifact.metadata.tags else ""

# AFTER:
", ".join(artifact.tags) if artifact.tags else ""
```

Lines 3983-3985, 4020-4021: Standalone `ArtifactMetadata` in pre-add preview -- **no change** (parsing still populates). Lines 8250+, 10081+: `BundleMetadata.tags` -- **out of scope**.

### Phase 2 Quality Gates

- [ ] No `metadata.tags` references remain in cache sync code
- [ ] API response `metadata` object has no `tags` field
- [ ] Search indexes find user-applied and path-based tags
- [ ] CLI `list` command shows all tags
- [ ] `update_artifact()` writes tags to single location

---

## Phase 3: API Schema Cleanup

**Priority**: HIGH
**Dependencies**: Phase 2 complete (TASK-2.3 specifically)
**Assigned Subagent(s)**: `python-backend-engineer`

| Task ID | Task Name | Description | Acceptance Criteria | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|-------------|--------------|
| TASK-3.1 | Remove `tags` from `ArtifactMetadataResponse` | Remove the `tags: List[str]` field from the Pydantic schema | Schema no longer includes `metadata.tags` in OpenAPI spec | python-backend-engineer | TASK-2.3 |

### Implementation Details

**TASK-3.1: Remove `tags` from `ArtifactMetadataResponse`**

File: `skillmeat/api/schemas/artifacts.py` (line 179)

Remove the `tags: List[str]` field from `ArtifactMetadataResponse`. The top-level `ArtifactResponse.tags` (line 299) remains as the canonical tag field.

### Phase 3 Quality Gates

- [ ] `ArtifactMetadataResponse` schema has no `tags` field
- [ ] OpenAPI spec reflects the change
- [ ] No serialization errors on API responses

---

## Phase 4: Frontend Simplification

**Priority**: HIGH
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: `ui-engineer-enhanced`

| Task ID | Task Name | Description | Acceptance Criteria | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|-------------|--------------|
| TASK-4.1 | Simplify `mappers.ts` | Remove tag merge logic, use only `response.tags` | No `metadata?.tags` references in merge logic | ui-engineer-enhanced | TASK-3.1 |
| TASK-4.2 | Simplify `entity-mapper.ts` | Remove tag merge logic, use only `artifact.tags` | No `metadata?.tags` references in merge logic | ui-engineer-enhanced | TASK-3.1 |
| TASK-4.3 | Remove `tags` from metadata interfaces | Remove `tags?: string[]` from `ApiArtifactMetadata` and mapper metadata types | TypeScript types reflect single tag source | ui-engineer-enhanced | TASK-4.1 |
| TASK-4.4 | Fix `unified-card.tsx` | Change `item.metadata.tags` to `item.tags` with safe fallback | Legacy card path reads tags correctly | ui-engineer-enhanced | TASK-4.1 |
| TASK-4.5 | Update frontend tests | Remove merge-specific tests, update fixtures | Tests reflect single-source tags | ui-engineer-enhanced | TASK-4.1 |

### Implementation Details

**TASK-4.1: Simplify `mappers.ts`** (lines 307-310)

```typescript
// BEFORE:
const topLevelTags = response.tags || [];
const metadataTags = response.metadata?.tags || [];
const allTags = [...new Set([...topLevelTags, ...metadataTags])];

// AFTER:
const allTags = response.tags || [];
```

**TASK-4.2: Simplify `entity-mapper.ts`** (lines 411-414)

```typescript
// BEFORE:
const topLevelTags = artifact.tags ?? [];
const metadataTags = artifact.metadata?.tags ?? [];
const tags = [...new Set([...topLevelTags, ...metadataTags])];

// AFTER:
const tags = artifact.tags ?? [];
```

**TASK-4.3: Remove from interfaces**

File: `skillmeat/web/lib/api/entity-mapper.ts` (line 46) -- remove `tags?: string[];` from `ApiArtifactMetadata`. Also check `ArtifactMetadataResponse` type in `mappers.ts`.

**TASK-4.4: Fix `unified-card.tsx`** (line 119)

```typescript
// BEFORE:
tags: item.metadata.tags,

// AFTER:
tags: item.tags ?? item.metadata?.tags,
```

**TASK-4.5: Update frontend tests**

File: `skillmeat/web/lib/api/mappers.test.ts` (lines 159-196):
- Remove "merge and deduplicate from both sources" test
- Remove "handle tags from metadata only" test
- Keep "handle tags from top-level only" and "no tags" tests

File: `skillmeat/web/__tests__/lib/api/entity-mapper.test.ts` (lines 390-415):
- Remove "merges tags from both top-level and metadata" test
- Update fixtures to put tags at top level only

### Phase 4 Quality Gates

- [ ] No `metadata?.tags` merge logic in mappers
- [ ] `ApiArtifactMetadata` interface has no `tags` field
- [ ] `unified-card.tsx` reads tags from correct location
- [ ] Frontend tests pass
- [ ] TypeScript type-check passes (`pnpm type-check`)

---

## Phase 5: Python Test Updates

**Priority**: MEDIUM
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: `python-backend-engineer`

| Task ID | Task Name | Description | Acceptance Criteria | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|-------------|--------------|
| TASK-5.1 | Update `test_artifact.py` | Fix assertions for metadata.tags serialization and round-trip | Tests pass with new merge behavior | python-backend-engineer | TASK-1.1 |
| TASK-5.2 | Add merge behavior tests | New tests for `__post_init__` merge, dedup, and backward compat | Merge, dedup, and legacy TOML loading verified | python-backend-engineer | TASK-1.1 |

### Implementation Details

**TASK-5.1: Update existing tests**

File: `tests/unit/test_artifact.py`

- `test_to_dict_with_values`: Assert tags NOT in metadata dict output (was `{"title": ..., "tags": ["test"]}`, now `{"title": ...}`)
- `test_round_trip`: Assert `artifact.tags` has merged result, `artifact.metadata.tags == []`

**TASK-5.2: Add new tests**

```python
def test_post_init_merges_metadata_tags(self):
    """Tags from metadata are merged into artifact.tags and metadata.tags is cleared."""
    metadata = ArtifactMetadata(tags=["from-frontmatter", "shared"])
    artifact = Artifact(
        name="test", type=ArtifactType.SKILL, path="skills/test/",
        origin="local", metadata=metadata, added=datetime.utcnow(),
        tags=["user-tag", "shared"],
    )
    assert artifact.tags == ["user-tag", "shared", "from-frontmatter"]
    assert artifact.metadata.tags == []

def test_from_dict_merges_legacy_metadata_tags(self):
    """Artifact.from_dict merges legacy metadata.tags into top-level tags."""
    data = {
        "name": "test", "type": "skill", "path": "skills/test/",
        "origin": "local", "added": "2025-01-01T00:00:00",
        "metadata": {"tags": ["legacy-tag"]},
        "tags": ["top-tag"],
    }
    artifact = Artifact.from_dict(data)
    assert artifact.tags == ["top-tag", "legacy-tag"]
    assert artifact.metadata.tags == []
```

**No changes needed for:**
- `test_frontmatter_extraction.py` -- tests standalone `ArtifactMetadata` (still populated by parser)
- `test_local_source.py`, `tests/integration/test_sources.py` -- tests `FetchResult.metadata.tags` (standalone)
- Bundle/vault tests -- `BundleMetadata`, out of scope

### Phase 5 Quality Gates

- [ ] All existing Python tests pass
- [ ] New merge behavior tests pass
- [ ] Legacy TOML backward compat test passes

---

## Phase 6: Verification

**Priority**: HIGH
**Dependencies**: All phases complete

### Automated Verification

```bash
# Python tests
pytest -v --cov=skillmeat

# Frontend tests
cd skillmeat/web && pnpm test

# Type checking
cd skillmeat/web && pnpm type-check

# Lint
cd skillmeat/web && pnpm lint
```

### Manual Verification

1. Start dev servers (`skillmeat web dev`)
2. Load collection with tagged artifacts on `/collection` page
3. Verify tags display correctly in artifact modals
4. Load same artifacts on `/manage` page -- verify same tags
5. Update tags via modal -- verify round-trip
6. Inspect `collection.toml` -- tags should only appear at top level, NOT in `[metadata]` section
7. Restart servers -- verify tags persist correctly after reload

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Legacy TOML files with `metadata.tags` break on load | Low | High | `__post_init__` auto-merge handles this transparently |
| Standalone `ArtifactMetadata` consumers affected | Low | Medium | Parser still populates `metadata.tags`; only `Artifact`-wrapped instances merge |
| Frontend receives cached responses with old `metadata.tags` | Low | Low | Safe fallback with optional chaining in `unified-card.tsx` |
| Search breaks for project-scanned artifacts (dict format) | Medium | Medium | Fallback to `metadata.tags` when artifact has no top-level `tags` key |

### Data Consistency Risks

| Risk | Mitigation |
|------|------------|
| Existing `collection.toml` with both tag locations | `__post_init__` merges on load; next save writes consolidated format |
| ORM tags out of sync after consolidation | `TagService.sync_artifact_tags()` still receives from `Artifact.tags` -- no change |
| Cache refresh needed after deploy | Existing `/refresh-cache` endpoint handles this |

---

## Orchestration Quick Reference

### Batch 1: Core Model (Phase 1 -- Sequential)

```
Task("python-backend-engineer", "TASK-1.1 + TASK-1.2: Consolidate tag storage in core model.
     File: skillmeat/core/artifact.py
     1. In Artifact.__post_init__() (after line 289), add merge logic:
        if self.metadata and self.metadata.tags:
            self.tags = list(dict.fromkeys(self.tags + self.metadata.tags))
            self.metadata.tags = []
     2. In ArtifactMetadata.to_dict() (lines 75-76), remove:
        if self.tags:
            result['tags'] = self.tags
     Do NOT change from_dict(), metadata.py, or any other files.")
```

### Batch 2: Backend Consumers (Phase 2 -- Single agent, sequential)

```
Task("python-backend-engineer", "TASK-2.1 through TASK-2.6: Update all backend tag consumers.
     Files to modify:
     1. skillmeat/api/services/artifact_cache_service.py (lines 83-89): Simplify to json.dumps(file_artifact.tags)
     2. skillmeat/api/routers/user_collections.py (4 locations: lines 419-423, 735-739, 1560-1564, 2294-2298):
        Replace all merge logic with single-source reads from artifact.tags
     3. skillmeat/api/routers/artifacts.py (line 526): Remove tags from ArtifactMetadataResponse construction
     4. skillmeat/api/routers/artifacts.py (lines 2401-2402): Change metadata.tags write to artifact.tags
     5. skillmeat/core/search.py (lines 249, 953, 1280): Switch from metadata.tags to artifact.tags
     6. skillmeat/cli.py (line 259): Change metadata.tags to artifact.tags
     7. skillmeat/api/schemas/artifacts.py (line 179): Remove tags field from ArtifactMetadataResponse")
```

### Batch 3: Frontend (Phase 4 -- Parallel with Python tests)

```
Task("ui-engineer-enhanced", "TASK-4.1 through TASK-4.5: Simplify frontend tag handling.
     Files to modify:
     1. skillmeat/web/lib/api/mappers.ts (lines 307-310): Remove merge, use response.tags only
     2. skillmeat/web/lib/api/entity-mapper.ts (lines 411-414): Remove merge, use artifact.tags only
     3. skillmeat/web/lib/api/entity-mapper.ts (line 46): Remove tags from ApiArtifactMetadata
     4. skillmeat/web/components/shared/unified-card.tsx (line 119): Use item.tags with fallback
     5. skillmeat/web/lib/api/mappers.test.ts (lines 159-196): Remove merge tests
     6. skillmeat/web/__tests__/lib/api/entity-mapper.test.ts (lines 390-415): Remove merge tests")

Task("python-backend-engineer", "TASK-5.1 + TASK-5.2: Update Python tests.
     File: tests/unit/test_artifact.py
     1. Update test_to_dict_with_values: tags should NOT appear in metadata dict
     2. Update test_round_trip: artifact.tags has merged result, metadata.tags == []
     3. Add test_post_init_merges_metadata_tags: verify merge + dedup + clear
     4. Add test_from_dict_merges_legacy_metadata_tags: verify backward compat")
```

---

## Files Modified (Complete List)

| File | Phase | Changes |
|------|-------|---------|
| `skillmeat/core/artifact.py` | 1 | `__post_init__` merge; remove tags from `ArtifactMetadata.to_dict()` |
| `skillmeat/api/services/artifact_cache_service.py` | 2 | Simplify tag read (1 location) |
| `skillmeat/api/routers/user_collections.py` | 2 | Simplify tag reads (4 locations) |
| `skillmeat/api/routers/artifacts.py` | 2 | Remove `metadata.tags` from response; fix dual write |
| `skillmeat/api/schemas/artifacts.py` | 3 | Remove `tags` from `ArtifactMetadataResponse` |
| `skillmeat/core/search.py` | 2 | Switch 3 tag reads to `artifact.tags` |
| `skillmeat/cli.py` | 2 | Fix 1 tag display |
| `skillmeat/web/lib/api/mappers.ts` | 4 | Remove merge logic |
| `skillmeat/web/lib/api/entity-mapper.ts` | 4 | Remove merge logic; remove tags from metadata interface |
| `skillmeat/web/components/shared/unified-card.tsx` | 4 | Fix legacy tag path |
| `skillmeat/web/lib/api/mappers.test.ts` | 4 | Update tag tests |
| `skillmeat/web/__tests__/lib/api/entity-mapper.test.ts` | 4 | Update tag tests |
| `tests/unit/test_artifact.py` | 5 | Update existing + add new tests |

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Tag storage locations (file-based) | 2 independent fields | 1 (Artifact.tags) |
| Merge/dedup code locations | 8+ (4 backend, 2 frontend, 2 tests) | 0 |
| Tag-related bugs | 7 identified inconsistencies | 0 |
| Lines of merge logic | ~40 lines across files | 4 lines in `__post_init__` |
| TOML tag sections per artifact | 2 (`tags` + `[metadata].tags`) | 1 (`tags`) |

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-03
**Status**: Draft -- ready for execution
