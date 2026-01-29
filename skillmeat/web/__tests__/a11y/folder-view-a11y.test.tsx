/**
 * Accessibility Tests for Folder View Components
 *
 * Verifies ARIA attributes, screen reader compatibility, and accessibility
 * patterns for the marketplace folder view components.
 *
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { SemanticTree } from '@/app/marketplace/sources/[id]/components/semantic-tree';
import { TreeNode } from '@/app/marketplace/sources/[id]/components/tree-node';
import { FolderDetailPane } from '@/app/marketplace/sources/[id]/components/folder-detail-pane';
import { SubfoldersSection } from '@/app/marketplace/sources/[id]/components/subfolders-section';
import { SubfolderCard } from '@/app/marketplace/sources/[id]/components/subfolder-card';
import { ArtifactTypeSection } from '@/app/marketplace/sources/[id]/components/artifact-type-section';
import type { FolderTree, FolderNode } from '@/lib/tree-builder';
import type { CatalogEntry, CatalogFilters } from '@/types/marketplace';

// ============================================================================
// Test Data
// ============================================================================

const createMockFolderNode = (
  name: string,
  fullPath: string,
  options: Partial<FolderNode> = {}
): FolderNode => ({
  name,
  fullPath,
  directArtifacts: [],
  totalArtifactCount: options.totalArtifactCount ?? 3,
  directCount: options.directCount ?? 2,
  children: options.children ?? {},
  hasSubfolders: options.hasSubfolders ?? false,
  hasDirectArtifacts: options.hasDirectArtifacts ?? true,
});

const createMockCatalogEntry = (id: string, path: string): CatalogEntry => ({
  id,
  source_id: 'test-source',
  artifact_type: 'skill',
  name: `artifact-${id}`,
  path,
  upstream_url: `https://github.com/test/${path}`,
  detected_at: new Date().toISOString(),
  confidence_score: 0.95,
  status: 'available',
});

/**
 * Create a mock tree that won't be filtered out by semantic filtering.
 * Uses names that aren't in ROOT_EXCLUSIONS or LEAF_CONTAINERS.
 */
const createUnfilteredMockTree = (): FolderTree => ({
  tooling: {
    name: 'tooling',
    fullPath: 'tooling',
    directArtifacts: [
      createMockCatalogEntry('1', 'tooling/skill-1'),
      createMockCatalogEntry('2', 'tooling/skill-2'),
    ],
    totalArtifactCount: 10,
    directCount: 2,
    children: {
      'dev-helpers': {
        name: 'dev-helpers',
        fullPath: 'tooling/dev-helpers',
        directArtifacts: [createMockCatalogEntry('3', 'tooling/dev-helpers/skill-3')],
        totalArtifactCount: 5,
        directCount: 1,
        children: {},
        hasSubfolders: false,
        hasDirectArtifacts: true,
      },
      linting: {
        name: 'linting',
        fullPath: 'tooling/linting',
        directArtifacts: [createMockCatalogEntry('4', 'tooling/linting/skill-4')],
        totalArtifactCount: 3,
        directCount: 1,
        children: {},
        hasSubfolders: false,
        hasDirectArtifacts: true,
      },
    },
    hasSubfolders: true,
    hasDirectArtifacts: true,
  },
  formatters: {
    name: 'formatters',
    fullPath: 'formatters',
    directArtifacts: [createMockCatalogEntry('5', 'formatters/skill-5')],
    totalArtifactCount: 4,
    directCount: 1,
    children: {},
    hasSubfolders: false,
    hasDirectArtifacts: true,
  },
});

const mockFilters: CatalogFilters = {
  type: null,
  confidence: 0,
  search: '',
  status: null,
};

// ============================================================================
// SemanticTree Tests
// ============================================================================

describe('SemanticTree Accessibility', () => {
  const defaultProps = {
    tree: createUnfilteredMockTree(),
    selectedFolder: null,
    expanded: new Set<string>(),
    onSelectFolder: jest.fn(),
    onToggleExpand: jest.fn(),
  };

  it('should have no accessibility violations with content', async () => {
    const { container } = render(<SemanticTree {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no accessibility violations when empty', async () => {
    const { container } = render(<SemanticTree {...defaultProps} tree={{}} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('tree has correct ARIA role and label', () => {
    render(<SemanticTree {...defaultProps} />);
    const tree = screen.getByRole('tree');
    expect(tree).toBeInTheDocument();
    expect(tree).toHaveAttribute('aria-label', 'Folder tree');
  });

  it('navigation wrapper has correct label', () => {
    render(<SemanticTree {...defaultProps} />);
    const nav = screen.getByRole('navigation');
    expect(nav).toHaveAttribute('aria-label', 'Folder navigation');
  });

  it('tree items have correct ARIA attributes', () => {
    render(<SemanticTree {...defaultProps} />);
    const items = screen.getAllByRole('treeitem');
    expect(items.length).toBeGreaterThanOrEqual(1);

    items.forEach((item) => {
      expect(item).toHaveAttribute('aria-level');
      expect(item).toHaveAttribute('aria-setsize');
      expect(item).toHaveAttribute('aria-posinset');
      expect(item).toHaveAttribute('aria-selected');
      expect(item).toHaveAttribute('aria-label');
    });
  });

  it('expanded folders have aria-expanded="true"', () => {
    const expandedSet = new Set(['tooling']);
    render(<SemanticTree {...defaultProps} expanded={expandedSet} />);

    const items = screen.getAllByRole('treeitem');
    const expandedItem = items.find((item) =>
      item.getAttribute('aria-label')?.includes('tooling folder')
    );

    if (expandedItem) {
      expect(expandedItem).toHaveAttribute('aria-expanded', 'true');
    }
  });

  it('collapsed folders have aria-expanded="false"', () => {
    render(<SemanticTree {...defaultProps} />);

    const items = screen.getAllByRole('treeitem');
    items.forEach((item) => {
      const hasExpanded = item.hasAttribute('aria-expanded');
      if (hasExpanded) {
        expect(item).toHaveAttribute('aria-expanded', 'false');
      }
    });
  });

  it('selected folder has aria-selected="true"', () => {
    render(<SemanticTree {...defaultProps} selectedFolder="tooling" />);

    const items = screen.getAllByRole('treeitem');
    const selectedItem = items.find((item) =>
      item.getAttribute('aria-label')?.includes('tooling folder')
    );

    if (selectedItem) {
      expect(selectedItem).toHaveAttribute('aria-selected', 'true');
    }
  });

  it('uses proper tree structure with groups', () => {
    const expandedSet = new Set(['tooling']);
    render(<SemanticTree {...defaultProps} expanded={expandedSet} />);

    const groups = document.querySelectorAll('[role="group"]');
    expect(groups.length).toBeGreaterThanOrEqual(1);
  });

  it('empty tree shows appropriate message outside tree role', () => {
    render(<SemanticTree {...defaultProps} tree={{}} />);
    expect(screen.getByText('No folders to display')).toBeInTheDocument();
    expect(screen.queryByRole('tree')).not.toBeInTheDocument();
  });
});

// ============================================================================
// TreeNode Tests
// ============================================================================

describe('TreeNode Accessibility', () => {
  const defaultProps = {
    name: 'test-folder',
    fullPath: 'test-folder',
    depth: 0,
    directCount: 3,
    totalCount: 10,
    hasDirectArtifacts: true,
    hasSubfolders: true,
    isSelected: false,
    isExpanded: false,
    isFocused: false,
    onSelect: jest.fn(),
    onToggleExpand: jest.fn(),
    onFocus: jest.fn(),
    siblingCount: 2,
    positionInSet: 1,
  };

  // Wrapper component to provide required tree parent context for axe
  const TreeNodeWithWrapper = (props: typeof defaultProps) => (
    <div role="tree" aria-label="Test tree">
      <TreeNode {...props} />
    </div>
  );

  it('should have no accessibility violations', async () => {
    const { container } = render(<TreeNodeWithWrapper {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has correct role and ARIA attributes', () => {
    render(<TreeNode {...defaultProps} />);
    const item = screen.getByRole('treeitem');

    expect(item).toHaveAttribute('aria-level', '1');
    expect(item).toHaveAttribute('aria-setsize', '2');
    expect(item).toHaveAttribute('aria-posinset', '1');
    expect(item).toHaveAttribute('aria-expanded', 'false');
    expect(item).toHaveAttribute('aria-selected', 'false');
  });

  it('aria-label includes folder name and counts', () => {
    render(<TreeNode {...defaultProps} />);
    const item = screen.getByRole('treeitem');
    const ariaLabel = item.getAttribute('aria-label');

    expect(ariaLabel).toContain('test-folder folder');
    expect(ariaLabel).toContain('3 direct artifacts');
    expect(ariaLabel).toContain('10 total descendants');
    expect(ariaLabel).toContain('collapsed');
  });

  it('aria-expanded is not present when no subfolders', () => {
    render(<TreeNode {...defaultProps} hasSubfolders={false} />);
    const item = screen.getByRole('treeitem');

    expect(item).not.toHaveAttribute('aria-expanded');
  });

  it('expand/collapse button has aria-label', () => {
    render(<TreeNode {...defaultProps} />);
    const expandButton = screen.getByRole('button', { name: /expand folder|collapse folder/i });
    expect(expandButton).toBeInTheDocument();
  });

  it('badge is hidden from screen readers', () => {
    render(<TreeNode {...defaultProps} />);
    const badge = document.querySelector('[aria-hidden="true"]');
    expect(badge).toBeInTheDocument();
  });

  it('focused node has tabIndex=0', () => {
    render(<TreeNode {...defaultProps} isFocused={true} />);
    const item = screen.getByRole('treeitem');
    expect(item).toHaveAttribute('tabIndex', '0');
  });

  it('unfocused node has tabIndex=-1', () => {
    render(<TreeNode {...defaultProps} isFocused={false} />);
    const item = screen.getByRole('treeitem');
    expect(item).toHaveAttribute('tabIndex', '-1');
  });

  it('handles singular artifact count correctly', () => {
    render(<TreeNode {...defaultProps} directCount={1} totalCount={1} />);
    const item = screen.getByRole('treeitem');
    const ariaLabel = item.getAttribute('aria-label');

    expect(ariaLabel).toContain('1 direct artifact');
    expect(ariaLabel).toContain('1 total descendant');
    expect(ariaLabel).not.toContain('1 direct artifacts');
  });
});

// ============================================================================
// FolderDetailPane Tests
// ============================================================================

describe('FolderDetailPane Accessibility', () => {
  const mockFolder = createMockFolderNode('test-folder', 'test-folder', {
    hasDirectArtifacts: true,
    directCount: 2,
    totalArtifactCount: 5,
  });

  const mockCatalog = [
    createMockCatalogEntry('1', 'test-folder/skill-1'),
    createMockCatalogEntry('2', 'test-folder/skill-2'),
  ];

  const defaultProps = {
    folder: mockFolder,
    catalog: mockCatalog,
    filters: mockFilters,
    onImport: jest.fn(),
    onExclude: jest.fn(),
    onImportAll: jest.fn(),
    onSelectSubfolder: jest.fn(),
  };

  it('should have no accessibility violations', async () => {
    const { container } = render(<FolderDetailPane {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has role="region" with descriptive aria-label', () => {
    render(<FolderDetailPane {...defaultProps} />);
    const region = screen.getByRole('region');

    expect(region).toHaveAttribute('aria-label', 'test-folder folder details');
  });

  it('has aria-live="polite" for content updates', () => {
    render(<FolderDetailPane {...defaultProps} />);
    const region = screen.getByRole('region');

    expect(region).toHaveAttribute('aria-live', 'polite');
  });

  it('empty state has accessible region', () => {
    render(<FolderDetailPane {...defaultProps} folder={null} />);
    const region = screen.getByRole('region');

    expect(region).toHaveAttribute('aria-label', 'Folder details');
    expect(screen.getByText('Select a folder to view its contents')).toBeInTheDocument();
  });

  it('heading structure is correct', () => {
    render(<FolderDetailPane {...defaultProps} />);
    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toHaveTextContent('test-folder');
  });
});

// ============================================================================
// SubfoldersSection Tests
// ============================================================================

describe('SubfoldersSection Accessibility', () => {
  const mockSubfolders = [
    createMockFolderNode('subfolder-1', 'parent/subfolder-1', { totalArtifactCount: 3 }),
    createMockFolderNode('subfolder-2', 'parent/subfolder-2', { totalArtifactCount: 5 }),
  ];

  const defaultProps = {
    subfolders: mockSubfolders,
    onSelectFolder: jest.fn(),
  };

  it('should have no accessibility violations', async () => {
    const { container } = render(<SubfoldersSection {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has role="region" with count in aria-label', () => {
    render(<SubfoldersSection {...defaultProps} />);
    const region = screen.getByRole('region');

    expect(region).toHaveAttribute('aria-label', 'Subfolders, 2 folders');
  });

  it('singular folder count in aria-label', () => {
    render(<SubfoldersSection {...defaultProps} subfolders={[mockSubfolders[0]]} />);
    const region = screen.getByRole('region');

    expect(region).toHaveAttribute('aria-label', 'Subfolders, 1 folder');
  });

  it('uses list pattern for subfolder cards', () => {
    render(<SubfoldersSection {...defaultProps} />);

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('list is labeled by heading', () => {
    render(<SubfoldersSection {...defaultProps} />);
    const list = screen.getByRole('list');

    expect(list).toHaveAttribute('aria-labelledby', 'subfolders-heading');
  });

  it('count badge is hidden from screen readers', () => {
    render(<SubfoldersSection {...defaultProps} />);
    const countSpan = screen.getByText('(2)');
    expect(countSpan).toHaveAttribute('aria-hidden', 'true');
  });

  it('returns null for empty subfolders', () => {
    const { container } = render(<SubfoldersSection {...defaultProps} subfolders={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

// ============================================================================
// SubfolderCard Tests
// ============================================================================

describe('SubfolderCard Accessibility', () => {
  const mockFolder = createMockFolderNode('my-folder', 'parent/my-folder', {
    totalArtifactCount: 7,
  });

  const defaultProps = {
    folder: mockFolder,
    onSelect: jest.fn(),
  };

  it('should have no accessibility violations', async () => {
    const { container } = render(<SubfolderCard {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has role="button" with descriptive aria-label', () => {
    render(<SubfolderCard {...defaultProps} />);
    const button = screen.getByRole('button');

    expect(button).toHaveAttribute('aria-label', 'Open my-folder folder with 7 artifacts');
  });

  it('singular artifact in aria-label', () => {
    const singleArtifactFolder = createMockFolderNode('single', 'parent/single', {
      totalArtifactCount: 1,
    });
    render(<SubfolderCard folder={singleArtifactFolder} onSelect={jest.fn()} />);
    const button = screen.getByRole('button');

    expect(button).toHaveAttribute('aria-label', 'Open single folder with 1 artifact');
  });

  it('is keyboard accessible', async () => {
    const user = userEvent.setup();
    const onSelect = jest.fn();
    render(<SubfolderCard {...defaultProps} onSelect={onSelect} />);

    const button = screen.getByRole('button');
    button.focus();
    expect(button).toHaveFocus();

    await user.keyboard('{Enter}');
    expect(onSelect).toHaveBeenCalledWith('parent/my-folder');
  });

  it('has visible focus indicator', () => {
    render(<SubfolderCard {...defaultProps} />);
    const button = screen.getByRole('button');

    expect(button.className).toContain('focus-visible:');
  });
});

// ============================================================================
// ArtifactTypeSection Tests
// ============================================================================

describe('ArtifactTypeSection Accessibility', () => {
  const mockArtifacts = [
    createMockCatalogEntry('1', 'folder/skill-1'),
    createMockCatalogEntry('2', 'folder/skill-2'),
  ];

  const defaultProps = {
    type: 'skill' as const,
    artifacts: mockArtifacts,
    defaultExpanded: false,
    onImport: jest.fn(),
    onExclude: jest.fn(),
  };

  it('should have no accessibility violations', async () => {
    const { container } = render(<ArtifactTypeSection {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('collapsible trigger has aria-expanded', () => {
    render(<ArtifactTypeSection {...defaultProps} />);
    const trigger = screen.getByRole('button');

    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  it('expanded state updates aria-expanded', async () => {
    const user = userEvent.setup();
    render(<ArtifactTypeSection {...defaultProps} />);

    const trigger = screen.getByRole('button');
    await user.click(trigger);

    expect(trigger).toHaveAttribute('aria-expanded', 'true');
  });

  it('trigger has descriptive aria-label with count', () => {
    render(<ArtifactTypeSection {...defaultProps} />);
    const trigger = screen.getByRole('button');
    const ariaLabel = trigger.getAttribute('aria-label');

    expect(ariaLabel).toContain('Expand Skills section');
    expect(ariaLabel).toContain('2 items');
  });

  it('count badge is hidden from screen readers', () => {
    render(<ArtifactTypeSection {...defaultProps} />);
    const countBadge = screen.getByText('(2)');

    expect(countBadge).toHaveAttribute('aria-hidden', 'true');
  });

  it('action buttons have aria-labels', () => {
    render(<ArtifactTypeSection {...defaultProps} defaultExpanded={true} />);

    const importButtons = screen.getAllByRole('button', { name: /import/i });
    const excludeButtons = screen.getAllByRole('button', { name: /exclude/i });

    expect(importButtons.length).toBeGreaterThanOrEqual(1);
    expect(excludeButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('returns null for empty artifacts', () => {
    const { container } = render(<ArtifactTypeSection {...defaultProps} artifacts={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

// ============================================================================
// Keyboard Navigation Integration Tests
// ============================================================================

describe('Folder View Keyboard Navigation', () => {
  it('tree supports arrow key navigation', async () => {
    const user = userEvent.setup();
    const onSelectFolder = jest.fn();

    render(
      <SemanticTree
        tree={createUnfilteredMockTree()}
        selectedFolder={null}
        expanded={new Set()}
        onSelectFolder={onSelectFolder}
        onToggleExpand={jest.fn()}
      />
    );

    const firstItem = screen.getAllByRole('treeitem')[0];

    firstItem.focus();
    expect(firstItem).toHaveFocus();

    await user.keyboard('{ArrowDown}');
    await user.keyboard('{Enter}');
    expect(onSelectFolder).toHaveBeenCalled();
  });

  it('subfolder card is focusable', async () => {
    const user = userEvent.setup();
    const folder = createMockFolderNode('test', 'parent/test');

    render(<SubfolderCard folder={folder} onSelect={jest.fn()} />);

    const card = screen.getByRole('button');
    await user.tab();

    expect(card).toHaveFocus();
  });
});

// ============================================================================
// Focus Management Tests
// ============================================================================

describe('Focus Management Between Panes', () => {
  it('TreeNode has visible focus ring classes', () => {
    render(
      <TreeNode
        name="test"
        fullPath="test"
        depth={0}
        directCount={1}
        totalCount={1}
        hasDirectArtifacts={true}
        hasSubfolders={false}
        isSelected={false}
        isExpanded={false}
        isFocused={true}
        onSelect={jest.fn()}
        onToggleExpand={jest.fn()}
        onFocus={jest.fn()}
        siblingCount={1}
        positionInSet={1}
      />
    );

    const item = screen.getByRole('treeitem');
    expect(item.className).toContain('focus-visible:ring-2');
    expect(item.className).toContain('focus-visible:ring-ring');
  });

  it('SubfolderCard has visible focus ring classes', () => {
    const folder = createMockFolderNode('test', 'parent/test');
    render(<SubfolderCard folder={folder} onSelect={jest.fn()} />);

    const card = screen.getByRole('button');
    expect(card.className).toContain('focus-visible:ring-2');
    expect(card.className).toContain('focus-visible:ring-ring');
  });

  it('tree is single tab stop with roving tabindex', () => {
    render(
      <SemanticTree
        tree={createUnfilteredMockTree()}
        selectedFolder={null}
        expanded={new Set(['tooling'])}
        onSelectFolder={jest.fn()}
        onToggleExpand={jest.fn()}
      />
    );

    const items = screen.getAllByRole('treeitem');

    const tabbableItems = items.filter((item) => item.getAttribute('tabIndex') === '0');
    const untabbableItems = items.filter((item) => item.getAttribute('tabIndex') === '-1');

    expect(tabbableItems).toHaveLength(1);
    expect(untabbableItems.length).toBe(items.length - 1);
  });
});

// ============================================================================
// Live Region Tests
// ============================================================================

describe('Live Regions', () => {
  it('folder detail pane has polite live region', () => {
    const folder = createMockFolderNode('test', 'test');
    render(
      <FolderDetailPane
        folder={folder}
        catalog={[]}
        filters={mockFilters}
        onImport={jest.fn()}
        onExclude={jest.fn()}
        onImportAll={jest.fn()}
        onSelectSubfolder={jest.fn()}
      />
    );

    const region = screen.getByRole('region');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });

  it('live region container persists on folder change', () => {
    const folder1 = createMockFolderNode('folder-1', 'folder-1');
    const folder2 = createMockFolderNode('folder-2', 'folder-2');

    const { rerender } = render(
      <FolderDetailPane
        folder={folder1}
        catalog={[]}
        filters={mockFilters}
        onImport={jest.fn()}
        onExclude={jest.fn()}
        onImportAll={jest.fn()}
        onSelectSubfolder={jest.fn()}
      />
    );

    rerender(
      <FolderDetailPane
        folder={folder2}
        catalog={[]}
        filters={mockFilters}
        onImport={jest.fn()}
        onExclude={jest.fn()}
        onImportAll={jest.fn()}
        onSelectSubfolder={jest.fn()}
      />
    );

    const region = screen.getByRole('region');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });
});
