# Global Fields Management - Context

**PRD:** `docs/project_plans/PRDs/global-fields-management-v1.md`
**Implementation Plan:** `docs/project_plans/implementation_plans/features/global-fields-management-v1.md`
**Progress Tracking:** `.claude/progress/global-fields-management/`

---

## Overview

This feature delivers a centralized `/settings/fields` page enabling administrators to manage enumerable field options (Tags, Origin, Trust Level, Visibility, Auto Tags) across Artifacts and Marketplace Sources without direct database access.

### Key Outcomes

- Centralized UI at `/settings/fields` with object type tabs (Artifacts, Marketplace Sources)
- Full CRUD operations for tags (leveraging existing TagService)
- View-only display for system-managed fields (Auto Tags, Scan Status)
- Cascade delete support with usage validation
- <200ms API response times and <1s page load
- E2E test coverage for critical paths

---

## Architecture Decisions

### Backend Architecture

**Layered Flow:**
```
routers/fields.py → services/fields_service.py → repositories/tag_repository.py → database
```

**Key Components:**

1. **FieldRegistry** - Defines manageable fields per object type
   - Artifacts: Tags, Origin (view-only initially)
   - Marketplace Sources: Tags, Trust Level (view-only), Visibility (view-only), Auto Tags (view-only)

2. **FieldsService** - Wraps existing TagService for tag operations
   - Reuses TagService._slugify() for normalization
   - Adds validation: uniqueness, in-use checks, cascade deletes
   - Methods: list_field_options(), create_option(), update_option(), delete_option()

3. **Fields Router** - `/api/v1/fields/*` endpoints
   - GET /fields - List field options with pagination
   - POST /fields/options - Create option
   - PUT /fields/options/{id} - Update option
   - DELETE /fields/options/{id} - Delete option (cascade support)

**Error Handling:**
- 409 Conflict - Duplicate field values
- 422 Unprocessable Entity - Validation failures
- 400 Bad Request - In-use field deletion attempts
- 404 Not Found - Field/option not found

### Frontend Architecture

**Next.js 15 App Router Structure:**
```
/settings/fields (page.tsx - server component)
  └── FieldsClient.tsx ('use client' boundary)
      ├── ObjectTypeTabs (Artifacts, Marketplace Sources)
      ├── FieldSidebar (field list for selected object)
      └── FieldOptionsContent
          ├── FieldOptionsList (display options with actions)
          ├── AddOptionDialog (form validation, submission)
          ├── EditOptionDialog (pre-fill, validation)
          └── RemoveConfirmDialog (usage count, cascade warning)
```

**TanStack Query Hooks:**
- useFieldOptions() - Fetch field options with pagination
- useAddFieldOption() - Create option mutation
- useUpdateFieldOption() - Update option mutation
- useDeleteFieldOption() - Delete option mutation (cascade support)

**UI Components:**
- shadcn/ui primitives: Tabs, Card, Button, Dialog, Input, Badge
- Reuse existing tag-editor styling patterns for consistency

---

## Important Patterns to Follow

### Tag Normalization

**Always use existing TagService logic:**
- Trim → lowercase → replace spaces with underscores
- Example: "Python 3" → "python-3"
- Enforced at service layer, not UI

### Cascade Delete

**Tag deletion must cascade to artifacts:**
- Delete tag → remove from all artifact_tags associations
- Log operation with trace_id for audit
- Return cascade_count in response
- Existing TagService.delete_tag() handles this

### Validation Rules

**Field constraints:**
- Tag names: Not empty, unique (case-insensitive after normalization)
- Colors: Valid hex format or empty/null
- In-use prevention: Check usage_count before allowing deletion

### Pagination

**Cursor-based pagination for >50 items:**
- Use PageInfo DTO (cursor, has_next_page, has_previous_page)
- "Load More" button pattern in UI
- TanStack Query infinite query support

---

## Cross-Cutting Concerns

### Performance

**Targets:**
- API response: <200ms (p95)
- Page load: <1s (p95)
- Database query optimization for usage counts
- TanStack Query caching enabled

### Security

**Authentication & Authorization:**
- Use existing auth middleware
- Require admin role (TBD scope)
- Validate all inputs at service layer
- No direct database schema exposure

### Observability

**OpenTelemetry:**
- Spans for all field operations (list, create, update, delete)
- Structured JSON logs with trace_id, span_id, operation type
- Error tracking for validation failures and DB errors
- Monitor cascade delete operations

### Accessibility

**WCAG 2.1 AA Compliance:**
- Keyboard navigation (Tab, Enter, Esc)
- ARIA labels on icon buttons (Edit, Remove)
- Focus management in dialogs
- Color contrast compliance
- Descriptive error messages

---

## Integration Notes

### Existing Systems to Integrate With

**Backend:**
- TagService (`skillmeat/core/services/tag_service.py`) - Reuse normalization and cascade logic
- TagRepository - Data access layer
- MarketplaceSource model - JSON field for marketplace tags

**Frontend:**
- Settings page layout (`skillmeat/web/app/settings/page.tsx`) - Template for card-based layout
- tag-editor component (`skillmeat/web/components/shared/tag-editor.tsx`) - Styling patterns
- TanStack Query infrastructure - Already set up

### No Breaking Changes

**Backward Compatibility:**
- No changes to existing `/api/tags/*` endpoints
- No changes to existing tag-editor component behavior
- New `/api/v1/fields/*` endpoints are additive only

---

## Risk Mitigation

### High-Risk Areas

1. **Cascade Delete Operations**
   - Mitigation: Thorough unit testing, dry-run mode in Phase 3, audit logging
   - Verification: Integration tests covering cascade scenarios

2. **Tag Normalization Edge Cases**
   - Mitigation: Reuse existing TagService._slugify(), comprehensive test suite
   - Verification: Unit tests with diverse input (Unicode, special chars, empty strings)

3. **Performance with Large Field Lists**
   - Mitigation: Cursor pagination, client-side caching, query optimization
   - Verification: Performance profiling with >1000 tags

4. **User Confusion on Read-Only Fields**
   - Mitigation: Clear UI indicators (lock icon, disabled buttons, help text)
   - Verification: UX testing with target users

---

## Phase Dependencies

**Sequential Requirements:**

- Phase 1 (Backend) → Phase 3 (Tags CRUD)
- Phase 2 (Frontend) → Phase 3 (Tags CRUD)
- Phase 1 + Phase 2 → Phase 4 (Marketplace Fields)
- Phase 3 + Phase 4 → Phase 5 (Polish & Testing)
- Phase 5 → Phase 6 (Documentation)

**Parallel Opportunities:**

- Phase 1 and Phase 2 can run in parallel (backend + frontend teams)
- Phase 3 and Phase 4 can run in parallel after Phase 1+2 complete
- All Phase 5 tasks can run in parallel (polish sprint)
- All Phase 6 tasks can run in parallel (documentation sprint)

---

## Feature Flags

**FIELDS_MANAGEMENT_ENABLED** (default: true)
- Controls visibility of `/settings/fields` page
- Allows soft launch and gradual rollout

**FIELDS_ALLOW_ENUM_EDIT** (default: false)
- Future flag for enabling editing of enum field values (Trust Level, Visibility)
- View-only in Phase 1, editable in future phase

---

## Testing Strategy

### Unit Tests (>80% Coverage)

**Backend:**
- FieldsService methods: create, update, delete, list
- Tag normalization logic
- Cascade delete validation
- Usage count calculations
- Error handling paths

**Frontend:**
- TanStack Query hooks
- Form validation logic
- Dialog open/close state
- Error display components

### Integration Tests

**API Endpoints:**
- GET /fields - List with pagination
- POST /fields/options - Create with validation
- PUT /fields/options/{id} - Update with validation
- DELETE /fields/options/{id} - Delete with cascade

**Error Scenarios:**
- Duplicate tag creation (409)
- Invalid color format (422)
- Delete in-use field (400)

### E2E Tests (Playwright)

**Critical Path:**
1. Navigate to `/settings/fields`
2. Add new tag (verify normalization)
3. Edit existing tag (verify update)
4. Remove unused tag (verify deletion)
5. Attempt remove in-use tag (verify cascade warning)

---

## Deployment Plan

### Pre-Deployment Checklist

- [ ] All unit tests passing (>80% coverage)
- [ ] E2E tests passing in CI/CD
- [ ] Performance benchmarks met (<200ms API, <1s load)
- [ ] WCAG 2.1 AA accessibility verified
- [ ] Code review approved by team leads
- [ ] Feature flags implemented and testable

### Rollout Strategy

1. **Day 1:** Deploy with `FIELDS_MANAGEMENT_ENABLED=false` (disabled)
2. **Day 2:** Enable flag for beta testers, monitor error rates
3. **Day 3:** General availability (enable for all users)
4. **Ongoing:** Monitor API response times, cascade operations, error logs

### Rollback Plan

If critical issues discovered:
1. Set `FIELDS_MANAGEMENT_ENABLED=false` to hide page
2. Investigate logs using trace_id
3. Rollback code if necessary
4. Re-enable with fixes

---

## Additional Resources

**Deep Dive Documents:**
- Phase 1: `docs/project_plans/implementation_plans/features/global-fields-management-v1/phase-1-backend-infrastructure.md`
- Phase 2: `docs/project_plans/implementation_plans/features/global-fields-management-v1/phase-2-frontend-core.md`
- Phase 3: `docs/project_plans/implementation_plans/features/global-fields-management-v1/phase-3-tags-crud.md`
- Phase 4: `docs/project_plans/implementation_plans/features/global-fields-management-v1/phase-4-marketplace-fields.md`
- Phase 5: `docs/project_plans/implementation_plans/features/global-fields-management-v1/phase-5-polish-testing.md`
- Phase 6: `docs/project_plans/implementation_plans/features/global-fields-management-v1/phase-6-documentation.md`

**Symbol References:**
- API Routers: `ai/symbols-api.json` - Pattern examples for CRUD, pagination
- Services: `ai/symbols-api.json` - Business logic templates
- React Components: `ai/symbols-web.json` - shadcn primitives, custom components

**Database Schema:**
- Tag model: `skillmeat/cache/models.py`
- MarketplaceSource model: `skillmeat/cache/models.py`

---

## Open Questions & Decisions

### Resolved

- **Q:** Should Origin (Artifacts) be editable in Phase 1?
  - **A:** View-only in Phase 1; may enable edits in Phase 2 with `FIELDS_ALLOW_ENUM_EDIT` flag

- **Q:** Should Auto Tags be editable?
  - **A:** No; system-managed, view-only. Manual tags separate from auto-tags

- **Q:** What happens if a tag is removed while artifact edit modal is open?
  - **A:** Optimistic update handles removal; tag selector re-fetches on next interaction

### Pending

- **Q:** Should field management require admin role or be available to all users?
  - **A:** TBD; assume admin-only for security; implement auth check in service layer

- **Q:** Should we implement undo/redo for field deletions?
  - **A:** Not in Phase 1; can add soft-delete + restore in Phase 2

---

**Last Updated:** 2026-01-22
**Status:** Ready for implementation - Phase 1 can begin
