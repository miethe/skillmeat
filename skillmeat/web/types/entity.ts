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

/**
 * Unified artifact type for SkillMeat collection and project contexts.
 *
 * @deprecated Use Artifact from './artifact' instead.
 * This type is maintained for backward compatibility until Q3 2026.
 *
 * The unified Artifact type consolidates former Entity and Artifact types
 * into a single representation that supports both collection and deployment scenarios.
 *
 * Migration: Import { Artifact } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import type { Entity } from '@/types/entity';
 *
 * // New
 * import type { Artifact } from '@/types';
 * ```
 */
export type { Artifact as Entity } from './artifact';

/**
 * Supported artifact types in SkillMeat.
 *
 * @deprecated Use ArtifactType from './artifact' instead.
 * This type is maintained for backward compatibility until Q3 2026.
 *
 * Migration: Import { ArtifactType } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import type { EntityType } from '@/types/entity';
 *
 * // New
 * import type { ArtifactType } from '@/types';
 * ```
 */
export type { ArtifactType as EntityType } from './artifact';

/**
 * Unified synchronization status enum.
 *
 * @deprecated Use SyncStatus from './artifact' instead.
 * This type is maintained for backward compatibility until Q3 2026.
 *
 * Represents the sync state of an artifact across both collection
 * and deployment contexts.
 *
 * Migration: Import { SyncStatus } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import type { EntityStatus } from '@/types/entity';
 *
 * // New
 * import type { SyncStatus } from '@/types';
 * ```
 */
export type { SyncStatus as EntityStatus } from './artifact';

/**
 * Artifact scope determines where the artifact is stored.
 *
 * @deprecated Use ArtifactScope from './artifact' instead.
 * This type is maintained for backward compatibility until Q3 2026.
 *
 * - 'user': Global scope in ~/.skillmeat/collection/
 * - 'local': Project-specific scope in .claude/
 *
 * Migration: Import { ArtifactScope } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import type { EntityScope } from '@/types/entity';
 *
 * // New
 * import type { ArtifactScope } from '@/types';
 * ```
 */
export type { ArtifactScope as EntityScope } from './artifact';

/**
 * Human-readable descriptions for each sync status value.
 * Useful for UI display and tooltips.
 *
 * @deprecated Use STATUS_DESCRIPTIONS from './artifact' instead.
 * This export is maintained for backward compatibility until Q3 2026.
 *
 * Migration: Import { STATUS_DESCRIPTIONS } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 */
export { STATUS_DESCRIPTIONS } from './artifact';

// ============================================================================
// Entity Type Registry (deprecated alias)
// ============================================================================

/**
 * Global registry of all supported entity types and their configurations.
 *
 * @deprecated Use ARTIFACT_TYPES from './artifact' instead.
 * This constant is maintained for backward compatibility until Q3 2026.
 *
 * Used for:
 * - Dynamic form rendering (showing correct fields for artifact type)
 * - UI rendering (icons, colors, labels)
 * - Validation (required file names)
 * - Type lookups throughout the application
 *
 * Migration: Import { ARTIFACT_TYPES } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import { ENTITY_TYPES } from '@/types/entity';
 *
 * // New
 * import { ARTIFACT_TYPES } from '@/types';
 * ```
 */
export const ENTITY_TYPES = ARTIFACT_TYPES;

// ============================================================================
// Type Aliases (deprecated)
// ============================================================================

/**
 * Configuration for a specific entity type.
 *
 * @deprecated Use ArtifactTypeConfig from './artifact' instead.
 * This type is maintained for backward compatibility until Q3 2026.
 *
 * Defines UI presentation, form fields, and validation requirements.
 *
 * Migration: Import { ArtifactTypeConfig } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import type { EntityTypeConfig } from '@/types/entity';
 *
 * // New
 * import type { ArtifactTypeConfig } from '@/types';
 * ```
 */
export type EntityTypeConfig = ArtifactTypeConfig;

/**
 * Form schema for entity type creation/editing.
 *
 * @deprecated Use ArtifactFormSchema from './artifact' instead.
 * This type is maintained for backward compatibility until Q3 2026.
 *
 * Defines which fields are shown and how they are rendered.
 *
 * Migration: Import { ArtifactFormSchema } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import type { EntityFormSchema } from '@/types/entity';
 *
 * // New
 * import type { ArtifactFormSchema } from '@/types';
 * ```
 */
export type EntityFormSchema = ArtifactFormSchema;

/**
 * Form field configuration for entity type forms.
 *
 * @deprecated Use ArtifactFormField from './artifact' instead.
 * This type is maintained for backward compatibility until Q3 2026.
 *
 * Defines how a single field is rendered in create/edit forms.
 *
 * Migration: Import { ArtifactFormField } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import type { EntityFormField } from '@/types/entity';
 *
 * // New
 * import type { ArtifactFormField } from '@/types';
 * ```
 */
export type EntityFormField = ArtifactFormField;

// ============================================================================
// Helper Function Aliases (deprecated)
// ============================================================================

/**
 * Get configuration for an entity type.
 *
 * @deprecated Use getArtifactTypeConfig from './artifact' instead.
 * This function is maintained for backward compatibility until Q3 2026.
 *
 * Retrieves the artifact type configuration including display labels,
 * icons, colors, and form schema for dynamic rendering.
 *
 * @param type - The entity type to look up
 * @returns ArtifactTypeConfig with display and form information
 * @throws Error if type not found in registry
 *
 * Migration: Import { getArtifactTypeConfig } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import { getEntityTypeConfig } from '@/types/entity';
 * const skillConfig = getEntityTypeConfig('skill');
 *
 * // New
 * import { getArtifactTypeConfig } from '@/types';
 * const skillConfig = getArtifactTypeConfig('skill');
 *
 * console.log(skillConfig.label); // "Skill"
 * console.log(skillConfig.icon);  // "Sparkles"
 * ```
 */
export const getEntityTypeConfig: (type: ArtifactType) => ArtifactTypeConfig =
  getArtifactTypeConfig;

/**
 * Get all supported entity types.
 *
 * @deprecated Use getAllArtifactTypes from './artifact' instead.
 * This function is maintained for backward compatibility until Q3 2026.
 *
 * Returns an array of all artifact type identifiers supported by SkillMeat.
 *
 * @returns Array of all entity type identifiers
 *
 * Migration: Import { getAllArtifactTypes } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import { getAllEntityTypes } from '@/types/entity';
 * const types = getAllEntityTypes();
 *
 * // New
 * import { getAllArtifactTypes } from '@/types';
 * const types = getAllArtifactTypes();
 *
 * // ['skill', 'command', 'agent', 'mcp', 'hook']
 * ```
 */
export const getAllEntityTypes: () => ArtifactType[] = getAllArtifactTypes;

/**
 * Format an entity ID from type and name.
 *
 * @deprecated Use formatArtifactId from './artifact' instead.
 * This function is maintained for backward compatibility until Q3 2026.
 *
 * Combines an artifact type and name into the standard "type:name" format
 * used for artifact identification.
 *
 * @param type - The entity type
 * @param name - The entity name
 * @returns Formatted ID in "type:name" format
 *
 * Migration: Import { formatArtifactId } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import { formatEntityId } from '@/types/entity';
 * const id = formatEntityId('skill', 'canvas-design');
 *
 * // New
 * import { formatArtifactId } from '@/types';
 * const id = formatArtifactId('skill', 'canvas-design');
 *
 * // "skill:canvas-design"
 * ```
 */
export const formatEntityId: (type: ArtifactType, name: string) => string = formatArtifactId;

/**
 * Parse an entity ID into type and name components.
 *
 * @deprecated Use parseArtifactId from './artifact' instead.
 * This function is maintained for backward compatibility until Q3 2026.
 *
 * Splits an artifact ID in "type:name" format into its constituent type
 * and name components for processing.
 *
 * @param id - The entity ID to parse (format: "type:name")
 * @returns Object with type and name properties, or null if invalid format
 *
 * Migration: Import { parseArtifactId } from '@/types' instead.
 * See: .claude/guides/entity-to-artifact-migration.md
 *
 * @example
 * ```ts
 * // Old (deprecated)
 * import { parseEntityId } from '@/types/entity';
 * const parsed = parseEntityId('skill:canvas-design');
 *
 * // New
 * import { parseArtifactId } from '@/types';
 * const parsed = parseArtifactId('skill:canvas-design');
 *
 * if (parsed) {
 *   console.log(parsed.type); // "skill"
 *   console.log(parsed.name); // "canvas-design"
 * }
 * ```
 */
export const parseEntityId: (id: string) => { type: ArtifactType; name: string } | null =
  parseArtifactId;
