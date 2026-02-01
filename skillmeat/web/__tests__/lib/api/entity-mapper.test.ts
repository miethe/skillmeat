/**
 * Unit tests for centralized entity mapper
 *
 * Tests all mapping functions including edge cases, null handling,
 * and context-specific status resolution.
 */

import {
  mapArtifactToEntity,
  mapArtifactsToEntities,
  mapArtifactToEntitySafe,
  mapArtifactsToEntitiesSafe,
  type ApiArtifactResponse,
} from '@/lib/api/entity-mapper';

describe('mapArtifactToEntity', () => {
  // Base minimal artifact for testing
  const minimalArtifact: ApiArtifactResponse = {
    id: 'test-id',
    name: 'test-artifact',
    type: 'skill',
  };

  describe('required field validation', () => {
    it('maps all required fields correctly', () => {
      const result = mapArtifactToEntity(minimalArtifact);

      expect(result.id).toBe('test-id');
      expect(result.name).toBe('test-artifact');
      expect(result.type).toBe('skill');
    });

    it('throws error when id is missing', () => {
      const invalid = { ...minimalArtifact, id: '' };
      expect(() => mapArtifactToEntity(invalid)).toThrow('missing required field "id"');
    });

    it('throws error when name is missing', () => {
      const invalid = { ...minimalArtifact, name: '' };
      expect(() => mapArtifactToEntity(invalid)).toThrow('missing required field "name"');
    });

    it('throws error when type is missing', () => {
      const invalid = { ...minimalArtifact, type: '' };
      expect(() => mapArtifactToEntity(invalid)).toThrow('missing required field "type"');
    });

    it('throws error for unknown artifact type', () => {
      const invalid = { ...minimalArtifact, type: 'invalid-type' };
      expect(() => mapArtifactToEntity(invalid)).toThrow('unknown type "invalid-type"');
    });

    it('accepts all valid artifact types', () => {
      const validTypes = ['skill', 'command', 'agent', 'mcp', 'hook'];

      validTypes.forEach((type) => {
        const artifact = { ...minimalArtifact, type };
        const result = mapArtifactToEntity(artifact);
        expect(result.type).toBe(type);
      });
    });
  });

  describe('null and undefined field handling', () => {
    it('handles null/undefined fields gracefully', () => {
      const artifact: ApiArtifactResponse = {
        id: 'test-id',
        name: 'test-artifact',
        type: 'skill',
        description: undefined,
        author: undefined,
        tags: undefined,
        metadata: undefined,
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.description).toBeUndefined();
      expect(result.author).toBeUndefined();
      expect(result.tags).toBeUndefined();
    });

    it('provides default timestamps when missing', () => {
      const result = mapArtifactToEntity(minimalArtifact);

      expect(result.createdAt).toBeDefined();
      expect(result.updatedAt).toBeDefined();
      expect(new Date(result.createdAt).getTime()).not.toBeNaN();
      expect(new Date(result.updatedAt).getTime()).not.toBeNaN();
    });

    it('defaults scope to "user" for collection context', () => {
      const result = mapArtifactToEntity(minimalArtifact, 'collection');
      expect(result.scope).toBe('user');
    });

    it('defaults scope to "local" for project context', () => {
      const result = mapArtifactToEntity(minimalArtifact, 'project');
      expect(result.scope).toBe('local');
    });

    it('defaults scope to "user" for marketplace context', () => {
      const result = mapArtifactToEntity(minimalArtifact, 'marketplace');
      expect(result.scope).toBe('user');
    });

    it('respects explicit scope when provided', () => {
      const artifact = { ...minimalArtifact, scope: 'local' };
      const result = mapArtifactToEntity(artifact, 'collection');
      expect(result.scope).toBe('local');
    });
  });

  describe('collections array mapping', () => {
    it('maps collections array correctly', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        collections: [
          { id: 'col1', name: 'Collection 1', artifact_count: 5 },
          { id: 'col2', name: 'Collection 2', artifact_count: 10 },
        ],
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.collections).toBeDefined();
      expect(result.collections!).toHaveLength(2);
      expect(result.collections![0]).toEqual({
        id: 'col1',
        name: 'Collection 1',
        artifact_count: 5,
      });
      expect(result.collections![1]).toEqual({
        id: 'col2',
        name: 'Collection 2',
        artifact_count: 10,
      });
    });

    it('handles empty collections array', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        collections: [],
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.collections).toEqual([]);
      expect(Array.isArray(result.collections)).toBe(true);
    });

    it('handles undefined collections field', () => {
      const result = mapArtifactToEntity(minimalArtifact);
      expect(result.collections).toEqual([]);
    });

    it('handles null artifact_count in collections', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        collections: [{ id: 'col1', name: 'Collection 1', artifact_count: undefined }],
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.collections).toBeDefined();
      expect(result.collections).toHaveLength(1);
      expect(result.collections![0]?.artifact_count).toBeUndefined();
    });

    it('extracts primary collection from collections array', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        collections: [{ id: 'col1', name: 'Primary Collection' }],
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.collection).toBe('Primary Collection');
    });

    it('handles string collection field', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        collection: 'My Collection',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.collection).toBe('My Collection');
    });

    it('handles object collection field', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        collection: { id: 'col1', name: 'My Collection' },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.collection).toBe('My Collection');
    });
  });

  describe('sync status resolution', () => {
    it('uses correct status for collection context with synced artifact', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        status: 'synced',
      };

      const result = mapArtifactToEntity(artifact, 'collection');

      expect(result.syncStatus).toBe('synced');
    });

    it('uses correct status for project context with deployment_status', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        deployment_status: 'modified',
      };

      const result = mapArtifactToEntity(artifact, 'project');

      expect(result.syncStatus).toBe('modified');
    });

    it('prioritizes drift_status over other status fields', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        drift_status: 'conflict',
        status: 'synced',
        sync_status: 'outdated',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.syncStatus).toBe('conflict');
    });

    it('detects error status from drift_status', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        drift_status: 'error',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.syncStatus).toBe('error');
    });

    it('detects modified status from has_local_modifications', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        has_local_modifications: true,
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.syncStatus).toBe('modified');
    });

    it('detects outdated status from update_available', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        upstream: {
          tracking_enabled: true,
          update_available: true,
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.syncStatus).toBe('outdated');
    });

    it('detects outdated status from SHA mismatch', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        upstream: {
          tracking_enabled: true,
          update_available: false,
          current_sha: 'abc123',
          upstream_sha: 'def456',
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.syncStatus).toBe('outdated');
    });

    it('uses marketplace context with default synced status', () => {
      const result = mapArtifactToEntity(minimalArtifact, 'marketplace');
      expect(result.syncStatus).toBe('synced');
    });

    it('handles case-insensitive status values', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        status: 'MODIFIED',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.syncStatus).toBe('modified');
    });

    it('detects modified status from nested upstream.drift_status', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        upstream: {
          tracking_enabled: true,
          update_available: false,
          drift_status: 'modified',
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.syncStatus).toBe('modified');
    });

    it('detects outdated status from nested upstream.drift_status', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        upstream: {
          tracking_enabled: true,
          update_available: false,
          drift_status: 'outdated',
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.syncStatus).toBe('outdated');
    });

    it('detects outdated from deployment_status in project context', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        deployment_status: 'outdated',
      };

      const result = mapArtifactToEntity(artifact, 'project');

      expect(result.syncStatus).toBe('outdated');
    });
  });

  describe('metadata flattening', () => {
    it('flattens metadata from nested object', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        metadata: {
          description: 'Nested description',
          author: 'Nested author',
          license: 'MIT',
          tags: ['tag1', 'tag2'],
          version: '1.0.0',
          dependencies: ['dep1', 'dep2'],
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.description).toBe('Nested description');
      expect(result.author).toBe('Nested author');
      expect(result.license).toBe('MIT');
      expect(result.tags).toEqual(['tag1', 'tag2']);
      expect(result.version).toBe('1.0.0');
      expect(result.dependencies).toEqual(['dep1', 'dep2']);
    });

    it('prefers top-level fields over nested metadata', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        description: 'Top-level description',
        metadata: {
          description: 'Nested description',
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.description).toBe('Top-level description');
    });

    it('merges tags from both top-level and metadata', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        tags: ['top1', 'top2'],
        metadata: {
          tags: ['meta1', 'top2'], // 'top2' is duplicate
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.tags).toContain('top1');
      expect(result.tags).toContain('top2');
      expect(result.tags).toContain('meta1');
      expect(result.tags?.filter((t) => t === 'top2')).toHaveLength(1); // Deduplication
    });

    it('handles empty tags array correctly', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        tags: [],
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.tags).toBeUndefined(); // Empty array should not be included
    });
  });

  describe('version resolution', () => {
    it('prefers resolved_version over version', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        version: '1.0.0',
        resolved_version: '1.1.0',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.version).toBe('1.1.0');
    });

    it('falls back to version when resolved_version is missing', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        version: '1.0.0',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.version).toBe('1.0.0');
    });

    it('falls back to metadata.version when both are missing', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        metadata: {
          version: '2.0.0',
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.version).toBe('2.0.0');
    });
  });

  describe('upstream tracking', () => {
    it('maps upstream tracking info when present', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        upstream: {
          tracking_enabled: true,
          update_available: false,
          upstream_url: 'https://github.com/user/repo',
          upstream_version: '1.2.0',
          current_sha: 'abc123',
          upstream_sha: 'abc123',
          last_checked: '2024-01-01T00:00:00Z',
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.upstream).toBeDefined();
      expect(result.upstream?.enabled).toBe(true);
      expect(result.upstream?.updateAvailable).toBe(false);
      expect(result.upstream?.url).toBe('https://github.com/user/repo');
      expect(result.upstream?.version).toBe('1.2.0');
      expect(result.upstream?.currentSha).toBe('abc123');
      expect(result.upstream?.upstreamSha).toBe('abc123');
      expect(result.upstream?.lastChecked).toBe('2024-01-01T00:00:00Z');
    });

    it('handles missing upstream field', () => {
      const result = mapArtifactToEntity(minimalArtifact);
      expect(result.upstream).toBeUndefined();
    });

    it('handles null upstream field', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        upstream: undefined,
      };

      const result = mapArtifactToEntity(artifact);
      expect(result.upstream).toBeUndefined();
    });

    it('omits optional upstream fields when missing', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        upstream: {
          tracking_enabled: true,
          update_available: false,
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.upstream?.enabled).toBe(true);
      expect(result.upstream?.url).toBeUndefined();
      expect(result.upstream?.version).toBeUndefined();
    });
  });

  describe('usage statistics', () => {
    it('maps usage_stats with snake_case fields', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        usage_stats: {
          total_deployments: 5,
          active_projects: 3,
          usage_count: 10,
          last_used: '2024-01-01T00:00:00Z',
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.usageStats).toBeDefined();
      expect(result.usageStats?.totalDeployments).toBe(5);
      expect(result.usageStats?.activeProjects).toBe(3);
      expect(result.usageStats?.usageCount).toBe(10);
      expect(result.usageStats?.lastUsed).toBe('2024-01-01T00:00:00Z');
    });

    it('maps usageStats with camelCase fields', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        usageStats: {
          totalDeployments: 7,
          activeProjects: 2,
          usageCount: 15,
          lastUsed: '2024-02-01T00:00:00Z',
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.usageStats).toBeDefined();
      expect(result.usageStats?.totalDeployments).toBe(7);
      expect(result.usageStats?.activeProjects).toBe(2);
      expect(result.usageStats?.usageCount).toBe(15);
      expect(result.usageStats?.lastUsed).toBe('2024-02-01T00:00:00Z');
    });

    it('handles missing usage stats', () => {
      const result = mapArtifactToEntity(minimalArtifact);
      expect(result.usageStats).toBeUndefined();
    });
  });

  describe('score mapping', () => {
    it('maps complete score object', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        score: {
          confidence: 0.95,
          trust_score: 0.85,
          quality_score: 0.9,
          match_score: 0.8,
          last_updated: '2024-01-01T00:00:00Z',
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.score).toBeDefined();
      expect(result.score?.confidence).toBe(0.95);
      expect(result.score?.trustScore).toBe(0.85);
      expect(result.score?.qualityScore).toBe(0.9);
      expect(result.score?.matchScore).toBe(0.8);
      expect(result.score?.lastUpdated).toBe('2024-01-01T00:00:00Z');
    });

    it('handles minimal score with only confidence', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        score: {
          confidence: 0.75,
        },
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.score?.confidence).toBe(0.75);
      expect(result.score?.trustScore).toBeUndefined();
    });

    it('handles missing score', () => {
      const result = mapArtifactToEntity(minimalArtifact);
      expect(result.score).toBeUndefined();
    });
  });

  describe('timestamp resolution', () => {
    it('uses provided timestamps when available', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-02T00:00:00Z',
        deployedAt: '2024-01-03T00:00:00Z',
        modifiedAt: '2024-01-04T00:00:00Z',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.createdAt).toBe('2024-01-01T00:00:00Z');
      expect(result.updatedAt).toBe('2024-01-02T00:00:00Z');
      expect(result.deployedAt).toBe('2024-01-03T00:00:00Z');
      expect(result.modifiedAt).toBe('2024-01-04T00:00:00Z');
    });

    it('prefers camelCase over snake_case timestamps', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        createdAt: '2024-01-01T00:00:00Z',
        created_at: '2024-01-02T00:00:00Z',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.createdAt).toBe('2024-01-01T00:00:00Z');
    });

    it('falls back updatedAt to createdAt when both timestamp fields are missing', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        // No timestamp fields provided
      };

      const result = mapArtifactToEntity(artifact);

      // When both are missing, both get current time
      // updatedAt should equal createdAt (both are 'now')
      expect(result.createdAt).toBe(result.updatedAt);
      expect(new Date(result.createdAt).getTime()).not.toBeNaN();
    });
  });

  describe('project path and origin fields', () => {
    it('maps projectPath from camelCase', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        projectPath: '/path/to/project',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.projectPath).toBe('/path/to/project');
    });

    it('maps projectPath from snake_case', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        project_path: '/path/to/project',
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.projectPath).toBe('/path/to/project');
    });

    it('maps source, origin, and aliases', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        source: 'github:user/repo',
        origin: 'github',
        origin_source: 'https://github.com/user/repo',
        aliases: ['alias1', 'alias2'],
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.source).toBe('github:user/repo');
      expect(result.origin).toBe('github');
      expect(result.origin_source).toBe('https://github.com/user/repo');
      expect(result.aliases).toEqual(['alias1', 'alias2']);
    });

    it('omits empty aliases array', () => {
      const artifact: ApiArtifactResponse = {
        ...minimalArtifact,
        aliases: [],
      };

      const result = mapArtifactToEntity(artifact);

      expect(result.aliases).toBeUndefined();
    });
  });
});

describe('mapArtifactsToEntities', () => {
  const artifact1: ApiArtifactResponse = {
    id: 'id1',
    name: 'artifact1',
    type: 'skill',
  };

  const artifact2: ApiArtifactResponse = {
    id: 'id2',
    name: 'artifact2',
    type: 'command',
  };

  it('maps array of artifacts', () => {
    const results = mapArtifactsToEntities([artifact1, artifact2]);

    expect(results).toHaveLength(2);
    expect(results[0]?.id).toBe('id1');
    expect(results[0]?.type).toBe('skill');
    expect(results[1]?.id).toBe('id2');
    expect(results[1]?.type).toBe('command');
  });

  it('handles empty array', () => {
    const results = mapArtifactsToEntities([]);
    expect(results).toEqual([]);
  });

  it('preserves order of artifacts', () => {
    const results = mapArtifactsToEntities([artifact2, artifact1]);

    expect(results[0]?.id).toBe('id2');
    expect(results[1]?.id).toBe('id1');
  });

  it('propagates context to all artifacts', () => {
    const results = mapArtifactsToEntities([artifact1, artifact2], 'project');

    expect(results[0]?.scope).toBe('local');
    expect(results[1]?.scope).toBe('local');
  });

  it('throws error if any artifact is invalid', () => {
    const invalidArtifact = { ...artifact1, id: '' };

    expect(() => mapArtifactsToEntities([artifact1, invalidArtifact])).toThrow();
  });
});

describe('mapArtifactToEntitySafe', () => {
  const validArtifact: ApiArtifactResponse = {
    id: 'test-id',
    name: 'test-artifact',
    type: 'skill',
  };

  it('returns mapped entity for valid artifact', () => {
    const result = mapArtifactToEntitySafe(validArtifact);

    expect(result).not.toBeNull();
    expect(result?.id).toBe('test-id');
  });

  it('returns null for invalid artifact', () => {
    const invalidArtifact = { ...validArtifact, id: '' };
    const result = mapArtifactToEntitySafe(invalidArtifact);

    expect(result).toBeNull();
  });

  it('returns null for missing type', () => {
    const invalidArtifact = { ...validArtifact, type: '' };
    const result = mapArtifactToEntitySafe(invalidArtifact);

    expect(result).toBeNull();
  });

  it('returns null for unknown type', () => {
    const invalidArtifact = { ...validArtifact, type: 'unknown' };
    const result = mapArtifactToEntitySafe(invalidArtifact);

    expect(result).toBeNull();
  });
});

describe('mapArtifactsToEntitiesSafe', () => {
  const validArtifact1: ApiArtifactResponse = {
    id: 'id1',
    name: 'artifact1',
    type: 'skill',
  };

  const validArtifact2: ApiArtifactResponse = {
    id: 'id2',
    name: 'artifact2',
    type: 'command',
  };

  const invalidArtifact: ApiArtifactResponse = {
    id: '',
    name: 'invalid',
    type: 'skill',
  };

  it('maps valid artifacts and filters invalid ones', () => {
    const results = mapArtifactsToEntitiesSafe([
      validArtifact1,
      invalidArtifact,
      validArtifact2,
    ]);

    expect(results).toHaveLength(2);
    expect(results[0]?.id).toBe('id1');
    expect(results[1]?.id).toBe('id2');
  });

  it('returns empty array when all artifacts are invalid', () => {
    const results = mapArtifactsToEntitiesSafe([invalidArtifact, invalidArtifact]);

    expect(results).toEqual([]);
  });

  it('returns all artifacts when all are valid', () => {
    const results = mapArtifactsToEntitiesSafe([validArtifact1, validArtifact2]);

    expect(results).toHaveLength(2);
  });

  it('handles empty array', () => {
    const results = mapArtifactsToEntitiesSafe([]);
    expect(results).toEqual([]);
  });
});
