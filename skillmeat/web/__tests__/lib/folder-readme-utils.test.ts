import { extractFolderReadme, extractFirstParagraph } from '@/lib/folder-readme-utils';
import { CatalogEntry } from '@/types/marketplace';

// Extended type for test entries with content/metadata fields
type CatalogEntryWithExtras = CatalogEntry & {
  content?: string;
  metadata?: {
    description?: string;
    [key: string]: any;
  };
};

// Helper to create mock catalog entries
function createMockEntry(overrides: Partial<CatalogEntryWithExtras> = {}): CatalogEntry {
  return {
    id: 'test-id',
    source_id: 'source-1',
    artifact_type: 'skill',
    name: 'test-artifact',
    path: 'test/path',
    upstream_url: 'https://github.com/test/repo',
    detected_at: '2024-01-01T00:00:00Z',
    confidence_score: 0.9,
    status: 'new',
    ...overrides,
  } as CatalogEntry;
}

describe('extractFirstParagraph', () => {
  describe('basic functionality', () => {
    it('should extract first paragraph from simple markdown', () => {
      const content = `# Heading

This is the first paragraph with meaningful content.

This is the second paragraph.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph with meaningful content.');
    });

    it('should return null for empty content', () => {
      expect(extractFirstParagraph('')).toBeNull();
      expect(extractFirstParagraph('   ')).toBeNull();
    });

    it('should return null for null/undefined input', () => {
      expect(extractFirstParagraph(null as any)).toBeNull();
      expect(extractFirstParagraph(undefined as any)).toBeNull();
    });

    it('should return null for non-string input', () => {
      expect(extractFirstParagraph(123 as any)).toBeNull();
      expect(extractFirstParagraph({} as any)).toBeNull();
    });
  });

  describe('frontmatter handling', () => {
    it('should strip YAML frontmatter', () => {
      const content = `---
title: My Document
author: Test Author
---

# Heading

This is the first paragraph after frontmatter.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph after frontmatter.');
    });

    it('should handle content without frontmatter', () => {
      const content = `# Heading

This is a paragraph without frontmatter.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is a paragraph without frontmatter.');
    });

    it('should return null if only frontmatter exists', () => {
      const content = `---
title: Only Frontmatter
---`;

      const result = extractFirstParagraph(content);
      expect(result).toBeNull();
    });
  });

  describe('markdown element skipping', () => {
    it('should skip multiple headings', () => {
      const content = `# Main Heading
## Subheading
### Sub-subheading

This is the first paragraph.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph.');
    });

    it('should skip empty lines', () => {
      const content = `# Heading



This is the first paragraph after empty lines.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph after empty lines.');
    });

    it('should skip list items starting with dash', () => {
      const content = `# Features

- Feature 1
- Feature 2
- Feature 3

This is the first paragraph after the list.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph after the list.');
    });

    it('should skip list items starting with asterisk', () => {
      const content = `# Features

* Feature 1
* Feature 2

This is the first paragraph.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph.');
    });

    it('should skip blockquotes', () => {
      const content = `# Quote

> This is a quote
> Continued quote

This is the first paragraph.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph.');
    });

    it('should skip code blocks', () => {
      const content = `# Code

\`\`\`javascript
const x = 42;
\`\`\`

This is the first paragraph.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph.');
    });

    it('should skip tables', () => {
      const content = `# Table

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |

This is the first paragraph.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph.');
    });
  });

  describe('multi-line paragraph handling', () => {
    it('should join multi-line paragraphs', () => {
      const content = `# Heading

This is a paragraph
that spans multiple
lines in the markdown.

Second paragraph.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is a paragraph that spans multiple lines in the markdown.');
    });

    it('should stop at empty line between paragraphs', () => {
      const content = `This is the first paragraph
with multiple lines.

This is the second paragraph.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This is the first paragraph with multiple lines.');
    });
  });

  describe('length constraints', () => {
    it('should return null for paragraphs shorter than 20 characters', () => {
      const content = `# Heading

Short text.

Another paragraph.`;

      const result = extractFirstParagraph(content);
      expect(result).toBeNull();
    });

    it('should accept paragraphs exactly 20 characters', () => {
      const content = `# Heading

Exactly twenty chars`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('Exactly twenty chars');
    });

    it('should truncate paragraphs longer than 300 characters', () => {
      const longText = 'a'.repeat(350);
      const content = `# Heading

${longText}`;

      const result = extractFirstParagraph(content);
      expect(result).toHaveLength(300);
      expect(result).toMatch(/\.\.\.$/);
      expect(result).toBe('a'.repeat(297) + '...');
    });

    it('should not truncate paragraphs exactly 300 characters', () => {
      const exactText = 'a'.repeat(300);
      const content = `# Heading

${exactText}`;

      const result = extractFirstParagraph(content);
      expect(result).toBe(exactText);
      expect(result).toHaveLength(300);
    });

    it('should not truncate paragraphs under 300 characters', () => {
      const text = 'This is a paragraph with exactly one hundred characters to test the length constraint properly yes.';
      const content = `# Heading

${text}`;

      const result = extractFirstParagraph(content);
      expect(result).toBe(text);
    });
  });

  describe('edge cases', () => {
    it('should return null for document with only headings', () => {
      const content = `# Main Heading
## Subheading
### Sub-subheading`;

      const result = extractFirstParagraph(content);
      expect(result).toBeNull();
    });

    it('should return null for document with only lists', () => {
      const content = `- Item 1
- Item 2
- Item 3`;

      const result = extractFirstParagraph(content);
      expect(result).toBeNull();
    });

    it('should handle paragraph starting immediately after frontmatter', () => {
      const content = `---
title: Test
---
This paragraph starts right after frontmatter.`;

      const result = extractFirstParagraph(content);
      expect(result).toBe('This paragraph starts right after frontmatter.');
    });
  });
});

describe('extractFolderReadme', () => {
  describe('basic functionality', () => {
    it('should find and extract README content', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/dev-tools/README.md',
          name: 'README.md',
          content: '# Dev Tools\n\nThis is a collection of development tools for testing.',
        }),
        createMockEntry({
          path: 'plugins/dev-tools/formatter',
          name: 'formatter',
        }),
      ];

      const result = extractFolderReadme('plugins/dev-tools', entries);
      expect(result).toBe('This is a collection of development tools for testing.');
    });

    it('should handle case-insensitive README filenames', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/readme.md',
          name: 'readme.md',
          content: '# Plugins\n\nThis is the plugins folder description.',
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBe('This is the plugins folder description.');
    });

    it('should return null when no README exists', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/dev-tools/formatter',
          name: 'formatter',
        }),
      ];

      const result = extractFolderReadme('plugins/dev-tools', entries);
      expect(result).toBeNull();
    });
  });

  describe('input validation', () => {
    it('should return null for empty folder path', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({ path: 'README.md' }),
      ];

      expect(extractFolderReadme('', entries)).toBeNull();
      expect(extractFolderReadme('   ', entries)).toBeNull();
    });

    it('should return null for invalid folder path', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({ path: 'plugins/README.md' }),
      ];

      expect(extractFolderReadme('/', entries)).toBeNull();
    });

    it('should return null for empty entries array', () => {
      expect(extractFolderReadme('plugins', [])).toBeNull();
    });

    it('should return null for null/undefined inputs', () => {
      expect(extractFolderReadme(null as any, [])).toBeNull();
      expect(extractFolderReadme('plugins', null as any)).toBeNull();
    });
  });

  describe('path normalization', () => {
    it('should normalize backslashes to forward slashes', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins\\dev-tools\\README.md',
          content: '# Tools\n\nDevelopment tools for Windows paths.',
        }),
      ];

      const result = extractFolderReadme('plugins/dev-tools', entries);
      expect(result).toBe('Development tools for Windows paths.');
    });

    it('should handle mixed slashes in folder path', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/dev-tools/README.md',
          content: '# Tools\n\nDevelopment tools description.',
        }),
      ];

      const result = extractFolderReadme('plugins\\dev-tools', entries);
      expect(result).toBe('Development tools description.');
    });
  });

  describe('direct child detection', () => {
    it('should only find READMEs directly in the folder', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/dev-tools/README.md',
          content: '# Direct README\n\nThis is the direct README in dev-tools.',
        }),
        createMockEntry({
          path: 'plugins/dev-tools/subfolder/README.md',
          content: '# Nested README\n\nThis is a nested README in a subfolder.',
        }),
      ];

      const result = extractFolderReadme('plugins/dev-tools', entries);
      expect(result).toBe('This is the direct README in dev-tools.');
    });

    it('should not match README in parent folder', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
          content: '# Parent README\n\nThis is the parent folder README.',
        }),
      ];

      const result = extractFolderReadme('plugins/dev-tools', entries);
      expect(result).toBeNull();
    });

    it('should not match README with similar prefix', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/dev-tools-extra/README.md',
          content: '# Similar Path\n\nThis is from a similarly named folder.',
        }),
      ];

      const result = extractFolderReadme('plugins/dev-tools', entries);
      expect(result).toBeNull();
    });
  });

  describe('content extraction', () => {
    it('should extract from content field if available', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
          content: '# Plugins\n\nExtracted from content field.',
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBe('Extracted from content field.');
    });

    it('should fall back to metadata.description if content not available', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
          metadata: { description: 'Extracted from metadata description.' },
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBe('Extracted from metadata description.');
    });

    it('should return null if neither content nor metadata available', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBeNull();
    });

    it('should prefer content over metadata when both exist', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
          content: '# Title\n\nPreferred content field.',
          metadata: { description: 'Metadata description.' },
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBe('Preferred content field.');
    });

    it('should handle non-string metadata.description gracefully', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
          metadata: { description: 123 as any },
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBeNull();
    });
  });

  describe('invalid entry handling', () => {
    it('should skip entries with invalid paths', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: null as any,
          content: '# Invalid\n\nThis entry has no path.',
        }),
        createMockEntry({
          path: 'plugins/README.md',
          content: '# Valid\n\nThis is the valid README.',
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBe('This is the valid README.');
    });

    it('should skip entries with non-string paths', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 123 as any,
          content: '# Invalid\n\nThis entry has invalid path type.',
        }),
        createMockEntry({
          path: 'plugins/README.md',
          content: '# Valid\n\nThis is the valid README.',
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBe('This is the valid README.');
    });
  });

  describe('edge cases', () => {
    it('should handle README with only headings', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
          content: '# Main Heading\n## Subheading\n### Sub-subheading',
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBeNull();
    });

    it('should handle empty README content', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
          content: '',
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBeNull();
    });

    it('should use first README when multiple exist (edge case)', () => {
      // This shouldn't happen in practice, but handle gracefully
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
          content: '# First\n\nThis is the first README found.',
        }),
        createMockEntry({
          path: 'plugins/readme.md',
          content: '# Second\n\nThis is the second README found.',
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBe('This is the first README found.');
    });

    it('should handle top-level folder paths', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'plugins/README.md',
          content: '# Plugins\n\nTop-level plugins folder description.',
        }),
      ];

      const result = extractFolderReadme('plugins', entries);
      expect(result).toBe('Top-level plugins folder description.');
    });

    it('should handle deeply nested folder paths', () => {
      const entries: CatalogEntry[] = [
        createMockEntry({
          path: 'a/b/c/d/e/README.md',
          content: '# Deep\n\nDeeply nested folder description.',
        }),
      ];

      const result = extractFolderReadme('a/b/c/d/e', entries);
      expect(result).toBe('Deeply nested folder description.');
    });
  });
});
