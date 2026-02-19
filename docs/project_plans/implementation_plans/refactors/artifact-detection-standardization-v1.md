---
status: inferred_complete
schema_version: 2
doc_type: implementation_plan
feature_slug: artifact-detection-standardization
prd_ref: null
---
# Implementation Plan: Artifact Detection Standardization Refactor

**Project:** SkillMeat
**Feature Name:** Artifact Detection Standardization
**Filepath Name:** `artifact-detection-standardization-v1`
**Status:** Ready for Execution
**Created:** 2026-01-06
**Version:** 1.0

---

## Executive Summary

This implementation plan consolidates fragmented artifact detection logic (4,837 lines across 5 modules) into a unified core that serves as the single source of truth for:

- Type definitions (canonical `ArtifactType` enum)
- Artifact signatures (directory vs file structure rules)
- Container alias normalization (supports 20+ aliases)
- Detection result structures (consistent confidence scoring)
- Detection algorithms (strict local mode, heuristic marketplace mode)

**Scope:** 5 phases over 7 weeks
**Total Effort:** ~60 story points
**Track:** Full (Large project requiring comprehensive planning)
**Key Deliverables:**
- Unified `artifact_detection.py` core module (~400 lines)
- Rebuilt local discovery using shared detector
- Refactored marketplace heuristics (80%+ reuse of shared rules)
- Aligned validators and defaults
- 100+ test cases with backwards compatibility safeguards

---

## Phase Overview

| Phase | Focus | Duration | Story Points | Status |
|-------|-------|----------|--------------|--------|
| **[Phase 1: Detection Core](artifact-detection-standardization-v1/phase-1-detection-core.md)** | Create unified detection module with types, signatures, registries | 1 week | 13 | Ready |
| **[Phase 2: Local Discovery](artifact-detection-standardization-v1/phase-2-local-discovery.md)** | Rebuild discovery to use shared detector with recursive traversal | 1 week | 12 | Ready |
| **[Phase 3: Marketplace Refactor](artifact-detection-standardization-v1/phase-3-marketplace.md)** | Refactor heuristics to reuse 80%+ shared rules, keep scoring | 2 weeks | 18 | Ready |
| **[Phase 4: Validators & Defaults](artifact-detection-standardization-v1/phase-4-validators.md)** | Align validators and defaults to use shared signatures | 1 week | 10 | Ready |
| **[Phase 5: Testing & Safeguards](artifact-detection-standardization-v1/phase-5-testing.md)** | Comprehensive testing, deprecation docs, migration guide | 2 weeks | 17 | Ready |

---

## High-Level Success Criteria

### Code Quality
- ✓ Zero `ArtifactType` enum duplicates (eliminate heuristic_detector.py duplicate)
- ✓ Single manifest file configuration location (from 3 hardcoded locations)
- ✓ Unified container alias definitions (from 3 fragmented approaches)
- ✓ 4,837 lines consolidated to ~2,500 lines (48% reduction)

### Testing & Compatibility
- ✓ 100+ test cases all passing
- ✓ >90% code coverage on detection module
- ✓ All existing unit tests pass (zero regressions)
- ✓ Backwards compatible (no breaking API changes)

### Functional Goals
- ✓ Local detection: Strict mode (100% confidence when rules match)
- ✓ Marketplace detection: Heuristic mode (0-100 confidence, 80%+ shared rules)
- ✓ Container aliases: Support 20+ names (commands, agents, skills, hooks, mcp, subagents, etc.)
- ✓ Deprecation warnings: Clear guidance for legacy patterns

---

## Key Architecture Changes

### Before (Fragmented)
```
Local Discovery ────┐
Marketplace ────────├──> 5 ArtifactType defs (2 duplicated)
Validators ─────────┤    3 Manifest configs
CLI Defaults ───────┤    3 Container alias defs
artifact.py ────────┘    4 Detection implementations
```

### After (Unified)
```
Shared Detection Core (artifact_detection.py)
├── ArtifactType enum (canonical)
├── DetectionResult dataclass
├── ARTIFACT_SIGNATURES registry
├── MANIFEST_FILES registry
├── CONTAINER_ALIASES registry
└── Detection functions: normalize_container_name(), infer_artifact_type(), detect_artifact(), extract_manifest_file()

All detection layers import from core:
├── Local Discovery (strict mode)
├── Marketplace Heuristics (heuristic mode + scoring)
├── Validators (aligned rules)
└── CLI Defaults (standardized inference)
```

---

## Implementation Workflow

### Recommended Execution Order

**Sequential phases** (each phase depends on previous):
1. Phase 1: Create core detection module
2. Phase 2: Rebuild local discovery
3. Phase 3: Refactor marketplace heuristics
4. Phase 4: Align validators and defaults
5. Phase 5: Comprehensive testing and documentation

### Parallel Opportunities
- Phase 2 tests can be written in parallel while Phase 1 implementation finishes
- Phase 3 can draft refactoring while Phase 2 is in progress
- Phase 4 validators refactoring is independent after Phase 1 complete

---

## Quality Gates (Phase Completion)

### Phase 1
- [ ] `artifact_detection.py` module created and imports work
- [ ] 20+ initial unit tests pass
- [ ] ArtifactType enum has no import conflicts
- [ ] artifact.py successfully imports from new module

### Phase 2
- [ ] All existing discovery tests pass
- [ ] New nested artifact detection tests pass
- [ ] Deprecation warnings logged correctly
- [ ] No performance regression vs Phase 1 baseline

### Phase 3
- [ ] All existing marketplace tests pass
- [ ] Confidence scores match previous behavior
- [ ] Manual directory mapping still works
- [ ] 80%+ of detection logic uses shared rules

### Phase 4
- [ ] All validation tests pass
- [ ] Type names consistent across modules
- [ ] CLI defaults use shared inference
- [ ] No breaking API changes

### Phase 5
- [ ] 100+ test cases all passing
- [ ] >90% code coverage on detection module
- [ ] All existing unit tests pass
- [ ] Migration guide complete and reviewed

---

## Detailed Phase Plans

For task-level breakdown, acceptance criteria, and subagent assignments, see:

- **[Phase 1: Detection Core](artifact-detection-standardization-v1/phase-1-detection-core.md)** - Types, signatures, core functions
- **[Phase 2: Local Discovery](artifact-detection-standardization-v1/phase-2-local-discovery.md)** - Discovery rebuild, recursive traversal
- **[Phase 3: Marketplace Refactor](artifact-detection-standardization-v1/phase-3-marketplace.md)** - Heuristics refactor, scoring
- **[Phase 4: Validators & Defaults](artifact-detection-standardization-v1/phase-4-validators.md)** - Validator/defaults alignment
- **[Phase 5: Testing & Safeguards](artifact-detection-standardization-v1/phase-5-testing.md)** - Testing, docs, migration

---

## Risk Management

### Key Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Type mismatch in marketplace scoring | Low | High | Phase 5 integration tests; verify confidence scores unchanged |
| Regression in local discovery | Medium | Medium | All existing tests pass Phase 2; backwards compatibility safeguards |
| Container alias normalization breaks existing repos | Low | High | Comprehensive Phase 5 testing with real GitHub repos |
| Deprecation warnings too aggressive | Medium | Low | Warnings only (not errors); clear migration path |
| Performance regression in detection | Low | Medium | Benchmark before/after each phase |

### Backwards Compatibility
- **Zero breaking changes** to external APIs
- `Artifact` dataclass public interface unchanged
- API responses accept both new and old type names
- Existing collections continue working (with optional deprecation warnings)

---

## Success Metrics

### Quantitative
- Code reduction: 4,837 → 2,500 lines (48%)
- Type duplication: 2 enums → 1 enum (50% reduction)
- Manifest definitions: 3 locations → 1 location (67% reduction)
- Test coverage: 100+ test cases, >90% on detection module
- ArtifactType enum imports: Every detection module uses shared version

### Qualitative
- Developers report consistent artifact detection across tools
- Marketplace and local discovery yield same classifications
- Clear, documented migration path for legacy patterns
- No type mismatch issues in changelog post-release

---

## Files Modified

### New Files
- `skillmeat/core/artifact_detection.py` (400 lines)
- `tests/core/test_artifact_detection.py` (45+ test cases)
- `tests/core/integration/test_detection_consistency.py` (30+ test cases)
- `.claude/context/artifact-detection-standards.md` (reference doc)
- `docs/migration/deprecated-artifact-patterns.md` (migration guide)

### Modified Files
- `skillmeat/core/artifact.py` (import ArtifactType from new module)
- `skillmeat/core/discovery.py` (use shared detector, recursive traversal)
- `skillmeat/core/marketplace/heuristic_detector.py` (remove duplicate enum, reuse shared rules)
- `skillmeat/utils/validator.py` (use shared signatures)
- `skillmeat/defaults.py` (use shared inference)
- All associated test files

---

## Next Steps

1. **Review Plan:** Stakeholders review this plan and phase files
2. **Start Phase 1:** Begin with `phase-1-detection-core.md` tasks
3. **Daily Standup:** Sync on blockers and cross-phase dependencies
4. **Phase Gates:** Complete quality gates before moving to next phase
5. **Final Review:** Phase 5 integration testing and documentation

---

**Document Version:** 1.0
**Status:** Ready for Phase 1 Implementation
**Last Updated:** 2026-01-06
