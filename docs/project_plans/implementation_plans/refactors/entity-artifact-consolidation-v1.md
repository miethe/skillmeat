---
status: inferred_complete
schema_version: 2
doc_type: implementation_plan
feature_slug: entity-artifact-consolidation
prd_ref: null
---
# Implementation Plan: Entity and Artifact Type System Consolidation

**Epic ID**: REFACTOR-TYPE-CONSOLIDATION
**Complexity**: Large (L)
**Track**: Full Track (Opus-powered)
**Estimated Effort**: 35-45 story points
**Timeline**: 3-4 sprints (4-6 weeks)
**Status**: Ready for Implementation

---

## Executive Summary

This implementation plan guides the consolidation of parallel Entity and Artifact type systems in the SkillMeat web frontend into a unified `Artifact` type. The consolidation eliminates 4 redundant conversion functions, fixes 3+ modal-related bugs, and removes ~150 lines of conversion boilerplate while maintaining 100% backward compatibility for 6 months.

**Key Outcomes**:
- Single source of truth for artifact representation
- Collections tab populated on /manage page
- Source tab appears on /collection page without prior /marketplace navigation
- Modal navigation handlers consistently provided across both pages
- Unified `SyncStatus` enum replaces dual status systems

---

## Quick Reference: Orchestration Commands

### Phase 1: Type Definition & Backward Compatibility
```bash
# Parallel execution
Task("backend-typescript-architect", "Implement Phase 1: Type Definition & Backward Compatibility", model="opus")
```

### Phase 2: Registry Consolidation
```bash
Task("backend-typescript-architect", "Implement Phase 2: Registry Consolidation", model="opus")
```

### Phase 3: API Mapper Centralization
```bash
Task("backend-typescript-architect", "Implement Phase 3: API Mapper Centralization", model="opus")
```

### Phase 4: Component Type Unification
```bash
Task("ui-engineer-enhanced", "Implement Phase 4: Component Type Unification", model="opus")
```

### Phase 5: Deprecation & Cleanup
```bash
Task("documentation-writer", "Implement Phase 5: Deprecation & Cleanup", model="sonnet")
```

---

## Project Structure

Implementation organized into separate phase documents:

1. **[Phase 1-2: Type Definition & Registry](entity-artifact-consolidation-v1/phase-1-2-types.md)** - Type definition, backward compatibility, registry consolidation
2. **[Phase 3: API Mappers](entity-artifact-consolidation-v1/phase-3-mappers.md)** - Centralized mapper implementation
3. **[Phase 4-5: Components & Cleanup](entity-artifact-consolidation-v1/phase-4-5-components.md)** - Component unification and deprecation

---

## Complexity Assessment

### Why Large (L) + Full Track?

| Factor | Justification |
|--------|---------------|
| **Scope** | 5 sequential phases across entire type system and 20+ components |
| **Files Modified** | 40-50 files across types, hooks, components, and pages |
| **Risk** | High: Type changes, data mapping bugs, modal functionality |
| **Cross-cutting** | Affects both `/collection` and `/manage` pages, multiple hooks, multiple component types |
| **Testing** | Requires unit, integration, and E2E testing across both data pipelines |
| **Architecture** | Requires validation of type safety, status mapping logic, and data consistency |

**Model Selection**:
- **Opus** for architecture decisions, type design, complex mapping logic
- **Sonnet** for bulk component updates, simple refactoring
- **Haiku** for mechanical tasks (file search, status tracking)

---

## Phase Dependencies & Sequencing

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Type Definition & Backward Compatibility              │
│ - Create unified Artifact interface                             │
│ - Define SyncStatus enum                                        │
│ - Create backward compatibility aliases                         │
│ Dependencies: None                                              │
│ Duration: 3-4 days                                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Registry Consolidation                                 │
│ - Create ARTIFACT_TYPES registry                                │
│ - Update imports to use new registry                            │
│ - Create deprecation aliases                                    │
│ Dependencies: Phase 1 complete                                  │
│ Duration: 2-3 days                                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: API Mapper Centralization                              │
│ - Create single mapApiResponseToArtifact() function             │
│ - Implement determineSyncStatus() logic                         │
│ - Update hooks to use new mapper                                │
│ - Remove old conversion functions                               │
│ Dependencies: Phase 1-2 complete                                │
│ Duration: 4-5 days                                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Component Type Unification                             │
│ - Update UnifiedEntityModal to accept Artifact                  │
│ - Update all Entity-typed components                            │
│ - Refactor /collection and /manage pages                        │
│ Dependencies: Phase 1-3 complete                                │
│ Duration: 5-7 days                                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: Deprecation & Cleanup                                  │
│ - Add deprecation notices                                       │
│ - Document migration path                                       │
│ - Audit remaining Entity usages                                 │
│ - Update architecture docs                                      │
│ Dependencies: Phase 1-4 complete and passing all tests          │
│ Duration: 2-3 days                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Risk Summary & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Type compatibility during migration** | High | Phase 1 provides backward compatibility aliases; both old/new imports work throughout |
| **Data loss in mapper consolidation** | High | Side-by-side testing, unit tests for all 25+ properties, integration tests comparing before/after |
| **Incomplete modal handler coverage** | Medium | Phase 4 makes handlers required in props, runtime warning if missing, page wrappers ensure handlers |
| **Status determination logic bugs** | Medium | Implement incrementally with test coverage for each status value, QA all possible states |
| **Breaking changes to existing code** | Medium | Full test suite after each phase, TypeScript strict mode, manual QA per phase merge |
| **Performance regression** | Low | Profile old vs new mapper, monitor bundle size, no additional renders |

See detailed risk mitigations in phase documents.

---

## Quality Gates

### Phase Completion Criteria

Each phase must satisfy:
1. **TypeScript Compilation**: Zero errors in strict mode
2. **Test Coverage**: >85% for new/modified code
3. **Backward Compatibility**: Old imports still work (Phases 1-3)
4. **Visual Regression**: No changes to UI (all phases)
5. **Functional Verification**: Manual testing of affected features
6. **Code Review**: All changes reviewed by 2+ team members

### Cross-Phase Validation

- [ ] Existing tests pass (full test suite)
- [ ] Collection artifact display identical before/after
- [ ] Modal opens with complete data in both contexts
- [ ] Navigation handlers work consistently
- [ ] No console errors or warnings
- [ ] Bundle size delta <2%

---

## Key Files by Phase

### Phase 1 & 2 (Type Definition & Registry)

Primary files:
- `skillmeat/web/types/artifact.ts` - Expand with unified definition + registry
- `skillmeat/web/types/entity.ts` - Deprecate, re-export aliases

Files to update (imports):
- `skillmeat/web/components/**/*.tsx` - Update ENTITY_TYPES → ARTIFACT_TYPES imports
- `skillmeat/web/hooks/**/*.ts` - Update type imports
- `skillmeat/web/app/**/*.tsx` - Update type imports

### Phase 3 (API Mapping)

New files:
- `skillmeat/web/lib/api/mappers.ts` - Single mapper function

Modified files:
- `skillmeat/web/hooks/useArtifacts.ts` - Remove mapApiArtifact()
- `skillmeat/web/hooks/useEntityLifecycle.tsx` - Use new mapper
- `skillmeat/web/app/collection/page.tsx` - Remove artifactToEntity()
- `skillmeat/web/components/sync-status/sync-status-tab.tsx` - Remove entityToArtifact()

### Phase 4 (Component Unification)

Affected components (~15-20):
- `skillmeat/web/components/entity/unified-entity-modal.tsx`
- `skillmeat/web/components/entity/entity-form.tsx`
- `skillmeat/web/components/entity/modal-collections-tab.tsx`
- `skillmeat/web/components/entity/modal-sources-tab.tsx`
- `skillmeat/web/components/sync-status/**/*.tsx`
- `skillmeat/web/app/collection/page.tsx`
- `skillmeat/web/app/manage/page.tsx`

### Phase 5 (Deprecation)

Documentation:
- `.claude/guides/entity-to-artifact-migration.md` - Migration guide
- `skillmeat/web/CLAUDE.md` - Update type references
- `docs/project_plans/architecture/` - Update architecture docs

---

## Testing Strategy

### Unit Tests (Phase 3-4)

**Mapper Testing** (`lib/api/mappers.test.ts`):
- [ ] All 25+ properties mapped correctly
- [ ] All status enum values handled
- [ ] Optional fields preserved
- [ ] Flattened metadata structure correct
- [ ] Context parameter affects output (project vs collection)

**Type Safety** (TypeScript):
- [ ] No `any` types in unified code
- [ ] Backward compatibility aliases work
- [ ] Type inference correct for components

### Integration Tests (Phase 3-4)

**Data Pipeline** (`hooks/useArtifacts.test.ts`, `hooks/useEntityLifecycle.test.tsx`):
- [ ] `/collection` page receives complete artifact data
- [ ] `/manage` page receives complete entity/artifact data
- [ ] Modal opens with same data regardless of source

**Component Rendering** (`components/entity/__tests__/unified-entity-modal.test.tsx`):
- [ ] Collections tab renders with data
- [ ] Sources tab appears and fetches on demand
- [ ] Form submission works with new structure
- [ ] Navigation handlers called correctly

### E2E Tests (Phase 4-5)

**User Workflows**:
- [ ] User navigates to /collection, opens artifact modal
- [ ] Collections tab shows all collections
- [ ] Source tab appears without prior /marketplace visit
- [ ] Clicking source navigates correctly
- [ ] User navigates to /manage, opens artifact modal
- [ ] All modal features work identically to /collection

### Manual QA (All phases)

- [ ] Collections tab populated on /manage page (was empty in bug)
- [ ] Source tab appears on /collection page immediately
- [ ] Source link navigation functional on /collection page
- [ ] No synthetic fallback artifacts created
- [ ] All form CRUD operations work

---

## Effort Estimation

### Per-Phase Breakdown

| Phase | Tasks | Story Points | Duration | Critical Path |
|-------|-------|--------------|----------|---------------|
| **Phase 1** | 5 | 8 | 3-4 days | Yes (blocks all others) |
| **Phase 2** | 4 | 6 | 2-3 days | Yes (blocks Phase 3) |
| **Phase 3** | 6 | 12 | 4-5 days | Yes (critical mapper) |
| **Phase 4** | 8 | 13 | 5-7 days | Yes (component unification) |
| **Phase 5** | 3 | 6 | 2-3 days | No (docs only) |
| **Total** | **26** | **45** | **4-6 weeks** | **All phases** |

**Contingency**: +20% (~9 points) for unforeseen issues during component refactoring

---

## Success Metrics

| Metric | Target | Baseline | Impact |
|--------|--------|----------|--------|
| **Type definition files** | 1 | 2 | Code consolidation |
| **Conversion functions** | 0-1 | 4 | Maintenance burden |
| **Status enum values** | 5 unified | 4+4 separate | Type safety |
| **Modal/conversion bugs** | 0 | 3+ per sprint | Quality |
| **Component type consistency** | 100% | ~60% | Type safety |
| **Test coverage** | >85% | ~65% | Quality assurance |

---

## Implementation Approach

### Deployment Strategy

1. **Feature Branch**: `feat/entity-artifact-consolidation`
2. **Phase Merges**: Merge each phase separately after passing all quality gates
3. **Backward Compatibility**: Deprecation aliases maintained throughout 6-month window
4. **Rollback Capability**: Each phase can be rolled back independently

### Code Review Process

- [ ] All changes reviewed before merging
- [ ] TypeScript strict mode passes
- [ ] Test coverage >80%
- [ ] Backward compatibility maintained
- [ ] No performance regressions
- [ ] Migration guide up to date

### Daily Development

1. Implement phase tasks sequentially
2. Run full test suite after each task
3. Integration testing on /collection and /manage pages
4. Update progress YAML file daily
5. Document blockers in progress notes

---

## Related Documentation

### Analysis & Context

- [Entity vs Artifact Architecture Analysis](../../reports/entity-vs-artifact-architecture-analysis.md) - Root cause analysis and recommendations
- [Artifact Modal Architecture Analysis](../../reports/artifact-modal-architecture-analysis.md) - Bug fixes and architectural improvements
- [Original PRD](../../PRDs/refactors/entity-artifact-consolidation-v1.md) - Complete requirements specification

### Type System Reference

- `skillmeat/web/types/artifact.ts` (105 lines) - Current artifact type
- `skillmeat/web/types/entity.ts` (417 lines) - Current entity type (to be deprecated)
- `skillmeat/web/types/enums.ts` - Enum definitions

### Conversion Logic Reference

- `skillmeat/web/hooks/useArtifacts.ts:291-352` - `mapApiArtifact()`
- `skillmeat/web/hooks/useEntityLifecycle.tsx:194-255` - `mapApiArtifactToEntity()`
- `skillmeat/web/app/collection/page.tsx:100-147` - `artifactToEntity()`
- `skillmeat/web/components/sync-status/sync-status-tab.tsx:50-80` - `entityToArtifact()`

### Backend Reference

- `skillmeat/api/schemas/artifacts.py:164-232` - `ArtifactResponse` schema (no changes required)

---

## Phase Document Index

### Detailed Phase Implementation Plans

See separate phase documents for complete task breakdowns, acceptance criteria, and testing strategies:

1. **[Phase 1-2: Type Definition & Registry Consolidation](entity-artifact-consolidation-v1/phase-1-2-types.md)**
   - Create unified Artifact interface with all properties
   - Define SyncStatus enum (synced | modified | outdated | conflict | error)
   - Create backward compatibility aliases (Entity = Artifact)
   - Create ARTIFACT_TYPES registry (identical to ENTITY_TYPES)
   - Update all imports across ~20-30 files

2. **[Phase 3: API Mapper Centralization](entity-artifact-consolidation-v1/phase-3-mappers.md)**
   - Create `mapApiResponseToArtifact()` in new `lib/api/mappers.ts`
   - Implement `determineSyncStatus()` logic
   - Update `useArtifacts.ts` and `useEntityLifecycle.tsx`
   - Remove redundant conversion functions
   - Comprehensive unit & integration testing

3. **[Phase 4-5: Component Unification & Deprecation](entity-artifact-consolidation-v1/phase-4-5-components.md)**
   - Update UnifiedEntityModal to accept Artifact type
   - Refactor all Entity-typed components (~20 components)
   - Update /collection and /manage pages
   - Add deprecation notices and migration guide
   - Final validation and cleanup

---

## Next Steps

1. **Approval**: Confirm implementation plan with team
2. **Setup**: Create feature branch `feat/entity-artifact-consolidation`
3. **Phase 1**: Begin Phase 1 implementation (estimated 3-4 days)
4. **Daily Sync**: Coordinate with team on blockers/decisions
5. **Testing**: Run full test suite after each phase merge
6. **Documentation**: Update CLAUDE.md and architecture docs

---

**Document Owner**: Frontend Architect
**Last Updated**: 2026-01-28
**Status**: Ready for Implementation
**Approval**: [Pending]
