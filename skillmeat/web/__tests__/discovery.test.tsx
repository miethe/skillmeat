/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DiscoveryBanner } from '@/components/discovery/DiscoveryBanner';
import { BulkImportModal } from '@/components/discovery/BulkImportModal';
import type { DiscoveredArtifact } from '@/types/discovery';

// Test wrapper with providers
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('DiscoveryBanner', () => {
  it('displays discovered count', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner discoveredCount={5} onReview={onReview} />
      </TestWrapper>
    );
    expect(screen.getByText(/Found 5 Artifacts/i)).toBeInTheDocument();
  });

  it('displays correct singular form', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner discoveredCount={1} onReview={onReview} />
      </TestWrapper>
    );
    expect(screen.getByText(/Found 1 Artifact$/i)).toBeInTheDocument();
  });

  it('calls onReview when button clicked', async () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner discoveredCount={5} onReview={onReview} />
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
        <DiscoveryBanner discoveredCount={5} onReview={onReview} dismissible />
      </TestWrapper>
    );

    expect(screen.getByText(/Found 5 Artifacts/i)).toBeInTheDocument();

    const dismissButton = screen.getByRole('button', { name: /Dismiss/i });
    await userEvent.click(dismissButton);

    await waitFor(() => {
      expect(screen.queryByText(/Found 5 Artifacts/i)).not.toBeInTheDocument();
    });
  });

  it('can be closed with X button when dismissible', async () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner discoveredCount={5} onReview={onReview} dismissible />
      </TestWrapper>
    );

    const closeButton = screen.getByRole('button', { name: /Close/i });
    await userEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText(/Found 5 Artifacts/i)).not.toBeInTheDocument();
    });
  });

  it('returns null when discoveredCount is 0', () => {
    const onReview = jest.fn();
    const { container } = render(
      <TestWrapper>
        <DiscoveryBanner discoveredCount={0} onReview={onReview} />
      </TestWrapper>
    );
    expect(container.firstChild).toBeNull();
  });

  it('does not show dismiss buttons when dismissible is false', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner discoveredCount={5} onReview={onReview} dismissible={false} />
      </TestWrapper>
    );

    expect(screen.queryByRole('button', { name: /Dismiss/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Close/i })).not.toBeInTheDocument();
  });

  it('has proper ARIA attributes', () => {
    const onReview = jest.fn();
    render(
      <TestWrapper>
        <DiscoveryBanner discoveredCount={5} onReview={onReview} />
      </TestWrapper>
    );

    const alert = screen.getByRole('status');
    expect(alert).toHaveAttribute('aria-live', 'polite');
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
      expect(onImport).toHaveBeenCalledWith([mockArtifacts[0]]);
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
});
