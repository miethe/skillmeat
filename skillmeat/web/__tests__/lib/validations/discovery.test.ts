/**
 * Unit tests for discovery validation schemas
 */

import {
  validateGitHubSource,
  validateArtifactParameters,
  validateBulkImportRequest,
  githubSourceSchema,
  versionSchema,
  scopeSchema,
  artifactTypeSchema,
} from '@/lib/validations/discovery';

describe('Discovery Validations', () => {
  describe('validateGitHubSource', () => {
    it('validates standard format', () => {
      const result = validateGitHubSource('user/repo/path');
      expect(result.success).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('validates with version', () => {
      const result = validateGitHubSource('user/repo/path@v1.0.0');
      expect(result.success).toBe(true);
    });

    it('validates HTTPS URL', () => {
      const result = validateGitHubSource('https://github.com/user/repo/path');
      expect(result.success).toBe(true);
    });

    it('validates with dashes and underscores', () => {
      const result = validateGitHubSource('my-user/my-repo/my_path');
      expect(result.success).toBe(true);
    });

    it('rejects invalid format', () => {
      const result = validateGitHubSource('invalid!source');
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('rejects empty string', () => {
      const result = validateGitHubSource('');
      expect(result.success).toBe(false);
      expect(result.error).toContain('required');
    });

    it('rejects incomplete path', () => {
      const result = validateGitHubSource('user/repo');
      expect(result.success).toBe(false);
    });
  });

  describe('versionSchema', () => {
    it('accepts "latest"', () => {
      const result = versionSchema.safeParse('latest');
      expect(result.success).toBe(true);
    });

    it('accepts version with @', () => {
      const result = versionSchema.safeParse('@v1.0.0');
      expect(result.success).toBe(true);
    });

    it('accepts semver', () => {
      const result = versionSchema.safeParse('1.0.0');
      expect(result.success).toBe(true);
    });

    it('accepts semver with v prefix', () => {
      const result = versionSchema.safeParse('v1.0.0');
      expect(result.success).toBe(true);
    });

    it('accepts undefined', () => {
      const result = versionSchema.safeParse(undefined);
      expect(result.success).toBe(true);
    });

    it('rejects invalid version', () => {
      const result = versionSchema.safeParse('invalid');
      expect(result.success).toBe(false);
    });
  });

  describe('scopeSchema', () => {
    it('accepts "user"', () => {
      const result = scopeSchema.safeParse('user');
      expect(result.success).toBe(true);
    });

    it('accepts "local"', () => {
      const result = scopeSchema.safeParse('local');
      expect(result.success).toBe(true);
    });

    it('rejects invalid scope', () => {
      const result = scopeSchema.safeParse('global');
      expect(result.success).toBe(false);
    });
  });

  describe('artifactTypeSchema', () => {
    const validTypes = ['skill', 'command', 'agent', 'hook', 'mcp'];

    validTypes.forEach((type) => {
      it(`accepts "${type}"`, () => {
        const result = artifactTypeSchema.safeParse(type);
        expect(result.success).toBe(true);
      });
    });

    it('rejects invalid type', () => {
      const result = artifactTypeSchema.safeParse('invalid');
      expect(result.success).toBe(false);
    });
  });

  describe('validateArtifactParameters', () => {
    it('validates valid parameters', () => {
      const result = validateArtifactParameters({
        source: 'user/repo/skill',
        version: 'latest',
        scope: 'user',
        tags: ['test', 'example'],
        aliases: ['alias1'],
      });

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.errors).toBeUndefined();
    });

    it('validates minimal parameters', () => {
      const result = validateArtifactParameters({
        version: 'latest',
      });

      expect(result.success).toBe(true);
    });

    it('rejects invalid scope', () => {
      const result = validateArtifactParameters({
        scope: 'invalid',
      });

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors?.scope).toBeDefined();
    });

    it('rejects empty tags', () => {
      const result = validateArtifactParameters({
        tags: [''],
      });

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
    });
  });

  describe('validateBulkImportRequest', () => {
    it('validates valid request', () => {
      const result = validateBulkImportRequest({
        artifacts: [
          {
            source: 'user/repo/skill',
            artifact_type: 'skill',
          },
        ],
      });

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.errors).toBeUndefined();
    });

    it('validates request with multiple artifacts', () => {
      const result = validateBulkImportRequest({
        artifacts: [
          { source: 'user/repo/skill', artifact_type: 'skill' },
          { source: 'user/repo/command', artifact_type: 'command' },
        ],
        auto_resolve_conflicts: true,
      });

      expect(result.success).toBe(true);
    });

    it('validates request with optional fields', () => {
      const result = validateBulkImportRequest({
        artifacts: [
          {
            source: 'user/repo/skill',
            artifact_type: 'skill',
            name: 'my-skill',
            description: 'A test skill',
            tags: ['test'],
            scope: 'user',
          },
        ],
      });

      expect(result.success).toBe(true);
    });

    it('rejects empty artifacts array', () => {
      const result = validateBulkImportRequest({
        artifacts: [],
      });

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors?.artifacts).toContain('At least one artifact');
    });

    it('rejects invalid artifact type', () => {
      const result = validateBulkImportRequest({
        artifacts: [
          {
            source: 'user/repo/skill',
            artifact_type: 'invalid',
          },
        ],
      });

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
    });

    it('rejects invalid source format', () => {
      const result = validateBulkImportRequest({
        artifacts: [
          {
            source: 'invalid',
            artifact_type: 'skill',
          },
        ],
      });

      expect(result.success).toBe(false);
      expect(result.errors).toBeDefined();
    });
  });
});
