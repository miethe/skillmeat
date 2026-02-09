---
title: "Phase 5: Migration and Compatibility Hardening"
parent: ../multi-platform-project-deployments-v1.md
---

# Phase 5: Migration and Compatibility Hardening

**Duration**: 0.75 week (3-4 days)
**Dependencies**: Phases 1-4 complete
**Total Effort**: 5 story points

## Overview

Phase 5 is the final phase that ensures backward compatibility. It creates a migration script to infer default `claude_code` profiles for existing projects, backfills legacy deployment records with profile metadata, and runs comprehensive regression tests to verify existing Claude-only workflows remain unchanged. This phase ensures zero manual migration burden on users upgrading to the multi-platform system.

## Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P5-T1 | Create migration script: infer default profiles | Create `scripts/migrate_to_deployment_profiles.py` that scans existing projects (found via `skillmeat.core.discovery`); for each project without explicit profiles, creates default `claude_code` profile matching current `.claude/` directory structure and artifact path mappings | Script identifies all legacy projects; creates sensible default profiles; dry-run mode available to preview changes | 1.5 pts | python-backend-engineer | P2-T5, P1-T6 |
| P5-T2 | Backfill deployment records with profile metadata | Script (from P5-T1) also backfills existing deployment records to populate `deployment_profile_id`, `platform`, `profile_root_dir` fields; match based on artifact path (assume `.claude/` = `claude_code` profile) | Deployment records updated with profile info; no data loss; backward-compat queries still work with `None` values where applicable | 1 pt | python-backend-engineer | P2-T3, P1-T9 |
| P5-T3 | Create regression test suite for Claude-only workflows | Build comprehensive test suite covering: `skillmeat deploy` (without --profile, uses default), `skillmeat status` (without --profile, shows all), `skillmeat undeploy`, `skillmeat init` (without --profile), artifact import, context entity deployment to `.claude/` — all should work exactly as before | Test suite covers all basic workflows; all tests pass; no behavioral changes for Claude-only users | 1.5 pts | testing-specialist | P2-T6, P2-T7, P2-T8 |
| P5-T4 | Verify profile-aware features with fresh projects | Create test scenarios with new projects: init with --profile, deploy to multiple profiles, status per profile, cross-profile sync — verify features work as designed and documented | Test scenarios cover all new Phase 1-4 features; all tests pass; no regressions to old features | 1 pt | testing-specialist | P2-T1 through P4-T19 |
| P5-T5 | Documentation: migration guide and upgrade notes | Create `docs/migration/multi-platform-deployment-upgrade.md` documenting: what changed, what stays the same, how to verify upgrade (regression tests), how to opt-in to multi-platform (new --profile flags), known limitations (symlink edge cases), troubleshooting; update README and CHANGELOG; update user-facing command docs to reflect profile-aware init/deploy/status/context deploy behavior | Migration guide covers upgrade path; users can confidently upgrade; troubleshooting section addresses common issues; top-level docs and command reference include profile-aware workflows | 1 pt | documentation-writer | P2-T1 through P4-T19 |

## Quality Gates

- [x] Migration script successfully identifies legacy projects
- [x] Default profiles created with correct directory mappings
- [x] Deployment records backfilled with profile metadata; all data preserved
- [x] Regression test suite passes: all Claude-only workflows unchanged
- [x] New profile features tested with fresh projects; all work as designed
- [x] Migration documentation clear and complete
- [x] Zero breaking changes for existing users
- [x] Upgrade can be automated (migration script runs explicitly)
- [x] Post-upgrade, both old and new workflows function correctly

## Key Files

**Migration Scripts** (new):
- `scripts/migrate_to_deployment_profiles.py` — Migration script (P5-T1, P5-T2)
- `scripts/migrate_to_deployment_profiles_dryrun.md` — Documentation and examples (P5-T5)

**Documentation** (new/modified):
- `docs/migration/multi-platform-deployment-upgrade.md` — New migration guide (P5-T5)
- `README.md` — Updated with multi-platform note and migration link (P5-T5)
- `CHANGELOG.md` — Added entry for Phase 0-5 completion (P5-T5)
- `docs/user/README.md` — Added migration guide in user docs index (P5-T5)
- `docs/user/cli/commands.md` — Added profile-aware CLI command coverage (P5-T5)
- `scripts/migrate_to_deployment_profiles_dryrun.md` — Dry-run walkthrough for migration safety validation (P5-T5)

**Tests** (new):
- `tests/test_claude_only_regression.py` — Regression test suite (P5-T3)
- `tests/test_multi_platform_fresh_projects.py` — New feature tests (P5-T4)
- `tests/test_migration_script.py` — Migration script tests (P5-T1)

## Task Details

### P5-T1: Migration Script

The migration script should:
1. Use `skillmeat.core.discovery.discover_projects()` (profile-aware from Phase 2) to find all projects
2. For each project, check if `deployment_profiles` is empty
3. If empty, create default `claude_code` profile with:
   - `profile_id = "claude_code"`
   - `platform = Platform.CLAUDE_CODE`
   - `root_dir = ".claude"`
   - `artifact_path_map` matching current structure (e.g., `skills -> skills/{name}`)
   - `project_config_filenames = ["CLAUDE.md"]` (or scan for existing project config)
   - `context_path_prefixes = [".claude/"]`
4. Support `--dry-run` flag to preview changes without writing
5. Support `--verbose` flag to show before/after for each project
6. Handle errors gracefully (bad project structures, missing directories) with clear error messages

### P5-T2: Backfill Deployment Records

The backfill should:
1. Iterate existing deployment records
2. For each record with `deployment_profile_id = None`:
   - Infer profile based on `artifact_path` (if starts with `.claude/`, use `claude_code`)
   - Set `platform` to match inferred profile
   - Set `profile_root_dir` to profile's root
3. Support rollback in case of errors
4. Log summary (N records backfilled, M records already populated)

### P5-T3: Regression Test Suite

Regression tests should verify:
- `skillmeat deploy <artifact>` deploys to default profile (Claude)
- `skillmeat status` shows deployments (includes Claude artifacts)
- `skillmeat undeploy <artifact>` removes from default profile
- `skillmeat init` creates `.claude/` structure
- Artifact import works, artifacts deployable
- Context entity deploy to `.claude/` works
- All tests pass on both fresh and migrated projects
- No changes to behavior when running without `--profile` flag

### P5-T4: New Feature Verification

Tests should verify:
- `skillmeat init --profile codex` creates `.codex/` structure
- `skillmeat deploy <artifact> --profile codex` deploys to Codex
- `skillmeat status --profile codex` shows Codex deployments
- `skillmeat deploy <artifact> --all-profiles` deploys to all profiles
- Artifact `target_platforms` filtering works
- Context entity deployment respects profiles
- Cross-profile sync view in UI shows correctly
- Profile management UI works

## Integration Notes

**Automation**: Consider making migration automatic on first `skillmeat` command post-upgrade (detect old projects, run migration silently, no user intervention needed). Alternatively, document explicit migration command.

**Rollback**: If migration is automated, provide clear rollback procedure (documented in migration guide).

**Testing Strategy**: Run migration tests on both fresh database and database with existing data to ensure no regressions.

**Documentation Importance**: Phase 5's documentation task (P5-T5) is critical for user confidence. Clearly communicate: what changed (internal), what stays same (user experience for Claude-only users), how to adopt new features (profiles).

**Timing**: Phase 5 should be last phase to ensure all Phases 1-4 features are rock-solid before shipping migration and regression tests.

---

**Phase Status**: Completed (2026-02-09)
**Blocks**: None
**Blocked By**: Phases 1-4 (Data Model, Deployment Engine, Context Entity, Discovery/Cache/UI)

---

## Summary: Feature Completion Criteria

When all Phases 0-5 are complete and all quality gates passed:

1. ✓ Projects can host multiple deployment profiles (Phase 1-2)
2. ✓ Artifacts optionally scoped to platforms (Phase 1, Phase 4)
3. ✓ Deploy/status/sync/discovery profile-aware (Phase 2-4)
4. ✓ Legacy projects zero-change upgrade (Phase 5)
5. ✓ All phases' quality gates passed and regression tests green

**Release Criteria**: All quality gates passed + Phase 5 migration tested + documentation reviewed + zero P0/P1 bugs found in integration testing.
