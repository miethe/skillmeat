/**
 * Parity tests for re-export stubs — BASE-002 scenario 10
 *
 * Scenario 10 — Re-export stubs:
 *   The in-app re-export stubs (e.g. components/entity/file-tree.tsx,
 *   components/entity/content-pane.tsx, lib/frontmatter.ts, …) simply
 *   re-export everything from @skillmeat/content-viewer.  These tests
 *   verify that the public barrel from the package exports the same symbols
 *   that consumers expect, so any future package restructuring that silently
 *   removes or renames an export is caught immediately.
 *
 * The tests intentionally import from the package barrel (@skillmeat/content-viewer)
 * rather than the in-app stubs to avoid resolving @/ path aliases that are only
 * available inside the Next.js module resolver.
 */

// ---------------------------------------------------------------------------
// Module-level mocks — prevent CodeMirror / react-markdown from loading in
// jsdom. The package barrel exports SplitPreview which transitively imports
// react-markdown (ESM-only). Mocking these here keeps the test environment
// stable without modifying the transformIgnorePatterns config.
// ---------------------------------------------------------------------------

jest.mock('../../components/SplitPreview', () => ({
  SplitPreview: () => <div data-testid="mock-split-preview">MockSplitPreview</div>,
}));

jest.mock('../../components/MarkdownEditor', () => ({
  MarkdownEditor: () => <div data-testid="mock-markdown-editor">MockMarkdownEditor</div>,
}));

// ---------------------------------------------------------------------------
// Imports — public barrel only (no internal paths)
// ---------------------------------------------------------------------------

import React from 'react';
import * as ContentViewerPackage from '@skillmeat/content-viewer';

// ---------------------------------------------------------------------------
// Component exports
// ---------------------------------------------------------------------------

describe('Re-export parity — components (scenario 10)', () => {
  it('exports FileTree as a function (component)', () => {
    expect(typeof ContentViewerPackage.FileTree).toBe('function');
  });

  it('exports FrontmatterDisplay as a function (component)', () => {
    expect(typeof ContentViewerPackage.FrontmatterDisplay).toBe('function');
  });

  it('exports ContentPane as a function (component)', () => {
    expect(typeof ContentViewerPackage.ContentPane).toBe('function');
  });

  it('exports SplitPreview as a function (component)', () => {
    expect(typeof ContentViewerPackage.SplitPreview).toBe('function');
  });

  it('exports MarkdownEditor as a function (component)', () => {
    expect(typeof ContentViewerPackage.MarkdownEditor).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// Utility function exports
// ---------------------------------------------------------------------------

describe('Re-export parity — utility functions (scenario 10)', () => {
  it('exports parseFrontmatter as a function', () => {
    expect(typeof ContentViewerPackage.parseFrontmatter).toBe('function');
  });

  it('exports stripFrontmatter as a function', () => {
    expect(typeof ContentViewerPackage.stripFrontmatter).toBe('function');
  });

  it('exports detectFrontmatter as a function', () => {
    expect(typeof ContentViewerPackage.detectFrontmatter).toBe('function');
  });

  it('exports extractFirstParagraph as a function', () => {
    expect(typeof ContentViewerPackage.extractFirstParagraph).toBe('function');
  });

  it('exports extractFolderReadme as a function', () => {
    expect(typeof ContentViewerPackage.extractFolderReadme).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// Provider / hook exports
// ---------------------------------------------------------------------------

describe('Re-export parity — provider and hook (scenario 10)', () => {
  it('exports ContentViewerProvider as a function (component)', () => {
    expect(typeof ContentViewerPackage.ContentViewerProvider).toBe('function');
  });

  it('exports useContentViewerAdapter as a function (hook)', () => {
    expect(typeof ContentViewerPackage.useContentViewerAdapter).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// Functional equivalence spot-checks
// These verify that the re-exported utilities behave identically to what
// the in-app stubs used to expose — confirming no silent wrapping occurred.
// ---------------------------------------------------------------------------

describe('Re-export parity — functional equivalence (scenario 10)', () => {
  it('parseFrontmatter from package returns same result as direct call', () => {
    const input = '---\ntitle: Test\n---\nBody';
    const result = ContentViewerPackage.parseFrontmatter(input);

    expect(result.frontmatter).not.toBeNull();
    expect((result.frontmatter as Record<string, unknown>)['title']).toBe('Test');
    expect(result.content).toBe('Body');
  });

  it('stripFrontmatter from package removes the frontmatter block', () => {
    const input = '---\ntitle: Test\n---\nBody content';
    const stripped = ContentViewerPackage.stripFrontmatter(input);

    expect(stripped).toBe('Body content');
    expect(stripped).not.toContain('---');
  });

  it('detectFrontmatter from package correctly identifies frontmatter presence', () => {
    expect(ContentViewerPackage.detectFrontmatter('---\ntitle: t\n---\nBody')).toBe(true);
    expect(ContentViewerPackage.detectFrontmatter('# No frontmatter here')).toBe(false);
  });

  it('extractFirstParagraph from package skips headings and returns first paragraph', () => {
    const markdown = '# Heading\n\nThis is the first meaningful paragraph with enough content.';
    const paragraph = ContentViewerPackage.extractFirstParagraph(markdown);

    expect(paragraph).toBe('This is the first meaningful paragraph with enough content.');
  });

  it('extractFolderReadme from package finds README in folder entries', () => {
    const entries = [
      { path: 'plugins/README.md', content: 'A description of the plugins folder with extra text here.' },
      { path: 'plugins/index.ts' },
    ];

    const result = ContentViewerPackage.extractFolderReadme('plugins', entries);

    expect(result).toBe('A description of the plugins folder with extra text here.');
  });

  it('extractFolderReadme returns null when no README exists for the folder', () => {
    const entries = [
      { path: 'plugins/index.ts' },
      { path: 'other/README.md', content: 'Wrong folder readme content here.' },
    ];

    const result = ContentViewerPackage.extractFolderReadme('plugins', entries);

    expect(result).toBeNull();
  });
});
