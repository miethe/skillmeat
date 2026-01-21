/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CatalogTabs } from '@/app/marketplace/sources/[id]/components/catalog-tabs';

/**
 * Unit tests for CatalogTabs component
 *
 * Tests cover:
 * 1. Rendering - tabs display, counts in parentheses, zero-count styling
 * 2. Tab click interaction - correct callback values
 * 3. Selected state - active tab highlighting
 * 4. Count display - total and individual counts
 */

const mockCountsByType = {
  skill: 12,
  agent: 5,
  command: 3,
  mcp_server: 0,
  hook: 2,
};

const mockCountsAllZero = {
  skill: 0,
  agent: 0,
  command: 0,
  mcp_server: 0,
  hook: 0,
};

const mockCountsSingleType = {
  skill: 42,
  agent: 0,
  command: 0,
  mcp_server: 0,
  hook: 0,
};

describe('CatalogTabs', () => {
  describe('Rendering', () => {
    it('renders "All Types" tab', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      expect(screen.getByText('All Types')).toBeInTheDocument();
    });

    it('renders all artifact type tabs', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // Verify each artifact type tab is rendered (labels hidden on mobile, check by presence)
      expect(screen.getByText('Skills')).toBeInTheDocument();
      expect(screen.getByText('Agents')).toBeInTheDocument();
      expect(screen.getByText('Commands')).toBeInTheDocument();
      expect(screen.getByText('MCP')).toBeInTheDocument();
      expect(screen.getByText('Hooks')).toBeInTheDocument();
    });

    it('shows counts in parentheses for each tab', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // Check for individual counts
      expect(screen.getByText('(12)')).toBeInTheDocument(); // Skills
      expect(screen.getByText('(5)')).toBeInTheDocument(); // Agents
      expect(screen.getByText('(3)')).toBeInTheDocument(); // Commands
      expect(screen.getByText('(2)')).toBeInTheDocument(); // Hooks
      // MCP has 0 count
      expect(screen.getAllByText('(0)').length).toBeGreaterThanOrEqual(1);
    });

    it('zero-count tabs have opacity class for visual muting', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // Find MCP tab (which has 0 count) and verify it has opacity-50 class
      const mcpTab = screen.getByRole('tab', { name: /mcp/i });
      expect(mcpTab).toHaveClass('opacity-50');
    });

    it('non-zero-count tabs do not have opacity-50 class', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // Find Skills tab (which has 12 count) and verify it does NOT have opacity-50 class
      const skillsTab = screen.getByRole('tab', { name: /skills/i });
      expect(skillsTab).not.toHaveClass('opacity-50');
    });
  });

  describe('Tab Click Interaction', () => {
    it('clicking "All Types" calls onTypeChange with null', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType="skill"
          onTypeChange={mockOnTypeChange}
        />
      );

      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      await user.click(allTypesTab);

      expect(mockOnTypeChange).toHaveBeenCalledWith(null);
    });

    it('clicking "Skills" calls onTypeChange with "skill"', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const skillsTab = screen.getByRole('tab', { name: /skills/i });
      await user.click(skillsTab);

      expect(mockOnTypeChange).toHaveBeenCalledWith('skill');
    });

    it('clicking "Agents" calls onTypeChange with "agent"', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const agentsTab = screen.getByRole('tab', { name: /agents/i });
      await user.click(agentsTab);

      expect(mockOnTypeChange).toHaveBeenCalledWith('agent');
    });

    it('clicking "Commands" calls onTypeChange with "command"', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const commandsTab = screen.getByRole('tab', { name: /commands/i });
      await user.click(commandsTab);

      expect(mockOnTypeChange).toHaveBeenCalledWith('command');
    });

    it('clicking "MCP" calls onTypeChange with "mcp_server"', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const mcpTab = screen.getByRole('tab', { name: /mcp/i });
      await user.click(mcpTab);

      expect(mockOnTypeChange).toHaveBeenCalledWith('mcp_server');
    });

    it('clicking "Hooks" calls onTypeChange with "hook"', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const hooksTab = screen.getByRole('tab', { name: /hooks/i });
      await user.click(hooksTab);

      expect(mockOnTypeChange).toHaveBeenCalledWith('hook');
    });

    it('clicking zero-count tab still triggers onTypeChange', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // MCP has 0 count but should still be clickable
      const mcpTab = screen.getByRole('tab', { name: /mcp/i });
      await user.click(mcpTab);

      expect(mockOnTypeChange).toHaveBeenCalledWith('mcp_server');
    });
  });

  describe('Selected State', () => {
    it('when selectedType is null, "All Types" tab is active', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      expect(allTypesTab).toHaveAttribute('data-state', 'active');
    });

    it('when selectedType is "skill", Skills tab is active', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType="skill"
          onTypeChange={mockOnTypeChange}
        />
      );

      const skillsTab = screen.getByRole('tab', { name: /skills/i });
      expect(skillsTab).toHaveAttribute('data-state', 'active');

      // All Types should be inactive
      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      expect(allTypesTab).toHaveAttribute('data-state', 'inactive');
    });

    it('when selectedType is "agent", Agents tab is active', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType="agent"
          onTypeChange={mockOnTypeChange}
        />
      );

      const agentsTab = screen.getByRole('tab', { name: /agents/i });
      expect(agentsTab).toHaveAttribute('data-state', 'active');
    });

    it('when selectedType is "mcp_server", MCP tab is active', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType="mcp_server"
          onTypeChange={mockOnTypeChange}
        />
      );

      const mcpTab = screen.getByRole('tab', { name: /mcp/i });
      expect(mcpTab).toHaveAttribute('data-state', 'active');
    });

    it('only one tab can be active at a time', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType="skill"
          onTypeChange={mockOnTypeChange}
        />
      );

      const tabs = screen.getAllByRole('tab');
      const activeTabs = tabs.filter((tab) => tab.getAttribute('data-state') === 'active');

      expect(activeTabs).toHaveLength(1);
    });
  });

  describe('Count Display', () => {
    it('total count in "All Types" is sum of all type counts', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // Total should be 12 + 5 + 3 + 0 + 2 = 22
      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      expect(allTypesTab).toHaveTextContent('(22)');
    });

    it('displays zero total when all counts are zero', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsAllZero}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      expect(allTypesTab).toHaveTextContent('(0)');
    });

    it('handles single non-zero type correctly', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsSingleType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // Total should equal the single type count (42)
      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      expect(allTypesTab).toHaveTextContent('(42)');
    });

    it('handles missing type counts gracefully (defaults to 0)', () => {
      const mockOnTypeChange = jest.fn();
      // Only provide some types, others should default to 0
      const partialCounts = {
        skill: 5,
        agent: 3,
      };

      render(
        <CatalogTabs
          countsByType={partialCounts}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // Total should be 5 + 3 = 8 (missing types default to 0)
      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      expect(allTypesTab).toHaveTextContent('(8)');

      // MCP tab (not in counts) should show (0)
      const mcpTab = screen.getByRole('tab', { name: /mcp/i });
      expect(mcpTab).toHaveTextContent('(0)');
    });

    it('displays large counts correctly', () => {
      const mockOnTypeChange = jest.fn();
      const largeCounts = {
        skill: 1000,
        agent: 500,
        command: 250,
        mcp_server: 100,
        hook: 150,
      };

      render(
        <CatalogTabs
          countsByType={largeCounts}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // Total should be 2000
      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      expect(allTypesTab).toHaveTextContent('(2000)');
    });
  });

  describe('Accessibility', () => {
    it('tabs have proper role', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const tabs = screen.getAllByRole('tab');
      expect(tabs.length).toBe(6); // All Types + 5 artifact types
    });

    it('tablist has proper role', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      expect(screen.getByRole('tablist')).toBeInTheDocument();
    });

    it('keyboard navigation works with Enter key', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const skillsTab = screen.getByRole('tab', { name: /skills/i });
      // Use userEvent.click to focus and then keyboard, avoiding act() warnings
      await user.click(skillsTab);
      mockOnTypeChange.mockClear(); // Clear the click call
      await user.keyboard('{Enter}');

      expect(mockOnTypeChange).toHaveBeenCalledWith('skill');
    });

    it('keyboard navigation works with Space key', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const agentsTab = screen.getByRole('tab', { name: /agents/i });
      // Use userEvent.click to focus and then keyboard, avoiding act() warnings
      await user.click(agentsTab);
      mockOnTypeChange.mockClear(); // Clear the click call
      await user.keyboard(' ');

      expect(mockOnTypeChange).toHaveBeenCalledWith('agent');
    });
  });

  describe('Visual Styling', () => {
    it('tabs container has horizontal scroll class', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const tabsList = screen.getByRole('tablist');
      expect(tabsList).toHaveClass('overflow-x-auto');
    });

    it('tabs have transition classes', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const skillsTab = screen.getByRole('tab', { name: /skills/i });
      expect(skillsTab).toHaveClass('transition-all');
    });

    it('zero-count tab count span has reduced opacity', () => {
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      // Find the MCP tab's count span specifically
      const mcpTab = screen.getByRole('tab', { name: /mcp/i });
      const countSpan = mcpTab.querySelector('span.opacity-50');
      expect(countSpan).toBeInTheDocument();
      expect(countSpan).toHaveTextContent('(0)');
    });
  });

  describe('Edge Cases', () => {
    it('handles empty countsByType object', () => {
      const mockOnTypeChange = jest.fn();
      render(<CatalogTabs countsByType={{}} selectedType={null} onTypeChange={mockOnTypeChange} />);

      // All tabs should show 0 count
      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      expect(allTypesTab).toHaveTextContent('(0)');
    });

    it('handles unknown selectedType gracefully', () => {
      const mockOnTypeChange = jest.fn();
      // Pass an unknown type - component should still render
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType="unknown_type"
          onTypeChange={mockOnTypeChange}
        />
      );

      // All Types should not be active
      const allTypesTab = screen.getByRole('tab', { name: /all types/i });
      expect(allTypesTab).toHaveAttribute('data-state', 'inactive');

      // Component should still render all tabs
      const tabs = screen.getAllByRole('tab');
      expect(tabs.length).toBe(6);
    });

    it('handles rapid clicking without errors', async () => {
      const user = userEvent.setup();
      const mockOnTypeChange = jest.fn();
      render(
        <CatalogTabs
          countsByType={mockCountsByType}
          selectedType={null}
          onTypeChange={mockOnTypeChange}
        />
      );

      const skillsTab = screen.getByRole('tab', { name: /skills/i });
      const agentsTab = screen.getByRole('tab', { name: /agents/i });
      const commandsTab = screen.getByRole('tab', { name: /commands/i });

      // Rapid clicks on different tabs - component should handle without errors
      await user.click(skillsTab);
      await user.click(agentsTab);
      await user.click(commandsTab);

      // Verify all expected values were passed (Radix Tabs may call multiple times internally)
      expect(mockOnTypeChange).toHaveBeenCalledWith('skill');
      expect(mockOnTypeChange).toHaveBeenCalledWith('agent');
      expect(mockOnTypeChange).toHaveBeenCalledWith('command');
      // At minimum, we should have 3 calls (could be more due to Radix internals)
      expect(mockOnTypeChange.mock.calls.length).toBeGreaterThanOrEqual(3);
    });
  });
});
