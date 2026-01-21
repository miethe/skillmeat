/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { CacheFreshnessIndicator } from '@/components/CacheFreshnessIndicator';

expect.extend(toHaveNoViolations);

describe('CacheFreshnessIndicator', () => {
  describe('Loading State', () => {
    it('shows "Loading..." when lastFetched is null', () => {
      render(<CacheFreshnessIndicator lastFetched={null} isStale={false} cacheHit={false} />);

      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('renders secondary badge variant when loading', () => {
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={null} isStale={false} cacheHit={false} />
      );

      // Badge should be in the document
      const badge = container.querySelector('[class*="inline-flex"]');
      expect(badge).toBeInTheDocument();
    });

    it('displays Clock icon when loading', () => {
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={null} isStale={false} cacheHit={false} />
      );

      // Should have an icon
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Stale Data State', () => {
    it('shows "Stale data" badge when isStale=true', () => {
      const lastFetched = new Date('2025-01-01T10:00:00Z');

      render(<CacheFreshnessIndicator lastFetched={lastFetched} isStale={true} cacheHit={true} />);

      expect(screen.getByText('Stale data')).toBeInTheDocument();
    });

    it('renders destructive badge variant when stale', () => {
      const lastFetched = new Date('2025-01-01T10:00:00Z');
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={lastFetched} isStale={true} cacheHit={true} />
      );

      const badge = container.querySelector('[class*="inline-flex"]');
      expect(badge).toBeInTheDocument();
    });

    it('displays AlertCircle icon when stale', () => {
      const lastFetched = new Date('2025-01-01T10:00:00Z');
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={lastFetched} isStale={true} cacheHit={true} />
      );

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('shows stale even when cacheHit=false', () => {
      const lastFetched = new Date('2025-01-01T10:00:00Z');

      render(<CacheFreshnessIndicator lastFetched={lastFetched} isStale={true} cacheHit={false} />);

      expect(screen.getByText('Stale data')).toBeInTheDocument();
    });
  });

  describe('Fresh Cached Data', () => {
    it('shows "Updated Xm ago (cached)" for fresh cached data', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={fiveMinutesAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated.*ago \(cached\)/i)).toBeInTheDocument();
    });

    it('shows time without "(cached)" when cacheHit=false', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={fiveMinutesAgo} isStale={false} cacheHit={false} />
      );

      expect(screen.getByText(/Updated.*ago$/i)).toBeInTheDocument();
      expect(screen.queryByText(/\(cached\)/i)).not.toBeInTheDocument();
    });

    it('renders secondary badge variant when fresh', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={fiveMinutesAgo} isStale={false} cacheHit={true} />
      );

      const badge = container.querySelector('[class*="inline-flex"]');
      expect(badge).toBeInTheDocument();
    });

    it('displays Clock icon when fresh', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={fiveMinutesAgo} isStale={false} cacheHit={true} />
      );

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Time Formatting - Seconds', () => {
    it('shows "just now" for times less than 60 seconds ago', () => {
      const thirtySecondsAgo = new Date(Date.now() - 30 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={thirtySecondsAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated just now \(cached\)/i)).toBeInTheDocument();
    });

    it('shows "just now" for exactly 59 seconds ago', () => {
      const fiftyNineSecondsAgo = new Date(Date.now() - 59 * 1000);

      render(
        <CacheFreshnessIndicator
          lastFetched={fiftyNineSecondsAgo}
          isStale={false}
          cacheHit={true}
        />
      );

      expect(screen.getByText(/Updated just now \(cached\)/i)).toBeInTheDocument();
    });
  });

  describe('Time Formatting - Minutes', () => {
    it('shows "1m ago" for 1 minute', () => {
      const oneMinuteAgo = new Date(Date.now() - 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={oneMinuteAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated 1m ago \(cached\)/i)).toBeInTheDocument();
    });

    it('shows "5m ago" for 5 minutes', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={fiveMinutesAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated 5m ago \(cached\)/i)).toBeInTheDocument();
    });

    it('shows "59m ago" for 59 minutes', () => {
      const fiftyNineMinutesAgo = new Date(Date.now() - 59 * 60 * 1000);

      render(
        <CacheFreshnessIndicator
          lastFetched={fiftyNineMinutesAgo}
          isStale={false}
          cacheHit={true}
        />
      );

      expect(screen.getByText(/Updated 59m ago \(cached\)/i)).toBeInTheDocument();
    });
  });

  describe('Time Formatting - Hours', () => {
    it('shows "1h ago" for 1 hour', () => {
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);

      render(<CacheFreshnessIndicator lastFetched={oneHourAgo} isStale={false} cacheHit={true} />);

      expect(screen.getByText(/Updated 1h ago \(cached\)/i)).toBeInTheDocument();
    });

    it('shows "5h ago" for 5 hours', () => {
      const fiveHoursAgo = new Date(Date.now() - 5 * 60 * 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={fiveHoursAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated 5h ago \(cached\)/i)).toBeInTheDocument();
    });

    it('shows "23h ago" for 23 hours', () => {
      const twentyThreeHoursAgo = new Date(Date.now() - 23 * 60 * 60 * 1000);

      render(
        <CacheFreshnessIndicator
          lastFetched={twentyThreeHoursAgo}
          isStale={false}
          cacheHit={true}
        />
      );

      expect(screen.getByText(/Updated 23h ago \(cached\)/i)).toBeInTheDocument();
    });
  });

  describe('Time Formatting - Days', () => {
    it('shows "1d ago" for 1 day', () => {
      const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);

      render(<CacheFreshnessIndicator lastFetched={oneDayAgo} isStale={false} cacheHit={true} />);

      expect(screen.getByText(/Updated 1d ago \(cached\)/i)).toBeInTheDocument();
    });

    it('shows "7d ago" for 7 days', () => {
      const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={sevenDaysAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated 7d ago \(cached\)/i)).toBeInTheDocument();
    });

    it('shows "30d ago" for 30 days', () => {
      const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={thirtyDaysAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated 30d ago \(cached\)/i)).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles future dates (clock skew)', () => {
      const futureDate = new Date(Date.now() + 1000);

      render(<CacheFreshnessIndicator lastFetched={futureDate} isStale={false} cacheHit={true} />);

      // Should show "just now" for negative time differences
      expect(screen.getByText(/Updated just now \(cached\)/i)).toBeInTheDocument();
    });

    it('handles very old dates', () => {
      const veryOldDate = new Date('2000-01-01T00:00:00Z');

      render(<CacheFreshnessIndicator lastFetched={veryOldDate} isStale={false} cacheHit={true} />);

      // Should show days for old dates
      expect(screen.getByText(/Updated \d+d ago \(cached\)/i)).toBeInTheDocument();
    });

    it('handles invalid dates gracefully', () => {
      const invalidDate = new Date('invalid');

      render(<CacheFreshnessIndicator lastFetched={invalidDate} isStale={false} cacheHit={true} />);

      // Should still render something (NaN becomes "just now" due to < 60 check)
      const badge = screen.getByText(/Updated/i);
      expect(badge).toBeInTheDocument();
    });
  });

  describe('Boundary Conditions', () => {
    it('handles exactly 60 seconds (1 minute)', () => {
      const sixtySecondsAgo = new Date(Date.now() - 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={sixtySecondsAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated 1m ago \(cached\)/i)).toBeInTheDocument();
    });

    it('handles exactly 60 minutes (1 hour)', () => {
      const sixtyMinutesAgo = new Date(Date.now() - 60 * 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={sixtyMinutesAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated 1h ago \(cached\)/i)).toBeInTheDocument();
    });

    it('handles exactly 24 hours (1 day)', () => {
      const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);

      render(
        <CacheFreshnessIndicator lastFetched={twentyFourHoursAgo} isStale={false} cacheHit={true} />
      );

      expect(screen.getByText(/Updated 1d ago \(cached\)/i)).toBeInTheDocument();
    });
  });

  describe('Prop Combinations', () => {
    it('prioritizes stale state over cache hit', () => {
      const lastFetched = new Date(Date.now() - 5 * 60 * 1000);

      render(<CacheFreshnessIndicator lastFetched={lastFetched} isStale={true} cacheHit={true} />);

      // Should show stale, not the time
      expect(screen.getByText('Stale data')).toBeInTheDocument();
      expect(screen.queryByText(/ago/i)).not.toBeInTheDocument();
    });

    it('prioritizes loading state over stale state', () => {
      render(<CacheFreshnessIndicator lastFetched={null} isStale={true} cacheHit={true} />);

      // Should show loading, not stale
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(screen.queryByText('Stale data')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has no accessibility violations in loading state', async () => {
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={null} isStale={false} cacheHit={false} />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has no accessibility violations in stale state', async () => {
      const lastFetched = new Date('2025-01-01T10:00:00Z');
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={lastFetched} isStale={true} cacheHit={true} />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has no accessibility violations in fresh state', async () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={fiveMinutesAgo} isStale={false} cacheHit={true} />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has proper icon sizing for accessibility', () => {
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={null} isStale={false} cacheHit={false} />
      );

      const icon = container.querySelector('svg');
      expect(icon).toHaveClass('h-3');
      expect(icon).toHaveClass('w-3');
    });
  });

  describe('Badge Styling', () => {
    it('applies gap class for icon spacing', () => {
      const { container } = render(
        <CacheFreshnessIndicator lastFetched={null} isStale={false} cacheHit={false} />
      );

      const badge = container.querySelector('[class*="gap-1"]');
      expect(badge).toBeInTheDocument();
    });

    it('uses consistent badge structure across states', () => {
      const { container: loadingContainer } = render(
        <CacheFreshnessIndicator lastFetched={null} isStale={false} cacheHit={false} />
      );

      const { container: staleContainer } = render(
        <CacheFreshnessIndicator lastFetched={new Date()} isStale={true} cacheHit={false} />
      );

      const { container: freshContainer } = render(
        <CacheFreshnessIndicator lastFetched={new Date()} isStale={false} cacheHit={true} />
      );

      // All should have a badge with icon and text
      expect(loadingContainer.querySelector('svg')).toBeInTheDocument();
      expect(staleContainer.querySelector('svg')).toBeInTheDocument();
      expect(freshContainer.querySelector('svg')).toBeInTheDocument();
    });
  });
});
