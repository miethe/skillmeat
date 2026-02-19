---
type: progress
prd: enhanced-frontmatter-utilization
phase: 0
status: pending
progress: 0
created: 2026-01-21
updated: 2026-01-21
tasks:
- id: P0-T1
  name: Create Platform enum
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  effort: 1
- id: P0-T2
  name: Create Tool enum with all 17 Claude Code tools
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  effort: 2
- id: P0-T3
  name: Create frontend Platform and Tool type definitions
  status: pending
  assigned_to:
  - ui-engineer
  dependencies:
  - P0-T1
  - P0-T2
  model: sonnet
  effort: 2
- id: P0-T4
  name: Add tools field to backend Artifact/ArtifactMetadata
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P0-T2
  model: opus
  effort: 2
- id: P0-T5
  name: Add tools field to frontend Artifact types
  status: pending
  assigned_to:
  - ui-engineer
  dependencies:
  - P0-T3
  - P0-T4
  model: sonnet
  effort: 1
- id: P1-T1
  name: Add frontmatter parsing to artifact detection
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P0-T4
  model: opus
  effort: 3
- id: P1-T2
  name: Implement description auto-population from frontmatter
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T1
  model: opus
  effort: 2
- id: P1-T3
  name: Implement tools extraction from frontmatter
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T1
  - P0-T2
  model: opus
  effort: 3
- id: P1-T4
  name: Update API schemas for tools field
  status: pending
  assigned_to:
  - backend-architect
  dependencies:
  - P0-T4
  model: sonnet
  effort: 2
- id: P1-T5
  name: Database migration for tools field
  status: pending
  assigned_to:
  - data-layer-expert
  dependencies:
  - P0-T4
  model: opus
  effort: 2
- id: P1-T6
  name: Unit tests for frontmatter extraction
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T1
  - P1-T2
  - P1-T3
  model: sonnet
  effort: 2
- id: P2-T1
  name: Create LinkedArtifactReference dataclass
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T1
  model: opus
  effort: 2
- id: P2-T2
  name: Add linked_artifacts field to Artifact model
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T1
  model: opus
  effort: 2
- id: P2-T3
  name: Implement auto-linking logic during import
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T2
  model: opus
  effort: 4
- id: P2-T4
  name: Create unlinked_references tracking
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T3
  model: opus
  effort: 2
- id: P2-T5
  name: API endpoints for manual artifact linking
  status: pending
  assigned_to:
  - backend-architect
  dependencies:
  - P2-T2
  model: opus
  effort: 3
- id: P2-T6
  name: Frontend types for linked artifacts
  status: pending
  assigned_to:
  - ui-engineer
  dependencies:
  - P2-T1
  model: sonnet
  effort: 2
- id: P2-T7
  name: Unit tests for artifact linking
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T3
  - P2-T4
  model: sonnet
  effort: 1
- id: P3-T1
  name: Update ContentPane to exclude raw frontmatter
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P1-T1
  model: opus
  effort: 2
- id: P3-T2
  name: Create LinkedArtifactsSection component
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-T6
  model: opus
  effort: 4
- id: P3-T3
  name: Create ArtifactLinkingDialog component
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-T5
  - P2-T6
  model: opus
  effort: 5
- id: P3-T4
  name: Add tools filter to artifact search
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - P0-T5
  - P1-T4
  model: sonnet
  effort: 3
- id: P3-T5
  name: Integration testing for linking UI
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P3-T2
  - P3-T3
  model: sonnet
  effort: 2
- id: P3-T6
  name: E2E tests for complete workflow
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - P3-T1
  - P3-T2
  - P3-T3
  - P3-T4
  model: sonnet
  effort: 2
parallelization:
  batch_0_1:
  - P0-T1
  - P0-T2
  batch_0_2:
  - P0-T3
  - P0-T4
  batch_0_3:
  - P0-T5
  batch_1_1:
  - P1-T1
  - P1-T4
  - P1-T5
  batch_1_2:
  - P1-T2
  - P1-T3
  batch_1_3:
  - P1-T6
  batch_2_1:
  - P2-T1
  batch_2_2:
  - P2-T2
  - P2-T6
  batch_2_3:
  - P2-T3
  - P2-T5
  batch_2_4:
  - P2-T4
  - P2-T7
  batch_3_1:
  - P3-T1
  - P3-T4
  batch_3_2:
  - P3-T2
  batch_3_3:
  - P3-T3
  batch_3_4:
  - P3-T5
  - P3-T6
schema_version: 2
doc_type: progress
feature_slug: enhanced-frontmatter-utilization
---

# Enhanced Frontmatter Utilization - Progress Tracking

## Overview

| Phase | Name | Effort | Status |
|-------|------|--------|--------|
| 0 | Enums & Foundations | 8 pts | pending |
| 1 | Backend Extraction | 14 pts | pending |
| 2 | Artifact Linking | 16 pts | pending |
| 3 | UI Components | 18 pts | pending |
| **Total** | | **56 pts** | |

## Quick Reference - Task() Commands

### Phase 0: Enums & Foundations
```python
# Batch 0.1 (parallel)
Task("python-backend-engineer", "Create Platform enum in skillmeat/core/artifact.py with CLAUDE_CODE, CURSOR, OTHER values", model="sonnet")
Task("python-backend-engineer", "Create Tool enum in skillmeat/core/artifact.py with all 17 Claude Code tools", model="sonnet")

# Batch 0.2 (parallel, after 0.1)
Task("ui-engineer", "Create Platform and Tool TypeScript types in skillmeat/web/types/artifact.ts matching backend enums", model="sonnet")
Task("python-backend-engineer", "Add tools: List[Tool] field to ArtifactMetadata in skillmeat/core/artifact.py", model="opus")

# Batch 0.3 (after 0.2)
Task("ui-engineer", "Add tools field to frontend Artifact and ArtifactMetadata interfaces", model="sonnet")
```

### Phase 1: Backend Extraction
```python
# Batch 1.1 (parallel)
Task("python-backend-engineer", "Add frontmatter parsing to artifact detection in skillmeat/core/artifact_detection.py", model="opus")
Task("backend-architect", "Update API schemas in skillmeat/api/schemas/artifact.py for tools field", model="sonnet")
Task("data-layer-expert", "Create Alembic migration for tools field in artifact table", model="opus")

# Batch 1.2 (parallel, after 1.1)
Task("python-backend-engineer", "Implement description auto-population from frontmatter during artifact import", model="opus")
Task("python-backend-engineer", "Implement tools extraction from frontmatter tools/allowed-tools fields", model="opus")

# Batch 1.3 (after 1.2)
Task("python-backend-engineer", "Write unit tests for frontmatter extraction and tools parsing", model="sonnet")
```

### Phase 2: Artifact Linking
```python
# Batch 2.1
Task("python-backend-engineer", "Create LinkedArtifactReference dataclass with name, artifact_type, artifact_id, source_field", model="opus")

# Batch 2.2 (parallel)
Task("python-backend-engineer", "Add linked_artifacts and unlinked_references fields to Artifact model", model="opus")
Task("ui-engineer", "Create LinkedArtifactReference TypeScript interface matching backend", model="sonnet")

# Batch 2.3 (parallel, after 2.2)
Task("python-backend-engineer", "Implement auto-linking logic during artifact import to match skills by name within source", model="opus")
Task("backend-architect", "Create API endpoints for manual artifact linking CRUD operations", model="opus")

# Batch 2.4 (after 2.3)
Task("python-backend-engineer", "Implement unlinked_references tracking for unmatched frontmatter references", model="opus")
Task("python-backend-engineer", "Write unit tests for artifact linking and auto-link logic", model="sonnet")
```

### Phase 3: UI Components
```python
# Batch 3.1 (parallel)
Task("ui-engineer-enhanced", "Update ContentPane to use stripFrontmatter() when FrontmatterDisplay is rendered", model="opus")
Task("frontend-developer", "Add tools filter to artifact search/list pages", model="sonnet")

# Batch 3.2
Task("ui-engineer-enhanced", "Create LinkedArtifactsSection component showing linked and unlinked artifacts", model="opus")

# Batch 3.3 (after 3.2)
Task("ui-engineer-enhanced", "Create ArtifactLinkingDialog for searching and linking Collection artifacts", model="opus")

# Batch 3.4 (after 3.3)
Task("ui-engineer-enhanced", "Write integration tests for LinkedArtifactsSection and ArtifactLinkingDialog", model="sonnet")
Task("frontend-developer", "Write E2E tests for complete frontmatter import → view → link workflow", model="sonnet")
```

## CLI Updates

Status updates via CLI (0 tokens):
```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/enhanced-frontmatter-utilization/all-phases-progress.md \
  -t P0-T1 -s completed
```

Batch updates:
```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/enhanced-frontmatter-utilization/all-phases-progress.md \
  --updates "P0-T1:completed,P0-T2:completed"
```

## Quality Gates

| Phase | Gate | Criteria |
|-------|------|----------|
| 0 | Enums Complete | All 17 tools enumerated, Platform enum created, frontend types synced |
| 1 | Extraction Complete | >95% description auto-population, >80% tools extraction, unit tests passing |
| 2 | Linking Complete | >70% auto-link success, unlinked refs tracked, API endpoints working |
| 3 | UI Complete | ContentPane excludes raw FM, linking UI functional, E2E tests passing |

## Related Documents

- PRD: `docs/project_plans/PRDs/features/enhanced-frontmatter-utilization-v1.md`
- Implementation Plan: `docs/project_plans/implementation_plans/features/enhanced-frontmatter-utilization-v1.md`
- Phase Details:
  - `docs/project_plans/implementation_plans/features/enhanced-frontmatter-utilization-v1/phase-0-enums-foundations.md`
  - `docs/project_plans/implementation_plans/features/enhanced-frontmatter-utilization-v1/phase-1-backend-extraction.md`
  - `docs/project_plans/implementation_plans/features/enhanced-frontmatter-utilization-v1/phase-2-artifact-linking.md`
  - `docs/project_plans/implementation_plans/features/enhanced-frontmatter-utilization-v1/phase-3-ui-components.md`
