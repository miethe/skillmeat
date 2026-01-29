/**
 * Type Backward Compatibility Tests
 *
 * These tests verify that the Entity→Artifact type consolidation maintains
 * backward compatibility. If this file compiles without errors, the types
 * are compatible.
 *
 * @version 1.0.0
 * @see .claude/plans/entity-artifact-consolidation-v1/prd.md
 */

// Test imports from artifact.ts (new canonical location)
import type {
  Artifact,
  ArtifactType,
  ArtifactScope,
  SyncStatus,
  ArtifactStatus,  // deprecated alias for SyncStatus
  ArtifactFilters,
  CollectionRef,
} from '../artifact';

// Test imports from entity.ts (backward compatibility)
import type {
  Entity,
  EntityType,
  EntityStatus,
  EntityScope,
  EntityTypeConfig,
  EntityFormSchema,
  EntityFormField,
} from '../entity';

import {
  ENTITY_TYPES,
  getEntityTypeConfig,
  getAllEntityTypes,
  formatEntityId,
  parseEntityId,
  STATUS_DESCRIPTIONS,
} from '../entity';

// =============================================================================
// Type Alias Compatibility Tests
// =============================================================================

/**
 * Verify Entity is assignable to Artifact and vice versa.
 * This ensures the type alias works correctly.
 */
function testEntityArtifactInterchangeability() {
  // Create a mock artifact
  const artifact: Artifact = {
    id: 'skill:test-skill',
    name: 'test-skill',
    type: 'skill',
    scope: 'user',
    syncStatus: 'synced',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  // Entity should accept Artifact
  const entityFromArtifact: Entity = artifact;

  // Artifact should accept Entity
  const entity: Entity = {
    id: 'command:test-command',
    name: 'test-command',
    type: 'command',
    scope: 'local',
    syncStatus: 'modified',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const artifactFromEntity: Artifact = entity;

  // Suppress unused variable warnings
  void entityFromArtifact;
  void artifactFromEntity;
}

/**
 * Verify EntityType is assignable to ArtifactType and vice versa.
 */
function testTypeAliasInterchangeability() {
  const artifactType: ArtifactType = 'skill';
  const entityType: EntityType = artifactType;

  const entityType2: EntityType = 'command';
  const artifactType2: ArtifactType = entityType2;

  // All artifact types should be valid entity types
  const allTypes: EntityType[] = ['skill', 'command', 'agent', 'mcp', 'hook'];

  void entityType;
  void artifactType2;
  void allTypes;
}

/**
 * Verify EntityStatus is assignable to SyncStatus and vice versa.
 */
function testStatusAliasInterchangeability() {
  const syncStatus: SyncStatus = 'synced';
  const entityStatus: EntityStatus = syncStatus;

  const entityStatus2: EntityStatus = 'modified';
  const syncStatus2: SyncStatus = entityStatus2;

  // All sync statuses should be valid entity statuses
  const allStatuses: EntityStatus[] = ['synced', 'modified', 'outdated', 'conflict', 'error'];

  void entityStatus;
  void syncStatus2;
  void allStatuses;
}

/**
 * Verify EntityScope is assignable to ArtifactScope and vice versa.
 */
function testScopeAliasInterchangeability() {
  const artifactScope: ArtifactScope = 'user';
  const entityScope: EntityScope = artifactScope;

  const entityScope2: EntityScope = 'local';
  const artifactScope2: ArtifactScope = entityScope2;

  void entityScope;
  void artifactScope2;
}

/**
 * Verify ArtifactStatus (deprecated) is assignable to SyncStatus.
 */
function testDeprecatedArtifactStatus() {
  const artifactStatus: ArtifactStatus = 'synced';
  const syncStatus: SyncStatus = artifactStatus;

  void syncStatus;
}

// =============================================================================
// Runtime Function Tests
// =============================================================================

describe('Type backward compatibility', () => {
  describe('Type aliases', () => {
    it('Entity and Artifact should be interchangeable', () => {
      // Type-level test: if this compiles, types are compatible
      testEntityArtifactInterchangeability();
      expect(true).toBe(true);
    });

    it('EntityType and ArtifactType should be interchangeable', () => {
      testTypeAliasInterchangeability();
      expect(true).toBe(true);
    });

    it('EntityStatus and SyncStatus should be interchangeable', () => {
      testStatusAliasInterchangeability();
      expect(true).toBe(true);
    });

    it('EntityScope and ArtifactScope should be interchangeable', () => {
      testScopeAliasInterchangeability();
      expect(true).toBe(true);
    });

    it('ArtifactStatus (deprecated) should alias SyncStatus', () => {
      testDeprecatedArtifactStatus();
      expect(true).toBe(true);
    });
  });

  describe('ENTITY_TYPES registry', () => {
    it('should contain all five artifact types', () => {
      const types = getAllEntityTypes();
      expect(types).toHaveLength(5);
      expect(types).toContain('skill');
      expect(types).toContain('command');
      expect(types).toContain('agent');
      expect(types).toContain('mcp');
      expect(types).toContain('hook');
    });

    it('should return valid config for each type', () => {
      const types = getAllEntityTypes();
      for (const type of types) {
        const config = getEntityTypeConfig(type);
        expect(config).toBeDefined();
        expect(config.type).toBe(type);
        expect(config.label).toBeTruthy();
        expect(config.pluralLabel).toBeTruthy();
        expect(config.icon).toBeTruthy();
        expect(config.color).toBeTruthy();
        expect(config.requiredFile).toBeTruthy();
        expect(config.formSchema).toBeDefined();
        expect(config.formSchema.fields).toBeInstanceOf(Array);
      }
    });
  });

  describe('ID formatting functions', () => {
    it('formatEntityId should create type:name format', () => {
      expect(formatEntityId('skill', 'canvas-design')).toBe('skill:canvas-design');
      expect(formatEntityId('command', 'deploy')).toBe('command:deploy');
    });

    it('parseEntityId should extract type and name', () => {
      const parsed = parseEntityId('skill:canvas-design');
      expect(parsed).not.toBeNull();
      expect(parsed?.type).toBe('skill');
      expect(parsed?.name).toBe('canvas-design');
    });

    it('parseEntityId should return null for invalid format', () => {
      expect(parseEntityId('invalid')).toBeNull();
      expect(parseEntityId('too:many:colons')).toBeNull();
      expect(parseEntityId(':no-type')).toBeNull();
      expect(parseEntityId('no-name:')).toBeNull();
      expect(parseEntityId('invalid-type:name')).toBeNull();
    });
  });

  describe('STATUS_DESCRIPTIONS', () => {
    it('should have descriptions for all sync statuses', () => {
      const statuses: SyncStatus[] = ['synced', 'modified', 'outdated', 'conflict', 'error'];
      for (const status of statuses) {
        expect(STATUS_DESCRIPTIONS[status]).toBeTruthy();
        expect(typeof STATUS_DESCRIPTIONS[status]).toBe('string');
      }
    });
  });
});

// =============================================================================
// Type-Only Tests (compile-time verification)
// =============================================================================

/**
 * These types exist only for compile-time verification.
 * They ensure the type system correctly recognizes the aliases.
 */

// Verify EntityTypeConfig works with entity.ts types
type _TypeConfigTest = EntityTypeConfig extends {
  type: EntityType;
  label: string;
  formSchema: EntityFormSchema;
} ? true : never;

// Verify ENTITY_TYPES is correctly typed
type _EntityTypesTest = typeof ENTITY_TYPES extends Record<EntityType, EntityTypeConfig> ? true : never;

// Verify CollectionRef is available (new in unified Artifact)
type _CollectionRefTest = CollectionRef extends { id: string; name: string } ? true : never;

// Verify ArtifactFilters uses SyncStatus
type _FiltersTest = ArtifactFilters extends { status?: SyncStatus | 'all' } ? true : never;
