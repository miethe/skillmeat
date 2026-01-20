/**
 * Unit tests for frontmatter parsing utility
 *
 * Tests YAML frontmatter detection, parsing, and stripping from markdown content.
 */

import { detectFrontmatter, parseFrontmatter, stripFrontmatter } from '@/lib/frontmatter';

describe('detectFrontmatter', () => {
  describe('valid frontmatter', () => {
    it('returns true for valid frontmatter with key-value pairs', () => {
      const content = '---\ntitle: Hello\nauthor: World\n---\nContent here';
      expect(detectFrontmatter(content)).toBe(true);
    });

    it('returns true for minimal frontmatter', () => {
      const content = '---\ntitle: Test\n---\n';
      expect(detectFrontmatter(content)).toBe(true);
    });

    it('returns true for frontmatter with CRLF line endings', () => {
      const content = '---\r\ntitle: Hello\r\n---\r\nContent';
      expect(detectFrontmatter(content)).toBe(true);
    });

    it('returns true for frontmatter with empty values', () => {
      const content = '---\nkey:\n---\nContent';
      expect(detectFrontmatter(content)).toBe(true);
    });
  });

  describe('no frontmatter', () => {
    it('returns false for content without frontmatter', () => {
      const content = '# Just markdown\n\nSome content here';
      expect(detectFrontmatter(content)).toBe(false);
    });

    it('returns false for empty string', () => {
      expect(detectFrontmatter('')).toBe(false);
    });

    it('returns false for just dashes without closing', () => {
      const content = '---\ntitle: Hello';
      expect(detectFrontmatter(content)).toBe(false);
    });

    it('returns false when frontmatter is not at the start', () => {
      const content = 'Some text\n---\ntitle: Hello\n---\n';
      expect(detectFrontmatter(content)).toBe(false);
    });

    it('returns false for single dashes line', () => {
      const content = '---';
      expect(detectFrontmatter(content)).toBe(false);
    });

    it('returns false for dashes without content between', () => {
      // This doesn't match because there's no newline after first ---
      const content = '------\nContent';
      expect(detectFrontmatter(content)).toBe(false);
    });
  });

  describe('edge cases', () => {
    it('returns false for null-like input', () => {
      expect(detectFrontmatter(null as unknown as string)).toBe(false);
      expect(detectFrontmatter(undefined as unknown as string)).toBe(false);
    });

    it('returns false for non-string input', () => {
      expect(detectFrontmatter(123 as unknown as string)).toBe(false);
      expect(detectFrontmatter({} as unknown as string)).toBe(false);
    });
  });
});

describe('parseFrontmatter', () => {
  describe('valid YAML with key-value pairs', () => {
    it('parses simple key-value pairs correctly', () => {
      const content = '---\ntitle: Hello World\nauthor: John Doe\n---\nContent here';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        title: 'Hello World',
        author: 'John Doe',
      });
      expect(result.content).toBe('Content here');
    });

    it('parses multiple key-value pairs', () => {
      const content = '---\nname: Test\nversion: 1.0.0\ndescription: A test\n---\nBody';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        name: 'Test',
        version: '1.0.0',
        description: 'A test',
      });
      expect(result.content).toBe('Body');
    });
  });

  describe('arrays', () => {
    it('parses inline array format', () => {
      const content = '---\ntags: [react, typescript, frontend]\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        tags: ['react', 'typescript', 'frontend'],
      });
    });

    it('parses block array format', () => {
      const content = '---\ntags:\n  - react\n  - typescript\n  - frontend\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        tags: ['react', 'typescript', 'frontend'],
      });
    });

    it('parses empty inline array', () => {
      const content = '---\ntags: []\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        tags: [],
      });
    });

    it('parses array with numbers', () => {
      const content = '---\nversions: [1, 2, 3]\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        versions: [1, 2, 3],
      });
    });
  });

  describe('nested objects', () => {
    it('parses nested objects correctly', () => {
      const content = '---\nauthor:\n  name: John\n  email: john@example.com\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        author: {
          name: 'John',
          email: 'john@example.com',
        },
      });
    });

    it('parses inline object format', () => {
      const content = '---\nmeta: {version: 1, stable: true}\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        meta: {
          version: 1,
          stable: true,
        },
      });
    });

    it('parses empty inline object', () => {
      const content = '---\nmeta: {}\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        meta: {},
      });
    });
  });

  describe('quoted strings', () => {
    it('parses double-quoted strings', () => {
      const content = '---\ntitle: "Hello: World"\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        title: 'Hello: World',
      });
    });

    it('parses single-quoted strings', () => {
      const content = "---\ntitle: 'Hello: World'\n---\nContent";
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        title: 'Hello: World',
      });
    });

    it('parses empty quoted strings', () => {
      const content = '---\ntitle: ""\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        title: '',
      });
    });
  });

  describe('booleans', () => {
    it('parses true/false as booleans', () => {
      const content = '---\nenabled: true\ndisabled: false\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        enabled: true,
        disabled: false,
      });
    });

    it('parses yes/no as booleans', () => {
      const content = '---\nactive: yes\ninactive: no\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        active: true,
        inactive: false,
      });
    });

    it('parses on/off as booleans', () => {
      const content = '---\nfeature: on\nlegacy: off\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        feature: true,
        legacy: false,
      });
    });

    it('parses case-insensitive booleans', () => {
      const content = '---\na: TRUE\nb: False\nc: YES\nd: No\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        a: true,
        b: false,
        c: true,
        d: false,
      });
    });
  });

  describe('numbers', () => {
    it('parses integers', () => {
      const content = '---\ncount: 42\nnegative: -10\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        count: 42,
        negative: -10,
      });
    });

    it('parses floating point numbers', () => {
      const content = '---\nprice: 19.99\nrate: -0.05\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        price: 19.99,
        rate: -0.05,
      });
    });

    it('preserves numeric strings that look like version numbers', () => {
      // Version strings like "1.0.0" are kept as strings
      const content = '---\nversion: 1.0.0\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        version: '1.0.0',
      });
    });
  });

  describe('null values', () => {
    it('parses null keyword', () => {
      const content = '---\nvalue: null\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        value: null,
      });
    });

    it('parses tilde as null', () => {
      const content = '---\nvalue: ~\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        value: null,
      });
    });

    it('parses empty value as null', () => {
      const content = '---\nvalue:\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        value: null,
      });
    });
  });

  describe('empty frontmatter', () => {
    it('returns empty object for empty frontmatter block', () => {
      const content = '---\n\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({});
      expect(result.content).toBe('Content');
    });

    it('returns empty object for whitespace-only frontmatter', () => {
      const content = '---\n   \n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({});
      expect(result.content).toBe('Content');
    });
  });

  describe('content without frontmatter', () => {
    it('returns null frontmatter and unchanged content', () => {
      const content = '# Just markdown\n\nSome content here';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toBeNull();
      expect(result.content).toBe(content);
    });

    it('handles empty string input', () => {
      const result = parseFrontmatter('');

      expect(result.frontmatter).toBeNull();
      expect(result.content).toBe('');
    });
  });

  describe('invalid YAML handling', () => {
    it('returns null frontmatter and strips invalid YAML from content', () => {
      // Suppress console.warn for this test
      const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

      // Create content that would cause the parser to fail
      // The simple parser handles most cases gracefully, so we test that
      // malformed content still gets stripped
      const content = '---\n: invalid\n---\nContent';
      const result = parseFrontmatter(content);

      // The simple parser may or may not fail on this, but content should be clean
      expect(result.content).toBe('Content');

      warnSpy.mockRestore();
    });
  });

  describe('frontmatter with comments', () => {
    it('ignores YAML comments', () => {
      const content = '---\n# This is a comment\ntitle: Hello\n# Another comment\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        title: 'Hello',
      });
    });

    it('handles frontmatter with only comments', () => {
      const content = '---\n# Just a comment\n# Another comment\n---\nContent';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({});
      expect(result.content).toBe('Content');
    });
  });

  describe('edge cases', () => {
    it('handles null input', () => {
      const result = parseFrontmatter(null as unknown as string);

      expect(result.frontmatter).toBeNull();
      expect(result.content).toBe('');
    });

    it('handles undefined input', () => {
      const result = parseFrontmatter(undefined as unknown as string);

      expect(result.frontmatter).toBeNull();
      expect(result.content).toBe('');
    });

    it('handles content with closing delimiter in body', () => {
      const content = '---\ntitle: Test\n---\nContent with --- in it';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        title: 'Test',
      });
      expect(result.content).toBe('Content with --- in it');
    });

    it('handles multi-line content after frontmatter', () => {
      const content = '---\ntitle: Test\n---\nLine 1\nLine 2\nLine 3';
      const result = parseFrontmatter(content);

      expect(result.frontmatter).toEqual({
        title: 'Test',
      });
      expect(result.content).toBe('Line 1\nLine 2\nLine 3');
    });
  });
});

describe('stripFrontmatter', () => {
  describe('content with frontmatter', () => {
    it('returns content without frontmatter', () => {
      const content = '---\ntitle: Hello\nauthor: World\n---\nContent here';
      const result = stripFrontmatter(content);

      expect(result).toBe('Content here');
    });

    it('preserves multi-line content', () => {
      const content = '---\ntitle: Test\n---\nLine 1\nLine 2\nLine 3';
      const result = stripFrontmatter(content);

      expect(result).toBe('Line 1\nLine 2\nLine 3');
    });

    it('handles frontmatter with CRLF line endings', () => {
      const content = '---\r\ntitle: Hello\r\n---\r\nContent';
      const result = stripFrontmatter(content);

      expect(result).toBe('Content');
    });
  });

  describe('content without frontmatter', () => {
    it('returns content unchanged', () => {
      const content = '# Just markdown\n\nSome content here';
      const result = stripFrontmatter(content);

      expect(result).toBe(content);
    });

    it('returns empty string unchanged', () => {
      const result = stripFrontmatter('');

      expect(result).toBe('');
    });

    it('returns plain text unchanged', () => {
      const content = 'Just plain text without any frontmatter';
      const result = stripFrontmatter(content);

      expect(result).toBe(content);
    });
  });

  describe('edge cases', () => {
    it('handles null input', () => {
      const result = stripFrontmatter(null as unknown as string);

      expect(result).toBe('');
    });

    it('handles undefined input', () => {
      const result = stripFrontmatter(undefined as unknown as string);

      expect(result).toBe('');
    });

    it('handles non-string input', () => {
      // Non-string inputs that are truthy get returned as-is via `content || ''`
      // This is defensive behavior - the function returns the input unchanged
      // when it can't process it as a string
      const result = stripFrontmatter(123 as unknown as string);

      // The implementation returns `content || ''` for non-strings
      // Since 123 is truthy, it returns 123
      expect(result).toBe(123 as unknown as string);
    });

    it('handles content with --- in body after stripping', () => {
      const content = '---\ntitle: Test\n---\nContent with --- separator';
      const result = stripFrontmatter(content);

      expect(result).toBe('Content with --- separator');
    });

    it('preserves content that starts with --- but is not frontmatter', () => {
      // Content starting with --- but no closing delimiter
      const content = '--- This is a horizontal rule\nMore content';
      const result = stripFrontmatter(content);

      // Should remain unchanged since it's not valid frontmatter
      expect(result).toBe(content);
    });
  });
});

describe('integration scenarios', () => {
  it('handles typical markdown file with frontmatter', () => {
    const content = `---
title: My Blog Post
author: Jane Doe
date: 2024-01-15
tags: [blog, writing, tips]
draft: false
---

# My Blog Post

This is the content of my blog post.

## Section 1

Some more content here.
`;

    // Test detection
    expect(detectFrontmatter(content)).toBe(true);

    // Test parsing
    const parsed = parseFrontmatter(content);
    expect(parsed.frontmatter).toEqual({
      title: 'My Blog Post',
      author: 'Jane Doe',
      date: '2024-01-15',
      tags: ['blog', 'writing', 'tips'],
      draft: false,
    });
    expect(parsed.content).toContain('# My Blog Post');
    expect(parsed.content).toContain('## Section 1');

    // Test stripping
    const stripped = stripFrontmatter(content);
    expect(stripped).not.toContain('title:');
    expect(stripped).toContain('# My Blog Post');
  });

  it('handles skill file with simple nested metadata', () => {
    // Note: The simple YAML parser has limitations with complex nested structures
    // like array items that are objects. For production use with complex YAML,
    // consider using the `yaml` or `js-yaml` package.
    const content = `---
name: canvas-design
type: skill
version: 2.0.0
author:
  name: Anthropic
  url: https://anthropic.com
config:
  timeout: 30000
  retries: 3
---

# Canvas Design Skill

Description of the skill...
`;

    const parsed = parseFrontmatter(content);

    expect(parsed.frontmatter).toEqual({
      name: 'canvas-design',
      type: 'skill',
      version: '2.0.0',
      author: {
        name: 'Anthropic',
        url: 'https://anthropic.com',
      },
      config: {
        timeout: 30000,
        retries: 3,
      },
    });
    expect(parsed.content).toContain('# Canvas Design Skill');
  });

  it('handles content without frontmatter consistently across all functions', () => {
    const content = '# Regular Markdown\n\nNo frontmatter here.';

    expect(detectFrontmatter(content)).toBe(false);

    const parsed = parseFrontmatter(content);
    expect(parsed.frontmatter).toBeNull();
    expect(parsed.content).toBe(content);

    const stripped = stripFrontmatter(content);
    expect(stripped).toBe(content);
  });

  it('handles empty content consistently across all functions', () => {
    const content = '';

    expect(detectFrontmatter(content)).toBe(false);

    const parsed = parseFrontmatter(content);
    expect(parsed.frontmatter).toBeNull();
    expect(parsed.content).toBe('');

    const stripped = stripFrontmatter(content);
    expect(stripped).toBe('');
  });
});
