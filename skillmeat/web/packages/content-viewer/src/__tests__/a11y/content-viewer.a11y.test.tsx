/**
 * Accessibility Tests for @skillmeat/content-viewer
 * @jest-environment jsdom
 *
 * ============================================================================
 * AUDIT SUMMARY — WCAG 2.1 AA Review
 * ============================================================================
 *
 * FileTree
 * --------
 * PASS  role="tree" on root container with aria-label (customisable via ariaLabel prop).
 * PASS  role="treeitem" on every node; aria-expanded on directories only.
 * PASS  aria-level, aria-setsize, aria-posinset propagated to TreeNode.
 * PASS  role="group" with aria-label on expanded directory children.
 * PASS  role="none" wrapper div prevents spurious roles from leaking.
 * PASS  Roving tabindex (tabIndex 0 on focused node, -1 on all others).
 * PASS  Arrow key navigation (Up/Down/Home/End/Left/Right) via onKeyNavigation.
 * PASS  Enter/Space activate the focused node.
 * PASS  All decorative icons marked aria-hidden="true".
 * PASS  Delete button carries aria-label="Delete <filename>".
 * PASS  Add-file button carries aria-label="Add new file".
 * PASS  focus-visible:ring-2 ring class applied to treeitem for visible focus ring.
 * NOTE  Loading skeleton has no accessible role or label; this is acceptable
 *       because the tree container is absent — screen readers will not encounter
 *       focusable content during loading. No violation raised by axe.
 * NOTE  Empty-state heading ("No files found") uses h3 — acceptable as an
 *       informational placeholder; no interactive content present.
 *
 * ContentPane
 * -----------
 * PASS  role="region" with aria-label on the root container.
 * PASS  aria-labelledby points to the Breadcrumb <nav> id; avoids duplicate
 *       labelling (the nav also carries aria-label="File path").
 *       NOTE: aria-label and aria-labelledby are both present on the region —
 *       aria-labelledby takes precedence per the spec. The redundancy is harmless
 *       but the aria-label could be dropped once aria-labelledby is reliably set.
 *       // TODO: a11y fix needed — remove redundant aria-label from content-pane
 *       // region when aria-labelledby is present; aria-labelledby is sufficient.
 * PASS  Breadcrumb uses <nav aria-label="File path"> landmark.
 * PASS  aria-current="page" on final breadcrumb segment.
 * PASS  Edit button carries aria-label="Edit <path>".
 * PASS  Cancel/Save buttons have accessible text content.
 * PASS  Error state uses role="alert" (via Alert component which sets role="alert").
 * PASS  Truncation banner uses role="alert" through Alert component.
 * PASS  All decorative icons marked aria-hidden="true".
 * NOTE  EmptyState <FileText> icon lacks aria-hidden — minor (icon is presentational).
 *       // TODO: a11y fix needed — add aria-hidden="true" to the FileText icon in
 *       // the EmptyState sub-component inside ContentPane.tsx.
 * NOTE  isSaving state changes button text to "Saving..." — this is fine as-is;
 *       an aria-live region would improve the announcement but is not required for AA.
 *
 * FrontmatterDisplay
 * ------------------
 * PASS  Collapsible trigger is a <button> (via Radix CollapsibleTrigger + asChild).
 * PASS  aria-label on toggle button reflects current state ("Show"/"Hide frontmatter").
 * PASS  All icons are aria-hidden.
 * NOTE  Key-value pairs are rendered as plain <div> + <strong> pairs, not as a <dl>.
 *       This is a mild semantic gap — a definition list (<dl>/<dt>/<dd>) would be
 *       more appropriate for screen readers that announce "definition list, N items".
 *       axe does not flag this as a violation.
 *       // TODO: a11y fix needed — consider replacing the div+strong key-value pairs
 *       // in FrontmatterDisplay with a <dl>/<dt>/<dd> structure for richer SR semantics.
 *
 * SplitPreview / MarkdownEditor
 * ------------------------------
 * PASS  SplitPreview preview panel uses a scrollable region via Radix ScrollArea.
 * NOTE  The preview <div> wrapping ReactMarkdown has no explicit landmark or region
 *       role/label. The surrounding ContentPane region label covers it transitively.
 * NOTE  MarkdownEditor (CodeMirror 6) renders its own accessible text area
 *       (<div role="textbox" contenteditable="true"> with aria-multiline).
 *       CodeMirror handles its own keyboard/focus behaviour. No custom a11y wrapping
 *       is added by the component (acceptable — CodeMirror manages it internally).
 *       Both components are mocked in tests because CodeMirror cannot run in jsdom.
 *
 * Parity with pre-extraction behaviour
 * --------------------------------------
 * The components were extracted from the SkillMeat web app without semantic changes.
 * All ARIA attributes, keyboard handlers, and focus management logic are identical
 * to the originals in skillmeat/web/components/entity/. The findings above therefore
 * apply equally to both the package and the legacy locations.
 * ============================================================================
 */

import React, { act } from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { axe } from 'jest-axe';

// ---------------------------------------------------------------------------
// Module-level mocks — must be declared before imports
// ---------------------------------------------------------------------------

jest.mock('../../components/SplitPreview', () => ({
  SplitPreview: ({ content }: { content: string }) => (
    <div data-testid="mock-split-preview" role="region" aria-label="Markdown preview">
      {content}
    </div>
  ),
}));

jest.mock('../../components/MarkdownEditor', () => ({
  MarkdownEditor: ({ initialContent }: { initialContent: string }) => (
    <div
      data-testid="mock-markdown-editor"
      role="textbox"
      aria-multiline="true"
      aria-label="Markdown editor"
    >
      {initialContent}
    </div>
  ),
}));

// ---------------------------------------------------------------------------
// Imports — after mocks
// ---------------------------------------------------------------------------

import { FileTree } from '../../components/FileTree';
import { FrontmatterDisplay } from '../../components/FrontmatterDisplay';
import { ContentPane } from '../../components/ContentPane';
import type { FileNode } from '../../types';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const FLAT_FILES: FileNode[] = [
  { name: 'README.md', path: 'README.md', type: 'file' },
  { name: 'index.ts', path: 'index.ts', type: 'file' },
];

const NESTED_FILES: FileNode[] = [
  {
    name: 'src',
    path: 'src',
    type: 'directory',
    children: [
      { name: 'index.ts', path: 'src/index.ts', type: 'file' },
      { name: 'utils.ts', path: 'src/utils.ts', type: 'file' },
    ],
  },
  { name: 'README.md', path: 'README.md', type: 'file' },
];

const SAMPLE_FRONTMATTER: Record<string, unknown> = {
  title: 'My Skill',
  version: '1.0.0',
  tags: ['react', 'typescript'],
  author: { name: 'Alice', email: 'alice@example.com' },
  active: true,
};

// ============================================================================
// FileTree — ARIA structure
// ============================================================================

describe('FileTree — ARIA structure and axe', () => {
  it('has no axe violations with a flat file list', async () => {
    const { container } = render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations with nested directories (all collapsed)', async () => {
    const { container } = render(
      <FileTree
        entityId="test"
        files={NESTED_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations in read-only mode', async () => {
    const { container } = render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
        readOnly={true}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations with a selected file', async () => {
    const { container } = render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath="README.md"
        onSelect={jest.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations in loading state', async () => {
    const { container } = render(
      <FileTree
        entityId="test"
        files={[]}
        selectedPath={null}
        onSelect={jest.fn()}
        isLoading={true}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations in empty state', async () => {
    const { container } = render(
      <FileTree
        entityId="test"
        files={[]}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('applies role="tree" to the container', () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
        ariaLabel="Artifact files"
      />
    );
    expect(screen.getByRole('tree', { name: 'Artifact files' })).toBeInTheDocument();
  });

  it('applies default aria-label "File browser" when ariaLabel is omitted', () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    expect(screen.getByRole('tree', { name: 'File browser' })).toBeInTheDocument();
  });

  it('renders file nodes with role="treeitem"', () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const tree = screen.getByRole('tree');
    const items = within(tree).getAllByRole('treeitem');
    expect(items.length).toBeGreaterThanOrEqual(FLAT_FILES.length);
  });

  it('sets aria-selected=true on the currently selected file', () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath="README.md"
        onSelect={jest.fn()}
      />
    );
    const selected = screen.getByRole('treeitem', { name: /README\.md/i });
    expect(selected).toHaveAttribute('aria-selected', 'true');
  });

  it('sets aria-selected=false on unselected files', () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath="README.md"
        onSelect={jest.fn()}
      />
    );
    const unselected = screen.getByRole('treeitem', { name: /index\.ts/i });
    expect(unselected).toHaveAttribute('aria-selected', 'false');
  });

  it('sets aria-expanded=false on a collapsed directory', () => {
    render(
      <FileTree
        entityId="test"
        files={NESTED_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const dir = screen.getByRole('treeitem', { name: /^src$/i });
    expect(dir).toHaveAttribute('aria-expanded', 'false');
  });

  it('sets aria-expanded=true after expanding a directory', async () => {
    render(
      <FileTree
        entityId="test"
        files={NESTED_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const dir = screen.getByRole('treeitem', { name: /^src$/i });
    await act(async () => {
      fireEvent.click(dir);
    });
    expect(dir).toHaveAttribute('aria-expanded', 'true');
  });

  it('does not set aria-expanded on file nodes', () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const fileItem = screen.getByRole('treeitem', { name: /README\.md/i });
    expect(fileItem).not.toHaveAttribute('aria-expanded');
  });

  it('has no axe violations after expanding a directory', async () => {
    const { container } = render(
      <FileTree
        entityId="test"
        files={NESTED_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const dir = screen.getByRole('treeitem', { name: /^src$/i });
    await act(async () => {
      fireEvent.click(dir);
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('child group has aria-label describing the directory', async () => {
    render(
      <FileTree
        entityId="test"
        files={NESTED_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const dir = screen.getByRole('treeitem', { name: /^src$/i });
    await act(async () => {
      fireEvent.click(dir);
    });
    // The expanded children are wrapped in role="group" aria-label="Contents of src"
    expect(screen.getByRole('group', { name: /Contents of src/i })).toBeInTheDocument();
  });

  it('delete button has a descriptive aria-label', () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
        onDeleteFile={jest.fn()}
      />
    );
    // Delete buttons are present but visually hidden (opacity-0); they are still in DOM
    const deleteBtn = screen.getByRole('button', { name: /Delete README\.md/i });
    expect(deleteBtn).toBeInTheDocument();
  });

  it('add-file button has aria-label="Add new file"', () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
        onAddFile={jest.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /Add new file/i })).toBeInTheDocument();
  });

  it('has no axe violations when add-file and delete actions are present', async () => {
    const { container } = render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
        onAddFile={jest.fn()}
        onDeleteFile={jest.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

// ============================================================================
// FileTree — Keyboard navigation
// ============================================================================

describe('FileTree — keyboard navigation', () => {
  it('ArrowDown moves focus to the next treeitem', async () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const tree = screen.getByRole('tree');
    const items = within(tree).getAllByRole('treeitem');
    const first = items[0]!;
    const second = items[1]!;

    // Give focus to the first item explicitly
    await act(async () => {
      first.focus();
    });
    expect(document.activeElement).toBe(first);

    await act(async () => {
      fireEvent.keyDown(first, { key: 'ArrowDown' });
    });
    expect(document.activeElement).toBe(second);
  });

  it('ArrowUp moves focus to the previous treeitem', async () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const tree = screen.getByRole('tree');
    const items = within(tree).getAllByRole('treeitem');
    const first = items[0]!;
    const second = items[1]!;

    await act(async () => {
      second.focus();
    });
    await act(async () => {
      fireEvent.keyDown(second, { key: 'ArrowUp' });
    });
    expect(document.activeElement).toBe(first);
  });

  it('Home moves focus to the first treeitem', async () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const tree = screen.getByRole('tree');
    const items = within(tree).getAllByRole('treeitem');
    const last = items[items.length - 1]!;
    const first = items[0]!;

    await act(async () => {
      last.focus();
    });
    await act(async () => {
      fireEvent.keyDown(last, { key: 'Home' });
    });
    expect(document.activeElement).toBe(first);
  });

  it('End moves focus to the last treeitem', async () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const tree = screen.getByRole('tree');
    const items = within(tree).getAllByRole('treeitem');
    const first = items[0]!;
    const last = items[items.length - 1]!;

    await act(async () => {
      first.focus();
    });
    await act(async () => {
      fireEvent.keyDown(first, { key: 'End' });
    });
    expect(document.activeElement).toBe(last);
  });

  it('ArrowRight expands a collapsed directory', async () => {
    render(
      <FileTree
        entityId="test"
        files={NESTED_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const dir = screen.getByRole('treeitem', { name: /^src$/i });
    expect(dir).toHaveAttribute('aria-expanded', 'false');

    await act(async () => {
      dir.focus();
      fireEvent.keyDown(dir, { key: 'ArrowRight' });
    });
    expect(dir).toHaveAttribute('aria-expanded', 'true');
  });

  it('ArrowLeft collapses an expanded directory', async () => {
    render(
      <FileTree
        entityId="test"
        files={NESTED_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const dir = screen.getByRole('treeitem', { name: /^src$/i });

    // Expand first
    await act(async () => {
      dir.focus();
      fireEvent.keyDown(dir, { key: 'ArrowRight' });
    });
    expect(dir).toHaveAttribute('aria-expanded', 'true');

    // Now collapse
    await act(async () => {
      fireEvent.keyDown(dir, { key: 'ArrowLeft' });
    });
    expect(dir).toHaveAttribute('aria-expanded', 'false');
  });

  it('Enter activates (selects) a file node', async () => {
    const onSelect = jest.fn();
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={onSelect}
      />
    );
    const fileItem = screen.getByRole('treeitem', { name: /README\.md/i });

    await act(async () => {
      fileItem.focus();
      fireEvent.keyDown(fileItem, { key: 'Enter' });
    });
    expect(onSelect).toHaveBeenCalledWith('README.md');
  });

  it('Space activates (selects) a file node', async () => {
    const onSelect = jest.fn();
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={onSelect}
      />
    );
    const fileItem = screen.getByRole('treeitem', { name: /README\.md/i });

    await act(async () => {
      fileItem.focus();
      fireEvent.keyDown(fileItem, { key: ' ' });
    });
    expect(onSelect).toHaveBeenCalledWith('README.md');
  });

  it('only one treeitem has tabIndex=0 at a time (roving tabindex)', () => {
    render(
      <FileTree
        entityId="test"
        files={FLAT_FILES}
        selectedPath={null}
        onSelect={jest.fn()}
      />
    );
    const tree = screen.getByRole('tree');
    const items = within(tree).getAllByRole('treeitem');
    const focused = items.filter((el) => el.getAttribute('tabindex') === '0');
    expect(focused).toHaveLength(1);
  });
});

// ============================================================================
// ContentPane — ARIA structure and axe
// ============================================================================

describe('ContentPane — ARIA structure and axe', () => {
  it('has no axe violations in empty state (no path)', async () => {
    const { container } = render(<ContentPane path={null} content={null} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations in loading state', async () => {
    const { container } = render(
      <ContentPane path="src/index.ts" content={null} isLoading={true} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations with a plain text file in read-only mode', async () => {
    const { container } = render(
      <ContentPane path="src/index.ts" content="export const x = 1;" readOnly={true} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations with a markdown file in read-only mode', async () => {
    await act(async () => {});
    const { container } = render(
      <ContentPane path="README.md" content="# Hello world" readOnly={true} />
    );
    await act(async () => {});
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations when edit button is visible', async () => {
    const { container } = render(
      <ContentPane
        path="src/index.ts"
        content="export const x = 1;"
        readOnly={false}
        onEditStart={jest.fn()}
        onSave={jest.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations in editing mode (save/cancel visible)', async () => {
    const { container } = render(
      <ContentPane
        path="src/index.ts"
        content="export const x = 1;"
        readOnly={false}
        isEditing={true}
        editedContent="export const x = 2;"
        onEditStart={jest.fn()}
        onEditChange={jest.fn()}
        onSave={jest.fn()}
        onCancel={jest.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations in error state', async () => {
    const { container } = render(
      <ContentPane path="src/index.ts" content={null} error="Failed to load file" />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations with frontmatter content', async () => {
    const content = `---\ntitle: My Skill\ntags:\n  - react\n---\n\n# Body content`;
    const { container } = render(
      <ContentPane path="README.md" content={content} readOnly={true} />
    );
    await act(async () => {});
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations with truncation banner', async () => {
    const { container } = render(
      <ContentPane
        path="big-file.ts"
        content="// lots of code"
        readOnly={true}
        truncationInfo={{ truncated: true, originalSize: 2097152 }}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has role="region" on the content pane container', () => {
    render(
      <ContentPane path="src/index.ts" content="const x = 1;" readOnly={true} />
    );
    // role="region" requires an accessible name to be recognised as a landmark
    expect(screen.getByRole('region')).toBeInTheDocument();
  });

  it('breadcrumb uses a nav landmark with aria-label="File path"', () => {
    render(
      <ContentPane path="src/index.ts" content="const x = 1;" readOnly={true} />
    );
    expect(screen.getByRole('navigation', { name: /File path/i })).toBeInTheDocument();
  });

  it('last breadcrumb segment has aria-current="page"', () => {
    render(
      <ContentPane path="src/index.ts" content="const x = 1;" readOnly={true} />
    );
    const current = screen.getByText('index.ts');
    expect(current).toHaveAttribute('aria-current', 'page');
  });

  it('edit button has descriptive aria-label', () => {
    render(
      <ContentPane
        path="src/index.ts"
        content="const x = 1;"
        readOnly={false}
        onEditStart={jest.fn()}
        onSave={jest.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /Edit src\/index\.ts/i })).toBeInTheDocument();
  });

  it('save and cancel buttons are accessible when in editing mode (markdown file)', () => {
    // Save/Cancel are rendered in the markdown branch of ContentPane when isEditing=true.
    // Non-markdown files only show the edit button (not the save/cancel pair).
    render(
      <ContentPane
        path="README.md"
        content="# Hello"
        readOnly={false}
        isEditing={true}
        editedContent="# Hello World"
        onEditStart={jest.fn()}
        onEditChange={jest.fn()}
        onSave={jest.fn()}
        onCancel={jest.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /Save/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
  });

  it('error state uses role="alert" for immediate announcement', () => {
    render(
      <ContentPane path="src/index.ts" content={null} error="Network error" />
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('truncation banner uses role="alert"', () => {
    render(
      <ContentPane
        path="big.ts"
        content="// content"
        readOnly={true}
        truncationInfo={{ truncated: true, originalSize: 5000000 }}
      />
    );
    // The truncation Alert component sets role="alert"
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});

// ============================================================================
// FrontmatterDisplay — ARIA structure and axe
// ============================================================================

describe('FrontmatterDisplay — ARIA structure and axe', () => {
  it('has no axe violations in expanded state (default)', async () => {
    const { container } = render(
      <FrontmatterDisplay frontmatter={SAMPLE_FRONTMATTER} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations in collapsed state', async () => {
    const { container } = render(
      <FrontmatterDisplay frontmatter={SAMPLE_FRONTMATTER} defaultCollapsed={true} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations after toggling open', async () => {
    const { container } = render(
      <FrontmatterDisplay frontmatter={SAMPLE_FRONTMATTER} defaultCollapsed={true} />
    );
    const toggleBtn = screen.getByRole('button', { name: /Show frontmatter/i });
    await act(async () => {
      fireEvent.click(toggleBtn);
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has no axe violations with a minimal single-key frontmatter', async () => {
    const { container } = render(
      <FrontmatterDisplay frontmatter={{ title: 'Hello' }} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('renders nothing when frontmatter is empty', () => {
    const { container } = render(<FrontmatterDisplay frontmatter={{}} />);
    expect(container.firstChild).toBeNull();
  });

  it('toggle button has aria-label="Hide frontmatter" when expanded', () => {
    render(<FrontmatterDisplay frontmatter={SAMPLE_FRONTMATTER} defaultCollapsed={false} />);
    expect(screen.getByRole('button', { name: /Hide frontmatter/i })).toBeInTheDocument();
  });

  it('toggle button has aria-label="Show frontmatter" when collapsed', () => {
    render(<FrontmatterDisplay frontmatter={SAMPLE_FRONTMATTER} defaultCollapsed={true} />);
    expect(screen.getByRole('button', { name: /Show frontmatter/i })).toBeInTheDocument();
  });

  it('toggle button label switches after click', async () => {
    render(<FrontmatterDisplay frontmatter={SAMPLE_FRONTMATTER} defaultCollapsed={true} />);
    const btn = screen.getByRole('button', { name: /Show frontmatter/i });
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(screen.getByRole('button', { name: /Hide frontmatter/i })).toBeInTheDocument();
  });

  it('section heading "Frontmatter" is present', () => {
    render(<FrontmatterDisplay frontmatter={SAMPLE_FRONTMATTER} />);
    expect(screen.getByText('Frontmatter')).toBeInTheDocument();
  });

  it('key-value entries are visible when expanded', () => {
    render(
      <FrontmatterDisplay frontmatter={{ title: 'My Skill', version: '2.0' }} defaultCollapsed={false} />
    );
    expect(screen.getByText('title')).toBeInTheDocument();
    expect(screen.getByText('My Skill')).toBeInTheDocument();
    expect(screen.getByText('version')).toBeInTheDocument();
    expect(screen.getByText('2.0')).toBeInTheDocument();
  });

  // TODO: a11y fix needed — consider replacing the div+strong key-value pairs
  // in FrontmatterDisplay with a <dl>/<dt>/<dd> structure for richer SR semantics.
  it('documents that key-value pairs are plain divs rather than a definition list', () => {
    const { container } = render(
      <FrontmatterDisplay frontmatter={{ title: 'My Skill' }} defaultCollapsed={false} />
    );
    // Assert current behaviour: no <dl> element present
    expect(container.querySelector('dl')).toBeNull();
  });
});
