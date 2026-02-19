---
title: 'Phase 2: Deployment Engine Refactor'
parent: ../multi-platform-project-deployments-v1.md
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: multi-platform-project-deployments
prd_ref: null
plan_ref: null
---
# Phase 2: Deployment Engine Refactor

**Duration**: 2 weeks
**Dependencies**: Phase 1 complete (models, schemas, DB tables)
**Total Effort**: 25 story points

## Overview

Phase 2 is the critical path refactor that removes hardcoded `.claude/` assumptions from the deployment engine. It introduces profile-based path resolution, updates deploy/undeploy/status flows to accept `--profile` flags, and extends CLI/API endpoints to support multi-platform deployments. This is the largest phase and unblocks Phases 3-5.

## Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P2-T1 | Inventory all hardcoded `.claude/` paths | Audit `skillmeat/core/deployment.py`, `skillmeat/storage/deployment.py`, `skillmeat/storage/project.py`, `skillmeat/cache/watcher.py`, `skillmeat/core/discovery.py` for hardcoded `.claude/` strings; document in task output | Document lists each file, line number, context (path resolution, config file location, artifact path); estimated 8-12 occurrences | 1 pt | python-backend-engineer | None |
| P2-T2 | Create profile-aware path resolver utility | Create `skillmeat/core/path_resolver.py` with functions: `resolve_artifact_path(artifact, profile) -> Path`, `resolve_deployment_path(deployment, profile) -> Path`, `resolve_config_path(project, profile) -> Path`, `resolve_context_path(entity, profile) -> Path`; handle symlink resolution; validate target is inside profile root | All resolvers use `Path.resolve()`; test with symlinks and native paths; validators prevent path traversal; return informative errors | 2 pts | python-backend-engineer | P1-T5, P1-T6 |
| P2-T3 | Refactor deployment path resolution in core | Replace hardcoded `.claude/` in `skillmeat/core/deployment.py` lines 215, 389 with profile-aware resolution using `path_resolver.py`; ensure `deploy()` and `undeploy()` methods accept `profile_id` parameter; update error messages to include profile info | `deploy()` creates artifacts at profile root; `undeploy()` removes from correct profile; deployment records populate `deployment_profile_id`, `platform`, `profile_root_dir` fields | 2 pts | python-backend-engineer | P2-T2, P1-T9 |
| P2-T4 | Refactor storage layer path resolution | Replace hardcoded `.claude/` in `skillmeat/storage/deployment.py` (lines 27, 92, 205) and `skillmeat/storage/project.py` (line 95) with profile-aware resolver; update DeploymentTracker to accept profile when resolving paths; update ProjectMetadata to accept profile | DeploymentTracker resolves `.claude/.skillmeat-deployment.toml` → `{profile.root_dir}/.skillmeat-deployment.toml`; ProjectMetadata resolves `.claude/.skillmeat-project.toml` → `{profile.root_dir}/.skillmeat-project.toml` | 2 pts | python-backend-engineer | P2-T2 |
| P2-T5 | Refactor discovery to profile-aware scanning | Update `skillmeat/core/discovery.py` to accept optional `profile_id` parameter; when no profile specified, scan all configured profiles; return deployment counts segmented by profile; update `discover_projects()` to find not just `.claude/` but also `.codex/`, `.gemini/`, custom roots | Discovery finds projects with any profile; returns `ProjectDiscovery` with `profiles_found` list; correctly handles projects with multiple profiles | 2 pts | python-backend-engineer | P2-T2 |
| P2-T6 | Add --profile flag to CLI deploy command | Update `skillmeat/cli.py` deploy command to accept `--profile <profile_id>`; if not specified, use project's primary/default profile; add `--all-profiles` flag to deploy to all configured profiles at once; update help text | `skillmeat deploy <artifact> --profile codex` works; `--all-profiles` deployer all profiles; default behavior (no flag) uses primary profile | 1.5 pts | python-backend-engineer | P2-T3, P2-T4 |
| P2-T7 | Add --profile flag to CLI status/undeploy commands | Update `skillmeat status --profile <id>` and `skillmeat undeploy <artifact> --profile <id>` commands; ensure both output per-profile info and aggregate stats | Commands accept --profile; output shows which profiles have artifact deployed; aggregate stats show total across profiles | 1.5 pts | python-backend-engineer | P2-T3 |
| P2-T8 | Update `skillmeat init` to be profile-aware | Add `--profile <profile_id>` flag to `skillmeat init` (e.g., `skillmeat init --profile codex`); if specified, scaffold that profile's directory structure and create default profile configuration; if not specified, default to `claude_code` profile | `init --profile codex` creates `.codex/` directory tree with correct layout; creates project metadata with that profile as primary; backward compatible (no flag = `.claude/`) | 1.5 pts | python-backend-engineer | P2-T3 |
| P2-T9 | Create repository for DeploymentProfile queries | Add methods to `skillmeat/cache/repositories/deployment_profile_repository.py`: `get_primary_profile(project_id)`, `get_profile_by_platform(project_id, platform)`, `list_all_profiles(project_id)`, `ensure_default_claude_profile(project_id)` (for backward compat) | Repos support querying profiles by type; handles projects with no profiles (fallback to default Claude); used by Phase 2-5 logic | 1 pt | python-backend-engineer | P1-T10 |
| P2-T10 | Add profile parameter to API deploy endpoints | Update `POST /artifacts/{artifact_id}/deploy` endpoint to accept optional `deployment_profile_id` in request body; if not specified, use project's primary profile; add `all_profiles: bool = False` to deploy all profiles | Endpoint validates `deployment_profile_id` exists for project; returns 400 if profile not found; response includes which profiles artifact deployed to | 1.5 pts | python-backend-engineer | P2-T3, P2-T11 |
| P2-T11 | Add profile parameter to API status/undeploy endpoints | Update `GET /projects/{project_id}/status` to segment deployments by profile in response; add optional `profile_id` query param to filter to single profile; update undeploy endpoint similarly | Status endpoint response includes `deployments: { [profile_id]: [artifacts] }`; profile filter works correctly | 1.5 pts | python-backend-engineer | P2-T3 |
| P2-T12 | Update deployment router documentation | Update docstrings and OpenAPI descriptions in `skillmeat/api/routers/deployments.py` to document new `deployment_profile_id` parameter, semantics, and examples | OpenAPI schema includes profile params; examples show `--profile codex` usage; migration guidance for existing projects | 0.5 pts | documentation-writer | P2-T10, P2-T11 |
| P2-T13 | Integration test: deploy same artifact to multiple profiles | Create test deploying one artifact to Claude and Codex profiles in same project; verify both deployments tracked separately; verify undeploy from one profile doesn't affect other | Test creates project with 2 profiles; deploys same artifact to both; verifies deployment records; undeloys from one and checks the other still exists | 2 pts | python-backend-engineer | P2-T3, P2-T6 |
| P2-T14 | Integration test: profile-aware discovery and status | Create test with project containing 3 profiles; deploy artifacts to different profiles; verify discovery finds all profiles; verify status shows per-profile breakdown | Test exercises discovery and status with multiple profiles; validates aggregation and per-profile filtering | 2 pts | python-backend-engineer | P2-T5, P2-T11 |
| P2-T15 | Integration test: `skillmeat init` with profile | Test `skillmeat init --profile codex` scaffolds correct directory; test `skillmeat init` defaults to Claude; test --all-profiles flag | Tests cover both explicit and default profile init; verify directory structure matches profile root | 1 pt | python-backend-engineer | P2-T8 |
| P2-T16 | Symlink-aware path resolution (bridge to Phase 0) | Add explicit symlink detection in path resolver; if target resolves through symlink, log warning to help debug Phase 0 adapter scenarios; add test case for symlink resolution | Path resolver detects symlinks; returns real path after resolution; test verifies behavior with both symlinks and native dirs | 1 pt | python-backend-engineer | P2-T2 |
| P2-T17 | Backward compatibility: auto-create default Claude profile | When opening existing project without profiles, auto-create `claude_code` profile matching current `.claude/` structure; no manual migration needed for users | On first load of old project, default profile created transparently; backfill completes in Phase 5 | 1 pt | python-backend-engineer | P2-T9 |

## Quality Gates

- [ ] All hardcoded `.claude/` paths identified and refactored
- [ ] Path resolver utility thoroughly tested (symlinks, path traversal protection, error handling)
- [ ] CLI `--profile` flags working on all commands (deploy, status, undeploy, init)
- [ ] `--all-profiles` flag deploys cleanly to all configured profiles
- [ ] API endpoints accept and validate `deployment_profile_id` parameter
- [ ] Integration tests pass: multi-profile deployment, discovery, status aggregation
- [ ] Backward compatibility: existing Claude-only projects auto-get default profile
- [ ] Deployment records correctly populate `deployment_profile_id`, `platform`, `profile_root_dir`
- [ ] Symlink edge cases handled (Phase 0 bridge scenarios)
- [ ] All new/modified code reviewed and >85% test coverage

## Key Files

**Core Logic** (modified):
- `skillmeat/core/deployment.py` — Profile-aware deploy/undeploy, replace lines 215, 389 (P2-T3)
- `skillmeat/core/path_resolver.py` — New (P2-T2)
- `skillmeat/core/discovery.py` — Profile-aware scanning (P2-T5)

**Storage Layer** (modified):
- `skillmeat/storage/deployment.py` — Profile-aware DeploymentTracker, replace lines 27, 92, 205 (P2-T4)
- `skillmeat/storage/project.py` — Profile-aware ProjectMetadata, replace line 95 (P2-T4)

**CLI** (modified):
- `skillmeat/cli.py` — Add `--profile` and `--all-profiles` flags to deploy, status, undeploy, init (P2-T6, P2-T7, P2-T8)

**Repository** (modified):
- `skillmeat/cache/repositories.py` — Add deployment profile query helpers (P2-T9)

**API** (modified):
- `skillmeat/api/routers/deployments.py` — Accept `deployment_profile_id`, update endpoints (P2-T10, P2-T11, P2-T12)

**Tests** (new):
- `tests/test_core_path_resolver.py` — Path resolver unit tests (P2-T2)
- `tests/test_core_deployment_profile_aware.py` — Multi-profile deployment tests (P2-T13)
- `tests/test_discovery_profile_aware.py` — Discovery and status tests (P2-T14)
- `tests/test_cli_init_profile.py` — `skillmeat init --profile` tests (P2-T15)
- `tests/test_symlink_path_resolution.py` — Symlink edge cases (P2-T16)

## Integration Notes

**Critical Path Task**: This phase is the longest and unblocks Phases 3-5. Phases 2-3 can run partially in parallel (context entity validation can start once P2-T2 path resolver is ready), but Phase 4 discovery/UI requires P2 deployment logic to be solid.

**Path Resolver Design**: The new `path_resolver.py` is the centerpiece. It encapsulates all profile-aware logic, making subsequent phases and maintenance easier.

**Backward Compatibility**: P2-T17 auto-creates default profile for old projects, ensuring zero manual migration. Phase 5 formalizes backfill with explicit migration script.

**Symlink Bridge**: P2-T16 adds logging to help debug Phase 0 adapter scenarios when native profiles coexist with symlinks.

**API Contract Change**: The `POST /artifacts/{artifact_id}/deploy` response structure changes to include `deployment_profile_id`. Ensure frontend (Phase 4) updates correspondingly.

---

**Phase Status**: Completed (2026-02-07)
**Blocks**: None
**Blocked By**: None
