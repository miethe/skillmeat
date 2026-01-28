# Quick Feature: Cross-Modal Navigation Tabs

**Status**: completed
**Created**: 2026-01-27
**Estimated Scope**: 4-6 files, ~400 lines

## Summary

Add bidirectional navigation between artifact contexts:
- CatalogEntryModal (marketplace sources) → Collections/Deployments tabs
- UnifiedEntityModal (collections) → Sources tab
- Both modals → clickable cards that navigate to the artifact in the target context

## Requirements

### 1. CatalogEntryModal - Collections Tab
- Only visible for imported artifacts (`entry.status === 'imported'`)
- Lists all collections containing the imported artifact
- Uses card component showing artifact in collection context
- Clicking card: navigates to `/manage` and opens UnifiedEntityModal for that collection artifact

### 2. CatalogEntryModal - Deployments Tab
- Only visible for imported artifacts
- Lists all projects where the artifact is deployed
- Uses DeploymentCard component
- Clicking card: navigates to `/projects/[path]` and opens modal for deployed artifact

### 3. UnifiedEntityModal - Sources Tab
- Only visible for artifacts with a `source` field matching a catalog entry
- Shows a card linking back to the source catalog entry
- Clicking card: navigates to `/marketplace/sources/[sourceId]` and opens CatalogEntryModal

### 4. UnifiedEntityModal - Deployments Tab Enhancement
- Update existing deployment cards to be clickable
- Clicking navigates to `/projects/[projectPath]` and opens the artifact modal

## Technical Approach

### Data Flow
```
CatalogEntry (marketplace)
  └── import_id → Artifact (collection)
        └── source field → back to CatalogEntry
        └── deployments → DeployedArtifact (project)
```

### New API Hooks Needed
1. `useArtifactBySource(sourceId, path)` - Find collection artifact by its source info
2. Existing: `useDeploymentList` - Already fetches deployments per project

### Navigation Pattern
- Use Next.js router with URL state for modal opening
- Pattern: `/manage?artifact={id}` or `/marketplace/sources/{id}?artifact={path}`
- Modal opening controlled by URL search params

## Files to Modify

| File | Changes |
|------|---------|
| `CatalogEntryModal.tsx` | Add Collections and Deployments tabs, navigation handlers |
| `unified-entity-modal.tsx` | Add Sources tab, update Deployments tab clicks |
| `lib/api/artifacts.ts` | Add `fetchArtifactBySource` function |
| `hooks/use-artifacts.ts` | Add `useArtifactBySource` hook |
| `types/marketplace.ts` | Ensure CatalogEntry has `import_id` field |

## New Components

### CatalogCollectionsTab
- Reuses patterns from `ModalCollectionsTab`
- Fetches artifact by `entry.import_id` to get `collections` array
- Renders collection cards with navigation

### CatalogDeploymentsTab
- Similar to deployments section in UnifiedEntityModal
- Fetches all projects, filters to artifact deployments
- Uses DeploymentCard with navigation callback

### SourceTab (for UnifiedEntityModal)
- New component in `components/entity/`
- Shows source catalog entry card
- Navigation to marketplace source page

## Testing Plan

1. Import an artifact from a source
2. Verify Collections tab appears in CatalogEntryModal
3. Click collection card → verify navigation to manage page with modal
4. Verify Deployments tab shows projects
5. Deploy artifact to project
6. Click deployment card → verify navigation to project
7. Open artifact in collection → verify Sources tab
8. Click source card → verify navigation back to marketplace

## Implementation Notes

### Data Linking Challenge

CatalogEntry → Artifact linking is asymmetric:
- CatalogEntry has `import_id` but no API to query artifacts by it
- Artifact has `source` field but no direct link back to CatalogEntry

### Workaround Implemented

**CatalogEntryModal Collections/Deployments:**
- Search artifacts by name + type to find the imported artifact
- Use the artifact's `collections` array from API response
- Filter deployments by artifact name + type

**UnifiedEntityModal Sources:**
- Use `useSources()` hook to get all marketplace sources
- Match entity's `source` field against `owner/repo` pattern
- Query matching source's catalog to find exact entry by name/type
- Navigate using actual database sourceId

## Rollback

Feature is additive (new tabs). Safe to merge incrementally.
