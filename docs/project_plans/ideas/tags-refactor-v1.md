# Tags Refactor V1

**Date:** 2025-12-18

## Context

A couple issues were encountered with the Tags implementation in the web app, including a bug and necessary enhancements.

## Issues

When trying to save edits after adding tags to an artifact via the "Edit Parameters" form when viewing an artifact modal from the /collection page, the request fails with a 422:

1. [API] INFO:     skillmeat.observability.tracing:

```log
Starting span: PUT /api/v1/artifacts/skill:notebooklm-skill/parameters
[API] WARNING:     skillmeat.api.server - Validation error for http://127.0.0.1:8080/api/v1/artifacts/skill:notebooklm-skill/parameters: [{'type': 'value_error', 'loc': ('body', 'parameters', 'scope'), 'msg': "Value error, scope must be 'user' or 'local'", 'input':
'default', 'ctx': {'error': ValueError("scope must be 'user' or 'local'")}}]
```

## Enhancements

1. The Tags field for artifacts should use a Tags component, similar to that from shadcn.io (different than shadcn/ui!) - https://www.shadcn.io/registry/tags.json. Specifically, Tags should:

- allow users to search for existing/add new tags by typing and pressing Enter, as well as remove existing tags by clicking an 'x' on each tag.
- be visually distinct in the selection form, looking identical to how they will render on the artifact - as rounded, colored Badges.
- have a slight hover effect, be clickable to filter by that tag, and have an 'x' to remove them when in edit mode.
- be keyboard accessible, allowing users to navigate between tags using arrow keys, and remove tags using Backspace or Delete keys.
- support copy-pasting multiple tags at once, splitting them by commas.
- exist globally, meaning tags added to one artifact are available for selection on all artifacts.
- be filterable, being added to the Filters bar in artifact views. The button should exist next to the Filters and Sort buttons, opening a popover showing all existing tags, each with a count of how many artifacts have that tag. Users can select one or more tags to filter the artifact list by clicking the tag directly, being highlighted when selected. An input at the top of the popover allows users to search for tags by name.
- be associated with every primary entity in the app.
- have metrics accessible via the dashboard analytics on the root '/' page.

## Implementation Considerations

Consider the best DB schema approach for storing tags, such as a many-to-many relationship table between artifacts and tags.
Utilize the shadcn/ui MCP for guidance on building the various components. Utilizing existing components (our own and 3rd party) where possible, with customizations as needed.