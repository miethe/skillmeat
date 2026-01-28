/**
 * Unit tests for API Response Mappers
 *
 * Tests the centralized mapping functions that convert API responses
 * to unified Artifact types. Part of Phase 3 Entity-Artifact consolidation.
 *
 * @version 1.0.0
 */

import {
  mapApiResponseToArtifact,
  mapApiResponsesToArtifacts,
  determineSyncStatus,
  validateArtifactMapping,
  createMinimalArtifact,
  type ArtifactResponse,
  type MappingContext,
} from './mappers';
import type { Artifact, SyncStatus } from '@/types/artifact';

// ============================================================================
// Test Fixtures
// ============================================================================

/**
 * Factory function for creating minimal valid API responses.
 * Reduces boilerplate in individual tests.
 */
function createApiResponse(overrides: Partial<ArtifactResponse> = {}): ArtifactResponse {
  return {
    id: 'skill:test-artifact',
    name: 'test-artifact',
    type: 'skill',
    ...overrides,
  };
}

/**
 * Fixed timestamp for deterministic tests.
 */
const FIXED_DATE = '2024-01-15T10:00:00Z';
const LATER_DATE = '2024-01-20T15:30:00Z';

// ============================================================================
// mapApiResponseToArtifact Tests
// ============================================================================

describe('mapApiResponseToArtifact', () => {
  describe('Required fields mapping', () => {
    it('should map id, name, type correctly', () => {
      const response = createApiResponse({
        id: 'skill:canvas-design',
        name: 'canvas-design',
        type: 'skill',
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.id).toBe('skill:canvas-design');
      expect(artifact.name).toBe('canvas-design');
      expect(artifact.type).toBe('skill');
    });

    it('should throw error when id is missing', () => {
      const response = createApiResponse({ id: '' });

      expect(() => mapApiResponseToArtifact(response, 'collection')).toThrow(
        'Artifact mapping error: missing required field "id"'
      );
    });

    it('should throw error when name is missing', () => {
      const response = createApiResponse({ name: '' });

      expect(() => mapApiResponseToArtifact(response, 'collection')).toThrow(
        'Artifact mapping error: missing required field "name"'
      );
    });

    it('should throw error when type is missing', () => {
      const response = createApiResponse({ type: '' });

      expect(() => mapApiResponseToArtifact(response, 'collection')).toThrow(
        'Artifact mapping error: missing required field "type"'
      );
    });

    it('should throw error for unknown artifact type', () => {
      const response = createApiResponse({ type: 'unknown-type' });

      expect(() => mapApiResponseToArtifact(response, 'collection')).toThrow(
        'Artifact mapping error: unknown type "unknown-type"'
      );
    });

    it('should accept all valid artifact types', () => {
      const types = ['skill', 'command', 'agent', 'mcp', 'hook'];

      types.forEach((type) => {
        const response = createApiResponse({ type });
        const artifact = mapApiResponseToArtifact(response, 'collection');
        expect(artifact.type).toBe(type);
      });
    });
  });

  describe('Metadata flattening', () => {
    it('should flatten description from metadata', () => {
      const response = createApiResponse({
        metadata: { description: 'A design skill' },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.description).toBe('A design skill');
    });

    it('should prefer top-level description over nested', () => {
      const response = createApiResponse({
        description: 'Top level description',
        metadata: { description: 'Nested description' },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.description).toBe('Top level description');
    });

    it('should flatten author from metadata', () => {
      const response = createApiResponse({
        metadata: { author: 'test-author' },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.author).toBe('test-author');
    });

    it('should flatten license from metadata', () => {
      const response = createApiResponse({
        metadata: { license: 'MIT' },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.license).toBe('MIT');
    });

    it('should flatten version from metadata', () => {
      const response = createApiResponse({
        metadata: { version: '1.2.3' },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.version).toBe('1.2.3');
    });

    it('should merge and deduplicate tags from both sources', () => {
      const response = createApiResponse({
        tags: ['frontend', 'design'],
        metadata: { tags: ['design', 'ui'] },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.tags).toEqual(['frontend', 'design', 'ui']);
    });

    it('should handle tags from top-level only', () => {
      const response = createApiResponse({
        tags: ['frontend', 'design'],
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.tags).toEqual(['frontend', 'design']);
    });

    it('should handle tags from metadata only', () => {
      const response = createApiResponse({
        metadata: { tags: ['backend', 'api'] },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.tags).toEqual(['backend', 'api']);
    });

    it('should not include tags property when no tags exist', () => {
      const response = createApiResponse({});

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.tags).toBeUndefined();
    });
  });

  describe('Context handling', () => {
    it('should include projectPath only in project context', () => {
      const response = createApiResponse({
        project_path: '/home/user/project',
      });

      const projectArtifact = mapApiResponseToArtifact(response, 'project');
      expect(projectArtifact.projectPath).toBe('/home/user/project');

      const collectionArtifact = mapApiResponseToArtifact(response, 'collection');
      expect(collectionArtifact.projectPath).toBeUndefined();
    });

    it('should default scope to user for collection context', () => {
      const response = createApiResponse({});

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.scope).toBe('user');
    });

    it('should default scope to local for project context', () => {
      const response = createApiResponse({});

      const artifact = mapApiResponseToArtifact(response, 'project');

      expect(artifact.scope).toBe('local');
    });

    it('should respect explicit scope from response', () => {
      const response = createApiResponse({ scope: 'local' });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.scope).toBe('local');
    });
  });

  describe('Upstream tracking', () => {
    it('should map upstream object with all fields', () => {
      const response = createApiResponse({
        upstream: {
          tracking_enabled: true,
          current_sha: 'abc123',
          upstream_sha: 'def456',
          upstream_url: 'https://github.com/user/repo',
          upstream_version: 'v1.0.0',
          update_available: true,
          last_checked: FIXED_DATE,
        },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.upstream).toEqual({
        enabled: true,
        currentSha: 'abc123',
        upstreamSha: 'def456',
        url: 'https://github.com/user/repo',
        version: 'v1.0.0',
        updateAvailable: true,
        lastChecked: FIXED_DATE,
      });
    });

    it('should map upstream object with minimal fields', () => {
      const response = createApiResponse({
        upstream: {
          tracking_enabled: false,
          update_available: false,
        },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.upstream).toEqual({
        enabled: false,
        updateAvailable: false,
      });
    });

    it('should not include upstream when not present', () => {
      const response = createApiResponse({});

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.upstream).toBeUndefined();
    });
  });

  describe('Usage statistics', () => {
    it('should map usage_stats with snake_case fields', () => {
      const response = createApiResponse({
        usage_stats: {
          total_deployments: 10,
          active_projects: 3,
          last_used: FIXED_DATE,
          usage_count: 50,
        },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.usageStats).toEqual({
        totalDeployments: 10,
        activeProjects: 3,
        lastUsed: FIXED_DATE,
        usageCount: 50,
      });
    });

    it('should map usageStats with camelCase fields', () => {
      const response = createApiResponse({
        usageStats: {
          total_deployments: 5,
          active_projects: 2,
          usage_count: 25,
        },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.usageStats).toEqual({
        totalDeployments: 5,
        activeProjects: 2,
        usageCount: 25,
      });
    });

    it('should prefer usage_stats over usageStats when both present', () => {
      const response = createApiResponse({
        usage_stats: {
          total_deployments: 10,
          active_projects: 3,
          usage_count: 50,
        },
        usageStats: {
          total_deployments: 5,
          active_projects: 2,
          usage_count: 25,
        },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.usageStats?.totalDeployments).toBe(10);
    });

    it('should not include usageStats when not present', () => {
      const response = createApiResponse({});

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.usageStats).toBeUndefined();
    });
  });

  describe('Score mapping', () => {
    it('should map score with all fields', () => {
      const response = createApiResponse({
        score: {
          confidence: 0.95,
          trust_score: 0.9,
          quality_score: 0.85,
          match_score: 0.8,
          last_updated: FIXED_DATE,
        },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.score).toEqual({
        confidence: 0.95,
        trustScore: 0.9,
        qualityScore: 0.85,
        matchScore: 0.8,
        lastUpdated: FIXED_DATE,
      });
    });

    it('should map score with minimal fields', () => {
      const response = createApiResponse({
        score: {
          confidence: 0.7,
        },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.score).toEqual({
        confidence: 0.7,
      });
    });
  });

  describe('Collections mapping', () => {
    it('should map collection string', () => {
      const response = createApiResponse({
        collection: 'default',
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.collection).toBe('default');
    });

    it('should map collection object', () => {
      const response = createApiResponse({
        collection: { id: 'col-123', name: 'my-collection' },
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.collection).toBe('my-collection');
    });

    it('should map collections array', () => {
      const response = createApiResponse({
        collections: [
          { id: 'col-1', name: 'collection-1', artifact_count: 5 },
          { id: 'col-2', name: 'collection-2', artifact_count: 10 },
        ],
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.collections).toEqual([
        { id: 'col-1', name: 'collection-1', artifact_count: 5 },
        { id: 'col-2', name: 'collection-2', artifact_count: 10 },
      ]);
    });

    it('should not include collections when array is empty', () => {
      const response = createApiResponse({
        collections: [],
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.collections).toBeUndefined();
    });
  });

  describe('Timestamp handling', () => {
    it('should resolve createdAt from multiple possible fields', () => {
      // Test createdAt field
      let response = createApiResponse({ createdAt: FIXED_DATE });
      let artifact = mapApiResponseToArtifact(response, 'collection');
      expect(artifact.createdAt).toBe(FIXED_DATE);

      // Test created_at field
      response = createApiResponse({ created_at: FIXED_DATE });
      artifact = mapApiResponseToArtifact(response, 'collection');
      expect(artifact.createdAt).toBe(FIXED_DATE);

      // Test added field
      response = createApiResponse({ added: FIXED_DATE });
      artifact = mapApiResponseToArtifact(response, 'collection');
      expect(artifact.createdAt).toBe(FIXED_DATE);
    });

    it('should resolve updatedAt from multiple possible fields', () => {
      // Test updatedAt field
      let response = createApiResponse({ updatedAt: LATER_DATE, createdAt: FIXED_DATE });
      let artifact = mapApiResponseToArtifact(response, 'collection');
      expect(artifact.updatedAt).toBe(LATER_DATE);

      // Test updated_at field
      response = createApiResponse({ updated_at: LATER_DATE, createdAt: FIXED_DATE });
      artifact = mapApiResponseToArtifact(response, 'collection');
      expect(artifact.updatedAt).toBe(LATER_DATE);

      // Test updated field
      response = createApiResponse({ updated: LATER_DATE, createdAt: FIXED_DATE });
      artifact = mapApiResponseToArtifact(response, 'collection');
      expect(artifact.updatedAt).toBe(LATER_DATE);
    });

    it('should default updatedAt to createdAt if not present', () => {
      const response = createApiResponse({ createdAt: FIXED_DATE });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.updatedAt).toBe(FIXED_DATE);
    });

    it('should generate default timestamp when none provided', () => {
      const response = createApiResponse({});
      const beforeTest = new Date().toISOString();

      const artifact = mapApiResponseToArtifact(response, 'collection');

      const afterTest = new Date().toISOString();

      // Verify timestamps are within test window
      expect(artifact.createdAt >= beforeTest).toBe(true);
      expect(artifact.createdAt <= afterTest).toBe(true);
    });

    it('should map deployedAt from multiple possible fields', () => {
      let response = createApiResponse({ deployedAt: FIXED_DATE });
      let artifact = mapApiResponseToArtifact(response, 'project');
      expect(artifact.deployedAt).toBe(FIXED_DATE);

      response = createApiResponse({ deployed_at: FIXED_DATE });
      artifact = mapApiResponseToArtifact(response, 'project');
      expect(artifact.deployedAt).toBe(FIXED_DATE);
    });

    it('should map modifiedAt from multiple possible fields', () => {
      let response = createApiResponse({ modifiedAt: LATER_DATE });
      let artifact = mapApiResponseToArtifact(response, 'project');
      expect(artifact.modifiedAt).toBe(LATER_DATE);

      response = createApiResponse({ modified_at: LATER_DATE });
      artifact = mapApiResponseToArtifact(response, 'project');
      expect(artifact.modifiedAt).toBe(LATER_DATE);
    });
  });

  describe('Source and origin mapping', () => {
    it('should map source field', () => {
      const response = createApiResponse({
        source: 'anthropics/skills/canvas-design',
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.source).toBe('anthropics/skills/canvas-design');
    });

    it('should map origin field', () => {
      const response = createApiResponse({
        origin: 'github',
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.origin).toBe('github');
    });

    it('should map origin_source field', () => {
      const response = createApiResponse({
        origin_source: 'github',
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.origin_source).toBe('github');
    });

    it('should map aliases array', () => {
      const response = createApiResponse({
        aliases: ['design', 'canvas'],
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.aliases).toEqual(['design', 'canvas']);
    });

    it('should not include aliases when array is empty', () => {
      const response = createApiResponse({
        aliases: [],
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.aliases).toBeUndefined();
    });

    it('should map dependencies array', () => {
      const response = createApiResponse({
        dependencies: ['skill:base', 'command:helper'],
      });

      const artifact = mapApiResponseToArtifact(response, 'collection');

      expect(artifact.dependencies).toEqual(['skill:base', 'command:helper']);
    });
  });
});

// ============================================================================
// determineSyncStatus Tests
// ============================================================================

describe('determineSyncStatus', () => {
  describe('Error priority (highest)', () => {
    it('should return error when syncStatus is error', () => {
      const response = createApiResponse({ syncStatus: 'error' });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('error');
    });

    it('should return error when sync_status is error', () => {
      const response = createApiResponse({ sync_status: 'error' });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('error');
    });

    it('should return error when error field is present', () => {
      const response = createApiResponse({ error: 'Some error message' });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('error');
    });

    it('should return error when both syncStatus and error are present', () => {
      const response = createApiResponse({
        syncStatus: 'synced',
        error: 'Some error',
      });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('error');
    });
  });

  describe('Conflict detection', () => {
    it('should return conflict when syncStatus is conflict', () => {
      const response = createApiResponse({ syncStatus: 'conflict' });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('conflict');
    });

    it('should return conflict when conflictState.hasConflict is true', () => {
      const response = createApiResponse({
        conflictState: {
          hasConflict: true,
          conflictType: 'merge',
          message: 'Merge conflict',
        },
      });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('conflict');
    });

    it('should not return conflict when conflictState.hasConflict is false', () => {
      const response = createApiResponse({
        conflictState: { hasConflict: false },
      });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('synced');
    });
  });

  describe('Modified detection (project context only)', () => {
    it('should return modified when syncStatus is modified in project context', () => {
      const response = createApiResponse({ syncStatus: 'modified' });

      const status = determineSyncStatus(response, 'project');

      expect(status).toBe('modified');
    });

    it('should return modified when modifiedAt > deployedAt in project context', () => {
      const response = createApiResponse({
        deployedAt: FIXED_DATE,
        modifiedAt: LATER_DATE,
      });

      const status = determineSyncStatus(response, 'project');

      expect(status).toBe('modified');
    });

    it('should return modified when modified_at > deployed_at in project context', () => {
      const response = createApiResponse({
        deployed_at: FIXED_DATE,
        modified_at: LATER_DATE,
      });

      const status = determineSyncStatus(response, 'project');

      expect(status).toBe('modified');
    });

    it('should not detect modified in collection context', () => {
      const response = createApiResponse({
        deployedAt: FIXED_DATE,
        modifiedAt: LATER_DATE,
      });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('synced');
    });

    it('should return synced when modifiedAt <= deployedAt in project context', () => {
      const response = createApiResponse({
        deployedAt: LATER_DATE,
        modifiedAt: FIXED_DATE,
      });

      const status = determineSyncStatus(response, 'project');

      expect(status).toBe('synced');
    });
  });

  describe('Outdated detection', () => {
    it('should return outdated when upstream.update_available is true', () => {
      const response = createApiResponse({
        upstream: {
          tracking_enabled: true,
          update_available: true,
        },
      });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('outdated');
    });

    it('should return outdated when SHA mismatch exists', () => {
      const response = createApiResponse({
        upstream: {
          tracking_enabled: true,
          current_sha: 'abc123',
          upstream_sha: 'def456',
          update_available: false,
        },
      });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('outdated');
    });

    it('should return synced when SHAs match', () => {
      const response = createApiResponse({
        upstream: {
          tracking_enabled: true,
          current_sha: 'abc123',
          upstream_sha: 'abc123',
          update_available: false,
        },
      });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('synced');
    });
  });

  describe('Synced default case', () => {
    it('should return synced when no special conditions met', () => {
      const response = createApiResponse({});

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('synced');
    });

    it('should return synced when syncStatus is synced', () => {
      const response = createApiResponse({ syncStatus: 'synced' });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('synced');
    });

    it('should return synced with upstream but no updates', () => {
      const response = createApiResponse({
        upstream: {
          tracking_enabled: true,
          update_available: false,
        },
      });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('synced');
    });
  });

  describe('Priority order verification', () => {
    it('should prioritize error over conflict', () => {
      const response = createApiResponse({
        syncStatus: 'error',
        conflictState: { hasConflict: true },
      });

      const status = determineSyncStatus(response, 'collection');

      expect(status).toBe('error');
    });

    it('should prioritize conflict over modified', () => {
      const response = createApiResponse({
        syncStatus: 'conflict',
        deployedAt: FIXED_DATE,
        modifiedAt: LATER_DATE,
      });

      const status = determineSyncStatus(response, 'project');

      expect(status).toBe('conflict');
    });

    it('should prioritize modified over outdated in project context', () => {
      const response = createApiResponse({
        deployedAt: FIXED_DATE,
        modifiedAt: LATER_DATE,
        upstream: {
          tracking_enabled: true,
          update_available: true,
        },
      });

      const status = determineSyncStatus(response, 'project');

      expect(status).toBe('modified');
    });
  });
});

// ============================================================================
// mapApiResponsesToArtifacts Tests
// ============================================================================

describe('mapApiResponsesToArtifacts', () => {
  it('should convert multiple responses to artifacts', () => {
    const responses: ArtifactResponse[] = [
      createApiResponse({ id: 'skill:one', name: 'one', type: 'skill' }),
      createApiResponse({ id: 'command:two', name: 'two', type: 'command' }),
      createApiResponse({ id: 'agent:three', name: 'three', type: 'agent' }),
    ];

    const artifacts = mapApiResponsesToArtifacts(responses, 'collection');

    expect(artifacts).toHaveLength(3);
    expect(artifacts[0].id).toBe('skill:one');
    expect(artifacts[1].id).toBe('command:two');
    expect(artifacts[2].id).toBe('agent:three');
  });

  it('should handle empty array', () => {
    const responses: ArtifactResponse[] = [];

    const artifacts = mapApiResponsesToArtifacts(responses, 'collection');

    expect(artifacts).toEqual([]);
  });

  it('should preserve order of responses', () => {
    const responses: ArtifactResponse[] = [
      createApiResponse({ id: 'skill:c', name: 'c' }),
      createApiResponse({ id: 'skill:a', name: 'a' }),
      createApiResponse({ id: 'skill:b', name: 'b' }),
    ];

    const artifacts = mapApiResponsesToArtifacts(responses, 'collection');

    expect(artifacts[0].name).toBe('c');
    expect(artifacts[1].name).toBe('a');
    expect(artifacts[2].name).toBe('b');
  });

  it('should propagate mapping errors', () => {
    const responses: ArtifactResponse[] = [
      createApiResponse({ id: 'skill:valid', name: 'valid' }),
      createApiResponse({ id: '', name: 'invalid' }), // Missing id
    ];

    expect(() => mapApiResponsesToArtifacts(responses, 'collection')).toThrow(
      'Artifact mapping error: missing required field "id"'
    );
  });

  it('should apply context consistently to all responses', () => {
    const responses: ArtifactResponse[] = [
      createApiResponse({ id: 'skill:one', project_path: '/path/one' }),
      createApiResponse({ id: 'skill:two', project_path: '/path/two' }),
    ];

    const projectArtifacts = mapApiResponsesToArtifacts(responses, 'project');
    const collectionArtifacts = mapApiResponsesToArtifacts(responses, 'collection');

    expect(projectArtifacts[0].projectPath).toBe('/path/one');
    expect(projectArtifacts[1].projectPath).toBe('/path/two');
    expect(collectionArtifacts[0].projectPath).toBeUndefined();
    expect(collectionArtifacts[1].projectPath).toBeUndefined();
  });
});

// ============================================================================
// validateArtifactMapping Tests
// ============================================================================

describe('validateArtifactMapping', () => {
  it('should return true for valid artifact with all required fields', () => {
    const artifact = createMinimalArtifact();

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(true);
  });

  it('should return false when id is missing', () => {
    const artifact = createMinimalArtifact({ id: '' });

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return false when id is not a string', () => {
    const artifact = createMinimalArtifact();
    // Force invalid type for testing
    (artifact as unknown as { id: number }).id = 123;

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return false when name is missing', () => {
    const artifact = createMinimalArtifact({ name: '' });

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return false when type is missing', () => {
    const artifact = createMinimalArtifact();
    // Force invalid type for testing
    (artifact as unknown as { type: string }).type = '';

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return false when syncStatus is invalid', () => {
    const artifact = createMinimalArtifact();
    // Force invalid status for testing
    (artifact as unknown as { syncStatus: string }).syncStatus = 'invalid';

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return false when syncStatus is missing', () => {
    const artifact = createMinimalArtifact();
    // Force missing status for testing
    (artifact as unknown as { syncStatus: undefined }).syncStatus = undefined;

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return false when createdAt is missing', () => {
    const artifact = createMinimalArtifact({ createdAt: '' });

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return false when updatedAt is missing', () => {
    const artifact = createMinimalArtifact({ updatedAt: '' });

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return false when createdAt is not ISO 8601 format', () => {
    const artifact = createMinimalArtifact({ createdAt: '2024/01/15' });

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return false when updatedAt is not ISO 8601 format', () => {
    const artifact = createMinimalArtifact({ updatedAt: 'January 15, 2024' });

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(false);
  });

  it('should return true for all valid sync statuses', () => {
    const statuses: SyncStatus[] = ['synced', 'modified', 'outdated', 'conflict', 'error'];

    statuses.forEach((status) => {
      const artifact = createMinimalArtifact({ syncStatus: status });
      expect(validateArtifactMapping(artifact)).toBe(true);
    });
  });

  it('should return true for artifact with optional fields', () => {
    const artifact = createMinimalArtifact({
      description: 'A test artifact',
      tags: ['test', 'unit'],
      author: 'test-author',
      upstream: {
        enabled: true,
        updateAvailable: false,
      },
    });

    const isValid = validateArtifactMapping(artifact);

    expect(isValid).toBe(true);
  });
});

// ============================================================================
// createMinimalArtifact Tests
// ============================================================================

describe('createMinimalArtifact', () => {
  it('should create artifact with default values', () => {
    const artifact = createMinimalArtifact();

    expect(artifact.id).toBe('skill:placeholder');
    expect(artifact.name).toBe('placeholder');
    expect(artifact.type).toBe('skill');
    expect(artifact.scope).toBe('user');
    expect(artifact.syncStatus).toBe('synced');
    expect(artifact.createdAt).toBeDefined();
    expect(artifact.updatedAt).toBeDefined();
  });

  it('should allow overriding all fields', () => {
    const overrides = {
      id: 'command:custom',
      name: 'custom-command',
      type: 'command' as const,
      scope: 'local' as const,
      syncStatus: 'modified' as const,
      description: 'Custom description',
    };

    const artifact = createMinimalArtifact(overrides);

    expect(artifact.id).toBe('command:custom');
    expect(artifact.name).toBe('custom-command');
    expect(artifact.type).toBe('command');
    expect(artifact.scope).toBe('local');
    expect(artifact.syncStatus).toBe('modified');
    expect(artifact.description).toBe('Custom description');
  });

  it('should generate timestamps at call time', () => {
    const before = new Date().toISOString();
    const artifact = createMinimalArtifact();
    const after = new Date().toISOString();

    expect(artifact.createdAt >= before).toBe(true);
    expect(artifact.createdAt <= after).toBe(true);
    expect(artifact.updatedAt >= before).toBe(true);
    expect(artifact.updatedAt <= after).toBe(true);
  });

  it('should allow partial overrides', () => {
    const artifact = createMinimalArtifact({
      name: 'just-name-change',
    });

    expect(artifact.name).toBe('just-name-change');
    expect(artifact.id).toBe('skill:placeholder'); // Default preserved
    expect(artifact.type).toBe('skill'); // Default preserved
  });
});
