
# ADR-008: Artifact Tiering and Composition Hierarchy

**Status:** Proposed
**Date:** 2026-03-10
**Deciders:** Lead Architect, Core Implementation Team
**Related Documents:** * `workflow-artifact-wiring-v1.md` (Replaces the "Tiering System Patch" section)
**Author:** Gemini 3.1 Pro

* `composite-artifact-infrastructure.md`
* `deployment-sets-v1.md`

## Context and Problem Statement

As the SkillMeat ecosystem has expanded beyond standard single-file tools (Commands, Agents) to include multi-resource packages (Plugins), complex state structures (Workflows, Context Modules), and recursive containers (Deployment Sets), the internal model for resolving dependencies and rendering the UI has grown ambiguous.

Initially, a temporary "Tiering System" conceptual patch was introduced within the `workflow-artifact-wiring-v1` PRD to explain how workflows sit above other artifacts. However, a formalized system-wide mental model and explicit relationship contract are required to manage graph dependencies, prevent circular references during deployments, and streamline the user interface.

## Decision

We will implement a strict, system-wide **4-Tier Artifact Hierarchy (Tiers 0 through 3)**. All artifacts known to SkillMeat will be classified into one of these tiers.

The core rule of this system is the **Downward Dependency Rule**: *An artifact may only contain, compose, or execute artifacts at its own tier or a lower tier.*

### The Tier Definitions

#### Tier 0: Atomic Primitives (The Leaf Nodes)

These are the foundational, indivisible building blocks of the platform. They provide raw data or isolated execution. They **cannot** contain or orchestrate other artifacts.

* **Compute / Execution:** `Agent`, `Command`, `Hook`, `MCP Server`
* **Knowledge / State:** `Context Entity` (rules, specs), `Memory Item` (decisions, gotchas)

#### Tier 1: First-Order Composites (The Structural Layer)

These entities exist primarily to organize, structure, or bundle Tier 0 primitives into logical, reusable units.

* **Compute Wrappers:** `Skill` (embeds its specific Commands, Agents, and Hooks), `Plugin` (explicit composite type mapping multiple standalone Tier 0 artifacts).
* **Context Wrappers:** `Context Module` (named groupings of Memory Items and Context Entities).
* **Organizational Wrappers:** `Template`, `Group`.

#### Tier 2: Recursive Aggregators (The Orchestration Scope)

Tier 2 artifacts act as "meta-containers." They bundle primitives (Tier 0) and composites (Tier 1), but crucially, they introduce **recursive** capabilities to map vast deployment footprints.

* **Deployment Orchestration:** `Deployment Set` (can contain Tier 0 artifacts, Tier 1 Groups, or other Tier 2 Deployment Sets to orchestrate atomic batch deployments).
* **Context Orchestration:** `Context Pack` (dynamically generated structures aggregating multiple Context Modules and active memories against a specific token budget).

#### Tier 3: Process & Distribution (The Top Level)

Tier 3 shifts the focus from *what* the artifacts are to *how* they are executed over time or transported across environments. They encapsulate the entire underlying graph.

* **Execution:** `Workflow` (defines multi-stage processes, binding Tier 0/1 execution tools to specific roles and injecting Tier 1/2 context into specific stages).
* **Distribution:** `Bundle` (`.skillmeat-pack` files serving as the ultimate deterministic export envelope containing a full graph of any lower-tier dependencies).

## Consequences

**Positive:**

1. **Dependency Resolution:** Circular dependencies are drastically reduced. If the parser sees a Tier 0 artifact attempting to declare a Tier 2 dependency, it will immediately fail validation.
2. **Simplified UI Architecture:** UI components can render consistent visual languages based on Tiers. For instance, deletion operations for Tier 2 and Tier 3 objects automatically imply cascading relationship warnings, whereas Tier 0 deletions are atomic.
3. **Deployment Safety:** Deployment logic knows that deploying a Tier 3 (Workflow) requires walking the tree down to Tier 0 to ensure all atomic prerequisites are satisfied before execution.

**Negative:**

1. **Migration Overhead:** We must retrofit existing data models (e.g., `ArtifactType` enums in `skillmeat/core/artifact_detection.py` and frontend TypeScript unions) to include a `tier` property.
2. **Strictness Constraints:** Edge cases that attempt to bypass the hierarchy (e.g., a Plugin trying to orchestrate a full Workflow) will now require deliberate refactoring into the correct Tier 3 model.

## Implementation Plan

1. **Remove the inline patch:** Strip the temporary tiering definitions out of `workflow-artifact-wiring-v1.md`.
2. **Backend Update:** Introduce an `ArtifactTier` Enum (`TIER_0`, `TIER_1`, `TIER_2`, `TIER_3`) into `skillmeat/core/enums.py` and map all existing `ArtifactType` values to their respective tier.
3. **Validation Engine:** Update `skillmeat/core/validation.py` to enforce the Downward Dependency Rule during import and association creation.
4. **Frontend Types:** Update `skillmeat/web/types/artifact.ts` to expose the Tier metadata, allowing the UI to group, filter, and warn users appropriately during destructive operations.