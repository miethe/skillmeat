/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe, toHaveNoViolations } from 'jest-axe';
import { NotificationProvider } from '@/lib/notification-store';
import { DiscoveryBanner } from '@/components/discovery/DiscoveryBanner';
import { BulkImportModal } from '@/components/discovery/BulkImportModal';
import type { DiscoveredArtifact } from '@/types/discovery';

expect.extend(toHaveNoViolations);

// Test wrapper with providers
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={queryClient}>
      <NotificationProvider>{children}</NotificationProvider>
    </QueryClientProvider>
  );
}

describe('DiscoveryBanner', () => {
  it('displays importable count', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} onReview={onReview} />
      </TestWrapper>
    );
    expect(screen.getByText(/5 Artifacts Ready to Import/i)).toBeInTheDocument();
  });

  it('displays correct singular form', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={1} onReview={onReview} />
      </TestWrapper>
    );
    expect(screen.getByText(/1 Artifact Ready to Import/i)).toBeInTheDocument();
  });

  it('calls onReview when button clicked', async () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} onReview={onReview} />
      </TestWrapper>
    );
    const reviewButton = screen.getByRole('button', { name: /Review & Import/i });
    await userEvent.click(reviewButton);
    expect(onReview).toHaveBeenCalledTimes(1);
  });

  it('can be dismissed when dismissible', async () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} onReview={onReview} dismissible />
      </TestWrapper>
    );

    expect(screen.getByText(/5 Artifacts Ready to Import/i)).toBeInTheDocument();

    const dismissButton = screen.getByRole('button', { name: /Dismiss/i });
    await userEvent.click(dismissButton);

    await waitFor(() => {
      expect(screen.queryByText(/5 Artifacts Ready to Import/i)).not.toBeInTheDocument();
    });
  });

  it('can be closed with X button when dismissible', async () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} onReview={onReview} dismissible />
      </TestWrapper>
    );

    const closeButton = screen.getByRole('button', { name: /Close/i });
    await userEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText(/5 Artifacts Ready to Import/i)).not.toBeInTheDocument();
    });
  });

  it('returns null when importableCount is 0', () => {
    const onReview = jest.fn();
    const { container } = render(
      <TestWrapper>
        <DiscoveryBanner importableCount={0} onReview={onReview} />
      </TestWrapper>
    );
    expect(container.firstChild).toBeNull();
  });

  it('does not show dismiss buttons when dismissible is false', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} onReview={onReview} dismissible={false} />
      </TestWrapper>
    );

    expect(screen.queryByRole('button', { name: /Dismiss/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Close/i })).not.toBeInTheDocument();
  });

  it('has proper ARIA attributes', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} onReview={onReview} />
      </TestWrapper>
    );

    const alert = screen.getByRole('status');
    expect(alert).toHaveAttribute('aria-live', 'polite');
  });

  it('shows total count when discoveredCount is provided and different', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={3} discoveredCount={10} onReview={onReview} />
      </TestWrapper>
    );

    expect(screen.getByText(/3 Artifacts Ready to Import/i)).toBeInTheDocument();
    expect(screen.getByText(/Found 10 total - 3 remaining/i)).toBeInTheDocument();
  });

  it('does not show total count when discoveredCount equals importableCount', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} discoveredCount={5} onReview={onReview} />
      </TestWrapper>
    );

    expect(screen.getByText(/5 Artifacts Ready to Import/i)).toBeInTheDocument();
    expect(screen.queryByText(/Found 5 total - 5 remaining/i)).not.toBeInTheDocument();
  });

  it('does not show total count when discoveredCount is not provided', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} onReview={onReview} />
      </TestWrapper>
    );

    expect(screen.getByText(/5 Artifacts Ready to Import/i)).toBeInTheDocument();
    expect(screen.queryByText(/Found.*total.*remaining/i)).not.toBeInTheDocument();
  });
});

describe('BulkImportModal', () => {
  const mockArtifacts: DiscoveredArtifact[] = [
    {
      type: 'skill',
      name: 'test-skill',
      source: 'user/repo/skill',
      version: 'latest',
      path: '/path/to/skill',
      discovered_at: '2025-01-01T00:00:00Z',
    },
    {
      type: 'command',
      name: 'test-command',
      source: 'user/repo/command',
      path: '/path/to/command',
      discovered_at: '2025-01-01T00:00:00Z',
    },
  ];

  it('renders artifacts in table', () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    expect(screen.getByText('test-skill')).toBeInTheDocument();
    expect(screen.getByText('test-command')).toBeInTheDocument();
  });

  it('displays artifact count in description', () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    expect(screen.getByText(/2 discovered/i)).toBeInTheDocument();
  });

  it('checkbox selection works', async () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    // Find checkboxes (first is "select all", others are individual)
    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]); // Select first artifact

    // Selection counter should show
    expect(screen.getByText('1 selected')).toBeInTheDocument();

    // Import button should show count
    expect(screen.getByRole('button', { name: /Import \(1\)/i })).toBeInTheDocument();
  });

  it('select all checkbox works', async () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    const selectAllCheckbox = screen.getByRole('checkbox', { name: /Select all/i });
    await userEvent.click(selectAllCheckbox);

    expect(screen.getByText('2 selected')).toBeInTheDocument();
  });

  it('import button disabled when none selected', () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    const importButton = screen.getByRole('button', { name: /^Import$/i });
    expect(importButton).toBeDisabled();
  });

  it('calls onImport with selected artifacts', async () => {
    const onClose = jest.fn();
    const onImport = jest.fn().mockResolvedValue(undefined);

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    // Select first artifact
    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]);

    // Click import
    const importButton = screen.getByRole('button', { name: /Import \(1\)/i });
    await userEvent.click(importButton);

    await waitFor(() => {
      expect(onImport).toHaveBeenCalledWith([mockArtifacts[0]], expect.any(Array));
    });
  });

  it('calls onClose when Cancel button clicked', async () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    await userEvent.click(cancelButton);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('shows empty state when no artifacts', () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={[]}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    expect(screen.getByText('No artifacts discovered')).toBeInTheDocument();
  });

  it('displays loading state during import', async () => {
    const onClose = jest.fn();
    const onImport = jest
      .fn()
      .mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    // Select an artifact
    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]);

    // Click import
    const importButton = screen.getByRole('button', { name: /Import \(1\)/i });
    await userEvent.click(importButton);

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText('Importing...')).toBeInTheDocument();
    });

    // Buttons should be disabled
    expect(screen.getByRole('button', { name: /Importing/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeDisabled();
  });

  it('handles import errors gracefully', async () => {
    const onClose = jest.fn();
    const onImport = jest.fn().mockRejectedValue(new Error('Import failed'));

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    // Select an artifact
    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]);

    // Click import
    const importButton = screen.getByRole('button', { name: /Import \(1\)/i });
    await userEvent.click(importButton);

    // Wait for import to complete
    await waitFor(() => {
      expect(onImport).toHaveBeenCalled();
    });

    // Modal should remain open on error
    expect(screen.getByText('test-skill')).toBeInTheDocument();
  });

  it('row click toggles selection', async () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    // Click on the row (not the checkbox)
    const row = screen.getByText('test-skill').closest('tr');
    expect(row).toBeTruthy();
    if (row) {
      await userEvent.click(row);
    }

    // Should be selected
    expect(screen.getByText('1 selected')).toBeInTheDocument();
  });

  it('edit button is present for each artifact', () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    const editButtons = screen.getAllByRole('button', { name: /Edit/i });
    expect(editButtons).toHaveLength(2);
  });

  it('displays artifact badges', () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    expect(screen.getByText('skill')).toBeInTheDocument();
    expect(screen.getByText('command')).toBeInTheDocument();
  });

  it('does not render when open is false', () => {
    const onClose = jest.fn();
    const onImport = jest.fn();

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={false}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    expect(screen.queryByText('Review Discovered Artifacts')).not.toBeInTheDocument();
  });

  describe('Skip Functionality', () => {
    it('renders skip checkboxes for each artifact', () => {
      const onClose = jest.fn();
      const onImport = jest.fn();

      render(
        <TestWrapper>
          <BulkImportModal
            artifacts={mockArtifacts}
            open={true}
            onClose={onClose}
            onImport={onImport}
          />
        </TestWrapper>
      );

      // Should have skip checkboxes (2 artifacts + 1 select-all = 3 total, then 2 skip checkboxes)
      const skipLabels = screen.getAllByText('Skip');
      expect(skipLabels).toHaveLength(2);
    });

    it('skip checkbox toggles correctly', async () => {
      const onClose = jest.fn();
      const onImport = jest.fn();

      render(
        <TestWrapper>
          <BulkImportModal
            artifacts={mockArtifacts}
            open={true}
            onClose={onClose}
            onImport={onImport}
          />
        </TestWrapper>
      );

      // Find skip checkbox for first artifact
      const skipCheckbox = screen.getByLabelText(/Don't show test-skill in future discoveries/i);
      expect(skipCheckbox).not.toBeChecked();

      // Toggle skip
      await userEvent.click(skipCheckbox);
      expect(skipCheckbox).toBeChecked();

      // Toggle back
      await userEvent.click(skipCheckbox);
      expect(skipCheckbox).not.toBeChecked();
    });

    it('skip checkboxes exist and can be toggled independently', async () => {
      const onClose = jest.fn();
      const onImport = jest.fn();

      render(
        <TestWrapper>
          <BulkImportModal
            artifacts={mockArtifacts}
            open={true}
            onClose={onClose}
            onImport={onImport}
          />
        </TestWrapper>
      );

      // Skip checkboxes should exist
      const skipCheckbox1 = screen.getByLabelText(/Don't show test-skill in future discoveries/i);
      const skipCheckbox2 = screen.getByLabelText(/Don't show test-command in future discoveries/i);

      // Toggle one without affecting the other
      await userEvent.click(skipCheckbox1);
      expect(skipCheckbox1).toBeChecked();
      expect(skipCheckbox2).not.toBeChecked();
    });


    it('passes skip list to onImport', async () => {
      const onClose = jest.fn();
      const onImport = jest.fn().mockResolvedValue({
        total_requested: 1,
        total_imported: 1,
        total_skipped: 0,
        total_failed: 0,
        imported_to_collection: 1,
        added_to_project: 1,
        results: [],
        duration_ms: 100,
      });

      render(
        <TestWrapper>
          <BulkImportModal
            artifacts={mockArtifacts}
            open={true}
            onClose={onClose}
            onImport={onImport}
          />
        </TestWrapper>
      );

      // Toggle skip for first artifact
      const skipCheckbox = screen.getByLabelText(/Don't show test-skill in future discoveries/i);
      await userEvent.click(skipCheckbox);

      // Select first artifact
      const selectCheckboxes = screen.getAllByRole('checkbox');
      await userEvent.click(selectCheckboxes[1]);

      // Click import
      const importButton = screen.getByRole('button', { name: /Import \(1\)/i });
      await userEvent.click(importButton);

      await waitFor(() => {
        expect(onImport).toHaveBeenCalledWith(
          [mockArtifacts[0]],
          ['skill:test-skill'] // Skip list should contain the skipped artifact key
        );
      });
    });

    it('skip checkbox has proper aria-label', () => {
      const onClose = jest.fn();
      const onImport = jest.fn();

      render(
        <TestWrapper>
          <BulkImportModal
            artifacts={mockArtifacts}
            open={true}
            onClose={onClose}
            onImport={onImport}
          />
        </TestWrapper>
      );

      const skipCheckbox1 = screen.getByLabelText(/Don't show test-skill in future discoveries/i);
      const skipCheckbox2 = screen.getByLabelText(/Don't show test-command in future discoveries/i);

      expect(skipCheckbox1).toBeInTheDocument();
      expect(skipCheckbox2).toBeInTheDocument();
    });

    it('skip state is cleared when modal closes', async () => {
      const onClose = jest.fn();
      const onImport = jest.fn();

      const { rerender } = render(
        <TestWrapper>
          <BulkImportModal
            artifacts={mockArtifacts}
            open={true}
            onClose={onClose}
            onImport={onImport}
          />
        </TestWrapper>
      );

      // Toggle skip
      const skipCheckbox = screen.getByLabelText(/Don't show test-skill in future discoveries/i);
      await userEvent.click(skipCheckbox);
      expect(skipCheckbox).toBeChecked();

      // Close modal
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      await userEvent.click(cancelButton);

      expect(onClose).toHaveBeenCalled();

      // Reopen modal (simulate)
      rerender(
        <TestWrapper>
          <BulkImportModal
            artifacts={mockArtifacts}
            open={true}
            onClose={onClose}
            onImport={onImport}
          />
        </TestWrapper>
      );

      // Skip state should be reset
      const newSkipCheckbox = screen.getByLabelText(/Don't show test-skill in future discoveries/i);
      expect(newSkipCheckbox).not.toBeChecked();
    });

    it('displays status labels for artifacts', () => {
      const artifactsWithStatus: DiscoveredArtifact[] = [
        {
          ...mockArtifacts[0],
          status: 'success',
        },
        {
          ...mockArtifacts[1],
          status: 'skipped',
        },
      ];

      const onClose = jest.fn();
      const onImport = jest.fn();

      render(
        <TestWrapper>
          <BulkImportModal
            artifacts={artifactsWithStatus}
            open={true}
            onClose={onClose}
            onImport={onImport}
          />
        </TestWrapper>
      );

      expect(screen.getByText(/Will add to Collection & Project/i)).toBeInTheDocument();
      expect(screen.getByText(/Skipped \(marked to skip\)/i)).toBeInTheDocument();
    });

    it('skip checkbox is disabled for already skipped artifacts', () => {
      const artifactsWithStatus: DiscoveredArtifact[] = [
        {
          ...mockArtifacts[0],
          status: 'skipped',
        },
      ];

      const onClose = jest.fn();
      const onImport = jest.fn();

      render(
        <TestWrapper>
          <BulkImportModal
            artifacts={artifactsWithStatus}
            open={true}
            onClose={onClose}
            onImport={onImport}
          />
        </TestWrapper>
      );

      const skipCheckbox = screen.getByLabelText(/Don't show test-skill in future discoveries/i);
      expect(skipCheckbox).toBeDisabled();
    });
  });
});

describe('Accessibility Tests', () => {
  const mockArtifacts: DiscoveredArtifact[] = [
    {
      type: 'skill',
      name: 'test-skill',
      source: 'user/repo/skill',
      version: 'latest',
      path: '/path/to/skill',
      discovered_at: '2025-01-01T00:00:00Z',
    },
  ];

  it('DiscoveryBanner has no accessibility violations', async () => {
    const onReview = jest.fn();
    const { container } = render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} onReview={onReview} />
      </TestWrapper>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('BulkImportModal has no accessibility violations', async () => {
    const onClose = jest.fn();
    const onImport = jest.fn();
    const { container } = render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('DiscoveryBanner keyboard navigation works', async () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner importableCount={5} onReview={onReview} dismissible />
      </TestWrapper>
    );

    // Tab to Review & Import button
    const reviewButton = screen.getByRole('button', { name: /Review & Import/i });
    reviewButton.focus();
    expect(reviewButton).toHaveFocus();

    // Press Enter to activate
    fireEvent.keyDown(reviewButton, { key: 'Enter', code: 'Enter' });
    await userEvent.keyboard('{Enter}');

    // Should call onReview
    expect(onReview).toHaveBeenCalled();
  });

  it('BulkImportModal announces loading state to screen readers', async () => {
    const onClose = jest.fn();
    const onImport = jest
      .fn()
      .mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));

    render(
      <TestWrapper>
        <BulkImportModal
          artifacts={mockArtifacts}
          open={true}
          onClose={onClose}
          onImport={onImport}
        />
      </TestWrapper>
    );

    // Select an artifact
    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]);

    // Click import
    const importButton = screen.getByRole('button', { name: /Import \(1\)/i });
    await userEvent.click(importButton);

    // Should announce loading to screen readers
    await waitFor(() => {
      const loadingAnnouncement = screen.getByText(/Importing.*artifacts.*please wait/i);
      expect(loadingAnnouncement).toBeInTheDocument();
      expect(loadingAnnouncement).toHaveAttribute('role', 'status');
      expect(loadingAnnouncement).toHaveAttribute('aria-live', 'polite');
    });
  });
});
