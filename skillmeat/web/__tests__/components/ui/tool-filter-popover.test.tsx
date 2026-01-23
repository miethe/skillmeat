/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToolFilterPopover, ToolFilterBar } from '@/components/ui/tool-filter-popover';
import { Tool } from '@/types/enums';

describe('ToolFilterPopover', () => {
  describe('Rendering', () => {
    it('renders trigger button with Tools label', () => {
      render(<ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />);

      expect(screen.getByRole('button', { name: /Tools/i })).toBeInTheDocument();
    });

    it('renders Wrench icon in trigger button', () => {
      const { container } = render(
        <ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />
      );

      // Check for SVG icon
      const button = screen.getByRole('button');
      const icon = button.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('does not show badge when no tools selected', () => {
      render(<ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />);

      // Badge should not exist
      expect(screen.queryByText('0')).not.toBeInTheDocument();
    });

    it('shows badge with count when tools are selected', () => {
      render(
        <ToolFilterPopover
          selectedTools={['Read', 'Write', 'Edit']}
          onChange={jest.fn()}
        />
      );

      // Badge should show count
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  describe('Popover Open/Close', () => {
    it('opens popover when button is clicked', async () => {
      const user = userEvent.setup();
      render(<ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />);

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      // Popover content should be visible
      expect(screen.getByText('Filter by tools')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Search tools...')).toBeInTheDocument();
    });

    it('closes popover when clicking outside', async () => {
      const user = userEvent.setup();
      render(
        <div>
          <ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />
          <div data-testid="outside">Outside</div>
        </div>
      );

      // Open popover
      await user.click(screen.getByRole('button', { name: /Tools/i }));
      expect(screen.getByText('Filter by tools')).toBeInTheDocument();

      // Click outside
      await user.click(screen.getByTestId('outside'));

      // Popover should close
      await waitFor(() => {
        expect(screen.queryByText('Filter by tools')).not.toBeInTheDocument();
      });
    });
  });

  describe('Tools List', () => {
    it('displays all known tools when no availableTools provided', async () => {
      const user = userEvent.setup();
      render(<ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />);

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      // Check for known tools from Tool enum
      expect(screen.getByText('Read')).toBeInTheDocument();
      expect(screen.getByText('Write')).toBeInTheDocument();
      expect(screen.getByText('Edit')).toBeInTheDocument();
      expect(screen.getByText('Bash')).toBeInTheDocument();
      expect(screen.getByText('Grep')).toBeInTheDocument();
      expect(screen.getByText('Glob')).toBeInTheDocument();
    });

    it('displays custom availableTools when provided', async () => {
      const user = userEvent.setup();
      const customTools = [
        { name: 'CustomTool1', artifact_count: 5 },
        { name: 'CustomTool2', artifact_count: 10 },
      ];

      render(
        <ToolFilterPopover
          selectedTools={[]}
          onChange={jest.fn()}
          availableTools={customTools}
        />
      );

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      expect(screen.getByText('CustomTool1')).toBeInTheDocument();
      expect(screen.getByText('CustomTool2')).toBeInTheDocument();
      // Known tools should not appear
      expect(screen.queryByText('Read')).not.toBeInTheDocument();
    });

    it('displays artifact count when available', async () => {
      const user = userEvent.setup();
      const toolsWithCounts = [
        { name: 'Read', artifact_count: 15 },
        { name: 'Write', artifact_count: 8 },
        { name: 'Edit', artifact_count: 0 },
      ];

      render(
        <ToolFilterPopover
          selectedTools={[]}
          onChange={jest.fn()}
          availableTools={toolsWithCounts}
        />
      );

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      expect(screen.getByText('15')).toBeInTheDocument();
      expect(screen.getByText('8')).toBeInTheDocument();
      // Count of 0 should not be displayed
      expect(screen.queryByText('0')).not.toBeInTheDocument();
    });
  });

  describe('Checkbox Selection', () => {
    it('shows unchecked checkbox for unselected tools', async () => {
      const user = userEvent.setup();
      render(<ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />);

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      // Find the Read tool row - it should have an unchecked state
      const readRow = screen.getByText('Read').closest('div[class*="cursor-pointer"]');
      expect(readRow).toBeInTheDocument();

      // The checkbox indicator should not have the checked styling
      const checkbox = readRow?.querySelector('div[class*="border-input"]');
      expect(checkbox).toBeInTheDocument();
    });

    it('shows checked checkbox for selected tools', async () => {
      const user = userEvent.setup();
      render(
        <ToolFilterPopover selectedTools={['Read']} onChange={jest.fn()} />
      );

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      // Find the Read tool row - it should have a checked state
      const readRow = screen.getByText('Read').closest('div[class*="cursor-pointer"]');
      expect(readRow).toBeInTheDocument();

      // The checkbox indicator should have the checked styling
      const checkbox = readRow?.querySelector('div[class*="bg-primary"]');
      expect(checkbox).toBeInTheDocument();
    });

    it('calls onChange with added tool when clicking unchecked tool', async () => {
      const user = userEvent.setup();
      const handleChange = jest.fn();

      render(
        <ToolFilterPopover selectedTools={[]} onChange={handleChange} />
      );

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      // Click on Read tool row
      const readRow = screen.getByText('Read').closest('div[class*="cursor-pointer"]');
      await user.click(readRow!);

      expect(handleChange).toHaveBeenCalledWith(['Read']);
    });

    it('calls onChange with tool removed when clicking checked tool', async () => {
      const user = userEvent.setup();
      const handleChange = jest.fn();

      render(
        <ToolFilterPopover
          selectedTools={['Read', 'Write']}
          onChange={handleChange}
        />
      );

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      // Click on Read tool row to deselect
      const readRow = screen.getByText('Read').closest('div[class*="cursor-pointer"]');
      await user.click(readRow!);

      expect(handleChange).toHaveBeenCalledWith(['Write']);
    });

    it('updates badge count when selection changes', async () => {
      const { rerender } = render(
        <ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />
      );

      // Initially no badge
      expect(screen.queryByText('1')).not.toBeInTheDocument();

      // Update selection
      rerender(
        <ToolFilterPopover selectedTools={['Read']} onChange={jest.fn()} />
      );

      expect(screen.getByText('1')).toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    it('filters tools by search input', async () => {
      const user = userEvent.setup();
      render(<ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />);

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      // Type in search
      const searchInput = screen.getByPlaceholderText('Search tools...');
      await user.type(searchInput, 'read');

      // Only Read should be visible
      expect(screen.getByText('Read')).toBeInTheDocument();
      expect(screen.queryByText('Write')).not.toBeInTheDocument();
      expect(screen.queryByText('Bash')).not.toBeInTheDocument();
    });

    it('search is case insensitive', async () => {
      const user = userEvent.setup();
      render(<ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />);

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      const searchInput = screen.getByPlaceholderText('Search tools...');
      await user.type(searchInput, 'BASH');

      expect(screen.getByText('Bash')).toBeInTheDocument();
    });

    it('shows "No tools found" when search has no matches', async () => {
      const user = userEvent.setup();
      render(<ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />);

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      const searchInput = screen.getByPlaceholderText('Search tools...');
      await user.type(searchInput, 'nonexistenttool');

      expect(screen.getByText('No tools found')).toBeInTheDocument();
    });

    it('clears search when Clear all is clicked', async () => {
      const user = userEvent.setup();
      const handleChange = jest.fn();

      render(
        <ToolFilterPopover
          selectedTools={['Read', 'Write']}
          onChange={handleChange}
        />
      );

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      // Type in search
      const searchInput = screen.getByPlaceholderText('Search tools...');
      await user.type(searchInput, 'test');

      // Click Clear all
      await user.click(screen.getByRole('button', { name: /Clear all/i }));

      // Search should be cleared
      expect(searchInput).toHaveValue('');
    });
  });

  describe('Clear All Button', () => {
    it('shows Clear all button only when tools are selected', async () => {
      const user = userEvent.setup();
      render(<ToolFilterPopover selectedTools={[]} onChange={jest.fn()} />);

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      // Clear all should not be visible
      expect(screen.queryByRole('button', { name: /Clear all/i })).not.toBeInTheDocument();
    });

    it('shows Clear all button when tools are selected', async () => {
      const user = userEvent.setup();
      render(
        <ToolFilterPopover selectedTools={['Read']} onChange={jest.fn()} />
      );

      await user.click(screen.getByRole('button', { name: /Tools/i }));

      expect(screen.getByRole('button', { name: /Clear all/i })).toBeInTheDocument();
    });

    it('calls onChange with empty array when Clear all is clicked', async () => {
      const user = userEvent.setup();
      const handleChange = jest.fn();

      render(
        <ToolFilterPopover
          selectedTools={['Read', 'Write', 'Edit']}
          onChange={handleChange}
        />
      );

      await user.click(screen.getByRole('button', { name: /Tools/i }));
      await user.click(screen.getByRole('button', { name: /Clear all/i }));

      expect(handleChange).toHaveBeenCalledWith([]);
    });
  });

  describe('Custom Styling', () => {
    it('applies custom className to trigger button', () => {
      render(
        <ToolFilterPopover
          selectedTools={[]}
          onChange={jest.fn()}
          className="custom-class"
        />
      );

      expect(screen.getByRole('button')).toHaveClass('custom-class');
    });
  });
});

describe('ToolFilterBar', () => {
  describe('Rendering', () => {
    it('returns null when no tools selected', () => {
      const { container } = render(
        <ToolFilterBar selectedTools={[]} onChange={jest.fn()} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('renders when tools are selected', () => {
      render(
        <ToolFilterBar selectedTools={['Read']} onChange={jest.fn()} />
      );

      expect(screen.getByText('Tools:')).toBeInTheDocument();
      expect(screen.getByText('Read')).toBeInTheDocument();
    });

    it('displays all selected tools as badges', () => {
      render(
        <ToolFilterBar
          selectedTools={['Read', 'Write', 'Edit']}
          onChange={jest.fn()}
        />
      );

      expect(screen.getByText('Read')).toBeInTheDocument();
      expect(screen.getByText('Write')).toBeInTheDocument();
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });
  });

  describe('Remove Tool', () => {
    it('removes tool when X button is clicked', async () => {
      const user = userEvent.setup();
      const handleChange = jest.fn();

      render(
        <ToolFilterBar
          selectedTools={['Read', 'Write']}
          onChange={handleChange}
        />
      );

      // Find the X icon in the Read badge and click it
      const readBadge = screen.getByText('Read').closest('div');
      const removeButton = readBadge?.querySelector('svg');
      await user.click(removeButton!);

      expect(handleChange).toHaveBeenCalledWith(['Write']);
    });
  });

  describe('Clear All', () => {
    it('shows Clear all button', () => {
      render(
        <ToolFilterBar
          selectedTools={['Read', 'Write']}
          onChange={jest.fn()}
        />
      );

      expect(screen.getByRole('button', { name: /Clear all/i })).toBeInTheDocument();
    });

    it('clears all selections when Clear all is clicked', async () => {
      const user = userEvent.setup();
      const handleChange = jest.fn();

      render(
        <ToolFilterBar
          selectedTools={['Read', 'Write', 'Edit']}
          onChange={handleChange}
        />
      );

      await user.click(screen.getByRole('button', { name: /Clear all/i }));

      expect(handleChange).toHaveBeenCalledWith([]);
    });
  });

  describe('Custom Styling', () => {
    it('applies custom className', () => {
      const { container } = render(
        <ToolFilterBar
          selectedTools={['Read']}
          onChange={jest.fn()}
          className="custom-bar-class"
        />
      );

      expect(container.firstChild).toHaveClass('custom-bar-class');
    });
  });
});
