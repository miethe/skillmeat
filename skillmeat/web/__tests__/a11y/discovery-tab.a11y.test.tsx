/**
 * Accessibility Tests for DiscoveryTab Component
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { NotificationProvider } from '@/lib/notification-store';
import { DiscoveryTab } from '@/components/discovery/DiscoveryTab';
import type { DiscoveredArtifact, SkipPreference } from '@/types/discovery';

// Test wrapper with NotificationProvider
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <NotificationProvider>{children}</NotificationProvider>;
}

const mockArtifacts: DiscoveredArtifact[] = [
  {
    type: 'skill',
    name: 'test-skill',
    source: 'github:user/repo/skill',
    version: 'latest',
    path: '/path/to/skill',
    discovered_at: '2025-01-01T00:00:00Z',
    description: 'A test skill',
    tags: ['test'],
  },
  {
    type: 'command',
    name: 'test-command',
    source: 'github:user/repo/command',
    path: '/path/to/command',
    discovered_at: '2025-01-02T00:00:00Z',
    description: 'A test command',
  },
  {
    type: 'agent',
    name: 'test-agent',
    source: 'github:user/repo/agent',
    path: '/path/to/agent',
    discovered_at: '2025-01-03T00:00:00Z',
  },
];

const mockSkipPrefs: SkipPreference[] = [
  {
    artifact_key: 'agent:test-agent',
    skip_reason: 'Not needed',
    added_date: '2025-01-03T00:00:00Z',
  },
];

describe('DiscoveryTab Accessibility', () => {
  describe('Basic Rendering', () => {
    it('should have no violations with artifacts', async () => {
      const { container } = render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} skipPrefs={mockSkipPrefs} />
        </TestWrapper>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no violations in loading state', async () => {
      const { container } = render(
        <TestWrapper>
          <DiscoveryTab artifacts={[]} isLoading={true} />
        </TestWrapper>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no violations in empty state', async () => {
      const { container } = render(
        <TestWrapper>
          <DiscoveryTab artifacts={[]} isLoading={false} />
        </TestWrapper>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no violations with filtered results', async () => {
      const { container } = render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} skipPrefs={mockSkipPrefs} />
        </TestWrapper>
      );

      // Apply filter
      const statusFilter = screen.getByLabelText(/Status/i);
      await userEvent.click(statusFilter);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Screen Reader Support', () => {
    it('should announce loading state', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={[]} isLoading={true} />
        </TestWrapper>
      );

      const loadingMessage = screen.getByText(/Loading discovered artifacts/i);
      expect(loadingMessage).toBeInTheDocument();
      expect(loadingMessage).toHaveAttribute('role', 'status');
      expect(loadingMessage).toHaveAttribute('aria-live', 'polite');
    });

    it('should have accessible region label', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      const region = screen.getByRole('region');
      expect(region).toHaveAttribute('aria-label', 'Discovered artifacts');
    });

    it('should have accessible status badges', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} skipPrefs={mockSkipPrefs} />
        </TestWrapper>
      );

      // Status badge should have aria-label
      const statusBadge = screen.getByLabelText(/Status: New/i);
      expect(statusBadge).toBeInTheDocument();
    });

    it('should have accessible type badges', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Type badge should have aria-label
      const typeBadge = screen.getByLabelText(/Type: skill/i);
      expect(typeBadge).toBeInTheDocument();
    });

    it('should hide decorative icons from screen readers', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Search icon should be hidden
      const searchInput = screen.getByPlaceholderText(/Search artifacts/i);
      const searchIcon = searchInput.previousElementSibling;
      expect(searchIcon).toHaveAttribute('aria-hidden', 'true');
    });

    it('should announce empty filter results', async () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Search for non-existent artifact
      const searchInput = screen.getByPlaceholderText(/Search artifacts/i);
      await userEvent.type(searchInput, 'nonexistent');

      await waitFor(() => {
        const emptyMessage = screen.getByText(/No artifacts match your filters/i);
        expect(emptyMessage).toBeInTheDocument();
      });
    });
  });

  describe('Keyboard Navigation', () => {
    it('should allow keyboard navigation through filters', async () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Tab to search input
      const searchInput = screen.getByPlaceholderText(/Search artifacts/i);
      searchInput.focus();
      expect(searchInput).toHaveFocus();

      // Tab to status filter
      await userEvent.tab();
      const statusFilter = screen.getByRole('combobox', { name: /Status/i });
      expect(statusFilter).toHaveFocus();

      // Tab to type filter
      await userEvent.tab();
      const typeFilter = screen.getByRole('combobox', { name: /Type/i });
      expect(typeFilter).toHaveFocus();
    });

    it('should support Enter/Space on table rows', async () => {
      const onViewDetails = jest.fn();
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} onViewDetails={onViewDetails} />
        </TestWrapper>
      );

      // Find first row with role="button"
      const firstRow = screen.getByLabelText(/View details for test-skill/i);
      firstRow.focus();

      // Press Enter
      await userEvent.keyboard('{Enter}');
      expect(onViewDetails).toHaveBeenCalledWith(mockArtifacts[0]);

      // Press Space
      await userEvent.keyboard(' ');
      expect(onViewDetails).toHaveBeenCalledTimes(2);
    });

    it('should have accessible sort toggle button', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      const sortToggle = screen.getByRole('button', { name: /Toggle sort order/i });
      expect(sortToggle).toBeInTheDocument();
      expect(sortToggle).toHaveAccessibleName();
    });

    it('should support keyboard navigation for clear filters', async () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Apply a filter
      const searchInput = screen.getByPlaceholderText(/Search artifacts/i);
      await userEvent.type(searchInput, 'test');

      // Tab to clear filters button
      const clearButton = screen.getByRole('button', { name: /Clear Filters/i });
      clearButton.focus();
      expect(clearButton).toHaveFocus();

      // Press Enter
      await userEvent.keyboard('{Enter}');
      expect(searchInput).toHaveValue('');
    });
  });

  describe('Form Controls', () => {
    it('should have properly labeled filter controls', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Status filter
      const statusLabel = screen.getByText('Status');
      expect(statusLabel).toBeInTheDocument();
      const statusFilter = screen.getByLabelText(/Status/i);
      expect(statusFilter).toHaveAttribute('id', 'status-filter');

      // Type filter
      const typeLabel = screen.getByText('Type');
      expect(typeLabel).toBeInTheDocument();
      const typeFilter = screen.getByLabelText(/Type/i);
      expect(typeFilter).toHaveAttribute('id', 'type-filter');

      // Sort field
      const sortLabel = screen.getByText('Sort By');
      expect(sortLabel).toBeInTheDocument();
      const sortField = screen.getByLabelText(/Sort By/i);
      expect(sortField).toHaveAttribute('id', 'sort-field');

      // Sort order
      const orderLabel = screen.getByText('Order');
      expect(orderLabel).toBeInTheDocument();
      const orderField = screen.getByLabelText(/Order/i);
      expect(orderField).toHaveAttribute('id', 'sort-order');
    });

    it('should have accessible search input', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      const searchInput = screen.getByPlaceholderText(/Search artifacts/i);
      expect(searchInput).toHaveAttribute('type', 'text');
      expect(searchInput).toHaveAccessibleName(/Search artifacts/i);
    });
  });

  describe('Table Structure', () => {
    it('should have semantic table structure', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Table should exist
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();

      // Should have column headers
      expect(screen.getByRole('columnheader', { name: /Name/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /Type/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /Status/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /Source/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /Discovered/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /Actions/i })).toBeInTheDocument();
    });

    it('should have accessible row labels', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Each row should have aria-label
      const skillRow = screen.getByLabelText(/View details for test-skill/i);
      expect(skillRow).toBeInTheDocument();
      expect(skillRow).toHaveAttribute('role', 'button');
      expect(skillRow).toHaveAttribute('tabIndex', '0');
    });
  });

  describe('Color Contrast', () => {
    it('should have compliant status badge colors', async () => {
      const { container } = render(
        <DiscoveryTab artifacts={mockArtifacts} skipPrefs={mockSkipPrefs} />
      );

      // Check color contrast specifically
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    });

    it('should have compliant type badge colors', async () => {
      const { container } = render(<DiscoveryTab artifacts={mockArtifacts} />);

      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    });
  });

  describe('Interactive Elements', () => {
    it('should have accessible action buttons', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} onImport={jest.fn()} onToggleSkip={jest.fn()} />
        </TestWrapper>
      );

      // Action menu triggers should have labels
      const actionButtons = screen.getAllByRole('button', { name: /Actions for/i });
      expect(actionButtons.length).toBeGreaterThan(0);

      actionButtons.forEach((button) => {
        expect(button).toHaveAccessibleName();
      });
    });

    it('should not rely solely on color for status indication', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} skipPrefs={mockSkipPrefs} />
        </TestWrapper>
      );

      // Status should be indicated by text, not just color
      const newBadge = screen.getByLabelText(/Status: New/i);
      expect(newBadge).toHaveTextContent(/New/i);

      // Skipped badge should also have text
      const skippedBadge = screen.getByLabelText(/Status: Skipped/i);
      expect(skippedBadge).toHaveTextContent(/Skipped/i);
    });
  });

  describe('Dynamic Content', () => {
    it('should announce filter results count', async () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Results summary should be present
      const summary = screen.getByText(/Showing \d+ of \d+ artifacts/i);
      expect(summary).toBeInTheDocument();
    });

    it('should handle empty state gracefully', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={[]} isLoading={false} />
        </TestWrapper>
      );

      const emptyState = screen.getByRole('status');
      expect(emptyState).toHaveTextContent(/No Artifacts Discovered/i);
    });
  });

  describe('Focus Management', () => {
    it('should maintain focus visibility on interactive elements', () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      const searchInput = screen.getByPlaceholderText(/Search artifacts/i);
      searchInput.focus();

      // Focus should be visible (browser default)
      expect(document.activeElement).toBe(searchInput);
    });

    it('should have logical tab order', async () => {
      render(
        <TestWrapper>
          <DiscoveryTab artifacts={mockArtifacts} />
        </TestWrapper>
      );

      // Start at search
      const searchInput = screen.getByPlaceholderText(/Search artifacts/i);
      searchInput.focus();
      expect(searchInput).toHaveFocus();

      // Tab through filters in order
      await userEvent.tab();
      expect(screen.getByRole('combobox', { name: /Status/i })).toHaveFocus();

      await userEvent.tab();
      expect(screen.getByRole('combobox', { name: /Type/i })).toHaveFocus();

      await userEvent.tab();
      expect(screen.getByRole('combobox', { name: /Sort By/i })).toHaveFocus();

      await userEvent.tab();
      expect(screen.getByRole('combobox', { name: /Order/i })).toHaveFocus();
    });
  });
});
