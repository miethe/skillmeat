<!-- Path Scope: skillmeat/web/hooks/**/*.ts -->

# Web Frontend Hooks - Patterns and Best Practices

Custom React hooks for SkillMeat web frontend using TanStack Query v5.

---

## Inventory (Auto-generated)

<!-- CODEBASE_GRAPH:HOOKS:START -->
| Hook | File | API Clients | Query Keys |
| --- | --- | --- | --- |
| useAddArtifactToCollection | skillmeat/web/hooks/use-collections.ts | ApiError, addArtifactToCollection, apiRequest, createCollection, deleteCollection, removeArtifactFromCollection, updateCollection | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| useAddArtifactToGroup | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useAddTagToArtifact | skillmeat/web/hooks/use-tags.ts | addTagToArtifact, createTag, deleteTag, fetchTags, getArtifactTags, removeTagFromArtifact, searchTags, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest, updateTag | - |
| useAnalyticsStream | skillmeat/web/hooks/useAnalyticsStream.ts | apiConfig | ['analytics', 'summary'], ['analytics', 'top-artifacts'], ['analytics', 'trends'], ['analytics'] |
| useAnalyticsSummary | skillmeat/web/hooks/useAnalytics.ts | ApiError, apiConfig, apiRequest | - |
| useAnalyzeMerge | skillmeat/web/hooks/use-merge.ts | analyzeMergeSafety, executeMerge, previewMerge, resolveConflict | ['collections', variables.localCollection], ['snapshots'] |
| useArtifact | skillmeat/web/hooks/useArtifacts.ts | ApiError, apiConfig, apiRequest | - |
| useArtifactDeletion | skillmeat/web/hooks/use-artifact-deletion.ts | deleteArtifactFromCollection, undeployArtifact | ['artifacts'], ['collections'], ['deployments'], ['projects'] |
| useArtifactTags | skillmeat/web/hooks/use-tags.ts | addTagToArtifact, createTag, deleteTag, fetchTags, getArtifactTags, removeTagFromArtifact, searchTags, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest, updateTag | - |
| useArtifacts | - | - | - |
| useArtifacts | skillmeat/web/hooks/useArtifacts.ts | ApiError, apiConfig, apiRequest | - |
| useBrokers | - | - | - |
| useBrokers | skillmeat/web/hooks/useMarketplace.ts | ApiError, apiRequest, useToast | - |
| useBulkTagApply | skillmeat/web/hooks/use-bulk-tag-apply.ts | sourceKeys, useToast | - |
| useBundleAnalytics | skillmeat/web/hooks/useBundles.ts | apiConfig, apiRequest | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| useBundles | skillmeat/web/hooks/useBundles.ts | apiConfig, apiRequest | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| useCacheRefresh | skillmeat/web/hooks/useCacheRefresh.ts | apiRequest | ['cache', projectId], ['cache'], ['projects', 'detail', projectId], ['projects'] |
| useCacheStatus | skillmeat/web/hooks/useCacheStatus.ts | apiRequest | ['cache', 'status'] |
| useCatalogFileContent | skillmeat/web/hooks/use-catalog-files.ts | fetchCatalogFileContent, fetchCatalogFileTree, type FileContentResponse, type FileTreeResponse | - |
| useCatalogFileTree | skillmeat/web/hooks/use-catalog-files.ts | fetchCatalogFileContent, fetchCatalogFileTree, type FileContentResponse, type FileTreeResponse | - |
| useCheckUpstream | skillmeat/web/hooks/useSync.ts | - | ['artifact', variables.artifactId], ['artifacts'] |
| useCollection | skillmeat/web/hooks/use-collections.ts | ApiError, addArtifactToCollection, apiRequest, createCollection, deleteCollection, removeArtifactFromCollection, updateCollection | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| useCollectionArtifacts | - | - | - |
| useCollectionArtifacts | skillmeat/web/hooks/use-collections.ts | ApiError, addArtifactToCollection, apiRequest, createCollection, deleteCollection, removeArtifactFromCollection, updateCollection | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| useCollectionContext | - | - | - |
| useCollectionContext | skillmeat/web/hooks/use-collection-context.ts | - | - |
| useCollections | skillmeat/web/hooks/use-collections.ts | ApiError, addArtifactToCollection, apiRequest, createCollection, deleteCollection, removeArtifactFromCollection, updateCollection | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| useConfirmDuplicates | skillmeat/web/hooks/useProjectDiscovery.ts | apiRequest | ['artifacts', 'discover', 'project', projectPath], ['artifacts', 'discover', 'project', variables.project_path], ['artifacts'], ['projects', 'detail', projectId] |
| useContextEntities | - | - | - |
| useContextEntities | skillmeat/web/hooks/use-context-entities.ts | createContextEntity, deleteContextEntity, fetchContextEntities, fetchContextEntity, fetchContextEntityContent, updateContextEntity | - |
| useContextEntity | skillmeat/web/hooks/use-context-entities.ts | createContextEntity, deleteContextEntity, fetchContextEntities, fetchContextEntity, fetchContextEntityContent, updateContextEntity | - |
| useContextEntityContent | skillmeat/web/hooks/use-context-entities.ts | createContextEntity, deleteContextEntity, fetchContextEntities, fetchContextEntity, fetchContextEntityContent, updateContextEntity | - |
| useContextSyncStatus | skillmeat/web/hooks/use-context-sync.ts | getSyncStatus, pullChanges, pushChanges, resolveConflict, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| useCreateCollection | skillmeat/web/hooks/use-collections.ts | ApiError, addArtifactToCollection, apiRequest, createCollection, deleteCollection, removeArtifactFromCollection, updateCollection | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| useCreateContextEntity | - | - | - |
| useCreateContextEntity | skillmeat/web/hooks/use-context-entities.ts | createContextEntity, deleteContextEntity, fetchContextEntities, fetchContextEntity, fetchContextEntityContent, updateContextEntity | - |
| useCreateGroup | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useCreateMcpServer | - | - | - |
| useCreateMcpServer | skillmeat/web/hooks/useMcpServers.ts | apiRequest | - |
| useCreateProject | skillmeat/web/hooks/useProjects.ts | ApiError, apiConfig, apiRequest | - |
| useCreateSnapshot | skillmeat/web/hooks/use-snapshots.ts | analyzeRollbackSafety, createSnapshot, deleteSnapshot, diffSnapshots, executeRollback, fetchSnapshot, fetchSnapshots | ['artifacts'], ['collections'] |
| useCreateSource | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useCreateTag | skillmeat/web/hooks/use-tags.ts | addTagToArtifact, createTag, deleteTag, fetchTags, getArtifactTags, removeTagFromArtifact, searchTags, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest, updateTag | - |
| useCreateTemplate | skillmeat/web/hooks/use-templates.ts | createTemplate, deleteTemplate, deployTemplate, fetchTemplateById, fetchTemplates, updateTemplate | ['deployments'] |
| useDebounce | skillmeat/web/hooks/use-debounce.ts | - | - |
| useDeleteArtifact | skillmeat/web/hooks/useArtifacts.ts | ApiError, apiConfig, apiRequest | - |
| useDeleteBundle | skillmeat/web/hooks/useBundles.ts | apiConfig, apiRequest | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| useDeleteCollection | skillmeat/web/hooks/use-collections.ts | ApiError, addArtifactToCollection, apiRequest, createCollection, deleteCollection, removeArtifactFromCollection, updateCollection | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| useDeleteContextEntity | - | - | - |
| useDeleteContextEntity | skillmeat/web/hooks/use-context-entities.ts | createContextEntity, deleteContextEntity, fetchContextEntities, fetchContextEntity, fetchContextEntityContent, updateContextEntity | - |
| useDeleteGroup | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useDeleteMcpServer | - | - | - |
| useDeleteMcpServer | skillmeat/web/hooks/useMcpServers.ts | apiRequest | - |
| useDeleteProject | skillmeat/web/hooks/useProjects.ts | ApiError, apiConfig, apiRequest | - |
| useDeleteSnapshot | skillmeat/web/hooks/use-snapshots.ts | analyzeRollbackSafety, createSnapshot, deleteSnapshot, diffSnapshots, executeRollback, fetchSnapshot, fetchSnapshots | ['artifacts'], ['collections'] |
| useDeleteSource | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useDeleteTag | skillmeat/web/hooks/use-tags.ts | addTagToArtifact, createTag, deleteTag, fetchTags, getArtifactTags, removeTagFromArtifact, searchTags, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest, updateTag | - |
| useDeleteTemplate | skillmeat/web/hooks/use-templates.ts | createTemplate, deleteTemplate, deployTemplate, fetchTemplateById, fetchTemplates, updateTemplate | ['deployments'] |
| useDeploy | skillmeat/web/hooks/useDeploy.ts | apiRequest | ['artifacts'], ['deployments'], ['projects', 'detail'] |
| useDeployArtifact | skillmeat/web/hooks/use-deployments.ts | deployArtifact, getDeploymentSummary, getDeployments, listDeployments, type DeploymentQueryParams, type DeploymentSummary, undeployArtifact | - |
| useDeployMcpServer | - | - | - |
| useDeployMcpServer | skillmeat/web/hooks/useMcpServers.ts | apiRequest | - |
| useDeployTemplate | skillmeat/web/hooks/use-templates.ts | createTemplate, deleteTemplate, deployTemplate, fetchTemplateById, fetchTemplates, updateTemplate | ['deployments'] |
| useDeploymentList | - | - | - |
| useDeploymentList | skillmeat/web/hooks/use-deployments.ts | deployArtifact, getDeploymentSummary, getDeployments, listDeployments, type DeploymentQueryParams, type DeploymentSummary, undeployArtifact | - |
| useDeploymentSummary | - | - | - |
| useDeploymentSummary | skillmeat/web/hooks/use-deployments.ts | deployArtifact, getDeploymentSummary, getDeployments, listDeployments, type DeploymentQueryParams, type DeploymentSummary, undeployArtifact | - |
| useDeployments | skillmeat/web/hooks/use-deployments.ts | deployArtifact, getDeploymentSummary, getDeployments, listDeployments, type DeploymentQueryParams, type DeploymentSummary, undeployArtifact | - |
| useDiffSnapshots | skillmeat/web/hooks/use-snapshots.ts | analyzeRollbackSafety, createSnapshot, deleteSnapshot, diffSnapshots, executeRollback, fetchSnapshot, fetchSnapshots | ['artifacts'], ['collections'] |
| useDiscovery | skillmeat/web/hooks/useDiscovery.ts | apiRequest | ['artifacts', 'detail', artifactId], ['artifacts', 'discover'], ['artifacts', 'list'], ['artifacts'], ['entities'] |
| useEditArtifactParameters | - | - | - |
| useEditArtifactParameters | skillmeat/web/hooks/useDiscovery.ts | apiRequest | ['artifacts', 'detail', artifactId], ['artifacts', 'discover'], ['artifacts', 'list'], ['artifacts'], ['entities'] |
| useEntityLifecycle | skillmeat/web/hooks/useEntityLifecycle.tsx | apiConfig, apiRequest | ['entities'], ['projects'] |
| useExcludeCatalogEntry | - | - | - |
| useExcludeCatalogEntry | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useExecuteMerge | skillmeat/web/hooks/use-merge.ts | analyzeMergeSafety, executeMerge, previewMerge, resolveConflict | ['collections', variables.localCollection], ['snapshots'] |
| useExportBundle | skillmeat/web/hooks/useExportBundle.ts | apiConfig, apiRequest | ['bundles'] |
| useFocusTrap | skillmeat/web/hooks/useFocusTrap.ts | - | - |
| useGitHubMetadata | skillmeat/web/hooks/useDiscovery.ts | apiRequest | ['artifacts', 'detail', artifactId], ['artifacts', 'discover'], ['artifacts', 'list'], ['artifacts'], ['entities'] |
| useGroup | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useGroupArtifacts | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useGroups | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useImportAllMatching | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useImportArtifacts | - | - | - |
| useImportArtifacts | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useImportBundle | skillmeat/web/hooks/useImportBundle.ts | apiConfig, apiRequest | ['artifacts'], ['bundle-preview', source], ['bundles'] |
| useInferUrl | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useInstallListing | - | - | - |
| useInstallListing | skillmeat/web/hooks/useMarketplace.ts | ApiError, apiRequest, useToast | - |
| useListing | - | - | - |
| useListing | skillmeat/web/hooks/useMarketplace.ts | ApiError, apiRequest, useToast | - |
| useListings | - | - | - |
| useListings | skillmeat/web/hooks/useMarketplace.ts | ApiError, apiRequest, useToast | - |
| useMcpBatchOperations | skillmeat/web/hooks/useMcpServers.ts | apiRequest | - |
| useMcpDeploymentStatus | - | - | - |
| useMcpDeploymentStatus | skillmeat/web/hooks/useMcpServers.ts | apiRequest | - |
| useMcpServer | - | - | - |
| useMcpServer | skillmeat/web/hooks/useMcpServers.ts | apiRequest | - |
| useMcpServers | - | - | - |
| useMcpServers | skillmeat/web/hooks/useMcpServers.ts | apiRequest | - |
| useMoveArtifactToGroup | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useOutdatedArtifacts | - | - | - |
| useOutdatedArtifacts | skillmeat/web/hooks/useOutdatedArtifacts.ts | apiRequest | - |
| usePathTags | skillmeat/web/hooks/use-path-tags.ts | getPathTags, updatePathTagStatus | - |
| usePendingContextChanges | skillmeat/web/hooks/use-context-sync.ts | getSyncStatus, pullChanges, pushChanges, resolveConflict, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| usePreviewBundle | skillmeat/web/hooks/useImportBundle.ts | apiConfig, apiRequest | ['artifacts'], ['bundle-preview', source], ['bundles'] |
| usePreviewMerge | skillmeat/web/hooks/use-merge.ts | analyzeMergeSafety, executeMerge, previewMerge, resolveConflict | ['collections', variables.localCollection], ['snapshots'] |
| useProject | - | - | - |
| useProject | skillmeat/web/hooks/useProjects.ts | ApiError, apiConfig, apiRequest | - |
| useProjectCache | - | - | - |
| useProjectCache | skillmeat/web/hooks/useProjectCache.ts | apiRequest | ['projects', 'list', 'with-cache-info'] |
| useProjectDiscovery | - | - | - |
| useProjectDiscovery | skillmeat/web/hooks/useProjectDiscovery.ts | apiRequest | ['artifacts', 'discover', 'project', projectPath], ['artifacts', 'discover', 'project', variables.project_path], ['artifacts'], ['projects', 'detail', projectId] |
| useProjects | skillmeat/web/hooks/useProjects.ts | ApiError, apiConfig, apiRequest | - |
| usePublishBundle | - | - | - |
| usePublishBundle | skillmeat/web/hooks/useMarketplace.ts | ApiError, apiRequest, useToast | - |
| usePullContextChanges | skillmeat/web/hooks/use-context-sync.ts | getSyncStatus, pullChanges, pushChanges, resolveConflict, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| usePushContextChanges | skillmeat/web/hooks/use-context-sync.ts | getSyncStatus, pullChanges, pushChanges, resolveConflict, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| useRefreshDeployments | - | - | - |
| useRefreshDeployments | skillmeat/web/hooks/use-deployments.ts | deployArtifact, getDeploymentSummary, getDeployments, listDeployments, type DeploymentQueryParams, type DeploymentSummary, undeployArtifact | - |
| useRemoveArtifactFromCollection | skillmeat/web/hooks/use-collections.ts | ApiError, addArtifactToCollection, apiRequest, createCollection, deleteCollection, removeArtifactFromCollection, updateCollection | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| useRemoveArtifactFromGroup | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useRemoveTagFromArtifact | skillmeat/web/hooks/use-tags.ts | addTagToArtifact, createTag, deleteTag, fetchTags, getArtifactTags, removeTagFromArtifact, searchTags, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest, updateTag | - |
| useReorderArtifactsInGroup | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useReorderGroups | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useRescanSource | - | - | - |
| useRescanSource | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useResolveConflict | skillmeat/web/hooks/use-merge.ts | analyzeMergeSafety, executeMerge, previewMerge, resolveConflict | ['collections', variables.localCollection], ['snapshots'] |
| useResolveContextConflict | skillmeat/web/hooks/use-context-sync.ts | getSyncStatus, pullChanges, pushChanges, resolveConflict, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| useRestoreCatalogEntry | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useRevokeShareLink | skillmeat/web/hooks/useBundles.ts | apiConfig, apiRequest | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| useRollback | skillmeat/web/hooks/use-snapshots.ts | analyzeRollbackSafety, createSnapshot, deleteSnapshot, diffSnapshots, executeRollback, fetchSnapshot, fetchSnapshots | ['artifacts'], ['collections'] |
| useRollbackAnalysis | skillmeat/web/hooks/use-snapshots.ts | analyzeRollbackSafety, createSnapshot, deleteSnapshot, diffSnapshots, executeRollback, fetchSnapshot, fetchSnapshots | ['artifacts'], ['collections'] |
| useSSE | skillmeat/web/hooks/useSSE.ts | - | - |
| useSearchTags | skillmeat/web/hooks/use-tags.ts | addTagToArtifact, createTag, deleteTag, fetchTags, getArtifactTags, removeTagFromArtifact, searchTags, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest, updateTag | - |
| useSnapshot | skillmeat/web/hooks/use-snapshots.ts | analyzeRollbackSafety, createSnapshot, deleteSnapshot, diffSnapshots, executeRollback, fetchSnapshot, fetchSnapshots | ['artifacts'], ['collections'] |
| useSnapshots | skillmeat/web/hooks/use-snapshots.ts | analyzeRollbackSafety, createSnapshot, deleteSnapshot, diffSnapshots, executeRollback, fetchSnapshot, fetchSnapshots | ['artifacts'], ['collections'] |
| useSource | - | - | - |
| useSource | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useSourceCatalog | - | - | - |
| useSourceCatalog | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useSources | - | - | - |
| useSources | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useSync | skillmeat/web/hooks/useSync.ts | - | ['artifact', variables.artifactId], ['artifacts'] |
| useTags | skillmeat/web/hooks/use-tags.ts | addTagToArtifact, createTag, deleteTag, fetchTags, getArtifactTags, removeTagFromArtifact, searchTags, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest, updateTag | - |
| useTemplate | skillmeat/web/hooks/use-templates.ts | createTemplate, deleteTemplate, deployTemplate, fetchTemplateById, fetchTemplates, updateTemplate | ['deployments'] |
| useTemplates | - | - | - |
| useTemplates | skillmeat/web/hooks/use-templates.ts | createTemplate, deleteTemplate, deployTemplate, fetchTemplateById, fetchTemplates, updateTemplate | ['deployments'] |
| useToast | - | - | - |
| useToast | skillmeat/web/hooks/use-toast.tsx | - | - |
| useToastNotification | skillmeat/web/hooks/use-toast-notification.ts | - | - |
| useTopArtifacts | skillmeat/web/hooks/useAnalytics.ts | ApiError, apiConfig, apiRequest | - |
| useUndeploy | skillmeat/web/hooks/useDeploy.ts | apiRequest | ['artifacts'], ['deployments'], ['projects', 'detail'] |
| useUndeployArtifact | skillmeat/web/hooks/use-deployments.ts | deployArtifact, getDeploymentSummary, getDeployments, listDeployments, type DeploymentQueryParams, type DeploymentSummary, undeployArtifact | - |
| useUndeployMcpServer | - | - | - |
| useUndeployMcpServer | skillmeat/web/hooks/useMcpServers.ts | apiRequest | - |
| useUpdateArtifact | skillmeat/web/hooks/useArtifacts.ts | ApiError, apiConfig, apiRequest | - |
| useUpdateCatalogEntryName | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useUpdateCollection | skillmeat/web/hooks/use-collections.ts | ApiError, addArtifactToCollection, apiRequest, createCollection, deleteCollection, removeArtifactFromCollection, updateCollection | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| useUpdateContextEntity | skillmeat/web/hooks/use-context-entities.ts | createContextEntity, deleteContextEntity, fetchContextEntities, fetchContextEntity, fetchContextEntityContent, updateContextEntity | - |
| useUpdateGroup | skillmeat/web/hooks/use-groups.ts | apiConfig, apiRequest | - |
| useUpdateMcpServer | - | - | - |
| useUpdateMcpServer | skillmeat/web/hooks/useMcpServers.ts | apiRequest | - |
| useUpdatePathTagStatus | skillmeat/web/hooks/use-path-tags.ts | getPathTags, updatePathTagStatus | - |
| useUpdateProject | - | - | - |
| useUpdateProject | skillmeat/web/hooks/useProjects.ts | ApiError, apiConfig, apiRequest | - |
| useUpdateShareLink | skillmeat/web/hooks/useBundles.ts | apiConfig, apiRequest | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| useUpdateSource | - | - | - |
| useUpdateSource | skillmeat/web/hooks/useMarketplaceSources.ts | apiRequest, inferUrl, useToast | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| useUpdateTag | skillmeat/web/hooks/use-tags.ts | addTagToArtifact, createTag, deleteTag, fetchTags, getArtifactTags, removeTagFromArtifact, searchTags, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest, updateTag | - |
| useUpdateTemplate | skillmeat/web/hooks/use-templates.ts | createTemplate, deleteTemplate, deployTemplate, fetchTemplateById, fetchTemplates, updateTemplate | ['deployments'] |
| useUsageTrends | skillmeat/web/hooks/useAnalytics.ts | ApiError, apiConfig, apiRequest | - |
| useValidateExport | skillmeat/web/hooks/useExportBundle.ts | apiConfig, apiRequest | ['bundles'] |
| useValidateImport | skillmeat/web/hooks/useImportBundle.ts | apiConfig, apiRequest | ['artifacts'], ['bundle-preview', source], ['bundles'] |
| useVersionGraph | skillmeat/web/hooks/useVersionGraph.ts | apiRequest | - |
<!-- CODEBASE_GRAPH:HOOKS:END -->

## Canonical Hooks Registry

**Pattern**: All hooks are exported from `@/hooks` barrel export.

### Import Pattern

```typescript
// CORRECT - Use barrel import
import { useCollections, useGroups, useToast } from '@/hooks';
import type { CollectionFilters } from '@/hooks';

// WRONG - Direct file imports
import { useCollections } from '@/hooks/use-collections';
import { useGroups } from '@/hooks/use-groups';
```

### Barrel Export Location

**File**: `skillmeat/web/hooks/index.ts`

All hooks and their types are exported from this single entry point.

### Why Barrel Imports?

1. **Consistency**: Single import source for all hooks
2. **Refactoring**: Internal file structure can change without updating imports
3. **Tree-shaking**: Modern bundlers optimize barrel exports
4. **Discovery**: IDE autocomplete shows all available hooks

### Adding New Hooks

When creating a new hook:
1. Create the hook file in `hooks/` (e.g., `hooks/use-my-feature.ts`)
2. Export it from `hooks/index.ts`
3. Import from `@/hooks` in components

---

## Stub Pattern (Not Yet Implemented)

### Identifying Stubs

Hooks may throw `ApiError('Feature not yet implemented', 501)` immediately in mutation functions. These are **stubs** for Phase 4 implementation.

**Example Stub**:
```typescript
export function useUpdateCollection() {
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateCollectionRequest }) => {
      // TODO: Backend endpoint not yet implemented (Phase 4)
      throw new ApiError('Collection update not yet implemented', 501);
    },
  });
}
```

### Fix Pattern

When implementing a stubbed hook:

1. **Find the API client function** in `lib/api/{domain}.ts`
2. **Import and call it** instead of throwing
3. **Wire cache invalidation** in `onSuccess` callback
4. **Update types** if needed (add optional fields to match backend schema)

**Example Fix**:
```typescript
// Before (stub)
mutationFn: async (data: CreateCollectionRequest) => {
  throw new ApiError('Collection creation not yet implemented', 501);
}

// After (implemented)
import { createCollection } from '@/lib/api/collections';

mutationFn: async (data: CreateCollectionRequest) => {
  return createCollection(data);
}
```

### Recent Example: Collection Creation

**Issue**: `useCreateCollection()` threw stub error despite backend being fully implemented.

**Fix**:
1. **Endpoint change**: `/collections` (read-only) → `/user-collections` (full CRUD)
2. **Hook change**: Import `createCollection` from `@/lib/api/collections`
3. **Call**: `return createCollection(data)` instead of throwing
4. **Type update**: Added `description?: string` to `CreateCollectionRequest`

**Reference**: See `.claude/worknotes/bug-fixes-2025-12.md` (2025-12-13 entry)

---

## TanStack Query Conventions

### Query Key Factories

Use factory pattern for type-safe cache keys:

```typescript
export const collectionKeys = {
  all: ['collections'] as const,
  lists: () => [...collectionKeys.all, 'list'] as const,
  list: (filters?: CollectionFilters) => [...collectionKeys.lists(), filters] as const,
  details: () => [...collectionKeys.all, 'detail'] as const,
  detail: (id: string) => [...collectionKeys.details(), id] as const,
  artifacts: (id: string) => [...collectionKeys.detail(id), 'artifacts'] as const,
};
```

**Usage**:
```typescript
// In queries
queryKey: collectionKeys.list({ limit: 10 })

// In cache invalidation
queryClient.invalidateQueries({ queryKey: collectionKeys.all });
queryClient.invalidateQueries({ queryKey: collectionKeys.detail(id) });
```

**Benefits**:
- Type-safe key construction
- Centralized key management
- Easy hierarchical invalidation

### Stale Time Configuration

Default configuration (from `components/providers.tsx`):

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5 minutes
      retry: 1,
    },
  },
});
```

**Override when needed**:
```typescript
export function useCollections() {
  return useQuery({
    queryKey: collectionKeys.all,
    queryFn: fetchCollections,
    staleTime: 1 * 60 * 1000,  // 1 minute for frequently changing data
  });
}
```

### Cache Invalidation Patterns

**Invalidate all collections** (after create/delete):
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: collectionKeys.all });
}
```

**Invalidate specific collection** (after update):
```typescript
onSuccess: (_, { id }) => {
  queryClient.invalidateQueries({ queryKey: collectionKeys.detail(id) });
  queryClient.invalidateQueries({ queryKey: collectionKeys.lists() });
}
```

**Invalidate collection artifacts** (after add/remove artifact):
```typescript
onSuccess: (_, { collectionId }) => {
  queryClient.invalidateQueries({ queryKey: collectionKeys.artifacts(collectionId) });
  queryClient.invalidateQueries({ queryKey: collectionKeys.detail(collectionId) });
}
```

---

## API Client Mapping

Hooks call corresponding functions in `lib/api/{domain}.ts`:

| Hook Domain | API Client File |
|-------------|----------------|
| `use-collections.ts` | `lib/api/collections.ts` |
| `use-groups.ts` | `lib/api/groups.ts` |
| `use-deployments.ts` | `lib/api/deployments.ts` |

**Import Pattern**:
```typescript
import { createCollection, updateCollection } from '@/lib/api/collections';
```

---

## Hook Structure Template

```typescript
/**
 * Hook description
 */
export function useEntityAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: EntityRequest): Promise<EntityResponse> => {
      // Call API client function (NOT inline fetch)
      return apiClientFunction(data);
    },
    onSuccess: (data, variables) => {
      // Invalidate relevant cache keys
      queryClient.invalidateQueries({ queryKey: entityKeys.all });
    },
    onError: (error) => {
      // Optional: Add toast notification
      console.error('Operation failed:', error);
    },
  });
}
```

---

## Common Antipatterns

❌ **Inline fetch in hooks**:
```typescript
// BAD: Inline fetch logic
mutationFn: async (data) => {
  const response = await fetch('/api/v1/collections', { ... });
  return response.json();
}
```

✅ **Use API client**:
```typescript
// GOOD: Call API client function
import { createCollection } from '@/lib/api/collections';
mutationFn: async (data) => createCollection(data)
```

❌ **Generic cache invalidation**:
```typescript
// BAD: Invalidates too much
queryClient.invalidateQueries();
```

✅ **Targeted invalidation**:
```typescript
// GOOD: Invalidates only what changed
queryClient.invalidateQueries({ queryKey: collectionKeys.detail(id) });
```

❌ **Leaving stubs in production**:
```typescript
// BAD: Stub still throwing error
throw new ApiError('Not implemented', 501);
```

✅ **Implement or remove**:
```typescript
// GOOD: Call real API or remove hook
return apiClientFunction(data);
```

---

## Error Handling

All hooks use `ApiError` from `lib/api.ts`:

```typescript
export class ApiError extends Error {
  status: number;
  body?: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}
```

**Usage in hooks**:
```typescript
mutationFn: async (data) => {
  try {
    return await apiClientFunction(data);
  } catch (error) {
    if (error instanceof ApiError) {
      // Handle API-specific errors
      throw error;
    }
    // Re-wrap generic errors
    throw new ApiError('Operation failed', 500);
  }
}
```

---

## Testing Hooks

Use `@testing-library/react-hooks` for hook tests:

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCollections } from '@/hooks/use-collections';

describe('useCollections', () => {
  it('fetches collections', async () => {
    const queryClient = new QueryClient();
    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useCollections(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeDefined();
  });
});
```

---

## Reference

- **TanStack Query Docs**: https://tanstack.com/query/latest
- **Stub Detection**: Look for `throw new ApiError(..., 501)`
- **API Client Location**: `skillmeat/web/lib/api/{domain}.ts`
- **Bug Fixes Log**: `.claude/worknotes/bug-fixes-2025-12.md`
