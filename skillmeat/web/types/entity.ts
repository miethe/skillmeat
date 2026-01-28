/**
 * DEPRECATED: This file is maintained for backward compatibility only.
 *
 * All type definitions have been consolidated into types/artifact.ts
 * under a unified Artifact type system.
 *
 * MIGRATION REQUIRED:
 * - Replace all imports of Entity with Artifact
 * - Replace EntityStatus with SyncStatus
 * - Replace ENTITY_TYPES with ARTIFACT_TYPES
 * - Replace EntityTypeConfig with ArtifactTypeConfig
 * - Replace getEntityTypeConfig with getArtifactTypeConfig
 * - Replace getAllEntityTypes with getAllArtifactTypes
 * - Replace formatEntityId with formatArtifactId
 * - Replace parseEntityId with parseArtifactId
 *
 * See: .claude/guides/entity-to-artifact-migration.md
 * Removal Date: Q3 2026
 */

// ============================================================================
// Imports from artifact.ts (canonical source)
// ============================================================================

import {
  ARTIFACT_TYPES,
  getArtifactTypeConfig,
  getAllArtifactTypes,
  formatArtifactId,
  parseArtifactId,
  type ArtifactTypeConfig,
  type ArtifactFormSchema,
  type ArtifactFormField,
  type ArtifactType,
} from './artifact';

// ============================================================================
// Re-exports from artifact.ts for backward compatibility
// ============================================================================
// These type aliases allow existing imports to continue working.
// New code should import directly from './artifact'.

export type {
  Artifact as Entity,
  ArtifactType as EntityType,
  SyncStatus as EntityStatus,
  ArtifactScope as EntityScope,
} from './artifact';

export { STATUS_DESCRIPTIONS } from './artifact';

// ============================================================================
// Entity Type Registry (deprecated alias)
// ============================================================================

/**
 * @deprecated Use ARTIFACT_TYPES from './artifact' instead
 * Maintained for backward compatibility until Q3 2026
 */
export const ENTITY_TYPES = ARTIFACT_TYPES;

// ============================================================================
// Type Aliases (deprecated)
// ============================================================================

/**
 * @deprecated Use ArtifactTypeConfig from './artifact' instead
 * Maintained for backward compatibility until Q3 2026
 */
export type EntityTypeConfig = ArtifactTypeConfig;

/**
 * @deprecated Use ArtifactFormSchema from './artifact' instead
 * Maintained for backward compatibility until Q3 2026
 */
export type EntityFormSchema = ArtifactFormSchema;

/**
 * @deprecated Use ArtifactFormField from './artifact' instead
 * Maintained for backward compatibility until Q3 2026
 */
export type EntityFormField = ArtifactFormField;

// ============================================================================
// Helper Function Aliases (deprecated)
// ============================================================================

/**
 * Get configuration for an entity type
 *
 * @param type - The entity type to look up
 * @returns EntityTypeConfig with display and form information
 *
 * @deprecated Use getArtifactTypeConfig from './artifact' instead
 * Maintained for backward compatibility until Q3 2026
 *
 * @example
 * ```ts
 * const skillConfig = getEntityTypeConfig('skill');
 * console.log(skillConfig.label); // "Skill"
 * console.log(skillConfig.icon);  // "Sparkles"
 * ```
 */
export const getEntityTypeConfig: (type: ArtifactType) => ArtifactTypeConfig = getArtifactTypeConfig;

/**
 * Get all supported entity types
 *
 * @returns Array of all entity type identifiers
 *
 * @deprecated Use getAllArtifactTypes from './artifact' instead
 * Maintained for backward compatibility until Q3 2026
 *
 * @example
 * ```ts
 * const types = getAllEntityTypes();
 * // ['skill', 'command', 'agent', 'mcp', 'hook']
 * ```
 */
export const getAllEntityTypes: () => ArtifactType[] = getAllArtifactTypes;

/**
 * Format an entity ID from type and name
 *
 * @param type - The entity type
 * @param name - The entity name
 * @returns Formatted ID in "type:name" format
 *
 * @deprecated Use formatArtifactId from './artifact' instead
 * Maintained for backward compatibility until Q3 2026
 *
 * @example
 * ```ts
 * const id = formatEntityId('skill', 'canvas-design');
 * // "skill:canvas-design"
 * ```
 */
export const formatEntityId: (type: ArtifactType, name: string) => string = formatArtifactId;

/**
 * Parse an entity ID into type and name components
 *
 * @param id - The entity ID to parse
 * @returns Object with type and name, or null if invalid format
 *
 * @deprecated Use parseArtifactId from './artifact' instead
 * Maintained for backward compatibility until Q3 2026
 *
 * @example
 * ```ts
 * const parsed = parseEntityId('skill:canvas-design');
 * if (parsed) {
 *   console.log(parsed.type); // "skill"
 *   console.log(parsed.name); // "canvas-design"
 * }
 * ```
 */
export const parseEntityId: (id: string) => { type: ArtifactType; name: string } | null = parseArtifactId;
