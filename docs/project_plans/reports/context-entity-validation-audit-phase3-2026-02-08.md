---
title: "Phase 3 Validation Layer Audit"
created: "2026-02-08"
phase: 3
feature: "multi-platform-project-deployments-v1"
---

# Context Entity Validation Matrix

| Layer | File | Lines | Current behavior |
|---|---|---:|---|
| API schema (create) | `skillmeat/api/schemas/context_entity.py` | 98-116 | Hardcodes `.claude/` prefix in Pydantic validator (`path_pattern must start with '.claude/'`), blocks non-`.claude` profile roots. |
| API schema (update) | `skillmeat/api/schemas/context_entity.py` | 185-205 | Repeats hardcoded `.claude/` prefix check; duplicates create validator logic. |
| Core domain validator | `skillmeat/core/validators/context_entity.py` | 40-81, 186-188, 234-236 | Security check logic is `.claude`-centric (`_validate_path_security` special-cases `.claude`), and type validators enforce `.claude/specs`, `.claude/rules`, `.claude/context`, `.claude/progress` prefixes. |
| Route-level deploy path security (CLI command used as deployment layer) | `skillmeat/cli.py` | 11588-11628 | Local function allows only `.claude/` subtree plus root `CLAUDE.md`/`AGENTS.md`; rejects `.codex`, `.gemini`, etc. |

## Findings

1. Validation is implemented independently in at least three places (schema, core validator, deploy-time path security).
2. All three places currently encode `.claude` assumptions.
3. Prefix and traversal checks are not centralized, making drift likely as profile rules evolve.

## Phase 3 Refactor Target

- Introduce one shared context path validator utility and route schema/core/CLI checks through it.
- Keep schema-time checks focused on generic path safety and leave profile-specific prefix enforcement to deploy-time profile resolution.
- Make deployment validation profile-aware by loading selected profile `context_prefixes` and `config_filenames`.
