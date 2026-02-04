import { hasValidUpstreamSource } from '@/lib/sync-utils';
import type { Artifact } from '@/types/artifact';

/**
 * Unit tests for hasValidUpstreamSource()
 *
 * Tests the sync eligibility check that determines whether an artifact
 * has a valid upstream source for sync operations. Returns true only when:
 * 1. origin is 'github'
 * 2. upstream tracking is enabled
 * 3. source string looks like a valid remote path (contains '/', not local)
 */

/** Helper to create a minimal Artifact fixture with only the fields under test. */
function makeArtifact(
  overrides: Partial<Pick<Artifact, 'origin' | 'upstream' | 'source'>>
): Artifact {
  return {
    origin: 'github',
    upstream: { enabled: true, updateAvailable: false },
    source: 'anthropics/skills/canvas-design',
    ...overrides,
  } as unknown as Artifact;
}

describe('hasValidUpstreamSource', () => {
  describe('valid upstream scenarios', () => {
    it('returns true for github origin + tracking enabled + valid source', () => {
      const artifact = makeArtifact({
        origin: 'github',
        upstream: { enabled: true, updateAvailable: false },
        source: 'anthropics/skills/canvas-design',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(true);
    });

    it('returns true for source with nested path segments', () => {
      const artifact = makeArtifact({
        source: 'user/repo/nested/path/skill',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(true);
    });

    it('returns true for source with version suffix', () => {
      const artifact = makeArtifact({
        source: 'user/repo/path@v1.2.0',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(true);
    });
  });

  describe('origin filtering', () => {
    it('returns false for marketplace origin (even with valid source)', () => {
      const artifact = makeArtifact({
        origin: 'marketplace',
        upstream: { enabled: true, updateAvailable: false },
        source: 'anthropics/skills/canvas-design',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false for local origin', () => {
      const artifact = makeArtifact({
        origin: 'local',
        upstream: { enabled: true, updateAvailable: false },
        source: 'anthropics/skills/canvas-design',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false for undefined origin', () => {
      const artifact = makeArtifact({
        origin: undefined,
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false for null-like origin', () => {
      const artifact = {
        origin: null,
        upstream: { enabled: true, updateAvailable: false },
        source: 'anthropics/skills/canvas-design',
      } as unknown as Artifact;

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });
  });

  describe('upstream tracking', () => {
    it('returns false when upstream.enabled is false', () => {
      const artifact = makeArtifact({
        upstream: { enabled: false, updateAvailable: false },
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false when upstream object is undefined', () => {
      const artifact = makeArtifact({
        upstream: undefined,
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false when upstream object is null', () => {
      const artifact = {
        origin: 'github',
        upstream: null,
        source: 'anthropics/skills/canvas-design',
      } as unknown as Artifact;

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });
  });

  describe('source string validation', () => {
    it('returns false for empty source string', () => {
      const artifact = makeArtifact({
        source: '',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false for undefined source', () => {
      const artifact = makeArtifact({
        source: undefined,
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false when source is "local"', () => {
      const artifact = makeArtifact({
        source: 'local',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false when source starts with "local:"', () => {
      const artifact = makeArtifact({
        source: 'local:/path/to/artifact',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false when source is "unknown"', () => {
      const artifact = makeArtifact({
        source: 'unknown',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false when source has no slash (not a remote path)', () => {
      const artifact = makeArtifact({
        source: 'just-a-name',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });

    it('returns false when source starts with "local" prefix even with slash', () => {
      const artifact = makeArtifact({
        source: 'localhost/some/path',
      });

      expect(hasValidUpstreamSource(artifact)).toBe(false);
    });
  });
});
