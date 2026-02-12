# Marketplace Import Cache Sync Analysis

**Date**: 2026-02-10
**Context**: Investigation of regression where marketplace imports fail to populate `description` and `source` linkage fields in DB cache
**Status**: Root cause identified, architectural recommendations provided

---

## Problem Statement

After importing an artifact from a Marketplace source (specifically the skill '1password'), the following fields are not populated in the web UI:

1. **Description field** — blank on both `/collection` (ArtifactDetailsModal) and `/manage` (ArtifactOperationsModal)
2. **Source linkage** — Source listed on Sources page but noted as "not having a source entry" and not clickable to navigate to source artifact

---

## Root Cause Analysis

### Three Import Code Paths Exist

| Code Path | File:Line | Creates DB Row | Populates Metadata |
|-----------|-----------|----------------|-------------------|
| **Batch import** (`POST /{source_id}/import`) | `marketplace_sources.py:~3716` | Bare row via `session.merge()` | Added `refresh_single_artifact_cache()` after (commit 9b7aca97) |
| **Single reimport** (`POST /{source_id}/reimport/{entry_id}`) | `marketplace_sources.py:~4046` | Bare row via `session.merge()` | **Never called** — this is why reimport fails |
| **Cache refresh** (periodic/manual) | `artifact_cache_service.py:~27` | Full create-or-update with metadata | Yes, from filesystem |

### The Core Architectural Problem

Import endpoints follow this pattern:

1. **Write metadata to filesystem** — `ImportCoordinator.import_entries()` writes manifest.toml with full metadata (description, upstream URL, origin, etc.)
2. **Create bare DB row** — `session.merge(CollectionArtifact(collection_id, artifact_id, added_at))` with only 3 fields
3. **Rely on separate cache refresh** — Batch import (after fix) calls `refresh_single_artifact_cache()`, which:
   - Re-reads the same metadata from filesystem
   - Updates the DB row with full metadata
   - Commits again

**Issues**:
- Reimport endpoint skips step 3 entirely
- Even with the fix, batch import does redundant filesystem I/O (write manifest → read manifest)
- Two DB round-trips per artifact (create bare row + commit, then update + commit)

### Why This Architecture Exists

The `refresh_single_artifact_cache()` function was designed as a **filesystem-to-DB sync mechanism** for periodic cache refreshes, not for import-time population. Import endpoints borrowed the "create bare row" pattern but forgot to add the refresh call.

---

## Data Flow Analysis

### What Metadata is Available at Import Time

| Field | Available from `ImportEntry`? | Available from filesystem? | Source |
|-------|------------------------------|---------------------------|--------|
| `description` | ✅ `entry.description` | ✅ `file_artifact.metadata.description` | Catalog entry (from SKILL.md frontmatter during source scan) |
| `source` (upstream URL) | ✅ `entry.upstream_url` | ✅ `file_artifact.upstream` | Catalog entry |
| `origin` | ✅ Known: `"marketplace"` | ✅ `file_artifact.origin` | Set during manifest update |
| `origin_source` | ✅ Known: `"github"` | ✅ `file_artifact.origin_source` | Set during manifest update |
| `tags_json` | ✅ `entry.tags` | ✅ `file_artifact.tags` | Catalog entry + approved path segments |
| `author` | ❌ | ✅ `file_artifact.metadata.author` | SKILL.md frontmatter only |
| `license` | ❌ | ✅ `file_artifact.metadata.license` | SKILL.md frontmatter only |
| `tools` | ❌ | ✅ `file_artifact.metadata.tools` | SKILL.md frontmatter only |
| `version` | ❌ | ✅ `file_artifact.metadata.version` | SKILL.md frontmatter only |
| `resolved_sha` | ❌ | ✅ `file_artifact.resolved_sha` | Git resolution during download |
| `resolved_version` | ❌ | ✅ `file_artifact.resolved_version` | Git resolution during download |
| `synced_at` | ❌ | ✅ Generated: `datetime.utcnow()` | Timestamp of sync |

**Summary**: `ImportEntry` provides ~60% of fields (description, source URL, origin, tags). Remaining fields (author, license, tools, version, resolved SHA/version) require reading the filesystem artifact.

### Current Flow (After Commit 9b7aca97)

```
┌─────────────────────────────────────────────────┐
│ POST /marketplace-sources/{id}/import           │
└──────────────────┬──────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────┐
│ ImportCoordinator.import_entries()              │
│ - Downloads artifact files from GitHub          │
│ - Writes manifest.toml with full metadata       │
│ - Returns ImportResult with ImportEntry[]       │
└──────────────────┬──────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────┐
│ Loop: Create bare CollectionArtifact rows       │
│ for entry in import_result.entries:             │
│   if entry.status == "success":                 │
│     association = CollectionArtifact(           │
│       collection_id="default",                  │
│       artifact_id=f"{type}:{name}",             │
│       added_at=utcnow(),                        │
│     )                                           │
│     session.merge(association)                  │
│ session.commit()  # ← First commit              │
└──────────────────┬──────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────┐
│ Loop: Refresh cache from filesystem (FIX)       │
│ for entry in import_result.entries:             │
│   if entry.status == "success":                 │
│     refresh_single_artifact_cache(              │
│       session, artifact_mgr, artifact_id        │
│     )                                           │
│     # Reads manifest.toml ← same file we wrote  │
│     # Updates CollectionArtifact with metadata  │
│     # session.commit() ← Second commit per item │
└──────────────────┬──────────────────────────────┘
                   │
                   v
                 Done
```

**Problems**:
1. Write manifest → read manifest (redundant I/O)
2. Create row + commit, then update row + commit (2 DB round-trips per artifact)
3. Reimport endpoint (`POST /{source_id}/reimport/{entry_id}`) still missing the refresh loop entirely

---

## Commits Applied

### Commit 9b7aca97 (2026-02-10)

**Title**: `fix(api): populate description and source linkage on marketplace import`

**Changes**:
1. `marketplace_sources.py`: Added `artifact_mgr: ArtifactManagerDep` to `import_artifacts()` signature, added refresh loop after bare row creation
2. `user_collections.py`: Added `origin`/`origin_source` mappings in all 3 response builder tiers (DB cache, file-based fallback, include_groups reconstruction)
3. `user_collections.py` schema: Added `origin: Optional[str]` and `origin_source: Optional[str]` to `ArtifactSummary`

**Status**: Fixes batch import path only. Reimport path still broken.

---

## Architectural Recommendations

### Option 1: Extract Shared Service Function (Recommended for Long-Term)

**Create new function** in `artifact_cache_service.py`:

```python
def create_or_update_collection_artifact(
    session: Session,
    collection_id: str,
    artifact_id: str,
    metadata: dict,
) -> CollectionArtifact:
    """Create or update CollectionArtifact with full metadata.

    Pure DB upsert - no filesystem reads, no manager dependencies.
    Sets synced_at = utcnow() automatically.

    Args:
        session: DB session
        collection_id: Collection ID (e.g., "default")
        artifact_id: Full artifact ID (e.g., "skill:1password")
        metadata: Dict with all metadata fields (description, source,
                  origin, origin_source, tags_json, author, etc.)

    Returns:
        CollectionArtifact ORM instance (committed)
    """
    assoc = (
        session.query(CollectionArtifact)
        .filter_by(collection_id=collection_id, artifact_id=artifact_id)
        .first()
    )

    metadata_with_timestamp = {
        **metadata,
        "synced_at": datetime.utcnow(),
    }

    if assoc:
        for key, value in metadata_with_timestamp.items():
            setattr(assoc, key, value)
    else:
        new_assoc = CollectionArtifact(
            collection_id=collection_id,
            artifact_id=artifact_id,
            added_at=datetime.utcnow(),
            **metadata_with_timestamp,
        )
        session.add(new_assoc)

    session.commit()
    return assoc or new_assoc
```

**Refactor `refresh_single_artifact_cache()`**:
```python
def refresh_single_artifact_cache(
    session: Session,
    artifact_mgr,
    artifact_id: str,
    collection_id: str = "default",
    deployment_profile_id: Optional[str] = None,
) -> bool:
    # ... validation ...

    # Read filesystem
    file_artifact = artifact_mgr.show(artifact_name)

    # Build metadata dict
    metadata = {
        "description": file_artifact.metadata.description if file_artifact.metadata else None,
        "author": file_artifact.metadata.author if file_artifact.metadata else None,
        # ... all other fields ...
    }

    # Delegate to shared function
    create_or_update_collection_artifact(
        session, collection_id, artifact_id, metadata
    )
    return True
```

**Refactor import endpoints**:
```python
# After ImportCoordinator.import_entries() returns
for entry in import_result.entries:
    if entry.status.value == "success":
        artifact_id = f"{entry.artifact_type}:{entry.name}"

        # Read filesystem artifact for full metadata
        file_artifact = artifact_mgr.show(entry.name)

        # Build metadata dict
        metadata = {
            "description": file_artifact.metadata.description if file_artifact.metadata else None,
            "source": getattr(file_artifact, "upstream", None),
            "origin": getattr(file_artifact, "origin", None),
            "origin_source": getattr(file_artifact, "origin_source", None),
            # ... all other fields from file_artifact ...
        }

        # Single DB operation
        create_or_update_collection_artifact(
            session, DEFAULT_COLLECTION_ID, artifact_id, metadata
        )
```

**Benefits**:
- Single DB round-trip per artifact (no bare row creation)
- Shared logic across all import paths and refresh
- Testable without filesystem dependencies
- Clear separation of concerns (DB upsert vs metadata extraction)

---

### Option 2: Minimal Fix (Fastest to Implement)

**Replace bare row creation with `refresh_single_artifact_cache()` call directly**:

```python
# BEFORE (current broken pattern):
association = CollectionArtifact(
    collection_id=DEFAULT_COLLECTION_ID,
    artifact_id=artifact_id,
    added_at=datetime.utcnow(),
)
session.merge(association)
session.commit()

# AFTER (minimal fix):
from skillmeat.api.services.artifact_cache_service import (
    refresh_single_artifact_cache,
)
refresh_single_artifact_cache(session, artifact_mgr, artifact_id)
```

**Apply to**:
1. Batch import endpoint (`marketplace_sources.py:~3716-3727`) — delete bare row loop, keep only refresh loop
2. Reimport endpoint (`marketplace_sources.py:~4046-4055`) — replace bare row with refresh call

**Benefits**:
- Minimal code change (delete + reuse existing function)
- Fixes both import paths immediately
- Leverages existing, tested `refresh_single_artifact_cache()` logic

**Drawbacks**:
- Still does redundant filesystem I/O (write manifest → read manifest)
- Still has per-artifact commits in refresh function

---

### Option 3: Hybrid Approach

**Keep `refresh_single_artifact_cache()` as-is** (for periodic/manual cache sync use cases), but create a lightweight **import-specific helper** that builds metadata from the `ImportEntry` + `artifact_mgr.show()` and upserts directly:

```python
def populate_collection_artifact_from_import(
    session: Session,
    artifact_mgr,
    collection_id: str,
    entry: ImportEntry,
) -> CollectionArtifact:
    """Populate CollectionArtifact from import result + filesystem.

    Optimized for import time - combines ImportEntry data with
    filesystem artifact metadata to minimize redundant I/O.
    """
    artifact_id = f"{entry.artifact_type}:{entry.name}"

    # Read filesystem for fields not in ImportEntry
    file_artifact = artifact_mgr.show(entry.name)

    # Combine ImportEntry data with filesystem data
    metadata = {
        "description": entry.description,  # From ImportEntry (already in memory)
        "source": entry.upstream_url,      # From ImportEntry
        "origin": "marketplace",           # Known at import time
        "origin_source": "github",         # Known at import time
        "tags_json": json.dumps(entry.tags),  # From ImportEntry
        # Read from filesystem for fields not in ImportEntry:
        "author": file_artifact.metadata.author if file_artifact.metadata else None,
        "license": file_artifact.metadata.license if file_artifact.metadata else None,
        "tools_json": json.dumps(file_artifact.metadata.tools) if file_artifact.metadata and file_artifact.metadata.tools else None,
        "version": file_artifact.metadata.version if file_artifact.metadata else None,
        "resolved_sha": getattr(file_artifact, "resolved_sha", None),
        "resolved_version": getattr(file_artifact, "resolved_version", None),
    }

    # Upsert
    return create_or_update_collection_artifact(
        session, collection_id, artifact_id, metadata
    )
```

**Benefits**:
- Avoids reading `description`, `tags`, `upstream_url` from filesystem (already in ImportEntry)
- Still gets complete metadata (author, license, tools, version from filesystem)
- Clean separation: `refresh_*` for sync, `populate_*` for import
- Single DB round-trip

---

## Recommendation Summary

| Option | Effort | Correctness | Performance | Maintainability |
|--------|--------|-------------|-------------|-----------------|
| **Option 1: Shared Service** | High | ✅ Best | ✅ Best (1 DB op) | ✅ Best (reusable, testable) |
| **Option 2: Minimal Fix** | Low | ✅ Good | ⚠️ Medium (2 DB ops, redundant FS I/O) | ⚠️ Medium (quick fix, not architectural) |
| **Option 3: Hybrid** | Medium | ✅ Best | ✅ Best (optimized for import) | ✅ Good (clear separation of concerns) |

**Recommended Path**:
1. **Immediate**: Apply **Option 2** to unblock reimport regression (fix reimport endpoint with `refresh_single_artifact_cache()` call)
2. **Next sprint**: Refactor to **Option 1** or **Option 3** for proper architecture

---

## Files Affected

### Current Fix (Commit 9b7aca97)
- `skillmeat/api/routers/marketplace_sources.py` (batch import only)
- `skillmeat/api/routers/user_collections.py` (response builders)
- `skillmeat/api/schemas/user_collections.py` (ArtifactSummary schema)

### Additional Files Needing Fix
- `skillmeat/api/routers/marketplace_sources.py:4046-4058` — Reimport endpoint (missing refresh call)

### Files for Architectural Refactor (Option 1/3)
- `skillmeat/api/services/artifact_cache_service.py` — New `create_or_update_collection_artifact()` or `populate_collection_artifact_from_import()` function
- `skillmeat/api/routers/marketplace_sources.py` — Both import endpoints refactored to use new service

---

## Testing Strategy

### Manual Testing
1. Delete existing imported artifact from collection
2. Import artifact from marketplace source
3. Verify in web UI:
   - Description appears in ArtifactDetailsModal (/collection page)
   - Description appears in ArtifactOperationsModal (/manage page)
   - Source is clickable/navigable on Sources tab
4. Reimport same artifact (delete + import again)
5. Verify all fields still populated correctly

### Automated Testing
- Add integration test for `POST /{source_id}/import` that verifies `CollectionArtifact.description`, `origin`, `origin_source`, `source` are populated
- Add integration test for `POST /{source_id}/reimport/{entry_id}` with same assertions
- Add unit test for new service function (Option 1/3) that verifies metadata dict correctly populates all fields

---

## Next Steps

1. **Decide**: Choose Option 2 (immediate) vs Option 1/3 (refactor)
2. **Implement**: Apply selected approach to reimport endpoint
3. **Test**: Manual verification with 1password skill or similar marketplace artifact
4. **Optional**: If Option 1/3 selected, refactor batch import to use new service as well
5. **Document**: Update CLAUDE.md data flow section if architecture changes significantly

---

## References

- Original issue report: User imported '1password' skill from marketplace, description blank, source not clickable
- Exploration findings: Session logs from `codebase-explorer` and `ultrathink-debugger` agents
- Commit 9b7aca97: Initial fix for batch import path
- Data flow principles: Root CLAUDE.md → "Data Flow Principles" section
