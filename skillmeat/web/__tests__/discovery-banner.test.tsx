/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DiscoveryBanner } from '@/components/discovery/DiscoveryBanner';

// Create mock functions that can be spied on
const mockTrackBannerView = jest.fn();
const mockTrackScan = jest.fn();
const mockTrackModalOpen = jest.fn();
const mockTrackImport = jest.fn();

// Mock the analytics hook
jest.mock('@/lib/analytics', () => ({
  useTrackDiscovery: () => ({
    trackBannerView: mockTrackBannerView,
    trackScan: mockTrackScan,
    trackModalOpen: mockTrackModalOpen,
    trackImport: mockTrackImport,
  }),
}));

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
  const defaultProps = {
    importableCount: 5,
    onReview: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Display Logic', () => {
    it('displays importable count, not total discovered', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={7}
            discoveredCount={13}
            onReview={jest.fn()}
          />
        </TestWrapper>
      );

      expect(screen.getByText(/7 Artifacts Ready to Import/i)).toBeInTheDocument();
      expect(screen.getByText(/Found 13 total - 7 remaining/i)).toBeInTheDocument();
    });

    it('hides when importable count is 0', () => {
      const { container } = render(
        <TestWrapper>
          <DiscoveryBanner importableCount={0} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(container.firstChild).toBeNull();
    });

    it('shows singular "Artifact" when count is 1', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={1} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(screen.getByText('1 Artifact Ready to Import')).toBeInTheDocument();
    });

    it('shows plural "Artifacts" when count is greater than 1', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={5} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(screen.getByText('5 Artifacts Ready to Import')).toBeInTheDocument();
    });

    it('does not show total count info when discoveredCount equals importableCount', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={5}
            discoveredCount={5}
            onReview={jest.fn()}
          />
        </TestWrapper>
      );

      // Should not show "Found X total - Y remaining" when counts are equal
      expect(screen.queryByText(/Found.*total/i)).not.toBeInTheDocument();
    });

    it('does not show total count info when discoveredCount is not provided', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={5} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(screen.queryByText(/Found.*total/i)).not.toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('calls onReview when Review & Import button is clicked', async () => {
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

    it('can be dismissed via Dismiss button', async () => {
      const { container } = render(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={5}
            onReview={jest.fn()}
            dismissible={true}
          />
        </TestWrapper>
      );

      expect(container.firstChild).not.toBeNull();

      const dismissButton = screen.getByRole('button', { name: /Dismiss notification/i });
      await userEvent.click(dismissButton);

      expect(container.firstChild).toBeNull();
    });

    it('can be dismissed via close icon', async () => {
      const { container } = render(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={5}
            onReview={jest.fn()}
            dismissible={true}
          />
        </TestWrapper>
      );

      const closeButton = screen.getByRole('button', { name: /Close/i });
      await userEvent.click(closeButton);

      expect(container.firstChild).toBeNull();
    });

    it('does not show dismiss buttons when dismissible is false', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={5}
            onReview={jest.fn()}
            dismissible={false}
          />
        </TestWrapper>
      );

      expect(screen.queryByRole('button', { name: /Dismiss notification/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Close/i })).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA role and live region', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={5} onReview={jest.fn()} />
        </TestWrapper>
      );

      const alert = screen.getByRole('status');
      expect(alert).toHaveAttribute('aria-live', 'polite');
    });

    it('has accessible labels for buttons', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={5}
            onReview={jest.fn()}
            dismissible={true}
          />
        </TestWrapper>
      );

      expect(screen.getByRole('button', { name: /Review & Import/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Dismiss notification/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Close/i })).toBeInTheDocument();
    });

    it('keyboard navigation works for Review button', async () => {
      const onReview = jest.fn();
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={5} onReview={onReview} />
        </TestWrapper>
      );

      const reviewButton = screen.getByRole('button', { name: /Review & Import/i });
      reviewButton.focus();
      expect(reviewButton).toHaveFocus();

      // Press Enter to activate
      await userEvent.keyboard('{Enter}');
      expect(onReview).toHaveBeenCalled();
    });
  });

  describe('Analytics Tracking', () => {
    it('tracks banner view when mounted with importable artifacts', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={5} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(mockTrackBannerView).toHaveBeenCalledWith(5);
    });

    it('does not track when importable count is 0', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={0} onReview={jest.fn()} />
        </TestWrapper>
      );

      // Check that the mock was never called with 0 in this render
      // Note: mockTrackBannerView might have been called in previous tests
      // So we just check it wasn't called during this test's render
      const callsBefore = mockTrackBannerView.mock.calls.length;

      // Re-render to ensure it stays not called
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={0} onReview={jest.fn()} />
        </TestWrapper>
      );

      // Should not have added new calls
      expect(mockTrackBannerView.mock.calls.length).toBe(callsBefore);
    });

    it('tracks banner view with correct count when discoveredCount is different', () => {
      mockTrackBannerView.mockClear();

      render(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={3}
            discoveredCount={10}
            onReview={jest.fn()}
          />
        </TestWrapper>
      );

      // Should track importableCount, not discoveredCount
      expect(mockTrackBannerView).toHaveBeenCalledWith(3);
    });
  });

  describe('Edge Cases', () => {
    it('handles large counts correctly', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={999} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(screen.getByText('999 Artifacts Ready to Import')).toBeInTheDocument();
    });

    it('handles dismissal and remounting', async () => {
      const { rerender } = render(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={5}
            onReview={jest.fn()}
            dismissible={true}
          />
        </TestWrapper>
      );

      // Dismiss the banner
      const dismissButton = screen.getByRole('button', { name: /Dismiss notification/i });
      await userEvent.click(dismissButton);
      expect(screen.queryByText(/5 Artifacts Ready to Import/i)).not.toBeInTheDocument();

      // Remount with different count (simulates new discovery)
      rerender(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={3}
            onReview={jest.fn()}
            dismissible={true}
          />
        </TestWrapper>
      );

      // Banner should still be dismissed (component maintains state)
      expect(screen.queryByText(/3 Artifacts Ready to Import/i)).not.toBeInTheDocument();
    });

    it('handles rapid clicks on Review button', async () => {
      const onReview = jest.fn();
      render(
        <TestWrapper>
          <DiscoveryBanner importableCount={5} onReview={onReview} />
        </TestWrapper>
      );

      const reviewButton = screen.getByRole('button', { name: /Review & Import/i });

      // Click multiple times rapidly
      await userEvent.click(reviewButton);
      await userEvent.click(reviewButton);
      await userEvent.click(reviewButton);

      expect(onReview).toHaveBeenCalledTimes(3);
    });

    it('displays correctly with very long source strings', () => {
      render(
        <TestWrapper>
          <DiscoveryBanner
            importableCount={5}
            discoveredCount={100}
            onReview={jest.fn()}
          />
        </TestWrapper>
      );

      expect(screen.getByText(/Found 100 total - 5 remaining/i)).toBeInTheDocument();
    });
  });

  describe('Component Lifecycle', () => {
    it('cleans up properly on unmount', () => {
      const { unmount } = render(
        <TestWrapper>
          <DiscoveryBanner importableCount={5} onReview={jest.fn()} />
        </TestWrapper>
      );

      unmount();
      // No errors should be thrown
      expect(screen.queryByText(/5 Artifacts Ready to Import/i)).not.toBeInTheDocument();
    });

    it('updates correctly when props change', () => {
      const { rerender } = render(
        <TestWrapper>
          <DiscoveryBanner importableCount={5} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(screen.getByText('5 Artifacts Ready to Import')).toBeInTheDocument();

      // Update count
      rerender(
        <TestWrapper>
          <DiscoveryBanner importableCount={3} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(screen.getByText('3 Artifacts Ready to Import')).toBeInTheDocument();
    });

    it('re-tracks when importableCount changes', () => {
      mockTrackBannerView.mockClear();

      const { rerender } = render(
        <TestWrapper>
          <DiscoveryBanner importableCount={5} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(mockTrackBannerView).toHaveBeenCalledWith(5);

      // Update count
      rerender(
        <TestWrapper>
          <DiscoveryBanner importableCount={3} onReview={jest.fn()} />
        </TestWrapper>
      );

      expect(mockTrackBannerView).toHaveBeenCalledWith(3);
      expect(mockTrackBannerView).toHaveBeenCalledTimes(2);
    });
  });
});
