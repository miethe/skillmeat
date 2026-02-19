---
status: inferred_complete
---
# Implementation Plan: Marketplace Source Enhancements v1

**PRD Reference**: `docs/project_plans/PRDs/enhancements/marketplace-source-enhancements-v1.md`
**Status**: Ready for Execution
**Created**: 2025-12-31
**Complexity**: Medium (M)
**Track**: Standard
**Estimated Effort**: 34 story points
**Timeline**: 3 weeks

---

## Executive Summary

This implementation plan delivers three incremental UX enhancements to the marketplace source catalog experience:

1. **Frontmatter Display Component** - Structured YAML frontmatter viewer in catalog modal
2. **Tabbed Artifact Type Filter** - Replace dropdown with horizontal tabs (matching /manage page)
3. **"Not an Artifact" Marking** - Allow users to mark and hide false positive detections

**Value Proposition**: Improves catalog browsing efficiency by 40% through reduced clicks (2→1 for filtering), enhanced content visibility (frontmatter display), and data quality improvements (user-driven exclusions).

**Architecture Impact**:
- **Frontend-Only** (Features 1-2): No backend changes, reuse existing components
- **Full-Stack** (Feature 3): Database schema extension, new API endpoints, UI integration

**Key Patterns Reused**:
- EntityTabs component pattern from `/manage` page
- ContentPane integration for frontmatter display
- Radix UI primitives (Tabs, Collapsible, Dialog)
- TanStack Query mutation patterns
- Database soft-delete pattern (excluded_at timestamp)

---

## Implementation Phases

### Phase Overview

| Phase | Focus | Deliverables | Effort | Track |
|-------|-------|--------------|--------|-------|
| **Phase 1** | Frontend Foundation | Features 1-2 (Frontmatter + Tabs) | 13 SP | Fast Track (Haiku) |
| **Phase 2** | Backend Exclusions | Feature 3 Database + API | 8 SP | Standard Track (Haiku + Sonnet) |
| **Phase 3** | Frontend Exclusions | Feature 3 UI Integration | 8 SP | Standard Track (Haiku + Sonnet) |
| **Phase 4** | Polish & Testing | QA, Documentation, Release | 5 SP | Full Track (All models) |

**Total Effort**: 34 story points (~3 weeks with 1 developer)

---

## Phase 1: Frontend Foundation (Week 1)

**Goal**: Deliver frontmatter display and tabbed filtering without backend changes.

**Deliverables**:
- Frontmatter parsing utility (`lib/frontmatter.ts`)
- FrontmatterDisplay component (`components/entity/frontmatter-display.tsx`)
- CatalogTabs component (`app/marketplace/sources/[id]/components/catalog-tabs.tsx`)
- Integration into source detail page

### Task Breakdown

| ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To |
|----|-----------|-------------|---------------------|----------|-------------|
| **TASK-1.1** | Create frontmatter parsing utility | Implement `lib/frontmatter.ts` with YAML detection and parsing logic | - Detects `---\n...\n---\n` pattern<br>- Parses YAML safely with error handling<br>- Strips frontmatter from content<br>- Returns parsed object or null | 2h | ui-engineer |
| **TASK-1.2** | Create FrontmatterDisplay component | Build reusable collapsible frontmatter viewer with Radix Collapsible | - Props: frontmatter, collapsed, onToggle, variant<br>- Renders key-value pairs with bold keys<br>- Supports nested objects (1 level)<br>- Arrays as comma-separated values<br>- Max height 300px with scroll | 3h | ui-engineer-enhanced |
| **TASK-1.3** | Integrate frontmatter into ContentPane | Modify `components/entity/content-pane.tsx` to detect and display frontmatter | - Detects .md files with frontmatter<br>- Shows FrontmatterDisplay above content<br>- Strips frontmatter from displayed content<br>- Handles invalid YAML gracefully (warning) | 2h | ui-engineer-enhanced |
| **TASK-1.4** | Wire frontmatter to CatalogEntryModal | Update modal Contents tab to trigger frontmatter parsing | - Passes file content to parsing utility<br>- Renders FrontmatterDisplay when detected<br>- No rendering for non-.md or no frontmatter<br>- Smooth expand/collapse animation | 1h | ui-engineer-enhanced |
| **TASK-1.5** | Create CatalogTabs component | Build tabbed filter adapting EntityTabs pattern from /manage | - Tabs: All Types, Skills, Agents, Commands, MCP, Hooks<br>- Shows counts: "Skills (12)"<br>- Active tab highlighted (blue underline)<br>- Updates filters.artifact_type on click<br>- Syncs to URL ?type=skill | 3h | ui-engineer-enhanced |
| **TASK-1.6** | Replace Select dropdown with tabs | Integrate CatalogTabs into source detail page (lines 509-530) | - Tabs replace Select dropdown<br>- Filter state preserved<br>- URL sync works correctly<br>- Responsive design (horizontal scroll on mobile)<br>- Zero-count types shown but grayed | 2h | ui-engineer-enhanced |
| **TASK-1.7** | Unit tests for frontmatter utility | Test parsing, detection, error handling | - Valid YAML parsed correctly<br>- Invalid YAML returns null<br>- Frontmatter stripped from content<br>- Edge cases: empty, malformed, nested | 1h | ui-engineer |
| **TASK-1.8** | Unit tests for FrontmatterDisplay | Test component rendering and interaction | - Key-value pairs render correctly<br>- Collapse/expand toggle works<br>- Arrays render as comma-separated<br>- Nested objects indented | 1h | ui-engineer-enhanced |

**Quality Gates**:
- [ ] All unit tests pass with >80% coverage
- [ ] Frontmatter parsing <50ms for typical files (<10KB)
- [ ] Tab click → filter update <100ms
- [ ] No console errors or warnings
- [ ] Accessibility: keyboard navigation works, ARIA labels present
- [ ] Visual regression: matches design specs (Tailwind colors, spacing)

**Orchestration Quick Reference**:

**Batch 1** (Parallel - Haiku):
```
Task("ui-engineer", "TASK-1.1: Create lib/frontmatter.ts
     - Detect YAML frontmatter (^---\n...\n---\n)
     - Parse with yaml library, handle errors
     - Export: detectFrontmatter(), parseFrontmatter(), stripFrontmatter()
     - Return null on invalid YAML (don't throw)")

Task("ui-engineer", "TASK-1.7: Unit tests for frontmatter utility
     - Test file: __tests__/lib/frontmatter.test.ts
     - Valid YAML: parse correctly, strip from content
     - Invalid YAML: return null, no crash
     - Edge cases: empty, malformed, nested objects")
```

**Batch 2** (Parallel - Sonnet, depends on Batch 1):
```
Task("ui-engineer-enhanced", "TASK-1.2: Create FrontmatterDisplay component
     File: components/entity/frontmatter-display.tsx
     Props: frontmatter (Record<string,any>), collapsed (bool), onToggle, variant
     - Use Radix Collapsible primitive
     - Render key-value grid: <strong>{key}</strong>: {value}
     - Arrays as comma-separated, nested objects 1 level deep
     - Styling: bg-muted/30, border, max-height 300px")

Task("ui-engineer-enhanced", "TASK-1.5: Create CatalogTabs component
     File: app/marketplace/sources/[id]/components/catalog-tabs.tsx
     - Adapt EntityTabs pattern from app/manage/components/entity-tabs.tsx
     - Tabs: All Types, Skills, Agents, Commands, MCP, Hooks (use ENTITY_TYPES)
     - Show counts from catalogData.pages[0].counts_by_type
     - Update filters.artifact_type on click, sync to URL
     - Radix Tabs with data-[state=active] styling")

Task("ui-engineer-enhanced", "TASK-1.8: Unit tests for FrontmatterDisplay
     File: __tests__/components/entity/frontmatter-display.test.tsx
     - Renders key-value pairs correctly
     - Collapse/expand toggle works
     - Arrays render as comma-separated
     - Nested objects render indented")
```

**Batch 3** (Sequential - Sonnet, depends on Batch 2):
```
Task("ui-engineer-enhanced", "TASK-1.3: Integrate frontmatter into ContentPane
     File: components/entity/content-pane.tsx
     - Import: parseFrontmatter from lib/frontmatter
     - Detect .md files, extract frontmatter if present
     - Render FrontmatterDisplay above content
     - Strip frontmatter from content display
     - Handle invalid YAML: show warning, hide frontmatter section")

Task("ui-engineer-enhanced", "TASK-1.4: Wire frontmatter to CatalogEntryModal
     File: Check which modal component renders Contents tab
     - Pass file content to frontmatter parsing
     - Render FrontmatterDisplay when detected
     - Only for .md files with valid frontmatter
     - Test with real artifact: anthropics/skills/canvas-design")

Task("ui-engineer-enhanced", "TASK-1.6: Replace Select dropdown with tabs
     File: app/marketplace/sources/[id]/page.tsx (lines 509-530)
     - Replace Select with CatalogTabs component
     - Pass filters, setFilters, counts_by_type
     - Remove Select import and component
     - Verify filter state and URL sync work
     - Test responsive: mobile scroll, desktop full width")
```

---

## Phase 2: Backend Exclusions (Week 2)

**Goal**: Extend database schema and API to support artifact exclusion.

**Deliverables**:
- Database migration (Alembic)
- Updated SQLAlchemy models
- PATCH endpoint for exclusion/restoration
- Schema updates for API

### Task Breakdown

| ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To |
|----|-----------|-------------|---------------------|----------|-------------|
| **TASK-2.1** | Update marketplace types | Add 'excluded' to CatalogStatus enum in frontend types | - `types/marketplace.ts`: CatalogStatus includes 'excluded'<br>- Type exported and used in API types | 0.5h | ui-engineer |
| **TASK-2.2** | Create Alembic migration | Add excluded_at, excluded_reason columns to catalog table | - Migration file: `versions/YYYYMMDD_HHMM_add_exclusion_to_catalog.py`<br>- Columns nullable (default NULL)<br>- Upgrade/downgrade tested on dev DB<br>- No data loss on rollback | 1h | data-layer-expert |
| **TASK-2.3** | Update MarketplaceCatalogEntry model | Add excluded_at, excluded_reason fields to SQLAlchemy model | - File: `cache/models.py`<br>- `excluded_at: Mapped[Optional[datetime]]`<br>- `excluded_reason: Mapped[Optional[str]]`<br>- Fields documented in docstring | 0.5h | python-backend-engineer |
| **TASK-2.4** | Add exclusion schemas | Create request/response schemas for exclusion API | - File: `api/schemas/marketplace.py`<br>- `ExcludeEntryRequest(excluded: bool, reason: str | None)`<br>- `ExcludeEntryResponse` extends CatalogEntryResponse<br>- Pydantic validation | 1h | python-backend-engineer |
| **TASK-2.5** | Implement exclude/restore endpoint | Add PATCH `/marketplace/sources/{id}/artifacts/{entry_id}/exclude` | - Router: `api/routers/marketplace_sources.py`<br>- Updates excluded_at, excluded_reason<br>- Returns updated CatalogEntryResponse<br>- Sets status='excluded' when excluded=true<br>- Clears excluded fields when excluded=false | 2h | python-backend-engineer |
| **TASK-2.6** | Update catalog list endpoint | Filter out excluded entries by default, add ?include_excluded param | - Modify GET `/marketplace/sources/{id}/artifacts`<br>- Default: WHERE excluded_at IS NULL<br>- Param: ?include_excluded=true shows all<br>- Update counts_by_status to include excluded count | 1h | python-backend-engineer |
| **TASK-2.7** | Preserve exclusions during rescan | Ensure rescans don't overwrite excluded status | - File: `marketplace/scanner.py` (or equivalent)<br>- Check if entry has excluded_at before updating<br>- Skip status updates for excluded entries<br>- Document behavior in code comments | 1h | python-backend-engineer |
| **TASK-2.8** | Unit tests for exclusion API | Test exclude/restore mutations | - Test file: `tests/api/test_marketplace_exclusion.py`<br>- Mark as excluded: sets timestamp, status<br>- Restore: clears fields, returns to 'new' status<br>- Invalid entry ID: 404 error<br>- Excluded entries hidden from default list | 1h | python-backend-engineer |

**Quality Gates**:
- [ ] Migration runs successfully (up and down)
- [ ] Alembic current shows latest migration
- [ ] API tests pass with >80% coverage
- [ ] Excluded entries filtered from catalog list by default
- [ ] Rescan preserves excluded status (tested manually)
- [ ] OpenAPI spec updated automatically (FastAPI introspection)

**Orchestration Quick Reference**:

**Batch 1** (Parallel - Haiku + Sonnet):
```
Task("ui-engineer", "TASK-2.1: Update marketplace types
     File: skillmeat/web/types/marketplace.ts (line 114)
     - Change: export type CatalogStatus = 'new' | 'updated' | 'removed' | 'imported' | 'excluded';
     - Verify: type exported and used in CatalogEntry interface")

Task("data-layer-expert", "TASK-2.2: Create Alembic migration
     - Command: cd skillmeat && alembic revision -m 'add_exclusion_to_catalog'
     - File: skillmeat/api/migrations/versions/YYYYMMDD_HHMM_add_exclusion_to_catalog.py
     - Upgrade: add excluded_at (DateTime), excluded_reason (Text), both nullable
     - Downgrade: drop both columns
     - Test: alembic upgrade head && alembic downgrade -1")
```

**Batch 2** (Sequential - Sonnet, depends on Batch 1):
```
Task("python-backend-engineer", "TASK-2.3: Update MarketplaceCatalogEntry model
     File: skillmeat/cache/models.py (class MarketplaceCatalogEntry)
     - Add: excluded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
     - Add: excluded_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
     - Update docstring: document new fields")

Task("python-backend-engineer", "TASK-2.4: Add exclusion schemas
     File: skillmeat/api/schemas/marketplace.py
     - Create ExcludeEntryRequest(BaseModel): excluded (bool), reason (str | None)
     - Update CatalogEntryResponse: ensure status field accepts 'excluded'
     - Add validation: reason max 500 chars")
```

**Batch 3** (Sequential - Sonnet, depends on Batch 2):
```
Task("python-backend-engineer", "TASK-2.5: Implement exclude/restore endpoint
     File: skillmeat/api/routers/marketplace_sources.py
     - Add: @router.patch('/{source_id}/artifacts/{entry_id}/exclude')
     - Logic: if excluded=true → set excluded_at=now, status='excluded'
     - Logic: if excluded=false → clear excluded_at, excluded_reason, status='new'
     - Return: updated CatalogEntryResponse
     - Error handling: 404 if entry not found")

Task("python-backend-engineer", "TASK-2.6: Update catalog list endpoint
     File: skillmeat/api/routers/marketplace_sources.py (GET /{source_id}/artifacts)
     - Add query param: include_excluded (bool, default False)
     - Filter: WHERE excluded_at IS NULL if not include_excluded
     - Update counts_by_status: add 'excluded' count
     - Test: verify excluded entries hidden by default")

Task("python-backend-engineer", "TASK-2.7: Preserve exclusions during rescan
     File: Find scanner logic (marketplace/scanner.py or similar)
     - Before updating entry status: check if excluded_at is not NULL
     - If excluded: skip status update, preserve excluded_at/reason
     - Add comment: 'Preserve manual exclusions during rescan'")

Task("python-backend-engineer", "TASK-2.8: Unit tests for exclusion API
     File: tests/api/test_marketplace_exclusion.py
     - Test exclude: verify excluded_at set, status='excluded'
     - Test restore: verify fields cleared, status='new'
     - Test list filter: excluded entries not in default response
     - Test rescan preservation: mock rescan, verify excluded status kept")
```

---

## Phase 3: Frontend Exclusions (Week 2-3)

**Goal**: Build UI for marking, viewing, and restoring excluded artifacts.

**Deliverables**:
- Exclusion dialog component
- "Not an Artifact" link on catalog cards
- Excluded artifacts list section
- TanStack Query mutations

### Task Breakdown

| ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To |
|----|-----------|-------------|---------------------|----------|-------------|
| **TASK-3.1** | Add exclusion hooks | Create useExcludeCatalogEntry, useRestoreCatalogEntry mutations | - File: `hooks/useMarketplaceSources.ts`<br>- useExcludeCatalogEntry: calls PATCH with excluded=true<br>- useRestoreCatalogEntry: calls PATCH with excluded=false<br>- Invalidates catalog query on success<br>- Error handling with toast notification | 2h | ui-engineer |
| **TASK-3.2** | Create ExcludeArtifactDialog component | Confirmation dialog with Radix Dialog | - File: `components/marketplace/exclude-artifact-dialog.tsx`<br>- Props: entry, onConfirm, onCancel<br>- Message: "Mark this as not an artifact?"<br>- Shows entry name and description<br>- Buttons: Cancel (outline), Mark as Excluded (destructive) | 2h | ui-engineer-enhanced |
| **TASK-3.3** | Add "Not an Artifact" link to CatalogCard | Integrate exclusion trigger into card UI | - File: Find CatalogCard component (grep for catalog card)<br>- Add link below Import button<br>- Text: "Not an artifact" (text-muted-foreground)<br>- Opens ExcludeArtifactDialog on click<br>- Only shown for non-excluded entries | 1h | ui-engineer-enhanced |
| **TASK-3.4** | Create ExcludedArtifactsList component | Table component showing excluded entries | - File: `app/marketplace/sources/[id]/components/excluded-list.tsx`<br>- Collapsible section: "Show Excluded Artifacts (N)"<br>- Table columns: Name, Path, Excluded At, Actions<br>- Restore button per row<br>- Empty state: "No excluded artifacts" | 2h | ui-engineer-enhanced |
| **TASK-3.5** | Integrate excluded list into source page | Add collapsible section below catalog grid | - File: `app/marketplace/sources/[id]/page.tsx`<br>- Query catalog with ?include_excluded=true for count<br>- Render ExcludedArtifactsList component<br>- Default collapsed, expand on click<br>- Update on restore mutation success | 1h | ui-engineer-enhanced |
| **TASK-3.6** | Update Select All to skip excluded | Filter excluded entries from bulk selection | - File: Find bulk import logic in source page<br>- Filter: entries.filter(e => e.status !== 'excluded')<br>- Update Select All button count<br>- Visual feedback: excluded count shown separately | 1h | ui-engineer-enhanced |
| **TASK-3.7** | Add excluded status badge | Visual indicator for excluded entries | - File: Find status badge component<br>- Add 'excluded' case: gray badge "Excluded"<br>- Color: border-gray-400 text-gray-600 bg-gray-100<br>- Show in catalog card and excluded list | 0.5h | ui-engineer-enhanced |
| **TASK-3.8** | E2E test for exclusion workflow | Test mark → disappear → restore → reappear | - File: `tests/e2e/marketplace-exclusion.spec.ts`<br>- Navigate to source detail page<br>- Click "Not an artifact" → confirm → verify card disappears<br>- Open excluded list → find entry → restore → verify reappears<br>- Verify counts update correctly | 1.5h | ui-engineer |

**Quality Gates**:
- [ ] Exclusion mutation <500ms round-trip
- [ ] Excluded entries disappear from grid immediately (optimistic update)
- [ ] Excluded list updates on restore
- [ ] Select All count excludes excluded entries
- [ ] E2E test passes on CI
- [ ] No flickering or layout shift during mutations
- [ ] Accessibility: dialog keyboard-navigable, focus management

**Orchestration Quick Reference**:

**Batch 1** (Parallel - Haiku + Sonnet):
```
Task("ui-engineer", "TASK-3.1: Add exclusion hooks
     File: skillmeat/web/hooks/useMarketplaceSources.ts
     - useExcludeCatalogEntry: useMutation, POST /exclude with excluded=true
     - useRestoreCatalogEntry: useMutation, POST /exclude with excluded=false
     - onSuccess: invalidate catalog query
     - onError: show toast with error message")

Task("ui-engineer-enhanced", "TASK-3.2: Create ExcludeArtifactDialog
     File: skillmeat/web/components/marketplace/exclude-artifact-dialog.tsx
     - Use Radix Dialog primitive
     - Props: entry (CatalogEntry), open (bool), onConfirm, onCancel
     - Message: 'Mark this as not an artifact?'
     - Show entry name, note about Excluded list recovery
     - Buttons: Cancel (variant='outline'), Mark as Excluded (variant='destructive')")
```

**Batch 2** (Sequential - Sonnet, depends on Batch 1):
```
Task("ui-engineer-enhanced", "TASK-3.3: Add 'Not an Artifact' link to CatalogCard
     - Find CatalogCard component: grep 'CatalogCard' in app/marketplace
     - Add link below Import button: 'Not an artifact'
     - Styling: text-sm text-muted-foreground hover:underline
     - Opens ExcludeArtifactDialog with entry prop
     - Only render if entry.status !== 'excluded'")

Task("ui-engineer-enhanced", "TASK-3.4: Create ExcludedArtifactsList component
     File: skillmeat/web/app/marketplace/sources/[id]/components/excluded-list.tsx
     - Use Radix Collapsible for section
     - Header: 'Show Excluded Artifacts ({excludedCount})'
     - Table: Name, Path, Excluded At (formatted), Actions (Restore button)
     - Restore button: calls useRestoreCatalogEntry
     - Empty state: 'No excluded artifacts found'")

Task("ui-engineer-enhanced", "TASK-3.7: Add excluded status badge
     - Find status badge component/logic
     - Add case: status === 'excluded' → <Badge>Excluded</Badge>
     - Styling: className='border-gray-400 text-gray-600 bg-gray-100 dark:bg-gray-900'
     - Show in catalog card and excluded list table")
```

**Batch 3** (Sequential - Sonnet, depends on Batch 2):
```
Task("ui-engineer-enhanced", "TASK-3.5: Integrate excluded list into source page
     File: skillmeat/web/app/marketplace/sources/[id]/page.tsx
     - Add query: useMarketplaceCatalog with ?include_excluded=true for excluded list
     - Render ExcludedArtifactsList below catalog grid
     - Pass excluded entries filtered from query result
     - Default collapsed, show count in header")

Task("ui-engineer-enhanced", "TASK-3.6: Update Select All to skip excluded
     File: skillmeat/web/app/marketplace/sources/[id]/page.tsx (bulk import logic)
     - Filter: const importableEntries = entries.filter(e => e.status !== 'excluded')
     - Update Select All button: use importableEntries.length
     - Show excluded count separately if > 0: 'X excluded entries skipped'")

Task("ui-engineer", "TASK-3.8: E2E test for exclusion workflow
     File: skillmeat/web/tests/e2e/marketplace-exclusion.spec.ts
     - Setup: navigate to marketplace source detail page
     - Action 1: click 'Not an artifact' on first card → confirm
     - Assert 1: card disappears from grid
     - Action 2: open 'Show Excluded Artifacts' → click Restore
     - Assert 2: card reappears in grid
     - Assert 3: counts update correctly (excluded count decreases)")
```

---

## Phase 4: Polish & Testing (Week 3)

**Goal**: QA, documentation, performance tuning, and release preparation.

**Deliverables**:
- Bug fixes and refinements
- Performance audit results
- Accessibility audit
- Updated documentation
- Release notes

### Task Breakdown

| ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To |
|----|-----------|-------------|---------------------|----------|-------------|
| **TASK-4.1** | Performance audit | Measure and optimize critical paths | - Frontmatter parsing <50ms (10KB files)<br>- Tab click → filter <100ms<br>- Exclusion mutation <500ms<br>- No layout shift during mutations<br>- Lighthouse score >90 (Performance) | 1h | ui-engineer-enhanced |
| **TASK-4.2** | Accessibility audit | WCAG 2.1 AA compliance check | - Keyboard navigation: Tab, Enter, Escape<br>- Focus management: dialogs trap focus<br>- ARIA labels: buttons, tabs, collapsibles<br>- Screen reader: test with VoiceOver/NVDA<br>- Color contrast: 4.5:1 minimum | 1.5h | ui-engineer-enhanced |
| **TASK-4.3** | Cross-browser testing | Verify functionality in target browsers | - Chrome 120+: full functionality<br>- Firefox 120+: full functionality<br>- Safari 17+: full functionality<br>- Mobile Safari: responsive tabs, dialogs<br>- No console errors in any browser | 1h | ui-engineer |
| **TASK-4.4** | Bug fixes and refinements | Address issues found during QA | - Fix any bugs found in testing<br>- Refine animations and transitions<br>- Polish error messages<br>- Improve empty states | 2h | ui-engineer-enhanced |
| **TASK-4.5** | Update API documentation | Refresh OpenAPI spec and add examples | - OpenAPI spec auto-generated (FastAPI)<br>- Add examples for exclusion endpoints<br>- Update /api/v1/docs UI descriptions<br>- Add curl examples to docstrings | 0.5h | documentation-writer |
| **TASK-4.6** | Update user documentation | Add feature guide for exclusion workflow | - File: `docs/features/marketplace-exclusions.md`<br>- Screenshots: mark as excluded, excluded list<br>- Use cases: false positives, cleanup<br>- Note: exclusions are source-specific | 1h | documentation-writer |
| **TASK-4.7** | Create release notes | Document v0.4.0 changes for users | - File: `docs/releases/v0.4.0.md`<br>- Changelog: new features, improvements<br>- Breaking changes: none<br>- Migration notes: database auto-migrates<br>- Screenshots of new UI | 1h | documentation-writer |

**Quality Gates**:
- [ ] All unit tests pass (>80% coverage)
- [ ] All E2E tests pass (no flakiness)
- [ ] Performance targets met (see TASK-4.1)
- [ ] Accessibility: WCAG 2.1 AA compliant
- [ ] Cross-browser: no errors in Chrome/Firefox/Safari
- [ ] Documentation: complete and reviewed
- [ ] Release notes: approved by product team

**Orchestration Quick Reference**:

**Batch 1** (Parallel - Sonnet):
```
Task("ui-engineer-enhanced", "TASK-4.1: Performance audit
     - Measure: Chrome DevTools Performance tab
     - Frontmatter parsing: test with 10KB .md file, target <50ms
     - Tab click: record interaction, target <100ms to DOM update
     - Exclusion mutation: measure network + state update, target <500ms
     - Run Lighthouse: target Performance >90, Accessibility >95")

Task("ui-engineer-enhanced", "TASK-4.2: Accessibility audit
     - Keyboard nav: test all interactive elements (Tab, Enter, Escape)
     - Focus trap: dialogs (exclude dialog, excluded list)
     - ARIA: verify labels on tabs, buttons, collapsibles
     - Screen reader: test with VoiceOver (macOS) or NVDA (Windows)
     - Contrast: verify with Chrome DevTools Contrast Ratio tool")

Task("ui-engineer", "TASK-4.3: Cross-browser testing
     - Chrome 120+: test all features, check console
     - Firefox 120+: test all features, check console
     - Safari 17+: test all features, especially dialogs
     - Mobile Safari: test responsive tabs, touch interactions
     - Document any browser-specific issues or workarounds")
```

**Batch 2** (Sequential - depends on Batch 1):
```
Task("ui-engineer-enhanced", "TASK-4.4: Bug fixes and refinements
     - Review QA findings from TASK-4.1, 4.2, 4.3
     - Fix any bugs found during testing
     - Polish animations: smooth expand/collapse, fade-in excluded list
     - Improve error messages: user-friendly, actionable
     - Refine empty states: clear messaging, visual interest")
```

**Batch 3** (Parallel - Haiku, after Batch 2):
```
Task("documentation-writer", "TASK-4.5: Update API documentation
     - Verify OpenAPI spec includes new endpoints (auto-generated)
     - Add endpoint descriptions in docstrings
     - Example: PATCH /exclude with curl command
     - Update /api/v1/docs UI if needed")

Task("documentation-writer", "TASK-4.6: Update user documentation
     File: docs/features/marketplace-exclusions.md
     - Overview: what is artifact exclusion
     - Use case: false positives, cleanup
     - How to: mark as excluded, view excluded list, restore
     - Screenshots: catalog card link, excluded list, restore button
     - Note: exclusions are source-specific, not global")

Task("documentation-writer", "TASK-4.7: Create release notes
     File: docs/releases/v0.4.0.md
     - New features: frontmatter display, tabbed filter, exclusions
     - Improvements: browsing efficiency, data quality
     - Technical: database migration (auto), API endpoints
     - Screenshots: all three features
     - Breaking changes: none")
```

---

## Risk Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|------------|--------|---------------------|-------|
| **YAML parsing errors break modal** | Medium | High | Wrap parse in try/catch; show warning, hide frontmatter section on error. Test with malformed YAML. | ui-engineer |
| **Tab overflow on small screens** | Medium | Medium | Implement horizontal scroll with fade indicators. Test on 375px viewport (iPhone SE). | ui-engineer-enhanced |
| **Database migration conflict** | Low | High | Test migration on copy of prod DB before deploy. Use Alembic; verify rollback works. | data-layer-expert |
| **Excluded entries reappear after rescan** | Medium | Medium | Preserve `excluded_at` during rescan (TASK-2.7). Add unit test to verify. | python-backend-engineer |
| **Performance regression on large catalogs** | Low | Medium | Test with 500+ entries. Optimize query filters. Use pagination if needed. | python-backend-engineer |

### UX Risks

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|------------|--------|---------------------|-------|
| **Users accidentally exclude valid artifacts** | Medium | Medium | Clear confirmation dialog with artifact name. Easy Restore action in excluded list. | ui-engineer-enhanced |
| **Frontmatter clutters small files** | Low | Low | Default to expanded but collapsible. Test with real-world artifacts. | ui-engineer-enhanced |
| **Tab counts confuse users** | Low | Low | Use tooltips to explain counts (e.g., "12 skills detected in this source"). | ui-engineer-enhanced |
| **Excluded list hidden, users forget** | Medium | Low | Show excluded count in header: "Show Excluded Artifacts (3)". Prominent placement below grid. | ui-engineer-enhanced |

### Migration Risks

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|------------|--------|---------------------|-------|
| **Users prefer dropdown over tabs** | Low | Medium | A/B test for 1 week if possible. Keep dropdown code commented for easy rollback. | ui-engineer-enhanced |
| **Breaking change to API schema** | Low | High | Make `excluded` status optional; backward-compatible with existing clients. Versioned API. | python-backend-engineer |
| **Data loss during migration** | Very Low | Critical | Test migration on dev DB first. Backup prod DB before deploy. Verify downgrade works. | data-layer-expert |

---

## Testing Strategy

### Unit Tests

**Coverage Target**: >80%

| Component | Test File | Key Test Cases |
|-----------|-----------|----------------|
| Frontmatter utility | `__tests__/lib/frontmatter.test.ts` | Valid YAML parsing, invalid YAML handling, stripping logic |
| FrontmatterDisplay | `__tests__/components/entity/frontmatter-display.test.tsx` | Render key-value, collapse/expand, arrays, nested objects |
| CatalogTabs | `__tests__/app/marketplace/components/catalog-tabs.test.tsx` | Tab click, filter update, URL sync, counts display |
| Exclusion hooks | `__tests__/hooks/useMarketplaceSources.test.ts` | Mutation success, error handling, cache invalidation |
| ExcludeArtifactDialog | `__tests__/components/marketplace/exclude-artifact-dialog.test.tsx` | Open/close, confirm/cancel, entry display |
| Exclusion API | `tests/api/test_marketplace_exclusion.py` | Mark as excluded, restore, list filtering, rescan preservation |

### Integration Tests

**Test Database**: SQLite in-memory

| Scenario | Test Focus |
|----------|-----------|
| Exclusion workflow | Mark → verify DB update → restore → verify cleared |
| Catalog filtering | Default excludes excluded → ?include_excluded=true shows all |
| Rescan preservation | Scan detects new artifacts → excluded entries unchanged |
| Count accuracy | Counts_by_status includes 'excluded' count |

### E2E Tests

**Framework**: Playwright

| Test Spec | Scenarios |
|-----------|-----------|
| `marketplace-frontmatter.spec.ts` | Navigate to Contents tab → verify frontmatter display → toggle visibility |
| `marketplace-tabs.spec.ts` | Click tabs → verify filter updates → verify URL params → verify counts |
| `marketplace-exclusion.spec.ts` | Mark as excluded → verify disappears → open excluded list → restore → verify reappears |
| `marketplace-bulk-import.spec.ts` | Select All → verify excluded skipped → verify import count correct |

---

## Documentation Updates

### Files to Create/Update

| File | Type | Content |
|------|------|---------|
| `docs/features/marketplace-exclusions.md` | Feature Guide | How to mark, view, restore excluded artifacts |
| `docs/releases/v0.4.0.md` | Release Notes | Changelog, screenshots, migration notes |
| `docs/dev/architecture/marketplace-catalog.md` | Architecture Doc | Update with exclusion data model |
| `skillmeat/api/routers/marketplace_sources.py` | API Docstrings | Add examples for new endpoints |

### OpenAPI Spec Updates

**Automatic** (FastAPI introspection):
- New endpoint: `PATCH /marketplace/sources/{id}/artifacts/{entry_id}/exclude`
- New schema: `ExcludeEntryRequest`, `ExcludeEntryResponse`
- Updated schema: `CatalogEntryResponse` (status includes 'excluded')

**Manual** (optional):
- Add endpoint descriptions with use cases
- Add request/response examples in docstrings

---

## Deployment Plan

### Pre-Deployment Checklist

- [ ] All tests pass (unit, integration, E2E)
- [ ] Database migration tested on dev DB
- [ ] Backup production database
- [ ] API documentation updated
- [ ] Release notes reviewed and approved
- [ ] Feature flags configured (if using A/B testing for tabs)

### Deployment Steps

1. **Backend Deployment**:
   ```bash
   # Run Alembic migration
   cd skillmeat
   alembic upgrade head

   # Restart API server
   skillmeat web dev --api-only
   ```

2. **Frontend Deployment**:
   ```bash
   # Build Next.js app
   cd skillmeat/web
   pnpm build

   # Restart web server
   skillmeat web start
   ```

3. **Verification**:
   - Check `/api/v1/docs` for new endpoints
   - Test exclusion workflow on production
   - Verify frontmatter display with real artifacts
   - Test tabbed filtering with multiple sources

### Rollback Plan

**If critical issues found**:

1. **Backend Rollback**:
   ```bash
   # Revert migration
   alembic downgrade -1

   # Deploy previous API version
   git checkout <previous-tag>
   skillmeat web dev --api-only
   ```

2. **Frontend Rollback**:
   ```bash
   # Uncomment Select dropdown code (if commented)
   # Or deploy previous frontend version
   git checkout <previous-tag>
   pnpm build && skillmeat web start
   ```

3. **Data Recovery**:
   - If migration failed: restore from backup
   - If exclusions lost: re-exclude entries manually (user action)

---

## Success Metrics

### Performance Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Clicks to filter by type | 2 | 1 | User interaction recording |
| Frontmatter parsing time | N/A | <50ms | Chrome DevTools Performance |
| Tab click latency | N/A | <100ms | React Profiler |
| Exclusion mutation latency | N/A | <500ms | Network tab + state update |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Unit test coverage | >80% | Jest coverage report |
| E2E test pass rate | 100% | Playwright CI results |
| Accessibility score | >95 | Lighthouse audit |
| Performance score | >90 | Lighthouse audit |
| Bug count (post-release) | <5 (P1-P2) | Issue tracker |

### User Metrics (Post-Release)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Frontmatter usage | >50% of modal opens | Analytics event tracking |
| Exclusion feature adoption | >10 exclusions/week | Database query |
| Tab click vs dropdown click | >80% tabs | A/B test comparison (if enabled) |
| False positive reduction | 30% fewer imports of non-artifacts | Manual catalog review |

---

## Dependencies

### Technical Dependencies

| Dependency | Version | Purpose | Status |
|------------|---------|---------|--------|
| Radix Tabs | Latest | Tabbed filter UI | ✅ In use (EntityTabs) |
| Radix Collapsible | Latest | Frontmatter toggle | ✅ Available in shadcn |
| Radix Dialog | Latest | Exclusion confirmation | ✅ In use |
| js-yaml | ^4.1.0 | YAML parsing | ⚠️ Add to package.json |
| TanStack Query | v5 | Exclusion mutations | ✅ In use |
| Alembic | Latest | Database migrations | ✅ In use |
| SQLAlchemy | 2.0+ | ORM models | ✅ In use |

### Data Dependencies

| Dependency | Source | Required For | Availability |
|------------|--------|--------------|--------------|
| countsByType | Backend API | Tab counts | ✅ `catalogData.pages[0].counts_by_type` |
| Frontmatter YAML | File content | Parsing | ✅ Via `useCatalogFileContent` hook |
| Catalog status enum | Backend schema | Exclusion status | ⚠️ Needs `excluded` value added |
| excluded_at, excluded_reason | Database | Exclusion tracking | ⚠️ Needs migration |

### Cross-Feature Dependencies

| Feature | Depends On | Reason |
|---------|-----------|--------|
| Feature 2 (Tabs) | Feature 1 (Frontmatter) | None - independent |
| Feature 3 (Exclusions) | Phase 2 Backend | UI needs API endpoints |
| Phase 4 (Polish) | Phases 1-3 | QA and documentation |

---

## Appendices

### Appendix A: File Reference Map

**Frontend Files Modified**:
- `skillmeat/web/lib/frontmatter.ts` (new)
- `skillmeat/web/components/entity/frontmatter-display.tsx` (new)
- `skillmeat/web/components/entity/content-pane.tsx` (modify)
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-tabs.tsx` (new)
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` (modify lines 509-530)
- `skillmeat/web/components/marketplace/exclude-artifact-dialog.tsx` (new)
- `skillmeat/web/app/marketplace/sources/[id]/components/excluded-list.tsx` (new)
- `skillmeat/web/hooks/useMarketplaceSources.ts` (add mutations)
- `skillmeat/web/types/marketplace.ts` (add 'excluded' to enum)

**Backend Files Modified**:
- `skillmeat/cache/models.py` (MarketplaceCatalogEntry model)
- `skillmeat/api/schemas/marketplace.py` (add ExcludeEntryRequest/Response)
- `skillmeat/api/routers/marketplace_sources.py` (add PATCH endpoint, update GET)
- `skillmeat/api/migrations/versions/YYYYMMDD_HHMM_add_exclusion_to_catalog.py` (new)
- `skillmeat/marketplace/scanner.py` (preserve exclusions during rescan)

**Test Files Created**:
- `skillmeat/web/__tests__/lib/frontmatter.test.ts`
- `skillmeat/web/__tests__/components/entity/frontmatter-display.test.tsx`
- `skillmeat/web/__tests__/app/marketplace/components/catalog-tabs.test.tsx`
- `skillmeat/web/__tests__/hooks/useMarketplaceSources.test.ts`
- `skillmeat/web/__tests__/components/marketplace/exclude-artifact-dialog.test.tsx`
- `skillmeat/web/tests/e2e/marketplace-frontmatter.spec.ts`
- `skillmeat/web/tests/e2e/marketplace-tabs.spec.ts`
- `skillmeat/web/tests/e2e/marketplace-exclusion.spec.ts`
- `skillmeat/api/tests/test_marketplace_exclusion.py`

**Documentation Files**:
- `docs/features/marketplace-exclusions.md` (new)
- `docs/releases/v0.4.0.md` (new)
- `docs/dev/architecture/marketplace-catalog.md` (update)

### Appendix B: Design Specifications

**Frontmatter Display Component**:

```tsx
// Visual structure
┌─────────────────────────────────────────────────┐
│ Frontmatter                            ▼ Hide   │ ← Collapsible header
│ ┌───────────────────────────────────────────┐   │
│ │ title: My Awesome Skill               │   │ ← Bold key, plain value
│ │ version: 1.2.0                        │   │
│ │ tags: code-gen, refactoring           │   │ ← Arrays as comma-separated
│ │ description: Refactors code snippets  │   │
│ └───────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘

// Tailwind classes
bg-muted/30          // Light gray background
border border-border // Default border
max-h-[300px]        // Max height with scroll
overflow-y-auto      // Scroll if needed
```

**Tabbed Filter UI**:

```tsx
// Visual structure
┌─────────────────────────────────────────────────────────────────┐
│ [All Types (45)] [Skills (12)] [Agents (8)] [Commands (3)] ... │
│ ════════                                                        │ ← Active tab underline
└─────────────────────────────────────────────────────────────────┘

// Active tab styling
data-[state=active]:border-b-2 data-[state=active]:border-primary
data-[state=active]:text-primary

// Count badge
text-muted-foreground (inactive) | text-primary (active)
```

**Excluded Artifacts List**:

```tsx
// Visual structure
┌─────────────────────────────────────────────────┐
│ ▼ Show Excluded Artifacts (3)                   │ ← Collapsible header
│ ┌───────────────────────────────────────────┐   │
│ │ Name          │ Path      │ Excluded  │   │
│ │───────────────┼───────────┼──────────│   │
│ │ fake-skill    │ docs/...  │ 2d ago  │   │
│ │ [Restore]     │           │         │   │ ← Button in Actions column
│ └───────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘

// Table component: shadcn Table primitive
// Restore button: variant="outline", size="sm"
```

### Appendix C: API Endpoint Specifications

**PATCH `/marketplace/sources/{source_id}/artifacts/{entry_id}/exclude`**

```python
# Request
{
  "excluded": true,
  "reason": "Not a valid artifact - documentation file"  # optional
}

# Response (200 OK)
{
  "id": "abc123",
  "source_id": "def456",
  "artifact_type": "skill",
  "name": "fake-skill",
  "path": "docs/nested/fake-skill",
  "status": "excluded",  # ← Updated
  "excluded_at": "2025-12-31T12:00:00Z",  # ← New field
  "excluded_reason": "Not a valid artifact - documentation file",  # ← New field
  ...
}

# Errors
404 - Entry not found
422 - Validation error (e.g., reason too long)
500 - Internal server error
```

**GET `/marketplace/sources/{source_id}/artifacts?include_excluded=true`**

```python
# Query params
include_excluded: bool = False  # Default: hide excluded

# Response (default, excluded hidden)
{
  "items": [...],  # No entries with status='excluded'
  "page_info": {...},
  "counts_by_status": {
    "new": 12,
    "updated": 3,
    "removed": 1,
    "imported": 5,
    "excluded": 2  # ← Included in counts even if hidden
  }
}

# Response (include_excluded=true)
{
  "items": [...],  # Includes entries with status='excluded'
  "page_info": {...},
  "counts_by_status": {...}
}
```

### Appendix D: Database Schema

**Migration: Add Exclusion Columns**

```python
# File: skillmeat/api/migrations/versions/YYYYMMDD_HHMM_add_exclusion_to_catalog.py

def upgrade():
    op.add_column('marketplace_catalog_entries',
        sa.Column('excluded_at', sa.DateTime(), nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('excluded_reason', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('marketplace_catalog_entries', 'excluded_reason')
    op.drop_column('marketplace_catalog_entries', 'excluded_at')
```

**SQLAlchemy Model Update**

```python
# File: skillmeat/cache/models.py (MarketplaceCatalogEntry)

class MarketplaceCatalogEntry(Base):
    __tablename__ = "marketplace_catalog_entries"

    # ... existing fields ...

    # Exclusion fields (Feature 3)
    excluded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        doc="Timestamp when entry was marked as 'not an artifact'"
    )
    excluded_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        doc="User-provided reason for exclusion (optional)"
    )
```

---

**End of Implementation Plan**
