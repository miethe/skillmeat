---
schema_version: "1.0"
doc_type: spike
title: "SPIKE: Composite Artifacts - Class Table Inheritance Refactor"
status: draft
created: 2026-02-20
updated: 2026-02-20
feature_slug: composite-class-table-inheritance
complexity: Large
estimated_research_time: "4 hours"
research_questions:
  - "How should composites be unified with the artifacts table?"
  - "What is the migration strategy for existing composite:name IDs?"
  - "Which services break today and which would auto-heal?"
  - "What frontend changes are required?"
---

# SPIKE: Composite Artifacts - Class Table Inheritance Refactor

**SPIKE ID**: `SPIKE-2026-02-20-COMPOSITE-CTI`
**Date**: 2026-02-20
**Author**: spike-writer (Opus orchestration)
**Related Request**: Composite tag sync failure (commit 0fa9b6d1), ongoing relational feature gaps
**Complexity**: Large

## Executive Summary

Composite artifacts (plugins, stacks, suites) currently live in a separate `composite_artifacts` table with `composite:name` IDs and **no row in the main `artifacts` table** at import time. This means relational features that join on `artifacts.uuid` (tags, groups, ratings, deployments, collection membership) do not work for composites without special-casing. We already have one such patch (tag sync skip in `artifacts.py:3066-3075`). This SPIKE recommends giving every composite a first-class row in the `artifacts` table (with `type = "composite"`) and retaining `composite_artifacts` as a detail/extension table, connected via a foreign key to the artifact's UUID. This is conceptually "joined table inheritance" though we recommend implementing it as a **manual FK join** rather than SQLAlchemy's built-in `__mapper_args__` inheritance, to avoid complexity and maintain backward compatibility.

## Research Scope and Objectives

### Questions Investigated

1. How are composites currently stored, queried, displayed, imported, and where do things break?
2. Should we use SQLAlchemy's built-in joined table inheritance (`__mapper_args__` with discriminator) or a manual FK relationship?
3. What is the migration strategy for existing data?
4. What patches and workarounds exist today that can be removed?
5. What frontend changes are needed?
6. Which services auto-heal vs. require explicit updates?

## Current State Analysis

### Storage Architecture

**Two parallel systems exist today:**

| Aspect | Regular Artifacts | Composite Artifacts |
|--------|-------------------|---------------------|
| **Primary table** | `artifacts` (PK: `id` = `type:name`, unique `uuid`) | `composite_artifacts` (PK: `id` = `composite:name`) |
| **Identity** | UUID (ADR-007) | String ID only, no UUID |
| **Project FK** | `project_id` -> `projects.id` | None (uses `collection_id` string) |
| **Relational features** | Tags, groups, ratings, collections, versions, deployments | Memberships only |
| **Collection join** | `collection_artifacts.artifact_uuid` -> `artifacts.uuid` | Direct `collection_id` field |

**Key observation**: The `_ensure_artifact_row()` function in `artifact_cache_service.py:82-124` **already creates an `Artifact` row** for composites during marketplace import. This means imported composites DO have an `artifacts` row (with `type="composite"`, a UUID, and `project_id="__collection_artifacts__"`). However, locally-created composites via `CompositeMembershipRepository.create_composite()` do NOT create an `Artifact` row -- they only create a `composite_artifacts` row.

### What Currently Works

- **Marketplace-imported composites**: Get both an `Artifact` row (via `_ensure_artifact_row`) and a `CompositeArtifact` row (via `_upsert_composite_artifact_row`). Tags are synced on the `Artifact` row. These composites appear in `collection_artifacts` and thus show up on the collection page.
- **Composite memberships**: `CompositeMembership` correctly references child artifacts by `artifacts.uuid`.
- **Frontend collection page**: Uses `useInfiniteCollectionArtifacts` and `useInfiniteArtifacts` hooks which query the collection_artifacts/artifacts endpoints. Composites that have `Artifact` rows (imported ones) show up with `type: "composite"` and `compositeType` field.
- **Frontend composite API**: Separate `/api/v1/composites` endpoint queries `composite_artifacts` table directly.

### What Breaks Today

| Feature | Broken For | Root Cause | Current Workaround |
|---------|-----------|------------|-------------------|
| **Tag sync** | All composites via parameter editor | `sync_artifact_tags()` needs `artifacts.uuid`; composites may not have one | Skip tag sync for `composite:*` IDs (`artifacts.py:3067-3069`) |
| **Group membership** | Locally-created composites | `group_artifacts.artifact_uuid` -> `artifacts.uuid` FK; no artifact row exists | None (silently fails) |
| **Ratings** | Composites | `user_ratings.artifact_id` uses string ID (not FK, but queries expect artifact existence) | None |
| **Deployments** | Composites | Deployment tracking references artifact identity | Manual path-based workaround |
| **Version tracking** | Composites | `artifact_versions` FK to `artifacts` | None |
| **Locally-created plugins** | All features | `create_composite()` in `CompositeMembershipRepository` only creates `composite_artifacts` row, not `artifacts` row | None |

### Existing Workarounds Identified

1. **Tag sync skip** (`skillmeat/api/routers/artifacts.py:3066-3075`): `if not artifact_id.startswith("composite:")` guards tag sync.
2. **ArtifactManager skip** (`skillmeat/api/services/artifact_cache_service.py:350-351`): "For composite artifacts, `artifact_mgr.show()` is skipped entirely because the ArtifactManager does not understand the composite type."
3. **CLI composite filter** (`skillmeat/cli.py:325-326`): `skip_regular = composite_filter` -- composites are queried separately from regular artifacts.
4. **Sharing bundle skip** (`skillmeat/core/sharing/bundle.py:515`): Composite children with no files are skipped.

## Options Analysis

### Option A: SQLAlchemy Built-in Joined Table Inheritance

Use SQLAlchemy's `__mapper_args__` with `polymorphic_on` discriminator on `Artifact.type` and have `CompositeArtifact` inherit from `Artifact`.

```python
class Artifact(Base):
    __tablename__ = "artifacts"
    type: Mapped[str] = mapped_column(String, nullable=False)
    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "skill",  # default
    }

class CompositeArtifact(Artifact):
    __tablename__ = "composite_artifacts"
    id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity": "composite",
    }
```

**Pros:**
- Clean ORM semantics; querying `Artifact` automatically includes composites
- SQLAlchemy handles the join transparently
- `isinstance(artifact, CompositeArtifact)` works naturally

**Cons:**
- **Breaking change to `CompositeArtifact.id` semantics**: Currently PK is `composite:name` (string), would need to become FK to `artifacts.id`. The `artifacts.id` is `type:name` format which matches.
- **Complex migration**: Must align existing `composite_artifacts.id` values with `artifacts.id` values, ensure every composite has an `artifacts` row first.
- **Polymorphic query overhead**: Every `Artifact` query gains a LEFT JOIN to `composite_artifacts`, even when composites are not needed.
- **Relationship conflicts**: `CompositeArtifact` currently has its own relationships (`memberships`) and fields (`collection_id`, `composite_type`) that don't map cleanly into the inheritance pattern.
- **Tight coupling**: Changes to `Artifact` base class ripple into `CompositeArtifact`.
- **`collection_id` mismatch**: `Artifact` has `project_id`; `CompositeArtifact` has `collection_id`. Inheritance assumes the child extends the parent, not replaces fields.

**Verdict**: Too invasive. The field-level mismatches (`project_id` vs `collection_id`, different PK conventions) make true inheritance awkward.

### Option B: Manual FK Join (Recommended)

Keep `composite_artifacts` as a separate detail table but add a required FK from `composite_artifacts` to `artifacts.uuid`. Ensure every composite has an `Artifact` row.

```python
class CompositeArtifact(Base):
    __tablename__ = "composite_artifacts"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # "composite:name"
    artifact_uuid: Mapped[str] = mapped_column(
        String, ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        nullable=False, unique=True
    )
    # ... existing fields remain unchanged

    # New relationship
    artifact: Mapped["Artifact"] = relationship("Artifact", foreign_keys=[artifact_uuid])
```

**Pros:**
- **Minimal schema disruption**: `composite_artifacts` keeps its PK and all existing fields.
- **All relational features work**: Tags, groups, ratings, collections, etc. already join on `artifacts.uuid`.
- **No polymorphic query overhead**: Regular artifact queries remain unchanged.
- **Backward compatible**: Existing code querying `composite_artifacts` directly still works.
- **Already partially implemented**: `_ensure_artifact_row()` already creates `Artifact` rows for imported composites.
- **Clean upgrade path**: Just need to ensure ALL composites (not just imported ones) get `Artifact` rows.

**Cons:**
- Two-table join when you need both artifact metadata and composite details (but this is explicit and controllable).
- Must remember to create `Artifact` row whenever creating `CompositeArtifact`.

**Verdict**: Recommended. Low risk, high value, builds on existing patterns.

### Option C: Merge Everything Into `artifacts` Table

Add composite-specific columns (`composite_type`, `metadata_json`) directly to `artifacts` and drop `composite_artifacts`.

**Pros:**
- Single table for everything; simplest query model.

**Cons:**
- Many nullable columns that only apply to composites.
- Loses the `composite_memberships.composite_id` -> `composite_artifacts.id` FK (would need a self-referencing FK on `artifacts`).
- Destroys existing composite-specific query patterns.
- Largest migration with most risk.

**Verdict**: Over-simplification that creates different problems.

## Recommended Approach: Option B (Manual FK Join)

### Design Details

#### Schema Changes

**1. Add `artifact_uuid` column to `composite_artifacts`:**

```sql
ALTER TABLE composite_artifacts ADD COLUMN artifact_uuid TEXT;
-- Populate from existing artifacts table
UPDATE composite_artifacts SET artifact_uuid = (
    SELECT uuid FROM artifacts WHERE artifacts.id = composite_artifacts.id
);
-- Create Artifact rows for any composites that lack one
-- Then make the column NOT NULL with UNIQUE constraint
```

**2. Add relationship from `CompositeArtifact` to `Artifact`:**

```python
class CompositeArtifact(Base):
    artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    artifact: Mapped["Artifact"] = relationship(
        "Artifact", foreign_keys=[artifact_uuid], lazy="joined"
    )
```

**3. Add reverse relationship on `Artifact`:**

```python
class Artifact(Base):
    composite_detail: Mapped[Optional["CompositeArtifact"]] = relationship(
        "CompositeArtifact",
        foreign_keys="[CompositeArtifact.artifact_uuid]",
        uselist=False,
        lazy="select",
    )
```

#### UUID Generation for Existing Composites

For composites that already have an `Artifact` row (marketplace imports), link the existing UUID. For composites created locally (via `create_composite()`), generate new `Artifact` rows during migration.

```python
# Migration pseudocode
for composite in composite_artifacts:
    existing = artifacts.get(id=composite.id)
    if existing:
        composite.artifact_uuid = existing.uuid
    else:
        new_uuid = uuid4().hex
        artifacts.insert(
            id=composite.id,
            uuid=new_uuid,
            project_id="__collection_artifacts__",
            name=composite.id.split(":", 1)[1],
            type="composite",
            description=composite.description,
        )
        composite.artifact_uuid = new_uuid
```

#### Service Layer Changes

**`CompositeMembershipRepository.create_composite()`**: Must also create/ensure an `Artifact` row. This is the primary fix -- consolidate the `_ensure_artifact_row()` pattern from `artifact_cache_service.py` into the repository layer.

**`artifact_cache_service.py`**: `_ensure_artifact_row()` and `_upsert_composite_artifact_row()` should be unified. After this change, `_upsert_composite_artifact_row` should set the `artifact_uuid` FK on the composite row.

### Migration Strategy

#### Phase 1: Schema Migration (Alembic)

1. Add nullable `artifact_uuid` column to `composite_artifacts`.
2. Data migration: For each `composite_artifacts` row, find or create matching `artifacts` row and populate `artifact_uuid`.
3. Add NOT NULL constraint and UNIQUE index on `artifact_uuid`.
4. Add FK constraint to `artifacts.uuid`.

**Rollback plan**: Drop the `artifact_uuid` column. The `artifacts` rows created for composites are harmless to leave in place (they have `type="composite"` which is already allowed).

#### Phase 2: Code Updates

1. Update `CompositeArtifact` model with new `artifact_uuid` column and relationship.
2. Update `CompositeMembershipRepository.create_composite()` to also create `Artifact` row.
3. Remove tag sync skip workaround (`artifacts.py:3066-3075`).
4. Update `artifact_cache_service.py` to set `artifact_uuid` on composite rows.

#### Phase 3: Frontend Alignment

Frontend changes are minimal because composites already show up in the collection page when they have `Artifact` rows. The key change is ensuring locally-created composites also appear uniformly.

### Backward Compatibility

- Existing queries against `composite_artifacts` continue to work (the table is unchanged except for the new column).
- Existing queries against `artifacts` gain composite rows (already the case for marketplace imports; this just makes it universal).
- The `composite:name` ID format is preserved.
- `CompositeMembership.composite_id` still references `composite_artifacts.id`.

## Impact Assessment

### Layer-by-Layer Impact

#### Database Layer (Medium Impact)

- **New column**: `composite_artifacts.artifact_uuid` (String, FK, NOT NULL, UNIQUE)
- **New relationship**: `CompositeArtifact.artifact` <-> `Artifact.composite_detail`
- **Data migration**: Create `Artifact` rows for composites that lack them
- **No table drops**: `composite_artifacts` and `composite_memberships` unchanged structurally
- **Migration complexity**: Moderate (data migration with FK creation)

#### Repository Layer (Medium Impact)

- **`CompositeMembershipRepository.create_composite()`**: Must create `Artifact` row first, then `CompositeArtifact` with `artifact_uuid`
- **`CompositeMembershipRepository.delete_composite()`**: CASCADE from `artifacts.uuid` will clean up `composite_artifacts`, `composite_memberships`, `artifact_tags`, `group_artifacts`, `collection_artifacts` automatically
- **New method**: Consider adding `get_composite_by_uuid()` for service-layer convenience

#### Service Layer (Low-Medium Impact)

| Service | Change Required | Impact |
|---------|----------------|--------|
| `TagService.sync_artifact_tags()` | None -- already works with `artifacts.uuid` | Auto-heals |
| `artifact_cache_service.populate_collection_artifact_from_import()` | Set `artifact_uuid` on composite row | Small update |
| `artifact_cache_service._ensure_artifact_row()` | Move to shared utility or repository method | Refactor |
| Group service | None -- `group_artifacts.artifact_uuid` already joins `artifacts.uuid` | Auto-heals |
| Rating service | None -- `user_ratings.artifact_id` uses string ID, composites already have `artifacts.id` | Auto-heals |

#### API Layer (Low Impact)

- **Remove workaround**: `artifacts.py:3066-3075` tag sync skip can be deleted
- **Composite endpoints** (`/api/v1/composites`): No change needed (still query `composite_artifacts`)
- **Artifact endpoints** (`/api/v1/artifacts`): Composites already appear (they have `Artifact` rows); no change
- **Association endpoint** (`/api/v1/artifacts/{id}/associations`): Will work for composites once they have proper UUID

#### Frontend (Minimal Impact)

- **Collection page**: Already displays composites via `useInfiniteArtifacts` / `useInfiniteCollectionArtifacts`. No change needed.
- **Composite-specific UI**: `/api/v1/composites` endpoints remain unchanged. `useCreateComposite`, `useDeleteComposite`, etc. continue to work.
- **Plugin Members Tab**: Already queries memberships via composites API. No change.
- **Tag editing**: Will start working for composites once the workaround is removed. The parameter editor already passes tags; it was just being skipped.
- **Group assignment**: Will start working for composites once they have `artifacts.uuid` rows.
- **Rating**: May need minor frontend check if composites are currently excluded from the rating UI.

### Patch Cleanup Inventory

After this refactor, the following workarounds can be removed:

| Location | Lines | Description | Action |
|----------|-------|-------------|--------|
| `skillmeat/api/routers/artifacts.py` | 3067-3069 | `if not artifact_id.startswith("composite:")` tag sync skip | **Remove** |
| `skillmeat/api/services/artifact_cache_service.py` | 350-426 | Entire composite branch in `populate_collection_artifact_from_import()` | **Simplify** (still needs special handling for ArtifactManager.show(), but FK linking should be cleaner) |
| `skillmeat/cli.py` | 325-326 | `skip_regular = composite_filter` | **Review** (may still be needed for CLI listing behavior) |

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Data migration creates duplicate `Artifact` rows | High | Low | Migration checks for existing rows before creating; UNIQUE constraint on `composite_artifacts.artifact_uuid` prevents double-linking |
| CASCADE delete from `Artifact` removes composite data unexpectedly | High | Low | Only triggered when `Artifact` row is explicitly deleted; existing delete paths already handle this |
| Existing composite queries break due to new NOT NULL column | Medium | Low | Alembic migration populates column before adding constraint; no application downtime |
| Frontend caching shows stale data after migration | Low | Medium | Instruct users to clear browser cache or add cache-bust header after deployment |
| `CompositeMembership.composite_id` FK still points to `composite_artifacts.id` (not `artifacts.id`) | Low | Low | Acceptable; membership edge semantics are composite-specific, not artifact-generic |

## Success Criteria

- [ ] Every `CompositeArtifact` row has a corresponding `Artifact` row with valid UUID
- [ ] `composite_artifacts.artifact_uuid` FK is NOT NULL and UNIQUE with CASCADE
- [ ] Tag sync works for composites without any `startsWith("composite:")` guard
- [ ] Group assignment works for composites
- [ ] Locally-created plugins via `CreatePluginDialog` produce both `Artifact` and `CompositeArtifact` rows
- [ ] Marketplace-imported composites continue to work identically
- [ ] All existing E2E tests pass (`composite-artifacts.spec.ts`, `marketplace-composite-import.spec.ts`, `plugin-management.spec.ts`)
- [ ] Collection page displays composites identically before and after migration

## Effort Estimation

| Phase | Tasks | Estimated Effort | Assigned To |
|-------|-------|-----------------|-------------|
| **Phase 1: Migration** | Alembic migration with data backfill | 2-3 hours | `data-layer-expert` |
| **Phase 2: Model Updates** | Add `artifact_uuid` to `CompositeArtifact`, relationships | 1 hour | `python-backend-engineer` |
| **Phase 3: Repository Updates** | Update `create_composite()`, extract shared `_ensure_artifact_row` | 2 hours | `python-backend-engineer` |
| **Phase 4: Workaround Cleanup** | Remove tag sync skip, simplify cache service | 1 hour | `python-backend-engineer` |
| **Phase 5: Testing** | Migration test, integration tests for tag/group/composite flow | 2-3 hours | `python-backend-engineer` |
| **Phase 6: Frontend Validation** | Verify collection page, tag editor, group assignment | 1 hour | `ui-engineer-enhanced` |
| **Total** | | **9-13 hours** | |

**Confidence level**: High (builds on existing patterns; most infrastructure already exists).

## Dependencies and Prerequisites

- **Existing `Artifact` rows for composites**: Already created during marketplace import (`_ensure_artifact_row()`). Need to generalize this for local creation.
- **`type="composite"` in type constraint**: Already present in `check_artifact_type` constraint.
- **ADR-007 UUID column**: Already exists on `artifacts` table (added in migration `20260218_1000`).
- **No external service dependencies**: All changes are within the SkillMeat codebase.

## ADR Recommendation

**Recommended ADR**: "ADR-XXX: Composite Artifacts Use Manual FK Join to Artifacts Table"

**Key decision**: Use manual FK join (Option B) rather than SQLAlchemy built-in joined table inheritance (Option A), because:
1. Field-level mismatches between `Artifact` (project_id) and `CompositeArtifact` (collection_id) make true inheritance awkward.
2. Option B has minimal schema disruption and builds on existing patterns.
3. No polymorphic query overhead on regular artifact queries.
4. Backward compatible with all existing composite-specific code.

**ADR should be created**: Before implementation begins, as this is a fundamental data model decision.

## Implementation Checklist

### Database Layer
- [ ] Alembic migration: Add `artifact_uuid` column (nullable initially)
- [ ] Data migration: Create `Artifact` rows for composites lacking them
- [ ] Data migration: Populate `artifact_uuid` from matching `artifacts.uuid`
- [ ] Schema migration: Add NOT NULL, UNIQUE, FK constraints
- [ ] Verify CASCADE behavior (deleting Artifact cascades to CompositeArtifact)

### Model Layer
- [ ] Add `artifact_uuid` field to `CompositeArtifact` model
- [ ] Add `artifact` relationship on `CompositeArtifact`
- [ ] Add `composite_detail` relationship on `Artifact`
- [ ] Update `CompositeArtifact.to_dict()` to include `artifact_uuid`

### Repository Layer
- [ ] Extract `ensure_artifact_row()` to shared utility
- [ ] Update `CompositeMembershipRepository.create_composite()` to create `Artifact` row
- [ ] Update `CompositeMembershipRepository.delete_composite()` to handle cascade
- [ ] Update `artifact_cache_service._upsert_composite_artifact_row()` to set `artifact_uuid`

### API Layer
- [ ] Remove tag sync skip in `artifacts.py:3066-3075`
- [ ] Simplify composite branch in `populate_collection_artifact_from_import()`
- [ ] Verify `/api/v1/composites` endpoints still work

### Frontend Layer
- [ ] Verify collection page displays composites correctly
- [ ] Test tag editing for composites (should now work)
- [ ] Test group assignment for composites (should now work)
- [ ] Test plugin creation via `CreatePluginDialog`

### Testing
- [ ] Unit test: Migration creates correct `Artifact` rows
- [ ] Integration test: `create_composite()` produces both rows
- [ ] Integration test: Tag sync works for composites
- [ ] Integration test: Group assignment works for composites
- [ ] E2E: `composite-artifacts.spec.ts` passes
- [ ] E2E: `marketplace-composite-import.spec.ts` passes
- [ ] E2E: `plugin-management.spec.ts` passes

## Appendices

### A. Key File References

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `skillmeat/cache/models.py` | `Artifact` class | ~214-375 |
| `skillmeat/cache/models.py` | `CompositeArtifact` class | ~2905-3020 |
| `skillmeat/cache/models.py` | `CompositeMembership` class | ~3023-3152 |
| `skillmeat/cache/composite_repository.py` | All composite CRUD | Full file |
| `skillmeat/api/services/artifact_cache_service.py` | `_ensure_artifact_row()`, `_upsert_composite_artifact_row()`, composite branch | ~82-426 |
| `skillmeat/api/routers/artifacts.py` | Tag sync skip workaround | ~3066-3075 |
| `skillmeat/core/services/tag_service.py` | `sync_artifact_tags()` | ~413-428 |
| `skillmeat/web/lib/api/composites.ts` | Frontend composite API client | Full file |
| `skillmeat/web/app/collection/page.tsx` | Collection page with composite display | ~370-420, 649-654 |

### B. Existing Relational Models That Will Auto-Heal

Once composites universally have `Artifact` rows with UUIDs, these join tables work without code changes:

- `artifact_tags` (PK: `artifact_uuid`, `tag_id`) -- tags join on `artifacts.uuid`
- `group_artifacts` (PK: `group_id`, `artifact_uuid`) -- groups join on `artifacts.uuid`
- `collection_artifacts` (PK: `collection_id`, `artifact_uuid`) -- collections join on `artifacts.uuid`
- `composite_memberships` (PK: `collection_id`, `composite_id`, `child_artifact_uuid`) -- membership child references join on `artifacts.uuid`

The following use string IDs (not UUID FKs) and are already compatible:

- `user_ratings` (`artifact_id` is a string, not FK) -- works with `composite:name` string IDs

### C. Frontend Type Mapping

The frontend `Artifact` type already supports composites:

```typescript
// types/artifact.ts:173
compositeType?: 'plugin' | 'stack' | 'suite';

// lib/api/mappers.ts:288
const validTypes: ArtifactType[] = ['skill', 'command', 'agent', 'mcp', 'hook', 'composite'];

// lib/api/mappers.ts:370
...(response.composite_type && { compositeType: response.composite_type }),
```

No frontend type changes are required.
