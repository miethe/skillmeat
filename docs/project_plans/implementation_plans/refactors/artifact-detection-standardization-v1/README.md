# Artifact Detection Standardization Refactor - Implementation Plan

This directory contains the complete implementation plan for consolidating SkillMeat's artifact detection logic into a unified core module.

## Quick Navigation

### Main Plan
**[artifact-detection-standardization-v1.md](../artifact-detection-standardization-v1.md)** - Start here for executive summary and phase overview

### Phase-Specific Plans
1. **[phase-1-detection-core.md](phase-1-detection-core.md)** - Create unified detection module (1 week, 13 SP)
   - Define ArtifactType enum, DetectionResult, ArtifactSignature
   - Create ARTIFACT_SIGNATURES and CONTAINER_ALIASES registries
   - Implement core detection functions
   - 9 tasks with detailed acceptance criteria

2. **[phase-2-local-discovery.md](phase-2-local-discovery.md)** - Rebuild local discovery (1 week, 12 SP)
   - Import shared detection module into discovery.py
   - Replace fragmented detection with unified detector
   - Add recursive directory traversal for nested artifacts
   - Implement deprecation warnings
   - 9 tasks with detailed acceptance criteria

3. **[phase-3-marketplace.md](phase-3-marketplace.md)** - Refactor marketplace heuristics (2 weeks, 18 SP)
   - Remove duplicate ArtifactType enum
   - Reuse 80%+ of shared detection logic
   - Maintain marketplace-specific confidence scoring
   - Keep manual directory mapping and GitHub heuristics
   - 10 tasks with detailed acceptance criteria

4. **[phase-4-validators.md](phase-4-validators.md)** - Align validators and defaults (1 week, 10 SP)
   - Replace ad-hoc validation with shared ARTIFACT_SIGNATURES
   - Implement type normalization and validation
   - Route CLI defaults through shared inference
   - Add deprecation warning support
   - 10 tasks with detailed acceptance criteria

5. **[phase-5-testing.md](phase-5-testing.md)** - Testing and safeguards (2 weeks, 17 SP)
   - Create 100+ comprehensive test cases
   - Integration tests for cross-module consistency
   - Deprecation warning documentation
   - Migration guide for developers
   - Backwards compatibility report
   - 10 tasks with detailed acceptance criteria

---

## Key Metrics

### Scope
- **Total Duration:** 7 weeks
- **Total Story Points:** 70 (13+12+18+10+17)
- **Total Tasks:** 48 tasks across 5 phases
- **Test Cases:** 100+ (45 unit + 30 integration + existing)

### Impact
- **Code Reduction:** 4,837 → ~2,500 lines (48% reduction)
- **Enum Duplicates:** 2 → 1 (50% reduction)
- **Manifest Config Locations:** 3 → 1 (67% reduction)
- **Container Alias Definitions:** 3 → 1 (67% reduction)
- **Code Coverage:** >90% on artifact_detection.py

### Success Criteria
- Zero `ArtifactType` enum duplicates
- 100% local discovery rebuilt on shared detector
- Marketplace heuristics reuse 80%+ shared rules
- All validators use shared signatures
- CLI defaults route through shared inference
- 100+ test cases all passing
- Zero regressions (all existing tests pass)

---

## How to Use This Plan

### For Project Managers
1. Read main plan: **artifact-detection-standardization-v1.md**
2. Review phase summaries in Phase Overview table
3. Use story points to plan sprints/milestones
4. Check Quality Gates section for phase completion criteria

### For Implementation Teams
1. Start with Phase 1: **phase-1-detection-core.md**
2. Each phase has clear task breakdown with:
   - Task ID (TASK-1.1, TASK-1.2, etc.)
   - Acceptance criteria (checkbox list)
   - Story points and effort estimate
   - Dependencies on other tasks
3. Follow task sequence (respecting dependencies)
4. Use Quality Gates checklist to verify phase completion

### For Code Reviewers
1. Review phase implementation against task acceptance criteria
2. Verify Quality Gates passed before phase completion
3. Check test coverage and linting results
4. Verify backwards compatibility tests pass

### For QA/Testing
1. Focus on Phase 5: **phase-5-testing.md**
2. Run full test suite: `pytest tests/ -v`
3. Verify code coverage: >90% on artifact_detection.py
4. Check all existing tests still pass (zero regressions)
5. Use test cases from TASK-5.1 and TASK-5.2

---

## Files Modified

### New Files Created
- `skillmeat/core/artifact_detection.py` (~400 lines)
- `tests/core/test_artifact_detection.py` (45+ tests)
- `tests/core/integration/test_detection_consistency.py` (30+ tests)
- `docs/deprecation/artifact-detection-v1.md`
- `docs/migration/artifact-detection-v1-migration.md`
- `.claude/context/artifact-detection-standards.md`
- `docs/architecture/detection-system-design.md`

### Existing Files Modified
- `skillmeat/core/artifact.py` (import ArtifactType from new module)
- `skillmeat/core/discovery.py` (use shared detector, recursive traversal)
- `skillmeat/core/marketplace/heuristic_detector.py` (remove duplicate enum, reuse shared rules)
- `skillmeat/utils/validator.py` (use shared ARTIFACT_SIGNATURES)
- `skillmeat/defaults.py` (use shared inference)
- All associated test files

---

## Architecture Overview

### Before (Fragmented)
```
Local Discovery ────┐
Marketplace ────────├──> ArtifactType (duplicated in 2 places)
Validators ─────────┤    MANIFEST_FILES (hardcoded in 3 places)
CLI Defaults ───────┤    Container aliases (3 different approaches)
artifact.py ────────┘    Detection logic (4 independent implementations)
```

### After (Unified)
```
skillmeat/core/artifact_detection.py (NEW)
├── ArtifactType enum (canonical, single definition)
├── DetectionResult dataclass
├── ARTIFACT_SIGNATURES registry
├── MANIFEST_FILES registry
├── CONTAINER_ALIASES registry
├── normalize_container_name()
├── infer_artifact_type()
├── detect_artifact()
└── extract_manifest_file()

All detection layers import from core:
├── Local Discovery (strict mode)
├── Marketplace (heuristic mode + marketplace signals)
├── Validators (aligned rules)
└── CLI Defaults (standardized inference)
```

---

## Quality Gates Summary

### Phase 1 Gates
- [ ] Module created, imports work
- [ ] 20+ unit tests pass
- [ ] ArtifactType enum conflict-free
- [ ] artifact.py imports successfully

### Phase 2 Gates
- [ ] All existing discovery tests pass
- [ ] New nested discovery tests pass
- [ ] Deprecation warnings logged
- [ ] No performance regression

### Phase 3 Gates
- [ ] All existing marketplace tests pass
- [ ] Duplicate enum removed
- [ ] 80%+ detection logic uses shared module
- [ ] Confidence scores match pre-refactor

### Phase 4 Gates
- [ ] All validation tests pass
- [ ] All defaults tests pass
- [ ] Type normalization working
- [ ] No breaking API changes

### Phase 5 Gates
- [ ] 100+ tests passing
- [ ] >90% code coverage
- [ ] All existing tests pass (zero regressions)
- [ ] Documentation complete
- [ ] Backwards compatibility verified

---

## Key Dependencies

### Between Phases
- Phase 1 must complete before Phase 2, 3, 4 start
- Phase 2 and 3 can run in parallel after Phase 1 complete
- Phase 4 can start after Phase 1 complete (independent)
- Phase 5 requires Phases 1-4 complete

### Within Phases
- Each task has explicit dependencies listed
- Follow task sequence to respect dependencies
- See "Dependency Graph" section in each phase plan

---

## Risk Mitigation

### Potential Risks
| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Type mismatch in marketplace scoring | Low | Phase 5 integration tests |
| Regression in local discovery | Medium | All existing tests must pass |
| Container alias normalization breaks repos | Low | Comprehensive Phase 5 testing |
| Deprecation warnings too aggressive | Medium | Warnings only (not errors) |
| Performance regression | Low | Benchmarking before/after |

### Safety Measures
- All changes are backwards compatible
- No breaking changes to public APIs
- All existing tests must pass
- Deprecation warnings, not errors (legacy patterns still work)
- Comprehensive integration testing

---

## Getting Started

### Phase 1 Start Checklist
- [ ] Read artifact-detection-standardization-v1.md (main plan)
- [ ] Read phase-1-detection-core.md in detail
- [ ] Review CLAUDE.md for SkillMeat patterns
- [ ] Check task dependencies
- [ ] Start with TASK-1.1: Define Core Data Structures

### Each Phase Start
1. Read phase document completely
2. Understand all task dependencies
3. Review Quality Gates for phase completion
4. Start with first task (TASK-N.1)
5. Complete acceptance criteria for each task
6. Run test suite frequently
7. Check Quality Gates before phase completion

---

## Success Criteria Checklist

### Final Completion
- [ ] All 5 phases complete
- [ ] All 48 tasks completed with acceptance criteria met
- [ ] All quality gates passed
- [ ] 100+ test cases all passing
- [ ] >90% code coverage on artifact_detection.py
- [ ] Zero regressions (all existing tests pass)
- [ ] Code reduction achieved (48%)
- [ ] Enum duplicates eliminated (2→1)
- [ ] Documentation complete
- [ ] Backwards compatibility verified
- [ ] Ready for production deployment

---

## Support & Questions

### For Questions About
- **Phase 1-4 implementation:** See individual phase documents, especially "Implementation Notes" section
- **Testing & QA:** See Phase 5 document, TASK-5.1 through TASK-5.3
- **Architecture:** See main plan "Architecture Overview" and TASK-5.7 (Architecture Documentation)
- **Backwards compatibility:** See main plan "Backwards Compatibility" section
- **Deprecations:** See Phase 5, TASK-5.4 (Deprecation Documentation)

### References
- **PRD:** `docs/project_plans/PRDs/refactors/artifact-detection-standardization-v1.md`
- **Code Analysis:** `.claude/context/artifact-detection-code-patterns.md`
- **Detection System Design:** `docs/architecture/detection-system-design.md` (created in Phase 5)

---

**Document Version:** 1.0
**Created:** 2026-01-06
**Status:** Ready for Phase 1 Implementation
