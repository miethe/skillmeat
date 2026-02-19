---
parent: ../marketplace-source-detection-improvements-v1.md
section: Quality Assurance Gates
status: inferred_complete
---
# Quality Assurance Gates

## Phase 1 Gate

**Entry Criteria:**
- PRD approved and finalized
- Codebase ready for changes

**Exit Criteria:**
- [ ] All schema validation tests pass
- [ ] No existing data corrupted
- [ ] Backward compatibility confirmed
- [ ] Code review approved

**Sign-off:** Data layer lead

---

## Phase 2 Gate

**Entry Criteria:**
- Phase 1 complete and signed off

**Exit Criteria:**
- [ ] All heuristic detector tests pass (>70% coverage)
- [ ] All deduplication engine tests pass (>80% coverage)
- [ ] All integration tests pass (>60% coverage)
- [ ] Performance regression < 10% on existing scans
- [ ] Confidence scoring validated
- [ ] Code review approved

**Sign-off:** Backend team lead

---

## Phase 3 Gate

**Entry Criteria:**
- Phase 2 complete and signed off

**Exit Criteria:**
- [ ] All API tests pass (>75% coverage)
- [ ] PATCH endpoint validates and persists manual_map correctly
- [ ] GET endpoint returns manual_map
- [ ] Rescan applies manual_map and returns dedup counts
- [ ] OpenAPI documentation complete and accurate
- [ ] No breaking changes to existing API
- [ ] Code review approved

**Sign-off:** API team lead

---

## Phase 4 Gate

**Entry Criteria:**
- Phase 3 complete and signed off

**Exit Criteria:**
- [ ] All component tests pass (>60% coverage)
- [ ] Modal renders correctly with 100+ directories
- [ ] Type selectors and hierarchical mapping work
- [ ] Save/rescan actions call correct endpoints
- [ ] No console errors or TypeScript errors
- [ ] WCAG AA accessibility audit passes
- [ ] Code review approved

**Sign-off:** Frontend team lead

---

## Phase 5 Gate

**Entry Criteria:**
- Phase 4 complete and signed off

**Exit Criteria:**
- [ ] All E2E tests pass
- [ ] Edge cases handled gracefully
- [ ] Performance targets met
- [ ] Backward compatibility verified
- [ ] User documentation complete
- [ ] API documentation updated
- [ ] Developer guide complete
- [ ] Deployment checklist signed off
- [ ] Security review completed
- [ ] Code review approved

**Sign-off:** QA lead + Release manager
