---
title: 'Implementation Plan: Multi-Platform Project Deployments (v1)'
description: Add deployment profiles for Claude Code, Codex, Gemini, and future agent
  platforms without duplicating artifacts.
audience:
- ai-agents
- developers
- architects
- product
tags:
- implementation
- deployments
- platform
- codex
- claude
- gemini
- artifacts
created: 2026-02-07
updated: 2026-02-09
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/PRDs/features/agent-context-entities-v1.md
- /docs/project_plans/PRDs/features/enhanced-frontmatter-utilization-v1.md
schema_version: 2
doc_type: implementation_plan
feature_slug: multi-platform-project-deployments
prd_ref: null
---
# Implementation Plan: Multi-Platform Project Deployments (v1)

**Plan ID**: `IMPL-2026-02-07-multi-platform-project-deployments-v1`
**Date**: 2026-02-07
**Target Timeline**: 8-9 weeks
**Total Estimated Effort**: ~72 story points

## Executive Summary

This implementation plan enables SkillMeat to support platform-specific project deployments (Claude Code, Codex, Gemini, and future platforms) while maintaining backward compatibility with existing Claude-only projects. The approach is phased:

1. **Phase 0** (Immediate, non-invasive): Ship an adapter/symlink strategy so existing projects can work with multiple platforms today
2. **Phases 1-5** (8-9 weeks): Build native multi-platform deployment support through data models, deployment engine refactoring, context entity generalization, UI/discovery updates, and backward-compatible migration

**Key milestones**: Phase 0 can ship in days; Phase 1 foundations complete by week 1; critical path (Phases 2-3) by week 3; full system ready by week 9.

**Success criteria**: Projects can host multiple deployment profiles without artifact duplication; artifacts are optionally scoped to platforms; deploy/status/sync/discovery flows are profile-aware; legacy projects require zero manual migration.

## Implementation Strategy

### Architecture Sequence

The implementation follows a bottom-up approach aligned with MeatyPrompts layered architecture:

1. **Phase 0**: Adapter baseline (immediate, parallel, non-blocking)
2. **Phase 1**: Data model foundations (enums, schemas, DB models, API schemas)
3. **Phase 2**: Deployment engine refactor (path resolution, deploy/undeploy/status logic)
4. **Phase 3**: Context entity generalization (path validation, profile-aware safe roots)
5. **Phase 4**: Discovery, cache, and UI/UX (project discovery, file watcher, cache updates, frontend)
6. **Phase 5**: Migration and compatibility hardening (legacy data backfill, regression tests)

### Parallel Work Opportunities

- **Phase 0 + others**: Adapter script can be finalized and shipped while Phases 1-5 are in flight
- **Phase 1 parallel streams**: Enum/schema changes, DB models, API schemas can be done independently
- **Phase 2 parallel streams**: CLI/API endpoint additions can be developed in parallel with core refactoring
- **Phase 4 parallel streams**: UI component design can start while Phases 2-3 logic is being finalized

### Critical Path

The critical path (longest dependency chain) is: **Phase 1 (data model) → Phase 2 (deployment engine) → Phase 3 (context entity) → Phase 4 (discovery/UI) → Phase 5 (migration)**. This sequence cannot be parallelized because each phase depends on the previous layer's API contract.

However, **Phase 0 (adapter baseline) is completely parallel** and ships independently.

## Phase Breakdown

| Phase | Title | Duration | Dependencies | Effort | Status |
|-------|-------|----------|--------------|--------|--------|
| **Phase 0** | [Adapter Baseline](./multi-platform-project-deployments-v1/phase-0-adapter-baseline.md) | 0.5 week | None | 2 pts | Ready to ship |
| **Phase 1** | [Data Model Foundations](./multi-platform-project-deployments-v1/phase-1-data-model.md) | 1 week | None | 12 pts | Awaiting scheduling |
| **Phase 2** | [Deployment Engine Refactor](./multi-platform-project-deployments-v1/phase-2-deployment-engine.md) | 2 weeks | Phase 1 | 25 pts | Completed (2026-02-07) |
| **Phase 3** | [Context Entity Generalization](./multi-platform-project-deployments-v1/phase-3-context-entity.md) | 1.5 weeks | Phase 2 | 18 pts | Awaiting Phase 2 |
| **Phase 4** | [Discovery, Cache, and UI/UX](./multi-platform-project-deployments-v1/phase-4-discovery-cache-ui.md) | 1.5 weeks | Phase 2, 3 | 20 pts | Awaiting Phase 3 |
| **Phase 5** | [Migration and Compatibility](./multi-platform-project-deployments-v1/phase-5-migration-compat.md) | 0.75 week | Phases 1-4 | 5 pts | Completed (2026-02-09) |

**Total**: ~8-9 weeks, ~72 story points (3 FTE developers at capacity)

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Hardcoded `.claude/` paths across codebase | High | High | Phase 2 systematically refactors all path resolution; Phase 1 identifies all occurrences |
| Context entity triple-layer validation must change in lockstep | Medium | Medium | Phase 3 task P3-T4 explicitly coordinates all three layers; separate PR to avoid merge conflicts |
| Symlink resolution edge cases (Phase 0 → Phase 2 bridge) | Medium | Low | Document symlink semantics; Phase 2 adds explicit symlink-aware checks; Phase 0 script tested on multiple OSes |
| Cache invalidation misses non-`.claude/` profile changes | High | Medium | Phase 4 task P4-T2 explicitly expands FileWatcher to all profile roots; test with all platforms |
| Migration script misses legacy edge cases | Medium | Medium | Phase 5 includes backfill validation; existing Claude-only projects are baseline test scenario |
| UI deployment selector overwhelming users | Low | Medium | Phase 4 UI tasks include design review; default to primary profile; clear error messages for platform mismatches |

## Success Metrics

### Delivery Metrics
- Phase 0 shipped within 1 day; Phases 1-5 on timeline (±1 week)
- Code coverage >80% across all new/modified code
- Zero P0/P1 bugs in Phase 0 and Phase 1 deployments
- All phases pass regression tests (existing workflows unchanged)

### Technical Metrics
- All 6 phases' quality gates passed
- Backward compatibility verified (existing projects unchanged without migration)
- Symlink handling documented and tested on macOS/Linux/Windows
- Profile-aware discovery and cache tests have >85% coverage

### Functional Metrics
- Multi-platform projects deployable via CLI and web UI
- Artifact platform targeting optional and configurable
- Platform detection on import working for popular repos (Codex/Gemini)
- Cross-profile sync comparison UI working (e.g., "Claude v1.2 vs Codex v1.1")

## Security Requirements

1. **Path traversal protections**: Stay mandatory; all path resolution uses `Path.resolve()` and validates against profile roots
2. **Profile root validation**: Ensure resolved target is inside profile root or approved project-config directory
3. **No silent fallback**: Return explicit error if platform mismatch occurs (no implicit downgrade to Claude)
4. **Symlink-aware checks**: Resolve real paths before write/delete operations
5. **Directory co-ownership**: SkillMeat and other platform tools (Codex CLI, Gemini CLI) may both write to profile directories
   - SkillMeat MUST NOT delete files it didn't deploy (tracked via deployment records)
   - Discovery treats unrecognized files in profile roots as external and read-only
   - Conflict detection uses existing `local_modifications` mechanism

## API/CLI Contract Additions

### CLI Extensions

```bash
# Deploy with profile selection
skillmeat deploy <artifact> --profile claude_code
skillmeat deploy <artifact> --profile codex
skillmeat deploy <artifact> --all-profiles

# Status per profile
skillmeat status --profile codex

# Context entity deployment with profile
skillmeat context deploy <entity> --to-project <path> --profile gemini

# Project init with platform
skillmeat init --profile codex
```

### API Extensions

- Deploy endpoints accept `deployment_profile_id` query/body parameter
- Project endpoints return deployment counts segmented by profile/platform
- Artifact list endpoints support `target_platform` filter parameter
- Deployment status endpoint includes `profile_id` and `platform` in response

## Definition of Done

1. Projects can host multiple deployment profiles without duplicate artifact storage requirements.
2. Artifacts can be optionally scoped to platforms via `target_platforms` metadata.
3. Deploy/status/sync/discovery flows are profile-aware and backward compatible.
4. Legacy Claude-only projects keep working with zero manual migration steps.
5. All phases' quality gates passed; regression test suite green.
6. Documentation updated (README, API docs, CLI help text, migration guide).

---

## Phase Details

Detailed task breakdowns, acceptance criteria, and subagent assignments for each phase are in:

- [Phase 0: Adapter Baseline](./multi-platform-project-deployments-v1/phase-0-adapter-baseline.md) — Symlink adapter script, docs, testing
- [Phase 1: Data Model Foundations](./multi-platform-project-deployments-v1/phase-1-data-model.md) — Enums, DB models, API schemas
- [Phase 2: Deployment Engine Refactor](./multi-platform-project-deployments-v1/phase-2-deployment-engine.md) — Path resolution, deploy/undeploy/status logic, CLI/API
- [Phase 3: Context Entity Generalization](./multi-platform-project-deployments-v1/phase-3-context-entity.md) — Profile-aware validation, safe roots
- [Phase 4: Discovery, Cache, and UI/UX](./multi-platform-project-deployments-v1/phase-4-discovery-cache-ui.md) — FileWatcher, discovery, cache updates, frontend components
- [Phase 5: Migration and Compatibility](./multi-platform-project-deployments-v1/phase-5-migration-compat.md) — Backfill legacy data, regression tests

---

**Progress Tracking**: See `.claude/progress/multi-platform-project-deployments/`

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-09
