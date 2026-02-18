# ADR-007: Internal UUID Identity for Artifacts

**Status**: Accepted
**Date**: 2026-02-18
**Decision Makers**: Lead Architect
**Related**: Composite Artifact Infrastructure PRD (`docs/project_plans/PRDs/features/composite-artifact-infrastructure-v1.md`), ADR-004 (Artifact Version Tracking)

---

## Context

SkillMeat identifies artifacts using a `type:name` string format (e.g., `skill:canvas-design`). This convention exists because of the dual-stack architecture: the filesystem is the CLI's source of truth, and `type:name` maps directly to filesystem paths (`skills/canvas-design/` → `skill:canvas-design`).

This works for display and lookups but creates problems for relational integrity:

### Identity Problems

1. **No FK constraints possible** — Join tables (`collection_artifacts`, `group_artifacts`, `artifact_tags`) store `artifact_id` as bare strings with no FK. The comment at `skillmeat/cache/models.py:1198-1199` explicitly documents this: "No FK constraint — artifact_id uses type:name format from collection_artifacts, not project-scoped artifacts.id".

2. **Rename fragility** — If an artifact is renamed, every `type:name` reference across all join tables becomes stale. No cascade mechanism exists.

3. **Cross-collection ambiguity** — `skill:canvas-design` in collection A vs collection B are different artifacts with the same string ID. The `collection_id` column disambiguates, but it's implicit and error-prone.

4. **No versioned identity** — The `type:name` string can't carry version information. The Composite Artifact Infrastructure needs `pinned_version_hash` as a separate column because the ID can't express "which version."

### Composite Artifact Infrastructure Pressure

The Composite Artifact Infrastructure PRD introduces `CompositeMembership`, a many-to-many relationship table linking composite artifacts (Plugins) to child artifacts. Without stable identity, this table would inherit all the problems above — no cascades, no referential integrity, silent data corruption on renames.

Notably, `ArtifactVersion` (models.py) already uses `uuid.uuid4().hex` for its PK with a proper FK to `artifacts.id`, proving the UUID pattern works within the codebase.

---

## Decision

**Introduce an internal UUID column on `CachedArtifact` as the stable identity for all relational references, while keeping `type:name` as the human-facing/filesystem-facing identifier.**

### Phase 1: Add UUID Column + Use in Composite Tables

#### 1. Add UUID Column to `CachedArtifact`

```python
class CachedArtifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Keep: type:name for lookups
    uuid: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, default=lambda: uuid.uuid4().hex, index=True
    )
    collection_id: Mapped[str] = mapped_column(String, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    artifact_name: Mapped[str] = mapped_column(String, nullable=False)

    # ... existing fields unchanged
    # (content_hash, deployment_status, metadata, cached_at, etc.)
```

**Migration Strategy**:
- Generate UUIDs for all existing `CachedArtifact` rows (non-null constraint)
- Add unique index on `uuid`
- Backfill any NULL values with `uuid.uuid4().hex`

#### 2. Write UUID Into `.skillmeat-deployed.toml`

During deployment, capture the UUID in the deployment manifest:

```toml
[[deployed]]
artifact_name = "canvas-design"
artifact_type = "skill"
artifact_uuid = "a1b2c3d4e5f6..."  # NEW: stable identity
from_collection = "default"
content_hash = "..."
```

This allows the filesystem to carry UUID identity for sync/export purposes.

#### 3. Write UUID Into `manifest.toml` in Collections

Collections carry artifact UUIDs for referential integrity:

```toml
[[artifacts]]
name = "canvas-design"
type = "skill"
uuid = "a1b2c3d4e5f6..."
path = "skills/canvas-design/"
origin = "github"
source_url = "https://github.com/anthropics/skills/tree/main/canvas-design"
```

#### 4. Use UUID in `CompositeMembership` with Real FK

The Composite Membership table uses UUID with proper FK constraint:

```python
class CompositeMembership(Base):
    __tablename__ = "composite_memberships"

    collection_id: Mapped[str] = mapped_column(String, primary_key=True)
    composite_id: Mapped[str] = mapped_column(
        ForeignKey("composite_artifacts.id", ondelete="CASCADE"), primary_key=True
    )
    child_artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
    )
    relationship_type: Mapped[str] = mapped_column(String, default="contains")
    pinned_version_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    membership_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship for eager loading
    child_artifact: Mapped["CachedArtifact"] = relationship(
        "CachedArtifact",
        foreign_keys=[child_artifact_uuid],
        lazy="joined"
    )
```

**Benefits**:
- Real FK constraint ensures referential integrity
- `ondelete="CASCADE"` automatically removes memberships when child is deleted
- SQLAlchemy can eager-load child artifacts
- No orphaned memberships possible

### API Surface

The external API continues to use `type:name` as the artifact identifier in URLs and response payloads:

```
GET /api/v1/artifacts/skill:canvas-design
POST /api/v1/composites/plugin:my-plugin/members
  {
    "child_artifact_id": "skill:canvas-design",  # Still type:name in API
    "pinned_version_hash": "abc123..."
  }
```

UUID is an internal DB concern. Service layer resolves `type:name` to UUID internally:

```python
# Service layer
def add_composite_member(
    collection_id: str,
    composite_id: str,
    child_artifact_id: str,  # type:name from API
    pinned_version_hash: Optional[str] = None
) -> CompositeMembership:
    # Resolve type:name to UUID
    child_artifact = artifacts_repo.get_by_id(child_artifact_id, collection_id)
    if not child_artifact:
        raise ArtifactNotFoundError(child_artifact_id)

    # Create membership using UUID
    membership = CompositeMembership(
        collection_id=collection_id,
        composite_id=composite_id,
        child_artifact_uuid=child_artifact.uuid,  # Use UUID for FK
        pinned_version_hash=pinned_version_hash
    )
    return membership
```

### Phase 2: Migrate Existing Join Tables (Future)

Migrate `collection_artifacts`, `group_artifacts`, and `artifact_tags` from `type:name` strings to UUID FK references:

```python
class ArtifactTag(Base):
    __tablename__ = "artifact_tags"

    collection_id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True
    )
    tag: Mapped[str] = mapped_column(String, primary_key=True)
```

Keep `type:name` as a unique lookup index on `CachedArtifact` for efficient lookups. This Phase 2 migration is deferred — Phase 1 delivers the value for Composite Artifacts without requiring a system-wide migration.

---

## Consequences

### Positive

1. **Real FK Constraints**: `CompositeMembership` has true referential integrity with cascading deletes
2. **Rename-Safe**: Changing an artifact's name doesn't break relationships (UUID is immutable)
3. **Collection-Safe**: UUID is globally unique, no cross-collection ambiguity
4. **Eager Loading**: SQLAlchemy relationships work correctly with proper FKs
5. **Proven Pattern**: `ArtifactVersion` already uses `uuid.uuid4().hex` PKs with FK to `artifacts.id`
6. **Filesystem Support**: UUID carried in both `.skillmeat-deployed.toml` and `manifest.toml`
7. **Incremental**: Phase 1 requires no changes to CLI or existing join tables

### Negative

1. **Migration Required**: Existing databases must generate UUIDs for all artifacts (one-time migration)
2. **Manifest Format Change**: `.skillmeat-deployed.toml` and `manifest.toml` gain new `uuid` field
   - Backward-compatible: field is additive; old code ignores it
3. **Service Layer Complexity**: API receives `type:name` → service resolves to UUID → DB queries by UUID
   - Mitigation: Lookup is indexed; performance impact negligible
4. **Phase 2 Debt**: Future migration of join tables touches many code paths
   - Mitigation: Phase 1 unblocks composite feature; Phase 2 is optional cleanup

### Neutral

1. **Storage Overhead**: UUID is 32 hex chars — negligible per row (~3KB per 1M artifacts)
2. **CLI Unchanged**: CLI continues using filesystem paths and `type:name`
3. **API Unchanged**: Consumers still see `type:name` in responses
4. **No Performance Impact**: UUID lookup indexed; comparable to string lookup

---

## Alternatives Considered

### Alternative A: UUID as Primary Key (Replace `type:name` Entirely)

Make UUID the PK on `CachedArtifact`, drop `type:name` as PK. All join tables use UUID FKs immediately.

**Pros**:
- Simpler long-term (single identity)
- No dual-column lookup logic
- Smaller indexes

**Cons**:
- Too invasive for Phase 1
- Requires updating every query in every service layer
- Requires updating every API endpoint
- Requires migrating all join tables simultaneously
- High risk of missing references
- Risk/reward ratio poor when additive UUID achieves same goal

**Rejected**: ADR explicitly defers this to Phase 2. Phase 1 gains full composite feature value with UUID FK without system-wide rewrite.

### Alternative B: Collection-Scoped Composite FK

Make `collection_artifacts` the FK target (composite PK of `collection_id + artifact_id`), have `CompositeMembership` reference that.

**Pros**:
- Uses existing join table structure
- No new column on `CachedArtifact`

**Cons**:
- Still string-based identity
- Still rename-fragile
- FK is on a join table rather than the entity itself
- Doesn't solve fundamental identity problem, adds indirection
- Repeats the same pattern as existing tables

**Rejected**: Compounds technical debt rather than addressing it.

### Alternative C: Composite UUID Scoped to Collection

Create UUID that includes collection ID (e.g., `{collection_id}:{uuid}`).

**Pros**:
- Slightly more semantic

**Cons**:
- Unnecessary complexity
- UUID is already globally unique
- Adds parsing logic
- Collection already stored in membership table

**Rejected**: Simple UUID is sufficient; collection is managed separately.

### Alternative D: Keep `type:name` Everywhere (Status Quo)

Don't add UUIDs. `CompositeMembership.child_artifact_id` stores `type:name` like all other join tables.

**Pros**:
- No migration
- No schema change

**Cons**:
- Repeats documented problems
- No cascading deletes on rename
- No referential integrity enforcement
- Comment at `models.py:1198` already documents FK limitation
- Composite feature forced to inherit the same limitations
- Silent data corruption risk on renames

**Rejected**: Adding composite table with known structural problems amplifies debt.

---

## Implementation Timeline

### Phase 1 (Composite Infrastructure Release)

- [ ] Add `uuid` column to `CachedArtifact` with migration
- [ ] Write UUID to `.skillmeat-deployed.toml` during deployment
- [ ] Write UUID to `manifest.toml` during collection sync
- [ ] Implement `CompositeMembership` with UUID FK
- [ ] Update service layer to resolve `type:name` → UUID
- [ ] Add UUID to `CachedArtifact` API responses (optional, for observability)
- [ ] Test cascading deletes on artifact removal

### Phase 2 (Post-Composite, TBD)

- [ ] Migrate `collection_artifacts` to UUID FK
- [ ] Migrate `group_artifacts` to UUID FK
- [ ] Migrate `artifact_tags` to UUID FK
- [ ] Drop `type:name` as PK (keep as unique index)
- [ ] Retire Phase 1 compatibility layer

---

## Data Flow Examples

### Adding a Child to a Composite

```
1. API receives:
   POST /api/v1/composites/plugin:my-plugin/members
   { "child_artifact_id": "skill:canvas-design", "pinned_version_hash": "abc123..." }

2. Service layer:
   - Resolve "skill:canvas-design" → look up in CachedArtifact by id
   - Fetch child_artifact.uuid = "a1b2c3d4e5f6..."
   - Create CompositeMembership with child_artifact_uuid="a1b2c3d4e5f6..."

3. DB:
   INSERT INTO composite_memberships (collection_id, composite_id, child_artifact_uuid, ...)
   - FK constraint ensures artifact with that UUID exists
   - If parent deleted: CASCADE removes membership
   - If child deleted: CASCADE removes membership

4. API response:
   { "child_artifact_id": "skill:canvas-design", ... }  # Still type:name to client
```

### Renaming an Artifact

```
1. CLI updates artifact directory: skills/old-name/ → skills/new-name/

2. Cache invalidation: CachedArtifact id changes from "skill:old-name" → "skill:new-name"

3. CompositeMembership relationship:
   - UUID unchanged: child_artifact_uuid = "a1b2c3d4e5f6..." (still points to same artifact)
   - FK constraint satisfied (UUID still exists)
   - No orphaned memberships
   - Query by UUID still works

4. Lookups:
   - Old id string "skill:old-name" no longer resolves (won't match any artifact)
   - But UUID-based queries find the artifact correctly
   - When composite loads members, it uses UUID FK (works perfectly)
```

### Syncing Collection With Upstream

```
1. Collection manifest lists artifacts with UUID:
   [[artifacts]]
   name = "canvas-design"
   type = "skill"
   uuid = "a1b2c3d4e5f6..."

2. Sync process:
   - Match artifact by UUID (not by name, in case renamed)
   - Update artifact metadata while keeping UUID stable
   - Composite memberships remain intact (UUID unchanged)

3. Result:
   - Artifact can be renamed without breaking composites
   - Memberships use immutable UUID identity
```

---

## Testing Strategy

### Unit Tests

```python
# Test UUID generation on insert
def test_cached_artifact_uuid_generation():
    artifact = CachedArtifact(
        id="skill:test",
        collection_id="default",
        artifact_type="skill",
        artifact_name="test"
    )
    session.add(artifact)
    session.commit()
    assert artifact.uuid is not None
    assert len(artifact.uuid) == 32  # hex format
    assert artifact.uuid.isalnum()

# Test UUID uniqueness
def test_uuid_uniqueness():
    artifact1 = CachedArtifact(id="skill:a", collection_id="default", ...)
    artifact2 = CachedArtifact(id="skill:b", collection_id="default", ...)
    session.add(artifact1)
    session.add(artifact2)
    session.commit()
    assert artifact1.uuid != artifact2.uuid

# Test FK constraint
def test_composite_membership_fk_constraint():
    # Create child artifact
    child = CachedArtifact(id="skill:child", collection_id="default", ...)
    session.add(child)
    session.commit()

    # Create composite and membership
    composite = CompositeArtifact(id="plugin:test", collection_id="default", ...)
    session.add(composite)
    session.commit()

    membership = CompositeMembership(
        collection_id="default",
        composite_id="plugin:test",
        child_artifact_uuid=child.uuid
    )
    session.add(membership)
    session.commit()

    # Verify FK is set
    assert membership.child_artifact_uuid == child.uuid
    assert membership.child_artifact.artifact_name == "child"

# Test cascading delete
def test_cascade_delete_on_child_removal():
    child = CachedArtifact(id="skill:child", collection_id="default", ...)
    session.add(child)
    session.commit()

    composite = CompositeArtifact(id="plugin:test", collection_id="default", ...)
    session.add(composite)
    session.commit()

    membership = CompositeMembership(
        collection_id="default",
        composite_id="plugin:test",
        child_artifact_uuid=child.uuid
    )
    session.add(membership)
    session.commit()

    # Delete child
    session.delete(child)
    session.commit()

    # Membership should be gone (cascaded)
    assert session.query(CompositeMembership).filter_by(
        child_artifact_uuid=child.uuid
    ).count() == 0
```

### Integration Tests

```python
# Test service layer resolve and create
def test_add_composite_member_resolves_type_name():
    # Create child artifact
    child = create_cached_artifact(
        id="skill:canvas-design",
        collection_id="default"
    )
    session.commit()

    # Create composite
    composite = create_composite_artifact(
        id="plugin:my-plugin",
        collection_id="default"
    )
    session.commit()

    # Add member using type:name
    service = CompositeArtifactService(session)
    membership = service.add_composite_member(
        collection_id="default",
        composite_id="plugin:my-plugin",
        child_artifact_id="skill:canvas-design",  # type:name input
        pinned_version_hash="abc123..."
    )

    # Verify UUID was resolved and stored
    assert membership.child_artifact_uuid == child.uuid
    assert membership.child_artifact.id == "skill:canvas-design"
```

---

## References

- **PRD**: `docs/project_plans/PRDs/features/composite-artifact-infrastructure-v1.md`
- **Related ADR**: ADR-004 (Artifact Version Tracking)
- **Models**: `skillmeat/cache/models.py` (line 1198, FK comment)
- **ArtifactVersion**: Existing UUID pattern in `skillmeat/cache/models.py`

---

## Approval Status

**Status**: Accepted
**Next Steps**:
1. Phase 1 implementation (integrated into CAI Phase 1 — `phase-1-core-relationships.md`)
2. Phase 2 implementation (CAI Phase 5 — `phase-5-uuid-migration.md`)
3. Final approval upon completion of Phase 5
