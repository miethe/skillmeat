---
type: progress
prd: tags-refactor-v1
phase: 7-8
title: Testing and Documentation
status: pending
completed_at: null
progress: 0
total_tasks: 9
completed_tasks: 0
total_story_points: 16
completed_story_points: 0
tasks:
- id: TEST-001
  title: Backend Unit Tests
  description: Unit tests for tag service, repository, schemas
  status: pending
  story_points: 2
  assigned_to:
  - python-backend-engineer
  dependencies:
  - FILTER-004
  created_at: '2025-12-18'
- id: TEST-002
  title: API Integration Tests
  description: Test all tag endpoints with various scenarios
  status: pending
  story_points: 2
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TEST-001
  created_at: '2025-12-18'
- id: TEST-003
  title: Component Tests
  description: Test TagInput, Badge, Filter components
  status: pending
  story_points: 2
  assigned_to:
  - frontend-developer
  dependencies:
  - TEST-001
  created_at: '2025-12-18'
- id: TEST-004
  title: E2E Tests
  description: End-to-end tag workflow testing
  status: pending
  story_points: 2
  assigned_to:
  - frontend-developer
  dependencies:
  - TEST-003
  created_at: '2025-12-18'
- id: TEST-005
  title: Accessibility Tests
  description: WCAG 2.1 AA compliance automated testing
  status: pending
  story_points: 1
  assigned_to:
  - web-accessibility-checker
  dependencies:
  - TEST-004
  created_at: '2025-12-18'
- id: DOC-001
  title: API Documentation
  description: Document all tag endpoints with examples
  status: pending
  story_points: 1
  assigned_to:
  - api-documenter
  dependencies:
  - TEST-005
  created_at: '2025-12-18'
- id: DOC-002
  title: Component Documentation
  description: Document TagInput, Badge, Filter components
  status: pending
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-005
  created_at: '2025-12-18'
- id: DOC-003
  title: User Guide
  description: Create tag usage guide for end users
  status: pending
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-005
  created_at: '2025-12-18'
- id: DOC-004
  title: Developer Guide
  description: Create developer docs for tag system
  status: pending
  story_points: 1
  assigned_to:
  - documentation-writer
  dependencies:
  - TEST-005
  created_at: '2025-12-18'
parallelization:
  batch_1:
  - TEST-001
  batch_2:
  - TEST-002
  batch_3:
  - TEST-003
  batch_4:
  - TEST-004
  batch_5:
  - TEST-005
  batch_6:
  - DOC-001
  - DOC-002
  - DOC-003
  - DOC-004
context_files:
- tests/
- docs/
blockers: []
notes: Testing and documentation for tags system. Phases 7-8 verify implementation
  quality and document for users/developers. Depends on FILTER-004 completion.
schema_version: 2
doc_type: progress
feature_slug: tags-refactor-v1
---

# Phases 7-8: Testing and Documentation

Testing and documentation for the tags system, including unit tests, integration tests, component tests, E2E tests, accessibility validation, and user/developer documentation.

**Total Duration**: 3 days
**Total Story Points**: 16
**Dependencies**: Phase 6 (FILTER-004) complete
**Assigned Agents**: python-backend-engineer, frontend-developer, web-accessibility-checker, api-documenter, documentation-writer

---

## Phase 7: Testing Layer

**Duration**: 2 days
**Story Points**: 9
**Objective**: Comprehensive testing of backend, frontend, and accessibility requirements.

### TEST-001: Backend Unit Tests (2 pts)

```markdown
Task("python-backend-engineer", "TEST-001: Implement backend unit tests

Files to Create:
  - tests/unit/services/test_tag_service.py
  - tests/unit/services/test_artifact_tag_service.py
  - tests/unit/repositories/test_tag_repository.py
  - tests/unit/schemas/test_tag_schemas.py

Coverage Requirement: >80% for all tag-related code

Test Scenarios:

1. Tag Service Tests (test_tag_service.py)
   - test_create_tag_success: Create valid tag
   - test_create_tag_duplicate_name: Duplicate name raises error
   - test_create_tag_invalid_name: Empty/long names rejected
   - test_update_tag_success: Update tag fields
   - test_update_tag_slug_regeneration: Slug regenerates on name change
   - test_delete_tag_success: Delete removes tag and associations
   - test_list_tags_pagination: Cursor pagination works
   - test_search_tags_by_name: Search by substring (case-insensitive)
   - test_search_tags_empty: No results returns empty list
   - test_get_tag_404: Missing tag returns 404
   - test_tag_color_validation: Hex color format validated

2. Artifact-Tag Service Tests (test_artifact_tag_service.py)
   - test_add_tag_to_artifact_success: Tag added
   - test_add_tag_artifact_not_found: Missing artifact 404
   - test_add_tag_tag_not_found: Missing tag 404
   - test_add_tag_duplicate_association: Already associated 409
   - test_remove_tag_from_artifact_success: Tag removed
   - test_remove_tag_not_found: Missing association 404
   - test_get_artifact_tags_empty: No tags returns empty list
   - test_get_artifact_tags_multiple: Multiple tags returned
   - test_update_artifact_tags_replace_all: Replaces tag set
   - test_filter_artifacts_by_tags_and_logic: AND logic works
   - test_filter_artifacts_empty_result: No matches returns empty

3. Tag Repository Tests (test_tag_repository.py)
   - test_crud_operations: Create, read, update, delete
   - test_unique_constraint_name: Duplicate names rejected
   - test_unique_constraint_slug: Duplicate slugs rejected
   - test_pagination_cursor_decoding: Cursor works correctly
   - test_artifact_tag_association_cascade: Deleting tag removes associations
   - test_tag_statistics_accurate: Count queries return correct values
   - test_concurrent_operations: Multiple concurrent operations safe

4. Schema Validation Tests (test_tag_schemas.py)
   - test_tag_response_serialization: ORM → Pydantic
   - test_tag_create_request_validation: Valid input accepted
   - test_tag_create_request_invalid_name: Invalid name rejected
   - test_tag_color_hex_validation: Hex format validated
   - test_tag_update_request_optional_fields: Partial updates work
   - test_artifact_tags_response_serialization: Correct format

Test Fixtures:
- Sample tag data (valid and invalid)
- Sample artifacts
- Database session fixture
- Clean database before each test

Assertions:
- Verify correct return types
- Verify exception types and messages
- Verify database state changes
- Verify no side effects

Run Tests:
pytest tests/unit/services/test_tag_service.py -v --cov=skillmeat.core.services")
```

### TEST-002: API Integration Tests (2 pts)

```markdown
Task("python-backend-engineer", "TEST-002: Implement API integration tests

Files to Create:
  - tests/integration/routers/test_tags_router.py
  - tests/integration/routers/test_artifact_tags_router.py

Coverage Requirement: >80% for all endpoints

Test Scenarios:

1. Tag CRUD Endpoints (test_tags_router.py)
   - test_get_tags_list: GET /tags returns list
   - test_get_tags_pagination: Cursor pagination works
   - test_get_tags_search: Query param filtering works
   - test_get_tags_401_unauthorized: Missing auth returns 401
   - test_post_tags_create: POST /tags creates tag
   - test_post_tags_409_conflict: Duplicate name returns 409
   - test_post_tags_422_invalid: Invalid data returns 422
   - test_get_tag_by_id: GET /tags/{id} returns tag
   - test_get_tag_404_not_found: Missing ID returns 404
   - test_put_tag_update: PUT /tags/{id} updates tag
   - test_put_tag_404_not_found: Update missing ID returns 404
   - test_delete_tag: DELETE /tags/{id} removes tag
   - test_delete_tag_404_not_found: Delete missing ID returns 404
   - test_delete_tag_204_no_content: Delete returns 204 with no body

2. Artifact-Tag Endpoints (test_artifact_tags_router.py)
   - test_get_artifact_tags: GET /artifacts/{id}/tags returns tags
   - test_get_artifact_tags_empty: No tags returns empty list
   - test_get_artifact_tags_404: Missing artifact returns 404
   - test_post_artifact_tags_add: POST /artifacts/{id}/tags/{tag_id} adds tag
   - test_post_artifact_tags_409_conflict: Already associated returns 409
   - test_post_artifact_tags_404_artifact: Missing artifact returns 404
   - test_post_artifact_tags_404_tag: Missing tag returns 404
   - test_delete_artifact_tags: DELETE /artifacts/{id}/tags/{tag_id} removes
   - test_delete_artifact_tags_404: Missing association returns 404
   - test_put_artifact_tags_bulk_update: PUT with tag list replaces all

3. Response Format Tests
   - test_successful_response_format: Response envelope correct
   - test_error_response_format: Error format consistent
   - test_pagination_response_includes_cursor: Cursor present
   - test_pagination_response_no_cursor_at_end: Null cursor at end
   - test_status_codes_201_created: POST returns 201
   - test_status_codes_204_no_content: DELETE returns 204
   - test_status_codes_400_bad_request: Invalid input returns 400
   - test_status_codes_404_not_found: Missing resource returns 404
   - test_status_codes_409_conflict: Duplicate/conflict returns 409

4. Error Handling Tests
   - test_validation_error_detail: Validation errors include detail
   - test_database_error_handling: DB errors return 500
   - test_concurrent_write_safety: Concurrent writes safe (no race conditions)

5. Integration with Other Systems
   - test_tag_deletion_removes_associations: Cascading delete works
   - test_artifact_deletion_removes_associations: Cascade on artifact delete
   - test_tag_update_preserves_associations: Update doesn't break links

Test Fixtures:
- Create test database
- Create sample artifacts, tags, associations
- API client (test client from FastAPI)
- Clean database before each test

Run Tests:
pytest tests/integration/routers/test_tags_router.py -v --cov=skillmeat.api.app.routers")
```

### TEST-003: Component Tests (2 pts)

```markdown
Task("frontend-developer", "TEST-003: Implement component tests

Files to Create:
  - tests/components/TagInput.test.tsx
  - tests/components/TagBadge.test.tsx
  - tests/components/TagFilterPopover.test.tsx
  - tests/components/ArtifactDetail.test.tsx (tags section)

Framework: Jest + React Testing Library

Coverage Requirement: >80% for all components

Test Scenarios:

1. TagInput Component Tests (TagInput.test.tsx)
   - test_renders_with_empty_value: Initial render
   - test_renders_with_initial_tags: Shows selected tags
   - test_add_tag_by_typing_and_enter: Type + Enter creates tag
   - test_add_tag_by_clicking_suggestion: Click to add
   - test_search_filters_suggestions: Search works
   - test_remove_tag_by_clicking_x: X button removes
   - test_remove_tag_by_backspace: Backspace on empty removes last
   - test_copy_paste_comma_separated: CSV paste adds multiple
   - test_keyboard_navigation_suggestions: Arrow keys work
   - test_keyboard_navigation_escape: Escape closes dropdown
   - test_max_tags_limit: Cannot exceed maxTags
   - test_disabled_state: Disabled prop disables input
   - test_placeholder_text: Placeholder displays
   - test_readonly_mode: Readonly prevents changes
   - test_accessibility_aria_labels: ARIA attributes present
   - test_accessibility_keyboard_only: Usable without mouse

2. TagBadge Component Tests (TagBadge.test.tsx)
   - test_renders_with_name: Badge shows tag name
   - test_renders_with_color: Badge shows color
   - test_contrast_ratio_white_text: White text on dark background
   - test_contrast_ratio_black_text: Black text on light background
   - test_remove_button_click: Click X calls onRemove
   - test_remove_button_keyboard: Keyboard accessible remove
   - test_no_remove_button_readonly: No X when not removable
   - test_icon_optional: Icon displays if provided

3. TagFilterPopover Tests (TagFilterPopover.test.tsx)
   - test_renders_trigger_button: Button displays with count
   - test_click_opens_popover: Popover opens
   - test_click_outside_closes_popover: Popover closes
   - test_escape_closes_popover: Escape key closes
   - test_search_filters_tags: Search input filters tags
   - test_checkbox_toggle: Clicking checkbox toggles selection
   - test_multiple_selection: Can select multiple tags
   - test_select_all_button: Select all works
   - test_clear_all_button: Clear all works
   - test_tag_count_display: Shows 'X of Y selected'
   - test_shows_artifact_count: Tag count displayed
   - test_disabled_tags_with_zero_count: 0-count tags disabled
   - test_mobile_responsive: Mobile layout works
   - test_accessibility_keyboard_navigation: Tab/arrow keys work
   - test_accessibility_screen_reader: ARIA labels present

4. Artifact Detail Tags Tests (ArtifactDetail.test.tsx - tags section)
   - test_renders_tags_section: Tags section displays
   - test_no_tags_empty_state: Shows 'No tags' when empty
   - test_displays_all_tags: All tags rendered
   - test_badges_have_colors: Tag colors displayed
   - test_tag_click_filters: Clicking tag filters list
   - test_tag_click_updates_url: URL param updated
   - test_responsive_layout: Mobile wrapping works

Test Utilities:
- renderWithProviders: Render with QueryClient
- userEvent: Simulate user interactions (recommended over fireEvent)
- screen: Query rendered elements
- waitFor: Async operations

Run Tests:
npm test -- TagInput.test.tsx
npm test -- --coverage")
```

### TEST-004: E2E Tests (2 pts)

```markdown
Task("frontend-developer", "TEST-004: Implement end-to-end workflow tests

Framework: Playwright (recommended) or Cypress

Files to Create:
  - tests/e2e/tags.spec.ts
  - tests/e2e/artifact-tags.spec.ts

Test Scenarios:

1. Complete Tag Workflow (tags.spec.ts)
   - test_create_and_display_tag: Create tag via modal, see in list
   - test_search_tag_by_name: Search for created tag
   - test_edit_tag_color: Change tag color
   - test_delete_tag_cascades: Delete tag removes from artifacts
   - test_add_tag_to_artifact: Add tag via ParameterEditorModal
   - test_remove_tag_from_artifact: Remove tag and verify
   - test_view_tags_on_detail: Navigate to artifact, see tags

2. Artifact-Tag Workflow (artifact-tags.spec.ts)
   - test_add_tags_to_new_artifact: Create artifact, add tags
   - test_edit_tags_on_existing: Edit artifact, modify tags
   - test_copy_paste_multiple_tags: Paste CSV tags
   - test_tag_filtering: Filter artifact list by tags
   - test_filter_url_persistence: Reload page, filters persist
   - test_dashboard_tag_metrics: Dashboard shows tag stats
   - test_click_tag_filters_list: Click tag in detail → filtered list

3. Filter & Search Workflow
   - test_open_tag_filter_popover: Click filter, popover opens
   - test_select_multiple_filters: Select multiple tags
   - test_filter_updates_artifact_list: List updates on filter
   - test_clear_filters: Reset to all artifacts
   - test_search_with_active_filters: Search + filters work together

4. Keyboard & Accessibility Workflow
   - test_keyboard_only_tag_input: Use TagInput without mouse
   - test_keyboard_only_filtering: Filter without mouse
   - test_screen_reader_compatibility: Test with NVDA/JAWS
   - test_focus_management: Focus flows logically
   - test_high_contrast_mode: Works in high contrast

Test Page Objects (Optional):
```typescript
export class ArtifactPage {
  async addTagToArtifact(artifactName: string, tagName: string) {
    // Implementation
  }

  async filterByTag(tagName: string) {
    // Implementation
  }

  async getTagBadges() {
    // Implementation
  }
}
```

Run Tests:
npx playwright test
npx playwright test --ui  # Interactive mode")
```

### TEST-005: Accessibility Tests (1 pt)

```markdown
Task("web-accessibility-checker", "TEST-005: WCAG 2.1 AA compliance validation

Tools:
  - axe DevTools Core (automated)
  - axe-core npm package (CI)
  - WAVE browser extension
  - Manual keyboard testing
  - Screen reader testing

Automated Accessibility Testing:

Files to Create:
  - tests/accessibility/tags-a11y.test.ts

Using axe-core in tests:
```typescript
import { axe, toHaveNoViolations } from 'jest-axe';

describe('TagInput Accessibility', () => {
  it('should not have any accessibility violations', async () => {
    const { container } = render(<TagInput />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

Manual Testing Checklist:

1. Keyboard Navigation
   - [ ] Tab through all components
   - [ ] Focus visible on all elements
   - [ ] No keyboard traps
   - [ ] Logical tab order
   - [ ] Arrow keys work as expected
   - [ ] Escape closes modals/popovers
   - [ ] Enter submits forms
   - [ ] Space toggles checkboxes

2. Screen Reader Testing
   - [ ] All labels announced
   - [ ] Form inputs described
   - [ ] Error messages announced
   - [ ] Tag additions/removals announced
   - [ ] Suggestion list described
   - [ ] Popover content accessible
   - [ ] Proper heading hierarchy

3. Color & Contrast
   - [ ] Text on tag badges: 4.5:1 minimum
   - [ ] UI elements: 3:1 minimum
   - [ ] Focus indicators visible (3:1)
   - [ ] No information conveyed by color alone
   - [ ] Color blindness friendly (patterns/text)

4. Responsive & Mobile
   - [ ] Touch targets: 44x44px minimum
   - [ ] Spacing adequate on mobile
   - [ ] Zoom to 200% works
   - [ ] Landscape/portrait modes work
   - [ ] Mobile screen reader (iOS, Android)

5. Assistive Technology Compatibility
   - [ ] Works with: Screen readers (NVDA, JAWS, VoiceOver)
   - [ ] Works with: Speech recognition
   - [ ] Works with: Magnification software
   - [ ] Works with: High contrast mode
   - [ ] Works with: Reduced motion settings

WCAG 2.1 AA Criteria Coverage:

- [ ] 1.4.3 Contrast (Minimum) - Color contrast 4.5:1
- [ ] 2.1.1 Keyboard - All functionality keyboard accessible
- [ ] 2.1.2 No Keyboard Trap - Can escape with keyboard
- [ ] 2.4.3 Focus Order - Logical tab order
- [ ] 2.4.7 Focus Visible - Visual focus indicator
- [ ] 3.2.2 On Input - No context change on input
- [ ] 3.3.1 Error Identification - Errors clearly identified
- [ ] 3.3.3 Error Suggestion - Suggestions provided for errors
- [ ] 4.1.2 Name, Role, Value - Proper ARIA attributes

Test Report:
Create accessibility report with:
- Automated test results (axe-core)
- Manual testing checklist results
- Known limitations (if any)
- Remediation steps for failures
- WCAG 2.1 AA certification statement

Run Automated Tests:
npm run test:a11y")
```

---

## Phase 8: Documentation Layer

**Duration**: 1 day
**Story Points**: 4
**Objective**: Document tag system for users and developers.

### DOC-001: API Documentation (1 pt)

```markdown
Task("api-documenter", "DOC-001: Document tag API endpoints

File: docs/api/tags.md

Structure:

# Tag API Documentation

## Overview
Brief description of tag system, use cases, and architecture.

## Base URL
`https://api.skillmeat.local/api/v1` (or similar)

## Authentication
Document authentication requirements (if any).

## Endpoints

### List Tags
\`\`\`
GET /tags
\`\`\`

**Description**: Retrieve paginated list of tags with optional search

**Query Parameters**:
- limit (integer, default: 50, max: 100) - Items per page
- after_cursor (string, optional) - Pagination cursor from previous response
- search (string, optional) - Search tags by name (substring match)

**Response**: 200 OK
\`\`\`json
{
  \"data\": [
    {
      \"id\": 1,
      \"name\": \"python\",
      \"slug\": \"python\",
      \"color\": \"#3776ab\",
      \"created_at\": \"2025-12-18T10:00:00Z\",
      \"updated_at\": \"2025-12-18T10:00:00Z\",
      \"artifact_count\": 45
    }
  ],
  \"meta\": {
    \"next_cursor\": \"eyJpZCI6IDIsICJjcmVhdGVkX2F0IjogIjIwMjUtMTItMTlUMTA6MDA6MDBaIn0=\",
    \"count\": 50
  }
}
\`\`\`

**Error Responses**:
- 400 Bad Request: Invalid parameters
- 500 Internal Server Error: Server error

### Create Tag
\`\`\`
POST /tags
\`\`\`

**Description**: Create a new tag

**Request Body**:
\`\`\`json
{
  \"name\": \"fastapi\",
  \"color\": \"#009688\"
}
\`\`\`

**Response**: 201 Created
\`\`\`json
{
  \"data\": {
    \"id\": 2,
    \"name\": \"fastapi\",
    \"slug\": \"fastapi\",
    \"color\": \"#009688\",
    \"created_at\": \"2025-12-18T10:00:00Z\",
    \"updated_at\": \"2025-12-18T10:00:00Z\"
  }
}
\`\`\`

**Error Responses**:
- 400 Bad Request: Missing required fields
- 409 Conflict: Tag name already exists
- 422 Unprocessable Entity: Invalid data format

### Get Tag
\`\`\`
GET /tags/{tag_id}
\`\`\`

**Description**: Retrieve a specific tag by ID

**Path Parameters**:
- tag_id (integer, required) - Tag identifier

**Response**: 200 OK
\`\`\`json
{
  \"data\": {
    \"id\": 1,
    \"name\": \"python\",
    \"slug\": \"python\",
    \"color\": \"#3776ab\",
    \"created_at\": \"2025-12-18T10:00:00Z\",
    \"updated_at\": \"2025-12-18T10:00:00Z\"
  }
}
\`\`\`

**Error Responses**:
- 404 Not Found: Tag not found

### Update Tag
\`\`\`
PUT /tags/{tag_id}
\`\`\`

**Description**: Update tag properties

**Path Parameters**:
- tag_id (integer, required) - Tag identifier

**Request Body**:
\`\`\`json
{
  \"name\": \"python3\",
  \"color\": \"#3776ab\"
}
\`\`\`

**Response**: 200 OK

**Error Responses**:
- 404 Not Found: Tag not found
- 409 Conflict: Name already exists

### Delete Tag
\`\`\`
DELETE /tags/{tag_id}
\`\`\`

**Description**: Delete a tag and remove associations

**Response**: 204 No Content

**Error Responses**:
- 404 Not Found: Tag not found

### Get Artifact Tags
\`\`\`
GET /artifacts/{artifact_id}/tags
\`\`\`

**Description**: List all tags for an artifact

**Response**: 200 OK
\`\`\`json
{
  \"data\": {
    \"artifact_id\": \"abc123\",
    \"tags\": [ ... ]
  }
}
\`\`\`

### Add Tag to Artifact
\`\`\`
POST /artifacts/{artifact_id}/tags/{tag_id}
\`\`\`

**Response**: 201 Created

### Remove Tag from Artifact
\`\`\`
DELETE /artifacts/{artifact_id}/tags/{tag_id}
\`\`\`

**Response**: 204 No Content

## Common Use Cases

### Search for tags matching a pattern
\`\`\`
GET /tags?search=python&limit=10
\`\`\`

### Paginate through all tags
\`\`\`
GET /tags?limit=50&after_cursor=abc123
\`\`\`

### Add multiple tags to artifact
\`\`\`
POST /artifacts/{id}/tags/{tag1_id}
POST /artifacts/{id}/tags/{tag2_id}
\`\`\`

Or use bulk endpoint (if implemented):
\`\`\`
PUT /artifacts/{id}/tags
{\"tag_ids\": [1, 2, 3]}
\`\`\`

## Rate Limiting
Document rate limits (if applicable).

## Changelog
Document API changes and versions.")
```

### DOC-002: Component Documentation (1 pt)

```markdown
Task("documentation-writer", "DOC-002: Document frontend components

Files:
  - docs/components/TagInput.md
  - docs/components/TagBadge.md
  - docs/components/TagFilterPopover.md

## TagInput Component

**File**: `skillmeat/web/components/ui/tag-input.tsx`

**Purpose**: Searchable input component for adding/removing tags

**Usage**:
\`\`\`tsx
import { TagInput } from '@/components/ui/tag-input';

<TagInput
  value={tags}
  onChange={setTags}
  onSearchTags={searchTags}
  onCreateTag={createTag}
  placeholder=\"Add tags...\"
  allowCreate={true}
/>
\`\`\`

**Props**:
- value?: Tag[] - Selected tags
- onChange?: (tags: Tag[]) => void - Change handler
- onSearchTags?: (query: string) => Promise<Tag[]> - Search callback
- onCreateTag?: (name: string) => Promise<Tag> - Create callback
- disabled?: boolean - Disable input
- placeholder?: string - Placeholder text
- maxTags?: number - Limit number of tags
- allowCreate?: boolean - Allow creating new tags
- className?: string - Additional CSS classes

**Features**:
- Type to search
- Enter to add
- Backspace to remove
- Copy-paste CSV
- Keyboard navigation
- Accessible

**Examples**:
- Basic usage with static tags
- With API integration
- In form with validation
- Read-only mode

## TagBadge Component

**File**: `skillmeat/web/components/ui/badge.tsx`

**Purpose**: Display tag as colored badge with optional remove button

**Usage**:
\`\`\`tsx
import { Badge } from '@/components/ui/badge';

<Badge bgColor={tag.color} onRemove={() => removeTag(tag.id)}>
  {tag.name}
</Badge>
\`\`\`

**Props**:
- variant?: 'default' | 'secondary' | 'destructive' | 'outline'
- bgColor?: string - Hex color background
- onRemove?: () => void - Remove callback
- removable?: boolean - Show remove button
- children: React.ReactNode - Badge text
- className?: string - Additional CSS classes

**Styling**:
- Border radius: 6px
- Padding: 2.5px vertical, 4px horizontal
- Font size: xs, font-medium
- Colors: Auto white/black text based on background
- Contrast: 4.5:1 minimum

## TagFilterPopover Component

**File**: `skillmeat/web/components/TagFilterPopover.tsx`

**Purpose**: Multi-select filter popover showing all tags with counts

**Usage**:
\`\`\`tsx
import { TagFilterPopover } from '@/components/TagFilterPopover';

<TagFilterPopover
  tags={allTags}
  selectedTagIds={selectedIds}
  onTagsChange={setSelectedIds}
/>
\`\`\`

**Props**:
- tags: TagWithCount[] - Available tags with counts
- selectedTagIds: number[] - Currently selected IDs
- onTagsChange: (ids: number[]) => void - Change handler
- isLoading?: boolean - Loading state
- error?: string - Error message
- trigger?: React.ReactNode - Custom trigger button

**Features**:
- Search tags
- Multi-select
- Show artifact counts
- Select All / Clear All
- Keyboard accessible")
```

### DOC-003: User Guide (1 pt)

```markdown
Task("documentation-writer", "DOC-003: Create tag usage guide for end users

File: docs/guides/tags-user-guide.md

# Tag System - User Guide

## What are Tags?

Tags are labels you can add to artifacts to organize, categorize, and search them. Tags are global across your collection, meaning you can reuse the same tag on multiple artifacts.

**Examples**:
- Language tags: python, javascript, rust
- Framework tags: fastapi, react, vue
- Category tags: backend, frontend, testing, documentation
- Status tags: wip, deprecated, stable

## Creating Tags

### Option 1: While Editing an Artifact

1. Open artifact details
2. Click 'Edit' button
3. Scroll to 'Tags' section
4. Click in tags field
5. Type tag name (existing tags appear as suggestions)
6. Press Enter to add
7. Repeat for more tags
8. Click 'Save' to persist

### Option 2: Create New Tag

While in the tags field:
1. Type new tag name that doesn't exist
2. Press Enter (shows 'Create tag')
3. Tag is created and added immediately

## Adding Tags to Artifacts

**Method 1**: Edit mode (see above)

**Method 2**: In artifact details
1. Navigate to artifact
2. Tags displayed with 'Edit' button
3. Click 'Edit' to add/remove tags

**Method 3**: Bulk operations (planned for future)

## Searching by Tags

### Filter by Tag

1. On artifact list or collection page
2. Click 'Tags' filter button
3. Popover opens showing all tags with counts
4. Click checkbox to select tags (AND logic)
5. List updates to show only artifacts with selected tags

### Search Bar

Use tag names in search:
1. Search: 'python fastapi'
2. Shows artifacts with these words in name/description
3. Combine with tag filter for more precision

## Organizing with Tags

### Best Practices

- Use lowercase names (e.g., 'python' not 'Python')
- Keep names short and memorable (e.g., 'async' not 'asynchronous')
- Use consistent naming (e.g., 'backend' not 'back-end')
- Create tags for your use cases
- Share tag naming conventions with team

### Examples

**By Technology**:
- Languages: python, javascript, rust
- Frameworks: fastapi, react, django
- Tools: docker, kubernetes, postgres

**By Feature**:
- frontend, backend, database
- api, cli, library

**By Status**:
- stable, wip, deprecated, archived

**By Team**:
- team-a, team-b (if shared collection)

## Filtering & Analytics

### Tag Filter View

Shows:
- All available tags
- Artifact count for each tag
- Search to narrow list
- Bulk select/deselect
- Active filters applied

### Tag Metrics (Dashboard)

Dashboard displays:
- Total tag count
- Most used tags
- Top 10 tags by artifact count
- Recent tags created
- Tag usage trends

## Keyboard Shortcuts

In tag input:
- Type: Search for tags
- Enter: Add selected or create new
- Backspace (on empty): Remove last tag
- Escape: Close suggestions
- Arrow Up/Down: Navigate suggestions
- Delete: Remove selected

In filter popover:
- Tab: Navigate elements
- Space: Toggle checkbox
- Escape: Close popover

## Tips & Tricks

### Copy-Paste Multiple Tags

In tags field, paste comma-separated values:
- Paste: 'python, fastapi, async'
- Creates all three tags at once

### Tag Colors

Tags have assigned colors for visual distinction. Colors:
- Automatically assigned on creation
- Help quickly identify tags visually
- Used in artifact listings

### Finding Artifacts

1. Open collection
2. Click 'Tags' filter
3. Select tags (multiple selections)
4. See filtered list update in real-time
5. Click tag badge in artifact detail to filter by that tag

## Common Questions

**Q: Can I edit a tag name?**
A: Yes, click 'Edit' next to tag or in artifact details

**Q: Can I delete a tag?**
A: Yes, deletion removes tag from all artifacts

**Q: Can I create private tags?**
A: Tags are currently global to your collection (planned: team/project scopes)

**Q: How many tags can I add?**
A: No limit, but UI works best with 1-10 tags per artifact

**Q: Are tags case-sensitive?**
A: No, search is case-insensitive")
```

### DOC-004: Developer Guide (1 pt)

```markdown
Task("documentation-writer", "DOC-004: Create developer documentation for tag system

File: docs/guides/tags-architecture.md

# Tag System - Developer Guide

## Architecture Overview

The tag system is built with a many-to-many relationship between Artifacts and Tags:

\`\`\`
Artifacts --M:M--> Tags
           via artifact_tags junction table
\`\`\`

### Database Layer

**Tables**:
- tags: Core tag entity
- artifact_tags: M2M association

**Models**:
- skillmeat/storage/models/tag.py

### Service Layer

**Services**:
- TagService: Tag CRUD, search, management
- ArtifactTagService: Artifact-tag associations, filtering

**File**: skillmeat/core/services/

### API Layer

**Router**: skillmeat/api/app/routers/tags.py

**Endpoints**:
- GET /api/v1/tags
- POST /api/v1/tags
- PUT /api/v1/tags/{id}
- DELETE /api/v1/tags/{id}
- GET /api/v1/artifacts/{id}/tags
- POST /api/v1/artifacts/{id}/tags/{tag_id}
- DELETE /api/v1/artifacts/{id}/tags/{tag_id}

### Frontend Layer

**Components**:
- TagInput: Input component with search/create
- TagBadge: Display component
- TagFilterPopover: Filter UI
- useArtifactTags: React hook

**Files**:
- skillmeat/web/components/ui/tag-input.tsx
- skillmeat/web/components/ui/badge.tsx
- skillmeat/web/components/TagFilterPopover.tsx
- skillmeat/web/hooks/use-artifacts.ts

## Implementation Patterns

### Adding Tags to New Entities (Future)

To extend tags to new entities (e.g., Commands, Agents):

1. **Database**: Create M2M association table (entity_tags)
2. **Repository**: Add tag CRUD methods for new entity
3. **Service**: Create EntityTagService
4. **API**: Add router endpoints
5. **Frontend**: Add tag input component to entity editor

### Extending Tag Features

**Add tag templates** (tag sets for quick application):
1. Create TagTemplate model
2. Add 'Apply template' option in UI
3. API endpoint to fetch templates

**Add tag-based access control**:
1. Extend tag model with scope (public/private)
2. Add permission checks in API layer
3. Update UI to show accessible tags only

**Add tag analytics**:
1. Create analytics queries in repository
2. Add metrics endpoints in API
3. Add dashboard widgets in frontend

## Best Practices

### Tag Naming

- Enforce lowercase in validation
- Use slug for URLs/identifiers
- Strip whitespace on creation
- Prevent duplicates (case-insensitive)

### Performance

- Index artifact_tags on both FKs
- Use cursor pagination for large lists
- Cache tag counts if needed
- Batch tag operations where possible

### Error Handling

- 404: Resource not found
- 409: Duplicate tag name
- 422: Invalid data (validation)
- 500: Server error with logging

### Testing

- Unit test: Service layer logic
- Integration test: API endpoints
- Component test: React components
- E2E test: Complete workflows
- A11y test: Accessibility compliance

## Integration Points

### With Artifacts

Tags are associated via M2M table:
- On artifact creation: Tags passed in request
- On artifact update: Tags replaced with new set
- On artifact deletion: Cascade delete associations

### With Search

Tag queries integrated with artifact search:
- Filter by tags + search terms
- URL params: ?tag_ids=1,2,3&search=query
- Backend applies both filters (AND logic)

### With Analytics

Tag metrics available on dashboard:
- Tag distribution chart
- Most used tags
- Recently created tags
- Artifact coverage per tag

## Database Migrations

Tag schema added in single migration:
- Tags table creation
- artifact_tags junction table
- All indexes
- Foreign keys with CASCADE delete

Rollback removes all tag-related tables.

## Security Considerations

**Current**:
- No authentication/authorization
- All users see all tags
- All users can create/edit/delete tags

**Future Enhancements**:
- Role-based access control
- Private tags (user/team scoped)
- Audit logging for tag changes
- Tag naming validation/filters

## Monitoring & Observability

**Logging**:
- INFO: Tag CRUD operations
- WARNING: Tag deletions
- ERROR: Constraint violations, DB errors

**Tracing**:
- OpenTelemetry spans for service methods
- Attributes: tag.id, tag.name, artifact.id

**Metrics** (planned):
- Tags created per period
- Most popular tags
- Tag query latency

## Useful Queries

### Find artifacts with specific tags (AND logic)

\`\`\`python
from sqlalchemy import and_, select
from skillmeat.storage.models import Artifact, Tag

# Artifacts tagged with BOTH python AND fastapi
tag_ids = [1, 2]  # python, fastapi

subquery = select(
    distinct(artifact_tags.c.artifact_id)
).where(
    artifact_tags.c.tag_id.in_(tag_ids)
).group_by(artifact_tags.c.artifact_id).having(
    func.count(distinct(artifact_tags.c.tag_id)) == len(tag_ids)
)

artifacts = session.query(Artifact).filter(
    Artifact.id.in_(subquery)
).all()
\`\`\`

### Get tag usage statistics

\`\`\`python
from sqlalchemy import func

tag_counts = session.query(
    Tag,
    func.count(artifact_tags.c.artifact_id).label('count')
).outerjoin(
    artifact_tags
).group_by(Tag.id).order_by(
    desc('count')
).all()
\`\`\`

## Resources

- API Documentation: `docs/api/tags.md`
- Component Documentation: `docs/components/`
- Implementation Plan: `docs/project_plans/implementation_plans/.../tags-refactor-v1.md`
- Database Models: `skillmeat/storage/models/tag.py`
- Service Layer: `skillmeat/core/services/`")
```

---

## Quality Gates

### Phase 7 - Testing
- [ ] Code coverage >80% (backend and frontend)
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] All component tests passing
- [ ] E2E tests passing
- [ ] Accessibility compliance validated (WCAG 2.1 AA)
- [ ] CI/CD pipeline green

### Phase 8 - Documentation
- [ ] API documentation complete and accurate
- [ ] Component documentation complete
- [ ] User guides clear and comprehensive
- [ ] Developer guides enable extension
- [ ] All documentation merged to main

---

## Dependencies Summary

**Testing Phase**:
- TEST-001 → TEST-002 (unit tests → integration tests)
- TEST-003 can run in parallel with TEST-002
- TEST-004 depends on TEST-003
- TEST-005 depends on TEST-004

**Documentation Phase**:
- All doc tasks depend on TEST-005 (implementation complete)
- Doc tasks can run in parallel (DOC-001 through DOC-004)

---

## Orchestration Quick Reference

### Batch 1-4: Testing (Sequential, 2 days)

```markdown
Task("python-backend-engineer", "TEST-001-TEST-002: Backend testing

TEST-001: Backend unit tests (2 pts)
- Test tag service, repository, schemas
- >80% coverage required
- All CRUD operations, edge cases
Files: tests/unit/services/, tests/unit/repositories/

TEST-002: API integration tests (2 pts)
- Test all tag endpoints
- Test error handling and status codes
- >80% coverage required
Files: tests/integration/routers/

Run: pytest tests/unit/ tests/integration/")
```

```markdown
Task("frontend-developer", "TEST-003-TEST-004: Frontend testing

TEST-003: Component tests (2 pts)
- Test TagInput, Badge, Filter components
- User interactions, state changes
- >80% coverage required
Files: tests/components/

TEST-004: E2E tests (2 pts)
- Complete workflows from UI to API
- Tag creation → artifact tagging → filtering
- Keyboard and accessibility workflows
Files: tests/e2e/

Run: npm test
     npx playwright test")
```

```markdown
Task("web-accessibility-checker", "TEST-005: Accessibility compliance

TEST-005: WCAG 2.1 AA validation (1 pt)
- Automated testing with axe-core
- Manual testing with keyboard/screen reader
- Test report with compliance checklist
- All critical issues resolved

Coverage:
- Keyboard navigation: Full support
- Screen readers: All content announced
- Color contrast: 4.5:1 minimum
- Focus management: Logical tab order
- Mobile/touch: 44px+ targets

Run: npm run test:a11y")
```

### Batch 5-8: Documentation (Parallel, 1 day)

```markdown
Task("api-documenter", "DOC-001: API documentation

File: docs/api/tags.md

Content:
- Endpoint descriptions
- Request/response examples
- Query parameters
- Error codes
- Common use cases
- Rate limiting (if applicable)")
```

```markdown
Task("documentation-writer", "DOC-002-DOC-004: Component and user docs

DOC-002: Component documentation (1 pt)
- TagInput usage and props
- TagBadge styling and variants
- TagFilterPopover interaction
Files: docs/components/

DOC-003: User guide (1 pt)
- How to create tags
- How to add tags to artifacts
- How to filter by tags
- Best practices and tips
File: docs/guides/tags-user-guide.md

DOC-004: Developer guide (1 pt)
- Architecture overview
- Extending tags to new entities
- Performance considerations
- Testing strategies
- Database queries
File: docs/guides/tags-architecture.md")
```

---

## Context Files for Implementation

**Testing Framework**:
- Backend: pytest with SQLAlchemy test fixtures
- Frontend: Jest + React Testing Library
- E2E: Playwright or Cypress
- Accessibility: axe-core + manual testing

**Documentation Tools**:
- Markdown for all docs
- Code examples with syntax highlighting
- API examples with curl/Python/JavaScript
- Screenshots/diagrams if needed

**Related Files**:
- `.claude/rules/debugging.md` - Testing patterns
- `skillmeat/api/CLAUDE.md` - Backend testing guidelines
- `skillmeat/web/CLAUDE.md` - Frontend testing guidelines
