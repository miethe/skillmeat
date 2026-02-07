---
title: 'Implementation Plan: Marketplace GitHub Sources CRUD Enhancement'
description: Edit/Delete functionality and Description/Notes fields for GitHub Sources
  in SkillMeat
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- phases
- tasks
- web-ui
- marketplace
- crud
created: 2025-12-12
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/marketplace-github-ingestion-v1.md
---

# Implementation Plan: Marketplace GitHub Sources CRUD Enhancement

**Plan ID**: `IMPL-2025-12-12-MARKETPLACE-SOURCES-CRUD`
**Date**: 2025-12-12
**Author**: Claude Code (lead-architect)
**Related Documents**:
- **Feature**: Marketplace GitHub Ingestion v1 (completed, foundational work)

**Complexity**: Medium
**Total Estimated Effort**: 48 story points
**Target Timeline**: 2 weeks

## Executive Summary

This implementation plan enhances the completed Marketplace GitHub Ingestion feature with full CRUD capabilities and metadata support. Users will be able to Edit and Delete GitHub Sources directly from the UI with confirmation dialogs, and sources will support Description and Notes fields for better organization. The implementation follows the MeatyPrompts layered architecture: Schema → Repository → Service → API → UI, with special attention to maintaining consistency between frontend and backend representations.

**Key Deliverables**:
1. Database and backend schema updates (description, notes fields)
2. API endpoints enhanced to support PATCH/DELETE with new fields
3. TypeScript types reflecting backend schema
4. Edit modal component reusing AddSourceModal pattern
5. Delete confirmation dialog with consequences warning
6. Hover buttons on source cards and detail pages
7. Notes display section on source detail page with scrollable artifacts pane
8. Full test coverage and documentation

---

## Implementation Strategy

### Architecture Sequence

Following the MeatyPrompts layered pattern, work proceeds bottom-up:

1. **Database/Schema Layer** - Add description, notes fields to MarketplaceSource model
2. **Repository Layer** - Ensure PATCH/DELETE operations persist new fields
3. **API Layer** - Update request/response schemas, verify endpoints handle new fields
4. **Frontend Types** - Extend TypeScript interfaces to match API contracts
5. **UI Components** - Build modal, dialog, buttons, notes section
6. **Integration** - Wire components together on pages
7. **Testing** - Unit, integration, E2E tests + accessibility
8. **Documentation** - API docs, component docs, usage guides

### Parallel Work Opportunities

- **Phase 1** (Database/API) and **Phase 3** (Frontend Types) can start in parallel
- **Phase 2** (Frontend Component Development) can begin once types are defined
- **Phase 4** (Testing) can start incrementally as each phase completes

### Critical Path

1. Database Schema → 2. API Schemas/Endpoints → 3. Frontend Types → 4. UI Components → 5. Testing

---

## Phase Breakdown

### Phase 1: Database & Backend Schema

**Duration**: 1-2 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| SCHEMA-001 | Add description/notes to MarketplaceSource Model | Add `description: Optional[str]` and `notes: Optional[str]` fields to SQLAlchemy model | Model updated, nullable columns, Alembic migration created | 3 pts | data-layer-expert | None |
| SCHEMA-002 | Create Alembic Migration | Generate and validate migration script | Migration applies cleanly, tested on fresh DB | 2 pts | data-layer-expert | SCHEMA-001 |
| SCHEMA-003 | Update SourceResponse Schema | Add description and notes fields to Pydantic response model | Schema reflects new fields with proper documentation | 2 pts | python-backend-engineer | SCHEMA-001 |
| SCHEMA-004 | Update CreateSourceRequest Schema | Add optional description and notes fields | Validation includes max length constraints | 2 pts | python-backend-engineer | SCHEMA-001 |
| SCHEMA-005 | Create UpdateSourceRequest DTO | New DTO for PATCH endpoint with all editable fields | Includes description, notes, ref, root_hint, trust_level | 2 pts | python-backend-engineer | SCHEMA-001 |

**Phase 1 Quality Gates:**
- [ ] Migration creates description and notes columns
- [ ] Model fields are nullable and optional in response
- [ ] Pydantic schemas validate field lengths (e.g., description max 500 chars, notes max 2000 chars)
- [ ] OpenAPI spec updated with new fields
- [ ] No breaking changes to existing API contracts

---

### Phase 2: Backend API Enhancement

**Duration**: 2-3 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| API-001 | Enhance POST /marketplace/sources | Accept description and notes in request body | New fields stored and returned in response | 2 pts | python-backend-engineer | SCHEMA-005 |
| API-002 | Enhance PATCH /marketplace/sources/{id} | Accept description and notes as patchable fields | Can update any combination of fields independently | 3 pts | python-backend-engineer | SCHEMA-005 |
| API-003 | Verify DELETE /marketplace/sources/{id} | Ensure DELETE operation exists and works | Returns 204 on success, 404 if not found | 1 pt | python-backend-engineer | SCHEMA-003 |
| API-004 | Add Field Validation | Validate description (max 500 chars) and notes (max 2000 chars) | Invalid lengths return 422 with validation error | 2 pts | python-backend-engineer | SCHEMA-005 |
| API-005 | Test PATCH/DELETE Integration | Test endpoints with repository/transaction handlers | Catalog entries correctly deleted when source deleted | 2 pts | python-backend-engineer | API-002, API-003 |
| API-006 | Regenerate TypeScript SDK | Generate SDK from updated OpenAPI spec | SDK includes new fields and endpoints | 1 pt | python-backend-engineer | API-002 |

**Phase 2 Quality Gates:**
- [ ] POST endpoint accepts and persists description/notes
- [ ] PATCH endpoint updates fields without affecting others
- [ ] DELETE endpoint cascades to catalog entries
- [ ] Validation errors return proper ErrorResponse envelopes
- [ ] OpenAPI spec reflects all changes
- [ ] SDK regenerates without errors
- [ ] All responses include new fields (or null if not set)

---

### Phase 3: Frontend Type Updates

**Duration**: 1 day
**Dependencies**: Phase 2 complete (SDK regenerated)
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TYPES-001 | Extend GitHubSource Type | Add description and notes as optional fields | Type matches API response contract | 1 pt | ui-engineer-enhanced | API-006 |
| TYPES-002 | Extend CreateSourceRequest Type | Add optional description and notes | Type matches API request contract | 1 pt | ui-engineer-enhanced | API-006 |
| TYPES-003 | Create UpdateSourceRequest Type | New type for PATCH operations | Includes all patchable fields with optional status | 1 pt | ui-engineer-enhanced | API-006 |
| TYPES-004 | Update useMarketplaceSources Hook | Add mutation hooks for PATCH and DELETE | usePatchSource and useDeleteSource available | 2 pts | ui-engineer-enhanced | TYPES-003 |

**Phase 3 Quality Gates:**
- [ ] All types match backend schemas
- [ ] TypeScript strict mode passes
- [ ] Generated SDK types align with hand-written types (or use generated where possible)
- [ ] useMarketplaceSources hook has complete CRUD methods

---

### Phase 4: UI Components Development

**Duration**: 4-5 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UI-001 | Create DeleteConfirmationDialog | Dialog showing source name, artifact count, and delete confirmation | Warns about consequences, shows artifacts count, has Cancel/Delete buttons | 3 pts | ui-engineer-enhanced | TYPES-004 |
| UI-002 | Update AddSourceModal → EditSourceModal | Extend AddSourceModal to support edit mode with pre-populated fields | Detects edit mode, pre-fills all fields, auto-triggers rescan on save | 4 pts | ui-engineer-enhanced | TYPES-004 |
| UI-003 | Add Hover Buttons to SourceCard | Add Edit/Delete buttons visible on hover | Buttons appear smoothly, positioned in top-right corner | 3 pts | ui-engineer-enhanced | UI-002 |
| UI-004 | Add Action Buttons to Detail Page | Add Edit/Delete buttons below "Rescan" and "View Repo" in detail page header | Same style as card buttons, consistent placement | 3 pts | ui-engineer-enhanced | UI-002 |
| UI-005 | Create Notes Section Component | Display notes below artifacts catalog pane on detail page | Shows notes if present, empty state if blank, read-only display | 2 pts | ui-engineer-enhanced | TYPES-001 |
| UI-006 | Create Description Display Component | Show description on source card and detail page | Card shows first 100 chars, detail shows full text, below repo name | 2 pts | ui-engineer-enhanced | TYPES-001 |
| UI-007 | Make Artifacts Pane Scrollable | Ensure artifacts catalog section scrolls independently | Fixed header, scrollable content, doesn't affect notes section | 2 pts | ui-engineer-enhanced | UI-005 |
| UI-008 | Wire Delete Dialog to SourceCard | Connect delete button to confirmation dialog and API call | Dialog shows, delete executes, list updates | 2 pts | ui-engineer-enhanced | UI-001, UI-003 |
| UI-009 | Wire Edit Modal to SourceCard | Connect edit button to modal and API call | Modal shows, form pre-fills, save updates and refreshes data | 2 pts | ui-engineer-enhanced | UI-002, UI-003 |
| UI-010 | Update Detail Page Wiring | Connect all buttons and sections on source detail page | All actions work end-to-end, data updates correctly | 3 pts | ui-engineer-enhanced | UI-004, UI-005, UI-006 |

**Phase 4 Quality Gates:**
- [ ] Delete dialog warns about cascading deletions
- [ ] Edit modal pre-populates all fields correctly
- [ ] Rescan auto-triggers after successful edit
- [ ] Hover buttons appear/disappear smoothly
- [ ] Description displays truncated on card, full on detail
- [ ] Notes section shows below scrollable artifacts pane
- [ ] All buttons have proper loading and error states
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] Responsive on mobile (buttons accessible without hover)

---

### Phase 5: Testing & Quality Assurance

**Duration**: 2-3 days
**Dependencies**: Phase 4 complete
**Assigned Subagent(s)**: documentation-writer (test cases), ui-engineer-enhanced (E2E)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-001 | Unit Tests - Backend Schemas | Test validation, serialization, migration | >90% coverage, all edge cases | 3 pts | documentation-writer | SCHEMA-001 |
| TEST-002 | Unit Tests - API Endpoints | Test PATCH, DELETE with various field combinations | All happy paths and error cases covered | 4 pts | documentation-writer | API-002 |
| TEST-003 | Unit Tests - Frontend Components | Test EditSourceModal, DeleteDialog, buttons | Component rendering, event handlers, state management | 4 pts | documentation-writer | UI-010 |
| TEST-004 | Integration Tests - Edit Flow | Test PATCH endpoint with database, verify persistence | Data saved correctly, side effects correct | 2 pts | documentation-writer | API-002 |
| TEST-005 | Integration Tests - Delete Flow | Test DELETE endpoint cascading, catalog cleanup | Source and catalog entries deleted atomically | 2 pts | documentation-writer | API-003 |
| TEST-006 | E2E Tests - Edit Source | User flow: opens source, clicks edit, changes fields, saves | Verify UI updates, API calls correct, list refreshes | 3 pts | ui-engineer-enhanced | UI-010 |
| TEST-007 | E2E Tests - Delete Source | User flow: opens source, clicks delete, confirms, source removed | Dialog shows correctly, delete succeeds, list updates | 3 pts | ui-engineer-enhanced | UI-008 |
| TEST-008 | Accessibility Testing | Keyboard nav, screen reader, color contrast | All interactive elements keyboard-accessible | 2 pts | ui-engineer-enhanced | UI-010 |
| TEST-009 | Visual Regression Testing | Hover states, dialog appearance, responsive layouts | Screenshots match expected designs | 2 pts | ui-engineer-enhanced | UI-010 |

**Phase 5 Quality Gates:**
- [ ] Unit test coverage >85% for modified code
- [ ] All E2E user flows pass without manual intervention
- [ ] No accessibility violations (WCAG 2.1 AA)
- [ ] Delete dialog cascade verified in tests
- [ ] Edit flow with auto-rescan verified
- [ ] Responsive design tested on mobile, tablet, desktop

---

### Phase 6: Documentation & Deployment

**Duration**: 1 day
**Dependencies**: Phase 5 complete
**Assigned Subagent(s)**: documentation-writer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DOCS-001 | API Documentation | Update OpenAPI docs with new fields and behaviors | Clear field descriptions, examples, error cases documented | 2 pts | documentation-writer | API-006 |
| DOCS-002 | Component Documentation | Document EditSourceModal, DeleteDialog, UI components | Usage examples, props, accessibility notes | 2 pts | documentation-writer | UI-010 |
| DOCS-003 | User Guide Update | Add CRUD instructions to user documentation | Screenshots, step-by-step workflows for edit/delete | 1 pt | documentation-writer | UI-010 |
| DOCS-004 | Release Notes | Document new features and changes | Highlights: Edit/Delete, Description/Notes, auto-rescan on edit | 1 pt | documentation-writer | DOCS-001 |

**Phase 6 Quality Gates:**
- [ ] All API endpoints documented with examples
- [ ] Component props and patterns documented
- [ ] User guide includes screenshots
- [ ] Release notes ready for publication

---

## Task Priority & Sequencing

### Critical Path

```
Phase 1: Database Schema (3-4 days)
    ↓
Phase 2: API Enhancement (2-3 days)
    ↓
Phase 3: Frontend Types (1 day, can overlap with Phase 2)
    ↓
Phase 4: UI Components (4-5 days)
    ↓
Phase 5: Testing (2-3 days)
    ↓
Phase 6: Documentation (1 day)
```

### Parallelizable Tasks

- Phase 1 and early Phase 3 (types skeleton) can start together
- Phase 2 API and Phase 3 types refinement can overlap
- Phase 4 components can begin once Phase 3 types are firm
- Phase 5 unit tests can start during Phase 4 component development
- Phase 5 E2E tests should wait for Phase 4 completion

---

## Component Architecture

### EditSourceModal Component

**Location**: `skillmeat/web/components/marketplace/edit-source-modal.tsx`

```typescript
interface EditSourceModalProps {
  source: GitHubSource;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

// Extends AddSourceModal with:
// - Pre-populated fields from source
// - Edit mode detection (different title/description)
// - Auto-trigger rescan on save
// - Loading state during API call
```

### DeleteConfirmationDialog Component

**Location**: `skillmeat/web/components/marketplace/delete-source-dialog.tsx`

```typescript
interface DeleteConfirmationDialogProps {
  source: GitHubSource;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm?: () => void;
}

// Features:
// - Shows source name and repo URL
// - Warning about cascading deletion of catalog entries
// - Shows artifact count from source
// - Cancel/Delete button pair
// - Loading state during deletion
// - Error handling and display
```

### SourceCard Updates

**Location**: `skillmeat/web/components/marketplace/source-card.tsx`

```typescript
// Add to existing SourceCard:
// - Hover detection via group-hover
// - Edit/Delete buttons in top-right corner (hidden until hover)
// - Buttons stop propagation to prevent card click
// - Show description if present (first 100 chars)
```

### Source Detail Page Updates

**Location**: `skillmeat/web/app/marketplace/sources/[id]/page.tsx`

```typescript
// Add to existing detail page:
// - Edit/Delete buttons in header area (below Rescan, View Repo)
// - Description display below repo name
// - Notes section below artifacts pane
// - Make artifacts pane scrollable (fixed height, scroll internally)
```

---

## Backend Database Changes

### MarketplaceSource Model Extension

```python
# In skillmeat/cache/models.py or similar

class MarketplaceSource(Base):
    # ... existing fields ...

    description: str | None = Column(
        String(500),
        nullable=True,
        comment="User-provided description of the source",
    )
    notes: str | None = Column(
        String(2000),
        nullable=True,
        comment="Internal notes/documentation for this source",
    )
```

### Migration Strategy

- Use Alembic to generate migration
- Test on fresh database
- Ensure backwards compatibility (nullable fields)
- No data loss for existing sources

---

## API Contract Changes

### Create Source Request
```json
{
  "repo_url": "https://github.com/...",
  "ref": "main",
  "root_hint": "skills",
  "trust_level": "basic",
  "description": "Optional short description",
  "notes": "Optional internal notes"
}
```

### Update Source Request (PATCH)
```json
{
  "ref": "main",
  "root_hint": "skills",
  "trust_level": "basic",
  "description": "Updated description",
  "notes": "Updated notes"
}
```

### Source Response
```json
{
  "id": "src_abc123",
  "repo_url": "https://github.com/...",
  "owner": "anthropics",
  "repo_name": "anthropic-quickstarts",
  "ref": "main",
  "root_hint": "skills",
  "trust_level": "basic",
  "visibility": "public",
  "scan_status": "success",
  "artifact_count": 12,
  "last_sync_at": "2025-12-06T10:30:00Z",
  "last_error": null,
  "created_at": "2025-12-05T09:00:00Z",
  "updated_at": "2025-12-06T10:30:00Z",
  "description": "Optional short description",
  "notes": "Optional internal notes"
}
```

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Database migration fails | Medium | Test migration in staging environment first, rollback plan ready |
| Breaking API changes | Medium | Maintain backwards compatibility, version fields as optional |
| Cascade delete removes wrong data | High | Write comprehensive tests for cascade behavior, verify in staging |
| Edit modal field mismatch | Low | Share types between frontend and backend, generate SDK |
| Performance impact from larger schema | Low | Add indexes if needed, monitor query times |
| Accessibility issues with hover buttons | Medium | Test with keyboard and screen readers, provide keyboard fallback |

---

## Success Criteria

1. Users can Edit sources: Change ref, root_hint, trust_level, description, notes
2. Users can Delete sources with confirmation dialog warning about cascade
3. Edit triggers automatic rescan of the source
4. Description displays on source card (truncated) and detail page (full)
5. Notes display on detail page below scrollable artifacts pane
6. All E2E workflows pass without manual intervention
7. Mobile/tablet responsive design works without hover (buttons accessible)
8. Zero accessibility violations (WCAG 2.1 AA)
9. All tests pass with >85% code coverage
10. Documentation complete and up-to-date

---

## Effort Estimates

| Phase | Duration | Story Points | Team Size |
|-------|----------|--------------|-----------|
| Phase 1: Database/Schema | 1-2 days | 11 | 2 engineers |
| Phase 2: Backend API | 2-3 days | 11 | 1 engineer |
| Phase 3: Frontend Types | 1 day | 5 | 1 engineer |
| Phase 4: UI Components | 4-5 days | 28 | 1 engineer |
| Phase 5: Testing | 2-3 days | 25 | 2 engineers |
| Phase 6: Documentation | 1 day | 6 | 1 engineer |
| **Total** | **2 weeks** | **86 pts** | **Avg 1-2 per phase** |

---

## Dependencies & External Factors

- **Backend**: Database connection and Alembic setup functioning
- **Frontend**: useMarketplaceSources hook available and working
- **API**: Existing PATCH/DELETE endpoints operational
- **Testing**: Test database and E2E test framework setup
- **Deployment**: Staging and production environments available

---

## Sign-Off

This implementation plan is ready for execution once approved. All phases are scoped, dependencies identified, and acceptance criteria defined. Team assignments and story points provide clear guidance for project scheduling.

**Prepared by**: Claude Code (Implementation Planner)
**Date**: 2025-12-12
**Status**: Ready for Development
