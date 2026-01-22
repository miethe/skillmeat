# Global Fields Management Implementation Plan - Detailed Phase Breakdowns

This directory contains detailed technical implementation guides for each phase of the Global Fields Management feature.

## Plan Structure

```
global-fields-management-v1/
├── phase-1-backend-infrastructure.md  (25 pts, 5 days) - Database → Service → API
├── phase-2-frontend-core.md            (31 pts, 5 days) - Pages, Components, Hooks
├── phase-3-tags-crud.md               (21 pts, 5 days) - Full CRUD workflow
├── phase-4-marketplace-fields.md      (17 pts, 4 days) - Marketplace tab, read-only fields
├── phase-5-polish-testing.md          (22 pts, 4 days) - Accessibility, performance, tests
├── phase-6-documentation.md           (8 pts, 2 days) - API docs, user guide, ADR
└── README.md (this file)
```

## Quick Reference

### Phase 1: Backend Infrastructure (5 days)

**Lead**: `python-backend-engineer`

**Deliverables**:
- Field Registry system (`skillmeat/core/registry/field_registry.py`)
- FieldsService wrapper (`skillmeat/core/services/fields_service.py`)
- API schemas (`skillmeat/api/schemas/fields.py`)
- Fields router (`skillmeat/api/routers/fields.py`)
- Unit tests (>80% coverage)

**Key Tasks**:
- GFM-IMPL-1.1: Field Registry
- GFM-IMPL-1.2: FieldsService
- GFM-IMPL-1.3: Schemas
- GFM-IMPL-1.4: Router
- GFM-IMPL-1.5: Error Handling
- GFM-IMPL-1.6: Unit Tests

**Dependencies**: None (independent)

**Related**: `.claude/CLAUDE.md` → "MeatyPrompts Architecture", "Tag Service"

---

### Phase 2: Frontend Core (5 days)

**Lead**: `ui-engineer-enhanced`

**Deliverables**:
- Settings fields page (`skillmeat/web/app/settings/fields/page.tsx`)
- FieldsClient layout component
- Form dialogs (Add, Edit, Remove)
- TanStack Query hooks
- API client functions

**Key Tasks**:
- GFM-IMPL-2.1: Settings page
- GFM-IMPL-2.2: FieldsClient layout
- GFM-IMPL-2.3: FieldOptionsList
- GFM-IMPL-2.4: AddOptionDialog
- GFM-IMPL-2.5: EditOptionDialog
- GFM-IMPL-2.6: RemoveConfirmDialog
- GFM-IMPL-2.7: TanStack Query hooks
- GFM-IMPL-2.8: Error handling & UX

**Dependencies**: None (independent, but Phase 1 APIs needed for Phase 3 integration)

**Related**: `.claude/CLAUDE.md` → "Component Rules", "Page Rules", "Testing Rules"

---

### Phase 3: Tags CRUD Implementation (5 days)

**Lead**: `ui-engineer-enhanced` + `python-backend-engineer`

**Deliverables**:
- Complete tag CRUD workflow
- Cascade delete implementation
- Integration tests
- E2E tests

**Key Tasks**:
- GFM-IMPL-3.1: Wire AddOptionDialog
- GFM-IMPL-3.2: Wire EditOptionDialog
- GFM-IMPL-3.3: Wire RemoveConfirmDialog
- GFM-IMPL-3.4: Cascade delete service
- GFM-IMPL-3.5: Tag normalization validation
- GFM-IMPL-3.6: Integration tests
- GFM-IMPL-3.7: E2E tests

**Dependencies**: Phase 1 + Phase 2 complete

**Related**: `skillmeat/core/services/tag_service.py` (existing TagService)

---

### Phase 4: Marketplace Source Fields (4 days)

**Lead**: Backend + Frontend (parallel)

**Deliverables**:
- Marketplace Sources tab
- Read-only field display
- Marketplace tag CRUD
- Field descriptions/help text

**Key Tasks**:
- GFM-IMPL-4.1: Marketplace tab
- GFM-IMPL-4.2: Marketplace tags CRUD
- GFM-IMPL-4.3-4.5: Read-only fields (Trust Level, Visibility, Auto Tags)
- GFM-IMPL-4.6: Help text/descriptions
- GFM-IMPL-4.7: Integration tests

**Dependencies**: Phase 2 UI structure, Phase 1 API extensible

---

### Phase 5: Polish, Testing & Accessibility (4 days)

**Lead**: Both teams

**Deliverables**:
- WCAG 2.1 AA compliance
- Performance optimization
- Comprehensive test coverage
- Feature flags
- Cursor pagination

**Key Tasks**:
- GFM-IMPL-5.1: Accessibility audit
- GFM-IMPL-5.2: Cursor pagination
- GFM-IMPL-5.3: Performance optimization
- GFM-IMPL-5.4: Mobile responsiveness
- GFM-IMPL-5.5: Error logging & monitoring
- GFM-IMPL-5.6: Feature flags
- GFM-IMPL-5.7: Browser testing
- GFM-IMPL-5.8: Unit test coverage

**Dependencies**: Phases 3-4 complete

---

### Phase 6: Documentation & Deployment (2 days)

**Lead**: `documentation-writer`

**Deliverables**:
- API documentation (OpenAPI/Swagger)
- Component README
- User guide
- Deployment notes
- Architecture Decision Record

**Key Tasks**:
- GFM-IMPL-6.1: API documentation
- GFM-IMPL-6.2: Component README
- GFM-IMPL-6.3: User guide
- GFM-IMPL-6.4: Deployment notes
- GFM-IMPL-6.5: ADR

**Dependencies**: Phases 1-5 complete

---

## Implementation Workflow

### Week 1: Phases 1 & 2 (Parallel)

```
Backend Team                    Frontend Team
├─ Phase 1 Start                ├─ Phase 2 Start
│  ├─ Task 1.1: Registry        │  ├─ Task 2.1: Settings page
│  ├─ Task 1.2: Service         │  ├─ Task 2.2: FieldsClient
│  ├─ Task 1.3: Schemas         │  ├─ Task 2.3-2.6: Dialogs
│  ├─ Task 1.4: Router          │  ├─ Task 2.7: Hooks
│  ├─ Task 1.5-1.6: Tests/Errors│  └─ Task 2.8: Error handling
│  └─ Phase 1 Complete          └─ Phase 2 Complete
```

**Milestone**: Phase 1 API ready for integration

### Week 2: Phase 3 (Both teams)

```
├─ Task 3.1-3.3: UI integration
├─ Task 3.4: Cascade delete
├─ Task 3.5-3.7: Validation & tests
└─ Phase 3 Complete (Full tag CRUD working end-to-end)
```

**Milestone**: Tag management fully functional

### Week 3: Phase 4 (Parallel) + Phase 5 Start

```
Backend                         Frontend
├─ Task 4.2: Marketplace tags   ├─ Task 4.1: Marketplace tab
├─ Marketplace API complete     ├─ Task 4.3-4.6: Fields/help
└─ Phase 4 Complete             └─ Phase 5 Start (Accessibility, Perf)
```

### Week 4: Phase 5 Complete

```
├─ Task 5.1-5.8: Polish
├─ Accessibility verified
├─ Performance tested
└─ Phase 5 Complete
```

### Week 5: Phase 6

```
├─ Task 6.1: API docs
├─ Task 6.2-6.5: User docs & ADR
└─ Phase 6 Complete (Ready for production)
```

---

## File References

### Configuration & Registry

- `skillmeat/core/registry/field_registry.py` - Field definitions (Phase 1)
  - ObjectType enum (Artifacts, Marketplace Sources)
  - FieldType enum (Tag, Enum, String)
  - FieldMetadata dataclass
  - FieldRegistry class with lookup methods

### Services & Business Logic

- `skillmeat/core/services/fields_service.py` - Field operations (Phase 1)
  - FieldsService class wrapping TagService
  - CRUD methods: list, create, update, delete
  - Validation methods

- `skillmeat/core/services/tag_service.py` - Existing tag service (reuse)
  - TagService._slugify() for normalization
  - TagService.delete_tag() for cascade delete

### API Layer

- `skillmeat/api/routers/fields.py` - HTTP endpoints (Phase 1)
  - GET /api/v1/fields - List options
  - POST /api/v1/fields/options - Create
  - PUT /api/v1/fields/options/{id} - Update
  - DELETE /api/v1/fields/options/{id} - Delete

- `skillmeat/api/schemas/fields.py` - Request/response DTOs (Phase 1)
  - FieldOptionResponse
  - FieldListResponse
  - CreateFieldOptionRequest
  - UpdateFieldOptionRequest

### Frontend Pages & Components

- `skillmeat/web/app/settings/fields/page.tsx` - Settings page (Phase 2)
  - Server component with metadata
  - Renders FieldsClient

- `skillmeat/web/components/settings/fields-client.tsx` - Main layout (Phase 2)
  - Object type tabs (Artifacts, Marketplace Sources)
  - Field sidebar + options content

- `skillmeat/web/components/settings/field-*.tsx` - Sub-components (Phase 2)
  - field-options-list.tsx
  - add-option-dialog.tsx
  - edit-option-dialog.tsx
  - remove-option-dialog.tsx
  - field-sidebar.tsx (not detailed)

### Hooks & API Client

- `skillmeat/web/hooks/use-field-options.ts` - TanStack Query hooks (Phase 2)
  - useFieldOptions()
  - useCreateFieldOption()
  - useUpdateFieldOption()
  - useDeleteFieldOption()

- `skillmeat/web/hooks/index.ts` - Barrel export (Phase 2)
  - Re-export all hooks

- `skillmeat/web/lib/api/fields.ts` - API client functions (Phase 2)
  - getFieldOptions()
  - createFieldOption()
  - updateFieldOption()
  - deleteFieldOption()

### Types

- `skillmeat/web/types/fields.ts` - TypeScript definitions (Phase 2)
  - FieldOption interface
  - FieldListResponse interface
  - PageInfo interface

### Testing

- `tests/unit/core/services/test_fields_service.py` - Unit tests (Phase 1)
- `tests/api/routers/test_fields_router.py` - Integration tests (Phase 1)
- `skillmeat/web/__tests__/fields-*.tsx` - Component tests (Phase 2-5)
- `skillmeat/web/tests/fields.e2e.ts` - E2E tests (Phase 3-5)

---

## Shared Patterns & Conventions

### MeatyPrompts Architecture

```
Database Layer (ORM models)
    ↓
Repository Layer (data access)
    ↓
Service Layer (business logic)
    ↓
API Router Layer (HTTP endpoints)
    ↓
Frontend Client (React components)
```

**Application**:
- Phase 1 implements: Field Registry → Service → Router
- Repository already exists (TagRepository)
- Frontend (Phase 2) consumes Router via TanStack Query

### Error Handling Pattern

```python
try:
    # Business logic
    result = service.operation()
    logger.info(f"Operation succeeded: {result}")
    return result
except SpecificError as e:
    logger.warning(f"Expected error: {e}")
    raise HTTPException(status_code=expected_code, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal error")
```

### Component Pattern (Frontend)

```tsx
'use client';  // Only if using hooks/events

export default function Component({ prop }: Props) {
  const { data, isLoading, error } = useQuery(...);
  const mutation = useMutation(...);

  return (
    <div>
      {/* Loading state */}
      {/* Error state */}
      {/* Content */}
    </div>
  );
}
```

### Validation Pattern

```python
# Schema level (Pydantic)
@field_validator("name")
def validate_name(cls, v):
    if not v.strip():
        raise ValueError("Name required")
    return v.strip()

# Service level
def create_option(self, name, color):
    if not name.strip():
        raise ValueError("Name required")
    if color and not is_valid_hex(color):
        raise ValueError("Invalid color")
```

---

## Success Criteria Summary

### Functional

- [ ] `/settings/fields` page with tabs (Artifacts, Marketplace Sources)
- [ ] Full tag CRUD (add, edit, remove)
- [ ] Cascade delete with usage validation
- [ ] Read-only field display (Auto Tags, Trust Level, Visibility, Scan Status)
- [ ] All error messages user-friendly

### Technical

- [ ] MeatyPrompts layered architecture followed
- [ ] >80% unit test coverage
- [ ] E2E test for critical path
- [ ] API response <200ms (p95)
- [ ] Page load <1s (p95)
- [ ] No breaking changes to existing APIs

### Quality

- [ ] WCAG 2.1 AA accessibility
- [ ] Keyboard navigation working
- [ ] Mobile responsive
- [ ] Cross-browser compatible
- [ ] Feature flags implemented

---

## Next Steps

1. **Review** this implementation plan with team
2. **Unblock** dependencies (existing TagService, settings page layout)
3. **Start Phase 1** - Backend engineer begins with Field Registry
4. **Start Phase 2** - Frontend engineer begins with Settings page (parallel)
5. **Track Progress** - Use `.claude/progress/global-fields-management/` for status updates

---

## Support & Questions

For implementation questions or blockers:
- Reference main plan: `global-fields-management-v1.md`
- Review phase-specific technical details
- Check CLAUDE.md for architecture patterns
- Ask questions in PR/code review

**Plan prepared by**: Implementation Planner Orchestrator
**Date**: 2026-01-22
**Version**: 1.0 (Ready for Execution)
