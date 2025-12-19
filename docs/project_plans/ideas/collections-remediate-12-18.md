# Remediation of Collection UI/UX

**Date:** 2025-12-18

## Context

- Note the planning files from the Collections implementation for our app:
  - Primary PRD: `docs/project_plans/PRDs/enhancements/collections-navigation-v1.md`
  - Endpoint Consolidation PRD: `docs/project_plans/implementation_plans/features/collections-consolidation-plan.md`
  - Buttons PRD: `docs/project_plans/implementation_plans/features/add-collection-creation-buttons-v1.md`

## Objective

The web app is not functioning as expected per my intentions, but that gap may be with the designs vs the implementation.

Currently, users are able to swap between Collections via the dropdown in the sidebar as expected, as well as add Collections, Copy/Move artifacts to Collections, and the Collections dropdown notes the number of artifacts in each Collection.

However, there are still several key gaps in the user experience:

### 1. No "Collection View"

#### Current Behavior

- There is no dedicated view or page that displays the contents of a selected Collection.
- When a Collection has been selected from the dropdown, the main content area does not update to show the artifacts only within that Collection. Instead, it still shows all artifacts from all Collections.

#### Desired Behavior

- When a user selects a Collection from the dropdown, the main content area on the `/collection` page should update to display only the artifacts that belong to that selected Collection.
- When no Collection is selected (i.e., "All Collections"), the main content area should display artifacts from all Collections as it currently does.

### 2. Artifacts do not display their Collection association in the modal

#### Current Behavior

- When viewing an artifact's details in a modal, on the `Collections` tab, there are never any listed Collections, even if the artifact belongs to one or more Collections.

#### Desired Behavior

- When viewing an artifact's details in a modal, on the `Collections` tab, it should list all Collections that the artifact belongs to.
- Upon adding or removing the artifact from Collections via this tab, the changes should be reflected immediately in the UI without needing to refresh the page.
