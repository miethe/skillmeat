/**
 * API Response Mappers
 *
 * Centralized functions for converting API responses to unified Artifact types.
 * Part of Phase 3 of the Entity-Artifact consolidation refactor.
 *
 * @version 1.0.0
 */

import type {
  Artifact,
  ArtifactType,
  ArtifactScope,
  SyncStatus,
  CollectionRef,
} from '@/types/artifact';
import { Platform } from '@/types/enums';

// ============================================================================
// API Response Types (match backend response structure)
// ============================================================================

/**
 * Metadata object as returned by the API.
 * Properties use snake_case to match backend conventions.
 */
export interface ApiMetadata {
  title?: string;
  description?: string;
  license?: string;
  author?: string;
  version?: string;
  tools?: string[];
}

/**
 * Upstream tracking info as returned by the API.
 * Properties use snake_case to match backend conventions.
 */
export interface ApiUpstream {
  tracking_enabled: boolean;
  current_sha?: string;
  upstream_sha?: string;
  upstream_url?: string;
  upstream_version?: string;
  update_available: boolean;
  has_local_modifications?: boolean;
  last_checked?: string;
}

/**
 * Usage statistics as returned by the API.
 * Properties use snake_case to match backend conventions.
 */
export interface ApiUsageStats {
  total_deployments: number;
  active_projects: number;
  last_used?: string;
  usage_count: number;
}

/**
 * Score metrics as returned by the API.
 * Properties use snake_case to match backend conventions.
 */
export interface ApiScore {
  confidence: number;
  trust_score?: number;
  quality_score?: number;
  match_score?: number;
  last_updated?: string;
}

/**
 * Conflict state information from the API.
 */
export interface ApiConflictState {
  hasConflict: boolean;
  conflictType?: string;
  message?: string;
}

/**
 * Raw API response for a single artifact.
 * Matches the structure returned by the backend endpoints.
 */
export interface ArtifactResponse {
  // Identity (required)
  id: string;
  uuid?: string;
  name: string;
  type: string;

  // Context
  scope?: string;
  collection?: { id: string; name: string } | string;
  collections?: Array<{ id: string; name: string; artifact_count?: number }>;
  groups?: Array<{ id: string; name: string; position?: number }> | null;
  project_path?: string;

  // Source & Origin
  source?: string;
  origin?: string;
  origin_source?: string | null;
  aliases?: string[];

  // Status
  status?: string;
  syncStatus?: string;
  sync_status?: string;
  error?: string | null;
  conflictState?: ApiConflictState;

  // Composite sub-type (only present when type === 'composite')
  composite_type?: 'plugin' | 'stack' | 'suite';

  // Metadata (nested or flattened)
  metadata?: ApiMetadata;
  description?: string;
  tags?: string[];
  tools?: string[];
  target_platforms?: string[] | null;
  author?: string;
  license?: string;
  version?: string;
  dependencies?: string[];

  // Upstream tracking
  upstream?: ApiUpstream;

  // Usage stats
  usage_stats?: ApiUsageStats;
  usageStats?: ApiUsageStats;

  // Score
  score?: ApiScore;

  // Timestamps
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
}

// ============================================================================
// Mapping Context
// ============================================================================

/**
 * Context for artifact mapping operations.
 * Determines how certain fields are interpreted and whether
 * project-specific properties are included.
 */
export type MappingContext = 'collection' | 'project';

// ============================================================================
// Core Mapping Functions
// ============================================================================

/**
 * Determine the synchronization status from an API response.
 *
 * Priority order:
 * 1. Error - if syncStatus === 'error' or error field present
 * 2. Conflict - if syncStatus === 'conflict' or conflictState.hasConflict
 * 3. Modified (project context only) - if modifiedAt > deployedAt or syncStatus === 'modified'
 * 4. Outdated - if upstream.updateAvailable or SHA mismatch
 * 5. Default: synced
 *
 * @param response - Raw API response object
 * @param context - Whether this is a collection or project context
 * @returns Resolved SyncStatus value
 *
 * @example
 * ```ts
 * const status = determineSyncStatus({
 *   syncStatus: 'synced',
 *   upstream: { update_available: true }
 * }, 'collection');
 * // Returns: 'outdated'
 * ```
 */
export function determineSyncStatus(
  response: ArtifactResponse,
  context: MappingContext
): SyncStatus {
  // Normalize status field (API may use different names)
  const rawStatus = response.syncStatus || response.sync_status || response.status;

  // Priority 1: Error state
  if (rawStatus === 'error' || response.error) {
    return 'error';
  }

  // Priority 2: Conflict state
  if (rawStatus === 'conflict' || response.conflictState?.hasConflict) {
    return 'conflict';
  }

  // Priority 3: Modified (project context only)
  if (context === 'project') {
    const modifiedAt = response.modifiedAt || response.modified_at;
    const deployedAt = response.deployedAt || response.deployed_at;

    if (rawStatus === 'modified') {
      return 'modified';
    }

    // Compare timestamps if both exist
    if (modifiedAt && deployedAt) {
      const modifiedTime = new Date(modifiedAt).getTime();
      const deployedTime = new Date(deployedAt).getTime();
      if (modifiedTime > deployedTime) {
        return 'modified';
      }
    }
  }

  // Priority 4: Outdated (upstream has updates)
  if (response.upstream?.update_available) {
    return 'outdated';
  }

  // SHA mismatch also indicates outdated
  if (
    response.upstream?.current_sha &&
    response.upstream?.upstream_sha &&
    response.upstream.current_sha !== response.upstream.upstream_sha
  ) {
    return 'outdated';
  }

  // Priority 5: Default to synced
  return 'synced';
}

/**
 * Convert a raw API response to a unified Artifact type.
 *
 * Handles:
 * - Field name normalization (snake_case to camelCase)
 * - Metadata flattening (nested metadata to top-level properties)
 * - Timestamp resolution (multiple possible field names)
 * - Optional field spreading (only includes defined values)
 * - Status determination based on context
 *
 * @param response - Raw API response object
 * @param context - Whether this is a collection or project context
 * @returns Unified Artifact object
 * @throws Error if required fields (id, name, type) are missing
 *
 * @example
 * ```ts
 * const artifact = mapApiResponseToArtifact({
 *   id: 'skill:canvas-design',
 *   name: 'canvas-design',
 *   type: 'skill',
 *   metadata: { description: 'Design skills' },
 *   added: '2024-01-15T10:00:00Z',
 *   updated: '2024-01-20T15:30:00Z'
 * }, 'collection');
 *
 * console.log(artifact.description); // 'Design skills'
 * console.log(artifact.syncStatus);  // 'synced'
 * ```
 */
export function mapApiResponseToArtifact(
  response: ArtifactResponse,
  context: MappingContext
): Artifact {
  // Validate required fields
  if (!response.id) {
    throw new Error('Artifact mapping error: missing required field "id"');
  }
  if (!response.name) {
    throw new Error('Artifact mapping error: missing required field "name"');
  }
  if (!response.type) {
    throw new Error('Artifact mapping error: missing required field "type"');
  }

  // Validate type is a known artifact type
  const validTypes: ArtifactType[] = ['skill', 'command', 'agent', 'mcp', 'hook', 'composite'];
  if (!validTypes.includes(response.type as ArtifactType)) {
    throw new Error(`Artifact mapping error: unknown type "${response.type}"`);
  }

  // Resolve timestamps (API may use various field names)
  const createdAt =
    response.createdAt || response.created_at || response.added || new Date().toISOString();

  const updatedAt = response.updatedAt || response.updated_at || response.updated || createdAt;

  // Flatten metadata - prefer top-level, fall back to nested
  const description = response.description || response.metadata?.description;
  const author = response.author || response.metadata?.author;
  const license = response.license || response.metadata?.license;
  const version = response.version || response.metadata?.version;

  // Tags come from top-level only (backend consolidates into Artifact.tags)
  const allTags = response.tags || [];

  // Merge tools from both sources, deduplicate
  const topLevelTools = response.tools || [];
  const metadataTools = response.metadata?.tools || [];
  const allTools = [...new Set([...topLevelTools, ...metadataTools])];
  const targetPlatforms = (response.target_platforms || [])
    .map((value) => String(value))
    .filter((value): value is Platform =>
      Object.values(Platform).includes(value as Platform)
    );

  // Resolve scope (default to 'user' for collection context)
  const scope: ArtifactScope =
    (response.scope as ArtifactScope) || (context === 'project' ? 'local' : 'user');

  // Normalize collection references
  let collectionName: string | undefined;
  let collections: CollectionRef[] | undefined;

  if (response.collection) {
    if (typeof response.collection === 'string') {
      collectionName = response.collection;
    } else {
      collectionName = response.collection.name;
    }
  }

  if (response.collections && response.collections.length > 0) {
    collections = response.collections.map((c) => ({
      id: c.id,
      name: c.name,
      ...(c.artifact_count !== undefined && { artifact_count: c.artifact_count }),
    }));
  }

  // Determine sync status
  const syncStatus = determineSyncStatus(response, context);

  // Build the artifact object
  const artifact: Artifact = {
    // Identity (required)
    id: response.id,
    uuid: response.uuid ?? '',
    name: response.name,
    type: response.type as ArtifactType,

    // Context
    scope,
    ...(collectionName && { collection: collectionName }),
    ...(collections && { collections }),
    ...(response.groups && response.groups.length > 0 && { groups: response.groups }),
    ...(context === 'project' && response.project_path && { projectPath: response.project_path }),

    // Metadata (flattened)
    ...(description && { description }),
    ...(allTags.length > 0 && { tags: allTags }),
    ...(allTools.length > 0 && { tools: allTools }),
    ...(targetPlatforms.length > 0 && { targetPlatforms }),
    ...(author && { author }),
    ...(license && { license }),
    ...(version && { version }),
    ...(response.dependencies && { dependencies: response.dependencies }),

    // Composite sub-type
    ...(response.composite_type && { compositeType: response.composite_type }),

    // Source & Origin
    ...(response.source && { source: response.source }),
    ...(response.origin && { origin: response.origin as 'local' | 'github' | 'marketplace' }),
    ...(response.origin_source && { origin_source: response.origin_source }),
    ...(response.aliases && response.aliases.length > 0 && { aliases: response.aliases }),

    // Status
    syncStatus,

    // Upstream tracking
    ...(response.upstream && {
      upstream: {
        enabled: response.upstream.tracking_enabled,
        ...(response.upstream.upstream_url && { url: response.upstream.upstream_url }),
        ...(response.upstream.upstream_version && { version: response.upstream.upstream_version }),
        ...(response.upstream.current_sha && { currentSha: response.upstream.current_sha }),
        ...(response.upstream.upstream_sha && { upstreamSha: response.upstream.upstream_sha }),
        updateAvailable: response.upstream.update_available,
        ...(response.upstream.last_checked && { lastChecked: response.upstream.last_checked }),
      },
    }),

    // Usage statistics
    ...(response.usage_stats || response.usageStats
      ? {
          usageStats: {
            totalDeployments: (response.usage_stats || response.usageStats)!.total_deployments,
            activeProjects: (response.usage_stats || response.usageStats)!.active_projects,
            ...((response.usage_stats || response.usageStats)!.last_used && {
              lastUsed: (response.usage_stats || response.usageStats)!.last_used,
            }),
            usageCount: (response.usage_stats || response.usageStats)!.usage_count,
          },
        }
      : {}),

    // Score
    ...(response.score && {
      score: {
        confidence: response.score.confidence,
        ...(response.score.trust_score !== undefined && { trustScore: response.score.trust_score }),
        ...(response.score.quality_score !== undefined && {
          qualityScore: response.score.quality_score,
        }),
        ...(response.score.match_score !== undefined && { matchScore: response.score.match_score }),
        ...(response.score.last_updated && { lastUpdated: response.score.last_updated }),
      },
    }),

    // Timestamps (required)
    createdAt,
    updatedAt,

    // Project-specific timestamps
    ...((response.deployedAt || response.deployed_at) && {
      deployedAt: response.deployedAt || response.deployed_at,
    }),
    ...((response.modifiedAt || response.modified_at) && {
      modifiedAt: response.modifiedAt || response.modified_at,
    }),
  };

  return artifact;
}

/**
 * Convert an array of API responses to unified Artifact types.
 *
 * Batch processing wrapper around mapApiResponseToArtifact.
 * Preserves order and propagates any validation errors.
 *
 * @param responses - Array of raw API response objects
 * @param context - Whether these are collection or project artifacts
 * @returns Array of unified Artifact objects
 * @throws Error if any response fails validation
 *
 * @example
 * ```ts
 * const artifacts = mapApiResponsesToArtifacts(
 *   apiResponse.items,
 *   'collection'
 * );
 * ```
 */
export function mapApiResponsesToArtifacts(
  responses: ArtifactResponse[],
  context: MappingContext
): Artifact[] {
  return responses.map((response) => mapApiResponseToArtifact(response, context));
}

/**
 * Validate that an artifact has all required fields after mapping.
 *
 * Checks for:
 * - Required identity fields (id, name, type)
 * - Required status field (syncStatus)
 * - Required timestamps (createdAt, updatedAt)
 *
 * @param artifact - Artifact to validate
 * @returns true if artifact has all required fields, false otherwise
 *
 * @example
 * ```ts
 * const artifact = mapApiResponseToArtifact(response, 'collection');
 * if (!validateArtifactMapping(artifact)) {
 *   console.error('Invalid artifact mapping');
 * }
 * ```
 */
export function validateArtifactMapping(artifact: Artifact): boolean {
  // Required identity fields
  if (!artifact.id || typeof artifact.id !== 'string') return false;
  if (!artifact.name || typeof artifact.name !== 'string') return false;
  if (!artifact.type || typeof artifact.type !== 'string') return false;

  // Required status
  const validStatuses: SyncStatus[] = ['synced', 'modified', 'outdated', 'conflict', 'error'];
  if (!artifact.syncStatus || !validStatuses.includes(artifact.syncStatus)) return false;

  // Required timestamps
  if (!artifact.createdAt || typeof artifact.createdAt !== 'string') return false;
  if (!artifact.updatedAt || typeof artifact.updatedAt !== 'string') return false;

  // Validate timestamp format (ISO 8601)
  const isoPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
  if (!isoPattern.test(artifact.createdAt)) return false;
  if (!isoPattern.test(artifact.updatedAt)) return false;

  return true;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Create a minimal valid artifact for testing or placeholder purposes.
 *
 * @param overrides - Properties to override on the default artifact
 * @returns Minimal valid Artifact object
 */
export function createMinimalArtifact(overrides: Partial<Artifact> = {}): Artifact {
  const now = new Date().toISOString();
  return {
    id: 'skill:placeholder',
    uuid: '',
    name: 'placeholder',
    type: 'skill',
    scope: 'user',
    syncStatus: 'synced',
    createdAt: now,
    updatedAt: now,
    ...overrides,
  };
}
