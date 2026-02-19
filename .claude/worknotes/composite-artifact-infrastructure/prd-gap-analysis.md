# PRD Gap Analysis: Composite Artifact Infrastructure

**Author:** Gemini
**Date:** 2026-02-18

Based on a review of the attached PRD (`composite-artifact-infrastructure-v1.md`) against our design discussions, the document is **highly aligned** with the architectural vision we established. It correctly pivots from a "nested" model to a "relational" model and addresses the critical requirement of treating child artifacts as independent, deduplicated entities.

However, there are **three specific gaps** where the PRD could be tighter to fully realize the vision, particularly regarding legacy features and deployment specifics.

### ✅ Strong Alignment (What matches the vision)

1. **Relational Data Model:** The PRD correctly defines a many-to-many relationship via an `ArtifactAssociation` table (`CAI-001`), rather than using a simple parent ID column. This is the crux of the "composite" design.
2. **Deduplication Strategy:** `CAI-006` explicitly mandates SHA-256 content hashing to link existing artifacts rather than creating duplicates. This satisfies the "Smart Import" requirement.
3. **Versioning/Pinning:** `CAI-008` and `CAI-013` correctly address "Plugin Rot" by storing a `pinned_version_hash` and providing UI warnings if the installed version differs from the plugin's requirement.
4. **Extensibility:** `CAI-002` expands the `ArtifactType` enum to include `PLUGIN`, `STACK`, and `SUITE`, ensuring this isn't just for Claude Plugins but for any grouping paradigm.

### ⚠️ Gaps & Ambiguities (What needs refinement)

#### 1. Deployment Layout for Parent Metadata

**The Gap:** The PRD specifies how *child* artifacts are deployed (standard paths), but it is vague on where the **Parent Artifact's own files** (e.g., the `plugin.json` manifest, the plugin's `README.md`, or specific config files) land on the user's disk during deployment.
**The Risk:** If a plugin contains a `config.json` that the child skills rely on, and SkillMeat only deploys the children (the skills), the plugin will break.
**Recommendation:** Add a requirement to `CAI-004` (Deployment Logic) specifying that Parent Artifact files must be deployed to a dedicated namespace (e.g., `.claude/plugins/{plugin_name}/`) to ensure shared configs/docs are available to the agent.
**Decision:** When a Composite Artifact is deployed, the target should be based on the 'type' of Composite (ie Plugin) and the platform profile (ie Claude Code), ie for Plugins in Claude Code, deploy to `.claude/plugins/{plugin_name}/` with the following structure. When just the child artifacts are deployed, nothing should change based on the current logic, as it is key that child artifacts are kept fully independent of the parent composites. Regarding Compose Types, see below addendum.

#### 2. Unification with "Bundles"

**The Gap:** Our design discussion noted: *"Future 'Bundles' will simply be an export of a 'Composite Artifact'. This unifies the concept of Sharing and Plugins."* The PRD treats Composites as a new database feature but doesn't explicitly link it to the existing "Export Bundle" feature.
**The Risk:** We might end up with two competing concepts: "Bundles" (zip files) and "Composites" (database relationships).
**Recommendation:** Add a task in Phase 3 or 4 to update the `skillmeat export` command. It should be able to take a Composite Artifact ID and automatically generate a Bundle from its graph, rather than requiring the user to manually select files.
**Decision:** Follow the Recommendation to unify Bundles and Composites, ensuring that every Composite can be exported as a Bundle with a single command, while still enabling custom bundles to be created by users if they want to cherry-pick specific artifacts (we don't need to add any additional features around Bundles at this time, just ensure that Composites can be exported as Bundles).

#### 3. Discovery of "Loose" Parents

**The Gap:** `CAI-005` (Discovery integration) discusses building the graph. However, it doesn't explicitly handle the edge case where a user has *already* imported the child skills manually in the past, and *later* imports the Plugin.
**The Vision:** The system should ideally recognize, "Hey, you already have 4 of the 5 skills in this plugin."
**The Risk:** The import might fail or create confusion if it tries to re-import existing skills without explicitly acknowledging them as "Found in Library."
**Recommendation:** Refine `CAI-012` (Import Preview UI) to explicitly categorize children into three buckets: "New (Will Import)", "Existing (Identical Hash - Will Link)", and "Conflict (Different Hash - Needs Resolution)."
**Decision:** Follow Recommendation with caveat: in the case of Conflicts, the user should have the option to import as a new version (fork) of that existing artifact or to update the existing artifact using the merge functionality from the artifact Sync Status features, but the UI should make it clear that the existing artifact will be affected.

### Summary Recommendation

The PRD is **approved for implementation** following the integration of all recommended refinements per the Decision blocks and the below Addendum.

## Addenum: Composite Types

We need to include a concept of Composite Types, with the current default and only option being "Plugin". This enables the Composite Type to be flexible as a data structure while still encompassing the needs of the Plugin artifact type. This type will be an enum field which defines certain specifics about how the Composite should be treated, deployed, etc.
