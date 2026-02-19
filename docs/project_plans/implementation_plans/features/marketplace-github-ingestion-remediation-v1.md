---
title: 'Implementation Plan: Marketplace GitHub Ingestion Remediation'
description: 'Remediation plan to complete stubbed marketplace ingestion implementation
  from PR #26'
audience:
- ai-agents
- developers
tags:
- implementation
- remediation
- marketplace
- github
- ingestion
created: 2025-12-26
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/implementation_plans/features/marketplace-github-ingestion-v1.md
- /docs/project_plans/PRDs/features/marketplace-github-ingestion-v1.md
- /.claude/worknotes/marketplace-gaps-quick-ref.md
schema_version: 2
doc_type: implementation_plan
feature_slug: marketplace-github-ingestion-remediation
prd_ref: null
---

# Implementation Plan: Marketplace GitHub Ingestion Remediation

**Plan ID**: `IMPL-2025-12-26-marketplace-remediation`
**Date**: 2025-12-26
**Author**: Implementation Planner Agent
**Complexity**: Medium
**Total Estimated Effort**: 15 story points (~8 hours)

## Executive Summary

PR #26 (commit 1fc65c6) was merged claiming feature completion, but critical integrations were left stubbed. All code exists and is structurally sound, but key components are disconnected:

1. **Heuristic Detector**: Fully implemented but import/calls commented out
2. **Diff Engine**: Fully implemented but never called
3. **Import Coordinator**: Works but downloads are stubbed

Additionally, a new requirement emerged: **frontmatter-based detection toggle** for repos where directory names don't follow conventions.

This plan focuses on wiring existing components together and adding the frontmatter toggle.

## Implementation Strategy

### Approach: Integration-First

Since all components exist, we use an integration-first approach:
1. Wire existing components (no new code, just uncomment/call)
2. Add frontmatter detection feature
3. Validate end-to-end flow

### Critical Path

```
Phase 1 (Wire) → Phase 2 (Frontmatter) → Phase 3 (Validation)
   30 min              4 hours              2 hours
```

### Parallel Work Opportunities

- Phase 1 tasks can run in parallel (different files)
- Phase 2.1 (DB) must complete before 2.2-2.5
- Phase 3 can start after Phase 1 for quick validation

---

## Phase 1: Wire Existing Components

**Duration**: 30-45 minutes
**Dependencies**: None
**Assigned Subagent(s)**: python-backend-engineer

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------|--------------|
| REM-1.1 | Wire Heuristic Import | Uncomment import in github_scanner.py lines 30-34 | Import resolves without error | 5 min | python-backend-engineer | None |
| REM-1.2 | Wire Detector Init | Uncomment detector initialization line 101 | Detector instantiates | 5 min | python-backend-engineer | REM-1.1 |
| REM-1.3 | Wire scan_repository | Uncomment detect_artifacts_in_tree call lines 159-167, remove placeholder lines 169-174 | scan_repository returns detected artifacts | 10 min | python-backend-engineer | REM-1.2 |
| REM-1.4 | Wire scan_github_source | Uncomment detect_artifacts_in_tree call lines 464-471, remove placeholder lines 473-478 | Convenience function returns artifacts | 10 min | python-backend-engineer | REM-1.2 |
| REM-1.5 | Wire Diff Engine | Replace hardcoded `new_entries = []` with CatalogDiffEngine.compute_diff() call in marketplace_sources.py:545-548 | Rescan performs incremental updates | 15 min | python-backend-engineer | REM-1.3 |

### Quality Gates

- [ ] All imports resolve without circular dependency errors
- [ ] `python -m skillmeat.core.marketplace.heuristic_detector` shows detection output
- [ ] Unit tests pass: `pytest tests/core/marketplace/test_heuristic_detector.py`
- [ ] Scanner returns non-empty artifacts for test repo

### Files Modified

```
skillmeat/core/marketplace/github_scanner.py
  - Line 30-34: Uncomment import
  - Line 101: Uncomment self.detector = HeuristicDetector()
  - Lines 159-174: Enable detection, remove placeholder
  - Lines 464-478: Enable detection, remove placeholder

skillmeat/api/routers/marketplace_sources.py
  - Lines 545-548: Implement diff engine call
```

### Task Delegation Commands

```python
Task("python-backend-engineer", """REM-1.1 to REM-1.4: Wire heuristic detector in github_scanner.py.

Files: skillmeat/core/marketplace/github_scanner.py

Changes needed:
1. Lines 30-34: Uncomment the import block:
   from skillmeat.core.marketplace.heuristic_detector import (
       HeuristicDetector,
       detect_artifacts_in_tree,
   )

2. Line 101: Uncomment: self.detector = HeuristicDetector()

3. Lines 159-174: Uncomment the detection call, delete the placeholder:
   - Uncomment: base_url = f"https://github.com/{owner}/{repo}"
   - Uncomment: artifacts = detect_artifacts_in_tree(file_paths, repo_url=base_url, ...)
   - DELETE lines 169-174 (placeholder that returns empty list)

4. Lines 464-478: Same pattern - uncomment detection, delete placeholder

Test: python -m skillmeat.core.marketplace.heuristic_detector
Expected: Shows detected artifacts with confidence scores""")

Task("python-backend-engineer", """REM-1.5: Wire diff engine in marketplace_sources.py.

File: skillmeat/api/routers/marketplace_sources.py

Location: rescan_source() endpoint, lines 545-548

Current code (REPLACE):

```python
# TODO: Use diff engine for incremental updates
new_entries: List[MarketplaceCatalogEntry] = []
ctx.replace_catalog_entries(new_entries)
```

Replace with:

```python
from skillmeat.core.marketplace.diff_engine import CatalogDiffEngine

# Get existing entries for diff
existing_entries = catalog_repo.get_source_catalog(source_id=source_id)

# Compute diff between old and new catalog
diff_engine = CatalogDiffEngine()
diff_result = diff_engine.compute_diff(
    [e.to_dict() for e in existing_entries],
    scan_result.artifacts,  # From heuristic detector
    source_id,
)

# Apply diff results
ctx.apply_diff(diff_result)
```

Note: Check if `apply_diff` method exists on context, or use appropriate method.""")

---

## Phase 2: Frontmatter Detection Toggle

**Duration**: 4 hours
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer, ui-engineer

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------|--------------|
| REM-2.1 | DB Migration | Add `enable_frontmatter_detection` boolean column to marketplace_sources table | Migration runs, column exists with default false | 30 min | data-layer-expert | None |
| REM-2.2 | Update Model | Add field to MarketplaceSource SQLAlchemy model | Model reflects new column | 15 min | python-backend-engineer | REM-2.1 |
| REM-2.3 | Update Schemas | Add field to create/update request schemas and response schema | API accepts/returns field | 20 min | python-backend-engineer | REM-2.2 |
| REM-2.4 | Enhance Detector | Add frontmatter parsing to HeuristicDetector when enabled | Detector reads frontmatter, boosts confidence | 90 min | python-backend-engineer | REM-2.3 |
| REM-2.5 | Update Frontend | Add toggle to source add/edit form | Toggle appears and persists | 45 min | ui-engineer | REM-2.3 |

### Quality Gates

- [ ] Migration runs forward and backward cleanly
- [ ] API accepts `enable_frontmatter_detection` in create/update requests
- [ ] Detector parses frontmatter when enabled (test with sample repo)
- [ ] Frontend toggle appears and value persists on save

### Files Modified

```
skillmeat/cache/migrations/versions/XXX_add_frontmatter_detection.py (NEW)
skillmeat/cache/models.py (MarketplaceSource)
skillmeat/api/schemas/marketplace.py (MarketplaceSourceCreate, MarketplaceSourceUpdate, MarketplaceSourceResponse)
skillmeat/core/marketplace/heuristic_detector.py (analyze_paths, _parse_frontmatter)
skillmeat/web/components/marketplace/source-form.tsx
skillmeat/web/lib/api/marketplace-sources.ts (if needed)
```

### Task Delegation Commands

```python
Task("data-layer-expert", """REM-2.1: Create Alembic migration for frontmatter detection toggle.

Create migration: skillmeat/cache/migrations/versions/XXX_add_frontmatter_detection.py

Schema change:
- Table: marketplace_sources
- Add column: enable_frontmatter_detection BOOLEAN DEFAULT FALSE NOT NULL

Pattern to follow: See existing migrations in skillmeat/cache/migrations/versions/

Commands after creation:
- alembic upgrade head
- alembic downgrade -1 (verify rollback)
- alembic upgrade head""")

Task("python-backend-engineer", """REM-2.2 & REM-2.3: Update model and schemas for frontmatter toggle.

File 1: skillmeat/cache/models.py
Add to MarketplaceSource class (after visibility field ~line 1241):
```python
# Detection settings
enable_frontmatter_detection: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default="false",
    comment="Parse markdown frontmatter for artifact type hints",
)
```

File 2: skillmeat/api/schemas/marketplace.py
Add to relevant request/response schemas:
- MarketplaceSourceCreate: enable_frontmatter_detection: bool = False
- MarketplaceSourceUpdate: enable_frontmatter_detection: Optional[bool] = None
- MarketplaceSourceResponse: enable_frontmatter_detection: bool

Test: Check OpenAPI docs at /api/v1/docs shows new field""")

Task("python-backend-engineer", """REM-2.4: Enhance HeuristicDetector with frontmatter parsing.

File: skillmeat/core/marketplace/heuristic_detector.py

Changes:
1. Add `enable_frontmatter_detection: bool = False` parameter to:
   - HeuristicDetector.__init__
   - analyze_paths
   - detect_artifacts_in_tree

2. Add new method `_parse_frontmatter`:
```python
def _parse_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
    '''Parse YAML frontmatter from markdown content.

    Returns dict with keys like 'type', 'artifact-type', 'skill', 'command', etc.
    '''
    import yaml

    if not content.startswith('---'):
        return None

    # Find closing ---
    end_idx = content.find('---', 3)
    if end_idx == -1:
        return None

    frontmatter_str = content[3:end_idx].strip()
    try:
        return yaml.safe_load(frontmatter_str)
    except yaml.YAMLError:
        return None
```

3. In _score_directory, if enable_frontmatter_detection and .md files present:
   - Look for indicator keys: 'type', 'artifact-type', 'skill', 'command', 'agent', 'mcp'
   - If found, add frontmatter_weight (15 points) to score
   - Override artifact_type if frontmatter specifies it

4. Add to DetectionConfig:
   frontmatter_weight: int = 15

Test: Create test markdown with frontmatter type: skill, verify detection""")

Task("ui-engineer", """REM-2.5: Add frontmatter detection toggle to source form.

Files to modify:
1. skillmeat/web/components/marketplace/source-form.tsx (or wherever source add/edit lives)
2. Update types if needed

Add toggle field:
- Label: "Enable frontmatter detection"
- Description: "Scan markdown files for artifact type hints in YAML frontmatter"
- Default: false
- Position: After "Root Hint" field, before submit button

Pattern: Follow existing toggle/checkbox patterns in the form.

The API already accepts enable_frontmatter_detection after backend changes.""")


---

## Phase 3: Import Downloads (Deferred)

**Status**: DEFERRED - Lower priority than detection
**Duration**: 2 hours when implemented
**Dependencies**: Phase 1 complete

### Rationale for Deferral

The import download functionality (REM-3.x) is lower priority because:
1. Users can manually download artifacts after discovery
2. Detection is the critical blocking issue
3. Can be addressed in follow-up sprint

### Deferred Tasks

| Task ID | Task Name | Description | Est. | Subagent |
|---------|-----------|-------------|------|----------|
| REM-3.1 | Implement _download_artifact | Fetch files from GitHub API | 60 min | python-backend-engineer |
| REM-3.2 | Implement _update_manifest | Update collection manifest.toml | 30 min | python-backend-engineer |
| REM-3.3 | Wire Downloads | Replace stub in import_coordinator.py | 30 min | python-backend-engineer |

---

## Phase 4: Validation & Testing

**Duration**: 1-2 hours
**Dependencies**: Phase 1 complete (minimum), Phase 2 complete (full)
**Assigned Subagent(s)**: python-backend-engineer, testing specialist

### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent | Dependencies |
|---------|-----------|-------------|---------------------|------|----------|--------------|
| REM-4.1 | Unit Tests | Run existing marketplace tests | All tests pass | 15 min | python-backend-engineer | REM-1.5 |
| REM-4.2 | Integration Test | Add source, trigger scan, verify artifacts found | artifacts_found > 0 | 30 min | python-backend-engineer | REM-1.5 |
| REM-4.3 | Frontmatter Test | Test detection with frontmatter-marked repo | Correct type detected | 20 min | python-backend-engineer | REM-2.4 |
| REM-4.4 | E2E Smoke Test | Full flow via web UI | Source added, scanned, artifacts shown | 30 min | testing specialist | REM-2.5 |

### Quality Gates

- [ ] `pytest tests/core/marketplace/` passes
- [ ] `pytest tests/api/test_marketplace_sources.py` passes
- [ ] Manual test: Add anthropics/anthropic-quickstarts, verify skills detected
- [ ] Manual test: Toggle frontmatter detection, verify behavior changes

### Test Commands

```bash
# Unit tests
pytest tests/core/marketplace/test_heuristic_detector.py -v
pytest tests/core/marketplace/test_github_scanner.py -v

# Integration tests
pytest tests/api/test_marketplace_sources.py -v

# Manual integration test
curl -X POST http://localhost:8000/api/v1/marketplace/sources \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
    "ref": "main"
  }'

# Trigger rescan
curl -X POST http://localhost:8000/api/v1/marketplace/sources/{id}/rescan

# Check artifacts
curl http://localhost:8000/api/v1/marketplace/sources/{id}/artifacts
```

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Circular imports when uncommenting | Medium | Low | Test import after each change |
| Diff engine expects different data format | Medium | Medium | Review diff_engine.py interface before calling |
| Frontmatter parsing breaks detection | Low | Low | Add feature flag, fallback to directory-only |
| GitHub rate limiting during tests | Low | Medium | Use cached responses, mock in unit tests |

---

## Resource Requirements

### Team Composition

- **python-backend-engineer**: 1 FTE (Phases 1, 2.2-2.4, 3, 4)
- **data-layer-expert**: 0.25 FTE (Phase 2.1 only)
- **ui-engineer**: 0.25 FTE (Phase 2.5 only)

### Dependencies

- Existing code in `skillmeat/core/marketplace/`
- Alembic migration infrastructure
- Frontend source form component

---

## Success Metrics

### Delivery Metrics

- All critical gaps closed (REM-1.x complete)
- Frontmatter toggle functional (REM-2.x complete)
- Tests pass with >80% coverage on modified files

### Functional Metrics

- Scan returns artifacts for anthropics/anthropic-quickstarts (>0)
- Rescan updates catalog incrementally (not wipes)
- Frontmatter detection identifies types in non-standard directories

---

## Progress Tracking

See `.claude/progress/marketplace-github-ingestion-remediation/` for phase-by-phase progress.

---

## Appendix: File Locations Summary

### Phase 1 Files (Wire Components)

| File | Lines | Change |
|------|-------|--------|
| `github_scanner.py` | 30-34 | Uncomment import |
| `github_scanner.py` | 101 | Uncomment init |
| `github_scanner.py` | 159-174 | Enable detection, remove stub |
| `github_scanner.py` | 464-478 | Enable detection, remove stub |
| `marketplace_sources.py` | 545-548 | Implement diff call |

### Phase 2 Files (Frontmatter)

| File | Change |
|------|--------|
| `migrations/XXX_*.py` | NEW: Add column |
| `models.py` | Add field to MarketplaceSource |
| `schemas/marketplace.py` | Add to create/update/response |
| `heuristic_detector.py` | Add frontmatter parsing |
| `source-form.tsx` | Add toggle UI |

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2025-12-26
