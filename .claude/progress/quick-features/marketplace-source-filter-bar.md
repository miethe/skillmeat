---
type: quick-feature-plan
feature_slug: marketplace-source-filter-bar
request_log_id: null
status: completed
completed_at: 2026-01-03T00:00:00Z
created: 2026-01-03T00:00:00Z
estimated_scope: medium
---

# Marketplace Source Detail - Redesign Filter/Sort/Search Bar

## Scope

Redesign the `/marketplace/sources/{ID}` page toolbar to match the collection page patterns. Replace type tabs with a dropdown, add unified Sort By, Confidence Range filter, Select All toggle, and Grid/List view mode toggles.

## Reference

- **Render**: `docs/project_plans/renders/marketplace-sourcing-filters.png`
- **Pattern Source**: `skillmeat/web/components/collection/collection-toolbar.tsx`

## Affected Files

- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`: Refactor toolbar section, replace CatalogTabs with new toolbar component
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-tabs.tsx`: May be deprecated or adapted
- `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx`: NEW - Create toolbar component matching collection-toolbar pattern
- `skillmeat/web/components/ConfidenceFilter.tsx`: Reuse existing component

## Implementation Steps

1. Create `SourceToolbar` component with unified filter bar layout -> @ui-engineer-enhanced
   - Search input (left side)
   - Type dropdown (replacing tabs)
   - Sort By dropdown (Confidence High/Low, Name A-Z/Z-A, Date Added)
   - Confidence Range section (min/max inputs, include-low-confidence toggle)
   - Select All checkbox
   - View mode toggle buttons (Grid/List)

2. Integrate toolbar into source detail page, replace CatalogTabs -> @ui-engineer-enhanced

3. Add List view for artifacts (reuse ArtifactList pattern or create marketplace variant) -> @ui-engineer-enhanced

## Key Components from Render

| Component | Description |
|-----------|-------------|
| Search | Input with placeholder "Search artifacts..." |
| Type | Dropdown with "All Types (49)", Skills, Agents, Commands, MCP, Hooks |
| Sort by | Dropdown with Confidence High-Low/Low-High, Name A-Z/Z-A, Date Added |
| Confidence Range | Min/max inputs (50-100), percentage labels |
| Include low-confidence | Toggle switch |
| Select All | Checkbox |
| View Mode | Grid/List toggle buttons (not in render but requested) |

## Testing

- Visual regression: Compare with render
- Functional: All filters work correctly
- URL state: Filters persist in URL params
- Responsive: Works on mobile

## Completion Criteria

- [ ] SourceToolbar component created
- [ ] Type tabs replaced with dropdown
- [ ] Sort By dropdown working
- [ ] Confidence Range filter working
- [ ] Select All toggle working
- [ ] View mode toggle (Grid/List) working
- [ ] Tests pass
- [ ] Build succeeds
