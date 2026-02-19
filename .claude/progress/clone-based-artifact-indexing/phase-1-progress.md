---
type: progress
prd: clone-based-artifact-indexing
phase: 1
title: Database & Core Foundation
status: completed
started: null
updated: '2026-01-24'
completion: 0
total_tasks: 8
completed_tasks: 8
tasks:
- id: DB-101
  title: Create Alembic migration for clone_target_json field
  description: Add clone_target_json Text field to MarketplaceSource for JSON-serialized
    CloneTarget
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - Migration runs cleanly forward/backward on test DB
  - clone_target_json column exists on marketplace_sources table
  - Column is nullable Text type with appropriate comment
- id: DB-102
  title: Add deep_indexing_enabled boolean field
  description: Add deep_indexing_enabled boolean to MarketplaceSource with server_default
    false
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-101
  model: sonnet
  estimated_time: 30m
  story_points: 1
  acceptance_criteria:
  - Field defaults to false for existing and new rows
  - Migration runs cleanly forward/backward
- id: DB-103
  title: Add webhook pre-wire fields
  description: Add webhook_secret (String 64) and last_webhook_event_at (DateTime)
    to MarketplaceSource for future webhook support
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-101
  model: sonnet
  estimated_time: 30m
  story_points: 1
  acceptance_criteria:
  - Fields are nullable (pre-wired for future use)
  - webhook_secret has proper length constraint
  - Migration runs cleanly forward/backward
- id: DB-104
  title: Add deep index fields to MarketplaceCatalogEntry
  description: Add deep_search_text (Text), deep_indexed_at (DateTime), deep_index_files
    (Text/JSON) to catalog entries
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-101
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - deep_search_text stores full-text content for FTS
  - deep_indexed_at tracks last deep indexing timestamp
  - deep_index_files stores JSON array of indexed file paths
  - All fields nullable
- id: DB-105
  title: Update FTS5 virtual table with deep_search_text
  description: Drop and recreate catalog_fts FTS5 table with deep_search_text column;
    configure porter tokenizer
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-104
  model: opus
  estimated_time: 1h
  story_points: 3
  acceptance_criteria:
  - FTS5 table has all columns including deep_search_text
  - Tokenizer configured with porter unicode61
  - Full-text indexing works for all columns
  - FTS index rebuilt after migration
- id: CORE-101
  title: Implement CloneTarget dataclass
  description: Create skillmeat/core/clone_target.py with CloneTarget dataclass including
    strategy, sparse_patterns, artifacts_root, artifact_paths, tree_sha, computed_at
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 1.5h
  story_points: 2
  acceptance_criteria:
  - Dataclass can serialize to JSON
  - Dataclass can deserialize from JSON
  - All fields properly typed with Literal for strategy
  - computed_at uses datetime with timezone
- id: CORE-102
  title: Implement compute_clone_metadata()
  description: Create function to compute artifacts_root and sparse_patterns from
    DetectedArtifact list; handle edge cases
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CORE-101
  model: opus
  estimated_time: 2h
  story_points: 2
  acceptance_criteria:
  - Computes common ancestor path correctly
  - Handles empty artifact list
  - Handles single artifact
  - Handles scattered paths with no common root
  - Returns valid dict for CloneTarget construction
- id: CORE-103
  title: Add CloneTarget property to MarketplaceSource model
  description: Update SQLAlchemy model with clone_target_json column and clone_target
    property for deserialization
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - DB-101
  - CORE-101
  model: opus
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - Model tests pass
  - Can read/write CloneTarget from database
  - Property returns None when clone_target_json is null
  - Property correctly deserializes JSON to CloneTarget
parallelization:
  batch_1:
  - DB-101
  - CORE-101
  batch_2:
  - DB-102
  - DB-103
  - DB-104
  - CORE-102
  batch_3:
  - DB-105
  - CORE-103
  critical_path:
  - DB-101
  - DB-104
  - DB-105
  estimated_total_time: 8h
blockers: []
quality_gates:
- Alembic migrations run cleanly forward and backward
- FTS5 table schema validated with SQLite inspection
- CloneTarget serializes/deserializes without data loss
- compute_clone_metadata() handles empty/single/multiple artifacts correctly
- Unit tests for CloneTarget pass (>80% coverage)
- No breaking changes to existing MarketplaceCatalogEntry reads
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
schema_version: 2
doc_type: progress
feature_slug: clone-based-artifact-indexing
---

# Phase 1: Database & Core Foundation

**Plan:** `docs/project_plans/implementation_plans/features/clone-based-artifact-indexing-v1.md`
**SPIKE:** `docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md`
**Status:** Pending
**Story Points:** 11 total
**Duration:** 2-3 days

## Orchestration Quick Reference

**Batch 1** (Parallel - 2.5h estimated):
- DB-101 -> `data-layer-expert` (sonnet) - Alembic migration for clone_target_json
- CORE-101 -> `python-backend-engineer` (opus) - CloneTarget dataclass

**Batch 2** (After Batch 1 - 4h estimated):
- DB-102 -> `data-layer-expert` (sonnet) - deep_indexing_enabled field
- DB-103 -> `data-layer-expert` (sonnet) - webhook pre-wire fields
- DB-104 -> `data-layer-expert` (sonnet) - deep index fields on catalog entry
- CORE-102 -> `python-backend-engineer` (opus) - compute_clone_metadata()

**Batch 3** (After Batch 2 - 2h estimated):
- DB-105 -> `data-layer-expert` (opus) - FTS5 virtual table update
- CORE-103 -> `data-layer-expert` (opus) - CloneTarget property on model

### Task Delegation Commands

**Batch 1:**
```
Task("data-layer-expert", "DB-101: Create Alembic migration for clone_target_json

Add clone_target_json Text field to MarketplaceSource table.

Migration file: skillmeat/api/alembic/versions/xxx_add_clone_target_fields.py

Field spec:
- clone_target_json: Text, nullable=True
- Comment: 'JSON-serialized CloneTarget for rapid re-indexing'

Ensure migration runs cleanly forward and backward.
Reference: docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md", model="sonnet")

Task("python-backend-engineer", "CORE-101: Implement CloneTarget dataclass

Create skillmeat/core/clone_target.py with CloneTarget dataclass.

Fields:
- strategy: Literal['api', 'sparse_manifest', 'sparse_directory']
- sparse_patterns: List[str]  # e.g., ['.claude/**'] or ['skills/foo/SKILL.md']
- artifacts_root: Optional[str]  # e.g., '.claude/skills'
- artifact_paths: List[str]  # e.g., ['.claude/skills/foo', '.claude/skills/bar']
- tree_sha: str  # SHA of repo tree at computation time
- computed_at: datetime  # Timestamp with timezone

Requirements:
- to_json() method for serialization
- from_json() classmethod for deserialization
- All fields properly typed
- Use dataclasses or pydantic

Reference: docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md")
```

**Batch 2:**
```
Task("data-layer-expert", "DB-102: Add deep_indexing_enabled boolean field

Add deep_indexing_enabled to MarketplaceSource in same migration as DB-101.

Field spec:
- deep_indexing_enabled: Boolean, nullable=False, server_default='false'
- Comment: 'Clone entire artifact directories for enhanced search'

Ensure field defaults to false for existing and new rows.", model="sonnet")

Task("data-layer-expert", "DB-103: Add webhook pre-wire fields

Add webhook fields to MarketplaceSource (future use, all nullable).

Fields:
- webhook_secret: String(64), nullable=True
  Comment: 'Secret for GitHub webhook verification (future use)'
- last_webhook_event_at: DateTime, nullable=True
  Comment: 'Timestamp of last webhook event received'

These are pre-wired for future webhook integration.", model="sonnet")

Task("data-layer-expert", "DB-104: Add deep index fields to MarketplaceCatalogEntry

Add deep indexing fields to MarketplaceCatalogEntry table.

Fields:
- deep_search_text: Text, nullable=True
  Comment: 'Full-text content from deep indexing'
- deep_indexed_at: DateTime, nullable=True
  Comment: 'Timestamp of last deep indexing'
- deep_index_files: Text, nullable=True
  Comment: 'JSON array of files included in deep index'

Reference existing patterns in skillmeat/api/models/marketplace.py", model="sonnet")

Task("python-backend-engineer", "CORE-102: Implement compute_clone_metadata()

Create function in skillmeat/core/clone_target.py.

Signature:
def compute_clone_metadata(artifacts: List[DetectedArtifact]) -> dict

Returns dict with:
- artifacts_root: str | None (common ancestor path)
- artifact_paths: List[str] (all artifact paths)
- sparse_patterns: List[str] (manifest file patterns)

Logic:
1. If empty list: return all None/empty
2. If single artifact: dirname of path as root
3. If multiple: os.path.commonpath() for common ancestor
4. Handle scattered paths (no common root) gracefully

Generate sparse patterns based on artifact types using MANIFEST_PATTERNS from SPIKE.")
```

**Batch 3:**
```
Task("data-layer-expert", "DB-105: Update FTS5 virtual table with deep_search_text

Create migration to update catalog_fts FTS5 table.

Requirements:
1. DROP existing catalog_fts table
2. CREATE VIRTUAL TABLE catalog_fts USING fts5 with columns:
   - name UNINDEXED
   - artifact_type UNINDEXED
   - title
   - description
   - search_text
   - tags
   - deep_search_text (NEW)
   - content='marketplace_catalog_entries'
   - content_rowid='rowid'
   - tokenize='porter unicode61 remove_diacritics 2'
3. Rebuild FTS index: INSERT INTO catalog_fts(catalog_fts) VALUES('rebuild')

Note: FTS5 tables cannot be altered, must recreate.", model="opus")

Task("data-layer-expert", "CORE-103: Add CloneTarget property to MarketplaceSource model

Update skillmeat/api/models/marketplace.py MarketplaceSource class.

Add:
1. clone_target_json column mapping (from migration DB-101)
2. clone_target property that deserializes JSON to CloneTarget

Code:
@property
def clone_target(self) -> Optional[CloneTarget]:
    if not self.clone_target_json:
        return None
    return CloneTarget.from_json(self.clone_target_json)

@clone_target.setter
def clone_target(self, value: Optional[CloneTarget]) -> None:
    if value is None:
        self.clone_target_json = None
    else:
        self.clone_target_json = value.to_json()

Import CloneTarget from skillmeat.core.clone_target", model="opus")
```

---

## Success Criteria

- [ ] Alembic migrations run cleanly forward and backward
- [ ] FTS5 table schema validated with SQLite inspection
- [ ] CloneTarget serializes/deserializes without data loss
- [ ] compute_clone_metadata() handles empty/single/multiple artifacts correctly
- [ ] Unit tests for CloneTarget pass (>80% coverage)
- [ ] No breaking changes to existing MarketplaceCatalogEntry reads

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]
