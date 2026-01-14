<!-- Path Scope: skillmeat/api/schemas/**/*.py -->

# API Schemas - Inventory

<!-- CODEBASE_GRAPH:SCHEMAS:START -->
| Schema | File | Handlers |
| --- | --- | --- |
| <span title="A single duplicate match decision from the user.">DuplicateMatch</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="A single entry in a file tree (file or directory).">FileTreeEntry</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Action to take for a duplicate match.">DuplicateDecisionAction</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="All path segments for a catalog entry.">PathSegmentsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Get extracted path segments for a catalog entry.">get_path_tags</span> |
| <span title="All path segments for a catalog entry.">PathSegmentsResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="An artifact detected during scanning.">DetectedArtifact</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="An artifact discovered during scanning.">DiscoveredArtifact</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Artifact information in preview.">PreviewArtifact</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Artifact metadata from SKILL.md / COMMAND.md / AGENT.md.">ArtifactMetadataResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Base MCP server schema with common fields.">MCPServerBase</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Base schema for project template data.">ProjectTemplateBase</span> | skillmeat/api/schemas/project_template.py | - |
| <span title="Base schema for shared tag fields.">TagBase</span> | skillmeat/api/schemas/tags.py | - |
| <span title="Bundle analytics response.">BundleAnalyticsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Get analytics data for a specific bundle.">get_bundle_analytics</span> |
| <span title="Bundle analytics response.">BundleAnalyticsResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Bundle metadata response.">BundleMetadataResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Cache metadata for cached responses.">CacheInfo</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Cache statistics and status information.">CacheStatusResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="Get cache statistics and status.">get_cache_status</span> |
| <span title="Cache statistics and status information.">CacheStatusResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Cached artifact information.">CachedArtifactResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Cached project information.">CachedProjectResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Categorization of artifacts in bundle.">BundlePreviewCategorization</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Collection membership status for a discovered artifact.">CollectionStatus</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Complete version graph for an artifact.">VersionGraphResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Get complete version graph for an artifact.">get_version_graph</span> |
| <span title="Complete version graph for an artifact.">VersionGraphResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Conflict information for a single file.">ConflictMetadataResponse</span> | skillmeat/api/schemas/version.py | - |
| <span title="Cursor-based pagination information.">PageInfo</span> | skillmeat/api/schemas/common.py | - |
| <span title="Deployment information for a single project.">ProjectDeploymentInfo</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Deployment statistics for an artifact.">DeploymentStatistics</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Detail about a specific error.">ErrorDetail</span> | skillmeat/api/schemas/errors.py | - |
| <span title="Detailed breakdown of scoring components.">ScoreBreakdown</span> | skillmeat/api/schemas/match.py | - |
| <span title="Detailed bundle information response.">BundleDetailResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Get detailed information about a specific bundle.">get_bundle</span> |
| <span title="Detailed bundle information response.">BundleDetailResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Detailed information about a project including all deployments.">ProjectDetail</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py | <span title="Get details for a specific project.">get_project</span>, <span title="Update project metadata.">update_project</span> |
| <span title="Detailed information about a project including all deployments.">ProjectDetail</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Detailed response model for a single marketplace listing.">ListingDetailResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Get detailed information for a specific listing.">get_listing_detail</span> |
| <span title="Detailed response model for a single marketplace listing.">ListingDetailResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Diff information for a single file.">FileDiff</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Diff result between two snapshots.">VersionDiffResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/version.py | <span title="Compare two snapshots and generate a diff.">diff_snapshots</span> |
| <span title="Diff result between two snapshots.">VersionDiffResponse</span> | skillmeat/api/schemas/version.py | - |
| <span title="Embedded collection info for artifact responses.">ArtifactCollectionInfo</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Entity information within a project template.">TemplateEntitySchema</span> | skillmeat/api/schemas/project_template.py | - |
| <span title="File or directory node in artifact file tree.">FileNode</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Generic paginated response wrapper.">PaginatedResponse</span> | skillmeat/api/schemas/common.py | - |
| <span title="Hash-based collection matching result for a discovered artifact.">CollectionMatch</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Information about a discovered context entity in a project.">ContextEntityInfo</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Information about a modified artifact in a project.">ModifiedArtifactInfo</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Information about a single deployment.">DeploymentInfo</span> | skillmeat/api/schemas/deployments.py | - |
| <span title="Information about a stale artifact.">StaleArtifactResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Information about a sync conflict.">ConflictInfo</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Information about an available marketplace broker.">BrokerInfo</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Lightweight artifact summary for collection listings.">ArtifactSummary</span> | skillmeat/api/schemas/user_collections.py | - |
| <span title="List of stale artifacts.">StaleArtifactsListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="List outdated artifacts with sorting and filtering.">list_stale_artifacts</span> |
| <span title="List of stale artifacts.">StaleArtifactsListResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Marketplace entry information.">MarketplaceEntryResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Metadata fetched from GitHub.">GitHubMetadata</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Metadata for bundle export.">BundleExportMetadata</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Modification status for a single deployment.">DeploymentModificationStatus</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Node in version graph visualization.">VersionGraphNodeResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Options for bundle export.">BundleExportOptions</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Overall analytics summary.">AnalyticsSummaryResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/analytics.py | <span title="Get overall analytics summary.">get_analytics_summary</span> |
| <span title="Overall analytics summary.">AnalyticsSummaryResponse</span> | skillmeat/api/schemas/analytics.py | - |
| <span title="Paginated list of GitHub repository sources.">SourceListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="List all marketplace sources with pagination.">list_sources</span> |
| <span title="Paginated list of GitHub repository sources.">SourceListResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Paginated list of cached artifacts.">CachedArtifactsListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="List cached artifacts.">list_cached_artifacts</span> |
| <span title="Paginated list of cached artifacts.">CachedArtifactsListResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Paginated list of cached projects.">CachedProjectsListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="List cached projects.">list_cached_projects</span> |
| <span title="Paginated list of cached projects.">CachedProjectsListResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Paginated list of catalog entries with statistics.">CatalogListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="List artifacts from a source with optional filters and sorting.">list_artifacts</span> |
| <span title="Paginated list of catalog entries with statistics.">CatalogListResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Paginated list of marketplace entries.">MarketplaceListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="Get cached marketplace entries.">get_marketplace_cache</span> |
| <span title="Paginated list of marketplace entries.">MarketplaceListResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Paginated response for artifact listings.">ArtifactListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="List all artifacts with filters and pagination.">list_artifacts</span> |
| <span title="Paginated response for artifact listings.">ArtifactListResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Paginated response for artifacts within a collection.">CollectionArtifactsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/collections.py | <span title="List all artifacts in a collection with pagination.">list_collection_artifacts</span> |
| <span title="Paginated response for artifacts within a collection.">CollectionArtifactsResponse</span> | skillmeat/api/schemas/collections.py | - |
| <span title="Paginated response for collection artifacts.">CollectionArtifactsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/user_collections.py | <span title="List artifacts in a collection with pagination.">list_collection_artifacts</span>, <span title="List context entities in a collection with pagination.">list_collection_entities</span> |
| <span title="Paginated response for collection artifacts.">CollectionArtifactsResponse</span> | skillmeat/api/schemas/user_collections.py | - |
| <span title="Paginated response for collection listings.">CollectionListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/collections.py | <span title="List all collections with cursor-based pagination.">list_collections</span> |
| <span title="Paginated response for collection listings.">CollectionListResponse</span> | skillmeat/api/schemas/collections.py | - |
| <span title="Paginated response for context entity listings.">ContextEntityListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_entity.py | <span title="List all context entities with filtering and pagination.">list_context_entities</span> |
| <span title="Paginated response for context entity listings.">ContextEntityListResponse</span> | skillmeat/api/schemas/context_entity.py | - |
| <span title="Paginated response for marketplace listings.">ListingsPageResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Browse marketplace listings with filtering and pagination.">list_listings</span> |
| <span title="Paginated response for marketplace listings.">ListingsPageResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Paginated response for project listings.">ProjectListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py | <span title="List all projects with deployed artifacts.">list_projects</span> |
| <span title="Paginated response for project listings.">ProjectListResponse</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Paginated response for project template listings.">ProjectTemplateListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/project_template.py | <span title="List all project templates with pagination.">list_templates</span> |
| <span title="Paginated response for project template listings.">ProjectTemplateListResponse</span> | skillmeat/api/schemas/project_template.py | - |
| <span title="Paginated response for snapshot listings.">SnapshotListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/version.py | <span title="List all snapshots with cursor-based pagination.">list_snapshots</span> |
| <span title="Paginated response for snapshot listings.">SnapshotListResponse</span> | skillmeat/api/schemas/version.py | - |
| <span title="Paginated response for tag listings.">TagListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/tags.py | <span title="List all tags with cursor-based pagination.">list_tags</span> |
| <span title="Paginated response for tag listings.">TagListResponse</span> | skillmeat/api/schemas/tags.py | - |
| <span title="Paginated response for top artifacts by usage.">TopArtifactsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/analytics.py | <span title="Get top artifacts by usage.">get_top_artifacts</span> |
| <span title="Paginated response for top artifacts by usage.">TopArtifactsResponse</span> | skillmeat/api/schemas/analytics.py | - |
| <span title="Paginated response for user collection listings.">UserCollectionListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/user_collections.py | <span title="List all user collections with cursor-based pagination.">list_user_collections</span> |
| <span title="Paginated response for user collection listings.">UserCollectionListResponse</span> | skillmeat/api/schemas/user_collections.py | - |
| <span title="Paginated search results.">SearchResultsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="Search cached artifacts.">search_cache</span> |
| <span title="Paginated search results.">SearchResultsResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Parsed GitHub source specification.">GitHubSourceSpec</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Popular artifact statistics.">ArtifactPopularity</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Pre-flight rollback safety analysis.">RollbackSafetyAnalysisResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/version.py | <span title="Analyze whether rollback is safe before attempting.">analyze_rollback_safety</span> |
| <span title="Pre-flight rollback safety analysis.">RollbackSafetyAnalysisResponse</span> | skillmeat/api/schemas/version.py | - |
| <span title="Reason codes for import failures and skips.">ErrorReasonCode</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Request body for excluding or restoring a catalog entry.">ExcludeArtifactRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Mark or restore a catalog entry as excluded.">exclude_artifact</span> |
| <span title="Request body for excluding or restoring a catalog entry.">ExcludeArtifactRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request body for updating file content.">FileUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Create a new file within an artifact.">create_artifact_file</span>, <span title="Update a file's content within an artifact.">update_artifact_file_content</span> |
| <span title="Request body for updating file content.">FileUpdateRequest</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Request body for updating the display name of a catalog entry.">UpdateCatalogEntryNameRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Update the name for a catalog entry.">update_catalog_entry_name</span> |
| <span title="Request body for updating the display name of a catalog entry.">UpdateCatalogEntryNameRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request model for installing a marketplace listing.">InstallRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Install a marketplace listing.">install_listing</span> |
| <span title="Request model for installing a marketplace listing.">InstallRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request model for publishing a bundle to marketplace.">PublishRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Publish a bundle to the marketplace.">publish_bundle</span> |
| <span title="Request model for publishing a bundle to marketplace.">PublishRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request schema for adding a tag to an artifact.">ArtifactTagRequest</span> | skillmeat/api/schemas/tags.py | - |
| <span title="Request schema for adding artifacts to a collection.">AddArtifactsRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/user_collections.py | <span title="Add artifacts to a collection.">add_artifacts_to_collection</span> |
| <span title="Request schema for adding artifacts to a collection.">AddArtifactsRequest</span> | skillmeat/api/schemas/user_collections.py | - |
| <span title="Request schema for adding artifacts to a group.">AddGroupArtifactsRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Add artifacts to a group.">add_artifacts_to_group</span> |
| <span title="Request schema for adding artifacts to a group.">AddGroupArtifactsRequest</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Request schema for analyzing merge safety.">MergeAnalyzeRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/merge.py | <span title="Analyze merge safety (dry run).">analyze_merge</span> |
| <span title="Request schema for analyzing merge safety.">MergeAnalyzeRequest</span> | skillmeat/api/schemas/merge.py | - |
| <span title="Request schema for bulk reordering artifacts within a group.">ReorderArtifactsRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Bulk reorder artifacts in a group.">reorder_artifacts_in_group</span> |
| <span title="Request schema for bulk reordering artifacts within a group.">ReorderArtifactsRequest</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Request schema for bulk reordering groups within a collection.">GroupReorderRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Bulk reorder groups by updating their positions.">reorder_groups</span> |
| <span title="Request schema for bulk reordering groups within a collection.">GroupReorderRequest</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Request schema for creating a context entity.">ContextEntityCreateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_entity.py | <span title="Create a new context entity.">create_context_entity</span> |
| <span title="Request schema for creating a context entity.">ContextEntityCreateRequest</span> | skillmeat/api/schemas/context_entity.py | - |
| <span title="Request schema for creating a new MCP server.">MCPServerCreateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/mcp.py | <span title="Create a new MCP server in the collection.">create_mcp_server</span> |
| <span title="Request schema for creating a new MCP server.">MCPServerCreateRequest</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Request schema for creating a new collection.">CollectionCreateRequest</span> | skillmeat/api/schemas/collections.py | - |
| <span title="Request schema for creating a new group in a collection.">GroupCreateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Create a new group in a collection.">create_group</span> |
| <span title="Request schema for creating a new group in a collection.">GroupCreateRequest</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Request schema for creating a new project template.">ProjectTemplateCreateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/project_template.py | <span title="Create new project template from entity list.">create_template</span> |
| <span title="Request schema for creating a new project template.">ProjectTemplateCreateRequest</span> | skillmeat/api/schemas/project_template.py | - |
| <span title="Request schema for creating a new user collection.">UserCollectionCreateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/user_collections.py | <span title="Create a new user collection.">create_user_collection</span> |
| <span title="Request schema for creating a new user collection.">UserCollectionCreateRequest</span> | skillmeat/api/schemas/user_collections.py | - |
| <span title="Request schema for creating a project.">ProjectCreateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py | <span title="Create a new project.">create_project</span> |
| <span title="Request schema for creating a project.">ProjectCreateRequest</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Request schema for creating a tag.">TagCreateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/tags.py | <span title="Create a new tag.">create_tag</span> |
| <span title="Request schema for creating a tag.">TagCreateRequest</span> | skillmeat/api/schemas/tags.py | - |
| <span title="Request schema for creating an artifact.">ArtifactCreateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Create a new artifact from GitHub or local source.">create_artifact</span> |
| <span title="Request schema for creating an artifact.">ArtifactCreateRequest</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Request schema for deploying a project template.">DeployTemplateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/project_template.py | <span title="Deploy project template to target project path with performance optimizations.">deploy_template_endpoint</span> |
| <span title="Request schema for deploying a project template.">DeployTemplateRequest</span> | skillmeat/api/schemas/project_template.py | - |
| <span title="Request schema for deploying an MCP server.">DeploymentRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/mcp.py | <span title="Deploy MCP server to Claude Desktop.">deploy_mcp_server</span> |
| <span title="Request schema for deploying an MCP server.">DeploymentRequest</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Request schema for deploying an artifact.">ArtifactDeployRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Deploy artifact from collection to project.">deploy_artifact</span> |
| <span title="Request schema for deploying an artifact.">ArtifactDeployRequest</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Request schema for executing a merge.">MergeExecuteRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/merge.py | <span title="Execute merge with conflict detection.">execute_merge</span> |
| <span title="Request schema for executing a merge.">MergeExecuteRequest</span> | skillmeat/api/schemas/merge.py | - |
| <span title="Request schema for previewing merge changes.">MergePreviewRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/merge.py | <span title="Preview merge changes without executing.">preview_merge</span> |
| <span title="Request schema for previewing merge changes.">MergePreviewRequest</span> | skillmeat/api/schemas/merge.py | - |
| <span title="Request schema for pulling changes from project to collection.">SyncPullRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_sync.py | <span title="Pull changes from project to collection.">pull_changes</span> |
| <span title="Request schema for pulling changes from project to collection.">SyncPullRequest</span> | skillmeat/api/schemas/context_sync.py | - |
| <span title="Request schema for pushing collection changes to project.">SyncPushRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_sync.py | <span title="Push collection changes to project.">push_changes</span> |
| <span title="Request schema for pushing collection changes to project.">SyncPushRequest</span> | skillmeat/api/schemas/context_sync.py | - |
| <span title="Request schema for resolving a single conflict.">ConflictResolveRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/merge.py | <span title="Resolve a single merge conflict.">resolve_conflict</span> |
| <span title="Request schema for resolving a single conflict.">ConflictResolveRequest</span> | skillmeat/api/schemas/merge.py | - |
| <span title="Request schema for resolving sync conflicts.">SyncResolveRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_sync.py | <span title="Resolve sync conflict.">resolve_conflict</span> |
| <span title="Request schema for resolving sync conflicts.">SyncResolveRequest</span> | skillmeat/api/schemas/context_sync.py | - |
| <span title="Request schema for submitting artifact rating.">UserRatingRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/scoring.py | <span title="Submit a rating for an artifact.">submit_rating</span> |
| <span title="Request schema for submitting artifact rating.">UserRatingRequest</span> | skillmeat/api/schemas/scoring.py | - |
| <span title="Request schema for syncing an artifact.">ArtifactSyncRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Sync artifact from project to collection.">sync_artifact</span> |
| <span title="Request schema for syncing an artifact.">ArtifactSyncRequest</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Request schema for updating a context entity.">ContextEntityUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_entity.py | <span title="Update a context entity's metadata and/or content.">update_context_entity</span> |
| <span title="Request schema for updating a context entity.">ContextEntityUpdateRequest</span> | skillmeat/api/schemas/context_entity.py | - |
| <span title="Request schema for updating a group.">GroupUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Update a group's metadata.">update_group</span> |
| <span title="Request schema for updating a group.">GroupUpdateRequest</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Request schema for updating a project template.">ProjectTemplateUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/project_template.py | <span title="Update existing project template.">update_template</span> |
| <span title="Request schema for updating a project template.">ProjectTemplateUpdateRequest</span> | skillmeat/api/schemas/project_template.py | - |
| <span title="Request schema for updating a project.">ProjectUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py | <span title="Update project metadata.">update_project</span> |
| <span title="Request schema for updating a project.">ProjectUpdateRequest</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Request schema for updating a tag.">TagUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/tags.py | <span title="Update tag metadata.">update_tag</span> |
| <span title="Request schema for updating a tag.">TagUpdateRequest</span> | skillmeat/api/schemas/tags.py | - |
| <span title="Request schema for updating an MCP server.">MCPServerUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/mcp.py | <span title="Update an existing MCP server.">update_mcp_server</span> |
| <span title="Request schema for updating an MCP server.">MCPServerUpdateRequest</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Request schema for updating an artifact.">ArtifactUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Update an artifact's metadata, tags, and aliases.">update_artifact</span> |
| <span title="Request schema for updating an artifact.">ArtifactUpdateRequest</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Request schema for updating artifact metadata fields.">ArtifactUpdateMetadataRequest</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Request schema for updating collection metadata.">CollectionUpdateRequest</span> | skillmeat/api/schemas/collections.py | - |
| <span title="Request schema for updating user collection metadata.">UserCollectionUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/user_collections.py | <span title="Update a user collection.">update_user_collection</span> |
| <span title="Request schema for updating user collection metadata.">UserCollectionUpdateRequest</span> | skillmeat/api/schemas/user_collections.py | - |
| <span title="Request to add a GitHub repository source.">CreateSourceRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Create a new GitHub repository source.">create_source</span> |
| <span title="Request to add a GitHub repository source.">CreateSourceRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request to add a skip preference.">SkipPreferenceAddRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Add a skip preference for an artifact in a project.">add_skip_preference</span> |
| <span title="Request to add a skip preference.">SkipPreferenceAddRequest</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Request to compare two snapshots.">VersionDiffRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/version.py | <span title="Compare two snapshots and generate a diff.">diff_snapshots</span> |
| <span title="Request to compare two snapshots.">VersionDiffRequest</span> | skillmeat/api/schemas/version.py | - |
| <span title="Request to create a new snapshot.">SnapshotCreateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/version.py | <span title="Create a new snapshot of a collection.">create_snapshot</span> |
| <span title="Request to create a new snapshot.">SnapshotCreateRequest</span> | skillmeat/api/schemas/version.py | - |
| <span title="Request to create or update a bundle share link.">ShareLinkUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Create or update a shareable link for a bundle.">update_bundle_share_link</span> |
| <span title="Request to create or update a bundle share link.">ShareLinkUpdateRequest</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Request to deploy an artifact to a project.">DeployRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/deployments.py | <span title="Deploy an artifact to a project.">deploy_artifact</span> |
| <span title="Request to deploy an artifact to a project.">DeployRequest</span> | skillmeat/api/schemas/deployments.py | - |
| <span title="Request to export artifacts as a bundle.">BundleExportRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Export artifacts as a bundle.">export_bundle</span> |
| <span title="Request to export artifacts as a bundle.">BundleExportRequest</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Request to fetch GitHub metadata.">MetadataFetchRequest</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Request to import a bundle.">BundleImportRequest</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Request to import artifacts from catalog to collection.">ImportRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Import catalog entries to local collection.">import_artifacts</span> |
| <span title="Request to import artifacts from catalog to collection.">ImportRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request to import multiple artifacts.">BulkImportRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Bulk import multiple artifacts with graceful error handling.">bulk_import_artifacts</span> |
| <span title="Request to import multiple artifacts.">BulkImportRequest</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Request to infer GitHub source structure from a full URL.">InferUrlRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Infer GitHub repository structure from a full URL.">infer_github_url</span> |
| <span title="Request to infer GitHub source structure from a full URL.">InferUrlRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request to invalidate cache.">CacheInvalidateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="Invalidate cache.">invalidate_cache</span> |
| <span title="Request to invalidate cache.">CacheInvalidateRequest</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Request to process duplicate review decisions.">ConfirmDuplicatesRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Process duplicate review decisions from the frontend modal.">confirm_duplicates</span> |
| <span title="Request to process duplicate review decisions.">ConfirmDuplicatesRequest</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Request to remove a deployed artifact from a specific project.">ProjectDeploymentRemovalRequest</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Request to rollback to a previous snapshot.">RollbackRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/version.py | <span title="Rollback to a specific snapshot.">rollback</span> |
| <span title="Request to rollback to a previous snapshot.">RollbackRequest</span> | skillmeat/api/schemas/version.py | - |
| <span title="Request to scan for artifacts.">DiscoveryRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Scan collection for existing artifacts.">discover_artifacts</span> |
| <span title="Request to scan for artifacts.">DiscoveryRequest</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Request to set manual directory mappings for a source.">ManualMapRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request to trigger a rescan of a source.">ScanRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Trigger a rescan of a marketplace source.">rescan_source</span> |
| <span title="Request to trigger a rescan of a source.">ScanRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request to trigger cache refresh.">CacheRefreshRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="Trigger manual cache refresh.">refresh_cache</span> |
| <span title="Request to trigger cache refresh.">CacheRefreshRequest</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Request to undeploy (remove) an artifact from a project.">UndeployRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/deployments.py | <span title="Remove a deployed artifact from a project.">undeploy_artifact</span> |
| <span title="Request to undeploy (remove) an artifact from a project.">UndeployRequest</span> | skillmeat/api/schemas/deployments.py | - |
| <span title="Request to update a GitHub repository source.">UpdateSourceRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Update a marketplace source.">update_source</span> |
| <span title="Request to update a GitHub repository source.">UpdateSourceRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request to update a segment's approval status.">UpdateSegmentStatusRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Update approval status of a single path segment.">update_path_tag_status</span> |
| <span title="Request to update a segment's approval status.">UpdateSegmentStatusRequest</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Request to update artifact parameters.">ParameterUpdateRequest</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Update artifact parameters after import.">update_artifact_parameters</span> |
| <span title="Request to update artifact parameters.">ParameterUpdateRequest</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Response after creating a snapshot.">SnapshotCreateResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/version.py | <span title="Create a new snapshot of a collection.">create_snapshot</span> |
| <span title="Response after creating a snapshot.">SnapshotCreateResponse</span> | skillmeat/api/schemas/version.py | - |
| <span title="Response after updating segment status.">UpdateSegmentStatusResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Update approval status of a single path segment.">update_path_tag_status</span> |
| <span title="Response after updating segment status.">UpdateSegmentStatusResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response containing a skip preference.">SkipPreferenceResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Add a skip preference for an artifact in a project.">add_skip_preference</span> |
| <span title="Response containing a skip preference.">SkipPreferenceResponse</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Response containing file tree entries for an artifact.">FileTreeResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Get file tree for a marketplace artifact.">get_artifact_file_tree</span> |
| <span title="Response containing file tree entries for an artifact.">FileTreeResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response containing inferred GitHub source structure.">InferUrlResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Infer GitHub repository structure from a full URL.">infer_github_url</span> |
| <span title="Response containing inferred GitHub source structure.">InferUrlResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response containing list of skip preferences.">SkipPreferenceListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="List all skip preferences for a project.">list_skip_preferences</span> |
| <span title="Response containing list of skip preferences.">SkipPreferenceListResponse</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Response for artifact creation.">ArtifactCreateResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Create a new artifact from GitHub or local source.">create_artifact</span> |
| <span title="Response for artifact creation.">ArtifactCreateResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response for artifact diff.">ArtifactDiffResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Get diff between collection version and deployed project version.">get_artifact_diff</span> |
| <span title="Response for artifact diff.">ArtifactDiffResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response for artifact file content.">FileContentResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Create a new file within an artifact.">create_artifact_file</span>, <span title="Get content of a specific file within an artifact.">get_artifact_file_content</span>, <span title="Update a file's content within an artifact.">update_artifact_file_content</span> |
| <span title="Response for artifact file content.">FileContentResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response for artifact file listing.">FileListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="List all files in an artifact.">list_artifact_files</span> |
| <span title="Response for artifact file listing.">FileListResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response for listing bundles.">BundleListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="List all bundles with optional filtering.">list_bundles</span> |
| <span title="Response for listing bundles.">BundleListResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Response for modified artifacts in a project.">ModifiedArtifactsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py | <span title="Get list of all modified artifacts in a project.">get_modified_artifacts</span> |
| <span title="Response for modified artifacts in a project.">ModifiedArtifactsResponse</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Response for project context map discovery.">ContextMapResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py | <span title="Discover context entities in a project's .claude/ directory.">get_project_context_map</span> |
| <span title="Response for project context map discovery.">ContextMapResponse</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Response for project creation.">ProjectCreateResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py | <span title="Create a new project.">create_project</span> |
| <span title="Response for project creation.">ProjectCreateResponse</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Response for project deletion.">ProjectDeleteResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py | <span title="Delete a project.">delete_project</span> |
| <span title="Response for project deletion.">ProjectDeleteResponse</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Response for removing a deployed artifact from a project.">ProjectDeploymentRemovalResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/projects.py | <span title="Remove a deployed artifact from a specific project.">remove_project_deployment</span> |
| <span title="Response for removing a deployed artifact from a project.">ProjectDeploymentRemovalResponse</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Response for share link creation/update.">ShareLinkResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Create or update a shareable link for a bundle.">update_bundle_share_link</span> |
| <span title="Response for share link creation/update.">ShareLinkResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Response for share link deletion/revocation.">ShareLinkDeleteResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Revoke and delete the shareable link for a bundle.">delete_bundle_share_link</span> |
| <span title="Response for share link deletion/revocation.">ShareLinkDeleteResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Response for upstream diff comparing collection with GitHub source.">ArtifactUpstreamDiffResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Get diff between collection version and GitHub upstream source.">get_artifact_upstream_diff</span> |
| <span title="Response for upstream diff comparing collection with GitHub source.">ArtifactUpstreamDiffResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response for upstream status check.">ArtifactUpstreamResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Check upstream status and available updates for an artifact.">check_artifact_upstream</span> |
| <span title="Response for upstream status check.">ArtifactUpstreamResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response for usage trends over time.">TrendsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/analytics.py | <span title="Get usage trends over time.">get_usage_trends</span> |
| <span title="Response for usage trends over time.">TrendsResponse</span> | skillmeat/api/schemas/analytics.py | - |
| <span title="Response from GitHub metadata fetch.">MetadataFetchResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Fetch metadata from GitHub for a given source.">fetch_github_metadata</span> |
| <span title="Response from GitHub metadata fetch.">MetadataFetchResponse</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Response from a deployment operation.">DeploymentResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/deployments.py | <span title="Deploy an artifact to a project.">deploy_artifact</span> |
| <span title="Response from a deployment operation.">DeploymentResponse</span> | skillmeat/api/schemas/deployments.py | - |
| <span title="Response from an undeploy operation.">UndeployResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/deployments.py | <span title="Remove a deployed artifact from a project.">undeploy_artifact</span> |
| <span title="Response from an undeploy operation.">UndeployResponse</span> | skillmeat/api/schemas/deployments.py | - |
| <span title="Response from bundle deletion.">BundleDeleteResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Delete a bundle from the collection.">delete_bundle</span> |
| <span title="Response from bundle deletion.">BundleDeleteResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Response from bundle export operation.">BundleExportResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Export artifacts as a bundle.">export_bundle</span> |
| <span title="Response from bundle export operation.">BundleExportResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Response from bundle import operation.">BundleImportResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Import artifact bundle into collection.">import_bundle</span> |
| <span title="Response from bundle import operation.">BundleImportResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Response from bundle preview operation.">BundlePreviewResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Preview bundle before importing.">preview_bundle</span> |
| <span title="Response from bundle preview operation.">BundlePreviewResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Response from bundle validation.">BundleValidationResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/bundles.py | <span title="Validate bundle without importing.">validate_bundle</span> |
| <span title="Response from bundle validation.">BundleValidationResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Response from cache invalidation.">CacheInvalidateResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="Invalidate cache.">invalidate_cache</span> |
| <span title="Response from cache invalidation.">CacheInvalidateResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Response from cache refresh operation.">CacheRefreshResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/cache.py | <span title="Trigger manual cache refresh.">refresh_cache</span> |
| <span title="Response from cache refresh operation.">CacheRefreshResponse</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Response from clearing skip preferences.">SkipClearResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Clear all skip preferences for a project.">clear_skip_preferences</span>, <span title="Remove a single skip preference by artifact key.">remove_skip_preference</span> |
| <span title="Response from clearing skip preferences.">SkipClearResponse</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Response from drift detection for a single artifact.">DriftDetectionResponse</span> | skillmeat/api/schemas/drift.py | - |
| <span title="Response from modification check operation.">ModificationCheckResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Check for modifications in all deployed artifacts.">check_project_modifications</span> |
| <span title="Response from modification check operation.">ModificationCheckResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response from parameter update.">ParameterUpdateResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Update artifact parameters after import.">update_artifact_parameters</span> |
| <span title="Response from parameter update.">ParameterUpdateResponse</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Response from processing duplicate review decisions.">ConfirmDuplicatesResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Process duplicate review decisions from the frontend modal.">confirm_duplicates</span> |
| <span title="Response from processing duplicate review decisions.">ConfirmDuplicatesResponse</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Response listing all deployments in a project.">DeploymentListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/deployments.py | <span title="List all deployed artifacts in a project.">list_deployments</span> |
| <span title="Response listing all deployments in a project.">DeploymentListResponse</span> | skillmeat/api/schemas/deployments.py | - |
| <span title="Response model for a GitHub repository source.">SourceResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Create a new GitHub repository source.">create_source</span>, <span title="Get a marketplace source by ID.">get_source</span>, <span title="Update a marketplace source.">update_source</span> |
| <span title="Response model for a GitHub repository source.">SourceResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response model for a detected artifact in the catalog.">CatalogEntryResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Mark or restore a catalog entry as excluded.">exclude_artifact</span>, <span title="Restore an excluded catalog entry to the catalog.">restore_excluded_artifact</span>, <span title="Update the name for a catalog entry.">update_catalog_entry_name</span> |
| <span title="Response model for a detected artifact in the catalog.">CatalogEntryResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response model for a single marketplace listing.">ListingResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response model for file content from a marketplace artifact.">FileContentResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Get content of a file within a marketplace artifact.">get_artifact_file_content</span> |
| <span title="Response model for file content from a marketplace artifact.">FileContentResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response model for installation operations.">InstallResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Install a marketplace listing.">install_listing</span> |
| <span title="Response model for installation operations.">InstallResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response model for listing available brokers.">BrokerListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="List all available marketplace brokers.">list_brokers</span> |
| <span title="Response model for listing available brokers.">BrokerListResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response model for publish operations.">PublishResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Publish a bundle to the marketplace.">publish_bundle</span> |
| <span title="Response model for publish operations.">PublishResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Response schema for MCP server details.">MCPServerResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/mcp.py | <span title="Create a new MCP server in the collection.">create_mcp_server</span>, <span title="Get details for a specific MCP server.">get_mcp_server</span>, <span title="Update an existing MCP server.">update_mcp_server</span> |
| <span title="Response schema for MCP server details.">MCPServerResponse</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Response schema for MCP server health check.">HealthCheckResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/mcp.py | <span title="Get health status for a specific MCP server.">get_server_health</span> |
| <span title="Response schema for MCP server health check.">HealthCheckResponse</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Response schema for a collection with nested groups.">UserCollectionWithGroupsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/user_collections.py | <span title="Get details for a specific user collection.">get_user_collection</span> |
| <span title="Response schema for a collection with nested groups.">UserCollectionWithGroupsResponse</span> | skillmeat/api/schemas/user_collections.py | - |
| <span title="Response schema for a group with its artifacts list.">GroupWithArtifactsResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Add artifacts to a group.">add_artifacts_to_group</span>, <span title="Bulk reorder artifacts in a group.">reorder_artifacts_in_group</span>, <span title="Get a single group with its artifacts.">get_group</span> |
| <span title="Response schema for a group with its artifacts list.">GroupWithArtifactsResponse</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Response schema for a single artifact.">ArtifactResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Get details for a specific artifact.">get_artifact</span>, <span title="Update an artifact's metadata, tags, and aliases.">update_artifact</span> |
| <span title="Response schema for a single artifact.">ArtifactResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response schema for a single collection.">CollectionResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/collections.py | <span title="Get details for a specific collection.">get_collection</span> |
| <span title="Response schema for a single collection.">CollectionResponse</span> | skillmeat/api/schemas/collections.py | - |
| <span title="Response schema for a single context entity.">ContextEntityResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_entity.py | <span title="Create a new context entity.">create_context_entity</span>, <span title="Get a single context entity by ID.">get_context_entity</span>, <span title="Update a context entity's metadata and/or content.">update_context_entity</span> |
| <span title="Response schema for a single context entity.">ContextEntityResponse</span> | skillmeat/api/schemas/context_entity.py | - |
| <span title="Response schema for a single group.">GroupResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Create a new group in a collection.">create_group</span>, <span title="Update a group's metadata.">update_group</span> |
| <span title="Response schema for a single group.">GroupResponse</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Response schema for a single project template.">ProjectTemplateResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/project_template.py | <span title="Create new project template from entity list.">create_template</span>, <span title="Get project template by ID with full entity details.">get_template</span>, <span title="Update existing project template.">update_template</span> |
| <span title="Response schema for a single project template.">ProjectTemplateResponse</span> | skillmeat/api/schemas/project_template.py | - |
| <span title="Response schema for a single tag.">TagResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/tags.py | <span title="Create a new tag.">create_tag</span>, <span title="Get all tags assigned to a specific artifact.">get_artifact_tags</span>, <span title="Get tag by ID.">get_tag</span>, <span title="Get tag by slug.">get_tag_by_slug</span>, <span title="Search tags by name.">search_tags</span>, <span title="Update tag metadata.">update_tag</span> |
| <span title="Response schema for a single tag.">TagResponse</span> | skillmeat/api/schemas/tags.py | - |
| <span title="Response schema for a single user collection.">UserCollectionResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/user_collections.py | <span title="Create a new user collection.">create_user_collection</span>, <span title="Update a user collection.">update_user_collection</span> |
| <span title="Response schema for a single user collection.">UserCollectionResponse</span> | skillmeat/api/schemas/user_collections.py | - |
| <span title="Response schema for an artifact in a group.">GroupArtifactResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Update an artifact's position in a group.">update_artifact_position</span> |
| <span title="Response schema for an artifact in a group.">GroupArtifactResponse</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Response schema for artifact deployment.">ArtifactDeployResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Deploy artifact from collection to project.">deploy_artifact</span>, <span title="Remove deployed artifact from project.">undeploy_artifact</span> |
| <span title="Response schema for artifact deployment.">ArtifactDeployResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response schema for artifact matching endpoint.">MatchResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/match.py | <span title="Match artifacts against search query.">match_artifacts</span> |
| <span title="Response schema for artifact matching endpoint.">MatchResponse</span> | skillmeat/api/schemas/match.py | - |
| <span title="Response schema for artifact scoring information.">ArtifactScoreResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/scoring.py | <span title="Get confidence scores for an artifact.">get_artifact_scores</span> |
| <span title="Response schema for artifact scoring information.">ArtifactScoreResponse</span> | skillmeat/api/schemas/scoring.py | - |
| <span title="Response schema for artifact sync operation.">ArtifactSyncResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py | <span title="Sync artifact from project to collection.">sync_artifact</span> |
| <span title="Response schema for artifact sync operation.">ArtifactSyncResponse</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Response schema for community score information.">CommunityScoreResponse</span> | skillmeat/api/schemas/scoring.py | - |
| <span title="Response schema for conflict resolution.">ConflictResolveResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/merge.py | <span title="Resolve a single merge conflict.">resolve_conflict</span> |
| <span title="Response schema for conflict resolution.">ConflictResolveResponse</span> | skillmeat/api/schemas/merge.py | - |
| <span title="Response schema for deployment operation.">DeploymentResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/mcp.py | <span title="Deploy MCP server to Claude Desktop.">deploy_mcp_server</span>, <span title="Undeploy MCP server from Claude Desktop.">undeploy_mcp_server</span> |
| <span title="Response schema for deployment operation.">DeploymentResponse</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Response schema for deployment status.">DeploymentStatusResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/mcp.py | <span title="Get deployment status for an MCP server.">get_deployment_status</span> |
| <span title="Response schema for deployment status.">DeploymentStatusResponse</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Response schema for health check of all servers.">AllServersHealthResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/mcp.py | <span title="Get health status for all deployed MCP servers.">get_all_servers_health</span> |
| <span title="Response schema for health check of all servers.">AllServersHealthResponse</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Response schema for listing MCP servers.">MCPServerListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/mcp.py | <span title="List all MCP servers in collection.">list_mcp_servers</span> |
| <span title="Response schema for listing MCP servers.">MCPServerListResponse</span> | skillmeat/api/schemas/mcp.py | - |
| <span title="Response schema for listing groups.">GroupListResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Bulk reorder groups by updating their positions.">reorder_groups</span>, <span title="List all groups in a collection.">list_groups</span> |
| <span title="Response schema for listing groups.">GroupListResponse</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Response schema for merge execution.">MergeExecuteResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/merge.py | <span title="Execute merge with conflict detection.">execute_merge</span> |
| <span title="Response schema for merge execution.">MergeExecuteResponse</span> | skillmeat/api/schemas/merge.py | - |
| <span title="Response schema for merge preview.">MergePreviewResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/merge.py | <span title="Preview merge changes without executing.">preview_merge</span> |
| <span title="Response schema for merge preview.">MergePreviewResponse</span> | skillmeat/api/schemas/merge.py | - |
| <span title="Response schema for merge safety analysis.">MergeSafetyResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/merge.py | <span title="Analyze merge safety (dry run).">analyze_merge</span> |
| <span title="Response schema for merge safety analysis.">MergeSafetyResponse</span> | skillmeat/api/schemas/merge.py | - |
| <span title="Response schema for rating submission confirmation.">UserRatingResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/scoring.py | <span title="Submit a rating for an artifact.">submit_rating</span> |
| <span title="Response schema for rating submission confirmation.">UserRatingResponse</span> | skillmeat/api/schemas/scoring.py | - |
| <span title="Response schema for sync conflict information.">SyncConflictResponse</span> | skillmeat/api/schemas/context_sync.py | - |
| <span title="Response schema for sync operation result.">SyncResultResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_sync.py | <span title="Pull changes from project to collection.">pull_changes</span>, <span title="Push collection changes to project.">push_changes</span>, <span title="Resolve sync conflict.">resolve_conflict</span> |
| <span title="Response schema for sync operation result.">SyncResultResponse</span> | skillmeat/api/schemas/context_sync.py | - |
| <span title="Response schema for sync status information.">SyncStatusResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_sync.py | <span title="Get sync status for a project.">get_sync_status</span> |
| <span title="Response schema for sync status information.">SyncStatusResponse</span> | skillmeat/api/schemas/context_sync.py | - |
| <span title="Response schema for template deployment operation.">DeployTemplateResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/project_template.py | <span title="Deploy project template to target project path with performance optimizations.">deploy_template_endpoint</span> |
| <span title="Response schema for template deployment operation.">DeployTemplateResponse</span> | skillmeat/api/schemas/project_template.py | - |
| <span title="Result for a single imported artifact.">ImportResult</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Result of artifact discovery scan.">DiscoveryResult</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Discover artifacts in a specific project's .claude/ directory.">discover_project_artifacts</span>, <span title="Scan collection for existing artifacts.">discover_artifacts</span> |
| <span title="Result of artifact discovery scan.">DiscoveryResult</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Result of bulk import operation.">BulkImportResult</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py | <span title="Bulk import multiple artifacts with graceful error handling.">bulk_import_artifacts</span> |
| <span title="Result of bulk import operation.">BulkImportResult</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Result of heuristic matching on a file/directory.">HeuristicMatch</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Result of importing artifacts from catalog.">ImportResultDTO</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Import catalog entries to local collection.">import_artifacts</span> |
| <span title="Result of importing artifacts from catalog.">ImportResultDTO</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Result of scanning a GitHub repository.">ScanResultDTO</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/marketplace.py | <span title="Trigger a rescan of a marketplace source.">rescan_source</span> |
| <span title="Result of scanning a GitHub repository.">ScanResultDTO</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Rollback operation result.">RollbackResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/version.py | <span title="Rollback to a specific snapshot.">rollback</span> |
| <span title="Rollback operation result.">RollbackResponse</span> | skillmeat/api/schemas/version.py | - |
| <span title="Schema for updating artifact position in bulk reorder operations.">ArtifactPositionUpdate</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/groups.py | <span title="Update an artifact's position in a group.">update_artifact_position</span> |
| <span title="Schema for updating artifact position in bulk reorder operations.">ArtifactPositionUpdate</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Schema for updating group position in bulk reorder operations.">GroupPositionUpdate</span> | skillmeat/api/schemas/groups.py | - |
| <span title="Search result for a single artifact.">SearchResult</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Single artifact in the top artifacts list.">TopArtifactItem</span> | skillmeat/api/schemas/analytics.py | - |
| <span title="Single artifact to import in bulk operation.">BulkImportArtifact</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Single bundle in list response.">BundleListItem</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Single data point in a usage trend.">TrendDataPoint</span> | skillmeat/api/schemas/analytics.py | - |
| <span title="Single directory to artifact type mapping.">ManualMapEntry</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Single extracted path segment with approval status.">ExtractedSegmentResponse</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Single imported artifact in import result.">ImportedArtifactResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Single matched artifact with confidence score.">MatchedArtifact</span> | skillmeat/api/schemas/match.py | - |
| <span title="Single snapshot representation.">SnapshotResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/version.py | <span title="Get details for a specific snapshot.">get_snapshot</span> |
| <span title="Single snapshot representation.">SnapshotResponse</span> | skillmeat/api/schemas/version.py | - |
| <span title="Single validation issue.">ValidationIssueResponse</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Source type for artifact creation.">ArtifactSourceType</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Standard error codes for programmatic handling.">ErrorCodes</span> | skillmeat/api/schemas/errors.py | - |
| <span title="Standard error response envelope.">ErrorResponse</span> | skillmeat/api/schemas/common.py | - |
| <span title="Standard error response.">ErrorResponse</span> | skillmeat/api/schemas/errors.py | - |
| <span title="Statistics from deduplication process.">DeduplicationStats</span> | skillmeat/api/schemas/marketplace.py | - |
| <span title="Status of an artifact import operation.">ImportStatus</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Status of duplicate confirmation operation.">ConfirmDuplicatesStatus</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Status of the background refresh job.">RefreshJobStatus</span> | skillmeat/api/schemas/cache.py | - |
| <span title="Summary information about a project with deployments.">ProjectSummary</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Summary of a deployed artifact within a project.">DeployedArtifact</span> | skillmeat/api/schemas/projects.py | - |
| <span title="Summary of a group within a collection.">GroupSummary</span> | skillmeat/api/schemas/user_collections.py | - |
| <span title="Summary of an artifact within a bundle.">BundleArtifactSummary</span> | skillmeat/api/schemas/bundles.py | - |
| <span title="Summary of an artifact within a collection.">ArtifactSummary</span> | skillmeat/api/schemas/collections.py | - |
| <span title="Summary of drift detection results across all artifacts.">DriftSummaryResponse</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/drift.py | <span title="Get drift detection summary for a project.">get_project_drift_summary</span> |
| <span title="Summary of drift detection results across all artifacts.">DriftSummaryResponse</span> | skillmeat/api/schemas/drift.py | - |
| <span title="Type of context entity.">ContextEntityType</span> | /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/context_entity.py | <span title="List all context entities with filtering and pagination.">list_context_entities</span> |
| <span title="Type of context entity.">ContextEntityType</span> | skillmeat/api/schemas/context_entity.py | - |
| <span title="Type of match when checking collection membership.">MatchType</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Updatable artifact parameters.">ArtifactParameters</span> | skillmeat/api/schemas/discovery.py | - |
| <span title="Upstream tracking information for an artifact.">ArtifactUpstreamInfo</span> | skillmeat/api/schemas/artifacts.py | - |
| <span title="Validation error detail for a single field.">ValidationErrorDetail</span> | skillmeat/api/schemas/common.py | - |
| <span title="Variable values for template deployment.">TemplateVariableValue</span> | skillmeat/api/schemas/project_template.py | - |
| <span title="Version information for a single artifact instance.">ArtifactVersionInfo</span> | skillmeat/api/schemas/artifacts.py | - |
<!-- CODEBASE_GRAPH:SCHEMAS:END -->
