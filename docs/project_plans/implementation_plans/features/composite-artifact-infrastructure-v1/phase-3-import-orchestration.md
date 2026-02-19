---
title: 'Phase 3: Import Orchestration & Deduplication'
description: Transactional smart import with SHA-256 dedup, version pinning, and API
  endpoint
audience:
- ai-agents
- developers
tags:
- implementation
- phase-3
- import
- deduplication
- transactions
- api
created: 2026-02-17
updated: '2026-02-18'
category: product-planning
status: completed
related:
- /docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md
schema_version: 2
doc_type: phase_plan
feature_slug: composite-artifact-infrastructure
prd_ref: null
plan_ref: null
---

# Phase 3: Import Orchestration & Deduplication

**Phase ID**: CAI-P3
**Duration**: 3-4 days
**Dependencies**: Phase 1 complete, Phase 2 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect
**Estimated Effort**: 14 story points

---

## Phase Overview

Phase 3 implements the core smart import logic that makes the Composite Artifact Infrastructure useful. This phase:

1. Leverages existing `Artifact.content_hash` and `ArtifactVersion.content_hash` (UNIQUE index) infrastructure for deduplication — no parallel hashing system
2. Implements SHA-256 content hash computation compatible with existing content_hash fields
3. Creates deduplication logic (hash lookup → link existing / new version / create new)
4. Wraps plugin import in a single database transaction for atomicity
5. Records `pinned_version_hash` in membership metadata at import time
6. Propagates composite membership metadata to project deployments (Claude Code in v1)
7. Implements plugin meta-file storage in collection filesystem
8. Creates API endpoint for querying associations
9. Provides integration tests for core import flows
10. Unifies bundle export with the Composite model via `skillmeat export`

> **Note**: Enhanced version conflict handling for same-name-different-hash scenarios is deferred to a future enhancement. For v1, this case defaults to `CREATE_NEW_VERSION`.

The output of this phase feeds directly into Phase 4 (UI implementation) and enables the full end-to-end import workflow.

---

## Task Breakdown

### CAI-P3-01: Content Hash Computation

**Description**: Implement SHA-256 hash computation for all artifact types. For directory-based artifacts (skills), compute tree hash; for file artifacts (commands), compute file hash.

> **Important**: Leverage existing `Artifact.content_hash` and `ArtifactVersion.content_hash` (which has a UNIQUE index). The `compute_artifact_hash()` function should produce hashes compatible with the existing content_hash fields. If the existing hashing algorithm is already SHA-256, reuse it directly.

**Acceptance Criteria**:
- [ ] Function: `compute_artifact_hash(artifact_path: str) -> str`
  - Returns 64-character hex SHA-256 hash
  - For directories: merkle-tree hash of all files (sorted by path)
  - For files: direct file hash
  - Consistent: same artifact always produces same hash
- [ ] Hash computation strategy:
  - **Skills (directories)**: Tree hash of all files in skill directory, excluding cache/metadata
  - **Commands/Agents/Hooks (files)**: Direct SHA-256 of file content
  - **MCP (spec files)**: SHA-256 of spec content
- [ ] Hash output compatible with existing `ArtifactVersion.content_hash` format
- [ ] Exclusions: Don't hash `.git/`, `node_modules/`, `.DS_Store`, temp files
- [ ] Deterministic: Same artifact hashed multiple times = same hash
- [ ] Unit tests:
  - Same artifact → same hash
  - Different content → different hash
  - Tree hash stable across directory reordering
  - Very large directories handled efficiently
- [ ] Performance: Hashing <1GB artifact completes in <5s

**Key Files to Modify**:
- `skillmeat/core/importer.py` or new `skillmeat/core/deduplication.py` — Add `compute_artifact_hash()`

**Implementation Notes**:
- Check existing code in `skillmeat/cache/models.py` — `ArtifactVersion` already has `content_hash` with UNIQUE index. Reuse existing algorithm if SHA-256.
- For skill tree hash, consider using `hashlib.sha256()` with sorted directory traversal
- For commands/agents/hooks, use `hashlib.file_digest()` or read+hash
- Document hash strategy in docstring for reproducibility
- Consider if existing code already has hashing (check `core/shared/` or `utils/`)

**Estimate**: 1 story point

---

### CAI-P3-02: Deduplication Logic

**Description**: Implement the three-scenario deduplication decision tree: exact match (link existing), name match with different hash (new version or fork), new artifact (create).

> **Note**: For v1, Scenario B (name match, different hash) defaults to `CREATE_NEW_VERSION`. Enhanced conflict resolution UI for this scenario is deferred to a future enhancement.

**Acceptance Criteria**:
- [ ] Function: `resolve_artifact_for_import(discovered: DiscoveredArtifact, content_hash: str) -> DeduplicationResult`
  - Returns enum: `LINK_EXISTING`, `CREATE_NEW_VERSION`, `CREATE_NEW_ARTIFACT`, `CONFLICT_NEEDS_USER_DECISION`
- [ ] Logic:
  - **Scenario A (Exact match)**: Query DB for artifact with same content hash
    - If found: Return `LINK_EXISTING` + existing artifact ID
    - Decision: Use existing artifact, don't create new row
  - **Scenario B (Name match, different hash)**: Query DB for artifact with same name but different hash
    - If found: Return `CREATE_NEW_VERSION` (v1 default; enhanced conflict resolution deferred)
    - Decision: Create new `ArtifactVersion` linked to existing artifact
  - **Scenario C (New)**: No name or hash match found
    - Return `CREATE_NEW_ARTIFACT`
    - Decision: Create new artifact row
- [ ] Database queries check against existing `Artifact.content_hash` and `ArtifactVersion.content_hash` fields — not a separate hash store:
  - Hash lookup: `SELECT * FROM artifact_versions WHERE content_hash = ?` (leverages UNIQUE index)
  - Name lookup: `SELECT * FROM artifacts WHERE name = ? AND type = ?`
  - Efficient queries with appropriate indexes
- [ ] Return type `DeduplicationResult`:
  ```python
  @dataclass
  class DeduplicationResult:
      decision: str  # LINK_EXISTING | CREATE_NEW_VERSION | CREATE_NEW_ARTIFACT | CONFLICT
      artifact_id: Optional[str]  # ID to link/version if decision is LINK_EXISTING
      reason: str  # Explanation for decision
  ```
- [ ] Unit tests covering all three scenarios

**Key Files to Modify**:
- `skillmeat/core/deduplication.py` (new) or `skillmeat/core/importer.py` — Add dedup logic

**Implementation Notes**:
- For v1, default "name match + different hash" to CREATE_NEW_VERSION (append to existing artifact's version history)
- Future: Add user choice in import preview modal to fork instead
- Name matching should be case-insensitive and handle common variations
- Keep dedup decisions deterministic (same input → same decision every time)
- Logging: Log each dedup decision with artifact name + hash for observability

**Estimate**: 2 story points

---

### CAI-P3-03: Transaction Wrapper for Plugin Import

**Description**: Wrap entire plugin import (all children + composite entity + membership metadata rows) in a single database transaction. If any child import fails, roll back completely (no partial imports).

**Acceptance Criteria**:
- [ ] Function: `import_plugin_transactional(discovered_graph: DiscoveredGraph, source_url: str) -> ImportResult`
- [ ] Flow:
  1. Begin database transaction
  2. For each child in graph:
     a. Compute content hash
     b. Run dedup logic → get decision
     c. Execute decision: link existing OR create new version OR create new artifact
     d. If any step fails → raise exception (triggers rollback)
  3. After all children resolved:
     a. Create composite entity row
     b. Write membership rows linking composite to all children
  4. Commit transaction
- [ ] Rollback on failure:
  - Any exception during import → automatic transaction rollback
  - No orphaned rows left in DB
  - Collection filesystem state reverted (temp dir pattern already established)
- [ ] Return type `ImportResult`:
  ```python
  @dataclass
  class ImportResult:
      success: bool
      plugin_id: str
      children_imported: int
      children_reused: int
      errors: List[str]
      transaction_id: str  # For observability
  ```
- [ ] Error handling:
  - Database errors → rollback + return error
  - File I/O errors → rollback + return error
  - Validation errors → rollback + return error
  - Don't swallow exceptions; let caller handle
- [ ] Integration tests:
  - Happy path: all children + composite entity created, memberships written
  - Rollback scenario: mid-import failure leaves DB clean
  - Dedup scenario: re-import updates memberships only, no duplicate child artifacts

**Key Files to Modify**:
- `skillmeat/core/importer.py` — Add `import_plugin_transactional()` function

**Implementation Notes**:
- Use SQLAlchemy session transaction context manager: `with session.begin_nested():`
- Ensure all database writes within transaction (repository methods should accept session parameter)
- Collection filesystem writes should use temp-dir + atomic move (already established pattern in codebase)
- Transaction ID: Generate UUID or use SQLAlchemy transaction ID for logging/debugging
- Performance: Import should complete within existing import time budget (~30s for reasonable plugins)

**Estimate**: 2 story points

---

### CAI-P3-04: Version Pinning (pinned_version_hash)

**Description**: Record the `pinned_version_hash` in membership metadata at the time the association is created (plugin import). This hash enables future conflict detection when deploying.

**Acceptance Criteria**:
- [ ] At import time (Phase 3-03):
  - When creating membership row, compute content hash of child artifact as it exists at import time
  - Store hash in membership `pinned_version_hash`
- [ ] Query/retrieval:
  - Repository method: `get_membership(composite_id, child_artifact_id) -> MembershipRecord`
  - Returns membership with `pinned_version_hash` populated
- [ ] Schema validation:
  - `pinned_version_hash` is 64-char hex string (or NULL for unversioned associations)
  - Index on `pinned_version_hash` for conflict detection queries
  - If `ArtifactVersion.content_hash` exists for the same child/version, mismatch is logged as validation warning
- [ ] Unit tests:
  - Association created with correct pinned hash
  - Hash retrieved correctly
  - Can query associations by pinned hash
- [ ] Future use (Phase 4):
  - On deploy, check if current child hash differs from pinned hash
  - Warn user if conflict detected

**Key Files to Modify**:
- `skillmeat/core/importer.py` — Compute and store hash at association creation
- `skillmeat/cache/repositories.py` — Ensure hash is returned in queries

**Implementation Notes**:
- Pinned hash represents the version of the child artifact that the plugin author intended
- Association-time hash is source of truth for membership pinning; compare against `ArtifactVersion.content_hash` when available
- Future: Support hash migration strategies (side-by-side, overwrite, abort) in Phase 4
- Logging: Log pinned hash for each association created

**Estimate**: 1 story point

---

### CAI-P3-05: Project Deployment Propagation (Claude Code v1)

**Description**: Propagate composite membership metadata to project deployment state so children retain parent composite context. In v1, plugin deployment behavior is supported for Claude Code only.

**Acceptance Criteria**:
- [ ] Deployment metadata propagation:
  - Composite deployment creates/updates project-scoped linkage metadata
  - Child artifacts retain parent composite context in project views/modals
- [ ] Claude Code deployment structure:
  - Child artifacts deploy to standard artifact locations (e.g., `.claude/skills/`, `.claude/commands/`)
  - Composite non-artifact files (plugin.json, README, etc.) deploy to `.claude/plugins/{plugin_name}/`
  - Non-Claude platforms return explicit unsupported response for plugin deploy in v1
- [ ] Plugin sync behavior:
  - Plugins stored at: `~/.skillmeat/collections/{collection}/plugins/<plugin-name>/`
  - Plugin meta-files (plugin.json, README) stored there
  - Children stored under their respective type directories (not nested under plugin)
- [ ] Tests:
  - Syncing plugins puts them in correct directory
  - Children are synced independently to standard locations
  - Composite non-artifact files land in `.claude/plugins/{plugin_name}/`
  - No recursion/nesting of plugin directories

**Key Files to Modify**:
- `skillmeat/core/sync.py` — Add deployment metadata propagation + platform gating

**Implementation Notes**:
- Plugins are "meta" entities that don't duplicate child artifact content
- Children are fully independent; linkage is metadata only
- Ensure project deployment APIs expose composite linkage metadata for the "Part of" modal/tab UX
- Enforce explicit platform gating for non-Claude plugin deployment

**Estimate**: 1 story point

---

### CAI-P3-06: Plugin Meta-File Storage

**Description**: Implement the `plugins/` directory structure in the collection filesystem for storing plugin-specific meta-files (plugin.json, README, docs, etc.).

**Acceptance Criteria**:
- [ ] Directory structure:
  ```
  ~/.skillmeat/collections/{collection}/plugins/
  └── git-workflow-pro/
      ├── plugin.json
      ├── README.md
      └── manifest.toml
  ```
- [ ] Plugin meta-files stored separately from children:
  - Plugin's own files in `plugins/<name>/`
  - Children stored in `skills/`, `commands/`, etc. (independent of plugin)
- [ ] At import time:
  - Extract plugin meta-files from source
  - Write to `plugins/<plugin-name>/` directory
  - Use atomic move (temp dir + rename) pattern
- [ ] Manifest registration:
  - Update collection manifest to register plugin artifact
  - Lock file updated with plugin version/SHA
- [ ] Tests:
  - Plugin files written to correct directory
  - Children written to their type directories
  - Manifest updated correctly

**Key Files to Modify**:
- `skillmeat/core/importer.py` — Write plugin meta-files to correct path
- `skillmeat/storage/manifest.py` (or similar) — Register plugin in manifest

**Implementation Notes**:
- Plugin directory name should match plugin artifact name (slugified)
- Use existing `AtomicFileWriter` or `safe_write_with_rollback()` pattern if available
- Ensure permissions are correct (user-readable, not world-readable)

**Estimate**: 1 story point

---

### CAI-P3-07: GET /artifacts/{id}/associations API Endpoint

**Description**: Create a new API endpoint that returns associations for a given artifact (both parents and children with relationship metadata).

**Acceptance Criteria**:
- [ ] Endpoint: `GET /api/v1/artifacts/{artifact_id}/associations`
- [ ] Response schema `AssociationsDTO`:
  ```python
  @dataclass
  class AssociationsDTO:
      artifact_id: str
      parents: List[AssociationItemDTO]  # Plugins that contain this artifact
      children: List[AssociationItemDTO]  # Children of this plugin

  @dataclass
  class AssociationItemDTO:
      artifact_id: str
      artifact_name: str
      artifact_type: str
      relationship_type: str  # "contains", "requires", etc.
      pinned_version_hash: Optional[str]
      created_at: datetime
  ```
- [ ] HTTP behavior:
  - 200 OK + DTO for valid artifact_id
  - 404 Not Found for unknown artifact_id
  - 401 Unauthorized if not authenticated (use existing auth middleware)
- [ ] Query parameters (optional):
  - `include_parents: bool` (default true)
  - `include_children: bool` (default true)
  - `relationship_type: str` (filter by type, default all)
- [ ] OpenAPI documentation:
  - Endpoint documented in OpenAPI spec
  - Request/response schemas defined
  - Examples provided
- [ ] Performance:
  - Responds in <200ms for plugins with up to 50 children
  - Query optimized with `joinedload()` or similar

**Key Files to Modify**:
- `skillmeat/api/routers/artifacts.py` — Add new endpoint
- `skillmeat/api/schemas/associations.py` (new) — Define DTOs
- `skillmeat/api/openapi.json` — Regenerated after endpoint addition

**Implementation Notes**:
- Use existing router pattern from `skillmeat/api/routers/artifacts.py`
- Leverage repository `get_associations()` method from Phase 1
- Return DTOs only (never return ORM objects)
- Include artifact metadata (name, type) in association items for UI convenience
- Test with Postman or curl; verify against OpenAPI spec

**Estimate**: 2 story points

---

### CAI-P3-08: Integration Tests (Import Orchestration)

**Description**: Write integration tests validating plugin import happy path, deduplication scenarios, rollback behavior, and API endpoint.

**Acceptance Criteria**:
- [ ] Test file: `tests/integration/test_plugin_import_integration.py`
- [ ] Happy path test:
  - Create test plugin with 3 children (skills + commands)
  - Call `import_plugin_transactional()` with discovered graph
  - Verify: plugin created, 3 children created, 3 associations created
  - Verify: all DB transactions committed
  - Verify: files written to collection filesystem
  - Verify: `pinned_version_hash` stored correctly for each child
- [ ] Deduplication test:
  - First import: 1 plugin + 3 children (all new)
  - Re-import same plugin second time
  - Verify: 0 new artifacts created (children reused)
  - Verify: associations still created/updated
  - Verify: `children_reused` counter = 3
- [ ] Rollback test:
  - Create test plugin import that will fail mid-way (mock failure in child 2 of 3)
  - Call `import_plugin_transactional()`
  - Verify: transaction rolled back
  - Verify: no plugin row created
  - Verify: child 1 artifact not created (or rolled back)
  - Verify: collection filesystem in pre-import state
- [ ] API endpoint test:
  - Create plugin + children
  - Call `GET /api/v1/artifacts/{plugin_id}/associations`
  - Verify: returns 200 with correct parent/child lists
  - Verify: pinned hashes included in response

**Key Files to Create/Modify**:
- `tests/integration/test_plugin_import_integration.py` — New integration test file
- `tests/conftest.py` — Add fixtures for test plugins/artifacts

**Implementation Notes**:
- Tests should use real DB (SQLite in-memory or test PostgreSQL container)
- Fixtures: Create minimal valid plugins with real artifact files
- Mock filesystem I/O carefully (use actual temp dirs, don't mock)
- Timing: Tests may take 5-10 seconds due to transaction overhead; document this
- Coverage: Aim for >90% coverage of import path

**Estimate**: 2 story points

---

### CAI-P3-09: Observability (OpenTelemetry, Metrics, Structured Logging)

**Description**: Add OpenTelemetry instrumentation for all key operations: composite detection, hash computation, deduplication decision, import transaction, association write. Also add structured logging and metrics.

**Acceptance Criteria**:
- [ ] OpenTelemetry spans:
  - Span: `composite.detect` — Time spent in composite detection
  - Span: `artifact.hash_compute` — Hash computation per artifact
  - Span: `artifact.dedup_resolve` — Dedup decision per artifact
  - Span: `plugin.import_transactional` — Entire import transaction
  - Span: `association.write` — Writing association rows
  - All spans include relevant tags: `plugin_name`, `child_count`, `artifact_name`, `content_hash`
- [ ] Metrics:
  - Counter: `plugin_import_total` — Total plugins imported
  - Counter: `dedup_hit_total` — Artifacts linked to existing (reused)
  - Counter: `dedup_miss_total` — New artifacts created
  - Histogram: `plugin_import_duration_seconds` — Distribution of import times
  - Histogram: `artifact_hash_compute_duration_seconds` — Hash computation time
- [ ] Structured logging:
  - Log fields: `plugin_name`, `child_count`, `new_count`, `existing_count`, `transaction_id`, `duration_ms`
  - Examples:
    - "plugin_imported" → plugin_name, child_count, new_count, existing_count, duration_ms
    - "dedup_decision" → artifact_name, decision, content_hash
    - "import_failure" → error_msg, partial_imports_rolled_back
- [ ] Log levels:
  - INFO: Import started/completed
  - DEBUG: Per-child dedup decisions
  - WARN: Conflicts or dedup ambiguities
  - ERROR: Import failures
- [ ] No breaking changes to existing logging

**Key Files to Modify**:
- `skillmeat/core/importer.py` — Add OTel spans + metrics
- `skillmeat/core/deduplication.py` — Add spans + logging
- `skillmeat/observability/` — May add metric definitions

**Implementation Notes**:
- Use `from opentelemetry import trace; tracer = trace.get_tracer(__name__)`
- Spans should be nested: `import_transactional` → `dedup_resolve` → `hash_compute`
- Metrics: Use OpenTelemetry SDK (already in project likely)
- Structured logging: Use existing logging framework (structlog if available, else stdlib logging)
- Test: Verify spans appear in trace visualizers (Jaeger, etc.)

**Estimate**: 1 story point

---

### CAI-P3-10: Bundle Export for Composites

**Description**: Update `skillmeat export` command to accept a Composite Artifact ID and automatically generate a Bundle zip containing the composite's metadata plus all child artifacts. Unifies the legacy Bundle concept with the new Composite model.

**Acceptance Criteria**:
- [ ] `skillmeat export <composite_id>` generates a valid Bundle zip
- [ ] Bundle includes composite metadata + all child artifacts
- [ ] Existing manual bundle creation still works
- [ ] Unit test for export path

**Key Files to Modify**:
- `skillmeat/core/sharing/bundle.py` — Add composite-aware export logic
- CLI export command (e.g., `skillmeat/cli.py` or relevant CLI module)

**Implementation Notes**:
- Resolve composite membership to enumerate child artifacts
- Bundle zip should contain composite metadata (plugin.json, manifest) at root level
- Child artifacts placed in type-appropriate subdirectories within the bundle
- Reuse existing bundle creation infrastructure where possible

**Dependencies**: CAI-P3-03

**Estimate**: 1 story point

**Subagent**: python-backend-engineer

---

## Phase 3 Quality Gates

Before Phase 4 can begin, all the following must pass:

- [ ] Hash computation consistent: Same artifact → same hash every time
- [ ] Hash output compatible with existing `ArtifactVersion.content_hash` format
- [ ] Dedup logic correct: All three scenarios (link, new version, create) tested
- [ ] Transaction wrapper works: Happy path imports all children + composite entity atomically
- [ ] Rollback scenario passes: Mid-import failure leaves DB clean
- [ ] Pinned hash stored correctly: Memberships include hash, retrievable via API
- [ ] Project deployment propagation works for Claude Code
- [ ] Plugin files stored correctly: `~/.skillmeat/collections/{collection}/plugins/<name>/` directory created
- [ ] Non-Claude plugin deployment returns explicit unsupported response
- [ ] API endpoint works: `GET /api/v1/artifacts/{id}/associations` returns 200 with `AssociationsDTO`
- [ ] Bundle export works: `skillmeat export <composite_id>` produces valid zip
- [ ] Integration tests pass: Happy path, dedup, rollback, API all green
- [ ] Observability complete: OTel spans logged, metrics recorded, structured logs include required fields
- [ ] No regression in existing import: `pytest tests/test_importer.py -v` passes (flat artifact imports unaffected)

---

## Implementation Notes & References

### Deduplication Decision Tree

```
For each child in plugin:
  1. Compute content_hash
  2. Query DB for artifact with same hash
     → FOUND: LINK_EXISTING (use existing artifact ID)
     → NOT FOUND: Continue
  3. Query DB for artifact with same name
     → FOUND + different hash: CREATE_NEW_VERSION (or CONFLICT_NEEDS_USER_DECISION)
     → NOT FOUND: CREATE_NEW_ARTIFACT

Apply decision:
  - LINK_EXISTING: Use existing artifact ID in association
  - CREATE_NEW_VERSION: Create ArtifactVersion linked to existing artifact
  - CREATE_NEW_ARTIFACT: Create new Artifact row
```

### Transaction Pattern

```python
from sqlalchemy.orm import Session

def import_plugin_transactional(discovered_graph, source_url):
    session = get_session()
    try:
        with session.begin():  # Transaction starts here
            # Step 1: Import all children
            child_ids = []
            for child in discovered_graph.children:
                hash = compute_artifact_hash(child.path)
                decision = resolve_artifact_for_import(child, hash)
                artifact_id = apply_dedup_decision(decision, child)
                child_ids.append(artifact_id)

            # Step 2: Import plugin
            plugin_artifact = create_artifact_from_discovered(discovered_graph.parent)
            plugin_id = save_artifact(plugin_artifact, session)

            # Step 3: Create associations
            for child_id in child_ids:
                hash = compute_artifact_hash(...)
                create_membership(plugin_id, child_id, "contains", hash, session)

            # Transaction commits here on success
    except Exception as e:
        # Transaction rolled back automatically
        logger.error(f"Plugin import failed: {e}")
        raise
```

### OTel Instrumentation Example

```python
from opentelemetry import trace, metrics

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

import_counter = meter.create_counter("plugin_import_total")
reuse_counter = meter.create_counter("dedup_hit_total")
duration_histogram = meter.create_histogram("plugin_import_duration_seconds")

def import_plugin_transactional(discovered_graph, source_url):
    start_time = time.time()
    with tracer.start_as_current_span("plugin.import_transactional") as span:
        span.set_attribute("plugin_name", discovered_graph.parent.name)
        span.set_attribute("child_count", len(discovered_graph.children))

        # ... import logic ...

        duration = time.time() - start_time
        duration_histogram.record(duration)
        import_counter.add(1, {"status": "success"})
```

---

## Deliverables Checklist

- [ ] Content hash computation implemented and tested (compatible with existing `ArtifactVersion.content_hash`)
- [ ] Deduplication logic implemented with all three scenarios
- [ ] Transaction wrapper for plugin import implemented with rollback
- [ ] Version pinning (`pinned_version_hash`) stored and retrievable
- [ ] Project deployment propagation implemented (Claude Code v1 scope)
- [ ] Plugin meta-file storage implemented at `~/.skillmeat/collections/{collection}/plugins/`
- [ ] `GET /artifacts/{id}/associations` API endpoint implemented
- [ ] Bundle export for composites via `skillmeat export <composite_id>`
- [ ] Integration tests covering happy path, dedup, rollback, API
- [ ] OpenTelemetry spans, metrics, and structured logging added
- [ ] API endpoint documented in OpenAPI spec
- [ ] All Phase 3 quality gates passing
- [ ] Code reviewed and merged to main branch

> **Deferred**: Enhanced version conflict handling (same-name-different-hash with user choice UI) is planned for a future enhancement.

---

**Phase 3 Status**: Ready for implementation
**Estimated Completion**: 3-4 days from Phase 2 completion
**Next Phase**: Phase 4 - Web UI Implementation (depends on Phase 3 API endpoint being stable)
