<!-- Path Scope: skillmeat/web/hooks/**/*.ts -->

# Web Frontend Hooks - Inventory

<!-- CODEBASE_GRAPH:HOOKS:START -->
| Hook | File | API Clients | Query Keys |
| --- | --- | --- | --- |
| <span title="Add artifact to collection mutation">useAddArtifactToCollection</span> | skillmeat/web/hooks/use-collections.ts | <span title="Add artifact to collection">addArtifactToCollection</span>, <span title="Create new collection">createCollection</span>, <span title="Delete collection">deleteCollection</span>, <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span>, <span title="Remove artifact from collection">removeArtifactFromCollection</span>, <span title="Update existing collection">updateCollection</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, type CollectionArtifactsPaginatedResponse | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| <span title="Add artifact to group mutation">useAddArtifactToGroup</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Add tag to artifact mutation">useAddTagToArtifact</span> | skillmeat/web/hooks/use-tags.ts | <span title="Add tag to artifact">addTagToArtifact</span>, <span title="Create new tag">createTag</span>, <span title="Delete tag">deleteTag</span>, <span title="Fetch all tags with pagination">fetchTags</span>, <span title="Get all tags for an artifact">getArtifactTags</span>, <span title="Remove tag from artifact">removeTagFromArtifact</span>, <span title="Search tags by query string">searchTags</span>, <span title="Update existing tag">updateTag</span>, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest | - |
| <span title="Analyze rollback safety for a snapshot">useRollbackAnalysis</span> | skillmeat/web/hooks/use-snapshots.ts | <span title="Analyze rollback safety for a snapshot">analyzeRollbackSafety</span>, <span title="Compare two snapshots and get diff">diffSnapshots</span>, <span title="Create new version snapshot">createSnapshot</span>, <span title="Delete snapshot by ID">deleteSnapshot</span>, <span title="Execute rollback to a snapshot">executeRollback</span>, <span title="Fetch paginated list of snapshots">fetchSnapshots</span>, <span title="Fetch single snapshot by ID">fetchSnapshot</span> | ['artifacts'], ['collections'] |
| <span title="Bulk select helper - import all matching entries">useImportAllMatching</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Compare two snapshots mutation">useDiffSnapshots</span> | skillmeat/web/hooks/use-snapshots.ts | <span title="Analyze rollback safety for a snapshot">analyzeRollbackSafety</span>, <span title="Compare two snapshots and get diff">diffSnapshots</span>, <span title="Create new version snapshot">createSnapshot</span>, <span title="Delete snapshot by ID">deleteSnapshot</span>, <span title="Execute rollback to a snapshot">executeRollback</span>, <span title="Fetch paginated list of snapshots">fetchSnapshots</span>, <span title="Fetch single snapshot by ID">fetchSnapshot</span> | ['artifacts'], ['collections'] |
| <span title="Create a new MCP server">useCreateMcpServer</span> | skillmeat/web/hooks/useMcpServers.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Create new GitHub source">useCreateSource</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Create new collection mutation">useCreateCollection</span> | skillmeat/web/hooks/use-collections.ts | <span title="Add artifact to collection">addArtifactToCollection</span>, <span title="Create new collection">createCollection</span>, <span title="Delete collection">deleteCollection</span>, <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span>, <span title="Remove artifact from collection">removeArtifactFromCollection</span>, <span title="Update existing collection">updateCollection</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, type CollectionArtifactsPaginatedResponse | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| <span title="Create new context entity mutation">useCreateContextEntity</span> | skillmeat/web/hooks/use-context-entities.ts | <span title="Create new context entity">createContextEntity</span>, <span title="Delete context entity">deleteContextEntity</span>, <span title="Fetch context entities with optional filtering">fetchContextEntities</span>, <span title="Fetch raw markdown content for a context entity">fetchContextEntityContent</span>, <span title="Fetch single context entity by ID">fetchContextEntity</span>, <span title="Update existing context entity">updateContextEntity</span> | - |
| <span title="Create new group mutation">useCreateGroup</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Create new tag mutation">useCreateTag</span> | skillmeat/web/hooks/use-tags.ts | <span title="Add tag to artifact">addTagToArtifact</span>, <span title="Create new tag">createTag</span>, <span title="Delete tag">deleteTag</span>, <span title="Fetch all tags with pagination">fetchTags</span>, <span title="Get all tags for an artifact">getArtifactTags</span>, <span title="Remove tag from artifact">removeTagFromArtifact</span>, <span title="Search tags by query string">searchTags</span>, <span title="Update existing tag">updateTag</span>, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest | - |
| <span title="Create new template">useCreateTemplate</span> | skillmeat/web/hooks/use-templates.ts | <span title="Create new template">createTemplate</span>, <span title="Delete template">deleteTemplate</span>, <span title="Deploy template to a project">deployTemplate</span>, <span title="Fetch all templates with optional filtering and pagination">fetchTemplates</span>, <span title="Fetch template by ID with full entity details">fetchTemplateById</span>, <span title="Update existing template">updateTemplate</span> | ['deployments'] |
| <span title="Create new version snapshot mutation">useCreateSnapshot</span> | skillmeat/web/hooks/use-snapshots.ts | <span title="Analyze rollback safety for a snapshot">analyzeRollbackSafety</span>, <span title="Compare two snapshots and get diff">diffSnapshots</span>, <span title="Create new version snapshot">createSnapshot</span>, <span title="Delete snapshot by ID">deleteSnapshot</span>, <span title="Execute rollback to a snapshot">executeRollback</span>, <span title="Fetch paginated list of snapshots">fetchSnapshots</span>, <span title="Fetch single snapshot by ID">fetchSnapshot</span> | ['artifacts'], ['collections'] |
| <span title="Debounce a value by delaying updates until the specified delay has passed.">useDebounce</span> | skillmeat/web/hooks/use-debounce.ts | - | - |
| <span title="Delete GitHub source">useDeleteSource</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Delete an MCP server">useDeleteMcpServer</span> | skillmeat/web/hooks/useMcpServers.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Delete collection mutation">useDeleteCollection</span> | skillmeat/web/hooks/use-collections.ts | <span title="Add artifact to collection">addArtifactToCollection</span>, <span title="Create new collection">createCollection</span>, <span title="Delete collection">deleteCollection</span>, <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span>, <span title="Remove artifact from collection">removeArtifactFromCollection</span>, <span title="Update existing collection">updateCollection</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, type CollectionArtifactsPaginatedResponse | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| <span title="Delete context entity mutation">useDeleteContextEntity</span> | skillmeat/web/hooks/use-context-entities.ts | <span title="Create new context entity">createContextEntity</span>, <span title="Delete context entity">deleteContextEntity</span>, <span title="Fetch context entities with optional filtering">fetchContextEntities</span>, <span title="Fetch raw markdown content for a context entity">fetchContextEntityContent</span>, <span title="Fetch single context entity by ID">fetchContextEntity</span>, <span title="Update existing context entity">updateContextEntity</span> | - |
| <span title="Delete group mutation">useDeleteGroup</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Delete snapshot mutation">useDeleteSnapshot</span> | skillmeat/web/hooks/use-snapshots.ts | <span title="Analyze rollback safety for a snapshot">analyzeRollbackSafety</span>, <span title="Compare two snapshots and get diff">diffSnapshots</span>, <span title="Create new version snapshot">createSnapshot</span>, <span title="Delete snapshot by ID">deleteSnapshot</span>, <span title="Execute rollback to a snapshot">executeRollback</span>, <span title="Fetch paginated list of snapshots">fetchSnapshots</span>, <span title="Fetch single snapshot by ID">fetchSnapshot</span> | ['artifacts'], ['collections'] |
| <span title="Delete tag mutation">useDeleteTag</span> | skillmeat/web/hooks/use-tags.ts | <span title="Add tag to artifact">addTagToArtifact</span>, <span title="Create new tag">createTag</span>, <span title="Delete tag">deleteTag</span>, <span title="Fetch all tags with pagination">fetchTags</span>, <span title="Get all tags for an artifact">getArtifactTags</span>, <span title="Remove tag from artifact">removeTagFromArtifact</span>, <span title="Search tags by query string">searchTags</span>, <span title="Update existing tag">updateTag</span>, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest | - |
| <span title="Delete template">useDeleteTemplate</span> | skillmeat/web/hooks/use-templates.ts | <span title="Create new template">createTemplate</span>, <span title="Delete template">deleteTemplate</span>, <span title="Deploy template to a project">deployTemplate</span>, <span title="Fetch all templates with optional filtering and pagination">fetchTemplates</span>, <span title="Fetch template by ID with full entity details">fetchTemplateById</span>, <span title="Update existing template">updateTemplate</span> | ['deployments'] |
| <span title="Deploy an MCP server to Claude Desktop">useDeployMcpServer</span> | skillmeat/web/hooks/useMcpServers.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Deploy an artifact to a project mutation">useDeployArtifact</span> | skillmeat/web/hooks/use-deployments.ts | <span title="Deploy an artifact to a project">deployArtifact</span>, <span title="Get deployment summary statistics">getDeploymentSummary</span>, <span title="Get deployments with optional filtering">getDeployments</span>, <span title="List all deployed artifacts in a project">listDeployments</span>, <span title="Undeploy (remove) an artifact from a project">undeployArtifact</span>, type DeploymentQueryParams, type DeploymentSummary | - |
| <span title="Deploy template to a project">useDeployTemplate</span> | skillmeat/web/hooks/use-templates.ts | <span title="Create new template">createTemplate</span>, <span title="Delete template">deleteTemplate</span>, <span title="Deploy template to a project">deployTemplate</span>, <span title="Fetch all templates with optional filtering and pagination">fetchTemplates</span>, <span title="Fetch template by ID with full entity details">fetchTemplateById</span>, <span title="Update existing template">updateTemplate</span> | ['deployments'] |
| <span title="Execute rollback to snapshot mutation">useRollback</span> | skillmeat/web/hooks/use-snapshots.ts | <span title="Analyze rollback safety for a snapshot">analyzeRollbackSafety</span>, <span title="Compare two snapshots and get diff">diffSnapshots</span>, <span title="Create new version snapshot">createSnapshot</span>, <span title="Delete snapshot by ID">deleteSnapshot</span>, <span title="Execute rollback to a snapshot">executeRollback</span>, <span title="Fetch paginated list of snapshots">fetchSnapshots</span>, <span title="Fetch single snapshot by ID">fetchSnapshot</span> | ['artifacts'], ['collections'] |
| <span title="Fetch a specific MCP server by name">useMcpServer</span> | skillmeat/web/hooks/useMcpServers.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Fetch all GitHub sources with infinite scroll pagination">useSources</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Fetch all MCP servers in a collection">useMcpServers</span> | skillmeat/web/hooks/useMcpServers.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Fetch all collections with optional filtering and pagination">useCollections</span> | skillmeat/web/hooks/use-collections.ts | <span title="Add artifact to collection">addArtifactToCollection</span>, <span title="Create new collection">createCollection</span>, <span title="Delete collection">deleteCollection</span>, <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span>, <span title="Remove artifact from collection">removeArtifactFromCollection</span>, <span title="Update existing collection">updateCollection</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, type CollectionArtifactsPaginatedResponse | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| <span title="Fetch all tags for a specific artifact">useArtifactTags</span> | skillmeat/web/hooks/use-tags.ts | <span title="Add tag to artifact">addTagToArtifact</span>, <span title="Create new tag">createTag</span>, <span title="Delete tag">deleteTag</span>, <span title="Fetch all tags with pagination">fetchTags</span>, <span title="Get all tags for an artifact">getArtifactTags</span>, <span title="Remove tag from artifact">removeTagFromArtifact</span>, <span title="Search tags by query string">searchTags</span>, <span title="Update existing tag">updateTag</span>, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest | - |
| <span title="Fetch all tags with optional pagination">useTags</span> | skillmeat/web/hooks/use-tags.ts | <span title="Add tag to artifact">addTagToArtifact</span>, <span title="Create new tag">createTag</span>, <span title="Delete tag">deleteTag</span>, <span title="Fetch all tags with pagination">fetchTags</span>, <span title="Get all tags for an artifact">getArtifactTags</span>, <span title="Remove tag from artifact">removeTagFromArtifact</span>, <span title="Search tags by query string">searchTags</span>, <span title="Update existing tag">updateTag</span>, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest | - |
| <span title="Fetch all templates with optional filtering and pagination">useTemplates</span> | skillmeat/web/hooks/use-templates.ts | <span title="Create new template">createTemplate</span>, <span title="Delete template">deleteTemplate</span>, <span title="Deploy template to a project">deployTemplate</span>, <span title="Fetch all templates with optional filtering and pagination">fetchTemplates</span>, <span title="Fetch template by ID with full entity details">fetchTemplateById</span>, <span title="Update existing template">updateTemplate</span> | ['deployments'] |
| <span title="Fetch artifacts in a collection with pagination">useCollectionArtifacts</span> | skillmeat/web/hooks/use-collections.ts | <span title="Add artifact to collection">addArtifactToCollection</span>, <span title="Create new collection">createCollection</span>, <span title="Delete collection">deleteCollection</span>, <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span>, <span title="Remove artifact from collection">removeArtifactFromCollection</span>, <span title="Update existing collection">updateCollection</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, type CollectionArtifactsPaginatedResponse | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| <span title="Fetch artifacts in a group">useGroupArtifacts</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Fetch collection artifacts with infinite scroll pagination">useInfiniteCollectionArtifacts</span> | skillmeat/web/hooks/use-collections.ts | <span title="Add artifact to collection">addArtifactToCollection</span>, <span title="Create new collection">createCollection</span>, <span title="Delete collection">deleteCollection</span>, <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span>, <span title="Remove artifact from collection">removeArtifactFromCollection</span>, <span title="Update existing collection">updateCollection</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, type CollectionArtifactsPaginatedResponse | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| <span title="Fetch content of a specific file from a catalog artifact">useCatalogFileContent</span> | skillmeat/web/hooks/use-catalog-files.ts | <span title="Fetch content of a specific file from a catalog artifact">fetchCatalogFileContent</span>, <span title="Fetch file tree for a catalog artifact">fetchCatalogFileTree</span>, type FileContentResponse, type FileTreeResponse | - |
| <span title="Fetch context entities with optional filtering and pagination">useContextEntities</span> | skillmeat/web/hooks/use-context-entities.ts | <span title="Create new context entity">createContextEntity</span>, <span title="Delete context entity">deleteContextEntity</span>, <span title="Fetch context entities with optional filtering">fetchContextEntities</span>, <span title="Fetch raw markdown content for a context entity">fetchContextEntityContent</span>, <span title="Fetch single context entity by ID">fetchContextEntity</span>, <span title="Update existing context entity">updateContextEntity</span> | - |
| <span title="Fetch deployment status for an MCP server">useMcpDeploymentStatus</span> | skillmeat/web/hooks/useMcpServers.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Fetch file tree for a catalog artifact">useCatalogFileTree</span> | skillmeat/web/hooks/use-catalog-files.ts | <span title="Fetch content of a specific file from a catalog artifact">fetchCatalogFileContent</span>, <span title="Fetch file tree for a catalog artifact">fetchCatalogFileTree</span>, type FileContentResponse, type FileTreeResponse | - |
| <span title="Fetch groups for a collection">useGroups</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Fetch paginated list of snapshots with optional filtering">useSnapshots</span> | skillmeat/web/hooks/use-snapshots.ts | <span title="Analyze rollback safety for a snapshot">analyzeRollbackSafety</span>, <span title="Compare two snapshots and get diff">diffSnapshots</span>, <span title="Create new version snapshot">createSnapshot</span>, <span title="Delete snapshot by ID">deleteSnapshot</span>, <span title="Execute rollback to a snapshot">executeRollback</span>, <span title="Fetch paginated list of snapshots">fetchSnapshots</span>, <span title="Fetch single snapshot by ID">fetchSnapshot</span> | ['artifacts'], ['collections'] |
| <span title="Fetch path tag segments for a marketplace catalog entry">usePathTags</span> | skillmeat/web/hooks/use-path-tags.ts | <span title="Get extracted path tag segments for a marketplace catalog entry">getPathTags</span>, <span title="Update status of a specific path tag segment (approve or reject)">updatePathTagStatus</span> | - |
| <span title="Fetch raw markdown content for a context entity">useContextEntityContent</span> | skillmeat/web/hooks/use-context-entities.ts | <span title="Create new context entity">createContextEntity</span>, <span title="Delete context entity">deleteContextEntity</span>, <span title="Fetch context entities with optional filtering">fetchContextEntities</span>, <span title="Fetch raw markdown content for a context entity">fetchContextEntityContent</span>, <span title="Fetch single context entity by ID">fetchContextEntity</span>, <span title="Update existing context entity">updateContextEntity</span> | - |
| <span title="Fetch single collection by ID">useCollection</span> | skillmeat/web/hooks/use-collections.ts | <span title="Add artifact to collection">addArtifactToCollection</span>, <span title="Create new collection">createCollection</span>, <span title="Delete collection">deleteCollection</span>, <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span>, <span title="Remove artifact from collection">removeArtifactFromCollection</span>, <span title="Update existing collection">updateCollection</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, type CollectionArtifactsPaginatedResponse | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| <span title="Fetch single context entity by ID">useContextEntity</span> | skillmeat/web/hooks/use-context-entities.ts | <span title="Create new context entity">createContextEntity</span>, <span title="Delete context entity">deleteContextEntity</span>, <span title="Fetch context entities with optional filtering">fetchContextEntities</span>, <span title="Fetch raw markdown content for a context entity">fetchContextEntityContent</span>, <span title="Fetch single context entity by ID">fetchContextEntity</span>, <span title="Update existing context entity">updateContextEntity</span> | - |
| <span title="Fetch single group by ID with full details">useGroup</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Fetch single snapshot by ID">useSnapshot</span> | skillmeat/web/hooks/use-snapshots.ts | <span title="Analyze rollback safety for a snapshot">analyzeRollbackSafety</span>, <span title="Compare two snapshots and get diff">diffSnapshots</span>, <span title="Create new version snapshot">createSnapshot</span>, <span title="Delete snapshot by ID">deleteSnapshot</span>, <span title="Execute rollback to a snapshot">executeRollback</span>, <span title="Fetch paginated list of snapshots">fetchSnapshots</span>, <span title="Fetch single snapshot by ID">fetchSnapshot</span> | ['artifacts'], ['collections'] |
| <span title="Fetch single source by ID">useSource</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Fetch source catalog with filters and pagination">useSourceCatalog</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Fetch template by ID with full entity details">useTemplate</span> | skillmeat/web/hooks/use-templates.ts | <span title="Create new template">createTemplate</span>, <span title="Delete template">deleteTemplate</span>, <span title="Deploy template to a project">deployTemplate</span>, <span title="Fetch all templates with optional filtering and pagination">fetchTemplates</span>, <span title="Fetch template by ID with full entity details">fetchTemplateById</span>, <span title="Update existing template">updateTemplate</span> | ['deployments'] |
| <span title="Get deployment summary statistics">useDeploymentSummary</span> | skillmeat/web/hooks/use-deployments.ts | <span title="Deploy an artifact to a project">deployArtifact</span>, <span title="Get deployment summary statistics">getDeploymentSummary</span>, <span title="Get deployments with optional filtering">getDeployments</span>, <span title="List all deployed artifacts in a project">listDeployments</span>, <span title="Undeploy (remove) an artifact from a project">undeployArtifact</span>, type DeploymentQueryParams, type DeploymentSummary | - |
| <span title="Get deployments with optional filtering">useDeployments</span> | skillmeat/web/hooks/use-deployments.ts | <span title="Deploy an artifact to a project">deployArtifact</span>, <span title="Get deployment summary statistics">getDeploymentSummary</span>, <span title="Get deployments with optional filtering">getDeployments</span>, <span title="List all deployed artifacts in a project">listDeployments</span>, <span title="Undeploy (remove) an artifact from a project">undeployArtifact</span>, type DeploymentQueryParams, type DeploymentSummary | - |
| <span title="Hook for artifact discovery and bulk import operations">useDiscovery</span> | skillmeat/web/hooks/useDiscovery.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['artifacts', 'detail', artifactId], ['artifacts', 'discover'], ['artifacts', 'list'], ['artifacts'], ['entities'] |
| <span title="Hook for batch operations (select multiple servers)">useMcpBatchOperations</span> | skillmeat/web/hooks/useMcpServers.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Hook for bulk tag application to catalog entries by directory">useBulkTagApply</span> | skillmeat/web/hooks/use-bulk-tag-apply.ts | <span title="Query keys factory">sourceKeys</span>, <span title="export function useToast()">useToast</span> | - |
| <span title="Hook for confirming duplicate decisions during artifact import.">useConfirmDuplicates</span> | skillmeat/web/hooks/useProjectDiscovery.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['artifacts', 'discover', 'project', projectPath], ['artifacts', 'discover', 'project', variables.project_path], ['artifacts'], ['projects', 'detail', projectId] |
| <span title="Hook for discovering artifacts in a specific project's .claude/ directory.">useProjectDiscovery</span> | skillmeat/web/hooks/useProjectDiscovery.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['artifacts', 'discover', 'project', projectPath], ['artifacts', 'discover', 'project', variables.project_path], ['artifacts'], ['projects', 'detail', projectId] |
| <span title="Hook for editing artifact parameters">useEditArtifactParameters</span> | skillmeat/web/hooks/useDiscovery.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['artifacts', 'detail', artifactId], ['artifacts', 'discover'], ['artifacts', 'list'], ['artifacts'], ['entities'] |
| <span title="Hook for fetching GitHub metadata for an artifact source">useGitHubMetadata</span> | skillmeat/web/hooks/useDiscovery.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['artifacts', 'detail', artifactId], ['artifacts', 'discover'], ['artifacts', 'list'], ['artifacts'], ['entities'] |
| <span title="Hook for orchestrating artifact deletion across collection and projects">useArtifactDeletion</span> | skillmeat/web/hooks/use-artifact-deletion.ts | <span title="Delete artifact from collection">deleteArtifactFromCollection</span>, <span title="Undeploy (remove) an artifact from a project">undeployArtifact</span> | ['artifacts'], ['collections'], ['deployments'], ['projects'] |
| <span title="Hook that combines toast notifications with persistent notification store">useToastNotification</span> | skillmeat/web/hooks/use-toast-notification.ts | - | - |
| <span title="Hook to access the CollectionContext">useCollectionContext</span> | skillmeat/web/hooks/use-collection-context.ts | - | - |
| <span title="Hook to analyze merge safety">useAnalyzeMerge</span> | skillmeat/web/hooks/use-merge.ts | <span title="Analyze merge safety between snapshots">analyzeMergeSafety</span>, <span title="Execute merge between snapshots">executeMerge</span>, <span title="Preview merge changes between snapshots">previewMerge</span>, <span title="Resolve a merge conflict">resolveConflict</span> | ['collections', variables.localCollection], ['snapshots'] |
| <span title="Hook to create a new project">useCreateProject</span> | skillmeat/web/hooks/useProjects.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Hook to delete a bundle">useDeleteBundle</span> | skillmeat/web/hooks/useBundles.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| <span title="Hook to delete a project">useDeleteProject</span> | skillmeat/web/hooks/useProjects.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Hook to delete an artifact">useDeleteArtifact</span> | skillmeat/web/hooks/useArtifacts.ts | <span title="Fetch paginated artifacts from collection">fetchArtifactsPaginated</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span>, type ArtifactsPaginatedResponse | ['artifacts', 'infinite', filters] |
| <span title="Hook to deploy artifacts to projects">useDeploy</span> | skillmeat/web/hooks/useDeploy.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['artifacts'], ['deployments'], ['projects', 'detail'] |
| <span title="Hook to execute merge">useExecuteMerge</span> | skillmeat/web/hooks/use-merge.ts | <span title="Analyze merge safety between snapshots">analyzeMergeSafety</span>, <span title="Execute merge between snapshots">executeMerge</span>, <span title="Preview merge changes between snapshots">previewMerge</span>, <span title="Resolve a merge conflict">resolveConflict</span> | ['collections', variables.localCollection], ['snapshots'] |
| <span title="Hook to export a bundle with progress tracking">useExportBundle</span> | skillmeat/web/hooks/useExportBundle.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['bundles'] |
| <span title="Hook to fetch a single artifact by ID">useArtifact</span> | skillmeat/web/hooks/useArtifacts.ts | <span title="Fetch paginated artifacts from collection">fetchArtifactsPaginated</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span>, type ArtifactsPaginatedResponse | ['artifacts', 'infinite', filters] |
| <span title="Hook to fetch a single listing detail">useListing</span> | skillmeat/web/hooks/useMarketplace.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export function useToast()">useToast</span> | - |
| <span title="Hook to fetch a single project by ID">useProject</span> | skillmeat/web/hooks/useProjects.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Hook to fetch all artifacts with infinite scroll pagination">useInfiniteArtifacts</span> | skillmeat/web/hooks/useArtifacts.ts | <span title="Fetch paginated artifacts from collection">fetchArtifactsPaginated</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span>, type ArtifactsPaginatedResponse | ['artifacts', 'infinite', filters] |
| <span title="Hook to fetch all bundles">useBundles</span> | skillmeat/web/hooks/useBundles.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| <span title="Hook to fetch all projects with deployments">useProjects</span> | skillmeat/web/hooks/useProjects.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Hook to fetch analytics summary">useAnalyticsSummary</span> | skillmeat/web/hooks/useAnalytics.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Hook to fetch and filter artifacts">useArtifacts</span> | skillmeat/web/hooks/useArtifacts.ts | <span title="Fetch paginated artifacts from collection">fetchArtifactsPaginated</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span>, type ArtifactsPaginatedResponse | ['artifacts', 'infinite', filters] |
| <span title="Hook to fetch available brokers">useBrokers</span> | skillmeat/web/hooks/useMarketplace.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export function useToast()">useToast</span> | - |
| <span title="Hook to fetch bundle analytics">useBundleAnalytics</span> | skillmeat/web/hooks/useBundles.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| <span title="Hook to fetch context sync status for a project">useContextSyncStatus</span> | skillmeat/web/hooks/use-context-sync.ts | <span title="Get sync status for a project">getSyncStatus</span>, <span title="Pull changes from project to collection">pullChanges</span>, <span title="Push collection changes to project">pushChanges</span>, <span title="Resolve sync conflict">resolveConflict</span>, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| <span title="Hook to fetch outdated artifacts from the cache">useOutdatedArtifacts</span> | skillmeat/web/hooks/useOutdatedArtifacts.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Hook to fetch paginated marketplace listings">useListings</span> | skillmeat/web/hooks/useMarketplace.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export function useToast()">useToast</span> | - |
| <span title="Hook to fetch projects with cache awareness">useProjectCache</span> | skillmeat/web/hooks/useProjectCache.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['projects', 'list', 'with-cache-info'] |
| <span title="Hook to fetch top artifacts">useTopArtifacts</span> | skillmeat/web/hooks/useAnalytics.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Hook to fetch usage trends">useUsageTrends</span> | skillmeat/web/hooks/useAnalytics.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Hook to fetch version graph for an artifact">useVersionGraph</span> | skillmeat/web/hooks/useVersionGraph.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Hook to get count of pending context changes for an entity">usePendingContextChanges</span> | skillmeat/web/hooks/use-context-sync.ts | <span title="Get sync status for a project">getSyncStatus</span>, <span title="Pull changes from project to collection">pullChanges</span>, <span title="Push collection changes to project">pushChanges</span>, <span title="Resolve sync conflict">resolveConflict</span>, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| <span title="Hook to import a bundle with progress tracking">useImportBundle</span> | skillmeat/web/hooks/useImportBundle.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['artifacts'], ['bundle-preview', source], ['bundles'] |
| <span title="Hook to install a marketplace listing">useInstallListing</span> | skillmeat/web/hooks/useMarketplace.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export function useToast()">useToast</span> | - |
| <span title="Hook to manage analytics SSE stream">useAnalyticsStream</span> | skillmeat/web/hooks/useAnalyticsStream.ts | <span title="export const apiConfig =">apiConfig</span> | ['analytics', 'summary'], ['analytics', 'top-artifacts'], ['analytics', 'trends'], ['analytics'] |
| <span title="Hook to monitor cache status and statistics">useCacheStatus</span> | skillmeat/web/hooks/useCacheStatus.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['cache', 'status'] |
| <span title="Hook to preview a bundle before importing">usePreviewBundle</span> | skillmeat/web/hooks/useImportBundle.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['artifacts'], ['bundle-preview', source], ['bundles'] |
| <span title="Hook to preview merge changes">usePreviewMerge</span> | skillmeat/web/hooks/use-merge.ts | <span title="Analyze merge safety between snapshots">analyzeMergeSafety</span>, <span title="Execute merge between snapshots">executeMerge</span>, <span title="Preview merge changes between snapshots">previewMerge</span>, <span title="Resolve a merge conflict">resolveConflict</span> | ['collections', variables.localCollection], ['snapshots'] |
| <span title="Hook to publish a bundle to marketplace">usePublishBundle</span> | skillmeat/web/hooks/useMarketplace.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export function useToast()">useToast</span> | - |
| <span title="Hook to pull changes from project to collection">usePullContextChanges</span> | skillmeat/web/hooks/use-context-sync.ts | <span title="Get sync status for a project">getSyncStatus</span>, <span title="Pull changes from project to collection">pullChanges</span>, <span title="Push collection changes to project">pushChanges</span>, <span title="Resolve sync conflict">resolveConflict</span>, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| <span title="Hook to push changes from collection to project">usePushContextChanges</span> | skillmeat/web/hooks/use-context-sync.ts | <span title="Get sync status for a project">getSyncStatus</span>, <span title="Pull changes from project to collection">pullChanges</span>, <span title="Push collection changes to project">pushChanges</span>, <span title="Resolve sync conflict">resolveConflict</span>, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| <span title="Hook to resolve a single conflict">useResolveConflict</span> | skillmeat/web/hooks/use-merge.ts | <span title="Analyze merge safety between snapshots">analyzeMergeSafety</span>, <span title="Execute merge between snapshots">executeMerge</span>, <span title="Preview merge changes between snapshots">previewMerge</span>, <span title="Resolve a merge conflict">resolveConflict</span> | ['collections', variables.localCollection], ['snapshots'] |
| <span title="Hook to resolve context sync conflict">useResolveContextConflict</span> | skillmeat/web/hooks/use-context-sync.ts | <span title="Get sync status for a project">getSyncStatus</span>, <span title="Pull changes from project to collection">pullChanges</span>, <span title="Push collection changes to project">pushChanges</span>, <span title="Resolve sync conflict">resolveConflict</span>, type SyncResolution, type SyncStatus | ['artifact-files'], ['context-entities'], ['context-sync-status', projectPath], ['context-sync-status', variables.projectPath] |
| <span title="Hook to revoke a share link">useRevokeShareLink</span> | skillmeat/web/hooks/useBundles.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| <span title="Hook to trigger cache refresh operations">useCacheRefresh</span> | skillmeat/web/hooks/useCacheRefresh.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['cache', projectId], ['cache'], ['projects', 'detail', projectId], ['projects'] |
| <span title="Hook to undeploy (remove) artifacts from projects">useUndeploy</span> | skillmeat/web/hooks/useDeploy.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | ['artifacts'], ['deployments'], ['projects', 'detail'] |
| <span title="Hook to update an artifact">useUpdateArtifact</span> | skillmeat/web/hooks/useArtifacts.ts | <span title="Fetch paginated artifacts from collection">fetchArtifactsPaginated</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span>, type ArtifactsPaginatedResponse | ['artifacts', 'infinite', filters] |
| <span title="Hook to update an existing project">useUpdateProject</span> | skillmeat/web/hooks/useProjects.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export class ApiError extends Error">ApiError</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Hook to update share link settings">useUpdateShareLink</span> | skillmeat/web/hooks/useBundles.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['bundle-analytics', bundleId], ['bundles', filter], ['bundles'] |
| <span title="Hook to validate export request before executing">useValidateExport</span> | skillmeat/web/hooks/useExportBundle.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['bundles'] |
| <span title="Hook to validate import request before executing">useValidateImport</span> | skillmeat/web/hooks/useImportBundle.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['artifacts'], ['bundle-preview', source], ['bundles'] |
| <span title="Import artifacts from catalog to collection">useImportArtifacts</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Infer repository structure from GitHub URL">useInferUrl</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="List all deployments for a project">useDeploymentList</span> | skillmeat/web/hooks/use-deployments.ts | <span title="Deploy an artifact to a project">deployArtifact</span>, <span title="Get deployment summary statistics">getDeploymentSummary</span>, <span title="Get deployments with optional filtering">getDeployments</span>, <span title="List all deployed artifacts in a project">listDeployments</span>, <span title="Undeploy (remove) an artifact from a project">undeployArtifact</span>, type DeploymentQueryParams, type DeploymentSummary | - |
| <span title="Mark a catalog entry as excluded">useExcludeCatalogEntry</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Move artifact between groups">useMoveArtifactToGroup</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Refresh deployment data for a project">useRefreshDeployments</span> | skillmeat/web/hooks/use-deployments.ts | <span title="Deploy an artifact to a project">deployArtifact</span>, <span title="Get deployment summary statistics">getDeploymentSummary</span>, <span title="Get deployments with optional filtering">getDeployments</span>, <span title="List all deployed artifacts in a project">listDeployments</span>, <span title="Undeploy (remove) an artifact from a project">undeployArtifact</span>, type DeploymentQueryParams, type DeploymentSummary | - |
| <span title="Remove artifact from collection mutation">useRemoveArtifactFromCollection</span> | skillmeat/web/hooks/use-collections.ts | <span title="Add artifact to collection">addArtifactToCollection</span>, <span title="Create new collection">createCollection</span>, <span title="Delete collection">deleteCollection</span>, <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span>, <span title="Remove artifact from collection">removeArtifactFromCollection</span>, <span title="Update existing collection">updateCollection</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, type CollectionArtifactsPaginatedResponse | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| <span title="Remove artifact from group mutation">useRemoveArtifactFromGroup</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Remove tag from artifact mutation">useRemoveTagFromArtifact</span> | skillmeat/web/hooks/use-tags.ts | <span title="Add tag to artifact">addTagToArtifact</span>, <span title="Create new tag">createTag</span>, <span title="Delete tag">deleteTag</span>, <span title="Fetch all tags with pagination">fetchTags</span>, <span title="Get all tags for an artifact">getArtifactTags</span>, <span title="Remove tag from artifact">removeTagFromArtifact</span>, <span title="Search tags by query string">searchTags</span>, <span title="Update existing tag">updateTag</span>, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest | - |
| <span title="Reorder artifacts within a group">useReorderArtifactsInGroup</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Reorder groups within a collection (bulk position update)">useReorderGroups</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Restore an excluded catalog entry">useRestoreCatalogEntry</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Search tags by query string">useSearchTags</span> | skillmeat/web/hooks/use-tags.ts | <span title="Add tag to artifact">addTagToArtifact</span>, <span title="Create new tag">createTag</span>, <span title="Delete tag">deleteTag</span>, <span title="Fetch all tags with pagination">fetchTags</span>, <span title="Get all tags for an artifact">getArtifactTags</span>, <span title="Remove tag from artifact">removeTagFromArtifact</span>, <span title="Search tags by query string">searchTags</span>, <span title="Update existing tag">updateTag</span>, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest | - |
| <span title="Trigger source rescan">useRescanSource</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Undeploy (remove) an artifact from a project mutation">useUndeployArtifact</span> | skillmeat/web/hooks/use-deployments.ts | <span title="Deploy an artifact to a project">deployArtifact</span>, <span title="Get deployment summary statistics">getDeploymentSummary</span>, <span title="Get deployments with optional filtering">getDeployments</span>, <span title="List all deployed artifacts in a project">listDeployments</span>, <span title="Undeploy (remove) an artifact from a project">undeployArtifact</span>, type DeploymentQueryParams, type DeploymentSummary | - |
| <span title="Undeploy an MCP server from Claude Desktop">useUndeployMcpServer</span> | skillmeat/web/hooks/useMcpServers.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Update GitHub source">useUpdateSource</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Update an existing MCP server">useUpdateMcpServer</span> | skillmeat/web/hooks/useMcpServers.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span> | - |
| <span title="Update catalog entry name">useUpdateCatalogEntryName</span> | skillmeat/web/hooks/useMarketplaceSources.ts | <span title="Infer repository structure from GitHub URL">inferUrl</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export function useToast()">useToast</span> | ['artifacts'], [...sourceKeys.catalogs(), sourceId] |
| <span title="Update existing collection mutation">useUpdateCollection</span> | skillmeat/web/hooks/use-collections.ts | <span title="Add artifact to collection">addArtifactToCollection</span>, <span title="Create new collection">createCollection</span>, <span title="Delete collection">deleteCollection</span>, <span title="Fetch paginated artifacts in a collection">fetchCollectionArtifactsPaginated</span>, <span title="Remove artifact from collection">removeArtifactFromCollection</span>, <span title="Update existing collection">updateCollection</span>, <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, type CollectionArtifactsPaginatedResponse | ['artifacts'], [...collectionKeys.artifacts(id!), options] |
| <span title="Update existing context entity mutation">useUpdateContextEntity</span> | skillmeat/web/hooks/use-context-entities.ts | <span title="Create new context entity">createContextEntity</span>, <span title="Delete context entity">deleteContextEntity</span>, <span title="Fetch context entities with optional filtering">fetchContextEntities</span>, <span title="Fetch raw markdown content for a context entity">fetchContextEntityContent</span>, <span title="Fetch single context entity by ID">fetchContextEntity</span>, <span title="Update existing context entity">updateContextEntity</span> | - |
| <span title="Update existing group mutation">useUpdateGroup</span> | skillmeat/web/hooks/use-groups.ts | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | - |
| <span title="Update existing tag mutation">useUpdateTag</span> | skillmeat/web/hooks/use-tags.ts | <span title="Add tag to artifact">addTagToArtifact</span>, <span title="Create new tag">createTag</span>, <span title="Delete tag">deleteTag</span>, <span title="Fetch all tags with pagination">fetchTags</span>, <span title="Get all tags for an artifact">getArtifactTags</span>, <span title="Remove tag from artifact">removeTagFromArtifact</span>, <span title="Search tags by query string">searchTags</span>, <span title="Update existing tag">updateTag</span>, type Tag, type TagCreateRequest, type TagListResponse, type TagUpdateRequest | - |
| <span title="Update existing template">useUpdateTemplate</span> | skillmeat/web/hooks/use-templates.ts | <span title="Create new template">createTemplate</span>, <span title="Delete template">deleteTemplate</span>, <span title="Deploy template to a project">deployTemplate</span>, <span title="Fetch all templates with optional filtering and pagination">fetchTemplates</span>, <span title="Fetch template by ID with full entity details">fetchTemplateById</span>, <span title="Update existing template">updateTemplate</span> | ['deployments'] |
| <span title="Update the status of a path tag segment (approve or reject)">useUpdatePathTagStatus</span> | skillmeat/web/hooks/use-path-tags.ts | <span title="Get extracted path tag segments for a marketplace catalog entry">getPathTags</span>, <span title="Update status of a specific path tag segment (approve or reject)">updatePathTagStatus</span> | - |
| <span title="export function useCheckUpstream()">useCheckUpstream</span> | skillmeat/web/hooks/useSync.ts | - | ['artifact', variables.artifactId], ['artifacts'] |
| <span title="export function useFocusTrap(isActive: boolean)">useFocusTrap</span> | skillmeat/web/hooks/useFocusTrap.ts | - | - |
| <span title="export function useIntersectionObserver<T extends HTMLElement = HTMLDivElement>(">useIntersectionObserver</span> | skillmeat/web/hooks/use-intersection-observer.ts | - | - |
| <span title="export function useSSE<T = any>(url: string | null, options: UseSSEOptions = {})">useSSE</span> | skillmeat/web/hooks/useSSE.ts | - | - |
| <span title="export function useSync(options: UseSyncOptions = {})">useSync</span> | skillmeat/web/hooks/useSync.ts | - | ['artifact', variables.artifactId], ['artifacts'] |
| <span title="export function useToast()">useToast</span> | skillmeat/web/hooks/use-toast.tsx | - | - |
| <span title="useEntityLifecycle - Hook to access entity management context">useEntityLifecycle</span> | skillmeat/web/hooks/useEntityLifecycle.tsx | <span title="export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T>">apiRequest</span>, <span title="export const apiConfig =">apiConfig</span> | ['entities'], ['projects'] |
| useArtifacts | - | - | - |
| useBrokers | - | - | - |
| useCollectionContext | - | - | - |
| useContextEntities | - | - | - |
| useCreateContextEntity | - | - | - |
| useCreateMcpServer | - | - | - |
| useDeleteContextEntity | - | - | - |
| useDeleteMcpServer | - | - | - |
| useDeployMcpServer | - | - | - |
| useDeploymentList | - | - | - |
| useDeploymentSummary | - | - | - |
| useEditArtifactParameters | - | - | - |
| useExcludeCatalogEntry | - | - | - |
| useImportArtifacts | - | - | - |
| useInfiniteArtifacts | - | - | - |
| useInfiniteCollectionArtifacts | - | - | - |
| useInstallListing | - | - | - |
| useIntersectionObserver | - | - | - |
| useListing | - | - | - |
| useListings | - | - | - |
| useMcpDeploymentStatus | - | - | - |
| useMcpServer | - | - | - |
| useMcpServers | - | - | - |
| useOutdatedArtifacts | - | - | - |
| useProject | - | - | - |
| useProjectCache | - | - | - |
| useProjectDiscovery | - | - | - |
| usePublishBundle | - | - | - |
| useRefreshDeployments | - | - | - |
| useRescanSource | - | - | - |
| useSource | - | - | - |
| useSourceCatalog | - | - | - |
| useSources | - | - | - |
| useTemplates | - | - | - |
| useToast | - | - | - |
| useUndeployMcpServer | - | - | - |
| useUpdateMcpServer | - | - | - |
| useUpdateProject | - | - | - |
| useUpdateSource | - | - | - |
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
