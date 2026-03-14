/**
 * Parity tests for FileTree — BASE-002 scenarios 2 & 3
 *
 * Scenario 2 — Tree selection:
 *   Click a file node in the FileTree → onSelect callback is invoked with the
 *   correct file path.
 *
 * Scenario 3 — Tree keyboard navigation:
 *   Arrow keys move focus between visible tree items; Enter/Space activate the
 *   focused item (selects a file or toggles a directory).
 *
 * All imports come from the public @skillmeat/content-viewer barrel so any
 * future re-packaging is caught immediately if exports drift.
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
// Imports — after mocks are registered
// ---------------------------------------------------------------------------

import React, { act } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FileTree } from '@skillmeat/content-viewer';
import type { FileNode } from '@skillmeat/content-viewer';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const FLAT_FILES: FileNode[] = [
  { name: 'README.md', path: 'README.md', type: 'file' },
  { name: 'LICENSE', path: 'LICENSE', type: 'file' },
];

const NESTED_FILES: FileNode[] = [
  { name: 'README.md', path: 'README.md', type: 'file' },
  {
    name: 'src',
    path: 'src',
    type: 'directory',
    children: [
      { name: 'index.ts', path: 'src/index.ts', type: 'file' },
      { name: 'utils.ts', path: 'src/utils.ts', type: 'file' },
    ],
  },
];

// ---------------------------------------------------------------------------
// Scenario 2 — Tree selection
// ---------------------------------------------------------------------------

describe('FileTree — tree selection (scenario 2)', () => {
  it('calls onSelect with the clicked file path', async () => {
    const onSelect = jest.fn();

    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={FLAT_FILES}
          selectedPath={null}
          onSelect={onSelect}
        />
      );
    });

    await act(async () => {
      fireEvent.click(screen.getByText('README.md'));
    });

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('README.md');
  });

  it('calls onSelect with the second file path when the second file is clicked', async () => {
    const onSelect = jest.fn();

    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={FLAT_FILES}
          selectedPath={null}
          onSelect={onSelect}
        />
      );
    });

    await act(async () => {
      fireEvent.click(screen.getByText('LICENSE'));
    });

    expect(onSelect).toHaveBeenCalledWith('LICENSE');
  });

  it('marks a file as selected via aria-selected when selectedPath matches', async () => {
    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={FLAT_FILES}
          selectedPath="README.md"
          onSelect={jest.fn()}
        />
      );
    });

    const readmeItem = screen.getByTestId('tree-item-README.md');
    expect(readmeItem).toHaveAttribute('aria-selected', 'true');

    const licenseItem = screen.getByTestId('tree-item-LICENSE');
    expect(licenseItem).toHaveAttribute('aria-selected', 'false');
  });

  it('does NOT call onSelect when clicking a directory — clicking toggles expand instead', async () => {
    const onSelect = jest.fn();

    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={NESTED_FILES}
          selectedPath={null}
          onSelect={onSelect}
        />
      );
    });

    // Click the directory node
    await act(async () => {
      fireEvent.click(screen.getByText('src'));
    });

    // Directory click should NOT call onSelect
    expect(onSelect).not.toHaveBeenCalled();

    // Children should now be visible after expand
    expect(screen.getByText('index.ts')).toBeInTheDocument();
  });

  it('calls onSelect with child file path after expanding its parent directory', async () => {
    const onSelect = jest.fn();

    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={NESTED_FILES}
          selectedPath={null}
          onSelect={onSelect}
        />
      );
    });

    // Expand the directory first
    await act(async () => {
      fireEvent.click(screen.getByText('src'));
    });

    // Now click the nested file
    await act(async () => {
      fireEvent.click(screen.getByText('index.ts'));
    });

    expect(onSelect).toHaveBeenCalledWith('src/index.ts');
  });

  it('renders with the tree role accessible container', async () => {
    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={FLAT_FILES}
          selectedPath={null}
          onSelect={jest.fn()}
          ariaLabel="Artifact file browser"
        />
      );
    });

    const tree = screen.getByRole('tree', { name: 'Artifact file browser' });
    expect(tree).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Scenario 3 — Keyboard navigation
// ---------------------------------------------------------------------------

describe('FileTree — keyboard navigation (scenario 3)', () => {
  it('renders treeitem roles for each file node', async () => {
    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={FLAT_FILES}
          selectedPath={null}
          onSelect={jest.fn()}
        />
      );
    });

    const treeItems = screen.getAllByRole('treeitem');
    expect(treeItems.length).toBe(2);
  });

  it('Enter key on a file node triggers onSelect', async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup();

    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={FLAT_FILES}
          selectedPath={null}
          onSelect={onSelect}
        />
      );
    });

    const readmeItem = screen.getByTestId('tree-item-README.md');

    await act(async () => {
      readmeItem.focus();
      await user.keyboard('{Enter}');
    });

    expect(onSelect).toHaveBeenCalledWith('README.md');
  });

  it('Space key on a file node triggers onSelect', async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup();

    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={FLAT_FILES}
          selectedPath={null}
          onSelect={onSelect}
        />
      );
    });

    const readmeItem = screen.getByTestId('tree-item-README.md');

    await act(async () => {
      readmeItem.focus();
      await user.keyboard(' ');
    });

    expect(onSelect).toHaveBeenCalledWith('README.md');
  });

  it('ArrowRight key on a collapsed directory expands it', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={NESTED_FILES}
          selectedPath={null}
          onSelect={jest.fn()}
        />
      );
    });

    const dirItem = screen.getByTestId('tree-item-src');

    // src directory is collapsed initially — children not visible
    expect(screen.queryByText('index.ts')).not.toBeInTheDocument();

    await act(async () => {
      dirItem.focus();
      await user.keyboard('{ArrowRight}');
    });

    // Directory should now be expanded
    expect(screen.getByText('index.ts')).toBeInTheDocument();
    expect(dirItem).toHaveAttribute('aria-expanded', 'true');
  });

  it('ArrowLeft key on an expanded directory collapses it', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={NESTED_FILES}
          selectedPath={null}
          onSelect={jest.fn()}
        />
      );
    });

    const dirItem = screen.getByTestId('tree-item-src');

    // First expand the directory
    await act(async () => {
      dirItem.focus();
      await user.keyboard('{ArrowRight}');
    });

    expect(screen.getByText('index.ts')).toBeInTheDocument();

    // Now collapse it
    await act(async () => {
      await user.keyboard('{ArrowLeft}');
    });

    expect(screen.queryByText('index.ts')).not.toBeInTheDocument();
    expect(dirItem).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows loading skeleton when isLoading is true', async () => {
    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={[]}
          selectedPath={null}
          onSelect={jest.fn()}
          isLoading={true}
        />
      );
    });

    // In loading state the tree role should not be present
    expect(screen.queryByRole('tree')).not.toBeInTheDocument();
    // Skeleton elements should be rendered
    expect(screen.queryByRole('treeitem')).not.toBeInTheDocument();
  });

  it('shows empty state message when files array is empty and not loading', async () => {
    await act(async () => {
      render(
        <FileTree
          entityId="entity-1"
          files={[]}
          selectedPath={null}
          onSelect={jest.fn()}
        />
      );
    });

    expect(screen.getByText('No files found')).toBeInTheDocument();
  });
});
