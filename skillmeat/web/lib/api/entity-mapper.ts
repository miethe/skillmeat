/**
 * Centralized Entity Mapper
 *
 * Single source of truth for mapping API responses to Entity objects.
 * Ensures all Entity fields are consistently mapped regardless of context.
 *
 * This module consolidates the duplicate mapping locations that previously
 * existed across the frontend, ensuring consistent Entity data including
 * collection badges.
 *
 * @version 1.0.0
 */

import type {
  Artifact,
  ArtifactType,
  ArtifactScope,
  SyncStatus,
  CollectionRef,
  DeploymentSummary,
} from '@/types/artifact';

// Re-export Entity type alias for backward compatibility
export type Entity = Artifact;

/**
 * Context for entity mapping operations.
 *
 * Determines how certain fields are interpreted and which
 * default values are applied:
 * - 'collection': Artifact in user's global collection (default scope: 'user')
 * - 'project': Artifact deployed to a specific project (default scope: 'local')
 * - 'marketplace': Artifact from external marketplace source
 */
export type EntityContext = 'collection' | 'project' | 'marketplace';

/**
 * Nested metadata object that may be present in API responses.
 */
export interface ApiArtifactMetadata {
  title?: string | null;
  description?: string | null;
  author?: string | null;
  license?: string | null;
  version?: string | null;
  tags?: string[];
  tools?: string[];
  dependencies?: string[];
}

/**
 * Deployment summary from API response.
 */
export interface ApiDeploymentSummary {
  project_path: string;
  project_name: string;
  deployed_at: string;
}

/**
 * Extended API response type that includes all possible fields
 * from various API endpoints (collection, project, marketplace).
 *
 * This type is a superset of the SDK's ArtifactResponse to handle
 * variations in field naming and optional fields.
 */
export interface ApiArtifactResponse {
  // Identity (required in most responses)
  id: string;
  name: string;
  type: string;

  // Source & version - variations across endpoints
  source?: string;
  version?: string;
  resolved_version?: string;

  // Metadata - may be nested or flattened
  metadata?: ApiArtifactMetadata | null;
  description?: string;
  author?: string;
  license?: string;
  tags?: string[];
  tools?: string[];
  dependencies?: string[];

  // Status fields - various naming conventions
  status?: string;
  sync_status?: string;
  syncStatus?: string;
  drift_status?: string;
  deployment_status?: string;

  // Collections - CRITICAL: always map this field
  collections?: Array<{
    id: string;
    name: string;
    artifact_count?: number | null;
  }>;
  collection?: string | { id: string; name: string };

  // Deployments - list of projects where this artifact is deployed
  deployments?: ApiDeploymentSummary[] | null;

  // Scope and project
  scope?: string;
  project_path?: string;
  projectPath?: string;

  // Origin tracking
  origin?: string;
  origin_source?: string | null;
  aliases?: string[];

  // Upstream tracking - nested object
  upstream?: {
    tracking_enabled: boolean;
    current_sha?: string | null;
    upstream_sha?: string | null;
    upstream_url?: string | null;
    upstream_version?: string | null;
    update_available: boolean;
    has_local_modifications?: boolean;
    last_checked?: string | null;
    drift_status?: string | null;
  } | null;

  // Deployment stats
  deployment_stats?: {
    total_deployments: number;
    modified_deployments?: number;
    projects?: Array<unknown>;
  } | null;

  // Usage stats - variations
  usage_stats?: {
    total_deployments: number;
    active_projects: number;
    last_used?: string;
    usage_count: number;
  };
  usageStats?: {
    totalDeployments: number;
    activeProjects: number;
    lastUsed?: string;
    usageCount: number;
  };

  // Score
  score?: {
    confidence: number;
    trust_score?: number;
    quality_score?: number;
    match_score?: number;
    last_updated?: string;
  };

  // Timestamps - various naming conventions
  added?: string;
  updated?: string;
  created_at?: string;
  updated_at?: string;
  createdAt?: string;
  updatedAt?: string;
  deployed_at?: string;
  deployedAt?: string;
  modified_at?: string;
  modifiedAt?: string;

  // Local modification flag
  has_local_modifications?: boolean;
  hasLocalModifications?: boolean;
}

/**
 * Determine the synchronization status from an API response.
 *
 * Priority order:
 * 1. Error - if drift_status is 'error' or status is 'error'
 * 2. Conflict - if drift_status is 'conflict' or status is 'conflict'
 * 3. Modified - if has_local_modifications or drift_status is 'modified'
 * 4. Outdated - if upstream.update_available or drift_status is 'outdated'
 * 5. Default: synced
 *
 * @param artifact - Raw API response object
 * @param context - Whether this is a collection, project, or marketplace context
 * @returns Resolved SyncStatus value
 */
function determineSyncStatus(
  artifact: ApiArtifactResponse,
  context: EntityContext
): SyncStatus {
  // Check drift_status first (most specific)
  const driftStatus = artifact.drift_status ?? artifact.upstream?.drift_status;
  if (driftStatus) {
    const normalizedDrift = driftStatus.toLowerCase();
    if (normalizedDrift === 'error') return 'error';
    if (normalizedDrift === 'conflict') return 'conflict';
    if (normalizedDrift === 'modified') return 'modified';
    if (normalizedDrift === 'outdated') return 'outdated';
  }

  // Check explicit status fields
  const rawStatus = artifact.syncStatus ?? artifact.sync_status ?? artifact.status;
  if (rawStatus) {
    const normalizedStatus = rawStatus.toLowerCase();
    if (normalizedStatus === 'error') return 'error';
    if (normalizedStatus === 'conflict') return 'conflict';
    if (normalizedStatus === 'modified') return 'modified';
    if (normalizedStatus === 'outdated') return 'outdated';
    if (normalizedStatus === 'synced') return 'synced';
  }

  // Check for local modifications
  const hasLocalMods =
    artifact.has_local_modifications ??
    artifact.hasLocalModifications ??
    artifact.upstream?.has_local_modifications;
  if (hasLocalMods) {
    return 'modified';
  }

  // Check upstream for updates
  if (artifact.upstream?.update_available) {
    return 'outdated';
  }

  // Check SHA mismatch
  if (
    artifact.upstream?.current_sha &&
    artifact.upstream?.upstream_sha &&
    artifact.upstream.current_sha !== artifact.upstream.upstream_sha
  ) {
    return 'outdated';
  }

  // Project context: check deployment status
  if (context === 'project' && artifact.deployment_status) {
    const deployStatus = artifact.deployment_status.toLowerCase();
    if (deployStatus === 'modified') return 'modified';
    if (deployStatus === 'outdated') return 'outdated';
  }

  // Default to synced
  return 'synced';
}

/**
 * Resolve timestamps from various API response field names.
 *
 * @param artifact - Raw API response object
 * @returns Object with resolved createdAt and updatedAt ISO strings
 */
function resolveTimestamps(artifact: ApiArtifactResponse): {
  createdAt: string;
  updatedAt: string;
  deployedAt?: string;
  modifiedAt?: string;
} {
  const now = new Date().toISOString();

  const createdAt =
    artifact.createdAt ??
    artifact.created_at ??
    artifact.added ??
    now;

  const updatedAt =
    artifact.updatedAt ??
    artifact.updated_at ??
    artifact.updated ??
    createdAt;

  const deployedAt =
    artifact.deployedAt ??
    artifact.deployed_at ??
    undefined;

  const modifiedAt =
    artifact.modifiedAt ??
    artifact.modified_at ??
    undefined;

  return { createdAt, updatedAt, deployedAt, modifiedAt };
}

/**
 * Map collections array from API response to CollectionRef array.
 *
 * CRITICAL: This ensures collection badges are always properly mapped.
 *
 * @param artifact - Raw API response object
 * @returns Array of CollectionRef objects (never undefined)
 */
function mapCollections(artifact: ApiArtifactResponse): CollectionRef[] {
  if (!artifact.collections || artifact.collections.length === 0) {
    return [];
  }

  return artifact.collections.map((c) => ({
    id: c.id,
    name: c.name,
    artifact_count: c.artifact_count ?? undefined,
  }));
}

/**
 * Map deployments array from API response to DeploymentSummary array.
 *
 * @param artifact - Raw API response object
 * @returns Array of DeploymentSummary objects or null
 */
function mapDeployments(artifact: ApiArtifactResponse): DeploymentSummary[] | null {
  if (!artifact.deployments) {
    return null;
  }

  if (artifact.deployments.length === 0) {
    return [];
  }

  return artifact.deployments.map((d) => ({
    project_path: d.project_path,
    project_name: d.project_name,
    deployed_at: d.deployed_at,
  }));
}

/**
 * Extract primary collection identifier from various API response formats.
 *
 * Returns the collection `id` (e.g., "default") which matches the filesystem
 * collection name that the API expects, not the display `name` (e.g., "Default Collection").
 *
 * @param artifact - Raw API response object
 * @returns Primary collection id or undefined
 */
function extractPrimaryCollection(artifact: ApiArtifactResponse): string | undefined {
  // Check collections array first
  if (artifact.collections && artifact.collections.length > 0) {
    const firstCollection = artifact.collections[0];
    if (firstCollection) {
      return firstCollection.id;
    }
  }

  // Check single collection field
  if (artifact.collection) {
    if (typeof artifact.collection === 'string') {
      return artifact.collection;
    }
    return artifact.collection.id;
  }

  return undefined;
}

/**
 * Single source of truth for mapping API responses to Entity objects.
 *
 * Ensures all 24+ Entity fields are consistently mapped regardless of context,
 * eliminating the inconsistencies that previously existed across multiple
 * mapping locations.
 *
 * @param artifact - Raw API response object
 * @param context - Mapping context: 'collection', 'project', or 'marketplace'
 * @returns Fully mapped Entity object with all fields populated
 * @throws Error if required fields (id, name, type) are missing
 *
 * @example
 * ```ts
 * const entity = mapArtifactToEntity(apiResponse, 'collection');
 * console.log(entity.collections); // Always populated, never undefined
 * console.log(entity.syncStatus);  // Correctly determined from all status fields
 * ```
 */
export function mapArtifactToEntity(
  artifact: ApiArtifactResponse,
  context: EntityContext = 'collection'
): Entity {
  // Validate required fields
  if (!artifact.id) {
    throw new Error('Entity mapping error: missing required field "id"');
  }
  if (!artifact.name) {
    throw new Error('Entity mapping error: missing required field "name"');
  }
  if (!artifact.type) {
    throw new Error('Entity mapping error: missing required field "type"');
  }

  // Validate type is a known artifact type
  const validTypes: ArtifactType[] = ['skill', 'command', 'agent', 'mcp', 'hook'];
  if (!validTypes.includes(artifact.type as ArtifactType)) {
    throw new Error(`Entity mapping error: unknown type "${artifact.type}"`);
  }

  // Resolve timestamps
  const timestamps = resolveTimestamps(artifact);

  // Resolve scope based on context
  const scope: ArtifactScope =
    (artifact.scope as ArtifactScope) ?? (context === 'project' ? 'local' : 'user');

  // Flatten metadata - prefer top-level, fall back to nested
  const description =
    artifact.description ?? artifact.metadata?.description ?? undefined;
  const author = artifact.author ?? artifact.metadata?.author ?? undefined;
  const license = artifact.license ?? artifact.metadata?.license ?? undefined;

  // Merge tags from both sources, deduplicate
  const topLevelTags = artifact.tags ?? [];
  const metadataTags = artifact.metadata?.tags ?? [];
  const tags = [...new Set([...topLevelTags, ...metadataTags])];

  // Merge tools from both sources, deduplicate
  const topLevelTools = artifact.tools ?? [];
  const metadataTools = artifact.metadata?.tools ?? [];
  const tools = [...new Set([...topLevelTools, ...metadataTools])];

  // Resolve version (prefer resolved_version, fall back to version)
  const version = artifact.resolved_version ?? artifact.version ?? artifact.metadata?.version;

  // Dependencies from metadata
  const dependencies = artifact.dependencies ?? artifact.metadata?.dependencies;

  // Map collections - CRITICAL: always populate this field
  const collections = mapCollections(artifact);
  const collection = extractPrimaryCollection(artifact);

  // Map deployments
  const deployments = mapDeployments(artifact);

  // Determine sync status
  const syncStatus = determineSyncStatus(artifact, context);

  // Build upstream tracking info if present
  let upstream: Entity['upstream'] | undefined;
  if (artifact.upstream) {
    upstream = {
      enabled: artifact.upstream.tracking_enabled,
      updateAvailable: artifact.upstream.update_available,
      ...(artifact.upstream.upstream_url && { url: artifact.upstream.upstream_url }),
      ...(artifact.upstream.upstream_version && { version: artifact.upstream.upstream_version }),
      ...(artifact.upstream.current_sha && { currentSha: artifact.upstream.current_sha }),
      ...(artifact.upstream.upstream_sha && { upstreamSha: artifact.upstream.upstream_sha }),
      ...(artifact.upstream.last_checked && { lastChecked: artifact.upstream.last_checked }),
    };
  }

  // Build usage stats if present
  let usageStats: Entity['usageStats'] | undefined;
  if (artifact.usage_stats) {
    usageStats = {
      totalDeployments: artifact.usage_stats.total_deployments,
      activeProjects: artifact.usage_stats.active_projects,
      usageCount: artifact.usage_stats.usage_count,
      ...(artifact.usage_stats.last_used && { lastUsed: artifact.usage_stats.last_used }),
    };
  } else if (artifact.usageStats) {
    usageStats = {
      totalDeployments: artifact.usageStats.totalDeployments,
      activeProjects: artifact.usageStats.activeProjects,
      usageCount: artifact.usageStats.usageCount,
      ...(artifact.usageStats.lastUsed && { lastUsed: artifact.usageStats.lastUsed }),
    };
  }

  // Build score if present
  let score: Entity['score'] | undefined;
  if (artifact.score) {
    score = {
      confidence: artifact.score.confidence,
      ...(artifact.score.trust_score !== undefined && {
        trustScore: artifact.score.trust_score,
      }),
      ...(artifact.score.quality_score !== undefined && {
        qualityScore: artifact.score.quality_score,
      }),
      ...(artifact.score.match_score !== undefined && {
        matchScore: artifact.score.match_score,
      }),
      ...(artifact.score.last_updated && { lastUpdated: artifact.score.last_updated }),
    };
  }

  // Resolve project path
  const projectPath = artifact.projectPath ?? artifact.project_path;

  // Build the complete Entity object
  const entity: Entity = {
    // Identity (required)
    id: artifact.id,
    name: artifact.name,
    type: artifact.type as ArtifactType,

    // Context
    scope,
    ...(collection && { collection }),
    collections, // ALWAYS include collections array (may be empty)
    ...(projectPath && { projectPath }),
    ...(deployments !== null && { deployments }), // Include if present (even if empty array)

    // Metadata (flattened)
    ...(description && { description }),
    ...(tags.length > 0 && { tags }),
    ...(tools.length > 0 && { tools }),
    ...(author && { author }),
    ...(license && { license }),
    ...(version && { version }),
    ...(dependencies && dependencies.length > 0 && { dependencies }),

    // Source & Origin
    ...(artifact.source && { source: artifact.source }),
    ...(artifact.origin && { origin: artifact.origin as 'local' | 'github' | 'marketplace' }),
    ...(artifact.origin_source && { origin_source: artifact.origin_source }),
    ...(artifact.aliases && artifact.aliases.length > 0 && { aliases: artifact.aliases }),

    // Status
    syncStatus,

    // Upstream tracking
    ...(upstream && { upstream }),

    // Usage statistics
    ...(usageStats && { usageStats }),

    // Score
    ...(score && { score }),

    // Timestamps
    createdAt: timestamps.createdAt,
    updatedAt: timestamps.updatedAt,
    ...(timestamps.deployedAt && { deployedAt: timestamps.deployedAt }),
    ...(timestamps.modifiedAt && { modifiedAt: timestamps.modifiedAt }),
  };

  return entity;
}

/**
 * Batch mapping utility for lists of artifacts.
 *
 * Preserves order and propagates any validation errors.
 *
 * @param artifacts - Array of raw API response objects
 * @param context - Mapping context: 'collection', 'project', or 'marketplace'
 * @returns Array of fully mapped Entity objects
 * @throws Error if any artifact fails validation
 *
 * @example
 * ```ts
 * const entities = mapArtifactsToEntities(apiResponse.items, 'collection');
 * // All entities have consistent field mapping including collections
 * ```
 */
export function mapArtifactsToEntities(
  artifacts: ApiArtifactResponse[],
  context: EntityContext = 'collection'
): Entity[] {
  return artifacts.map((artifact) => mapArtifactToEntity(artifact, context));
}

/**
 * Safe mapping that returns null instead of throwing on invalid artifacts.
 *
 * Useful for gracefully handling partial API responses where some
 * artifacts may be malformed.
 *
 * @param artifact - Raw API response object
 * @param context - Mapping context
 * @returns Mapped Entity or null if mapping fails
 */
export function mapArtifactToEntitySafe(
  artifact: ApiArtifactResponse,
  context: EntityContext = 'collection'
): Entity | null {
  try {
    return mapArtifactToEntity(artifact, context);
  } catch {
    console.warn('[entity-mapper] Failed to map artifact:', artifact.id ?? 'unknown');
    return null;
  }
}

/**
 * Batch mapping with filtering of invalid artifacts.
 *
 * Silently filters out artifacts that fail validation, logging warnings.
 *
 * @param artifacts - Array of raw API response objects
 * @param context - Mapping context
 * @returns Array of successfully mapped Entity objects
 */
export function mapArtifactsToEntitiesSafe(
  artifacts: ApiArtifactResponse[],
  context: EntityContext = 'collection'
): Entity[] {
  return artifacts
    .map((artifact) => mapArtifactToEntitySafe(artifact, context))
    .filter((entity): entity is Entity => entity !== null);
}
