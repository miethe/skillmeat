---
type: progress
prd: multi-platform-project-deployments-v1
phase: 0
title: Adapter Baseline
status: planning
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- documentation-writer
- python-backend-engineer
contributors: []
tasks:
- id: P0-T1
  description: Finalize & document adapter script - Review setup_agent_platform_links.sh
    for completeness; add inline documentation; verify flag handling (--install-codex-home-skills)
  status: pending
  assigned_to:
  - documentation-writer
  dependencies: []
  estimated_effort: 0.5 pts
  priority: high
- id: P0-T2
  description: Write adapter usage guide - Create doc explaining what the adapter
    does, when to use it (vs native deployments in Phase 2+), limitations, and troubleshooting
  status: pending
  assigned_to:
  - documentation-writer
  dependencies:
  - P0-T1
  estimated_effort: 0.5 pts
  priority: medium
- id: P0-T3
  description: Test adapter on macOS, Linux, Windows - Manual or automated tests verify
    symlinks created correctly; --install-codex-home-skills works with default and
    custom CODEX_HOME
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P0-T1
  estimated_effort: 0.5 pts
  priority: high
- id: P0-T4
  description: Add symlink safety warnings to CLI - When running skillmeat init or
    skillmeat deploy in a project with adapter symlinks, emit informational warning
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P0-T1
  estimated_effort: 0.5 pts
  priority: medium
parallelization:
  batch_1:
  - P0-T1
  batch_2:
  - P0-T2
  - P0-T3
  - P0-T4
  critical_path:
  - P0-T1
  - P0-T3
  estimated_total_time: 1 pt (2 batches)
blockers: []
success_criteria:
- id: SC-1
  description: setup_agent_platform_links.sh production-ready and tested on 3+ OSes
  status: pending
- id: SC-2
  description: Inline documentation and usage guide complete and reviewed
  status: pending
- id: SC-3
  description: CLI warnings for symlink scenarios working
  status: pending
- id: SC-4
  description: No regressions to existing skillmeat init or skillmeat deploy behavior
  status: pending
files_modified:
- scripts/setup_agent_platform_links.sh
- docs/guides/adapter-strategy.md
- skillmeat/cli.py
schema_version: 2
doc_type: progress
feature_slug: multi-platform-project-deployments-v1
---

# Phase 0: Adapter Baseline

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/multi-platform-project-deployments/phase-0-progress.md -t P0-T1 -s completed
```

---

## Objective

Enable existing projects to work with multiple agent platforms (Codex, Gemini) via symlink-based adapters without modifying the underlying deployment architecture. Ships independently as a temporary bridge until native multi-platform support arrives in Phases 1-5.

---

## Orchestration Quick Reference

**Batch 1** (Sequential - foundation):
- P0-T1 -> `documentation-writer` (0.5 pts)

**Batch 2** (Parallel - all depend on P0-T1):
- P0-T2 -> `documentation-writer` (0.5 pts)
- P0-T3 -> `python-backend-engineer` (0.5 pts)
- P0-T4 -> `python-backend-engineer` (0.5 pts)

### Task Delegation Commands

**Batch 1**:
```python
Task("documentation-writer", "P0-T1: Finalize & document adapter script. File: scripts/setup_agent_platform_links.sh. Review for completeness, add inline documentation, verify flag handling (--install-codex-home-skills). Script must be production-ready with all flags documented.")
```

**Batch 2**:
```python
Task("documentation-writer", "P0-T2: Write adapter usage guide. File: docs/guides/adapter-strategy.md. Cover use cases, symlink semantics, cross-platform behavior (macOS/Linux/Windows), CODEX_HOME environment handling, limitations vs native deployments (Phase 2+), and troubleshooting.")

Task("python-backend-engineer", "P0-T3: Test adapter on macOS, Linux, Windows. Verify symlinks created correctly by setup_agent_platform_links.sh; --install-codex-home-skills works with default and custom CODEX_HOME; symlink targets are readable. No permission errors on any OS.")

Task("python-backend-engineer", "P0-T4: Add symlink safety warnings to CLI. Files: skillmeat/cli.py. When running skillmeat init or skillmeat deploy in a project with adapter symlinks, emit informational warning: 'This project uses adapter symlinks; changes here affect multiple platforms'. Warning must not block operations.")
```

---

## Implementation Notes

### Key Decisions
- Phase 0 is a non-invasive bridge; no schema/model/API changes
- Symlinks are intentionally transparent (writes resolve through symlink)
- Ships independently from Phases 1-5

### Known Gotchas
- Windows symlink support requires elevated privileges or Developer Mode
- Symlink targets must be validated to prevent dangling links
- Phase 2 will add symlink-aware path resolution to prevent cross-profile mutations

---

## Completion Notes

_Fill in when phase is complete._
