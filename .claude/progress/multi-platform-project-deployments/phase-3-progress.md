---
type: progress
prd: multi-platform-project-deployments-v1
phase: 3
title: Context Entity Generalization
status: completed
started: '2026-02-08T00:00:00Z'
completed: '2026-02-08T00:00:00Z'
overall_progress: 100
completion_estimate: on-track
total_tasks: 14
completed_tasks: 14
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- data-layer-expert
tasks:
- id: P3-T1
  description: Audit context entity validation layers - Identify all path validation
    in API schemas, core validators, and route-level checks; document validation matrix
    with file, line, current behavior
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 0.5 pts
  priority: critical
- id: P3-T2
  description: Create context-aware path validator utility - Create skillmeat/core/validators/context_path_validator.py
    with validate_context_path() using profile's context_path_prefixes; prevent path
    traversal
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T2
  - P1-T5
  estimated_effort: 1.5 pts
  priority: critical
- id: P3-T3
  description: Refactor API schema validators - Replace hardcoded .claude/ prefix
    check in skillmeat/api/schemas/context_entity.py with profile-aware validator
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T2
  estimated_effort: 1 pt
  priority: high
- id: P3-T4
  description: Refactor core domain validators (3-layer sync) - Update skillmeat/core/validators/context_entity.py
    and skillmeat/api/routers/context_entities.py to use unified profile-aware validator;
    DRY principle; coordinate in single PR
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T2
  estimated_effort: 2 pts
  priority: high
- id: P3-T5
  description: Add project_config_filenames field to DeploymentProfile - Add list[str]
    field to core model and DB model; create migration with sensible defaults per
    platform
  status: completed
  assigned_to:
  - data-layer-expert
  - python-backend-engineer
  dependencies:
  - P1-T5
  - P1-T6
  estimated_effort: 1 pt
  priority: high
- id: P3-T6
  description: Update context entity deployment to profile-aware filenames - Deploy
    logic checks project-config files per profile; context entities deploy alongside
    any profile's project config
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T5
  - P2-T3
  estimated_effort: 1.5 pts
  priority: high
- id: P3-T7
  description: Add profile selector to context entity deploy options - Update CLI
    context deploy with --profile; update API endpoint with deployment_profile_id;
    validation uses selected profile's path rules
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T2
  - P3-T4
  estimated_effort: 1 pt
  priority: high
- id: P3-T8
  description: 'Extend ContextEntity model with target_platforms - Add optional target_platforms:
    list[Platform] | None field; DB column; API schema update'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T1
  estimated_effort: 1 pt
  priority: medium
- id: P3-T9
  description: Implement context entity platform filtering - Check entity's target_platforms
    during deploy; return error if profile platform not in list unless --force flag
    used
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T8
  estimated_effort: 1 pt
  priority: medium
- id: P3-T10
  description: 'Unit tests: context path validator - Test multiple profile configurations,
    path traversal prevention, prefix matching across .claude/.codex/.gemini, platform
    targeting filters'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T2
  - P3-T9
  estimated_effort: 1.5 pts
  priority: high
- id: P3-T11
  description: 'Integration test: context entity deployment across profiles - Test
    project with Claude + Codex profiles; deploy context entity to both; verify path
    rules respected; verify platform targeting'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T6
  - P3-T7
  - P3-T9
  estimated_effort: 1.5 pts
  priority: high
- id: P3-T12
  description: 'Integration test: project config file discovery per profile - Test
    context entity deployment when project-config files exist in different profile
    roots (CLAUDE.md in .claude/, GEMINI.md in .gemini/)'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T6
  estimated_effort: 1.5 pts
  priority: medium
- id: P3-T13
  description: Update context entity API response to include platform info - Extend
    ContextEntityRead schema with target_platforms and deployed_to per-profile breakdown;
    update OpenAPI docs
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T8
  estimated_effort: 1 pt
  priority: medium
- id: P3-T14
  description: 'Backward compatibility: auto-detect project config roots - For existing
    projects without explicit profile config_filenames, auto-detect .claude/*.md config
    files and add to default profile''s context_path_prefixes'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P3-T6
  estimated_effort: 1 pt
  priority: high
parallelization:
  batch_1:
  - P3-T1
  - P3-T8
  batch_2:
  - P3-T2
  - P3-T5
  - P3-T9
  batch_3:
  - P3-T3
  - P3-T4
  - P3-T6
  - P3-T13
  batch_4:
  - P3-T7
  - P3-T10
  - P3-T12
  - P3-T14
  batch_5:
  - P3-T11
  critical_path:
  - P3-T1
  - P3-T2
  - P3-T4
  - P3-T7
  - P3-T11
  estimated_total_time: 18 pts (5 batches)
blockers: []
success_criteria:
- id: SC-1
  description: All three context entity validation layers refactored to unified profile-aware
    validator
  status: completed
- id: SC-2
  description: Path traversal tests pass; security review approved
  status: completed
- id: SC-3
  description: Context entities deployable to multiple profile roots in same project
  status: completed
- id: SC-4
  description: Platform targeting works correctly; --force override tested
  status: completed
- id: SC-5
  description: Project config file detection per profile working
  status: completed
- id: SC-6
  description: API response includes deployed profiles and platform info
  status: completed
- id: SC-7
  description: 'Backward compatibility: existing context entities auto-detect their
    profile'
  status: completed
- id: SC-8
  description: 'Integration tests pass: cross-profile context deployment, config file
    discovery'
  status: completed
files_modified:
- skillmeat/core/validators/context_path_validator.py
- skillmeat/core/validators/context_entity.py
- skillmeat/core/path_resolver.py
- skillmeat/api/schemas/context_entity.py
- skillmeat/api/routers/context_entities.py
- skillmeat/cache/repositories.py
- skillmeat/cli.py
- tests/test_core_context_path_validator.py
- tests/test_context_entity_cross_profile.py
- tests/integration/test_context_cli.py
schema_version: 2
doc_type: progress
feature_slug: multi-platform-project-deployments-v1
---

# Phase 3: Context Entity Generalization

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/multi-platform-project-deployments/phase-3-progress.md -t P3-T1 -s completed
```

---

## Objective

Remove `.claude/`-only assumptions from context entity path validation. Unify three independent validation layers to be profile-aware, allowing context entities to deploy to non-`.claude` profile roots. Introduce support for project config filenames beyond `CLAUDE.md` and profile-scoped deployment options.

---

## Orchestration Quick Reference

**Batch 1** (Parallel - audit + independent model change):
- P3-T1 -> `python-backend-engineer` (0.5 pts)
- P3-T8 -> `python-backend-engineer` (1 pt)

**Batch 2** (Parallel - core validator + DB field + platform filter):
- P3-T2 -> `python-backend-engineer` (1.5 pts)
- P3-T5 -> `data-layer-expert` + `python-backend-engineer` (1 pt)
- P3-T9 -> `python-backend-engineer` (1 pt)

**Batch 3** (Parallel - refactors using validator + deploy logic + response schema):
- P3-T3 -> `python-backend-engineer` (1 pt)
- P3-T4 -> `python-backend-engineer` (2 pts)
- P3-T6 -> `python-backend-engineer` (1.5 pts)
- P3-T13 -> `python-backend-engineer` (1 pt)

**Batch 4** (Parallel - CLI/tests depend on refactors):
- P3-T7 -> `python-backend-engineer` (1 pt)
- P3-T10 -> `python-backend-engineer` (1.5 pts)
- P3-T12 -> `python-backend-engineer` (1.5 pts)
- P3-T14 -> `python-backend-engineer` (1 pt)

**Batch 5** (Sequential - final integration test):
- P3-T11 -> `python-backend-engineer` (1.5 pts)

### Task Delegation Commands

**Batch 1**:
```python
Task("python-backend-engineer", "P3-T1: Audit context entity validation layers. Identify all path validation in: skillmeat/api/schemas/context_entity.py (Pydantic validators), skillmeat/core/validators/context_entity.py (domain validators), skillmeat/api/routers/context_entities.py (route-level checks). Document validation matrix: layer, file, line, current behavior (e.g., 'requires .claude/ prefix'). Show 3 independent checks.")

Task("python-backend-engineer", "P3-T8: Extend ContextEntity model with target_platforms. File: skillmeat/core/models/context_entity.py. Add optional target_platforms: list[Platform] | None field (null = deployable anywhere). Add DB column via migration. Update API schema in skillmeat/api/schemas/context_entity.py.")
```

**Batch 2**:
```python
Task("python-backend-engineer", "P3-T2: Create context-aware path validator utility. File: skillmeat/core/validators/context_path_validator.py. Function: validate_context_path(path, project, profile_id, **opts) -> ValidatedPath. Use profile's context_path_prefixes to validate. Support multiple allowed prefixes per profile. Prevent path traversal. Return clear errors.")

Task("data-layer-expert", "P3-T5: Add project_config_filenames field to DeploymentProfile. Files: skillmeat/core/models/deployment_profile.py, skillmeat/cache/models.py. Add project_config_filenames: list[str] (e.g., ['CLAUDE.md', 'AGENTS.md'] for Claude, ['GEMINI.md'] for Gemini). Create migration with sensible defaults per platform. Update API schema.")

Task("python-backend-engineer", "P3-T9: Implement context entity platform filtering. In context deploy logic, check entity's target_platforms. Return error if profile's platform not in list, unless --force flag used. Clear error messages on platform mismatch.")
```

**Batch 3**:
```python
Task("python-backend-engineer", "P3-T3: Refactor API schema validators. File: skillmeat/api/schemas/context_entity.py. Replace hardcoded .claude/ prefix check with profile-aware validator from context_path_validator.py. Modify to accept optional profile_id in schema (or infer from project context). Update OpenAPI docs.")

Task("python-backend-engineer", "P3-T4: Refactor core domain validators (3-layer sync). Files: skillmeat/core/validators/context_entity.py, skillmeat/api/routers/context_entities.py. Update both to use unified profile-aware validator from context_path_validator.py. All three layers use same validation logic (DRY). Coordinate in single PR.")

Task("python-backend-engineer", "P3-T6: Update context entity deployment to profile-aware filenames. Modify context entity deploy logic to check project-config files per profile (from project_config_filenames). Ensure context entities deploy alongside any profile's project config. Deploy logic looks for per-profile config files as safe deployment roots.")

Task("python-backend-engineer", "P3-T13: Update context entity API response to include platform info. Extend ContextEntityRead schema with target_platforms and deployed_to: { 'claude_code': ['path1'], 'codex': ['path2'] } per-profile breakdown. Update OpenAPI docs.")
```

**Batch 4**:
```python
Task("python-backend-engineer", "P3-T7: Add profile selector to context entity deploy options. CLI: skillmeat context deploy <entity> --to-project <path> --profile codex. API: accept deployment_profile_id. Validation uses selected profile's path rules.")

Task("python-backend-engineer", "P3-T10: Unit tests for context path validator. Test: multiple profile configurations, path traversal prevention, prefix matching across .claude/.codex/.gemini, symlinks, platform targeting filters, platform mismatches. Cover valid paths, invalid paths, multiple prefixes.")

Task("python-backend-engineer", "P3-T12: Integration test: project config file discovery per profile. Test context entity deployment when project-config files exist in different profile roots (CLAUDE.md in .claude/, GEMINI.md in .gemini/). Verify each entity deploys to correct profile root.")

Task("python-backend-engineer", "P3-T14: Backward compatibility: auto-detect project config roots. For existing projects without explicit DeploymentProfile project_config_filenames, auto-detect .claude/*.md config files and add them to default profile's context_path_prefixes. Existing context entities continue working.")
```

**Batch 5**:
```python
Task("python-backend-engineer", "P3-T11: Integration test: context entity deployment across profiles. Create project with Claude + Codex profiles. Deploy context entity to both. Verify each respects profile's path rules. Verify platform targeting works. Test full deploy flow per profile.")
```

---

## Implementation Notes

### Key Decisions
- context_path_validator.py is reusable across context entity, artifact, and future features
- P3-T4 modifies three validation layers simultaneously -- coordinate in single PR
- Backward compatibility via auto-detection (P3-T14)

### Known Gotchas
- Three validation layers currently enforce .claude/ prefix independently
- P3-T4 must be coordinated carefully to avoid merge conflicts across 3 files
- Platform targeting with --force override needs clear UX messaging

---

## Completion Notes

_Fill in when phase is complete._
