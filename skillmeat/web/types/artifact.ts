/**
 * Artifact Types for SkillMeat Collection
 *
 * These types represent artifacts in the collection (Skills, Commands, Agents, MCP servers, Hooks, Plugins)
 *
 * @version 2.0.0 - Unified Artifact interface consolidating former Artifact and Entity types
 */

import { Platform, Tool } from './enums';

/**
 * Supported artifact types in SkillMeat.
 */
export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook' | 'composite';

/**
 * Artifact scope determines where the artifact is stored.
 * - 'user': Global scope in ~/.skillmeat/collection/
 * - 'local': Project-specific scope in .claude/
 */
export type ArtifactScope = 'user' | 'local';

/**
 * Unified synchronization status enum.
 *
 * Represents the sync state of an artifact across both collection
 * and deployment contexts. Replaces former ArtifactStatus and EntityStatus.
 *
 * Status mapping guide:
 *
 * Collection context:
 *   - synced: Artifact matches collection version
 *   - outdated: Newer version available upstream
 *   - conflict: Unresolvable conflict with upstream
 *   - error: Error fetching or processing
 *
 * Project context:
 *   - synced: Deployed artifact matches source
 *   - modified: Local changes not in source
 *   - outdated: Source has newer version
 *   - conflict: Merge conflict between local and source
 *   - error: Error in deployment or sync process
 */
export type SyncStatus = 'synced' | 'modified' | 'outdated' | 'conflict' | 'error';

/**
 * Human-readable descriptions for each sync status value.
 * Useful for UI display and tooltips.
 */
export const STATUS_DESCRIPTIONS: Record<SyncStatus, string> = {
  synced: 'Up to date with source',
  modified: 'Local modifications not in source',
  outdated: 'Newer version available',
  conflict: 'Unresolvable conflict',
  error: 'Error in sync process',
};

/**
 * @deprecated Use SyncStatus instead. ArtifactStatus is retained for backward compatibility.
 */
export type ArtifactStatus = SyncStatus;

/**
 * Reference to a collection that an artifact belongs to.
 * Supports many-to-many relationship between artifacts and collections.
 */
export interface CollectionRef {
  /** Unique identifier for the collection */
  id: string;
  /** Human-readable collection name */
  name: string;
  /** Number of artifacts in this collection (optional for performance) */
  artifact_count?: number;
}

/**
 * Summary of a single deployment of an artifact.
 * Used for tracking where artifacts are deployed.
 */
export interface DeploymentSummary {
  /** Absolute path to the project directory */
  project_path: string;
  /** Human-readable project name */
  project_name: string;
  /** ISO 8601 timestamp when artifact was deployed to this project */
  deployed_at: string;
  /** Whether local modifications have been detected in this deployment */
  local_modifications?: boolean;
  /** SHA-256 content hash at deployment time */
  content_hash?: string;
  /** Deployment profile ID (e.g., "claude_code", "codex") */
  deployment_profile_id?: string;
  /** Target platform for this deployment */
  platform?: string;
}

/**
 * Artifact metadata containing descriptive information.
 * @deprecated Metadata is now flattened into the Artifact interface. Kept for backward compatibility.
 */
export interface ArtifactMetadata {
  title?: string;
  description?: string;
  license?: string;
  author?: string;
  version?: string;
  tags?: string[];
  tools?: Tool[]; // Claude Code tools used by this artifact
}

/**
 * Upstream tracking information for artifacts sourced from external repositories.
 * @deprecated Use Artifact.upstream instead. Kept for backward compatibility.
 */
export interface UpstreamStatus {
  hasUpstream: boolean;
  upstreamUrl?: string;
  upstreamVersion?: string;
  currentVersion?: string;
  isOutdated: boolean;
  lastChecked?: string;
}

/**
 * Usage statistics for an artifact.
 * @deprecated Use Artifact.usageStats instead. Kept for backward compatibility.
 */
export interface UsageStats {
  totalDeployments: number;
  activeProjects: number;
  lastUsed?: string;
  usageCount: number;
}

/**
 * Scoring metrics for artifact quality and relevance.
 * @deprecated Use Artifact.score instead. Kept for backward compatibility.
 */
export interface ArtifactScore {
  confidence: number;
  trustScore?: number;
  qualityScore?: number;
  matchScore?: number;
  lastUpdated?: string;
}

/**
 * Unified artifact type for SkillMeat collection and project contexts.
 *
 * Consolidates former Artifact and Entity types into a single representation
 * that supports both collection and deployment scenarios.
 *
 * @version 2.0.0
 */
export interface Artifact {
  // ============================================================================
  // Identity (required)
  // ============================================================================

  /** Unique identifier in "type:name" format (e.g., "skill:canvas-design") */
  id: string;

  /** Human-readable artifact name */
  name: string;

  /** Artifact type: skill, command, agent, mcp, hook, or composite */
  type: ArtifactType;

  // ============================================================================
  // Context (supports collection OR project scope)
  // ============================================================================

  /** Storage scope: 'user' (global) or 'local' (project-specific) */
  scope: ArtifactScope;

  /** Collection name when artifact is in collection context */
  collection?: string;

  /** All collections this artifact belongs to (many-to-many relationship) */
  collections?: CollectionRef[];

  /** Project path when artifact is deployed to a project */
  projectPath?: string;

  /** All deployments of this artifact across projects */
  deployments?: DeploymentSummary[] | null;

  // ============================================================================
  // Metadata (flattened from former nested objects)
  // ============================================================================

  /** Human-readable description of the artifact's purpose */
  description?: string;

  /** Categorization tags for filtering and discovery */
  tags?: string[];

  /** Artifact author or maintainer */
  author?: string;

  /** License identifier (e.g., "MIT", "Apache-2.0") */
  license?: string;

  /** Semantic version string */
  version?: string;

  /** Claude Code tools used by this artifact */
  tools?: string[];

  /** List of artifact dependencies (artifact IDs or package names) */
  dependencies?: string[];

  /** Optional platform targeting restrictions (undefined/null means universal) */
  targetPlatforms?: Platform[];

  /** Groups this artifact belongs to (only populated when include_groups=true) */
  groups?: { id: string; name: string; position?: number }[] | null;

  // ============================================================================
  // Source & Origin
  // ============================================================================

  /** Source specification: GitHub spec (owner/repo/path) or local file path */
  source?: string;

  /** Origin category indicating where the artifact came from */
  origin?: 'local' | 'github' | 'marketplace';

  /** Platform source when origin is 'marketplace' (e.g., 'github', 'gitlab', 'bitbucket') */
  origin_source?: string;

  /** Alternative names for referencing this artifact */
  aliases?: string[];

  // ============================================================================
  // Unified Status
  // ============================================================================

  /**
   * Synchronization status indicating the artifact's state relative to its source.
   * Replaces former ArtifactStatus and EntityStatus fields.
   */
  syncStatus: SyncStatus;

  // ============================================================================
  // Upstream Tracking (optional)
  // ============================================================================

  /**
   * Upstream repository tracking information.
   * Present when artifact is sourced from an external repository.
   */
  upstream?: {
    /** Whether upstream tracking is enabled for this artifact */
    enabled: boolean;
    /** URL of the upstream repository */
    url?: string;
    /** Version tag or branch being tracked */
    version?: string;
    /** Current local commit SHA */
    currentSha?: string;
    /** Latest upstream commit SHA */
    upstreamSha?: string;
    /** Whether an update is available from upstream */
    updateAvailable: boolean;
    /** ISO 8601 timestamp of last upstream check */
    lastChecked?: string;
  };

  // ============================================================================
  // Usage Statistics (optional)
  // ============================================================================

  /**
   * Usage statistics tracking deployment and activation patterns.
   * Useful for analytics and popularity ranking.
   */
  usageStats?: {
    /** Total number of times this artifact has been deployed */
    totalDeployments: number;
    /** Number of projects currently using this artifact */
    activeProjects: number;
    /** ISO 8601 timestamp of last usage */
    lastUsed?: string;
    /** Total usage count (invocations, not just deployments) */
    usageCount: number;
  };

  // ============================================================================
  // Scoring (optional)
  // ============================================================================

  /**
   * Quality and relevance scoring metrics.
   * Used for search ranking and recommendations.
   */
  score?: {
    /** Overall confidence score (0-1) */
    confidence: number;
    /** Trust score based on source reputation (0-1) */
    trustScore?: number;
    /** Quality score based on code analysis (0-1) */
    qualityScore?: number;
    /** Search match score for relevance ranking (0-1) */
    matchScore?: number;
    /** ISO 8601 timestamp of last score calculation */
    lastUpdated?: string;
  };

  // ============================================================================
  // Timestamps
  // ============================================================================

  /** ISO 8601 timestamp when artifact was first added to collection */
  createdAt: string;

  /** ISO 8601 timestamp of last update (metadata or content) */
  updatedAt: string;

  /** ISO 8601 timestamp when artifact was deployed to current project (former Entity field) */
  deployedAt?: string;

  /** ISO 8601 timestamp of last local modification (former Entity field) */
  modifiedAt?: string;
}

// ============================================================================
// Artifact Type Registry
// ============================================================================

/**
 * Form field configuration for artifact type forms.
 * Defines how a single field is rendered in create/edit forms.
 */
export interface ArtifactFormField {
  /** Field name (maps to artifact property) */
  name: string;
  /** User-facing field label */
  label: string;
  /** Input type: text input, textarea, select dropdown, tags, or checkbox */
  type: 'text' | 'textarea' | 'select' | 'tags' | 'boolean';
  /** Whether field must have a value */
  required?: boolean;
  /** Placeholder text for input fields */
  placeholder?: string;
  /** Options for select fields */
  options?: { value: string; label: string }[];
}

/**
 * Form schema for artifact type creation/editing.
 * Defines which fields are shown and how they are rendered.
 */
export interface ArtifactFormSchema {
  /** Array of form fields to display */
  fields: ArtifactFormField[];
}

/**
 * Configuration for a specific artifact type.
 * Defines UI presentation, form fields, and validation requirements.
 */
export interface ArtifactTypeConfig {
  /** The artifact type identifier */
  type: ArtifactType;
  /** Display label (singular) */
  label: string;
  /** Display label (plural) */
  pluralLabel: string;
  /** Lucide icon name for visual representation */
  icon: string;
  /** Tailwind color class for icon/badge coloring */
  color: string;
  /** Required file name for artifact validation (e.g., SKILL.md) */
  requiredFile: string;
  /** Form field schema for creation/editing */
  formSchema: ArtifactFormSchema;
}

/**
 * Global registry of all supported artifact types and their configurations.
 *
 * Used for:
 * - Dynamic form rendering (showing correct fields for artifact type)
 * - UI rendering (icons, colors, labels)
 * - Validation (required file names)
 * - Type lookups throughout the application
 */
export const ARTIFACT_TYPES: Record<ArtifactType, ArtifactTypeConfig> = {
  skill: {
    type: 'skill',
    label: 'Skill',
    pluralLabel: 'Skills',
    icon: 'Sparkles',
    color: 'text-purple-500',
    requiredFile: 'SKILL.md',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-skill',
        },
        {
          name: 'source',
          label: 'Source',
          type: 'text',
          required: true,
          placeholder: 'user/repo/path or local path',
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this skill do?',
        },
        {
          name: 'tags',
          label: 'Tags',
          type: 'tags',
          required: false,
          placeholder: 'Add tags...',
        },
      ],
    },
  },
  command: {
    type: 'command',
    label: 'Command',
    pluralLabel: 'Commands',
    icon: 'Terminal',
    color: 'text-blue-500',
    requiredFile: 'COMMAND.md',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-command',
        },
        {
          name: 'source',
          label: 'Source',
          type: 'text',
          required: true,
          placeholder: 'user/repo/path or local path',
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this command do?',
        },
        {
          name: 'tags',
          label: 'Tags',
          type: 'tags',
          required: false,
          placeholder: 'Add tags...',
        },
      ],
    },
  },
  agent: {
    type: 'agent',
    label: 'Agent',
    pluralLabel: 'Agents',
    icon: 'Bot',
    color: 'text-green-500',
    requiredFile: 'AGENT.md',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-agent',
        },
        {
          name: 'source',
          label: 'Source',
          type: 'text',
          required: true,
          placeholder: 'user/repo/path or local path',
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this agent do?',
        },
        {
          name: 'tags',
          label: 'Tags',
          type: 'tags',
          required: false,
          placeholder: 'Add tags...',
        },
      ],
    },
  },
  mcp: {
    type: 'mcp',
    label: 'MCP Server',
    pluralLabel: 'MCP Servers',
    icon: 'Server',
    color: 'text-orange-500',
    requiredFile: 'mcp.json',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-mcp-server',
        },
        {
          name: 'command',
          label: 'Command',
          type: 'text',
          required: true,
          placeholder: 'npx @modelcontextprotocol/server-example',
        },
        {
          name: 'args',
          label: 'Arguments',
          type: 'text',
          required: false,
          placeholder: '--port 3000',
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this MCP server provide?',
        },
      ],
    },
  },
  hook: {
    type: 'hook',
    label: 'Hook',
    pluralLabel: 'Hooks',
    icon: 'Webhook',
    color: 'text-pink-500',
    requiredFile: 'HOOK.md',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-hook',
        },
        {
          name: 'trigger',
          label: 'Trigger',
          type: 'select',
          required: true,
          options: [
            { value: 'pre-commit', label: 'Pre-commit' },
            { value: 'post-commit', label: 'Post-commit' },
            { value: 'pre-push', label: 'Pre-push' },
          ],
        },
        {
          name: 'script',
          label: 'Script',
          type: 'textarea',
          required: true,
          placeholder: '#!/bin/bash\necho "Running hook..."',
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this hook do?',
        },
      ],
    },
  },
  composite: {
    type: 'composite',
    label: 'Plugin',
    pluralLabel: 'Plugins',
    icon: 'Blocks',
    color: 'text-indigo-500',
    requiredFile: 'PLUGIN.md',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-plugin',
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this plugin do?',
        },
        {
          name: 'tags',
          label: 'Tags',
          type: 'tags',
          required: false,
          placeholder: 'Add tags...',
        },
        {
          name: 'members',
          label: 'Members',
          type: 'tags',
          required: false,
          placeholder: 'artifact_id[:position]',
        },
      ],
    },
  },
};

// ============================================================================
// Artifact Type Helper Functions
// ============================================================================

/**
 * Get configuration for a specific artifact type.
 *
 * @param type - The artifact type to look up
 * @returns ArtifactTypeConfig with display and form information
 * @throws Error if type not found in registry
 *
 * @example
 * ```ts
 * const skillConfig = getArtifactTypeConfig('skill');
 * console.log(skillConfig.label); // "Skill"
 * console.log(skillConfig.icon);  // "Sparkles"
 * ```
 */
export function getArtifactTypeConfig(type: ArtifactType): ArtifactTypeConfig {
  const config = ARTIFACT_TYPES[type];
  if (!config) {
    throw new Error(`Unknown artifact type: ${type}`);
  }
  return config;
}

/**
 * Get array of all artifact types.
 *
 * @returns Array of all artifact type identifiers
 *
 * @example
 * ```ts
 * const types = getAllArtifactTypes();
 * // ['skill', 'command', 'agent', 'mcp', 'hook', 'composite']
 * ```
 */
export function getAllArtifactTypes(): ArtifactType[] {
  return Object.keys(ARTIFACT_TYPES) as ArtifactType[];
}

/**
 * Format an artifact ID from type and name.
 *
 * @param type - The artifact type
 * @param name - The artifact name
 * @returns Formatted ID in "type:name" format
 *
 * @example
 * ```ts
 * const id = formatArtifactId('skill', 'canvas-design');
 * // "skill:canvas-design"
 * const pluginId = formatArtifactId('composite', 'my-plugin');
 * // "composite:my-plugin"
 * ```
 */
export function formatArtifactId(type: ArtifactType, name: string): string {
  return `${type}:${name}`;
}

/**
 * Parse an artifact ID into type and name components.
 *
 * @param id - The artifact ID to parse
 * @returns Object with type and name, or null if invalid format
 *
 * @example
 * ```ts
 * const parsed = parseArtifactId('skill:canvas-design');
 * if (parsed) {
 *   console.log(parsed.type); // "skill"
 *   console.log(parsed.name); // "canvas-design"
 * }
 *
 * const plugin = parseArtifactId('composite:my-plugin');
 * if (plugin) {
 *   console.log(plugin.type); // "composite"
 *   console.log(plugin.name); // "my-plugin"
 * }
 * ```
 */
export function parseArtifactId(id: string): { type: ArtifactType; name: string } | null {
  const parts = id.split(':');
  if (parts.length !== 2) return null;

  const [type, name] = parts;
  if (!type || !name || !ARTIFACT_TYPES[type as ArtifactType]) return null;

  return { type: type as ArtifactType, name };
}

// ============================================================================
// Query and Filter Types
// ============================================================================

/**
 * Filter options for querying artifacts.
 */
export interface ArtifactFilters {
  type?: ArtifactType | 'all';
  status?: SyncStatus | 'all';
  scope?: ArtifactScope | 'all';
  /** Platform filter; 'universal' means artifacts without target platform restrictions */
  platform?: Platform | 'universal' | 'all';
  search?: string;
  /** Group ID for filtering artifacts by group (only applicable in specific collection context) */
  groupId?: string;
  /** Tag IDs to filter artifacts by (multi-select) */
  tags?: string[];
  /** Tool names to filter artifacts by (multi-select) */
  tools?: string[];
}

export type SortField = 'name' | 'updatedAt' | 'usageCount' | 'confidence';
export type SortOrder = 'asc' | 'desc';

export interface ArtifactSort {
  field: SortField;
  order: SortOrder;
}

export interface ArtifactsResponse {
  artifacts: Artifact[];
  total: number;
  page: number;
  pageSize: number;
}

// ============================================================================
// Backward Compatibility Aliases (6-month deprecation window)
// ============================================================================
// These are replaced incrementally over time.
// See: .claude/guides/entity-to-artifact-migration.md
// Removal Date: Q3 2026

/**
 * @deprecated Use `Artifact` instead
 * Maintained for backward compatibility until Q3 2026
 */
export type Entity = Artifact;

/**
 * @deprecated Use `ArtifactType` instead
 * Maintained for backward compatibility until Q3 2026
 */
export type EntityType = ArtifactType;

/**
 * @deprecated Use `SyncStatus` instead
 * Maintained for backward compatibility until Q3 2026
 */
export type EntityStatus = SyncStatus;

/**
 * @deprecated Use `ArtifactScope` instead
 * Maintained for backward compatibility until Q3 2026
 */
export type EntityScope = ArtifactScope;
