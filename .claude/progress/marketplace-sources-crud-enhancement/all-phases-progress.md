---
prd: "marketplace-sources-crud-enhancement"
version: "1.0.0"
created_at: "2025-12-12T00:00:00Z"
total_points: 86
completed_points: 86
completion_percentage: 100%

phases:
  - id: 1
    name: "Database & Backend Schema"
    points: 11
    status: "completed"
    tasks: ["SCHEMA-001", "SCHEMA-002", "SCHEMA-003", "SCHEMA-004", "SCHEMA-005"]

  - id: 2
    name: "Backend API Enhancement"
    points: 11
    status: "completed"
    tasks: ["API-001", "API-002", "API-003", "API-004", "API-005", "API-006"]

  - id: 3
    name: "Frontend Type Updates"
    points: 5
    status: "completed"
    tasks: ["TYPES-001", "TYPES-002", "TYPES-003", "TYPES-004"]

  - id: 4
    name: "UI Components Development"
    points: 28
    status: "completed"
    tasks: ["UI-001", "UI-002", "UI-003", "UI-004", "UI-005", "UI-006", "UI-007", "UI-008", "UI-009", "UI-010"]

  - id: 5
    name: "Testing & QA"
    points: 25
    status: "completed"
    tasks: ["TEST-001", "TEST-002", "TEST-003", "TEST-004", "TEST-005", "TEST-006", "TEST-007", "TEST-008", "TEST-009"]

  - id: 6
    name: "Documentation"
    points: 6
    status: "completed"
    tasks: ["DOCS-001", "DOCS-002", "DOCS-003", "DOCS-004"]

tasks:
  # Phase 1: Database & Backend Schema
  - id: "SCHEMA-001"
    phase: 1
    name: "Add description/notes to MarketplaceSource Model"
    points: 3
    status: "completed"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    description: |
      Add `description` and `notes` fields to MarketplaceSource SQLAlchemy model.
      - description: nullable String(500) for marketplace listing descriptions
      - notes: nullable String(1000) for internal user notes
    files:
      - "skillmeat/api/app/models/marketplace_source.py"

  - id: "SCHEMA-002"
    phase: 1
    name: "Create Alembic Migration"
    points: 2
    status: "completed"
    assigned_to: ["data-layer-expert"]
    dependencies: ["SCHEMA-001"]
    description: |
      Create Alembic migration to add description and notes columns to marketplace_sources table.
      - Auto-generate migration or write manually
      - Ensure columns are nullable with defaults
      - Test migration up and down
    files:
      - "skillmeat/api/alembic/versions/"

  - id: "SCHEMA-003"
    phase: 1
    name: "Update SourceResponse Schema"
    points: 2
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SCHEMA-001"]
    description: |
      Update Pydantic SourceResponse schema to include description and notes fields.
      - Add description: str | None field
      - Add notes: str | None field
      - Include in OpenAPI documentation
    files:
      - "skillmeat/api/app/schemas/source.py"

  - id: "SCHEMA-004"
    phase: 1
    name: "Update CreateSourceRequest Schema"
    points: 2
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SCHEMA-001"]
    description: |
      Update CreateSourceRequest Pydantic schema for POST endpoints.
      - Add description: str | None field (optional)
      - Add notes: str | None field (optional)
      - Add field validators for max length (500 for description, 1000 for notes)
    files:
      - "skillmeat/api/app/schemas/source.py"

  - id: "SCHEMA-005"
    phase: 1
    name: "Create UpdateSourceRequest DTO"
    points: 2
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SCHEMA-001"]
    description: |
      Create new UpdateSourceRequest Pydantic schema for PATCH endpoints.
      - Make all fields optional (partial updates)
      - Include description, notes, and any other patchable fields
      - Add field validators for max length
    files:
      - "skillmeat/api/app/schemas/source.py"

  # Phase 2: Backend API Enhancement
  - id: "API-001"
    phase: 2
    name: "Enhance POST /marketplace/sources"
    points: 2
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SCHEMA-005"]
    description: |
      Update POST endpoint to accept and persist description and notes.
      - Use CreateSourceRequest schema with new fields
      - Map request fields to model
      - Return updated SourceResponse
    files:
      - "skillmeat/api/app/routers/marketplace.py"

  - id: "API-002"
    phase: 2
    name: "Enhance PATCH /marketplace/sources/{id}"
    points: 3
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SCHEMA-005"]
    description: |
      Implement PATCH endpoint for partial updates to marketplace sources.
      - Accept UpdateSourceRequest with optional fields
      - Only update provided fields (respect PATCH semantics)
      - Return updated SourceResponse
      - Include 404 handling for non-existent sources
    files:
      - "skillmeat/api/app/routers/marketplace.py"

  - id: "API-003"
    phase: 2
    name: "Verify DELETE /marketplace/sources/{id}"
    points: 1
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SCHEMA-003"]
    description: |
      Verify existing DELETE endpoint works correctly.
      - Check implementation exists and handles 404s
      - Verify response status codes (204 No Content)
      - Confirm proper cleanup of related records if needed
    files:
      - "skillmeat/api/app/routers/marketplace.py"

  - id: "API-004"
    phase: 2
    name: "Add Field Validation"
    points: 2
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SCHEMA-005"]
    description: |
      Add comprehensive field validation to all schemas.
      - Validate description max 500 chars
      - Validate notes max 1000 chars
      - Prevent empty strings (use None instead)
      - Add custom validators using Pydantic
    files:
      - "skillmeat/api/app/schemas/source.py"

  - id: "API-005"
    phase: 2
    name: "Test PATCH/DELETE Integration"
    points: 2
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-002", "API-003"]
    description: |
      Integration tests for PATCH and DELETE endpoints.
      - Test PATCH updates specific fields only
      - Test PATCH with invalid data
      - Test DELETE returns 204
      - Test DELETE with non-existent ID returns 404
    files:
      - "skillmeat/api/tests/test_marketplace_api.py"

  - id: "API-006"
    phase: 2
    name: "Regenerate TypeScript SDK"
    points: 1
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-002"]
    description: |
      Regenerate TypeScript SDK from updated OpenAPI spec.
      - Run openapi-generator or similar tool
      - Commit generated types to web/api/generated/
      - Verify SourceResponse, CreateSourceRequest, UpdateSourceRequest are updated
    files:
      - "skillmeat/web/api/generated/"

  # Phase 3: Frontend Type Updates
  - id: "TYPES-001"
    phase: 3
    name: "Extend GitHubSource Type"
    points: 1
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["API-006"]
    description: |
      Update GitHubSource TypeScript type to include description and notes.
      - Add description?: string field
      - Add notes?: string field
      - Update imports/exports
    files:
      - "skillmeat/web/api/types/marketplace.ts"

  - id: "TYPES-002"
    phase: 3
    name: "Extend CreateSourceRequest Type"
    points: 1
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["API-006"]
    description: |
      Update CreateSourceRequest TypeScript type.
      - Add description?: string field
      - Add notes?: string field
      - Import from generated SDK types if available
    files:
      - "skillmeat/web/api/types/marketplace.ts"

  - id: "TYPES-003"
    phase: 3
    name: "Create UpdateSourceRequest Type"
    points: 1
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["API-006"]
    description: |
      Create new UpdateSourceRequest TypeScript type for PATCH operations.
      - Make all fields optional (id?, name?, description?, notes?)
      - Re-export from main types file
    files:
      - "skillmeat/web/api/types/marketplace.ts"

  - id: "TYPES-004"
    phase: 3
    name: "Update useMarketplaceSources Hook"
    points: 2
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TYPES-003"]
    description: |
      Update React hook to support edit and delete operations.
      - Add updateSource(id, data: UpdateSourceRequest) function
      - Add deleteSource(id) function
      - Handle loading and error states
      - Return updated types
    files:
      - "skillmeat/web/hooks/useMarketplaceSources.ts"

  # Phase 4: UI Components Development
  - id: "UI-001"
    phase: 4
    name: "Create DeleteConfirmationDialog"
    points: 3
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TYPES-004"]
    description: |
      Create reusable DeleteConfirmationDialog component using Radix/shadcn.
      - Show source name in confirmation
      - Destructive action button (red)
      - Loading state during deletion
      - Error handling with user feedback
    files:
      - "skillmeat/web/components/DeleteConfirmationDialog.tsx"

  - id: "UI-002"
    phase: 4
    name: "Update AddSourceModal → EditSourceModal"
    points: 4
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TYPES-004"]
    description: |
      Convert AddSourceModal to support both add and edit modes.
      - Accept optional source prop for edit mode
      - Render form fields for description and notes
      - Add textarea for notes with character counter
      - Show different title/button labels for edit vs add
      - Call updateSource hook for edit, createSource for add
    files:
      - "skillmeat/web/components/SourceModal.tsx"

  - id: "UI-003"
    phase: 4
    name: "Add Hover Buttons to SourceCard"
    points: 3
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-002"]
    description: |
      Add edit and delete action buttons to SourceCard component.
      - Show on hover with smooth animation
      - Edit button (pencil icon) opens EditSourceModal
      - Delete button (trash icon) opens DeleteConfirmationDialog
      - Button positioning and styling
    files:
      - "skillmeat/web/components/SourceCard.tsx"

  - id: "UI-004"
    phase: 4
    name: "Add Action Buttons to Detail Page"
    points: 3
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-002"]
    description: |
      Add edit and delete buttons to source detail page.
      - Edit button in header or toolbar area
      - Delete button with confirmation
      - Loading states during operations
      - Redirect after delete
    files:
      - "skillmeat/web/app/marketplace/[id]/page.tsx"

  - id: "UI-005"
    phase: 4
    name: "Create Notes Section Component"
    points: 2
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TYPES-001"]
    description: |
      Create component to display notes with styling.
      - Show notes in formatted section on detail page
      - Handle empty/null notes gracefully
      - Include label "Notes" or "Internal Notes"
      - Markdown support optional
    files:
      - "skillmeat/web/components/NotesSection.tsx"

  - id: "UI-006"
    phase: 4
    name: "Create Description Display Component"
    points: 2
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TYPES-001"]
    description: |
      Create component to display description.
      - Show description in formatted section on detail page
      - Handle empty/null descriptions gracefully
      - Include label "Description"
      - Consider markdown or rich text support
    files:
      - "skillmeat/web/components/DescriptionSection.tsx"

  - id: "UI-007"
    phase: 4
    name: "Make Artifacts Pane Scrollable"
    points: 2
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-005"]
    description: |
      Fix scrolling behavior on detail page when content grows.
      - Make artifacts pane scrollable independently
      - Prevent page from becoming too tall
      - Test with long notes and descriptions
    files:
      - "skillmeat/web/app/marketplace/[id]/page.tsx"

  - id: "UI-008"
    phase: 4
    name: "Wire Delete Dialog to SourceCard"
    points: 2
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-001", "UI-003"]
    description: |
      Connect DeleteConfirmationDialog to SourceCard delete button.
      - Handle successful deletion
      - Refresh source list after deletion
      - Show error messages if delete fails
    files:
      - "skillmeat/web/components/SourceCard.tsx"

  - id: "UI-009"
    phase: 4
    name: "Wire Edit Modal to SourceCard"
    points: 2
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-002", "UI-003"]
    description: |
      Connect EditSourceModal to SourceCard edit button.
      - Pass source data to modal for editing
      - Handle successful update
      - Refresh source data after edit
      - Show error messages if update fails
    files:
      - "skillmeat/web/components/SourceCard.tsx"

  - id: "UI-010"
    phase: 4
    name: "Update Detail Page Wiring"
    points: 3
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-004", "UI-005", "UI-006"]
    description: |
      Wire all components on source detail page.
      - Display description using DescriptionSection
      - Display notes using NotesSection
      - Connect edit button to EditSourceModal
      - Connect delete button to DeleteConfirmationDialog
      - Handle navigation after delete
      - Test all interactions
    files:
      - "skillmeat/web/app/marketplace/[id]/page.tsx"

  # Phase 5: Testing & QA
  - id: "TEST-001"
    phase: 5
    name: "Unit Tests - Backend Schemas"
    points: 3
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SCHEMA-001"]
    description: |
      Write unit tests for updated schema models and validators.
      - Test description validation (max 500 chars)
      - Test notes validation (max 1000 chars)
      - Test optional field handling
      - Test schema serialization
    files:
      - "skillmeat/api/tests/test_schemas.py"

  - id: "TEST-002"
    phase: 5
    name: "Unit Tests - API Endpoints"
    points: 4
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-002"]
    description: |
      Write unit tests for API endpoints.
      - Test POST with description and notes
      - Test PATCH with partial updates
      - Test PATCH with invalid data
      - Test DELETE success and 404 scenarios
    files:
      - "skillmeat/api/tests/test_marketplace_api.py"

  - id: "TEST-003"
    phase: 5
    name: "Unit Tests - Frontend Components"
    points: 4
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-010"]
    description: |
      Write unit tests for React components using Vitest/React Testing Library.
      - Test DeleteConfirmationDialog rendering and interactions
      - Test EditSourceModal form validation
      - Test SourceCard button rendering and click handlers
      - Test NotesSection and DescriptionSection display
    files:
      - "skillmeat/web/__tests__/components/"

  - id: "TEST-004"
    phase: 5
    name: "Integration Tests - Edit Flow"
    points: 2
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-002"]
    description: |
      Test end-to-end edit flow in backend.
      - Create source → Update via PATCH → Verify changes
      - Test partial updates (update only notes, then only description)
      - Test concurrent update handling
    files:
      - "skillmeat/api/tests/test_integration.py"

  - id: "TEST-005"
    phase: 5
    name: "Integration Tests - Delete Flow"
    points: 2
    status: "completed"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["API-003"]
    description: |
      Test end-to-end delete flow in backend.
      - Create source → Delete → Verify gone
      - Test cascade deletes if applicable
      - Test foreign key constraints
    files:
      - "skillmeat/api/tests/test_integration.py"

  - id: "TEST-006"
    phase: 5
    name: "E2E Tests - Edit Source"
    points: 3
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-010"]
    description: |
      End-to-end tests using Playwright or similar.
      - Navigate to source detail page
      - Click edit button
      - Fill form with new description/notes
      - Submit and verify updates
    files:
      - "skillmeat/web/e2e/tests/"

  - id: "TEST-007"
    phase: 5
    name: "E2E Tests - Delete Source"
    points: 3
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-008"]
    description: |
      End-to-end tests for delete flow.
      - Navigate to source card
      - Click delete button
      - Confirm deletion in dialog
      - Verify source is removed from list
    files:
      - "skillmeat/web/e2e/tests/"

  - id: "TEST-008"
    phase: 5
    name: "Accessibility Testing"
    points: 2
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-010"]
    description: |
      Verify accessibility compliance.
      - Test with screen readers
      - Test keyboard navigation (Tab, Enter, Escape)
      - Verify ARIA labels on buttons and dialogs
      - Check color contrast
    files:
      - "skillmeat/web/__tests__/"

  - id: "TEST-009"
    phase: 5
    name: "Visual Regression Testing"
    points: 2
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UI-010"]
    description: |
      Visual regression tests with Percy or similar.
      - Capture baseline screenshots of marketplace pages
      - Verify edit/delete buttons render correctly
      - Verify responsive design on mobile
    files:
      - "skillmeat/web/"

  # Phase 6: Documentation
  - id: "DOCS-001"
    phase: 6
    name: "API Documentation"
    points: 2
    status: "completed"
    assigned_to: ["documentation-writer"]
    dependencies: ["API-006"]
    description: |
      Update API documentation for new/updated endpoints.
      - Document PATCH /marketplace/sources/{id} endpoint
      - Include request/response examples
      - Document field validation rules
      - Include error response examples
    files:
      - "skillmeat/api/docs/"
      - "skillmeat/api/README.md"

  - id: "DOCS-002"
    phase: 6
    name: "Component Documentation"
    points: 2
    status: "completed"
    assigned_to: ["documentation-writer"]
    dependencies: ["UI-010"]
    description: |
      Document new UI components.
      - DeleteConfirmationDialog usage and API
      - EditSourceModal props and callbacks
      - NotesSection and DescriptionSection
      - Include Storybook stories if applicable
    files:
      - "skillmeat/web/docs/"
      - "skillmeat/web/README.md"

  - id: "DOCS-003"
    phase: 6
    name: "User Guide Update"
    points: 1
    status: "completed"
    assigned_to: ["documentation-writer"]
    dependencies: ["UI-010"]
    description: |
      Update user-facing documentation.
      - Add sections for editing marketplace sources
      - Add sections for deleting sources
      - Include screenshots or GIFs
      - Update marketplace feature overview
    files:
      - "skillmeat/docs/user-guide/"

  - id: "DOCS-004"
    phase: 6
    name: "Release Notes"
    points: 1
    status: "completed"
    assigned_to: ["documentation-writer"]
    dependencies: ["DOCS-001"]
    description: |
      Create release notes for this feature.
      - Summarize new capabilities (edit, delete, description, notes)
      - List breaking changes if any
      - Link to related documentation
      - Include upgrade instructions if needed
    files:
      - "skillmeat/CHANGELOG.md"
      - "skillmeat/RELEASES.md"

parallelization:
  batch_1:
    - "SCHEMA-001"
    description: "No dependencies - kick off Phase 1"

  batch_2:
    - "SCHEMA-002"
    - "SCHEMA-003"
    - "SCHEMA-004"
    - "SCHEMA-005"
    description: "All depend on SCHEMA-001 - Run in parallel"

  batch_3:
    - "API-001"
    - "API-002"
    - "API-003"
    - "API-004"
    description: "Phase 2 core tasks - All depend on Phase 1 schemas"

  batch_4:
    - "API-005"
    - "API-006"
    description: "Backend integration and SDK generation - Depend on API-002/003"

  batch_5:
    - "TYPES-001"
    - "TYPES-002"
    - "TYPES-003"
    description: "Frontend types - Depend on API-006, can run in parallel"

  batch_6:
    - "TYPES-004"
    description: "Hook update - Depends on TYPES-003"

  batch_7:
    - "UI-001"
    - "UI-002"
    - "UI-005"
    - "UI-006"
    description: "Core UI components - Depend on TYPES-001/004, run in parallel"

  batch_8:
    - "UI-003"
    - "UI-004"
    - "UI-007"
    description: "Component enhancements - Depend on UI-002/005"

  batch_9:
    - "UI-008"
    - "UI-009"
    - "UI-010"
    description: "Wiring and integration - Depend on batch_8 components"

  batch_10:
    - "TEST-001"
    - "TEST-002"
    - "TEST-004"
    - "TEST-005"
    description: "Backend tests - Run in parallel after Phase 2"

  batch_11:
    - "TEST-003"
    - "TEST-006"
    - "TEST-007"
    - "TEST-008"
    - "TEST-009"
    description: "Frontend tests - Run in parallel after UI-010"

  batch_12:
    - "DOCS-001"
    - "DOCS-002"
    - "DOCS-003"
    description: "Documentation - Run in parallel"

  batch_13:
    - "DOCS-004"
    description: "Release notes - Last documentation task"

---

# Marketplace Sources CRUD Enhancement - All Phases Progress

**PRD**: marketplace-sources-crud-enhancement
**Version**: 1.0.0
**Created**: 2025-12-12
**Total Points**: 86
**Completed**: 86/86 (100%)

---

## Overview

Complete CRUD enhancement for marketplace sources with edit (PATCH) and delete (DELETE) capabilities, updated data model with description/notes fields, frontend components, and comprehensive testing.

**Objectives**:
- Enable users to edit marketplace source descriptions and add internal notes
- Implement DELETE functionality for source removal
- Extend data model with description and notes fields
- Build production-ready UI components with Radix/shadcn
- Comprehensive test coverage (unit, integration, E2E)
- Full documentation and release notes

---

## Phase 1: Database & Backend Schema (11 pts)

**Status**: completed
**Goal**: Extend MarketplaceSource model with description and notes fields; create migration and update all Pydantic schemas.

### Tasks

| ID | Name | Points | Assigned To | Status |
|---|---|---|---|---|
| SCHEMA-001 | Add description/notes to MarketplaceSource Model | 3 | data-layer-expert | completed |
| SCHEMA-002 | Create Alembic Migration | 2 | data-layer-expert | completed |
| SCHEMA-003 | Update SourceResponse Schema | 2 | python-backend-engineer | completed |
| SCHEMA-004 | Update CreateSourceRequest Schema | 2 | python-backend-engineer | completed |
| SCHEMA-005 | Create UpdateSourceRequest DTO | 2 | python-backend-engineer | completed |

**Key Files**:
- `skillmeat/api/app/models/marketplace_source.py` - Model definition
- `skillmeat/api/alembic/versions/` - Migration files
- `skillmeat/api/app/schemas/source.py` - Pydantic schemas

---

## Phase 2: Backend API Enhancement (11 pts)

**Status**: completed
**Goal**: Implement/enhance POST, PATCH, DELETE endpoints with proper validation and error handling.

### Tasks

| ID | Name | Points | Assigned To | Status |
|---|---|---|---|---|
| API-001 | Enhance POST /marketplace/sources | 2 | python-backend-engineer | completed |
| API-002 | Enhance PATCH /marketplace/sources/{id} | 3 | python-backend-engineer | completed |
| API-003 | Verify DELETE /marketplace/sources/{id} | 1 | python-backend-engineer | completed |
| API-004 | Add Field Validation | 2 | python-backend-engineer | completed |
| API-005 | Test PATCH/DELETE Integration | 2 | python-backend-engineer | completed |
| API-006 | Regenerate TypeScript SDK | 1 | python-backend-engineer | completed |

**Key Files**:
- `skillmeat/api/app/routers/marketplace.py` - API routes
- `skillmeat/api/tests/test_marketplace_api.py` - Tests
- `skillmeat/web/api/generated/` - Generated TypeScript SDK

---

## Phase 3: Frontend Type Updates (5 pts)

**Status**: completed
**Goal**: Update TypeScript types to match backend changes and support edit/delete operations.

### Tasks

| ID | Name | Points | Assigned To | Status |
|---|---|---|---|---|
| TYPES-001 | Extend GitHubSource Type | 1 | ui-engineer-enhanced | completed |
| TYPES-002 | Extend CreateSourceRequest Type | 1 | ui-engineer-enhanced | completed |
| TYPES-003 | Create UpdateSourceRequest Type | 1 | ui-engineer-enhanced | completed |
| TYPES-004 | Update useMarketplaceSources Hook | 2 | ui-engineer-enhanced | completed |

**Key Files**:
- `skillmeat/web/api/types/marketplace.ts` - Type definitions
- `skillmeat/web/hooks/useMarketplaceSources.ts` - React hooks

---

## Phase 4: UI Components Development (28 pts)

**Status**: completed
**Goal**: Build production-grade UI components for edit/delete functionality with proper state management and error handling.

### Tasks

| ID | Name | Points | Assigned To | Status |
|---|---|---|---|---|
| UI-001 | Create DeleteConfirmationDialog | 3 | ui-engineer-enhanced | completed |
| UI-002 | Update AddSourceModal → EditSourceModal | 4 | ui-engineer-enhanced | completed |
| UI-003 | Add Hover Buttons to SourceCard | 3 | ui-engineer-enhanced | completed |
| UI-004 | Add Action Buttons to Detail Page | 3 | ui-engineer-enhanced | completed |
| UI-005 | Create Notes Section Component | 2 | ui-engineer-enhanced | completed |
| UI-006 | Create Description Display Component | 2 | ui-engineer-enhanced | completed |
| UI-007 | Make Artifacts Pane Scrollable | 2 | ui-engineer-enhanced | completed |
| UI-008 | Wire Delete Dialog to SourceCard | 2 | ui-engineer-enhanced | completed |
| UI-009 | Wire Edit Modal to SourceCard | 2 | ui-engineer-enhanced | completed |
| UI-010 | Update Detail Page Wiring | 3 | ui-engineer-enhanced | completed |

**Key Files**:
- `skillmeat/web/components/` - React components
- `skillmeat/web/app/marketplace/` - App pages
- `skillmeat/web/hooks/` - React hooks

---

## Phase 5: Testing & QA (25 pts)

**Status**: completed
**Goal**: Comprehensive test coverage across unit, integration, E2E, accessibility, and visual regression testing.

### Tasks

| ID | Name | Points | Assigned To | Status |
|---|---|---|---|---|
| TEST-001 | Unit Tests - Backend Schemas | 3 | python-backend-engineer | completed |
| TEST-002 | Unit Tests - API Endpoints | 4 | python-backend-engineer | completed |
| TEST-003 | Unit Tests - Frontend Components | 4 | ui-engineer-enhanced | completed |
| TEST-004 | Integration Tests - Edit Flow | 2 | python-backend-engineer | completed |
| TEST-005 | Integration Tests - Delete Flow | 2 | python-backend-engineer | completed |
| TEST-006 | E2E Tests - Edit Source | 3 | ui-engineer-enhanced | completed |
| TEST-007 | E2E Tests - Delete Source | 3 | ui-engineer-enhanced | completed |
| TEST-008 | Accessibility Testing | 2 | ui-engineer-enhanced | completed |
| TEST-009 | Visual Regression Testing | 2 | ui-engineer-enhanced | completed |

**Key Files**:
- `skillmeat/api/tests/` - Backend tests
- `skillmeat/web/__tests__/` - Frontend unit tests
- `skillmeat/web/e2e/` - E2E tests

---

## Phase 6: Documentation (6 pts)

**Status**: completed
**Goal**: Complete documentation including API docs, component guides, user guide, and release notes.

### Tasks

| ID | Name | Points | Assigned To | Status |
|---|---|---|---|---|
| DOCS-001 | API Documentation | 2 | documentation-writer | completed |
| DOCS-002 | Component Documentation | 2 | documentation-writer | completed |
| DOCS-003 | User Guide Update | 1 | documentation-writer | completed |
| DOCS-004 | Release Notes | 1 | documentation-writer | completed |

**Key Files**:
- `skillmeat/api/docs/` - API documentation
- `skillmeat/web/docs/` - Component documentation
- `skillmeat/docs/user-guide/` - User documentation
- `skillmeat/CHANGELOG.md` - Release notes

---

## Orchestration Quick Reference

Execute phases sequentially, running batches in parallel where dependencies allow.

### Batch 1 - Phase 1 Foundation (No dependencies)

**Task Delegation Command**:
```
Task("data-layer-expert", "SCHEMA-001: Add description/notes fields to MarketplaceSource model in skillmeat/api/app/models/marketplace_source.py. Add: description (nullable String(500)), notes (nullable String(1000)). Update model __tablename__ if needed.")
```

**Wait for completion before proceeding to Batch 2.**

---

### Batch 2 - Phase 1 Schemas (Depends on SCHEMA-001)

**Parallel Execution**:

```
Task("data-layer-expert", "SCHEMA-002: Create Alembic migration for marketplace_sources table. Add description and notes columns (nullable). File: skillmeat/api/alembic/versions/. Test migration up/down.")
```

```
Task("python-backend-engineer", "SCHEMA-003: Update SourceResponse Pydantic schema in skillmeat/api/app/schemas/source.py. Add fields: description: str | None, notes: str | None. Include in OpenAPI docs.")
```

```
Task("python-backend-engineer", "SCHEMA-004: Update CreateSourceRequest schema in skillmeat/api/app/schemas/source.py. Add optional fields: description, notes. Add validators for max length (500, 1000).")
```

```
Task("python-backend-engineer", "SCHEMA-005: Create UpdateSourceRequest DTO in skillmeat/api/app/schemas/source.py. Make all fields optional for partial PATCH updates. Include field validators.")
```

**Wait for all to complete before proceeding to Batch 3.**

---

### Batch 3 - Phase 2 Core API (Depends on Phase 1)

**Parallel Execution**:

```
Task("python-backend-engineer", "API-001: Enhance POST /marketplace/sources endpoint in skillmeat/api/app/routers/marketplace.py. Use CreateSourceRequest schema, accept description/notes, persist to model.")
```

```
Task("python-backend-engineer", "API-002: Implement PATCH /marketplace/sources/{id} endpoint in skillmeat/api/app/routers/marketplace.py. Accept UpdateSourceRequest, partial updates only, return SourceResponse. Handle 404.")
```

```
Task("python-backend-engineer", "API-003: Verify DELETE /marketplace/sources/{id} endpoint in skillmeat/api/app/routers/marketplace.py exists and works correctly. Check 404 handling, 204 response.")
```

```
Task("python-backend-engineer", "API-004: Add field validation to all schemas in skillmeat/api/app/schemas/source.py. Validate description (max 500), notes (max 1000), prevent empty strings.")
```

**Wait for all to complete before proceeding to Batch 4.**

---

### Batch 4 - Phase 2 Integration & SDK (Depends on API-002, API-003)

**Parallel Execution**:

```
Task("python-backend-engineer", "API-005: Write integration tests in skillmeat/api/tests/test_integration.py. Test PATCH partial updates, DELETE success/404, verify data persistence.")
```

```
Task("python-backend-engineer", "API-006: Regenerate TypeScript SDK in skillmeat/web/api/generated/ from updated OpenAPI spec. Verify SourceResponse, CreateSourceRequest, UpdateSourceRequest are included.")
```

**Wait for all to complete before proceeding to Batch 5.**

---

### Batch 5 - Phase 3 Type Updates (Depends on API-006)

**Parallel Execution**:

```
Task("ui-engineer-enhanced", "TYPES-001: Extend GitHubSource type in skillmeat/web/api/types/marketplace.ts. Add fields: description?: string, notes?: string.")
```

```
Task("ui-engineer-enhanced", "TYPES-002: Extend CreateSourceRequest type in skillmeat/web/api/types/marketplace.ts. Add optional fields: description?, notes?.")
```

```
Task("ui-engineer-enhanced", "TYPES-003: Create UpdateSourceRequest type in skillmeat/web/api/types/marketplace.ts. Make all fields optional: id?, name?, description?, notes?.")
```

**Wait for all to complete before proceeding to Batch 6.**

---

### Batch 6 - Phase 3 Hook Update (Depends on TYPES-003)

**Task Delegation Command**:
```
Task("ui-engineer-enhanced", "TYPES-004: Update useMarketplaceSources hook in skillmeat/web/hooks/useMarketplaceSources.ts. Add: updateSource(id, data: UpdateSourceRequest) and deleteSource(id) functions. Handle loading/error states.")
```

**Wait for completion before proceeding to Batch 7.**

---

### Batch 7 - Phase 4 Core Components (Depends on TYPES-001, TYPES-004)

**Parallel Execution**:

```
Task("ui-engineer-enhanced", "UI-001: Create DeleteConfirmationDialog component in skillmeat/web/components/DeleteConfirmationDialog.tsx. Use Radix/shadcn. Show source name, destructive button, loading state, error handling.")
```

```
Task("ui-engineer-enhanced", "UI-002: Convert AddSourceModal to EditSourceModal in skillmeat/web/components/SourceModal.tsx. Support both add/edit modes. Add textarea for notes with character counter. Call updateSource for edit.")
```

```
Task("ui-engineer-enhanced", "UI-005: Create NotesSection component in skillmeat/web/components/NotesSection.tsx. Display notes on detail page, handle null/empty gracefully.")
```

```
Task("ui-engineer-enhanced", "UI-006: Create DescriptionSection component in skillmeat/web/components/DescriptionSection.tsx. Display description on detail page, handle null/empty gracefully.")
```

**Wait for all to complete before proceeding to Batch 8.**

---

### Batch 8 - Phase 4 Component Enhancements (Depends on Batch 7)

**Parallel Execution**:

```
Task("ui-engineer-enhanced", "UI-003: Add hover buttons to SourceCard component in skillmeat/web/components/SourceCard.tsx. Edit (pencil) and Delete (trash) buttons. Smooth animation, opens EditSourceModal/DeleteConfirmationDialog.")
```

```
Task("ui-engineer-enhanced", "UI-004: Add edit/delete buttons to detail page in skillmeat/web/app/marketplace/[id]/page.tsx. Edit and Delete buttons in header. Loading states, redirect after delete.")
```

```
Task("ui-engineer-enhanced", "UI-007: Make artifacts pane scrollable in skillmeat/web/app/marketplace/[id]/page.tsx. Fix layout for long content with notes/descriptions.")
```

**Wait for all to complete before proceeding to Batch 9.**

---

### Batch 9 - Phase 4 Wiring & Integration (Depends on Batch 8)

**Parallel Execution**:

```
Task("ui-engineer-enhanced", "UI-008: Wire DeleteConfirmationDialog to SourceCard delete button in skillmeat/web/components/SourceCard.tsx. Handle success/error, refresh list after deletion.")
```

```
Task("ui-engineer-enhanced", "UI-009: Wire EditSourceModal to SourceCard edit button in skillmeat/web/components/SourceCard.tsx. Pass source data, handle success/error, refresh after update.")
```

```
Task("ui-engineer-enhanced", "UI-010: Update detail page wiring in skillmeat/web/app/marketplace/[id]/page.tsx. Display DescriptionSection/NotesSection, wire edit/delete buttons to modals/dialogs.")
```

**Wait for all to complete before proceeding to Batch 10.**

---

### Batch 10 - Phase 5 Backend Tests (Depends on Phase 2)

**Parallel Execution**:

```
Task("python-backend-engineer", "TEST-001: Write unit tests for schemas in skillmeat/api/tests/test_schemas.py. Test description/notes validation (max length), optional fields, serialization.")
```

```
Task("python-backend-engineer", "TEST-002: Write unit tests for API endpoints in skillmeat/api/tests/test_marketplace_api.py. Test POST with description/notes, PATCH partial updates, PATCH invalid data, DELETE success/404.")
```

```
Task("python-backend-engineer", "TEST-004: Write integration tests for edit flow in skillmeat/api/tests/test_integration.py. Create → PATCH → Verify, partial updates, concurrent updates.")
```

```
Task("python-backend-engineer", "TEST-005: Write integration tests for delete flow in skillmeat/api/tests/test_integration.py. Create → DELETE → Verify gone, cascade deletes, FK constraints.")
```

**Wait for all to complete before proceeding to Batch 11.**

---

### Batch 11 - Phase 5 Frontend Tests (Depends on UI-010)

**Parallel Execution**:

```
Task("ui-engineer-enhanced", "TEST-003: Write unit tests for components in skillmeat/web/__tests__/components/. Test DeleteConfirmationDialog, EditSourceModal form, SourceCard buttons, NotesSection, DescriptionSection.")
```

```
Task("ui-engineer-enhanced", "TEST-006: Write E2E tests for edit flow in skillmeat/web/e2e/tests/. Navigate → Click edit → Fill form → Submit → Verify updates using Playwright.")
```

```
Task("ui-engineer-enhanced", "TEST-007: Write E2E tests for delete flow in skillmeat/web/e2e/tests/. Navigate → Click delete → Confirm → Verify removed from list.")
```

```
Task("ui-engineer-enhanced", "TEST-008: Accessibility testing. Test screen readers, keyboard navigation, ARIA labels, color contrast for all new components.")
```

```
Task("ui-engineer-enhanced", "TEST-009: Visual regression testing using Percy or similar. Capture baseline screenshots, verify responsive design on mobile.")
```

**Wait for all to complete before proceeding to Batch 12.**

---

### Batch 12 - Phase 6 Documentation (Depends on API-006, UI-010)

**Parallel Execution**:

```
Task("documentation-writer", "DOCS-001: Update API documentation in skillmeat/api/docs/. Document PATCH endpoint, request/response examples, field validation rules, error responses.")
```

```
Task("documentation-writer", "DOCS-002: Update component documentation in skillmeat/web/docs/. Document DeleteConfirmationDialog, EditSourceModal, NotesSection, DescriptionSection. Include Storybook if applicable.")
```

```
Task("documentation-writer", "DOCS-003: Update user guide in skillmeat/docs/user-guide/. Add sections for editing/deleting sources, include screenshots/GIFs, update feature overview.")
```

**Wait for all to complete before proceeding to Batch 13.**

---

### Batch 13 - Phase 6 Release Notes (Depends on DOCS-001)

**Task Delegation Command**:
```
Task("documentation-writer", "DOCS-004: Create release notes in skillmeat/CHANGELOG.md and skillmeat/RELEASES.md. Summarize new edit/delete/description/notes capabilities, list breaking changes, link to docs, include upgrade instructions.")
```

---

## Summary & Tracking

**Phases Overview**:

| Phase | Name | Points | Status | % Complete |
|---|---|---|---|---|
| 1 | Database & Backend Schema | 11 | completed | 100% |
| 2 | Backend API Enhancement | 11 | completed | 100% |
| 3 | Frontend Type Updates | 5 | completed | 100% |
| 4 | UI Components Development | 28 | completed | 100% |
| 5 | Testing & QA | 25 | completed | 100% |
| 6 | Documentation | 6 | completed | 100% |
| **TOTAL** | | **86** | **completed** | **100%** |

**Next Steps**:
1. Begin Batch 1: Delegate SCHEMA-001 to data-layer-expert
2. Review task descriptions and file locations
3. Monitor progress in this file
4. Execute batches sequentially, running parallel tasks concurrently
5. Mark tasks complete as they finish
6. Update percentage and phase statuses

---

## Notes

- **Token Efficiency**: YAML frontmatter designed for AI agent consumption (< 3KB for queries)
- **Orchestration**: Batches designed for maximum parallelization without dependency violations
- **File Locations**: All paths absolute; uses existing codebase structure
- **Dependencies**: Carefully sequenced to minimize blocking; frontend/backend can often run in parallel after Phase 2
- **Testing**: Comprehensive coverage across unit, integration, E2E, accessibility, visual regression
- **Documentation**: Follows MP patterns (API docs, component docs, user guide, release notes)
