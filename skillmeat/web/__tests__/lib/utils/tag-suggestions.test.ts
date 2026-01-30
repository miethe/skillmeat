/**
 * Tests for tag suggestion utilities
 */
import { generateTagSuggestions, isValidTag, normalizeTag } from '@/lib/utils/tag-suggestions';

describe('generateTagSuggestions', () => {
  describe('basic path parsing', () => {
    it('returns empty array for empty path', () => {
      expect(generateTagSuggestions('')).toEqual([]);
    });

    it('returns empty array for null/undefined', () => {
      expect(generateTagSuggestions(null as unknown as string)).toEqual([]);
      expect(generateTagSuggestions(undefined as unknown as string)).toEqual([]);
    });

    it('splits path into segments', () => {
      const result = generateTagSuggestions('skills/canvas-design');
      expect(result).toContain('skills');
      expect(result).toContain('canvas-design');
    });

    it('handles deeply nested paths', () => {
      const result = generateTagSuggestions('packages/ai-tools/prompts/generator');
      expect(result).toContain('ai-tools');
      expect(result).toContain('prompts');
      expect(result).toContain('generator');
    });

    it('removes leading and trailing slashes', () => {
      const result = generateTagSuggestions('/skills/canvas/');
      expect(result).toContain('skills');
      expect(result).toContain('canvas');
    });

    it('handles multiple consecutive slashes', () => {
      const result = generateTagSuggestions('skills//canvas');
      expect(result).toContain('skills');
      expect(result).toContain('canvas');
    });
  });

  describe('excluded words filtering', () => {
    it('filters out common source directories', () => {
      const result = generateTagSuggestions('src/lib/dist/build/my-component');
      expect(result).not.toContain('src');
      expect(result).not.toContain('lib');
      expect(result).not.toContain('dist');
      expect(result).not.toContain('build');
      expect(result).toContain('my-component');
    });

    it('filters out common project structure words', () => {
      const result = generateTagSuggestions('app/components/utils/helpers/my-util');
      expect(result).not.toContain('app');
      expect(result).not.toContain('components');
      expect(result).not.toContain('utils');
      expect(result).not.toContain('helpers');
      expect(result).toContain('my-util');
    });

    it('filters out node_modules and vendor', () => {
      const result = generateTagSuggestions('node_modules/react/vendor/lodash');
      expect(result).not.toContain('node_modules');
      expect(result).not.toContain('vendor');
      expect(result).toContain('react');
      expect(result).toContain('lodash');
    });

    it('filters out version/environment indicators', () => {
      const result = generateTagSuggestions('v1/dev/prod/staging/test/my-feature');
      expect(result).not.toContain('v1');
      expect(result).not.toContain('dev');
      expect(result).not.toContain('prod');
      expect(result).not.toContain('staging');
      expect(result).not.toContain('test');
      expect(result).toContain('my-feature');
    });

    it('filters out documentation directories', () => {
      const result = generateTagSuggestions('docs/examples/samples/demo/my-doc');
      expect(result).not.toContain('docs');
      expect(result).not.toContain('examples');
      expect(result).not.toContain('samples');
      expect(result).not.toContain('demo');
      expect(result).toContain('my-doc');
    });
  });

  describe('normalization', () => {
    it('converts to lowercase', () => {
      const result = generateTagSuggestions('Skills/CANVAS-Design');
      expect(result).toContain('skills');
      expect(result).toContain('canvas-design');
      expect(result).not.toContain('Skills');
      expect(result).not.toContain('CANVAS-Design');
    });

    it('trims whitespace from segments', () => {
      const result = generateTagSuggestions('  skills / canvas  ');
      expect(result).toContain('skills');
      expect(result).toContain('canvas');
    });

    it('filters out segments shorter than 2 characters', () => {
      const result = generateTagSuggestions('a/b/ab/abc/abcd');
      expect(result).not.toContain('a');
      expect(result).not.toContain('b');
      expect(result).toContain('ab');
      expect(result).toContain('abc');
      expect(result).toContain('abcd');
    });

    it('filters out pure numbers', () => {
      const result = generateTagSuggestions('v2/123/456/my-feature');
      expect(result).not.toContain('123');
      expect(result).not.toContain('456');
      expect(result).toContain('my-feature');
    });
  });

  describe('deduplication', () => {
    it('returns unique segments only', () => {
      const result = generateTagSuggestions('skills/canvas/skills/canvas');
      expect(result).toEqual(['skills', 'canvas']);
    });

    it('deduplicates case-insensitively', () => {
      const result = generateTagSuggestions('Skills/skills/SKILLS');
      expect(result).toEqual(['skills']);
    });
  });

  describe('real-world paths', () => {
    it('handles Claude artifact paths', () => {
      const result = generateTagSuggestions('anthropics/skills/canvas-design');
      expect(result).toContain('anthropics');
      expect(result).toContain('skills');
      expect(result).toContain('canvas-design');
    });

    it('handles GitHub repo structure', () => {
      const result = generateTagSuggestions('owner/repo/src/components/Button');
      expect(result).not.toContain('src');
      expect(result).not.toContain('components');
      expect(result).toContain('owner');
      expect(result).toContain('repo');
      expect(result).toContain('button');
    });

    it('handles npm package paths', () => {
      const result = generateTagSuggestions('@org/package-name/lib/index');
      expect(result).not.toContain('lib');
      expect(result).toContain('@org');
      expect(result).toContain('package-name');
      expect(result).toContain('index');
    });
  });
});

describe('isValidTag', () => {
  it('returns false for empty string', () => {
    expect(isValidTag('')).toBe(false);
  });

  it('returns false for null/undefined', () => {
    expect(isValidTag(null as unknown as string)).toBe(false);
    expect(isValidTag(undefined as unknown as string)).toBe(false);
  });

  it('returns false for whitespace only', () => {
    expect(isValidTag('   ')).toBe(false);
    expect(isValidTag('\t\n')).toBe(false);
  });

  it('returns false for single character', () => {
    expect(isValidTag('a')).toBe(false);
    expect(isValidTag('1')).toBe(false);
  });

  it('returns true for valid tags', () => {
    expect(isValidTag('ab')).toBe(true);
    expect(isValidTag('python')).toBe(true);
    expect(isValidTag('canvas-design')).toBe(true);
    expect(isValidTag('my_tag_123')).toBe(true);
  });

  it('returns true after trimming valid tags', () => {
    expect(isValidTag('  python  ')).toBe(true);
    expect(isValidTag('\tcanvas\n')).toBe(true);
  });
});

describe('normalizeTag', () => {
  it('converts to lowercase', () => {
    expect(normalizeTag('PYTHON')).toBe('python');
    expect(normalizeTag('CamelCase')).toBe('camelcase');
  });

  it('trims whitespace', () => {
    expect(normalizeTag('  python  ')).toBe('python');
    expect(normalizeTag('\tcanvas\n')).toBe('canvas');
  });

  it('preserves hyphens and underscores', () => {
    expect(normalizeTag('canvas-design')).toBe('canvas-design');
    expect(normalizeTag('my_tag')).toBe('my_tag');
  });

  it('preserves numbers', () => {
    expect(normalizeTag('v2-beta')).toBe('v2-beta');
    expect(normalizeTag('python3')).toBe('python3');
  });
});
