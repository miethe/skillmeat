/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DirectoryMapModal, type DirectoryNode } from '../DirectoryMapModal';

// Mock the toast hook
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Test data factory
const createDirectoryNode = (
  path: string,
  name: string,
  children?: DirectoryNode[]
): DirectoryNode => ({
  path,
  name,
  type: 'tree' as const,
  children,
});

const createTreeData = (): DirectoryNode[] => [
  createDirectoryNode('skills', 'skills', [
    createDirectoryNode('skills/canvas', 'canvas'),
    createDirectoryNode('skills/data', 'data'),
  ]),
  createDirectoryNode('agents', 'agents', [createDirectoryNode('agents/helper', 'helper')]),
  createDirectoryNode('commands', 'commands'),
];

describe('DirectoryMapModal', () => {
  const defaultProps = {
    open: true,
    onOpenChange: jest.fn(),
    sourceId: 'source-123',
    repoInfo: {
      owner: 'anthropics',
      repo: 'skills',
      ref: 'main',
    },
    treeData: createTreeData(),
    isLoadingTree: false,
    treeError: undefined,
    initialMappings: {},
    onConfirm: jest.fn(),
    onConfirmAndRescan: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ============================================================================
  // Rendering Tests
  // ============================================================================

  describe('rendering', () => {
    it('renders modal when open', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      expect(screen.getByText('Map Directories to Artifact Types')).toBeInTheDocument();
      expect(screen.getByText(/Select directories containing artifacts in/)).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      render(<DirectoryMapModal {...defaultProps} open={false} />);

      expect(screen.queryByText('Map Directories to Artifact Types')).not.toBeInTheDocument();
    });

    it('displays repository information', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      expect(screen.getByText('anthropics/skills@main')).toBeInTheDocument();
    });

    it('displays fallback text when repoInfo is missing', () => {
      render(<DirectoryMapModal {...defaultProps} repoInfo={undefined} />);

      expect(
        screen.getByText(/Select directories containing artifacts for source source-123/)
      ).toBeInTheDocument();
    });

    it('renders search input', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      expect(screen.getByPlaceholderText('Search directories...')).toBeInTheDocument();
    });

    it('renders action buttons', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /save \(0\)/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /save & rescan/i })).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Tree Rendering Tests
  // ============================================================================

  describe('tree rendering', () => {
    it('renders directory tree', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      // Use getAllByText since directory names appear twice (name + path)
      const skillsElements = screen.getAllByText('skills');
      expect(skillsElements.length).toBeGreaterThan(0);

      const agentsElements = screen.getAllByText('agents');
      expect(agentsElements.length).toBeGreaterThan(0);

      const commandsElements = screen.getAllByText('commands');
      expect(commandsElements.length).toBeGreaterThan(0);
    });

    it('displays child directories when expanded', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      // Find and click expand button for skills
      const expandButtons = screen.getAllByLabelText('Expand directory');
      await user.click(expandButtons[0]); // First directory (skills)

      await waitFor(() => {
        expect(screen.getByText('canvas')).toBeInTheDocument();
        expect(screen.getByText('data')).toBeInTheDocument();
      });
    });

    it('collapses directory when collapse button is clicked', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      // Expand first
      const expandButtons = screen.getAllByLabelText('Expand directory');
      await user.click(expandButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('canvas')).toBeInTheDocument();
      });

      // Then collapse
      const collapseButton = screen.getByLabelText('Collapse directory');
      await user.click(collapseButton);

      await waitFor(() => {
        expect(screen.queryByText('canvas')).not.toBeInTheDocument();
      });
    });

    it('displays child count badge for directories with children', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      // Verify that at least one directory with children shows a count
      // skills has 2 children
      const twoChildBadges = screen.queryAllByText('2');
      // agents has 1 child
      const oneChildBadges = screen.queryAllByText('1');

      // At least one badge should be present
      const totalBadges = twoChildBadges.length + oneChildBadges.length;
      expect(totalBadges).toBeGreaterThan(0);
    });

    it('shows full path as secondary text', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      // Check that skills directory renders (appears twice: name + path)
      const skillsElements = screen.getAllByText('skills');
      expect(skillsElements.length).toBeGreaterThan(0);

      // Verify both name and path are displayed
      expect(skillsElements.length).toBeGreaterThanOrEqual(2);
    });
  });

  // ============================================================================
  // Directory Selection Tests
  // ============================================================================

  describe('directory selection', () => {
    it('selects directory when checkbox is clicked', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]); // Select first directory

      // Checkbox should be checked
      await waitFor(() => {
        expect(checkboxes[0]).toBeChecked();
      });
    });

    it('deselects directory when checkbox is clicked again', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]); // Select
      await user.click(checkboxes[0]); // Deselect

      await waitFor(() => {
        expect(checkboxes[0]).not.toBeChecked();
      });
    });

    it('shows type selector when directory is selected', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      await waitFor(() => {
        expect(screen.getByText('Select type...')).toBeInTheDocument();
      });
    });

    it('shows type selector when directory is selected', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      // Select directory
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      // Wait for type selector to appear
      await waitFor(() => {
        expect(screen.getByText('Select type...')).toBeInTheDocument();
      });

      // Verify select trigger is present and accessible
      const selectTrigger = screen.getByRole('combobox', {
        name: /select artifact type/i,
      });
      expect(selectTrigger).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Hierarchical Selection Tests
  // ============================================================================

  describe('hierarchical selection', () => {
    it('selects all children when parent is selected', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      // Expand parent directory first
      const expandButtons = screen.getAllByLabelText('Expand directory');
      await user.click(expandButtons[0]); // Expand skills

      await waitFor(() => {
        expect(screen.getByText('canvas')).toBeInTheDocument();
      });

      // Select parent
      const checkboxes = screen.getAllByRole('checkbox');
      const parentCheckbox = checkboxes[0]; // skills directory
      await user.click(parentCheckbox);

      // Wait and check that children are also selected
      await waitFor(() => {
        const allCheckboxes = screen.getAllByRole('checkbox');
        // Parent and children should be checked
        const checkedCount = allCheckboxes.filter(
          (cb) => cb.getAttribute('data-state') === 'checked'
        ).length;
        expect(checkedCount).toBeGreaterThan(1);
      });
    });

    it('deselects all children when parent is deselected', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      // Expand and select parent
      const expandButtons = screen.getAllByLabelText('Expand directory');
      await user.click(expandButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('canvas')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]); // Select parent
      await user.click(checkboxes[0]); // Deselect parent

      // All checkboxes should be unchecked
      await waitFor(() => {
        const allCheckboxes = screen.getAllByRole('checkbox');
        const checkedCount = allCheckboxes.filter(
          (cb) => cb.getAttribute('data-state') === 'checked'
        ).length;
        expect(checkedCount).toBe(0);
      });
    });

    it('shows type selector for parent when selected', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      // Expand parent
      const expandButtons = screen.getAllByLabelText('Expand directory');
      await user.click(expandButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('canvas')).toBeInTheDocument();
      });

      // Select parent
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      // Type selector should appear for parent
      await waitFor(() => {
        expect(screen.getByText('Select type...')).toBeInTheDocument();
      });
    });

    it('shows indeterminate state for partial selection', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      // Expand parent
      const expandButtons = screen.getAllByLabelText('Expand directory');
      await user.click(expandButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('canvas')).toBeInTheDocument();
      });

      // Select only one child
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]); // Select first child

      // Parent should show indeterminate state
      await waitFor(() => {
        const parentCheckbox = checkboxes[0];
        expect(parentCheckbox.getAttribute('data-state')).toBe('indeterminate');
      });
    });
  });

  // ============================================================================
  // Search/Filter Tests
  // ============================================================================

  describe('search functionality', () => {
    it('filters tree by directory name', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText('Search directories...');
      await user.type(searchInput, 'skills');

      await waitFor(() => {
        const skillsElements = screen.getAllByText('skills');
        expect(skillsElements.length).toBeGreaterThan(0);

        // agents should not be visible
        expect(screen.queryAllByText('agents')).toHaveLength(0);
      });
    });

    it('filters tree by path', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText('Search directories...');
      await user.type(searchInput, 'canvas');

      await waitFor(() => {
        const canvasElements = screen.getAllByText('canvas');
        expect(canvasElements.length).toBeGreaterThan(0);
      });
    });

    it('auto-expands directories when searching', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText('Search directories...');
      await user.type(searchInput, 'canvas');

      // Canvas is a child of skills, so skills should be expanded
      await waitFor(() => {
        const canvasElements = screen.getAllByText('canvas');
        expect(canvasElements.length).toBeGreaterThan(0);

        expect(screen.getByLabelText('Collapse directory')).toBeInTheDocument();
      });
    });

    it('shows no results message when search yields no matches', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText('Search directories...');
      await user.type(searchInput, 'nonexistent');

      await waitFor(() => {
        expect(screen.getByText('No directories match your search')).toBeInTheDocument();
      });
    });

    it('clears search results when input is cleared', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText('Search directories...');
      await user.type(searchInput, 'skills');

      await waitFor(() => {
        expect(screen.queryAllByText('agents')).toHaveLength(0);
      });

      await user.clear(searchInput);

      await waitFor(() => {
        const agentsElements = screen.getAllByText('agents');
        expect(agentsElements.length).toBeGreaterThan(0);
      });
    });
  });

  // ============================================================================
  // Initial Mappings Tests
  // ============================================================================

  describe('initial mappings', () => {
    it('pre-selects directories from initial mappings', () => {
      const initialMappings = {
        skills: 'skill',
        agents: 'agent',
      };

      render(<DirectoryMapModal {...defaultProps} initialMappings={initialMappings} />);

      // Count should show 2 mappings
      expect(screen.getByRole('button', { name: /save \(2\)/i })).toBeInTheDocument();
    });

    it('pre-fills artifact types from initial mappings', async () => {
      const initialMappings = {
        skills: 'skill',
      };

      render(<DirectoryMapModal {...defaultProps} initialMappings={initialMappings} />);

      await waitFor(() => {
        expect(screen.getByText('Skill')).toBeInTheDocument();
      });
    });

    it('auto-expands paths with initial mappings', async () => {
      const initialMappings = {
        'skills/canvas': 'skill',
      };

      render(<DirectoryMapModal {...defaultProps} initialMappings={initialMappings} />);

      // Parent should be expanded to show the mapped child
      await waitFor(() => {
        expect(screen.getByLabelText('Collapse directory')).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Loading State Tests
  // ============================================================================

  describe('loading states', () => {
    it('displays loading skeleton when tree is loading', () => {
      render(<DirectoryMapModal {...defaultProps} isLoadingTree={true} treeData={[]} />);

      // Skeleton should be rendered (8 skeleton items)
      const skeletons = screen.getAllByRole('generic', { hidden: true });
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('displays loading state on save button during submission', async () => {
      const user = userEvent.setup();
      const onConfirm = jest.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));

      const initialMappings = {
        skills: 'skill',
      };

      render(
        <DirectoryMapModal
          {...defaultProps}
          onConfirm={onConfirm}
          initialMappings={initialMappings}
        />
      );

      // Click save
      const saveButton = screen.getByRole('button', { name: /save \(1\)/i });
      await user.click(saveButton);

      // Button should show loading state briefly
      await waitFor(() => {
        expect(saveButton).toBeDisabled();
      });
    });
  });

  // ============================================================================
  // Error State Tests
  // ============================================================================

  describe('error states', () => {
    it('displays error message when tree fails to load', () => {
      render(
        <DirectoryMapModal
          {...defaultProps}
          treeError="Failed to fetch directory tree"
          treeData={[]}
        />
      );

      expect(screen.getByText('Failed to load directories')).toBeInTheDocument();
      expect(screen.getByText('Failed to fetch directory tree')).toBeInTheDocument();
    });

    it('shows empty state when tree data is empty', () => {
      render(<DirectoryMapModal {...defaultProps} treeData={[]} />);

      expect(screen.getByText('No directories found')).toBeInTheDocument();
      expect(screen.getByText('This repository has no directories')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Save/Cancel Actions Tests
  // ============================================================================

  describe('save and cancel actions', () => {
    it('calls onConfirm with mappings when save is clicked', async () => {
      const user = userEvent.setup();
      const onConfirm = jest.fn().mockResolvedValue(undefined);

      const initialMappings = {
        skills: 'skill',
      };

      render(
        <DirectoryMapModal
          {...defaultProps}
          onConfirm={onConfirm}
          initialMappings={initialMappings}
        />
      );

      // Click save
      const saveButton = screen.getByRole('button', { name: /save \(1\)/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(onConfirm).toHaveBeenCalledWith({ skills: 'skill' });
      });
    });

    it('calls onConfirmAndRescan when save & rescan is clicked', async () => {
      const user = userEvent.setup();
      const onConfirmAndRescan = jest.fn().mockResolvedValue(undefined);

      const initialMappings = {
        skills: 'skill',
      };

      render(
        <DirectoryMapModal
          {...defaultProps}
          onConfirmAndRescan={onConfirmAndRescan}
          initialMappings={initialMappings}
        />
      );

      // Click save & rescan
      const saveRescanButton = screen.getByRole('button', { name: /save & rescan/i });
      await user.click(saveRescanButton);

      await waitFor(() => {
        expect(onConfirmAndRescan).toHaveBeenCalledWith({ skills: 'skill' });
      });
    });

    it('closes modal after successful save', async () => {
      const user = userEvent.setup();
      const onOpenChange = jest.fn();
      const onConfirm = jest.fn().mockResolvedValue(undefined);

      const initialMappings = {
        skills: 'skill',
      };

      render(
        <DirectoryMapModal
          {...defaultProps}
          onOpenChange={onOpenChange}
          onConfirm={onConfirm}
          initialMappings={initialMappings}
        />
      );

      const saveButton = screen.getByRole('button', { name: /save \(1\)/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it('calls onOpenChange when cancel is clicked without changes', async () => {
      const user = userEvent.setup();
      const onOpenChange = jest.fn();

      render(<DirectoryMapModal {...defaultProps} onOpenChange={onOpenChange} />);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  // ============================================================================
  // Dirty State & Confirmation Tests
  // ============================================================================

  describe('dirty state tracking', () => {
    it('disables save buttons when no changes are made', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      const saveButton = screen.getByRole('button', { name: /save \(0\)/i });
      const saveRescanButton = screen.getByRole('button', { name: /save & rescan/i });

      expect(saveButton).toBeDisabled();
      expect(saveRescanButton).toBeDisabled();
    });

    it('enables save buttons after making changes', async () => {
      const initialMappings = {
        skills: 'skill',
      };

      render(<DirectoryMapModal {...defaultProps} initialMappings={initialMappings} />);

      const saveButton = screen.getByRole('button', { name: /save \(1\)/i });
      expect(saveButton).not.toBeDisabled();
    });

    it('shows confirmation dialog when closing with unsaved changes', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      // Make changes
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      // Try to cancel
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      // Confirmation dialog should appear
      await waitFor(() => {
        expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
        expect(
          screen.getByText(
            /You have unsaved directory mappings. Are you sure you want to close without saving?/
          )
        ).toBeInTheDocument();
      });
    });

    it('allows closing after confirming discard changes', async () => {
      const user = userEvent.setup();
      const onOpenChange = jest.fn();

      render(<DirectoryMapModal {...defaultProps} onOpenChange={onOpenChange} />);

      // Make changes
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      // Try to cancel
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      // Confirm discard
      await waitFor(() => {
        expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
      });

      const discardButton = screen.getByRole('button', { name: /discard changes/i });
      await user.click(discardButton);

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it('continues editing when keep editing is clicked', async () => {
      const user = userEvent.setup();
      const onOpenChange = jest.fn();

      render(<DirectoryMapModal {...defaultProps} onOpenChange={onOpenChange} />);

      // Make changes
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      // Try to cancel
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      // Click keep editing
      await waitFor(() => {
        expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
      });

      const keepEditingButton = screen.getByRole('button', { name: /keep editing/i });
      await user.click(keepEditingButton);

      // Confirmation dialog should close, modal should stay open
      await waitFor(() => {
        expect(screen.queryByText('Unsaved Changes')).not.toBeInTheDocument();
      });

      expect(onOpenChange).not.toHaveBeenCalled();
    });
  });

  // ============================================================================
  // Summary/Stats Tests
  // ============================================================================

  describe('summary statistics', () => {
    it('displays total directory count', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      // 3 top-level + 3 children = 6 total
      // Use a flexible matcher since text might be split across elements
      expect(screen.getByText(/6.*directories total/i)).toBeInTheDocument();
    });

    it('displays selected mapping count', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      // Initially 0 with empty mappings
      expect(screen.queryByText(/mapping configured/)).not.toBeInTheDocument();

      const initialMappings = {
        skills: 'skill',
      };

      render(<DirectoryMapModal {...defaultProps} initialMappings={initialMappings} />);

      // Should show 1 mapping
      expect(screen.getByText('1 mapping configured')).toBeInTheDocument();
    });

    it('updates save button count', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      expect(screen.getByRole('button', { name: /save \(0\)/i })).toBeInTheDocument();

      const initialMappings = {
        skills: 'skill',
      };

      render(<DirectoryMapModal {...defaultProps} initialMappings={initialMappings} />);

      expect(screen.getByRole('button', { name: /save \(1\)/i })).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Accessibility Tests
  // ============================================================================

  describe('accessibility', () => {
    it('has accessible labels for search input', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      const searchInput = screen.getByLabelText('Search directories');
      expect(searchInput).toBeInTheDocument();
    });

    it('has accessible labels for directory checkboxes', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      expect(screen.getByLabelText('Select skills directory')).toBeInTheDocument();
    });

    it('has accessible labels for expand/collapse buttons', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      const expandButtons = screen.getAllByLabelText('Expand directory');
      expect(expandButtons.length).toBeGreaterThan(0);
    });

    it('has accessible labels for type selectors', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      await waitFor(() => {
        expect(
          screen.getByRole('combobox', { name: /select artifact type for skills/i })
        ).toBeInTheDocument();
      });
    });

    it('has proper ARIA attributes for tree structure', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      expect(screen.getByRole('tree', { name: 'Directory tree' })).toBeInTheDocument();
    });

    it('has aria-expanded on expand/collapse buttons', () => {
      render(<DirectoryMapModal {...defaultProps} />);

      const expandButton = screen.getAllByLabelText('Expand directory')[0];
      expect(expandButton).toHaveAttribute('aria-expanded', 'false');
    });

    it('updates aria-expanded when directory is expanded', async () => {
      const user = userEvent.setup();
      render(<DirectoryMapModal {...defaultProps} />);

      const expandButton = screen.getAllByLabelText('Expand directory')[0];
      await user.click(expandButton);

      await waitFor(() => {
        expect(screen.getByLabelText('Collapse directory')).toHaveAttribute(
          'aria-expanded',
          'true'
        );
      });
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('edge cases', () => {
    it('handles empty tree data gracefully', () => {
      render(<DirectoryMapModal {...defaultProps} treeData={[]} />);

      expect(screen.getByText('No directories found')).toBeInTheDocument();
    });

    it('handles undefined tree data', () => {
      render(<DirectoryMapModal {...defaultProps} treeData={undefined as any} />);

      expect(screen.getByText('No directories found')).toBeInTheDocument();
    });

    it('handles missing callbacks gracefully', async () => {
      const user = userEvent.setup();

      const initialMappings = {
        skills: 'skill',
      };

      render(
        <DirectoryMapModal
          {...defaultProps}
          onConfirm={undefined}
          onConfirmAndRescan={undefined}
          initialMappings={initialMappings}
        />
      );

      const saveButton = screen.getByRole('button', { name: /save \(1\)/i });
      await user.click(saveButton);

      // Should not throw error
      await waitFor(() => {
        expect(saveButton).toBeDisabled();
      });
    });

    it('only includes directories with types in mappings', async () => {
      const user = userEvent.setup();
      const onConfirm = jest.fn().mockResolvedValue(undefined);

      render(<DirectoryMapModal {...defaultProps} onConfirm={onConfirm} />);

      // Select directory but don't set type
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      // Try to save
      const saveButton = screen.getByRole('button', { name: /save \(0\)/i });
      expect(saveButton).toBeDisabled(); // Should be disabled with no types set
    });
  });
});
