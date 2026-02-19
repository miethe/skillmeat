---
type: context
prd: artifact-detection-standardization
created: '2026-01-06'
updated: '2026-01-06'
schema_version: 2
doc_type: context
feature_slug: artifact-detection-standardization
---

# Artifact Detection Standardization - Context Notes

## PRD Reference

- **PRD**: `docs/project_plans/PRDs/refactors/artifact-detection-standardization-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/refactors/artifact-detection-standardization-v1.md`
- **Progress**: `.claude/progress/artifact-detection-standardization/`

## Project Summary

Consolidate fragmented artifact detection logic (4,837 lines across 5 modules) into a unified core module used by all detection layers.

## Key Files

### To Create

| File | Purpose |
|------|---------|
| `skillmeat/core/artifact_detection.py` | Unified detection core (~400 lines) |
| `tests/core/test_artifact_detection.py` | Unit tests (45+) |
| `tests/core/integration/test_detection_consistency.py` | Integration tests (30+) |

### To Modify

| File | Changes |
|------|---------|
| `skillmeat/core/artifact.py` | Import ArtifactType from detection module |
| `skillmeat/core/discovery.py` | Use shared detector, add nested discovery |
| `skillmeat/core/marketplace/heuristic_detector.py` | Remove duplicate enum, use shared baseline |
| `skillmeat/utils/validator.py` | Use shared signatures |
| `skillmeat/defaults.py` | Use shared inference |

## Canonical Artifact Types

From official Claude Code documentation:

| Type | Structure | Manifest | Container |
|------|-----------|----------|-----------|
| SKILL | Directory | SKILL.md (required) | skills/ |
| COMMAND | Single .md file | None | commands/ |
| AGENT | Single .md file | None | agents/ |
| HOOK | JSON config | settings.json | - |
| MCP | JSON config | .mcp.json | - |

## Container Aliases

| Type | Aliases |
|------|---------|
| SKILL | skills, skill, claude-skills |
| COMMAND | commands, command, claude-commands |
| AGENT | agents, agent, subagents, claude-agents |
| HOOK | hooks, hook, claude-hooks |
| MCP | mcp, mcp-servers, servers, mcp_servers, claude-mcp |

## Phase Dependencies

```
Phase 1 (Detection Core)
    ↓
Phase 2 (Discovery) ─┬─ Phase 3 (Marketplace) ─┬─ Phase 4 (Validators)
    ↓                │            ↓            │           ↓
    └────────────────┴────────────┴────────────┴───────────┘
                               ↓
                        Phase 5 (Testing)
```

Phases 2, 3, 4 can run in parallel after Phase 1 completes.

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-06 | Standardize on 5 types: skill/command/agent/hook/mcp | Match Claude Code official spec |
| 2026-01-06 | Deprecate directory-based commands/agents | Only skills should be directories |
| 2026-01-06 | Local detection uses strict mode (100%) | Developers control .claude/ structure |
| 2026-01-06 | Marketplace uses heuristic mode (0-100%) | GitHub repos need flexible detection |
| 2026-01-06 | Keep mcp_server in API/DB for backwards compat | Use MCP internally, translate at API layer |

## Technical Notes

### Detection Modes

- **Strict mode** (local): Rules match = 100% confidence, else 0%
- **Heuristic mode** (marketplace): Multi-signal scoring 0-100%

### Backwards Compatibility

- Zero breaking changes to public APIs
- Deprecation warnings only (errors in Phase 6+)
- Support both "mcp" and "mcp_server" type names

### Performance Considerations

- Depth limit for nested discovery (3-5 levels)
- Cache container normalization results
- Benchmark before/after each phase

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Type mismatch in marketplace | Low | Integration tests |
| Discovery regression | Medium | Existing tests as gate |
| Container alias breaks | Low | Centralized aliases |
| Deprecation warnings spam | Low | Make toggleable |

## Session Handoff Notes

*Add notes here during implementation sessions*

---

*Last updated: 2026-01-06*
