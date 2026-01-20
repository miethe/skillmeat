# Collections & Groups UX Enhancement v1 - Implementation Plan

**Status**: Ready for Development
**Created**: 2026-01-19
**Complexity**: Large (L) | **Total Effort**: 47 story points | **Timeline**: 3-4 weeks

---

## Quick Navigation

This directory contains the complete, detailed implementation plan for the Collections & Groups UX Enhancement. All documents follow a consistent structure and can be read independently.

### Master Plan

**File**: `../collections-groups-ux-enhancement-v1.md` (parent directory)

The master plan provides:
- Executive summary and strategic context
- Complete phase overview and dependencies
- Architecture and design decisions
- Quality standards and testing strategy
- Risk management and rollout plan
- Success metrics and monitoring

**Start here** if you're new to the project.

---

## Phase-Specific Documents

Each phase is documented in its own task file with detailed breakdown of work items.

### Phase 1: Data Layer & Hooks (8 SP, 3-4 days)

**File**: `phase-1-tasks.md`

**Scope**: Build foundation for data fetching
- `useGroups()` hook (verify existing implementation)
- `useArtifactGroups()` hook (new)
- `fetchArtifactGroups()` API client (new)
- Cache key hierarchy
- Error handling patterns
- Unit tests (≥80% coverage)

**Assigned To**: backend-typescript-architect (Opus)

**Handoff**: Phase 1 delivers working hooks that Phases 2-5 depend on

---

### Phase 2: Collection Badges on Cards (10 SP, 4-5 days)

**File**: `phase-2-tasks.md`

**Scope**: Add visual collection membership indicators
- `CollectionBadgeStack` component (new)
- Enhanced `UnifiedCard` component
- Badge positioning and styling
- Accessibility (WCAG 2.1 AA)
- Performance profiling (≤50ms per card)
- Unit & snapshot tests

**Assigned To**: ui-engineer-enhanced (Opus)

**Dependencies**: Phase 1
**Handoff**: Collection badge pattern reused in Phase 3

---

### Phase 3: Group Badges & Modal Enhancement (9 SP, 4-5 days)

**File**: `phase-3-tasks.md`

**Scope**: Add group membership indicators and modal groups display
- `GroupBadgeRow` component (new)
- `GroupsDisplay` component (new)
- Enhanced `UnifiedCard` with group badges
- Enhanced `ModalCollectionsTab` with groups section
- Badge styling (distinct from collection badges)
- Unit & snapshot tests
- Accessibility validation

**Assigned To**: ui-engineer-enhanced (Opus)

**Dependencies**: Phases 1-2
**Handoff**: GroupsDisplay and badge styling reused in Phase 4

---

### Phase 4: Groups Sidebar Page (12 SP, 5-6 days)

**File**: `phase-4-tasks.md`

**Scope**: Create dedicated `/groups` page
- Sidebar navigation item ("Groups")
- `/groups` page layout and routing
- `GroupsPageClient` main component
- `GroupSelector` dropdown component
- `GroupArtifactGrid` artifact display
- `ViewModeToggle` (Grid/List)
- Filters integration
- Unit tests and E2E happy path test
- Performance profiling (groups ≤200ms, artifacts ≤500ms)

**Assigned To**: frontend-developer (Opus)

**Dependencies**: Phases 1-3
**Handoff**: Group selector and filtering patterns inform Phase 5

---

### Phase 5: Group Filter Integration (8 SP, 3-4 days)

**File**: `phase-5-tasks.md`

**Scope**: Add group filtering to collection/manage pages
- `GroupFilterSelect` component (new)
- Enhanced `Filters` component (/collection page)
- Enhanced `EntityFilters` component (/manage page)
- Query hook integration (groupId support)
- URL parameter handling
- Unit & integration tests
- E2E verification

**Assigned To**: ui-engineer-enhanced (Sonnet)

**Dependencies**: Phases 1-4
**Note**: Can use Sonnet model for cost efficiency (well-scoped task)

---

## Navigating the Plan

### For Project Managers

1. Read: Master plan Executive Summary
2. Review: Phase Overview & Dependencies table
3. Track: Phase-specific Definition of Done sections
4. Monitor: Quality Gates and Risk Management sections

### For Developers

1. Read: Master plan Architecture Overview
2. Review: Your assigned phase task document
3. Implement: Tasks in order (dependencies matter!)
4. Test: Quality gates before phase completion
5. Handoff: Review "Handoff to Phase N+1" section

### For QA/Testing Engineers

1. Read: Master plan Testing Strategy section
2. Review: Phase-specific test cases
3. Run: Integration tests between phases
4. Monitor: Performance benchmarks
5. Validate: Accessibility compliance

### For UI/Design Engineers

1. Read: Phase 2 "Badge Positioning & Styling" (P2-T3)
2. Coordinate: Design decisions documented there
3. Review: Phase 3 "Coordinate Badge Styling" (P3-T5)
4. Approve: Component snapshots in test files

---

## Key Decisions & Assumptions

### Architectural Decisions

1. **Hook-First Approach**: All data fetching via custom hooks with TanStack Query
2. **No Backend Changes**: Leverage existing Groups API (no new endpoints)
3. **Conditional Rendering**: Badges shown contextually (collection vs. group view)
4. **Graceful Degradation**: Missing data skips badge render (not error state)
5. **Design System Reuse**: shadcn components, Tailwind, existing patterns

### Key Assumptions

1. Backend `/groups` API is complete and working (verified in Phase 1)
2. `Entity.collections` array is populated (already done by `artifactToEntity` conversion)
3. useCollectionContext() provides `selectedCollectionId` and view mode
4. Performance target ≤200ms added latency is acceptable
5. Design team available for coordination in Phases 2-3

### Open Questions (Deferred to Design Phase)

- Should group badges be clickable (navigate to /groups)?
- Badge position: top-right corner or below type indicator?
- Group filter: should it filter across collections on /manage page?

---

## Timeline & Resource Plan

### Critical Path

```
Phase 1 (Hooks)
    ↓
Phase 2 (Collection Badges) + Phase 3 (Group Badges) [parallel]
    ↓
Phase 4 (Groups Page)
    ↓
Phase 5 (Group Filter)
    ↓
Integration & Rollout
```

### Team Allocation

| Role | Phases | Estimated Hours |
|------|--------|-----------------|
| Backend/TS Architect (Opus) | 1 | 35-40 |
| UI Engineer (Opus) | 2, 3 | 40-50 |
| Frontend Developer (Opus) | 4 | 50-60 |
| UI Engineer (Sonnet) | 5 | 25-35 |
| Code Reviewer | All | 10-15 |
| QA/Testing | All | 30-40 |
| **Total** | | **200-240 hours** |

### Week-by-Week Breakdown

**Week 1**:
- Days 1-3: Phase 1 (hooks)
- Days 3-5: Phase 2 start (collection badges)

**Week 2**:
- Days 1-3: Phase 2 finish + Phase 3 start (parallel)
- Days 3-5: Phase 3 + Phase 4 start

**Week 3**:
- Days 1-4: Phase 4 (groups page)
- Day 5: Phase 5 start

**Week 4**:
- Days 1-3: Phase 5 (group filter)
- Days 4-5: Integration testing, fixes

**Final Days**:
- Code review, acceptance
- Beta rollout, monitoring setup

---

## Quality Standards

### Code Quality Checklist

All new code must:
- [ ] Use TypeScript strict mode (no `any` types)
- [ ] Pass ESLint with zero warnings
- [ ] Include JSDoc comments with examples
- [ ] Have ≥80% test coverage
- [ ] Follow project conventions (imports, naming, structure)

### Testing Requirements

- [ ] Unit tests for all components and hooks
- [ ] Snapshot tests for visual components
- [ ] Integration tests for multi-component workflows
- [ ] E2E test for happy path (all 5 components together)
- [ ] Performance profiling (compare before/after)
- [ ] Accessibility audit (axe DevTools, Lighthouse)

### Accessibility (WCAG 2.1 AA)

- [ ] Color contrast: ≥4.5:1 ratio for badges
- [ ] Keyboard navigation: Tab through all interactive elements
- [ ] Screen reader: all badges have aria-labels
- [ ] Focus visibility: clear focus indicators
- [ ] Semantic HTML: proper heading hierarchy, landmark roles

### Performance Targets

- Phase 2-3: Card render ≤50ms per card (with badges)
- Phase 4: Groups page load ≤200ms (groups list), ≤500ms (artifacts)
- Phase 5: Filter dropdown ≤150ms to populate
- Overall: ≤200ms added latency on /collection page

---

## Risk Management

### High-Risk Items

| Risk | Mitigation |
|------|-----------|
| **N+1 Query Problem** (100+ cards, 1 fetch each) | Use TanStack Query deduplication; implement batching |
| **Performance Regression** (badges slow page) | Profile early; lazy-load badges; implement virtualization if needed |
| **Stale Data** (groups not updating after mutations) | Hierarchical cache invalidation; test mutations |
| **Scope Creep** (drag-drop, bulk ops added) | Strictly enforce In-Scope list; defer to Phase 2 |
| **Accessibility Failures** (WCAG audit fails) | Test early with axe DevTools; use color contrast checker |

### Rollback Triggers

If any of these occur, trigger rollback:
- Error rate >0.5%
- Page load latency >500ms (>200ms increase)
- WCAG Level A accessibility failures
- Data loss or corruption
- Critical bugs affecting >5% of users

---

## Success Criteria

### Product Metrics (Post-Rollout)

| Metric | Target | Method |
|--------|--------|--------|
| Groups page adoption | 60%+ users within 2 weeks | GA: `groups_page_visited` |
| Group filter usage | 40%+ of collection sessions | GA: `group_filter_applied` |
| Modal engagement | 50%+ of modal opens with group interaction | GA: `modal_groups_viewed` |
| Card usability | +15 NPS point improvement | Post-launch survey |
| Performance | ≤200ms added latency | RUM/Lighthouse |
| Accessibility | Zero WCAG A failures | Issue tracker, audits |

### Engineering Metrics

| Metric | Target |
|--------|--------|
| Test coverage | ≥80% across all new code |
| Code review time | <24 hours turnaround |
| Build time | No increase (tests <5 min) |
| Type safety | Zero TypeScript errors |

---

## Deliverables Checklist

### Code Deliverables

- [ ] `use-artifact-groups.ts` hook (Phase 1)
- [ ] `fetchArtifactGroups()` API function (Phase 1)
- [ ] `collection-badge-stack.tsx` component (Phase 2)
- [ ] `group-badge-row.tsx` component (Phase 3)
- [ ] `groups-display.tsx` component (Phase 3)
- [ ] `/groups` page (Phase 4)
- [ ] `group-selector.tsx` component (Phase 4)
- [ ] `group-artifact-grid.tsx` component (Phase 4)
- [ ] `view-mode-toggle.tsx` component (Phase 4)
- [ ] `group-filter-select.tsx` component (Phase 5)

### Modified Files

- [ ] `unified-card.tsx` (Phases 2-3)
- [ ] `filters.tsx` (Phase 5)
- [ ] `entity-filters.tsx` (Phase 5)
- [ ] `modal-collections-tab.tsx` (Phase 3)
- [ ] `navigation.tsx` (Phase 4)
- [ ] `hooks/use-groups.ts` (Phase 1, 4)
- [ ] `hooks/index.ts` (Phase 1)

### Test Deliverables

- [ ] ≥80% coverage across all new code
- [ ] Snapshot test baselines
- [ ] E2E test suite (all 5 scenarios)
- [ ] Performance benchmark report
- [ ] Accessibility audit report

### Documentation Deliverables

- [ ] JSDoc comments on all exported functions
- [ ] Architecture decision record
- [ ] Design decisions documented in code comments
- [ ] Performance benchmark recorded
- [ ] User documentation (help center article)

---

## How to Use This Plan

### Starting Development

1. **Read** Phase 1 task document entirely
2. **Create** branch: `feat/collections-groups-ux/phase-1-hooks`
3. **Implement** tasks P1-T1 through P1-T8 in order
4. **Test**: Each task has acceptance criteria and quality gates
5. **Review**: Ensure all quality gates pass before phase completion
6. **Merge**: After code review approval
7. **Move to Phase 2** when Phase 1 complete

### During Development

- **Blockers**: Document in master plan "Risks" section
- **Design decisions**: Coordinate with UI team immediately (don't delay)
- **Performance issues**: Profile early; document findings
- **Test failures**: Fix before moving to next phase (dependencies matter)

### After Phase Completion

- **Record metrics**: Actual hours vs. estimate for retrospective
- **Document learnings**: Any gotchas or patterns discovered
- **Prepare handoff**: Review "Handoff to Phase N+1" section
- **Brief next team**: Share key decisions and patterns

---

## References & Resources

### Project Documentation

- **Master Plan**: `../collections-groups-ux-enhancement-v1.md`
- **Original PRD**: `/docs/project_plans/PRDs/harden-polish/collections-groups-ux-enhancement-v1.md`
- **Web CLAUDE.md**: `/skillmeat/web/CLAUDE.md`

### Code References

- **Groups Types**: `/skillmeat/web/types/groups.ts`
- **Groups API**: `/skillmeat/web/lib/api/groups.ts`
- **Groups Hooks**: `/skillmeat/web/hooks/use-groups.ts`
- **UnifiedCard**: `/skillmeat/web/components/shared/unified-card.tsx`

### External Resources

- **TanStack Query**: https://tanstack.com/query/latest
- **shadcn/ui**: https://ui.shadcn.com/
- **WCAG 2.1**: https://www.w3.org/WAI/WCAG21/quickref/
- **Lighthouse**: https://developers.google.com/web/tools/lighthouse

---

## Support & Questions

### Getting Help

1. **Phase questions**: Review master plan relevant section
2. **Technical blockers**: Ask in #engineering Slack
3. **Design coordination**: Reach out to UI team early
4. **Performance issues**: Use React DevTools Profiler

### Escalation

- **Scope changes**: Discuss with project lead
- **Timeline delays**: Report ASAP; adjust plan
- **Technical blockers**: Document in PRD "Open Questions" section

---

## Approval & Sign-Off

**Plan Status**: ✅ READY FOR DEVELOPMENT

**Approved By**: Claude Code (AI Agent)
**Date**: 2026-01-19
**Last Updated**: 2026-01-19

**Next Steps**:
1. Create Linear board with phase stories
2. Assign engineers to phases
3. Begin Phase 1 development
4. Daily standups during development weeks

---

**Implementation Plan Complete**

All phases are ready for execution. Begin with Phase 1 and proceed sequentially.
