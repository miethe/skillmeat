# Path Tag Review E2E Tests

End-to-end tests for the path-based tag extraction review workflow (Phase 2).

## Test File

- **Location**: `tests/e2e/path-tag-review.spec.ts`
- **Framework**: Playwright
- **Test Count**: 18 tests across 8 test suites

## Test Coverage

### 1. Opening and Viewing (3 tests)

- ✅ User can open catalog entry and navigate to Suggested Tags tab
- ✅ Displays all extracted segments with correct statuses
- ✅ Displays summary with correct counts

### 2. Approving Segments (3 tests)

- ✅ User can approve a pending segment
- ✅ Approve button shows loading state while request is pending
- ✅ Summary counts update after approving segment

### 3. Rejecting Segments (2 tests)

- ✅ User can reject a pending segment
- ✅ Summary counts update after rejecting segment

### 4. Excluded Segments (2 tests)

- ✅ Excluded segments display with badge and no action buttons
- ✅ Excluded segments are included in summary counts

### 5. Persistence (1 test)

- ✅ Changes persist after closing and reopening modal

### 6. Error Handling (2 tests)

- ✅ Displays error state when path segments fail to load
- ✅ Displays error when status update fails

### 7. Loading States (1 test)

- ✅ Displays loading skeleton while path segments are loading

### 8. Accessibility (2 tests)

- ✅ Approve and reject buttons have proper ARIA labels
- ✅ Tab navigation works correctly

## Running Tests

### Run all path tag review tests

```bash
cd skillmeat/web
pnpm test:e2e tests/e2e/path-tag-review.spec.ts
```

### Run specific test suite

```bash
pnpm test:e2e tests/e2e/path-tag-review.spec.ts -g "Approving Segments"
```

### Run in UI mode (interactive)

```bash
pnpm test:e2e:ui tests/e2e/path-tag-review.spec.ts
```

### Run in debug mode

```bash
pnpm test:e2e:debug tests/e2e/path-tag-review.spec.ts
```

### Run with specific browser

```bash
pnpm test:e2e tests/e2e/path-tag-review.spec.ts --project=chromium
```

## Mock Data Structure

The tests use comprehensive mock data to simulate the entire workflow:

### Mock Source

- GitHub repository: `anthropics/skills`
- Trust level: `official`
- Contains catalog entries with path segments

### Mock Catalog Entry

- Name: `ai-engineer`
- Path: `categories/05-data-ai/ai-engineer`
- Status: `new`
- Confidence score: 95

### Mock Path Segments

- **Pending segments**: `categories`, `05-data-ai`, `ai-engineer`
- **Excluded segments**: `src`, `lib` (with exclusion reasons)
- **Normalized values**: `05-data-ai` → `data-ai`

### Mock API Endpoints

- `GET /api/v1/marketplace/sources` - List sources
- `GET /api/v1/marketplace/sources/{id}` - Get source detail
- `GET /api/v1/marketplace/sources/{id}/catalog` - List catalog entries
- `GET /api/v1/marketplace/sources/{id}/catalog/{entryId}/path-segments` - Get path segments
- `PATCH /api/v1/marketplace/sources/{id}/catalog/{entryId}/path-segments` - Update segment status

## Test Helpers

The tests use shared helper functions from `tests/helpers/test-utils.ts`:

- `waitForPageLoad()` - Wait for page to be fully loaded
- `mockApiRoute()` - Mock API routes with custom responses
- `expectModalOpen()` - Verify modal is open
- `expectModalClosed()` - Verify modal is closed

## Component Selectors

The tests rely on the following component structure:

### CatalogEntryModal

- **Modal**: `[role="dialog"]`
- **Tabs**: `[role="tab"]` with text filters
- **Tab Content**: `[role="tabpanel"]`

### PathTagReview Component

- **Segment rows**: `div` with nested `text="segment-name"`
- **Approve button**: `button[aria-label="Approve segment"]`
- **Reject button**: `button[aria-label="Reject segment"]`
- **Status badges**: `text=Pending`, `text=Approved`, `text=Rejected`, `text=Excluded`
- **Summary counts**: Text content matching `/N pending/`, `/N approved/`, etc.

## Accessibility Testing

The tests verify:

- ✅ Proper ARIA labels on action buttons
- ✅ Keyboard navigation through tabs
- ✅ Focus management
- ✅ Screen reader support (via ARIA attributes)

## Known Limitations

1. **Timing-sensitive tests**: Loading states are difficult to test reliably due to fast mock responses. The test uses `waitForTimeout()` to give the UI time to render.

2. **Error toast notifications**: The tests don't currently verify toast notifications for mutation errors, as this depends on the component's implementation details.

3. **Integration with backend**: These are E2E tests with mocked APIs. For true integration testing, use the backend integration tests in `tests/integration/test_path_tags_workflow.py`.

## Maintenance

When updating the PathTagReview component:

1. **Update selectors** if component structure changes
2. **Add new tests** for new features
3. **Update mock data** to match API schema changes
4. **Verify accessibility** after UI changes

## Related Files

- **Component**: `components/marketplace/path-tag-review.tsx`
- **Component Tests**: `__tests__/components/marketplace/path-tag-review.test.tsx`
- **Hook**: `hooks/use-path-tags.ts`
- **API Client**: `lib/api/catalog.ts`
- **Types**: `types/path-tags.ts`
- **Backend Integration Tests**: `tests/integration/test_path_tags_workflow.py`

## CI/CD Integration

These tests run automatically in CI:

- **GitHub Actions**: On pull requests and merges to main
- **Browser Matrix**: Chromium, Firefox, WebKit
- **Retry Policy**: 2 retries on failure in CI
- **Parallel Execution**: Disabled in CI for consistency

## Debugging Failed Tests

### View test trace

```bash
pnpm exec playwright show-trace test-results/.../trace.zip
```

### View HTML report

```bash
pnpm exec playwright show-report
```

### Run with headed browser

```bash
pnpm test:e2e tests/e2e/path-tag-review.spec.ts --headed
```

### Run with slow-mo

```bash
pnpm test:e2e tests/e2e/path-tag-review.spec.ts --headed --slow-mo=1000
```

## Future Enhancements

Potential additions to the test suite:

1. **Bulk operations** - Approve/reject all pending segments
2. **Filtering** - Filter segments by status
3. **Sorting** - Sort segments by depth or alphabetically
4. **Export** - Export approved tags
5. **Undo/Redo** - Revert status changes
6. **Real backend** - Integration tests against real API (not mocked)
