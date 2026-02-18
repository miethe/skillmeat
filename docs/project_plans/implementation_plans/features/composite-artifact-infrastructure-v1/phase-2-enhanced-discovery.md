---
title: "Phase 2: Enhanced Discovery (Graph-Aware Detection)"
description: "Update discovery layer to detect composite roots and return dependency graphs"
audience: [ai-agents, developers]
tags: [implementation, phase-2, discovery, detection, graph]
created: 2026-02-17
updated: 2026-02-17
category: "product-planning"
status: draft
related:
  - /docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md
---

# Phase 2: Enhanced Discovery (Graph-Aware Detection)

**Phase ID**: CAI-P2
**Duration**: 2-3 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect
**Estimated Effort**: 8 story points

---

## Phase Overview

Phase 2 extends the discovery layer to detect composite artifact roots (Plugins) and build in-memory dependency graphs. This phase:

1. Defines `DiscoveredGraph` dataclass to represent parent + children + linkage
2. Implements `detect_composites()` function with heuristic composite root detection
3. Updates `discover_artifacts()` to return `DiscoveredGraph` for composites, flat `DiscoveryResult` for atomic artifacts
4. Validates detection accuracy with comprehensive unit tests and fixture repos
5. Implements `composite_artifacts_enabled` feature flag for gradual rollout

The output of this phase feeds directly into Phase 3 (import orchestration) and Phase 4 (UI preview modal).

---

## Task Breakdown

### CAI-P2-01: Define DiscoveredGraph Dataclass

**Description**: Create a new `DiscoveredGraph` dataclass that represents the hierarchical discovery result for composite artifacts. This structure holds the parent artifact, all discovered children, and linkage metadata.

**Acceptance Criteria**:
- [x] `DiscoveredGraph` dataclass defined (likely in `skillmeat/core/discovery.py` or new module `skillmeat/core/discovery/models.py`)
- [x] Fields:
  - `parent: DiscoveredArtifact` — The composite artifact (e.g., Plugin)
  - `children: List[DiscoveredArtifact]` — All child artifacts found
  - `links: List[Dict[str, Any]]` — Metadata about parent-child relationships (e.g., `{"parent_id": "...", "child_id": "...", "relationship_type": "contains"}`)
  - `source_root: str` — The filesystem path where composite was detected
- [x] Dataclass is JSON-serializable (all fields use standard types or have custom serialization)
- [x] Docstring explains when `DiscoveredGraph` is returned vs `DiscoveryResult`
- [x] Can be instantiated without errors

**Key Files to Modify**:
- `skillmeat/core/discovery.py` (or new `skillmeat/core/discovery/models.py`) — Define `DiscoveredGraph`

**Implementation Notes**:
- `DiscoveredGraph` is separate from the existing `DiscoveryResult` — both may be returned from discovery
- For v1, all relationships use `relationship_type = "contains"` (others reserved for future)
- `links` can be simple dicts with parent_id, child_id, relationship_type keys
- Consider if graph structure should include depth/ordering information (may be needed for UI preview)

**Estimate**: 1 story point

---

### CAI-P2-02: Implement detect_composites() Function

**Description**: Create the core composite detection function that identifies composite roots and recursively discovers all children. Detection is heuristic-based with a false positive guard.

**Acceptance Criteria**:
- [x] Function signature: `detect_composites(root_path: str) -> Optional[DiscoveredGraph]`
  - Returns `DiscoveredGraph` if composite detected
  - Returns `None` if root is not a composite (caller should fall back to flat discovery)
- [x] Detection logic:
  - **Signal 1**: Presence of `plugin.json` in root directory (authoritative; parse permissive v1 schema with `name`, `version`, optional metadata)
  - **Signal 2**: Multiple distinct artifact-type subdirectories (e.g., `skills/` + `commands/` + `agents/`)
  - **False positive guard**: Require at least 2 distinct artifact-type subdirectories to qualify as composite (prevents single-skill repo being mis-classified)
- [x] Child discovery:
  - Recursively scan each artifact-type subdirectory (e.g., `skills/`, `commands/`)
  - For each subdirectory, find all atomic artifacts (using existing detection logic)
  - Return list of `DiscoveredArtifact` objects for all children
- [x] Depth limit:
  - Limit detection to first 3 directory levels (for performance on deep repos)
  - Document limit in docstring
- [x] Parent artifact creation:
  - Create a `DiscoveredArtifact` representing the Plugin itself
  - Source = `plugin.json` if present, else synthesized plugin metadata
  - Type = `PLUGIN`
- [x] Error handling:
  - Gracefully handle permission errors, missing directories
  - Return `None` for invalid paths (don't raise exceptions)
- [x] Docstring with examples of composite vs non-composite repos

**Key Files to Modify**:
- `skillmeat/core/discovery.py` — Implement `detect_composites()`
- `skillmeat/core/artifact_detection.py` — May add `PLUGIN` signature to `ARTIFACT_SIGNATURES` dict

**Implementation Notes**:
- Plugin root detection: Check for `plugin.json` using existing file-reading patterns
- `plugin.json` parsing should be schema-tolerant: unknown keys ignored, invalid schema falls back to heuristic path
- Artifact-type subdirectories: Use `ARTIFACT_SIGNATURES` from `artifact_detection.py` to identify valid types
- Recursive child detection: Leverage existing `detect_artifact()` function for each child
- Synthesis of plugin metadata: If no `plugin.json`, create reasonable defaults (e.g., name from repo name)
- Performance: Set reasonable limits (3 levels, max 1000 files scanned per composite)

**Estimate**: 2 story points

---

### CAI-P2-03: Update discover_artifacts() Integration

**Description**: Update the main `discover_artifacts()` function to call `detect_composites()` first and return the appropriate result type (`DiscoveredGraph` vs `DiscoveryResult`).

**Acceptance Criteria**:
- [x] Function signature unchanged: `discover_artifacts(source_url: str) -> Union[DiscoveryResult, DiscoveredGraph]` (or similar)
- [x] Flow:
  1. Normalize source (GitHub URL, local path, etc.)
  2. Clone/fetch repository content
  3. Call `detect_composites(root_path)` first
  4. If `DiscoveredGraph` returned → return it
  5. If `None` returned → fall back to existing flat discovery logic
- [x] Existing flat discovery tests pass (no regression)
- [x] Composite detection path is taken for plugins
- [x] Feature flag `composite_artifacts_enabled` gates new detection:
  - If flag disabled → always use flat discovery (even if composite detected)
  - If flag enabled → use new composite detection path
- [x] Telemetry/logging: Log when composite is detected, how many children found
- [x] Docstring updated with new behavior

**Key Files to Modify**:
- `skillmeat/core/discovery.py` — Update `discover_artifacts()` function
- `skillmeat/api/config.py` — Define `composite_artifacts_enabled` flag in API settings

**Implementation Notes**:
- Feature flag should default to `True` in dev/staging, can be toggled for gradual rollout
- Existing callers of `discover_artifacts()` need to handle both return types
  - Either change callers to handle `Union`, or
  - Create separate `discover_with_graphs()` function (simpler if callers are few)
- Logging should be structured (use `structlog` if available) with: `composite_detected`, `child_count`

**Estimate**: 2 story points

---

### CAI-P2-04: Composite Detection Unit Tests

**Description**: Write comprehensive unit tests for composite detection using a fixture set of real and synthetic repositories. Tests must validate true positive rate (actual composites detected) and false positive rate (flat repos not mis-classified).

**Acceptance Criteria**:
- [x] Test file: `tests/test_composite_detection.py`
- [x] Fixture repos in `tests/fixtures/composite_repos/`:
  - **True positives** (should be detected as composites):
    - `git-workflow-pro/` — Plugin.json + multiple artifact types
    - `dev-toolkit/` — Multiple skills + commands (no plugin.json)
    - `data-processing-suite/` — Skills + agents
  - **True negatives** (flat repos, should NOT be detected):
    - Single-skill repos (one skill, no other artifacts)
    - Single-command repos
    - Empty repos
    - Repos with unrelated subdirectories (docs/, tests/, src/)
  - **Edge cases**:
    - Repos with only one artifact type (should fail false positive guard)
    - Very deep repos (>3 levels deep)
    - Repos with permission errors
- [x] Test cases:
  - `test_detect_composites_with_plugin_json()` — Plugin.json present
  - `test_detect_composites_multiple_types()` — Multiple artifact types, no plugin.json
  - `test_detect_composites_single_type_not_composite()` — Only one artifact type (should return None)
  - `test_detect_composites_false_positives()` — 10+ flat repos should not trigger composite detection
  - `test_detect_composites_returns_correct_children()` — Correct children listed for known plugin
  - `test_detect_composites_depth_limit()` — Deep repos don't cause issues
  - `test_detect_composites_permission_error()` — Gracefully handle permission errors
  - `test_detect_composites_performance()` — Detection completes in <500ms for reasonable repos
- [x] Metrics:
  - True positive rate >90% on fixture set
  - False positive rate <5% on fixture set
  - Performance: <500ms average per repo
- [x] Code coverage >80% for detection code

**Key Files to Create/Modify**:
- `tests/test_composite_detection.py` — New test file
- `tests/fixtures/composite_repos/` — Fixture directory with test repos

**Implementation Notes**:
- Fixture repos can be minimal (just directories + marker files)
- Use pytest parametrize for testing multiple repos efficiently
- False positive guard validation is critical: ensure 2+ distinct types are required
- Performance test: use timer context manager, assert <500ms
- Consider data-driven tests: table of (repo_path, expected_composite?, expected_child_count)

**Estimate**: 2 story points

---

### CAI-P2-05: Feature Flag Integration

**Description**: Implement the `composite_artifacts_enabled` feature flag to gate the new composite detection path. This allows safe gradual rollout without breaking existing flat discovery.

**Acceptance Criteria**:
- [x] Feature flag defined: `composite_artifacts_enabled: bool` (default `True`)
- [x] Flag location: `skillmeat/api/config.py` (API runtime), with optional mirroring in `skillmeat/config.py` for CLI workflows
- [x] Can be toggled via:
  - Environment variable: `SKILLMEAT_COMPOSITE_ARTIFACTS_ENABLED=false`
  - Config file: `.env` (API) and optional `~/.skillmeat/config.toml` mirror for CLI flows
  - Runtime API (optional): Admin endpoint to toggle flags
- [x] When flag disabled:
  - `discover_artifacts()` uses flat discovery even if composite detected
  - `detect_composites()` is not called
  - Behavior is identical to pre-feature behavior
- [x] When flag enabled:
  - New composite detection path is active
  - Import orchestration uses graph-aware logic (Phase 3)
- [x] Tests verify flag behavior:
  - Test with flag=True → composite detected
  - Test with flag=False → flat discovery used
  - Test toggle at runtime

**Key Files to Modify**:
- `skillmeat/api/config.py` — Define flag with default value
- `skillmeat/config.py` (optional) — Mirror flag for CLI-consumed config when needed
- `skillmeat/core/discovery.py` — Check flag before calling `detect_composites()`
- Tests — Verify flag behavior

**Implementation Notes**:
- Flag should be checked at the top of `discover_artifacts()` before composite detection
- Default should be `True` (new behavior enabled by default in dev/staging)
- For production rollout, can start with `False` and gradually enable after validation
- Consider ConfigManager pattern if already used in codebase

**Estimate**: 1 story point

---

## Phase 2 Quality Gates

Before Phase 3 can begin, all the following must pass:

- [ ] `DiscoveredGraph` dataclass defined and can be instantiated
- [ ] `detect_composites()` detects known composite repos: `test_detect_composites_with_plugin_json()` passes
- [ ] False positive guard works: Single-artifact repos return `None`
- [ ] False positive rate <5%: `test_detect_composites_false_positives()` validates 10+ repos
- [ ] Child discovery correct: `test_detect_composites_returns_correct_children()` passes
- [ ] Feature flag gates behavior: flag disabled → flat discovery, flag enabled → composite detection
- [ ] Existing flat discovery tests pass: `pytest tests/test_discovery.py -v` passes (no regression)
- [ ] Performance acceptable: Detection <500ms for typical repos
- [ ] Code coverage >80% for discovery code: `pytest --cov=skillmeat.core.discovery --cov-report=term-missing`

---

## Implementation Notes & References

### Composite Root Detection Logic

**Heuristic**:
1. Check for `plugin.json` in root → if present, assume composite (authoritative)
2. Check for multiple distinct artifact-type subdirectories (e.g., `skills/` AND `commands/`)
3. **False positive guard**: Require at least 2 distinct types (single-skill repos are not composites)

**Pseudocode**:
```python
def detect_composites(root_path):
    # Check for plugin.json
    if os.path.exists(os.path.join(root_path, "plugin.json")):
        return build_graph_with_plugin_json(root_path)

    # Check for multiple artifact-type subdirectories
    found_types = set()
    for artifact_type in ARTIFACT_SIGNATURES:
        type_dir = os.path.join(root_path, f"{artifact_type}s")  # skills/, commands/, etc.
        if os.path.isdir(type_dir):
            found_types.add(artifact_type)

    # False positive guard: need 2+ distinct types
    if len(found_types) >= 2:
        return build_graph_from_subdirs(root_path, found_types)

    return None  # Not a composite, caller should use flat discovery
```

### Artifact-Type Subdirectories

- Skills: `skills/` (directory per skill)
- Commands: `commands/` (markdown files)
- Agents: `agents/` (markdown files)
- Hooks: `hooks/` (markdown files)
- MCP: `mcps/` or `mcp_servers/` (spec files)

Refer to `ARTIFACT_SIGNATURES` in `skillmeat/core/artifact_detection.py` for canonical list.

### Child Discovery

Leverage existing detection logic:
```python
for artifact_type in found_types:
    type_dir = os.path.join(root_path, f"{artifact_type}s")
    for entry in os.listdir(type_dir):
        artifact = detect_artifact(os.path.join(type_dir, entry))
        if artifact:
            children.append(artifact)
```

### Testing with Fixtures

Create minimal fixture repos:
```
tests/fixtures/composite_repos/
├── git-workflow-pro/
│   ├── plugin.json
│   ├── skills/
│   │   └── git-commit/
│   │       └── SKILL.md
│   └── commands/
│       └── git-push.md
├── single-skill-repo/
│   └── skills/
│       └── my-skill/
│           └── SKILL.md
└── empty-repo/
```

---

## Deliverables Checklist

- [ ] `DiscoveredGraph` dataclass defined in `skillmeat/core/discovery.py`
- [ ] `detect_composites()` function implemented with heuristic detection
- [ ] `discover_artifacts()` updated to handle both graph and flat results
- [ ] `composite_artifacts_enabled` feature flag defined and integrated
- [ ] Unit test file created with >40 test cases covering true positives, false positives, edge cases
- [ ] Fixture repos created in `tests/fixtures/composite_repos/`
- [ ] False positive rate validated <5%
- [ ] Performance validated <500ms per repo
- [ ] All Phase 2 quality gates passing
- [ ] Code reviewed and merged to main branch

---

**Phase 2 Status**: Ready for implementation
**Estimated Completion**: 2-3 days from Phase 1 completion
**Next Phase**: Phase 3 - Import Orchestration & Deduplication (depends on Phase 2 completion)
