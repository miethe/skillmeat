# Design Doc: Generic Composite Artifacts (Relational Model)

**Status:** Draft (Revised 2026-02-18)
**Feature:** Composite Artifact Infrastructure
**Author:** Gemini
**Scope:** Core Architecture, Discovery, Import, Database

## 1. Executive Summary

We will implement a **Composite Artifact** system. Instead of rigid parent-child nesting, we will introduce a many-to-many relational structure.

A `Plugin` (or any future composite type like `Suite` or `Stack`) is defined as:

1. **Its own entity:** Containing its specific files (docs, configs, manifests).
2. **A set of relationships:** Links to other artifacts (Skills, Commands, Agents) that constitute its functionality.

This decoupling allows child artifacts to be first-class citizens—importable, versioned, and usable independently—while maintaining their association with the parent Plugin.

## 2. Data Model Architecture

We need a collection-scoped composite model to support shared dependencies while keeping atomic artifacts unchanged.

### A. Database Schema (`skillmeat/cache/models.py`)

We introduce a composite entity + membership metadata model. Membership handles the "Plugin contains Skill" relationship without mutating child artifact schema.

```python
from enum import Enum

class CompositeType(str, Enum):
    """Determines variant-specific behavior: deployment paths, storage layout, detection heuristics."""
    PLUGIN = "plugin"
    # Future: STACK = "stack", SUITE = "suite"

class CompositeArtifact(Base):
    __tablename__ = "composite_artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    collection_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    composite_type: Mapped[str] = mapped_column(String, default=CompositeType.PLUGIN.value)
    name: Mapped[str] = mapped_column(String, nullable=False)
    manifest_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class CompositeMembership(Base):
    __tablename__ = "composite_memberships"

    collection_id: Mapped[str] = mapped_column(String, primary_key=True)
    composite_id: Mapped[str] = mapped_column(
        ForeignKey("composite_artifacts.id", ondelete="CASCADE"), primary_key=True
    )
    # ADR-007: UUID FK enables real referential integrity, cascading deletes,
    # and rename-safe relationships. See docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md
    child_artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
    )

    # Metadata about the link (e.g., is it a required core component or optional extra?)
    relationship_type: Mapped[str] = mapped_column(String, default="contains")

    # Critical for versioning: Did this plugin assume a specific version of the child?
    pinned_version_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Optional JSON metadata for UI "Part of"/"Contains" context without child mutation
    membership_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship for eager loading child artifact data
    child_artifact: Mapped["CachedArtifact"] = relationship(
        "CachedArtifact",
        foreign_keys=[child_artifact_uuid],
        lazy="joined"
    )

```

### B. Artifact Types

Update `skillmeat/core/artifact_detection.py`. We add `COMPOSITE` as a deployable artifact type, and introduce a separate `CompositeType` enum to distinguish composite variants.

```python
class ArtifactType(str, Enum):
    # Atomic Types
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    MCP = "mcp"
    HOOK = "hook"

    # Composite Types
    COMPOSITE = "composite"

    @classmethod
    def composite_types(cls) -> list["ArtifactType"]:
        """Return all composite artifact types."""
        return [cls.COMPOSITE]

    @classmethod
    def deployable_types(cls) -> list["ArtifactType"]:
        """Return all types that can be deployed to a project.
        Includes COMPOSITE since composites are deployable (children go to
        standard locations, composite meta-files go to platform-specific paths).
        """
        return [cls.SKILL, cls.COMMAND, cls.AGENT, cls.MCP, cls.HOOK, cls.COMPOSITE]

class CompositeType(str, Enum):
    """Defines variant-specific behavior for composite artifacts.
    Each CompositeType determines: deployment structure, storage paths,
    detection heuristics, and CLI display behavior.
    """
    PLUGIN = "plugin"
    # Future: STACK = "stack", SUITE = "suite"

```

## 3. Discovery & Import Logic (Graph-Based)

The sourcing algorithm must change from "scanning a list" to "building a dependency graph."

### A. Detection Phase

When scanning a source (e.g., a GitHub repo):

1. **Root Detection:** Detect if the root (or a subfolder) matches a Composite signature (e.g., contains `plugin.json` or has multiple artifact subdirectories like `/skills` and `/commands`).
2. **Child Detection:** Recursively scan inside to find atomic artifacts.
3. **Graph Construction:**
* Create a `DiscoveredArtifact` for the Composite. *Content includes only the composite's specific files (README, config).*
* Create `DiscoveredArtifacts` for every child found.
* **Linkage:** In memory, store the discovered relationship: `Composite -> [Child A, Child B]`.



### B. Import Phase (The "Smart" Import)

When the user clicks "Import" on a Composite:

1. **Atomic Imports First:** The system iterates through all children.
* **Hash Check:** Calculate the SHA-256 of the child.
* **Deduplication:** * *Scenario A (Exact Match):* If an artifact with this content hash exists, use the existing ID.
* *Scenario B (Variation):* If an artifact with this *name* exists but a *different hash* (version drift), create a new `ArtifactVersion` or a new artifact entry (depending on user preference for forking vs. updating).
* *Scenario C (New):* Create the new artifact.



2. **Import Preview (3 Buckets):** Before executing, the UI presents:
* **New (Will Import):** Artifacts not found in the collection.
* **Existing (Identical Hash - Will Link):** Artifacts already present with matching content hash.
* **Conflict (Different Hash - Needs Resolution):** Artifacts with same name but different content. User can fork as new version or defer to merge functionality.

3. **Parent Import:** Import the Composite artifact itself (storing its specific docs/configs).
4. **Linkage Creation:** Write membership rows linking the Composite ID to resolved Child UUIDs (per ADR-007).

## 4. Versioning Strategy

Since a Composite is a specific set of artifacts, versioning is critical to prevent "Composite Rot" where a shared skill is updated for one composite but breaks another.

1. **Pinning:** The membership table includes `pinned_version_hash`.
2. **Deployment Logic:**
* When deploying `Composite X`:
* Look up children via `CompositeMembership` rows for that composite.
* Check each row's `pinned_version_hash`.
* **Conflict Check:** If `Skill Y` is already deployed in the project with a hash *different* from the Composite's pinned hash, warn the user.
* **Resolution:** Offer to side-by-side install (rename) or overwrite.

**Note:** Version conflict handling during import is deferred to a future enhancement. V1 surfaces conflicts in the import preview but does not implement inline resolution UI.

## 5. Storage & File Structure

We must strictly separate the Composite's "Meta Files" from the Children's "Functional Files."

### Collection Storage

```text
~/.skillmeat/collections/default/
├── plugins/
│   └── git-workflow-pro/    <-- The Parent Artifact
│       ├── plugin.json      <-- Config
│       └── README.md        <-- Documentation for the whole suite
├── skills/
│   └── git-commit/          <-- Child Artifact 1 (Imported independently)
└── commands/
    └── git-push.md          <-- Child Artifact 2 (Imported independently)

```

### Deployment Structure (.claude/)

When deploying the Composite, we re-assemble the structure virtually or physically based on the target platform's needs. In v1, this deploy path is supported for Claude Code; other platforms are deferred.

Deployment structure is platform-profile-specific. For Claude Code Plugins, composite non-artifact files (configs, manifests, docs, scripts) deploy to `.claude/plugins/{plugin_name}/`. Children deploy to their standard artifact locations.

```text
.claude/
├── plugins/
│   └── git-workflow-pro/    <-- Contains configs, manifests, docs, scripts
│       ├── plugin.json
│       └── README.md
├── skills/
│   └── git-commit/          <-- Deployed here, but SkillMeat knows it belongs to Composite X
└── commands/
    └── git-push.md

```

## 6. Implementation Plan

### Phase 1: Core Relationships (Backend)

1. **Schema Migration:** Create `composite_artifacts` + `composite_memberships` tables. Add UUID column to `CachedArtifact` per ADR-007 with unique index and backfill migration for existing rows.
2. **Model Updates:** Add `CompositeType` enum, composite entity + membership metadata models (atomic artifact schema remains unchanged). `CompositeMembership.child_artifact_uuid` uses real FK to `CachedArtifact.uuid`.
3. **Versioning:** Ensure `ArtifactVersion` (from the existing codebase) is integrated so different versions of the same skill can coexist in the DB.

### Phase 2: Enhanced Discovery (Core)

1. **Recursive Scanner:** Update `discovery.py` to return a hierarchical result set, not just a flat list.
2. **Composite Logic:** Implement `detect_composites` which looks for grouping patterns (folders containing multiple valid artifact types).

### Phase 3: Import Orchestration (Core)

1. **Transaction Handler:** Ensure importing a Composite wraps the import of all children in a single transaction.
2. **Deduplication Logic:** Implement the "Hash Check -> Link existing vs. Create new" logic defined in Section 3B. Leverage existing `Artifact.content_hash` and `ArtifactVersion.content_hash` fields for dedup rather than building parallel hashing.

### Phase 4: Web UI Updates + Bundle Export Unification

1. **Artifact Detail View:**
* Add "Contains" tab (for Parents) listing children.
* Add "Part of" section (for Children) listing parents.


2. **Import Modal:**
* When selecting a Composite, UI should show 3-bucket preview: "New (Will Import)", "Existing (Identical Hash - Will Link)", "Conflict (Different Hash - Needs Resolution)".

3. **Bundle Export Unification:**
* Update `skillmeat export` to export Composites as Bundles (zip including all children), unifying the legacy bundle concept with composite artifacts.


## 7. Migration of Legacy "Bundles"

SkillMeat currently has a concept of "Bundles" (zip files for sharing). This new design creates a formal database structure for them.

* **Action:** Future "Bundles" will simply be an export of a "Composite Artifact" and all its children. This unifies the concept of "Sharing" and "Plugins."
* **Phase 3 Task:** Phase 3 includes a task to update `skillmeat export` to export Composites as Bundles, unifying the two concepts. The `skillmeat export` command will detect composite artifacts and automatically include all child artifacts in the exported bundle zip, preserving membership metadata and pinned version hashes.
