---
title: "Phase 3: Context Entity Generalization"
parent: ../multi-platform-project-deployments-v1.md
---

# Phase 3: Context Entity Generalization

**Duration**: 1.5 weeks
**Dependencies**: Phase 2 complete (path resolver, profile-aware deployment logic)
**Total Effort**: 18 story points

## Overview

Phase 3 removes `.claude/`-only assumptions from context entity path validation. Currently, three validation layers enforce `.claude/` prefixes independently. Phase 3 unifies them to be profile-aware, allowing context entities to safely deploy to non-`.claude` profile roots. It also introduces support for project config filenames beyond `CLAUDE.md` (e.g., `AGENTS.md`, `GEMINI.md`) and profile-scoped deployment options.

## Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P3-T1 | Audit context entity validation layers | Identify all path validation in: `skillmeat/api/schemas/context_entity.py` (Pydantic validators), `skillmeat/core/validators/context_entity.py` (domain validators), `skillmeat/api/routers/context_entities.py` (route-level checks); document exact line numbers and current logic | Document creates validation matrix: layer, file, line, current behavior (e.g., "requires .claude/ prefix"); shows 3 independent checks | 0.5 pts | python-backend-engineer | None |
| P3-T2 | Create context-aware path validator utility | Create `skillmeat/core/validators/context_path_validator.py` with function: `validate_context_path(path: str, project: Project, profile_id: str, **opts) -> ValidatedPath`; use profile's `context_path_prefixes` to validate; support multiple allowed prefixes per profile | Validator uses DeploymentProfile `context_path_prefixes` list; validates path is under at least one allowed prefix; prevents path traversal; returns clear errors | 1.5 pts | python-backend-engineer | P2-T2, P1-T5 |
| P3-T3 | Refactor API schema validators | Replace hardcoded `.claude/` prefix check in `skillmeat/api/schemas/context_entity.py` with profile-aware validator; modify to accept optional `profile_id` in schema (or infer from project context) | Schema validator calls `context_path_validator.py`; no longer requires `.claude/` prefix; OpenAPI docs updated | 1 pt | python-backend-engineer | P3-T2 |
| P3-T4 | Refactor core domain validators (3-layer sync) | Update `skillmeat/core/validators/context_entity.py` to use profile-aware validator; update `skillmeat/api/routers/context_entities.py` route-level checks similarly; ensure all three layers use same validation logic (DRY principle); coordinate changes in single PR to avoid merge conflicts | All three layers use `context_path_validator.py`; no redundant checks; validators consistent across layers | 2 pts | python-backend-engineer | P3-T2 |
| P3-T5 | Add project_config_filename field to DeploymentProfile | Add `project_config_filenames: list[str]` to `skillmeat/core/models/deployment_profile.py` (e.g., `["CLAUDE.md", "AGENTS.md"]` for Claude profile, `["GEMINI.md"]` for Gemini); update API schema and DB model; add migration | DB migration adds field with sensible defaults per platform; API schema updated | 1 pt | data-layer-expert, python-backend-engineer | P1-T5, P1-T6 |
| P3-T6 | Update context entity deployment to profile-aware filenames | Modify context entity deploy logic to check project's project-config files (per profile) in addition to root-level `.claude/`, `.codex/`, `.gemini/` files; ensure context entities can be deployed alongside any profile's project config | Deploy logic looks for project config files per profile and treats them as safe deployment roots | 1.5 pts | python-backend-engineer | P3-T5, P2-T3 |
| P3-T7 | Add profile selector to context entity deploy options | Update CLI context deploy command to accept `--profile <profile_id>`; update API endpoint to accept `deployment_profile_id`; ensure context entity validation uses selected profile's path rules | `skillmeat context deploy <entity> --to-project <path> --profile codex` works; uses Codex profile's prefixes for validation | 1 pt | python-backend-engineer | P3-T2, P3-T4 |
| P3-T8 | Extend ContextEntity model with target_platforms | Add optional `target_platforms: list[Platform] | None` field to `skillmeat/core/models/context_entity.py`; semantics same as artifacts (null = deployable anywhere) | Field added and optional; DB column added in migration; API schema updated | 1 pt | python-backend-engineer | P1-T1 |
| P3-T9 | Implement context entity platform filtering | In context deploy logic, check entity's `target_platforms`; return error if profile's platform not in list, unless `--force` flag used | Deploy respects platform targeting; `--force` override available if needed; clear error messages on platform mismatch | 1 pt | python-backend-engineer | P3-T8 |
| P3-T10 | Unit tests: context path validator | Test validator with multiple profile configurations; test path traversal prevention; test prefix matching across different profile roots (`.claude`, `.codex`, `.gemini`); test platform targeting filters | Tests cover: valid paths, invalid paths, symlinks, path traversal attempts, multiple prefixes, platform mismatches | 1.5 pts | python-backend-engineer | P3-T2, P3-T9 |
| P3-T11 | Integration test: context entity deployment across profiles | Create test with project having Claude + Codex profiles; deploy context entity to both; verify each respects profile's path rules; verify platform targeting works | Test exercises full deploy flow per profile; validates both succeed or both fail as expected; platform filter working | 1.5 pts | python-backend-engineer | P3-T6, P3-T7, P3-T9 |
| P3-T12 | Integration test: project config file discovery per profile | Test context entity deployment when project-config files exist in different profile roots (e.g., `CLAUDE.md` in `.claude/`, `GEMINI.md` in `.gemini/`); verify each entity deploys to correct profile root | Test verifies context entities found and deployed to correct profile roots when multiple configs exist | 1.5 pts | python-backend-engineer | P3-T6 |
| P3-T13 | Update context entity API response to include platform info | Extend `ContextEntityRead` schema to include `target_platforms` and deployed profiles (e.g., `deployed_to: { "claude_code": ["path1"], "codex": ["path2"] }`); update OpenAPI docs | Schema updated; deployed_to object shows where entity is deployed per profile | 1 pt | python-backend-engineer | P3-T8 |
| P3-T14 | Backward compatibility: auto-detect project config roots | For existing projects without explicit DeploymentProfile `project_config_filenames`, auto-detect `.claude/*.md` config files and add them to default profile's `context_path_prefixes` | Existing projects' context entities continue to work without manual migration | 1 pt | python-backend-engineer | P3-T6 |

## Quality Gates

- [ ] All three context entity validation layers refactored to use unified profile-aware validator
- [ ] Path traversal tests pass; security review approved
- [ ] Context entities deployable to multiple profile roots in same project
- [ ] Platform targeting works correctly; `--force` override tested
- [ ] Project config file detection per profile working
- [ ] API response includes deployed profiles and platform info
- [ ] Backward compatibility: existing context entities auto-detect their profile
- [ ] Integration tests pass: cross-profile context deployment, config file discovery
- [ ] All new/modified code >85% test coverage
- [ ] No regressions to existing context entity workflows

## Key Files

**Core Validators** (new/modified):
- `skillmeat/core/validators/context_path_validator.py` — New unified validator (P3-T2)
- `skillmeat/core/validators/context_entity.py` — Refactored to use unified validator (P3-T4)
- `skillmeat/core/models/context_entity.py` — Added `target_platforms` field (P3-T8)

**API** (modified):
- `skillmeat/api/schemas/context_entity.py` — Refactored validators, added platform field (P3-T3, P3-T8, P3-T13)
- `skillmeat/api/routers/context_entities.py` — Refactored validation, added profile parameter (P3-T4, P3-T7)

**Data Models** (modified):
- `skillmeat/core/models/deployment_profile.py` — Added `project_config_filenames` (P3-T5)
- `skillmeat/cache/models.py` — DB migration for profile config field, context entity platform field (P3-T5, P3-T8)

**CLI** (modified):
- `skillmeat/cli.py` — Context deploy command accepts `--profile` (P3-T7)

**Tests** (new):
- `tests/test_core_context_path_validator.py` — Validator unit tests (P3-T10)
- `tests/test_context_entity_cross_profile.py` — Cross-profile deployment tests (P3-T11, P3-T12)
- `tests/test_context_entity_platform_filter.py` — Platform targeting tests (P3-T9)

## Integration Notes

**Critical Coordination**: P3-T4 modifies three validation layers simultaneously. Coordinate this in a single PR to avoid merge conflicts and ensure consistency. Consider feature-flagging if needed to roll out gradually.

**Path Validator Design**: `context_path_validator.py` is reusable across context entity, artifact, and other future features that need profile-aware path validation.

**Backward Compatibility**: P3-T14 ensures existing context entities auto-detect their profile on first access, avoiding manual migration.

**Phase 2 Dependency**: Phase 2's path resolver is used by the context path validator to resolve profile roots.

**Phase 4 Dependency**: Phase 4 (UI) will show context entity deployment status per profile; Phase 3 provides the data structure for that.

---

**Phase Status**: Awaiting Phase 2 completion
**Blocks**: Phase 4 (Discovery/UI), Phase 5 (Migration)
**Blocked By**: Phase 2 (Deployment Engine)
