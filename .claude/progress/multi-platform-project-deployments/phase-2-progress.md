---
type: progress
prd: multi-platform-project-deployments-v1
phase: 2
title: Deployment Engine Refactor
status: completed
started: '2026-02-07'
completed: '2026-02-07'
overall_progress: 100
completion_estimate: on-track
total_tasks: 17
completed_tasks: 17
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- documentation-writer
tasks:
- id: P2-T1
  description: Inventory all hardcoded .claude/ paths - Audit deployment.py, storage
    layers, watcher, discovery for hardcoded .claude/ strings; document file, line
    number, context
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1 pt
  priority: critical
- id: P2-T2
  description: Create profile-aware path resolver utility - Create skillmeat/core/path_resolver.py
    with resolve_artifact_path, resolve_deployment_path, resolve_config_path, resolve_context_path;
    handle symlinks; validate path traversal
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T5
  - P1-T6
  estimated_effort: 2 pts
  priority: critical
- id: P2-T3
  description: Refactor deployment path resolution in core - Replace hardcoded .claude/
    in skillmeat/core/deployment.py with profile-aware resolution; deploy/undeploy
    accept profile_id parameter
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T2
  - P1-T9
  estimated_effort: 2 pts
  priority: critical
- id: P2-T4
  description: Refactor storage layer path resolution - Replace hardcoded .claude/
    in skillmeat/storage/deployment.py and skillmeat/storage/project.py with profile-aware
    resolver
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T2
  estimated_effort: 2 pts
  priority: high
- id: P2-T5
  description: Refactor discovery to profile-aware scanning - Update skillmeat/core/discovery.py
    to accept optional profile_id; scan all configured profiles when none specified;
    find .codex/, .gemini/, custom roots
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T2
  estimated_effort: 2 pts
  priority: high
- id: P2-T6
  description: Add --profile flag to CLI deploy command - Update skillmeat/cli.py
    deploy with --profile <profile_id> and --all-profiles flags; default to primary
    profile
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T3
  - P2-T4
  estimated_effort: 1.5 pts
  priority: high
- id: P2-T7
  description: Add --profile flag to CLI status/undeploy commands - Update skillmeat
    status --profile and skillmeat undeploy --profile; output per-profile info and
    aggregate stats
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T3
  estimated_effort: 1.5 pts
  priority: high
- id: P2-T8
  description: Update skillmeat init to be profile-aware - Add --profile <profile_id>
    flag; scaffold profile directory structure; backward compatible (no flag = .claude/)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T3
  estimated_effort: 1.5 pts
  priority: high
- id: P2-T9
  description: Create repository for DeploymentProfile queries - Add get_primary_profile,
    get_profile_by_platform, list_all_profiles, ensure_default_claude_profile methods
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-T10
  estimated_effort: 1 pt
  priority: high
- id: P2-T10
  description: Add profile parameter to API deploy endpoints - Update POST /artifacts/{artifact_id}/deploy
    to accept optional deployment_profile_id; add all_profiles option
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T3
  - P2-T11
  estimated_effort: 1.5 pts
  priority: high
- id: P2-T11
  description: Add profile parameter to API status/undeploy endpoints - Update GET
    /projects/{project_id}/status to segment by profile; add optional profile_id query
    param
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T3
  estimated_effort: 1.5 pts
  priority: high
- id: P2-T12
  description: Update deployment router documentation - Update docstrings and OpenAPI
    descriptions for new deployment_profile_id parameter, semantics, and examples
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - P2-T10
  - P2-T11
  estimated_effort: 0.5 pts
  priority: medium
- id: P2-T13
  description: 'Integration test: deploy same artifact to multiple profiles - Test
    deploying one artifact to Claude and Codex profiles; verify separate tracking;
    verify undeploy isolation'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T3
  - P2-T6
  estimated_effort: 2 pts
  priority: high
- id: P2-T14
  description: 'Integration test: profile-aware discovery and status - Test project
    with 3 profiles; deploy to different profiles; verify discovery and per-profile
    status breakdown'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T5
  - P2-T11
  estimated_effort: 2 pts
  priority: high
- id: P2-T15
  description: 'Integration test: skillmeat init with profile - Test init --profile
    codex scaffolds correct directory; test default profile; test --all-profiles flag'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T8
  estimated_effort: 1 pt
  priority: medium
- id: P2-T16
  description: Symlink-aware path resolution (bridge to Phase 0) - Add explicit symlink
    detection in path resolver; log warning for symlink scenarios; test symlink resolution
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T2
  estimated_effort: 1 pt
  priority: medium
- id: P2-T17
  description: 'Backward compatibility: auto-create default Claude profile - When
    opening existing project without profiles, auto-create claude_code profile matching
    current .claude/ structure'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T9
  estimated_effort: 1 pt
  priority: high
parallelization:
  batch_1:
  - P2-T1
  batch_2:
  - P2-T2
  - P2-T9
  batch_3:
  - P2-T3
  - P2-T4
  - P2-T5
  - P2-T16
  batch_4:
  - P2-T6
  - P2-T7
  - P2-T8
  - P2-T11
  - P2-T17
  batch_5:
  - P2-T10
  - P2-T12
  - P2-T13
  - P2-T14
  - P2-T15
  critical_path:
  - P2-T1
  - P2-T2
  - P2-T3
  - P2-T6
  - P2-T13
  estimated_total_time: 25 pts (5 batches)
blockers: []
success_criteria:
- id: SC-1
  description: All hardcoded .claude/ paths identified and refactored
  status: completed
- id: SC-2
  description: Path resolver utility tested (symlinks, path traversal, errors)
  status: completed
- id: SC-3
  description: CLI --profile flags working on deploy, status, undeploy, init
  status: completed
- id: SC-4
  description: --all-profiles deploys cleanly to all configured profiles
  status: completed
- id: SC-5
  description: API endpoints accept and validate deployment_profile_id
  status: completed
- id: SC-6
  description: 'Integration tests pass: multi-profile deployment, discovery, status'
  status: completed
- id: SC-7
  description: 'Backward compatibility: existing Claude-only projects auto-get default
    profile'
  status: completed
- id: SC-8
  description: Symlink edge cases handled (Phase 0 bridge scenarios)
  status: completed
files_modified:
- skillmeat/core/deployment.py
- skillmeat/core/path_resolver.py
- skillmeat/core/discovery.py
- skillmeat/storage/deployment.py
- skillmeat/storage/project.py
- skillmeat/cli.py
- skillmeat/cache/repositories/deployment_profile_repository.py
- skillmeat/api/routers/deployments.py
- tests/test_core_path_resolver.py
- tests/test_core_deployment_profile_aware.py
- tests/test_discovery_profile_aware.py
- tests/test_cli_init_profile.py
- tests/test_symlink_path_resolution.py
progress: 100
updated: '2026-02-07'
schema_version: 2
doc_type: progress
feature_slug: multi-platform-project-deployments-v1
---

# Phase 2: Deployment Engine Refactor

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/multi-platform-project-deployments/phase-2-progress.md -t P2-T1 -s completed
```

---

## Objective

Remove hardcoded `.claude/` assumptions from the deployment engine. Introduce profile-based path resolution, update deploy/undeploy/status flows to accept `--profile` flags, and extend CLI/API endpoints to support multi-platform deployments. This is the largest phase and unblocks Phases 3-5.

---

## Orchestration Quick Reference

**Batch 1** (Sequential - audit first):
- P2-T1 -> `python-backend-engineer` (1 pt)

**Batch 2** (Parallel - path resolver + repo queries):
- P2-T2 -> `python-backend-engineer` (2 pts)
- P2-T9 -> `python-backend-engineer` (1 pt)

**Batch 3** (Parallel - core refactors depend on path resolver):
- P2-T3 -> `python-backend-engineer` (2 pts)
- P2-T4 -> `python-backend-engineer` (2 pts)
- P2-T5 -> `python-backend-engineer` (2 pts)
- P2-T16 -> `python-backend-engineer` (1 pt)

**Batch 4** (Parallel - CLI/API depend on core refactors):
- P2-T6 -> `python-backend-engineer` (1.5 pts)
- P2-T7 -> `python-backend-engineer` (1.5 pts)
- P2-T8 -> `python-backend-engineer` (1.5 pts)
- P2-T11 -> `python-backend-engineer` (1.5 pts)
- P2-T17 -> `python-backend-engineer` (1 pt)

**Batch 5** (Parallel - tests and dependent endpoints):
- P2-T10 -> `python-backend-engineer` (1.5 pts)
- P2-T12 -> `documentation-writer` (0.5 pts)
- P2-T13 -> `python-backend-engineer` (2 pts)
- P2-T14 -> `python-backend-engineer` (2 pts)
- P2-T15 -> `python-backend-engineer` (1 pt)

### Task Delegation Commands

**Batch 1**:
```python
Task("python-backend-engineer", "P2-T1: Inventory all hardcoded .claude/ paths. Audit: skillmeat/core/deployment.py, skillmeat/storage/deployment.py, skillmeat/storage/project.py, skillmeat/cache/watcher.py, skillmeat/core/discovery.py. Document each file, line number, and context (path resolution, config file location, artifact path). Expected 8-12 occurrences.")
```

**Batch 2**:
```python
Task("python-backend-engineer", "P2-T2: Create profile-aware path resolver utility. File: skillmeat/core/path_resolver.py. Functions: resolve_artifact_path(artifact, profile) -> Path, resolve_deployment_path(deployment, profile) -> Path, resolve_config_path(project, profile) -> Path, resolve_context_path(entity, profile) -> Path. Handle symlink resolution via Path.resolve(). Validate target inside profile root (prevent path traversal). Return informative errors.")

Task("python-backend-engineer", "P2-T9: Add query methods to deployment_profile_repository.py. Methods: get_primary_profile(project_id), get_profile_by_platform(project_id, platform), list_all_profiles(project_id), ensure_default_claude_profile(project_id) for backward compat. Handle projects with no profiles (fallback to default Claude).")
```

**Batch 3**:
```python
Task("python-backend-engineer", "P2-T3: Refactor deployment path resolution in core. File: skillmeat/core/deployment.py (lines 215, 389). Replace hardcoded .claude/ with profile-aware resolution from path_resolver.py. deploy() and undeploy() accept profile_id parameter. Deployment records populate deployment_profile_id, platform, profile_root_dir. Update error messages to include profile info.")

Task("python-backend-engineer", "P2-T4: Refactor storage layer path resolution. Files: skillmeat/storage/deployment.py (lines 27, 92, 205), skillmeat/storage/project.py (line 95). Replace hardcoded .claude/ with profile-aware resolver. DeploymentTracker: .claude/.skillmeat-deployment.toml -> {profile.root_dir}/.skillmeat-deployment.toml. ProjectMetadata similarly.")

Task("python-backend-engineer", "P2-T5: Refactor discovery to profile-aware scanning. File: skillmeat/core/discovery.py. Accept optional profile_id parameter. When no profile, scan all configured profiles. Return deployment counts segmented by profile. discover_projects() finds .codex/, .gemini/, custom roots in addition to .claude/. Return ProjectDiscovery with profiles_found list.")

Task("python-backend-engineer", "P2-T16: Symlink-aware path resolution (bridge to Phase 0). File: skillmeat/core/path_resolver.py. Add explicit symlink detection; if target resolves through symlink, log warning. Test with both symlinks and native dirs. Return real path after resolution.")
```

**Batch 4**:
```python
Task("python-backend-engineer", "P2-T6: Add --profile flag to CLI deploy command. File: skillmeat/cli.py. Add --profile <profile_id> to deploy command. If not specified, use project's primary/default profile. Add --all-profiles flag to deploy to all. Update help text.")

Task("python-backend-engineer", "P2-T7: Add --profile flag to CLI status/undeploy commands. File: skillmeat/cli.py. Update status --profile and undeploy --profile. Output shows which profiles have artifact deployed. Aggregate stats show total across profiles.")

Task("python-backend-engineer", "P2-T8: Update skillmeat init to be profile-aware. File: skillmeat/cli.py. Add --profile <profile_id> flag. init --profile codex creates .codex/ directory tree. Creates project metadata with that profile as primary. No flag = .claude/ (backward compatible).")

Task("python-backend-engineer", "P2-T11: Add profile parameter to API status/undeploy endpoints. File: skillmeat/api/routers/deployments.py. GET /projects/{project_id}/status segments deployments by profile: deployments: { [profile_id]: [artifacts] }. Add optional profile_id query param to filter. Update undeploy similarly.")

Task("python-backend-engineer", "P2-T17: Backward compatibility auto-create default Claude profile. On opening existing project without profiles, auto-create claude_code profile matching .claude/ structure. No manual migration needed. Transparent backfill. Uses ensure_default_claude_profile from repo.")
```

**Batch 5**:
```python
Task("python-backend-engineer", "P2-T10: Add profile parameter to API deploy endpoints. File: skillmeat/api/routers/deployments.py. POST /artifacts/{artifact_id}/deploy accepts optional deployment_profile_id in body. If not specified, use primary profile. Add all_profiles: bool = False. Validate profile exists (400 if not). Response includes which profiles deployed to.")

Task("documentation-writer", "P2-T12: Update deployment router documentation. File: skillmeat/api/routers/deployments.py. Update docstrings and OpenAPI descriptions for deployment_profile_id parameter. Add examples showing --profile codex usage. Include migration guidance for existing projects.")

Task("python-backend-engineer", "P2-T13: Integration test: deploy same artifact to multiple profiles. Create project with 2 profiles (Claude, Codex). Deploy same artifact to both. Verify separate deployment records. Undeploy from one, verify other still exists.")

Task("python-backend-engineer", "P2-T14: Integration test: profile-aware discovery and status. Create project with 3 profiles. Deploy artifacts to different profiles. Verify discovery finds all profiles. Verify status shows per-profile breakdown.")

Task("python-backend-engineer", "P2-T15: Integration test: skillmeat init with profile. Test init --profile codex scaffolds correct directory. Test init defaults to Claude. Verify directory structure matches profile root.")
```

---

## Implementation Notes

### Key Decisions
- path_resolver.py is the centerpiece; all profile-aware logic encapsulated there
- P2-T17 auto-creates default profile for old projects (zero manual migration)
- P2-T16 bridges Phase 0 adapter scenarios with logging

### Known Gotchas
- Hardcoded paths may exist in test fixtures -- check test files too
- API contract change: deploy response now includes deployment_profile_id
- Symlink resolution can differ between macOS and Linux
- Ensure --all-profiles handles projects with only 1 profile gracefully

---

## Completion Notes

_Fill in when phase is complete._
