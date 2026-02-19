---
title: 'Implementation Plan: Tag Management Architecture Fix'
description: Fix artifact_tags FK pointing to wrong table (causing 0 counts), add
  tag rename/delete write-back to filesystem (collection.toml + SKILL.md frontmatter)
audience:
- ai-agents
- developers
tags:
- implementation
- refactor
- tags
- data-model
- write-back
created: 2026-02-04
updated: 2026-02-04
category: refactors
status: inferred_complete
complexity: Medium
total_effort: 8-12 hours
related:
- /docs/project_plans/implementation_plans/refactors/tag-storage-consolidation-v1.md
- /docs/project_plans/implementation_plans/enhancements/tags-refactor-v1.md
schema_version: 2
doc_type: implementation_plan
feature_slug: tag-management-architecture-fix
prd_ref: null
---
# Implementation Plan: Tag Management Architecture Fix

**Plan ID**: `IMPL-2026-02-04-TAG-MGMT-ARCH-FIX`
**Date**: 2026-02-04
**Author**: Claude Opus 4.5 (AI-generated)

**Complexity**: Medium
**Target Timeline**: Single PR

---

## Executive Summary

Two critical bugs on `/settings/tags` page plus a missing write-back path:

1. **All tags show 0 artifacts** — `artifact_tags.artifact_id` has a FK constraint pointing to `artifacts` table (project-scoped), but `sync_artifact_tags()` passes `"type:name"` format IDs from `collection_artifacts`. The FK validation always fails, so zero rows are inserted into `artifact_tags`.

2. **Tag rename/delete don't persist** — Mutations only touch the DB. On next cache refresh, old tags from SKILL.md frontmatter are re-created. No write-back path exists to update filesystem sources.

---

## Problem Analysis

### Bug 1: FK Mismatch on artifact_tags

Current model (`cache/models.py:1078`):
```python
artifact_id: Mapped[str] = mapped_column(
    String, ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True
)
```

The `artifacts` table contains project-scoped artifact records with UUID-style IDs. But `sync_artifact_tags()` in `tag_service.py:454` passes artifact IDs in `"type:name"` format (e.g., `"skill:canvas-design"`) — matching `collection_artifacts.artifact_id`, not `artifacts.id`.

Result: Every `add_tag_to_artifact()` call fails the existence check at `repositories.py:3382`:
```python
artifact = session.query(Artifact).filter_by(id=artifact_id).first()
if not artifact:
    raise RepositoryError(f"Artifact {artifact_id} not found")
```

### Bug 2: No Write-Back for Tag Mutations

When tags are renamed/deleted via the web UI:
1. `PUT/DELETE /api/v1/tags/{tag_id}` updates the DB `tags` table
2. On next cache refresh, `sync_artifact_tags()` re-reads tags from `collection.toml` / SKILL.md frontmatter
3. The old tag names still exist in filesystem, so they get re-created
4. Result: renames revert, deletes reappear

---

## Solution Design

### Phase 1: Fix Tag Counts (FK Migration)

Remove the FK constraint from `artifact_tags.artifact_id` (matching `collection_artifacts.artifact_id` pattern which also has no FK). Update repository validation to check `collection_artifacts` table instead of `artifacts`.

**Files**:
- `skillmeat/cache/models.py` — Remove FK from ArtifactTag, add SQLite table recreation in `create_tables()`
- `skillmeat/cache/repositories.py` — Fix `add_tag_to_artifact()` validation to query `CollectionArtifact`

#### Task 1.1: Remove FK from ArtifactTag model

In `cache/models.py` line 1078, change:
```python
artifact_id: Mapped[str] = mapped_column(
    String, ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True
)
```
To:
```python
artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
# No FK constraint — artifact_id uses "type:name" format from
# collection_artifacts, not project-scoped artifacts.id
```

#### Task 1.2: Add migration logic in create_tables()

After `Base.metadata.create_all(engine)` in `create_tables()` (line 2530), add logic to detect and remove the old FK constraint. Since SQLite doesn't support ALTER TABLE DROP CONSTRAINT, this requires:
1. Check if `artifact_tags` has the FK (inspect schema)
2. If so, rename old table, create new without FK, copy data, drop old

#### Task 1.3: Fix repository validation

In `repositories.py`, update `add_tag_to_artifact()` (line 3381):
```python
# Before:
artifact = session.query(Artifact).filter_by(id=artifact_id).first()
# After:
ca = session.query(CollectionArtifact).filter_by(artifact_id=artifact_id).first()
if not ca:
    raise RepositoryError(f"Artifact {artifact_id} not found in any collection")
```

Same fix for `remove_tag_from_artifact()` — remove the artifact existence check (it's not needed for removal, only the association needs to exist).

---

### Phase 2: YAML Frontmatter Writer Utility

**New file**: `skillmeat/utils/frontmatter_writer.py`

Utility to update specific fields in YAML frontmatter of markdown files without destroying content.

#### Task 2.1: Core frontmatter update function

```python
def update_frontmatter_field(file_path: Path, field_name: str, new_value: Any) -> bool:
    """Update a single field in a markdown file's YAML frontmatter."""
```

Uses existing `_FRONTMATTER_PATTERN` regex from `metadata.py`, `yaml.safe_load()` / `yaml.dump()`, and `atomic_write()` from `utils/filesystem.py`.

#### Task 2.2: Tag-specific helpers

```python
def rename_tag_in_frontmatter(file_path: Path, old_name: str, new_name: str) -> bool:
def remove_tag_from_frontmatter(file_path: Path, tag_name: str) -> bool:
```

---

### Phase 3: Tag Write-Back Service

**New file**: `skillmeat/core/services/tag_write_service.py`

#### Task 3.1: TagWriteService class

```python
class TagWriteService:
    def rename_tag(self, old_name, new_name, collection_manager, artifact_manager) -> dict
    def delete_tag(self, tag_name, collection_manager, artifact_manager) -> dict
```

Each method:
1. Loads collection.toml via ManifestManager
2. Finds all artifacts with the target tag
3. Updates artifact tags in collection.toml
4. Saves collection.toml
5. For each affected artifact, updates SKILL.md frontmatter via frontmatter_writer
6. Returns dict with affected artifact IDs

---

### Phase 4: Wire Tag Router to Write-Back Service

**File**: `skillmeat/api/routers/tags.py`

#### Task 4.1: Update DELETE endpoint

Add write-back before DB delete:
1. Look up tag name from DB
2. Call `TagWriteService.delete_tag()` to update filesystem
3. Call `TagService.delete_tag()` to delete from DB
4. Update `tags_json` on affected `CollectionArtifact` rows

#### Task 4.2: Update PUT endpoint

If request includes a name change:
1. Call `TagWriteService.rename_tag()` to update filesystem
2. Call `TagService.update_tag()` to update DB
3. Update `tags_json` on affected `CollectionArtifact` rows

Color-only changes skip filesystem writes.

---

### Phase 5: Cleanup and Verification

#### Task 5.1: Verify sync_artifact_tags works end-to-end
After Phase 1 fixes, confirm `artifact_tags` rows are populated and `get_all_tag_counts()` returns non-zero.

#### Task 5.2: Run tests
- `pytest` from project root
- Frontend typecheck/lint if tag schemas changed

---

## Files Summary

| File | Action | Phase |
|------|--------|-------|
| `skillmeat/cache/models.py` | Remove FK, add migration | 1 |
| `skillmeat/cache/repositories.py` | Fix validation | 1 |
| `skillmeat/utils/frontmatter_writer.py` | **NEW** | 2 |
| `skillmeat/core/services/tag_write_service.py` | **NEW** | 3 |
| `skillmeat/api/routers/tags.py` | Wire write-back | 4 |

## Risks

| Risk | Mitigation |
|------|-----------|
| SQLite table recreation may lose data | Currently empty table due to FK bug; add safety check |
| YAML formatting changes on round-trip | Use `yaml.dump(default_flow_style=False)`; test with real files |
| Race condition between web rename and CLI sync | Use `atomic_write()`; accept last-writer-wins |
| Artifact without SKILL.md frontmatter | Skip gracefully, only update collection.toml |

---

## Orchestration Quick Reference

### Batch 1: Fix Tag Counts (Phase 1)
```
Task("python-backend-engineer", "Task 1.1-1.3: Fix artifact_tags FK mismatch.
     Files:
       - skillmeat/cache/models.py (line 1078, remove FK constraint)
       - skillmeat/cache/models.py (line 2530, add migration logic)
       - skillmeat/cache/repositories.py (line 3381, fix validation)
     Changes:
       - Remove ForeignKey from ArtifactTag.artifact_id
       - Add SQLite table recreation logic in create_tables()
       - Update add_tag_to_artifact() to check collection_artifacts
       - Update remove_tag_from_artifact() to remove validation
     Reason: artifact_tags uses 'type:name' format from collection_artifacts, not artifacts.id")
```

### Batch 2: YAML Frontmatter Writer (Phase 2)
```
Task("python-backend-engineer", "Task 2.1-2.2: Create frontmatter writer utility.
     File: skillmeat/utils/frontmatter_writer.py (NEW)
     Functions:
       - update_frontmatter_field(file_path, field_name, new_value)
       - rename_tag_in_frontmatter(file_path, old_name, new_name)
       - remove_tag_from_frontmatter(file_path, tag_name)
     Pattern: Reuse _FRONTMATTER_PATTERN from metadata.py, yaml lib, atomic_write()
     Reason: Update tags in SKILL.md frontmatter without destroying content")
```

### Batch 3: Tag Write-Back Service (Phase 3)
```
Task("python-backend-engineer", "Task 3.1: Create TagWriteService.
     File: skillmeat/core/services/tag_write_service.py (NEW)
     Class: TagWriteService
     Methods:
       - rename_tag(old_name, new_name, collection_manager, artifact_manager)
       - delete_tag(tag_name, collection_manager, artifact_manager)
     Logic:
       1. Load collection.toml
       2. Find artifacts with target tag
       3. Update collection.toml
       4. Update SKILL.md frontmatter via frontmatter_writer
       5. Return affected artifact IDs
     Reason: Persist tag changes to filesystem sources")
```

### Batch 4: Wire Tag Router (Phase 4)
```
Task("python-backend-engineer", "Task 4.1-4.2: Wire tag router to write-back service.
     File: skillmeat/api/routers/tags.py
     Changes:
       - DELETE endpoint: Call TagWriteService.delete_tag() before DB delete
       - PUT endpoint: Call TagWriteService.rename_tag() for name changes
       - Update tags_json on affected CollectionArtifact rows
     Reason: Tag mutations must update filesystem, not just DB")
```

### Batch 5: Verification (Phase 5)
```
Task("python-backend-engineer", "Task 5.1-5.2: Verify and test.
     Actions:
       - Test sync_artifact_tags() end-to-end
       - Confirm artifact_tags rows populated
       - Confirm get_all_tag_counts() returns non-zero
       - Run pytest from project root
       - Frontend typecheck if schemas changed
     Reason: Ensure both bugs are fixed and no regressions")
```

---

## Implementation Notes

### FK Removal Context
The `collection_artifacts` table also has no FK constraint on `artifact_id`, establishing the pattern that `"type:name"` format IDs don't use FKs. This fix aligns `artifact_tags` with that pattern.

### Write-Back Design Decisions
- **collection.toml**: Source of truth for artifact tags (top-level manifest)
- **SKILL.md frontmatter**: Secondary source, read-only during sync
- **Last-writer-wins**: Race conditions between web UI and CLI sync accepted
- **Atomic writes**: Use existing `atomic_write()` to minimize corruption risk

### SQLite Migration Notes
SQLite doesn't support `ALTER TABLE DROP CONSTRAINT`, so removing the FK requires:
1. Create new table without FK
2. Copy data from old table
3. Drop old table
4. Currently, `artifact_tags` is empty due to FK bug, so data loss risk is minimal

### Future Enhancements (Not in Scope)
- Phase 6: Validate tag write-back in CLI `sync` command
- Phase 7: Add UI feedback for write-back failures
- Phase 8: Support tag rename cascading to all artifact types (commands, agents, MCP servers)

---

**Progress Tracking:**

See `.claude/progress/tag-management-architecture-fix-v1/` directory for phase-by-phase progress files

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-04
