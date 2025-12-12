# Enhancements - Collections & Site Navigation

**Date:** December 12, 2025

## Context

Currently, the `/collection` and `/manage` pages serve nearly identical functions for browsing and managing artifacts, leading to confusion about when to use each. Instead, we should create an updated navigation structure and update the purpose of these 2 pages.

## Idea List

1. There should be a parent tab in the sidebar called "Collections" that leads to the /collection page, which serves as the main landing page for browsing and organizing artifacts at a high level.
    - Nested below this tab should be the tabs for 'Manage', 'Projects', and 'MCP Servers'.
2. The /collection page will be the core page to view all artifacts within the user's collection(s), with filtering, searching, and grouping functionality.
    - Clicking on an artifact card opens the unified artifact modal with all relevant details and actions.
    - /collection page opens to the default Collection. However, there should be a dropdown at the top, in-line with the page title, allowing users to switch between different Collections they have access to. This dropdown should include a 'Add Collection' option to create new Collections.
    - There should be an 'All Collections' view that aggregates artifacts from all Collections for broader browsing. This view can be selected from the Collection dropdown.
3. Users should be able to create custom groups of artifacts within their collection for better organization (by functionality, project phase, team ownership, etc).
    - On the /collection page, there should be a new view option, in addition to Grid and List, called 'Grouped View' that shows artifacts organized by their custom groups within the selected Collection.
    - Artifacts should be able to be dragged and dropped between groups in this view for easy reorganization, or added/removed from groups via a menu option on the artifact card and modal.
    - Clicking 'Manage Groups' from the artifact card or modal opens a dialog where users can create, rename, and delete groups, as well as assign/unassign the artifact to/from groups using checkboxes.
4. The /manage page will be repurposed as a Deployment Dashboard, showing a cross-project deployment view of artifacts.
    - This page will list all artifacts in the user's collection(s) along with the projects they are deployed to, deployment status, and version information.
    - Users can filter and sort artifacts based on deployment status, project, and other criteria.
    - Clicking on an artifact card opens the unified artifact modal with a new 'Deployments' tab showing detailed deployment information across projects.
    - Directly on the artifact card in this view, quickly see info like number of deployments, active/inactive status, 'Update Available'.
    - The card should have quick actions for 'Deploy to New Project' and 'View Deployments'.
    - In the future, we will add ability for cards to show a clear indicator if an artifact has a linting error or warning that needs to be addressed.
5. Users should be able to manage multiple Collections in the app, with the ability to switch between them easily.
    - Collections can be created, renamed, and deleted from the /collection page.
    - Artifacts can be copied/moved between Collections via a menu item on the artifact card or within the modal or bulk actions.
      - When in 'All Collections' view, artifacts should also support drag-and-drop to move them to specific Collections.
      - When a user clicks 'Move/Copy to Collections' from the artifact card or modal, a dialog should appear allowing them to select the target Collection(s) with checkboxes, with 2 buttons at the bottom: 'Move' and 'Copy'.
6. Every artifact card should have an ellipsis menu in the bottom right corner on hover with options: ['Move/Copy to Collections', 'Manage Groups', 'Edit', 'Delete'].
    - The 'Edit' option opens the unified artifact modal to the Edit Parameters dialog for editing.
    - The 'Delete' option opens a confirmation dialog before deleting the artifact.
7. The unified artifact modal should have a new tab called 'Collections/Groups' that shows which groups and collections the artifact belongs to, with options to manage them directly from this tab.
    - This tab should list all Collections the artifact is part of, and under each Collection, list the groups it belongs to within that Collection.
    - There should be buttons to 'Manage Groups' and 'Move/Copy to Collections' that open the respective dialogs for managing these aspects.
8. The /collection page should pull artifacts on start-up of the app and cache them locally via the existing local cache mechanism to improve load times and responsiveness.
    - The app should periodically refresh the cache in the background to ensure data is up-to-date without blocking the UI. Ideally, updates would also be pushed when changes are made via the web app or CLI.
    - Users should be able to manually trigger a refresh of the collection data via a button on the /collection page.
    - Ideally, this cache would persist across app restarts to minimize load times even further, allowing users to quickly access their collections and artifacts.