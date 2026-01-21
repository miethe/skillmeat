---
# === PROGRESS TRACKING: Configurable Frontmatter Caching ===
# Unified tracking for all phases (small feature, 26 pts total)
# Update using: python .claude/skills/artifact-tracking/scripts/update-status.py

type: progress
prd: "configurable-frontmatter-caching-v1"
phase: 0  # "Phase 0" of cross-source artifact search SPIKE
title: "Configurable Frontmatter Caching for Cross-Source Artifact Search"
status: "planning"
started: "2026-01-20"
completed: null

# Overall Progress
overall_progress: 0
completion_estimate: "on-track"

# Task Counts
total_tasks: 22
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

# Ownership
owners: ["python-backend-engineer", "ui-engineer-enhanced"]
contributors: ["data-layer-expert", "documentation-writer"]

# === PHASE 1: CONFIGURATION LAYER (4 pts) ===
# Assigned to: python-backend-engineer (Sonnet)
tasks:
  - id: "TASK-1.1"
    description: "Add artifact_search.indexing_mode config key with defaults"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1h"
    priority: "high"
    model: "sonnet"
    files: ["skillmeat/config.py"]

  - id: "TASK-1.2"
    description: "Add get_indexing_mode() and set_indexing_mode() helper methods"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1"]
    estimated_effort: "1h"
    priority: "high"
    model: "sonnet"
    files: ["skillmeat/config.py"]

  - id: "TASK-1.3"
    description: "Add CLI command support for artifact_search.indexing_mode"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2"]
    estimated_effort: "1h"
    priority: "medium"
    model: "sonnet"
    files: ["skillmeat/cli.py"]

  - id: "TASK-1.4"
    description: "Unit tests for ConfigManager indexing mode methods"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2"]
    estimated_effort: "1h"
    priority: "medium"
    model: "sonnet"
    files: ["tests/unit/test_config.py"]

# === PHASE 2: DATABASE LAYER (4 pts) ===
# Assigned to: data-layer-expert (Opus)
  - id: "TASK-2.1"
    description: "Add indexing_enabled column to MarketplaceSource model"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-1.1"]
    estimated_effort: "1h"
    priority: "high"
    model: "opus"
    files: ["skillmeat/cache/models.py"]

  - id: "TASK-2.2"
    description: "Create Alembic migration for indexing_enabled column"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-2.1"]
    estimated_effort: "1.5h"
    priority: "high"
    model: "opus"
    files: ["skillmeat/cache/migrations/versions/"]

  - id: "TASK-2.3"
    description: "Test migration on existing database with sources"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-2.2"]
    estimated_effort: "1h"
    priority: "high"
    model: "opus"

# === PHASE 3: API LAYER (7 pts) ===
# Assigned to: python-backend-engineer (Sonnet)
  - id: "TASK-3.1"
    description: "Update CreateSourceRequest schema with indexing_enabled field"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
    estimated_effort: "1h"
    priority: "high"
    model: "sonnet"
    files: ["skillmeat/api/schemas/marketplace.py"]

  - id: "TASK-3.2"
    description: "Update UpdateSourceRequest schema with indexing_enabled field"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-3.1"]
    estimated_effort: "0.5h"
    priority: "high"
    model: "sonnet"
    files: ["skillmeat/api/schemas/marketplace.py"]

  - id: "TASK-3.3"
    description: "Update SourceResponse schema with indexing_enabled field"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-3.1"]
    estimated_effort: "0.5h"
    priority: "high"
    model: "sonnet"
    files: ["skillmeat/api/schemas/marketplace.py"]

  - id: "TASK-3.4"
    description: "Add GET /config/indexing-mode endpoint for frontend"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2"]
    estimated_effort: "1h"
    priority: "medium"
    model: "sonnet"
    files: ["skillmeat/api/routers/config.py"]

  - id: "TASK-3.5"
    description: "Implement effective indexing state resolution function"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2", "TASK-3.1"]
    estimated_effort: "1.5h"
    priority: "high"
    model: "sonnet"
    files: ["skillmeat/api/routers/marketplace_sources.py"]

  - id: "TASK-3.6"
    description: "Update create/update endpoints to persist indexing_enabled"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-3.5"]
    estimated_effort: "1h"
    priority: "high"
    model: "sonnet"
    files: ["skillmeat/api/routers/marketplace_sources.py"]

# === PHASE 4: UI LAYER (8 pts) ===
# Assigned to: ui-engineer-enhanced (Opus)
  - id: "TASK-4.1"
    description: "Add useIndexingMode hook to fetch global config"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.4"]
    estimated_effort: "1h"
    priority: "high"
    model: "opus"
    files: ["skillmeat/web/hooks/useConfig.ts"]

  - id: "TASK-4.2"
    description: "Add indexing_enabled state to add-source-modal.tsx"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.1"]
    estimated_effort: "0.5h"
    priority: "high"
    model: "opus"
    files: ["skillmeat/web/components/marketplace/add-source-modal.tsx"]

  - id: "TASK-4.3"
    description: "Add toggle UI with tooltip following existing pattern"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.2"]
    estimated_effort: "1.5h"
    priority: "high"
    model: "opus"
    files: ["skillmeat/web/components/marketplace/add-source-modal.tsx"]

  - id: "TASK-4.4"
    description: "Add mode-aware visibility logic for toggle"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.3"]
    estimated_effort: "1h"
    priority: "high"
    model: "opus"
    files: ["skillmeat/web/components/marketplace/add-source-modal.tsx"]

  - id: "TASK-4.5"
    description: "Wire toggle to API payload in createSource mutation"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.4"]
    estimated_effort: "0.5h"
    priority: "high"
    model: "opus"
    files: ["skillmeat/web/components/marketplace/add-source-modal.tsx"]

  - id: "TASK-4.6"
    description: "Add toggle to edit-source-modal.tsx with same pattern"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.5"]
    estimated_effort: "1.5h"
    priority: "medium"
    model: "opus"
    files: ["skillmeat/web/components/marketplace/edit-source-modal.tsx"]

  - id: "TASK-4.7"
    description: "Update TypeScript types in marketplace.ts"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.3"]
    estimated_effort: "0.5h"
    priority: "high"
    model: "opus"
    files: ["skillmeat/web/types/marketplace.ts"]

# === PHASE 5: TESTING LAYER (8 pts) ===
# Assigned to: python-backend-engineer + ui-engineer-enhanced (parallel)
  - id: "TASK-5.1"
    description: "API integration tests for indexing mode + source creation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-3.6"]
    estimated_effort: "2h"
    priority: "high"
    model: "sonnet"
    files: ["tests/integration/test_marketplace_sources.py"]

  - id: "TASK-5.2"
    description: "Frontend component tests for toggle visibility logic"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.6"]
    estimated_effort: "2h"
    priority: "high"
    model: "opus"
    files: ["skillmeat/web/__tests__/marketplace/"]

  - id: "TASK-5.3"
    description: "E2E test for toggle behavior in all three modes"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.1", "TASK-5.2"]
    estimated_effort: "2h"
    priority: "medium"
    model: "opus"
    files: ["skillmeat/web/tests/marketplace.spec.ts"]

# === PHASE 6: DOCUMENTATION LAYER (4 pts) ===
# Assigned to: documentation-writer (Haiku)
  - id: "TASK-6.1"
    description: "Add docstrings to ConfigManager indexing methods"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["TASK-1.2"]
    estimated_effort: "0.5h"
    priority: "low"
    model: "haiku"
    files: ["skillmeat/config.py"]

  - id: "TASK-6.2"
    description: "Add docstrings to MarketplaceSource indexing_enabled"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["TASK-2.1"]
    estimated_effort: "0.5h"
    priority: "low"
    model: "haiku"
    files: ["skillmeat/cache/models.py"]

  - id: "TASK-6.3"
    description: "Update SPIKE document to reference this implementation"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["TASK-5.3"]
    estimated_effort: "1h"
    priority: "medium"
    model: "haiku"
    files: ["docs/project_plans/SPIKEs/cross-source-artifact-search-spike.md"]

# Parallelization Strategy
parallelization:
  batch_1: ["TASK-1.1"]                                    # Config key (foundation)
  batch_2: ["TASK-1.2", "TASK-2.1"]                        # Parallel: config methods + model
  batch_3: ["TASK-1.3", "TASK-1.4", "TASK-2.2", "TASK-3.1", "TASK-3.4"]  # Parallel work
  batch_4: ["TASK-2.3", "TASK-3.2", "TASK-3.3", "TASK-3.5", "TASK-4.1", "TASK-4.7"]
  batch_5: ["TASK-3.6", "TASK-4.2"]
  batch_6: ["TASK-4.3", "TASK-4.4"]
  batch_7: ["TASK-4.5", "TASK-4.6"]
  batch_8: ["TASK-5.1", "TASK-5.2"]                        # Parallel: API tests + UI tests
  batch_9: ["TASK-5.3", "TASK-6.1", "TASK-6.2"]
  batch_10: ["TASK-6.3"]                                   # Final: update SPIKE
  critical_path: ["TASK-1.1", "TASK-1.2", "TASK-3.5", "TASK-3.6", "TASK-4.3", "TASK-5.3"]
  estimated_total_time: "3-4 days (optimal parallel execution)"

# Blockers
blockers: []

# Success Criteria
success_criteria:
  - { id: "SC-1", description: "Config persists across application restarts", status: "pending" }
  - { id: "SC-2", description: "Migration rolls back cleanly", status: "pending" }
  - { id: "SC-3", description: "API validates indexing_enabled field", status: "pending" }
  - { id: "SC-4", description: "Toggle visible only when mode is on/opt_in", status: "pending" }
  - { id: "SC-5", description: "Toggle defaults correctly per mode", status: "pending" }
  - { id: "SC-6", description: ">80% test coverage on new code", status: "pending" }

# Files Modified
files_modified:
  - "skillmeat/config.py"
  - "skillmeat/cache/models.py"
  - "skillmeat/cache/migrations/versions/*.py"
  - "skillmeat/api/schemas/marketplace.py"
  - "skillmeat/api/routers/marketplace_sources.py"
  - "skillmeat/api/routers/config.py"
  - "skillmeat/web/components/marketplace/add-source-modal.tsx"
  - "skillmeat/web/components/marketplace/edit-source-modal.tsx"
  - "skillmeat/web/types/marketplace.ts"
  - "skillmeat/web/hooks/useConfig.ts"
---

# Configurable Frontmatter Caching - Phase 0 Progress

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

## CLI Updates

```bash
# Mark task complete
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/configurable-frontmatter-caching-v1/all-phases-progress.md \
  -t TASK-1.1 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/configurable-frontmatter-caching-v1/all-phases-progress.md \
  --updates "TASK-1.1:completed,TASK-1.2:completed"
```

---

## Objective

Add configurable control over frontmatter caching for cross-source artifact search. This is "Phase 0" of the cross-source artifact search SPIKE, providing the configuration infrastructure that subsequent phases depend on.

---

## Phase Summary

| Phase | Title | Points | Agents | Status |
|-------|-------|--------|--------|--------|
| 1 | Configuration Layer | 4 | python-backend-engineer (Sonnet) | pending |
| 2 | Database Layer | 4 | data-layer-expert (Opus) | pending |
| 3 | API Layer | 7 | python-backend-engineer (Sonnet) | pending |
| 4 | UI Layer | 8 | ui-engineer-enhanced (Opus) | pending |
| 5 | Testing Layer | 8 | python-backend-engineer + ui-engineer-enhanced | pending |
| 6 | Documentation Layer | 4 | documentation-writer (Haiku) | pending |

---

## Quick Reference: Task Invocations

```python
# Phase 1: Configuration Layer
Task("python-backend-engineer", "TASK-1.1: Add artifact_search.indexing_mode config key. File: skillmeat/config.py", model="sonnet")

# Phase 2: Database Layer
Task("data-layer-expert", "TASK-2.1: Add indexing_enabled column to MarketplaceSource. File: skillmeat/cache/models.py")

# Phase 3: API Layer
Task("python-backend-engineer", "TASK-3.5: Implement effective indexing state resolution. File: skillmeat/api/routers/marketplace_sources.py", model="sonnet")

# Phase 4: UI Layer
Task("ui-engineer-enhanced", "TASK-4.3: Add indexing toggle with tooltip to add-source-modal. File: skillmeat/web/components/marketplace/add-source-modal.tsx")

# Phase 5: Testing
Task("python-backend-engineer", "TASK-5.1: API integration tests for indexing mode", model="sonnet")
Task("ui-engineer-enhanced", "TASK-5.2: Frontend component tests for toggle visibility")
```

---

## Key Implementation Notes

### Mode Precedence Logic

```python
def get_effective_indexing_enabled(source: MarketplaceSource, config: ConfigManager) -> bool:
    """Resolve effective indexing state based on mode + per-source flag."""
    mode = config.get_indexing_mode()

    if mode == "off":
        return False  # Global disable, ignore per-source
    elif mode == "on":
        # Default enabled, allow per-source opt-out
        return source.indexing_enabled if source.indexing_enabled is not None else True
    else:  # "opt_in"
        # Default disabled, allow per-source opt-in
        return source.indexing_enabled if source.indexing_enabled is not None else False
```

### Toggle Visibility Rules

| Mode | Toggle Visible | Default State |
|------|---------------|---------------|
| "off" | No | N/A (hidden) |
| "on" | Yes | Checked |
| "opt_in" | Yes | Unchecked |

---

## Related Documents

- **PRD**: `docs/project_plans/PRDs/enhancements/configurable-frontmatter-caching-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/enhancements/configurable-frontmatter-caching-v1.md`
- **Parent SPIKE**: `docs/project_plans/SPIKEs/cross-source-artifact-search-spike.md`
- **Context Notes**: `.claude/worknotes/configurable-frontmatter-caching-v1/context.md`
