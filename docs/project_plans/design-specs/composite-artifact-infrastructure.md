# Design Doc: Generic Composite Artifacts (Relational Model)

**Status:** Draft
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

We need to move from a parent-child foreign key (1:N) to an association table (N:M) to support shared dependencies.

### A. Database Schema (`skillmeat/cache/models.py`)

We introduce `ArtifactAssociation` to link artifacts. This table handles the "Plugin contains Skill" relationship.

```python
class ArtifactAssociation(Base):
    __tablename__ = "artifact_associations"

    parent_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), primary_key=True)
    child_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), primary_key=True)
    
    # Metadata about the link (e.g., is it a required core component or optional extra?)
    relationship_type: Mapped[str] = mapped_column(String, default="contains") 
    
    # Critical for versioning: Did this plugin assume a specific version of the child?
    pinned_version_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class Artifact(Base):
    # ... existing fields ...

    # Parent relationships (e.g., Plugins that contain this Skill)
    parent_associations: Mapped[List["ArtifactAssociation"]] = relationship(
        "ArtifactAssociation",
        foreign_keys=[ArtifactAssociation.child_id],
        backref="child"
    )

    # Child relationships (e.g., Skills contained in this Plugin)
    child_associations: Mapped[List["ArtifactAssociation"]] = relationship(
        "ArtifactAssociation",
        foreign_keys=[ArtifactAssociation.parent_id],
        backref="parent"
    )

```

### B. Artifact Types

Update `skillmeat/core/enums.py`. We add `PLUGIN` now, but the architecture supports future types.

```python
class ArtifactType(str, Enum):
    # Atomic Types
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    MCP = "mcp"
    HOOK = "hook"
    
    # Composite Types
    PLUGIN = "plugin" 
    # Future: STACK, SUITE, WORKFLOW

```

## 3. Discovery & Import Logic (Graph-Based)

The sourcing algorithm must change from "scanning a list" to "building a dependency graph."

### A. Detection Phase

When scanning a source (e.g., a GitHub repo):

1. **Root Detection:** Detect if the root (or a subfolder) matches a Composite signature (e.g., contains `plugin.json` or has multiple artifact subdirectories like `/skills` and `/commands`).
2. **Child Detection:** Recursively scan inside to find atomic artifacts.
3. **Graph Construction:**
* Create a `DiscoveredArtifact` for the Plugin. *Content includes only the plugin's specific files (README, config).*
* Create `DiscoveredArtifacts` for every child found.
* **Linkage:** In memory, store the discovered relationship: `Plugin -> [Child A, Child B]`.



### B. Import Phase (The "Smart" Import)

When the user clicks "Import" on a Plugin:

1. **Atomic Imports First:** The system iterates through all children.
* **Hash Check:** Calculate the SHA-256 of the child.
* **Deduplication:** * *Scenario A (Exact Match):* If an artifact with this content hash exists, use the existing ID.
* *Scenario B (Variation):* If an artifact with this *name* exists but a *different hash* (version drift), create a new `ArtifactVersion` or a new artifact entry (depending on user preference for forking vs. updating).
* *Scenario C (New):* Create the new artifact.




2. **Parent Import:** Import the Plugin artifact itself (storing its specific docs/configs).
3. **Linkage Creation:** Write rows to `artifact_associations` linking the Plugin ID to the resolved Child IDs.

## 4. Versioning Strategy

Since a Plugin is a specific set of artifacts, versioning is critical to prevent "Plugin Rot" where a shared skill is updated for one plugin but breaks another.

1. **Pinning:** The `ArtifactAssociation` table includes `pinned_version_hash`.
2. **Deployment Logic:**
* When deploying `Plugin X`:
* Look up all children via `child_associations`.
* Check the `pinned_version_hash`.
* **Conflict Check:** If `Skill Y` is already deployed in the project with a hash *different* from the Plugin's pinned hash, warn the user.
* **Resolution:** Offer to side-by-side install (rename) or overwrite.





## 5. Storage & File Structure

We must strictly separate the Plugin's "Meta Files" from the Children's "Functional Files."

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

When deploying the Plugin, we re-assemble the structure virtually or physically based on the target platform's needs.

```text
.claude/
├── plugins/
│   └── git-workflow-pro/    <-- Contains only docs/metadata
├── skills/
│   └── git-commit/          <-- Deployed here, but SkillMeat knows it belongs to Plugin X
└── commands/
    └── git-push.md

```

## 6. Implementation Plan

### Phase 1: Core Relationships (Backend)

1. **Schema Migration:** Create `artifact_associations` table.
2. **Model Updates:** Update `Artifact` ORM to support the relationship.
3. **Versioning:** Ensure `ArtifactVersion` (from the existing codebase) is integrated so different versions of the same skill can coexist in the DB.

### Phase 2: Enhanced Discovery (Core)

1. **Recursive Scanner:** Update `heuristic_detector.py` to return a hierarchical result set, not just a flat list.
2. **Composite Logic:** Implement `detect_composites` which looks for grouping patterns (folders containing multiple valid artifact types).

### Phase 3: Import Orchestration (Core)

1. **Transaction Handler:** Ensure importing a Plugin wraps the import of all children in a single transaction.
2. **Deduplication Logic:** Implement the "Hash Check -> Link existing vs. Create new" logic defined in Section 3B.

### Phase 4: Web UI Updates

1. **Artifact Detail View:**
* Add "Contains" tab (for Parents) listing children.
* Add "Part of" section (for Children) listing parents.


2. **Import Modal:**
* When selecting a Plugin, UI should show: *"This will import 1 Plugin and 5 Child Artifacts (2 new, 3 existing)."*



## 7. Migration of Legacy "Bundles"

SkillMeat currently has a concept of "Bundles" (zip files for sharing). This new design creates a formal database structure for them.

* **Action:** Future "Bundles" will simply be an export of a "Composite Artifact" and all its children. This unifies the concept of "Sharing" and "Plugins."