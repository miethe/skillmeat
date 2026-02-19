---
title: 'Phase 0: Adapter Baseline'
parent: ../multi-platform-project-deployments-v1.md
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: multi-platform-project-deployments
prd_ref: null
plan_ref: null
---
# Phase 0: Adapter Baseline

**Duration**: 0.5 week (1-2 days)
**Dependencies**: None (can ship independently)
**Total Effort**: 2 story points

## Overview

Phase 0 is an immediate, non-invasive adapter strategy that enables existing projects to work with multiple agent platforms (Codex, Gemini) without modifying the underlying deployment architecture. Using symlink-based adapters, one canonical `.claude/` artifact set can be consumed by multiple tools today while the native multi-platform refactor (Phases 1-5) progresses in parallel.

This phase is production-ready and ships independently. It serves as a temporary bridge until Phases 2-5 deliver native multi-platform support.

## Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P0-T1 | Finalize & document adapter script | Review `scripts/setup_agent_platform_links.sh` for completeness; add inline documentation; verify flag handling (`--install-codex-home-skills`) | Script is production-ready; all flags documented; inline comments explain symlink semantics | 0.5 pts | documentation-writer | None |
| P0-T2 | Write adapter usage guide | Create doc explaining what the adapter does, when to use it (vs native deployments in Phase 2+), limitations, and troubleshooting | Guide covers use cases, symlink semantics, cross-platform behavior (macOS/Linux/Windows), `CODEX_HOME` environment handling | 0.5 pts | documentation-writer | P0-T1 |
| P0-T3 | Test adapter on macOS, Linux, Windows | Manual or automated tests verify symlinks created correctly; `--install-codex-home-skills` works with default and custom `CODEX_HOME`; symlink targets are readable | All three OSes: symlinks created; targets validated; no permission errors | 0.5 pts | python-backend-engineer | P0-T1 |
| P0-T4 | Add symlink safety warnings to CLI | When running `skillmeat init` or `skillmeat deploy` in a project with adapter symlinks, emit informational warning: "This project uses adapter symlinks; changes here affect multiple platforms" | Warnings appear in CLI output when appropriate; warning does not block operations | 0.5 pts | python-backend-engineer | P0-T1 |

## Quality Gates

- [ ] `scripts/setup_agent_platform_links.sh` production-ready and tested on 3+ OSes
- [ ] Inline documentation and usage guide complete and reviewed
- [ ] CLI warnings for symlink scenarios working
- [ ] No regressions to existing `skillmeat init` or `skillmeat deploy` behavior
- [ ] Documentation published (in README or dedicated guide)

## Key Files

- `scripts/setup_agent_platform_links.sh` — Symlink adapter script (already exists; P0-T1 finalizes)
- `docs/guides/adapter-strategy.md` — New usage guide (P0-T2 creates)
- `skillmeat/cli.py` — CLI entry points (P0-T4 adds warnings)
- `skillmeat/core/deployment.py` — Deployment logic (P0-T3 validates, no changes needed)

## Integration Notes

**Symlink Semantics**: Phase 0 symlinks are intentionally transparent. Writes to `.codex/skills/foo` resolve through the symlink to `.claude/skills/foo`. This is by design for the adapter approach.

**Bridge to Phase 2**: Phase 2 (Deployment Engine Refactor) adds native profile support with independent deployment paths. At that point, symlink adapters become optional and users can migrate to native profiles. Phase 2 tasks include symlink-aware path resolution to prevent unintended cross-profile mutations when both symlinks and native profiles coexist.

**No Schema/Model Changes**: Phase 0 does not modify any database schemas, enums, or API contracts. It is purely an operational layer that works with the current `.claude`-centric codebase.

---

**Phase Status**: Ready to schedule and ship immediately
**Blocks**: Phases 1-5 can proceed in parallel
**Blocked By**: Nothing
