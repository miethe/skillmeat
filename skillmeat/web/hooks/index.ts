/**
 * Hooks Registry - Canonical central export point for all SkillMeat hooks
 *
 * This is the single source of truth for hook exports. All imports should use:
 *
 *   import { useCollections } from '@/hooks';
 *
 * NOT individual file imports:
 *
 *   import { useCollections } from '@/hooks/use-collections';  // ✗ Still works but prefer registry
 *
 * ## Adding New Hooks
 *
 * 1. Create hook file in appropriate domain:
 *    - If it matches a domain (collections, groups, etc.), add to existing file
 *    - If it's a utility, create `use-{name}.ts` in kebab-case
 *
 * 2. Add export to this file in appropriate section
 *
 * 3. If it has a query key factory, export that too (see patterns below)
 *
 * 4. Update domain section comment if it affects hook count
 *
 * ## Organization
 *
 * Hooks are organized by domain with clear section comments:
 * - Collections (CRUD + artifacts)
 * - Groups (CRUD + artifacts)
 * - Deployments (CRUD + deploy/undeploy)
 * - Artifacts (list + bulk import)
 * - Projects (CRUD + discovery + caching)
 * - Bundles (CRUD + export/import + analytics)
 * - Cache (refresh + status)
 * - Marketplace (listings + sources)
 * - MCP (servers + deployment)
 * - Snapshots (CRUD + rollback + diff)
 * - Tags (CRUD + search + artifact tags)
 * - Templates (CRUD + deploy)
 * - Sync (push + pull + conflict resolution)
 * - Context Entities (CRUD + content)
 * - Context Sync (status + changes + merge)
 * - Catalog (file tree + content)
 * - Discovery (GitHub + discovery + parameters)
 * - Analytics (summary + trends + stream)
 * - SSE (real-time event streaming)
 * - Utility Hooks (debounce, toast, focus trap, etc.)
 * - Context Hooks (collection context + entity lifecycle)
 *
 * See `.claude/analysis/hooks-structure-analysis.md` for detailed inventory.
 */

// ============================================================================
// COLLECTIONS (9 hooks)
// ============================================================================
// Collection CRUD operations with artifact management
export {
  collectionKeys,
  useCollections,
  useCollection,
  useCollectionArtifacts,
  useInfiniteCollectionArtifacts,
  useCreateCollection,
  useUpdateCollection,
  useDeleteCollection,
  useAddArtifactToCollection,
  useRemoveArtifactFromCollection,
  type InfiniteArtifactsOptions,
} from './use-collections';

// ============================================================================
// GROUPS (12 hooks)
// ============================================================================
// Group CRUD operations with artifact ordering and management
export {
  groupKeys,
  useGroups,
  useGroup,
  useGroupArtifacts,
  useCreateGroup,
  useUpdateGroup,
  useDeleteGroup,
  useReorderGroups,
  useAddArtifactToGroup,
  useRemoveArtifactFromGroup,
  useReorderArtifactsInGroup,
  useMoveArtifactToGroup,
  useCopyGroup,
} from './use-groups';

// ============================================================================
// DEPLOYMENTS (6 hooks)
// ============================================================================
// Artifact deployment and undeployment operations
export {
  deploymentKeys,
  useDeploymentList,
  useDeployments,
  useDeploymentSummary,
  useDeployArtifact,
  useUndeployArtifact,
  useRefreshDeployments,
} from './use-deployments';

/**
 * @deprecated Use `useDeployArtifact` and `useUndeployArtifact` from `use-deployments.ts` instead.
 * This hook duplicates functionality from the deployments module.
 */
export { useDeploy, useUndeploy } from './useDeploy';

// ============================================================================
// ARTIFACTS (5 hooks)
// ============================================================================
// Core artifact operations, bulk import, and infinite scroll
export {
  useArtifacts,
  useArtifact,
  useUpdateArtifact,
  useDeleteArtifact,
  useInfiniteArtifacts,
  type InfiniteAllArtifactsOptions,
} from './useArtifacts';

// ============================================================================
// PROJECTS (7 hooks)
// ============================================================================
// Project CRUD, discovery, and caching operations
export {
  projectKeys,
  useProjects,
  useProject,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
} from './useProjects';

export { useProjectDiscovery, useConfirmDuplicates } from './useProjectDiscovery';
export { useProjectCache } from './useProjectCache';

// ============================================================================
// BUNDLES (7+ hooks)
// ============================================================================
// Bundle CRUD, analytics, sharing, export/import operations
export {
  useBundles,
  useBundleAnalytics,
  useDeleteBundle,
  useUpdateShareLink,
  useRevokeShareLink,
} from './useBundles';

export {
  useExportBundle,
  useValidateExport,
} from './useExportBundle';

export {
  usePreviewBundle,
  useImportBundle,
  useValidateImport,
} from './useImportBundle';

// ============================================================================
// CACHE (2 hooks)
// ============================================================================
// Cache refresh and status operations
export {
  useCacheRefresh,
} from './useCacheRefresh';

export {
  useCacheStatus,
} from './useCacheStatus';

// ============================================================================
// MARKETPLACE (5 hooks + 13 source hooks)
// ============================================================================
// Marketplace listings, brokers, and artifact sourcing
export {
  useListings,
  useListing,
  useBrokers,
  useInstallListing,
  usePublishBundle,
} from './useMarketplace';

export {
  sourceKeys,
  useSources,
  useSource,
  useCreateSource,
  useUpdateSource,
  useDeleteSource,
  useRescanSource,
  useSourceCatalog,
  useImportArtifacts,
  useImportAllMatching,
  useUpdateCatalogEntryName,
  useExcludeCatalogEntry,
  useRestoreCatalogEntry,
  useInferUrl,
} from './useMarketplaceSources';

// ============================================================================
// MCP (9 hooks)
// ============================================================================
// MCP server management and deployment
export {
  mcpQueryKeys,
  useMcpServers,
  useMcpServer,
  useMcpDeploymentStatus,
  useCreateMcpServer,
  useUpdateMcpServer,
  useDeleteMcpServer,
  useDeployMcpServer,
  useUndeployMcpServer,
  useMcpBatchOperations,
} from './useMcpServers';

// ============================================================================
// SNAPSHOTS (7 hooks)
// ============================================================================
// Snapshot CRUD, comparison, and rollback operations
export {
  snapshotKeys,
  useSnapshots,
  useSnapshot,
  useRollbackAnalysis,
  useCreateSnapshot,
  useDeleteSnapshot,
  useRollback,
  useDiffSnapshots,
} from './use-snapshots';

// ============================================================================
// TAGS (8 hooks)
// ============================================================================
// Tag CRUD, search, and artifact tagging operations
export {
  tagKeys,
  useTags,
  useSearchTags,
  useArtifactTags,
  useCreateTag,
  useUpdateTag,
  useDeleteTag,
  useAddTagToArtifact,
  useRemoveTagFromArtifact,
} from './use-tags';

// ============================================================================
// TEMPLATES (7 hooks)
// ============================================================================
// Template CRUD and deployment operations
export {
  templateKeys,
  useTemplates,
  useTemplate,
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
  useDeployTemplate,
} from './use-templates';

// ============================================================================
// SYNC (3 hooks)
// ============================================================================
// Synchronization and upstream change detection
export {
  useSync,
  useCheckUpstream,
  type ConflictInfo,
  type SyncRequest,
  type SyncResponse,
  type SyncError,
  type UseSyncOptions,
} from './useSync';

// ============================================================================
// CONTEXT ENTITIES (6 hooks)
// ============================================================================
// Context-bound entity CRUD operations
export {
  contextEntityKeys,
  useContextEntities,
  useContextEntity,
  useContextEntityContent,
  useCreateContextEntity,
  useUpdateContextEntity,
  useDeleteContextEntity,
  useDeployContextEntity,
} from './use-context-entities';

// ============================================================================
// CONTEXT SYNC (5 hooks)
// ============================================================================
// Context synchronization, change tracking, and conflict resolution
export {
  useContextSyncStatus,
  usePendingContextChanges,
  usePullContextChanges,
  usePushContextChanges,
  useResolveContextConflict,
} from './use-context-sync';

// ============================================================================
// CATALOG (2 hooks)
// ============================================================================
// Catalog file tree and content retrieval
export {
  catalogKeys,
  useCatalogFileTree,
  useCatalogFileContent,
} from './use-catalog-files';

// ============================================================================
// DISCOVERY (3 hooks)
// ============================================================================
// GitHub metadata, artifact discovery, and parameter editing
export {
  useDiscovery,
  useGitHubMetadata,
  useEditArtifactParameters,
} from './useDiscovery';

// ============================================================================
// ANALYTICS (5 hooks)
// ============================================================================
// Usage analytics, trends, and streaming analytics
export {
  useAnalyticsSummary,
  useTopArtifacts,
  useUsageTrends,
} from './useAnalytics';

export {
  useAnalyticsStream,
} from './useAnalyticsStream';

// ============================================================================
// SSE (1 hook)
// ============================================================================
// Server-sent events for real-time data streaming
export {
  useSSE,
} from './useSSE';

// ============================================================================
// UTILITY HOOKS
// ============================================================================

/**
 * Debounce a value with specified delay
 * @example
 * const debouncedSearchTerm = useDebounce(searchTerm, 500);
 */
export {
  useDebounce,
} from './use-debounce';

/**
 * Intersection observer for detecting element visibility
 * Useful for infinite scroll and lazy loading
 * @example
 * const { targetRef, isIntersecting } = useIntersectionObserver({ rootMargin: '100px' });
 */
export {
  useIntersectionObserver,
  type UseIntersectionObserverOptions,
  type UseIntersectionObserverResult,
} from './use-intersection-observer';

/**
 * Toast notification hook (shadcn/ui integration)
 * @example
 * const { toast } = useToast();
 * toast({ title: "Success", description: "Saved!" });
 */
export {
  useToast,
} from './use-toast';

/**
 * Alternative toast notification API
 */
export {
  useToastNotification,
} from './use-toast-notification';

/**
 * Focus trap for modal dialogs and accessibility
 */
export {
  useFocusTrap,
} from './useFocusTrap';

/**
 * Artifact deletion with confirmation
 */
export {
  useArtifactDeletion,
  type DeletionResult,
} from './use-artifact-deletion';

/**
 * Bulk tag application to multiple artifacts
 */
export {
  bulkTagKeys,
  useBulkTagApply,
} from './use-bulk-tag-apply';

/**
 * Path-based tag operations
 */
export {
  pathTagKeys,
  usePathTags,
  useUpdatePathTagStatus,
} from './use-path-tags';

/**
 * Merge operations for collections and contexts
 */
export {
  mergeKeys,
  useAnalyzeMerge,
  usePreviewMerge,
  useExecuteMerge,
  useResolveConflict,
} from './use-merge';

/**
 * Outdated artifact detection and updates
 */
export {
  useOutdatedArtifacts,
} from './useOutdatedArtifacts';

/**
 * Version graph visualization for artifact history
 */
export {
  versionKeys,
  useVersionGraph,
} from './useVersionGraph';

// ============================================================================
// CONTEXT HOOKS
// ============================================================================

/**
 * Collection-scoped context provider and hook
 * Use within CollectionProvider component
 */
export {
  useCollectionContext,
} from './use-collection-context';

/**
 * Entity lifecycle provider and hook
 * Manages entity creation, updates, and deletion in React context
 */
export {
  EntityLifecycleProvider,
  useEntityLifecycle,
} from './useEntityLifecycle';
