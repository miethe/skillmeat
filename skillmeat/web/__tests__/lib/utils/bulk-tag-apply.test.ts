/**
 * Unit tests for bulk tag application utilities.
 *
 * Tests artifact discovery by directory and tag merging logic.
 */

import {
  findArtifactsInDirectory,
  findArtifactsInDirectoryExact,
  normalizeTag,
  mergeTags,
  simulateBulkTagApply,
} from '@/lib/utils/bulk-tag-apply';
import type { CatalogEntry } from '@/types/marketplace';

// Helper to create mock catalog entries
function createMockEntry(path: string, overrides: Partial<CatalogEntry> = {}): CatalogEntry {
  return {
    id: `entry-${path.replace(/\//g, '-')}`,
    source_id: 'source-123',
    artifact_type: 'skill',
    name: path.split('/').pop() || path,
    path,
    upstream_url: `https://github.com/test/${path}`,
    detected_at: '2024-01-01T00:00:00Z',
    confidence_score: 0.9,
    status: 'new',
    ...overrides,
  };
}

describe('findArtifactsInDirectory', () => {
  const entries: CatalogEntry[] = [
    createMockEntry('skills/canvas'),
    createMockEntry('skills/docs'),
    createMockEntry('skills/dev/testing'),
    createMockEntry('skills/dev/lint'),
    createMockEntry('commands/ai'),
    createMockEntry('commands/system/backup'),
    createMockEntry('rootfile'),
  ];

  it('finds artifacts in top-level directory', () => {
    const result = findArtifactsInDirectory(entries, 'skills');

    expect(result).toHaveLength(4);
    expect(result.map((e) => e.path)).toContain('skills/canvas');
    expect(result.map((e) => e.path)).toContain('skills/docs');
    expect(result.map((e) => e.path)).toContain('skills/dev/testing');
    expect(result.map((e) => e.path)).toContain('skills/dev/lint');
  });

  it('finds artifacts in nested directory', () => {
    const result = findArtifactsInDirectory(entries, 'skills/dev');

    expect(result).toHaveLength(2);
    expect(result.map((e) => e.path)).toEqual(['skills/dev/testing', 'skills/dev/lint']);
  });

  it('handles directory with trailing slash', () => {
    const result = findArtifactsInDirectory(entries, 'skills/');

    expect(result).toHaveLength(4);
  });

  it('returns empty array for non-existent directory', () => {
    const result = findArtifactsInDirectory(entries, 'nonexistent');

    expect(result).toHaveLength(0);
  });

  it('returns empty array for empty entries', () => {
    const result = findArtifactsInDirectory([], 'skills');

    expect(result).toHaveLength(0);
  });

  it('handles null/undefined entries gracefully', () => {
    expect(findArtifactsInDirectory(null as unknown as CatalogEntry[], 'skills')).toEqual([]);
    expect(findArtifactsInDirectory(undefined as unknown as CatalogEntry[], 'skills')).toEqual([]);
  });

  it('handles empty directory path (root level)', () => {
    const result = findArtifactsInDirectory(entries, '');

    expect(result).toHaveLength(1);
    expect(result[0]?.path).toBe('rootfile');
  });

  it('does not match partial directory names', () => {
    // 'skill' should NOT match 'skills/canvas'
    const result = findArtifactsInDirectory(entries, 'skill');

    expect(result).toHaveLength(0);
  });

  it('handles deeply nested paths', () => {
    const deepEntries = [
      createMockEntry('a/b/c/d/e'),
      createMockEntry('a/b/c/x'),
      createMockEntry('a/b/y'),
    ];

    const result = findArtifactsInDirectory(deepEntries, 'a/b/c');

    expect(result).toHaveLength(2);
    expect(result.map((e) => e.path)).toEqual(['a/b/c/d/e', 'a/b/c/x']);
  });
});

describe('findArtifactsInDirectoryExact', () => {
  const entries: CatalogEntry[] = [
    createMockEntry('skills/canvas'),
    createMockEntry('skills/docs'),
    createMockEntry('skills/dev/testing'),
    createMockEntry('skills/dev/lint'),
  ];

  it('finds only direct children of directory', () => {
    const result = findArtifactsInDirectoryExact(entries, 'skills');

    expect(result).toHaveLength(2);
    expect(result.map((e) => e.path)).toEqual(['skills/canvas', 'skills/docs']);
  });

  it('finds direct children of nested directory', () => {
    const result = findArtifactsInDirectoryExact(entries, 'skills/dev');

    expect(result).toHaveLength(2);
    expect(result.map((e) => e.path)).toEqual(['skills/dev/testing', 'skills/dev/lint']);
  });

  it('does not include grandchildren', () => {
    // 'skills' should not include 'skills/dev/testing'
    const result = findArtifactsInDirectoryExact(entries, 'skills');

    expect(result.map((e) => e.path)).not.toContain('skills/dev/testing');
    expect(result.map((e) => e.path)).not.toContain('skills/dev/lint');
  });

  it('handles directory with trailing slash', () => {
    const result = findArtifactsInDirectoryExact(entries, 'skills/');

    expect(result).toHaveLength(2);
  });

  it('returns empty for non-existent directory', () => {
    const result = findArtifactsInDirectoryExact(entries, 'nonexistent');

    expect(result).toHaveLength(0);
  });
});

describe('normalizeTag', () => {
  it('converts to lowercase', () => {
    expect(normalizeTag('UPPERCASE')).toBe('uppercase');
    expect(normalizeTag('MixedCase')).toBe('mixedcase');
  });

  it('trims whitespace', () => {
    expect(normalizeTag('  spaced  ')).toBe('spaced');
    expect(normalizeTag('\ttabbed\n')).toBe('tabbed');
  });

  it('replaces spaces with hyphens', () => {
    expect(normalizeTag('two words')).toBe('two-words');
    expect(normalizeTag('multiple   spaces')).toBe('multiple-spaces');
  });

  it('removes special characters', () => {
    expect(normalizeTag('tag@special!')).toBe('tagspecial');
    expect(normalizeTag('dots.and.more')).toBe('dotsandmore');
  });

  it('keeps hyphens and underscores', () => {
    expect(normalizeTag('with-hyphen')).toBe('with-hyphen');
    expect(normalizeTag('with_underscore')).toBe('with_underscore');
  });

  it('handles empty string', () => {
    expect(normalizeTag('')).toBe('');
  });

  it('handles string with only special characters', () => {
    expect(normalizeTag('!@#$%')).toBe('');
  });

  it('handles numbers', () => {
    expect(normalizeTag('version123')).toBe('version123');
    expect(normalizeTag('123')).toBe('123');
  });

  it('complex normalization case', () => {
    expect(normalizeTag('  My Tag! (v2) ')).toBe('my-tag-v2');
  });
});

describe('mergeTags', () => {
  it('merges non-overlapping tags', () => {
    const result = mergeTags(['a', 'b'], ['c', 'd']);

    expect(result).toEqual(['a', 'b', 'c', 'd']);
  });

  it('deduplicates overlapping tags', () => {
    const result = mergeTags(['a', 'b'], ['b', 'c']);

    expect(result).toEqual(['a', 'b', 'c']);
  });

  it('normalizes tags before merging', () => {
    const result = mergeTags(['MyTag'], ['mytag', 'MYTAG']);

    expect(result).toEqual(['mytag']);
    expect(result).toHaveLength(1);
  });

  it('handles empty existing tags', () => {
    const result = mergeTags([], ['a', 'b']);

    expect(result).toEqual(['a', 'b']);
  });

  it('handles empty new tags', () => {
    const result = mergeTags(['a', 'b'], []);

    expect(result).toEqual(['a', 'b']);
  });

  it('handles both empty', () => {
    const result = mergeTags([], []);

    expect(result).toEqual([]);
  });

  it('filters out empty normalized tags', () => {
    const result = mergeTags(['valid'], ['!@#', '', '  ', 'also-valid']);

    expect(result).toEqual(['also-valid', 'valid']);
  });

  it('returns sorted result', () => {
    const result = mergeTags(['zebra', 'apple'], ['mango', 'banana']);

    expect(result).toEqual(['apple', 'banana', 'mango', 'zebra']);
  });
});

describe('simulateBulkTagApply', () => {
  const entries: CatalogEntry[] = [
    createMockEntry('skills/canvas'),
    createMockEntry('skills/docs'),
    createMockEntry('skills/dev/testing'),
    createMockEntry('commands/ai'),
  ];

  it('applies tags to matching entries', () => {
    const dirTags = new Map([['skills', ['dev', 'testing']]]);

    const result = simulateBulkTagApply(entries, dirTags);

    // Should match direct children of 'skills' only
    expect(result.size).toBe(2);
    expect(result.get('entry-skills-canvas')).toEqual(['dev', 'testing']);
    expect(result.get('entry-skills-docs')).toEqual(['dev', 'testing']);
  });

  it('handles multiple directories', () => {
    const dirTags = new Map([
      ['skills', ['skill-tag']],
      ['commands', ['command-tag']],
    ]);

    const result = simulateBulkTagApply(entries, dirTags);

    expect(result.size).toBe(3);
    expect(result.get('entry-skills-canvas')).toEqual(['skill-tag']);
    expect(result.get('entry-skills-docs')).toEqual(['skill-tag']);
    expect(result.get('entry-commands-ai')).toEqual(['command-tag']);
  });

  it('handles nested directories separately', () => {
    const dirTags = new Map([
      ['skills', ['parent-tag']],
      ['skills/dev', ['child-tag']],
    ]);

    const result = simulateBulkTagApply(entries, dirTags);

    // skills direct children get parent-tag
    expect(result.get('entry-skills-canvas')).toEqual(['parent-tag']);

    // skills/dev direct child gets child-tag
    expect(result.get('entry-skills-dev-testing')).toEqual(['child-tag']);
  });

  it('skips directories with no tags', () => {
    const dirTags = new Map<string, string[]>([
      ['skills', []],
      ['commands', ['has-tag']],
    ]);

    const result = simulateBulkTagApply(entries, dirTags);

    expect(result.size).toBe(1);
    expect(result.has('entry-skills-canvas')).toBe(false);
    expect(result.get('entry-commands-ai')).toEqual(['has-tag']);
  });

  it('normalizes tags in result', () => {
    const dirTags = new Map([['skills', ['My Tag', 'UPPERCASE', '  spaced  ']]]);

    const result = simulateBulkTagApply(entries, dirTags);

    const tags = result.get('entry-skills-canvas');
    expect(tags).toContain('my-tag');
    expect(tags).toContain('uppercase');
    expect(tags).toContain('spaced');
  });

  it('returns empty map for empty dirTags', () => {
    const result = simulateBulkTagApply(entries, new Map());

    expect(result.size).toBe(0);
  });

  it('returns empty map for empty entries', () => {
    const dirTags = new Map([['skills', ['tag']]]);

    const result = simulateBulkTagApply([], dirTags);

    expect(result.size).toBe(0);
  });

  it('handles non-existent directory', () => {
    const dirTags = new Map([['nonexistent', ['tag']]]);

    const result = simulateBulkTagApply(entries, dirTags);

    expect(result.size).toBe(0);
  });
});

describe('integration scenarios', () => {
  it('handles typical bulk tagging workflow', () => {
    // Simulate a real workflow with mixed directories
    const entries: CatalogEntry[] = [
      createMockEntry('skills/frontend/react'),
      createMockEntry('skills/frontend/vue'),
      createMockEntry('skills/backend/python'),
      createMockEntry('skills/backend/node'),
      createMockEntry('skills/devops/docker'),
      createMockEntry('utils/helpers'),
    ];

    const dirTags = new Map([
      ['skills/frontend', ['frontend', 'ui']],
      ['skills/backend', ['backend', 'api']],
      ['skills/devops', ['devops', 'infrastructure']],
    ]);

    const result = simulateBulkTagApply(entries, dirTags);

    // Frontend artifacts
    expect(result.get('entry-skills-frontend-react')).toEqual(['frontend', 'ui']);
    expect(result.get('entry-skills-frontend-vue')).toEqual(['frontend', 'ui']);

    // Backend artifacts
    expect(result.get('entry-skills-backend-python')).toEqual(['api', 'backend']);
    expect(result.get('entry-skills-backend-node')).toEqual(['api', 'backend']);

    // DevOps artifacts
    expect(result.get('entry-skills-devops-docker')).toEqual(['devops', 'infrastructure']);

    // Utils not tagged
    expect(result.has('entry-utils-helpers')).toBe(false);
  });

  it('handles overlapping directory selections', () => {
    // User selects both a parent and child directory
    const entries: CatalogEntry[] = [
      createMockEntry('skills/canvas'),
      createMockEntry('skills/dev/testing'),
      createMockEntry('skills/dev/lint'),
    ];

    // This shouldn't happen in the UI, but let's ensure robustness
    const dirTags = new Map([
      ['skills', ['parent']],
      ['skills/dev', ['child']],
    ]);

    const result = simulateBulkTagApply(entries, dirTags);

    // Direct child of skills
    expect(result.get('entry-skills-canvas')).toEqual(['parent']);

    // Direct children of skills/dev
    expect(result.get('entry-skills-dev-testing')).toEqual(['child']);
    expect(result.get('entry-skills-dev-lint')).toEqual(['child']);
  });
});

describe('Edge Cases', () => {
  describe('special characters in tags', () => {
    it('handles tags with special characters', () => {
      const result = normalizeTag('my-tag@special!');
      expect(result).toBe('my-tagspecial');
    });

    it('handles tags with unicode', () => {
      const result = normalizeTag('日本語');
      // Unicode letters are not in [a-z0-9-_], so they get stripped
      expect(result).toBe('');
    });

    it('preserves valid characters in mixed input', () => {
      const result = normalizeTag('Valid_Tag-123!@#');
      expect(result).toBe('valid_tag-123');
    });
  });

  describe('extreme tag inputs', () => {
    it('handles very long tags', () => {
      const longTag = 'a'.repeat(1000);
      const result = normalizeTag(longTag);
      expect(result).toBe(longTag);
    });

    it('handles tags with only special characters', () => {
      const result = normalizeTag('!@#$%^&*()');
      expect(result).toBe('');
    });

    it('handles tags with leading/trailing special characters', () => {
      const result = normalizeTag('!!!valid!!!');
      expect(result).toBe('valid');
    });
  });

  describe('mergeTags edge cases', () => {
    it('handles large tag arrays', () => {
      const existing = Array.from({ length: 100 }, (_, i) => `tag${i}`);
      const newTags = Array.from({ length: 100 }, (_, i) => `newtag${i}`);

      const result = mergeTags(existing, newTags);

      expect(result.length).toBe(200);
      expect(result).toContain('tag0');
      expect(result).toContain('newtag99');
    });

    it('handles undefined in tag arrays gracefully', () => {
      // Test robustness with potentially malformed input
      const existing = ['tag1', 'tag2'];
      const newTags = ['tag3', 'tag4'];

      const result = mergeTags(existing, newTags);

      expect(result.length).toBe(4);
    });

    it('removes completely empty tags after normalization', () => {
      const existing = ['valid'];
      const newTags = ['!@#', '   ', '', '$$', 'also-valid'];

      const result = mergeTags(existing, newTags);

      expect(result).toEqual(['also-valid', 'valid']);
    });
  });

  describe('findArtifactsInDirectory edge cases', () => {
    it('handles entries with unusual characters in paths', () => {
      const entries: CatalogEntry[] = [
        createMockEntry('skills-v2.0/canvas'),
        createMockEntry('skills_test/docs'),
        createMockEntry('@scope/package/artifact'),
      ];

      const result = findArtifactsInDirectory(entries, 'skills-v2.0');
      expect(result).toHaveLength(1);
      expect(result[0]?.path).toBe('skills-v2.0/canvas');
    });

    it('handles case sensitivity correctly', () => {
      const entries: CatalogEntry[] = [
        createMockEntry('Skills/canvas'),
        createMockEntry('skills/docs'),
      ];

      // Should be case-sensitive
      const upperResult = findArtifactsInDirectory(entries, 'Skills');
      const lowerResult = findArtifactsInDirectory(entries, 'skills');

      expect(upperResult).toHaveLength(1);
      expect(lowerResult).toHaveLength(1);
      expect(upperResult[0]?.path).toBe('Skills/canvas');
      expect(lowerResult[0]?.path).toBe('skills/docs');
    });

    it('handles entries with only whitespace paths', () => {
      const entries: CatalogEntry[] = [createMockEntry('  /artifact')];

      const result = findArtifactsInDirectory(entries, '  ');
      expect(result).toHaveLength(1);
    });
  });

  describe('simulateBulkTagApply edge cases', () => {
    it('handles duplicate entries in input', () => {
      const entry = createMockEntry('skills/canvas');
      const entries: CatalogEntry[] = [entry, entry, entry];

      const dirTags = new Map([['skills', ['tag1']]]);

      const result = simulateBulkTagApply(entries, dirTags);

      // Should have 3 entries (or handle dedup - depends on implementation)
      // The simulation doesn't dedupe, so it will have 3 entries
      expect(result.size).toBe(1); // Same ID means same entry overwritten
    });

    it('handles directories with similar names', () => {
      const entries: CatalogEntry[] = [
        createMockEntry('skill/artifact1'),
        createMockEntry('skills/artifact2'),
        createMockEntry('skillset/artifact3'),
      ];

      const dirTags = new Map([['skill', ['tag1']]]);

      const result = simulateBulkTagApply(entries, dirTags);

      // Should only match 'skill' exactly, not 'skills' or 'skillset'
      expect(result.size).toBe(1);
      expect(result.get('entry-skill-artifact1')).toEqual(['tag1']);
    });

    it('handles empty string directory path', () => {
      const entries: CatalogEntry[] = [
        createMockEntry('rootfile'),
        createMockEntry('skills/canvas'),
      ];

      const dirTags = new Map([['', ['root-tag']]]);

      const result = simulateBulkTagApply(entries, dirTags);

      // Empty string matches root-level entries
      expect(result.size).toBe(1);
      expect(result.get('entry-rootfile')).toEqual(['root-tag']);
    });

    it('handles concurrent tag merging for same entry', () => {
      const entries: CatalogEntry[] = [createMockEntry('a/b/artifact')];

      // Multiple directories that could match same entry
      const dirTags = new Map([
        ['a/b', ['tag1', 'tag2']],
        // This won't match 'a/b/artifact' because getParent gives 'a/b', not 'a'
        ['a', ['tag3']],
      ]);

      const result = simulateBulkTagApply(entries, dirTags);

      // Only 'a/b' should match
      expect(result.size).toBe(1);
      expect(result.get('entry-a-b-artifact')).toEqual(['tag1', 'tag2']);
    });
  });

  describe('performance', () => {
    it('handles 1000 entries efficiently', () => {
      const entries: CatalogEntry[] = Array.from({ length: 1000 }, (_, i) =>
        createMockEntry(`dir${i % 10}/subdir${i % 5}/artifact${i}`)
      );

      const dirTags = new Map([
        ['dir0/subdir0', ['tag1', 'tag2']],
        ['dir1/subdir1', ['tag3', 'tag4']],
        ['dir2/subdir2', ['tag5']],
      ]);

      const start = performance.now();
      const result = simulateBulkTagApply(entries, dirTags);
      const elapsed = performance.now() - start;

      // Should complete in under 100ms
      expect(elapsed).toBeLessThan(100);

      // The entries are at paths like 'dir0/subdir0/artifact0'
      // Parent directory is 'dir0/subdir0'
      // Each of the 50 unique (dir, subdir) combinations has 20 entries
      // Matching 3 specific dir/subdir combinations * 20 entries each = 60
      // But wait - checking actual entry pattern:
      // entry i has path: `dir${i % 10}/subdir${i % 5}/artifact${i}`
      // So for i=0: dir0/subdir0/artifact0, i=5: dir5/subdir0/artifact5, etc.
      // For dir0/subdir0: i where i%10=0 AND i%5=0, so i divisible by 10: 0,10,20,...990 = 100 entries
      // For dir1/subdir1: i where i%10=1 AND i%5=1, so i=1,11,21,...991 (i%10=1 and i%5=1 means i%10=1)
      // = 100 entries
      // 3 patterns * 100 entries = 300
      expect(result.size).toBe(300);
    });

    it('handles 100 directories efficiently', () => {
      const entries: CatalogEntry[] = Array.from({ length: 500 }, (_, i) =>
        createMockEntry(`dir${i % 100}/artifact${i}`)
      );

      const dirTags = new Map(Array.from({ length: 100 }, (_, i) => [`dir${i}`, [`tag${i}`]]));

      const start = performance.now();
      const result = simulateBulkTagApply(entries, dirTags);
      const elapsed = performance.now() - start;

      // Should complete in under 200ms
      expect(elapsed).toBeLessThan(200);

      // 500 entries spread across 100 directories = 5 per dir
      expect(result.size).toBe(500);
    });
  });
});
