/**
 * Unit tests for directory utility functions.
 *
 * Tests directory path extraction from marketplace catalog entries
 * for the bulk tag application feature.
 */

import {
  getParentDirectory,
  extractDirectoryPath,
  extractDirectories,
  extractParentDirectories,
  groupByDirectory,
} from '@/lib/utils/directory-utils';

describe('getParentDirectory', () => {
  it('extracts parent from simple nested path', () => {
    expect(getParentDirectory('skills/canvas-design')).toBe('skills');
  });

  it('extracts parent from deeply nested path', () => {
    expect(getParentDirectory('commands/ai/prompt-generator')).toBe('commands/ai');
  });

  it('returns empty string for root-level artifact', () => {
    expect(getParentDirectory('canvas')).toBe('');
  });

  it('handles empty string input', () => {
    expect(getParentDirectory('')).toBe('');
  });

  it('handles trailing slash', () => {
    expect(getParentDirectory('skills/')).toBe('');
    expect(getParentDirectory('skills/canvas/')).toBe('skills');
  });

  it('handles path with only slashes', () => {
    expect(getParentDirectory('/')).toBe('');
    // Double slash becomes single slash after trailing slash removal,
    // then has no parent (no remaining slashes)
    expect(getParentDirectory('//')).toBe('');
  });

  it('handles path starting with slash', () => {
    expect(getParentDirectory('/skills/canvas')).toBe('/skills');
  });
});

describe('extractDirectoryPath', () => {
  it('returns full path for nested artifact', () => {
    expect(extractDirectoryPath('skills/canvas-design')).toBe('skills/canvas-design');
  });

  it('returns full path for deeply nested artifact', () => {
    expect(extractDirectoryPath('commands/ai/prompt-generator')).toBe(
      'commands/ai/prompt-generator'
    );
  });

  it('returns empty string for root-level artifact', () => {
    expect(extractDirectoryPath('canvas')).toBe('');
  });

  it('handles empty string input', () => {
    expect(extractDirectoryPath('')).toBe('');
  });

  it('handles trailing slash', () => {
    expect(extractDirectoryPath('skills/')).toBe('');
    expect(extractDirectoryPath('skills/canvas/')).toBe('skills/canvas');
  });
});

describe('extractDirectories', () => {
  it('extracts directories from multiple entries', () => {
    const entries = [
      { path: 'skills/canvas-design' },
      { path: 'skills/document-skills' },
      { path: 'commands/ai/prompt-generator' },
    ];

    const result = extractDirectories(entries);

    expect(result).toEqual([
      'commands/ai/prompt-generator',
      'skills/canvas-design',
      'skills/document-skills',
    ]);
  });

  it('returns sorted unique list', () => {
    const entries = [{ path: 'skills/zebra' }, { path: 'skills/alpha' }, { path: 'commands/beta' }];

    const result = extractDirectories(entries);

    expect(result).toEqual(['commands/beta', 'skills/alpha', 'skills/zebra']);
  });

  it('deduplicates entries with same directory', () => {
    const entries = [
      { path: 'skills/canvas' },
      { path: 'skills/canvas' },
      { path: 'skills/canvas' },
    ];

    const result = extractDirectories(entries);

    expect(result).toEqual(['skills/canvas']);
    expect(result.length).toBe(1);
  });

  it('excludes root-level artifacts', () => {
    const entries = [{ path: 'skills/canvas' }, { path: 'rootfile' }, { path: 'commands/test' }];

    const result = extractDirectories(entries);

    expect(result).toEqual(['commands/test', 'skills/canvas']);
    expect(result).not.toContain('');
    expect(result).not.toContain('rootfile');
  });

  it('returns empty array for empty input', () => {
    expect(extractDirectories([])).toEqual([]);
  });

  it('handles null/undefined input gracefully', () => {
    expect(extractDirectories(null as unknown as Array<{ path: string }>)).toEqual([]);
    expect(extractDirectories(undefined as unknown as Array<{ path: string }>)).toEqual([]);
  });

  it('handles entries with trailing slashes', () => {
    const entries = [{ path: 'skills/canvas/' }, { path: 'skills/docs/' }];

    const result = extractDirectories(entries);

    expect(result).toEqual(['skills/canvas', 'skills/docs']);
  });

  it('handles deeply nested paths', () => {
    const entries = [{ path: 'a/b/c/d' }, { path: 'x/y/z' }];

    const result = extractDirectories(entries);

    expect(result).toEqual(['a/b/c/d', 'x/y/z']);
  });

  it('handles all root-level artifacts', () => {
    const entries = [{ path: 'file1' }, { path: 'file2' }, { path: 'file3' }];

    const result = extractDirectories(entries);

    expect(result).toEqual([]);
  });
});

describe('extractParentDirectories', () => {
  it('extracts parent directories from entries', () => {
    const entries = [
      { path: 'skills/canvas-design' },
      { path: 'skills/document-skills' },
      { path: 'commands/ai/prompt-generator' },
    ];

    const result = extractParentDirectories(entries);

    expect(result).toEqual(['commands/ai', 'skills']);
  });

  it('deduplicates parent directories', () => {
    const entries = [{ path: 'skills/canvas' }, { path: 'skills/docs' }, { path: 'skills/test' }];

    const result = extractParentDirectories(entries);

    expect(result).toEqual(['skills']);
    expect(result.length).toBe(1);
  });

  it('returns sorted list', () => {
    const entries = [{ path: 'zebra/artifact' }, { path: 'alpha/artifact' }];

    const result = extractParentDirectories(entries);

    expect(result).toEqual(['alpha', 'zebra']);
  });

  it('returns empty array for empty input', () => {
    expect(extractParentDirectories([])).toEqual([]);
  });

  it('excludes root-level artifacts', () => {
    const entries = [{ path: 'rootfile' }, { path: 'skills/nested' }];

    const result = extractParentDirectories(entries);

    expect(result).toEqual(['skills']);
  });
});

describe('groupByDirectory', () => {
  it('groups entries by parent directory', () => {
    const entries = [
      { path: 'skills/canvas', name: 'Canvas' },
      { path: 'skills/docs', name: 'Docs' },
      { path: 'commands/ai', name: 'AI' },
    ];

    const result = groupByDirectory(entries);

    expect(result.get('skills')).toEqual([
      { path: 'skills/canvas', name: 'Canvas' },
      { path: 'skills/docs', name: 'Docs' },
    ]);
    expect(result.get('commands')).toEqual([{ path: 'commands/ai', name: 'AI' }]);
  });

  it('groups root-level artifacts under empty string key', () => {
    const entries = [
      { path: 'rootfile', name: 'Root' },
      { path: 'skills/nested', name: 'Nested' },
    ];

    const result = groupByDirectory(entries);

    expect(result.get('')).toEqual([{ path: 'rootfile', name: 'Root' }]);
    expect(result.get('skills')).toEqual([{ path: 'skills/nested', name: 'Nested' }]);
  });

  it('preserves entry order within groups', () => {
    const entries = [
      { path: 'skills/first', order: 1 },
      { path: 'skills/second', order: 2 },
      { path: 'skills/third', order: 3 },
    ];

    const result = groupByDirectory(entries);

    expect(result.get('skills')).toEqual([
      { path: 'skills/first', order: 1 },
      { path: 'skills/second', order: 2 },
      { path: 'skills/third', order: 3 },
    ]);
  });

  it('handles empty input', () => {
    const result = groupByDirectory([]);

    expect(result.size).toBe(0);
  });

  it('handles deeply nested paths', () => {
    const entries = [
      { path: 'a/b/c', name: 'Deep' },
      { path: 'a/b/d', name: 'Sibling' },
    ];

    const result = groupByDirectory(entries);

    expect(result.get('a/b')).toEqual([
      { path: 'a/b/c', name: 'Deep' },
      { path: 'a/b/d', name: 'Sibling' },
    ]);
  });
});

describe('Edge Cases', () => {
  describe('special characters in paths', () => {
    it('handles hyphens in directory names', () => {
      expect(getParentDirectory('skills-v2/canvas')).toBe('skills-v2');
      expect(extractDirectoryPath('skills-v2/canvas')).toBe('skills-v2/canvas');
    });

    it('handles underscores in directory names', () => {
      expect(getParentDirectory('skills_test/canvas')).toBe('skills_test');
      expect(extractDirectoryPath('skills_test/canvas')).toBe('skills_test/canvas');
    });

    it('handles numbers in directory names', () => {
      expect(getParentDirectory('v2/skills/canvas')).toBe('v2/skills');
      expect(extractDirectoryPath('2024/january/report')).toBe('2024/january/report');
    });

    it('handles dots in directory names', () => {
      expect(getParentDirectory('skills.v2/canvas')).toBe('skills.v2');
      expect(extractDirectoryPath('com.example/package')).toBe('com.example/package');
    });

    it('handles at-symbol (scoped packages)', () => {
      expect(getParentDirectory('@scope/package/index')).toBe('@scope/package');
      expect(extractDirectoryPath('@anthropic/skills/canvas')).toBe('@anthropic/skills/canvas');
    });
  });

  describe('unicode characters', () => {
    it('handles unicode in path names', () => {
      expect(getParentDirectory('skills/日本語/test')).toBe('skills/日本語');
      expect(extractDirectoryPath('技能/canvas')).toBe('技能/canvas');
    });

    it('handles emojis in path names', () => {
      // While unusual, should handle gracefully
      expect(getParentDirectory('🎨/design/canvas')).toBe('🎨/design');
    });
  });

  describe('very long paths', () => {
    it('handles paths with many segments', () => {
      const longPath = 'a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p/artifact';
      expect(getParentDirectory(longPath)).toBe('a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p');
    });

    it('handles very long directory names', () => {
      const longDirName = 'a'.repeat(100);
      expect(getParentDirectory(`${longDirName}/artifact`)).toBe(longDirName);
    });
  });

  describe('whitespace handling', () => {
    it('preserves whitespace in directory names', () => {
      // Paths with spaces are unusual but should work
      expect(getParentDirectory('my skills/canvas design')).toBe('my skills');
      expect(extractDirectoryPath('my skills/canvas design')).toBe('my skills/canvas design');
    });
  });

  describe('mixed case handling', () => {
    it('preserves case in directory names', () => {
      expect(getParentDirectory('Skills/Canvas')).toBe('Skills');
      expect(extractDirectoryPath('SKILLS/CANVAS')).toBe('SKILLS/CANVAS');
    });

    it('groups by exact case match', () => {
      const entries = [
        { path: 'Skills/canvas', name: 'Canvas1' },
        { path: 'skills/canvas2', name: 'Canvas2' },
      ];

      const result = groupByDirectory(entries);

      // Case-sensitive grouping
      expect(result.get('Skills')).toEqual([{ path: 'Skills/canvas', name: 'Canvas1' }]);
      expect(result.get('skills')).toEqual([{ path: 'skills/canvas2', name: 'Canvas2' }]);
    });
  });

  describe('large dataset performance', () => {
    it('handles 1000+ entries efficiently', () => {
      // Create 1000 entries spread across 50 unique parent directories
      // Use floor(i/20) to create groups of 20 entries per parent dir
      const entries = Array.from({ length: 1000 }, (_, i) => ({
        path: `dir${Math.floor(i / 100)}/subdir${Math.floor((i % 100) / 20)}/artifact${i}`,
      }));

      const start = performance.now();
      const directories = extractDirectories(entries);
      const parentDirs = extractParentDirectories(entries);
      const grouped = groupByDirectory(entries);
      const elapsed = performance.now() - start;

      // Should complete in under 100ms for 1000 entries
      expect(elapsed).toBeLessThan(100);
      // extractDirectories returns full paths like 'dir0/subdir0/artifact0'
      // Each artifact has a unique path, so 1000 unique directories
      expect(directories.length).toBe(1000);
      // extractParentDirectories returns 'dir0/subdir0' etc.
      // 10 dirs (0-9) * 5 subdirs (0-4) = 50 unique parent directories
      expect(parentDirs.length).toBe(50);
      // groupByDirectory groups by parent, so 50 groups
      expect(grouped.size).toBe(50);
    });
  });
});
