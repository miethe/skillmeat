---
schema_version: '1.0'
doc_type: implementation_plan
title: Artifact Metadata Persistence & DB-Reset Resilience - Implementation Plan
status: completed
created: 2026-02-20
updated: '2026-02-20'
feature_slug: metadata-persistence
prd_ref: docs/project_plans/SPIKEs/SPIKE-artifact-metadata-persistence.md
plan_ref: null
scope: backend + storage layer
effort_estimate: 13 pts across 4 phases
priority: medium
risk_level: low
related_documents:
- docs/project_plans/SPIKEs/SPIKE-artifact-metadata-persistence.md
---
# Implementation Plan: Artifact Metadata Persistence & DB-Reset Resilience

## Executive Summary

Extend `collection.toml` to persist groups, group memberships, and tag definitions (colors/descriptions) that are currently DB-only. Add bidirectional write-through so web UI mutations persist to the filesystem and cache refresh recovers this data from the filesystem after a DB reset.

**Approach**: Bottom-up (dataclass -> storage -> write-through -> recovery)

**Key design decisions**:
- `collection.toml` is the filesystem home for collection-level organization (not `.skillmeat-deployed.toml`)
- DB remains the query cache for web UI -- no reads from TOML during normal web operation
- TOML is read only at startup/cache-refresh and written through on every mutation
- Performance impact: negligible (TOML write on group/tag mutations, ~1-5ms)

## Architecture: When File vs DB is Read

```
                    ┌──────────────┐
                    │ collection   │
                    │   .toml      │  ← Filesystem source of truth
                    └──────┬───────┘
                           │
              READ: startup + cache refresh ONLY
              WRITE: on every group/tag mutation (write-through)
                           │
                    ┌──────▼───────┐
                    │   DB Cache   │  ← Web UI query source
                    │  (SQLite)    │
                    └──────┬───────┘
                           │
              READ: every API request (normal operation)
              WRITE: every API mutation (before write-through)
                           │
                    ┌──────▼───────┐
                    │   Web UI     │
                    └──────────────┘
```

**Rules**:
1. **Normal web operation**: DB is the only read source. No TOML reads on API requests.
2. **Startup / cache refresh**: TOML is read and used to populate/reconcile DB rows.
3. **Mutations** (group CRUD, tag color changes): Write DB first, then write-through to TOML.
4. **CLI operations**: Continue reading/writing TOML directly (existing behavior).

This preserves current performance (DB reads are fast) while ensuring FS has a complete backup.

## Phase Overview

| Phase | Title | Effort | Agent | Details |
|-------|-------|--------|-------|---------|
| 1 | Schema Extension (Dataclass + ManifestManager) | 3 pts | python-backend-engineer | [Phase 1](#phase-1-schema-extension) |
| 2 | Write-Through from API Mutations | 5 pts | python-backend-engineer | [Phase 2](#phase-2-write-through) |
| 3 | FS → DB Recovery (Cache Refresh) | 3 pts | python-backend-engineer | [Phase 3](#phase-3-fs-db-recovery) |
| 4 | Testing & Validation | 2 pts | python-backend-engineer | [Phase 4](#phase-4-testing) |

**Critical path**: Phase 1 → Phase 2 → Phase 3 → Phase 4 (sequential)

---

## Phase 1: Schema Extension (Dataclass + ManifestManager)

**Goal**: Extend `Collection` dataclass and `ManifestManager` to read/write groups and tag definitions in `collection.toml`.

### Task Breakdown

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|---------------------|-----|
| MP-1.1 | Add `TagDefinition` dataclass | New dataclass in `collection.py` with `name`, `slug`, `color`, `description` fields | Dataclass exists with `to_dict()`/`from_dict()` | 0.5 |
| MP-1.2 | Add `GroupDefinition` dataclass | New dataclass in `collection.py` with `name`, `description`, `color`, `icon`, `position`, `members: List[str]` (artifact names) | Dataclass exists with `to_dict()`/`from_dict()` | 0.5 |
| MP-1.3 | Extend `Collection` dataclass | Add `tag_definitions: List[TagDefinition]` and `groups: List[GroupDefinition]` with `default_factory=list` | Fields present; `to_dict()`/`from_dict()` handle them; backward-compatible (old TOMLs without these sections parse fine) | 1.0 |
| MP-1.4 | Update `ManifestManager.read()` | Deserialize `[[tag_definitions]]` and `[[groups]]` sections from TOML | Old manifests without new sections return empty lists; new manifests parse correctly | 0.5 |
| MP-1.5 | Update `ManifestManager.write()` | Serialize new sections to TOML via `collection.to_dict()` | Written TOML includes `[[tag_definitions]]` and `[[groups]]` arrays; round-trip test passes | 0.5 |

### Key Files

| File | Change |
|------|--------|
| `skillmeat/core/collection.py` | Add `TagDefinition`, `GroupDefinition` dataclasses; extend `Collection.to_dict()`/`from_dict()` |
| `skillmeat/storage/manifest.py` | No direct changes needed (uses `Collection.to_dict()`/`from_dict()`) but verify round-trip |

### Enhanced `collection.toml` Schema

```toml
[collection]
name = "default"
version = "1.0.0"
created = "2026-02-20T00:00:00"
updated = "2026-02-20T00:00:00"

# Existing artifact entries (unchanged)
[[artifacts]]
name = "my-skill"
type = "skill"
source = "user/repo/my-skill"
version_spec = "latest"
resolved_sha = "abc123"
scope = "user"
aliases = ["ms"]
tags = ["backend", "auth"]

# NEW: Rich tag definitions
[[tag_definitions]]
name = "backend"
slug = "backend"
color = "#3B82F6"
description = "Server-side artifacts"

[[tag_definitions]]
name = "auth"
slug = "auth"
color = "#EF4444"
description = ""

# NEW: Group definitions with member lists
[[groups]]
name = "Authentication"
description = "Auth-related skills and agents"
color = "#10B981"
icon = "shield"
position = 0
members = ["jwt-auth", "oauth-handler", "session-manager"]

[[groups]]
name = "Data Layer"
description = "Database and caching artifacts"
color = "#6366F1"
icon = "database"
position = 1
members = ["db-migration", "cache-manager"]
```

### Design Notes

- **`members` uses artifact names** (not UUIDs) for human readability and portability. On DB recovery, names are resolved to UUIDs via the artifacts table.
- **Backward compatibility**: `from_dict()` defaults `tag_definitions` and `groups` to `[]` if missing from TOML. No migration needed for existing manifests.
- **Tag definitions are collection-scoped**: Colors/descriptions live here, not in SKILL.md frontmatter. SKILL.md carries tag names only (intrinsic to the artifact).

### Quality Gate

- [ ] `Collection.from_dict(Collection.to_dict(c))` round-trips perfectly for collections with groups and tag_definitions
- [ ] Old manifests (without new sections) parse without error
- [ ] New manifests serialize with correct TOML structure

---

## Phase 2: Write-Through from API Mutations

**Goal**: When groups or tag definitions are modified via the web UI, persist changes back to `collection.toml`.

### Task Breakdown

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|---------------------|-----|
| MP-2.1 | Create `ManifestSyncService` | New service in `skillmeat/core/services/manifest_sync_service.py` that reads current manifest, applies changes, and writes back atomically | Service exists with `sync_groups()` and `sync_tag_definitions()` methods | 1.5 |
| MP-2.2 | Wire group CRUD to write-through | After group create/update/delete in `groups.py` router, call `ManifestSyncService.sync_groups()` | Creating/updating/deleting a group updates `collection.toml` | 1.5 |
| MP-2.3 | Wire group-artifact membership to write-through | After add/remove artifact from group, call sync | Adding/removing artifacts from groups updates `members` list in TOML | 1.0 |
| MP-2.4 | Wire tag definition updates to write-through | After tag color/description update in `tags.py` router, call `ManifestSyncService.sync_tag_definitions()` | Changing tag color via UI updates `collection.toml` | 1.0 |

### `ManifestSyncService` Design

```python
class ManifestSyncService:
    """Write-through service: syncs DB state back to collection.toml."""

    def sync_groups(self, session: Session, collection_id: str) -> None:
        """Read all groups for collection from DB, write to manifest."""
        # 1. Query all Group rows for collection_id, ordered by position
        # 2. For each group, query GroupArtifact → Artifact to get member names
        # 3. Build List[GroupDefinition] from DB state
        # 4. Load manifest via CollectionManager
        # 5. Replace collection.groups with new list
        # 6. Save manifest via CollectionManager

    def sync_tag_definitions(self, session: Session, collection_id: str) -> None:
        """Read all tags from DB, write definitions to manifest."""
        # 1. Query all Tag rows (with color, description)
        # 2. Build List[TagDefinition] from DB state
        # 3. Load manifest via CollectionManager
        # 4. Replace collection.tag_definitions with new list
        # 5. Save manifest via CollectionManager
```

**Key design decisions**:
- **Full snapshot on every write**: Rather than incremental patches, we read all groups/tags from DB and write the full set. This is simpler and avoids drift.
- **Async-safe**: `ManifestManager.write()` already uses `atomic_write()`. The `CollectionManager` has an `RLock` for thread safety.
- **Performance**: A typical collection has <50 groups and <100 tags. Full snapshot + TOML serialization is ~1-5ms. Negligible compared to the DB transaction.
- **Error handling**: Write-through failures are logged but don't fail the API request. DB is authoritative during operation; TOML is a backup.

### Router Integration Pattern

```python
# In groups.py, after successful DB commit:
try:
    ManifestSyncService().sync_groups(session, collection_id)
except Exception as e:
    logger.warning(f"Failed to sync groups to manifest: {e}")
    # Don't fail the request - DB is the operational source
```

### Key Files

| File | Change |
|------|--------|
| `skillmeat/core/services/manifest_sync_service.py` | NEW: Write-through sync service |
| `skillmeat/api/routers/groups.py` | Add sync calls after: create, update, delete, copy, reorder, add/remove artifacts |
| `skillmeat/api/routers/tags.py` | Add sync calls after: create, update, delete (for color/description changes) |

### Collection Resolution

The sync service needs to know which collection a group belongs to. Groups already store `collection_id` (FK to collections table). The service resolves collection_id → collection filesystem path via the `collections` table's `path` or `name` field, then loads the manifest from `~/.skillmeat/collections/<name>/collection.toml`.

### Quality Gate

- [ ] Creating a group via API → `collection.toml` contains new group entry
- [ ] Updating group name/color/description → TOML updated
- [ ] Adding/removing artifact from group → `members` list updated in TOML
- [ ] Deleting a group → removed from TOML
- [ ] Reordering groups → positions updated in TOML
- [ ] Changing tag color via API → `tag_definitions` updated in TOML
- [ ] Write-through failure doesn't crash the API request

---

## Phase 3: FS → DB Recovery (Cache Refresh)

**Goal**: When DB is reset and cache refresh runs, recover groups and tag definitions from `collection.toml`.

### Task Breakdown

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|---------------------|-----|
| MP-3.1 | Recover tag definitions on refresh | During cache refresh, read `tag_definitions` from manifest and create/update Tag ORM rows with colors | After DB reset + refresh, tags have correct colors from TOML | 1.0 |
| MP-3.2 | Recover groups on refresh | During cache refresh, read `groups` from manifest, create Group rows, resolve member names to artifact UUIDs, create GroupArtifact rows | After DB reset + refresh, groups and memberships are restored | 1.5 |
| MP-3.3 | Handle member resolution failures | If a group references an artifact name that doesn't exist in DB yet, skip that member with a warning | Partial recovery works; missing members logged | 0.5 |

### Recovery Flow (during `POST /cache/refresh` or startup)

```
1. Cache refresh populates artifacts from filesystem (existing behavior)
2. NEW: Read collection.toml → get tag_definitions and groups
3. NEW: For each tag_definition:
   a. Find or create Tag row by slug
   b. Update color/description if different
4. NEW: For each group:
   a. Find or create Group row by (collection_id, name)
   b. Update description/color/icon/position
   c. For each member name:
      - Resolve to artifact_uuid via Artifact table lookup
      - Find or create GroupArtifact row
   d. Remove GroupArtifact rows for members not in TOML list
```

### Integration Point

The recovery logic hooks into the existing refresh flow in `artifact_cache_service.py` or `cache/refresh.py`. It runs **after** artifact population (so artifacts exist for name → UUID resolution).

### Conflict Resolution

| Scenario | Resolution |
|----------|------------|
| Group exists in both DB and TOML | DB wins (TOML is backup, not override) |
| Group exists in TOML but not DB | Create from TOML (recovery case) |
| Group exists in DB but not TOML | Keep DB version (TOML may not have been written yet) |
| Tag color differs between DB and TOML | DB wins during normal operation; TOML wins during recovery (DB is empty) |

**Detection**: If DB has zero groups for a collection but TOML has groups, that's a recovery scenario. If DB already has groups, skip TOML import (DB is authoritative).

### Key Files

| File | Change |
|------|--------|
| `skillmeat/api/services/artifact_cache_service.py` | Add `recover_collection_metadata()` called after artifact population |
| `skillmeat/cache/refresh.py` | Call recovery after `populate_artifacts()` |

### Quality Gate

- [ ] Delete `cache.db` → restart API → refresh → groups restored from TOML
- [ ] Delete `cache.db` → restart API → refresh → tag colors restored from TOML
- [ ] Group with member referencing non-existent artifact → warning logged, other members still added
- [ ] Existing DB with groups → refresh does NOT overwrite from TOML

---

## Phase 4: Testing & Validation

**Goal**: Comprehensive tests for the new persistence layer.

### Task Breakdown

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|---------------------|-----|
| MP-4.1 | Unit tests for dataclasses | Test `TagDefinition`, `GroupDefinition` round-trip serialization; backward-compat with old manifests | Tests pass for new dataclasses and old TOML format | 0.5 |
| MP-4.2 | Unit tests for ManifestSyncService | Test sync_groups and sync_tag_definitions with mock DB sessions | Full coverage of sync logic | 0.5 |
| MP-4.3 | Integration test: write-through | Create group via API → verify TOML updated → delete DB → refresh → verify group restored | Full round-trip works end-to-end | 0.5 |
| MP-4.4 | Integration test: backward compatibility | Load old-format `collection.toml` (no tag_definitions/groups) → verify no errors | Old manifests still work | 0.5 |

### Key Test Files

| File | Tests |
|------|-------|
| `tests/test_collection.py` (or new) | Dataclass serialization, backward compat |
| `tests/test_manifest_sync.py` (new) | Write-through service |
| `tests/test_metadata_recovery.py` (new) | DB reset → recovery flow |

### Quality Gate

- [ ] All new tests pass
- [ ] No regressions in existing tests
- [ ] `pytest -v --cov=skillmeat` shows coverage for new code

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| TOML write performance on large collections | Low | Low | Full snapshot is ~1-5ms for <100 groups; monitor |
| Thread safety during concurrent writes | Low | Medium | `CollectionManager` already has RLock; `ManifestManager.write()` uses atomic_write |
| Circular sync (write-through triggers refresh which triggers write-through) | Low | High | Recovery only runs when DB is empty for collection; write-through skips if called from recovery |
| Old manifest format breaks on new code | Low | High | `from_dict()` defaults missing keys to `[]`; tested in Phase 4 |
| Member name resolution fails (artifact renamed) | Medium | Low | Log warning, skip member; user can re-add via UI |

## Files Affected Summary

| File | Phase | Change Type |
|------|-------|-------------|
| `skillmeat/core/collection.py` | 1 | Modify (add dataclasses, extend Collection) |
| `skillmeat/storage/manifest.py` | 1 | Verify (may need minor adjustments for array serialization) |
| `skillmeat/core/services/manifest_sync_service.py` | 2 | NEW |
| `skillmeat/api/routers/groups.py` | 2 | Modify (add sync calls) |
| `skillmeat/api/routers/tags.py` | 2 | Modify (add sync calls) |
| `skillmeat/api/services/artifact_cache_service.py` | 3 | Modify (add recovery logic) |
| `skillmeat/cache/refresh.py` | 3 | Modify (call recovery after populate) |
| `tests/test_collection.py` | 4 | Modify or NEW |
| `tests/test_manifest_sync.py` | 4 | NEW |
| `tests/test_metadata_recovery.py` | 4 | NEW |

## Success Criteria

1. **Groups survive DB reset**: Delete cache.db → restart → refresh → all groups and memberships restored
2. **Tag colors survive DB reset**: Same flow, tag colors/descriptions restored
3. **No performance regression**: API response times unchanged for normal operations
4. **Backward compatible**: Existing collection.toml files (without new sections) continue to work
5. **Dev environment bootstrapping**: New developer can get full organizational structure from shared collection.toml
