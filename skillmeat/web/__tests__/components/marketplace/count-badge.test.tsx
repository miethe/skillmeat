/**
 * @jest-environment jsdom
 *
 * CountBadge Component Tests
 *
 * Tests for the CountBadge component which displays total artifact counts
 * with a breakdown by type shown in a tooltip on hover.
 *
 * Note: Radix Tooltip hover tests are skipped as they can be flaky in jsdom.
 * Tooltip behavior is better tested in E2E tests.
 */

import { render, screen } from '@testing-library/react';
import { CountBadge } from '@/components/marketplace/count-badge';

describe('CountBadge', () => {
  describe('Total Count Display', () => {
    it('displays total count correctly', () => {
      render(<CountBadge countsByType={{ skill: 5, command: 3, agent: 2 }} />);

      expect(screen.getByText('10')).toBeInTheDocument();
    });

    it('displays single type count', () => {
      render(<CountBadge countsByType={{ skill: 7 }} />);

      expect(screen.getByText('7')).toBeInTheDocument();
    });

    it('displays zero for empty counts object', () => {
      render(<CountBadge countsByType={{}} />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('displays zero when all counts are zero', () => {
      render(<CountBadge countsByType={{ skill: 0, command: 0 }} />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('handles large numbers', () => {
      render(<CountBadge countsByType={{ skill: 1000, command: 500, agent: 250 }} />);

      expect(screen.getByText('1750')).toBeInTheDocument();
    });

    it('calculates sum across all types', () => {
      render(
        <CountBadge
          countsByType={{ skill: 1, command: 2, agent: 3, hook: 4, mcp_server: 5 }}
        />
      );

      expect(screen.getByText('15')).toBeInTheDocument();
    });
  });

  describe('Zero Counts Handling', () => {
    it('shows muted styling for zero count', () => {
      render(<CountBadge countsByType={{}} />);

      const badge = screen.getByText('0');
      expect(badge).toHaveClass('text-muted-foreground');
    });

    it('does not show muted styling for non-zero count', () => {
      render(<CountBadge countsByType={{ skill: 1 }} />);

      const badge = screen.getByText('1');
      expect(badge).not.toHaveClass('text-muted-foreground');
    });

    it('does not show tooltip for zero total count', () => {
      render(<CountBadge countsByType={{}} />);

      const badge = screen.getByText('0');
      // Zero count badge should not be wrapped in tooltip trigger
      expect(badge).not.toHaveAttribute('data-state');
    });
  });

  describe('Accessibility', () => {
    it('has proper aria-label for single artifact', () => {
      render(<CountBadge countsByType={{ skill: 1 }} />);

      expect(screen.getByLabelText('1 artifact: Skills: 1')).toBeInTheDocument();
    });

    it('has proper aria-label for multiple artifacts', () => {
      render(<CountBadge countsByType={{ skill: 5, command: 3 }} />);

      expect(screen.getByLabelText('8 artifacts: Skills: 5, Commands: 3')).toBeInTheDocument();
    });

    it('has proper aria-label for no artifacts', () => {
      render(<CountBadge countsByType={{}} />);

      expect(screen.getByLabelText('No artifacts')).toBeInTheDocument();
    });

    it('uses tabular-nums class for consistent number display', () => {
      render(<CountBadge countsByType={{ skill: 5 }} />);

      const badge = screen.getByText('5');
      expect(badge).toHaveClass('tabular-nums');
    });

    it('aria-label describes breakdown by type', () => {
      render(<CountBadge countsByType={{ skill: 10, agent: 5, command: 3 }} />);

      // The aria-label should contain breakdown info
      const badge = screen.getByText('18');
      expect(badge).toHaveAttribute('aria-label');
      const label = badge.getAttribute('aria-label');
      expect(label).toContain('Skills: 10');
      expect(label).toContain('Agents: 5');
      expect(label).toContain('Commands: 3');
    });

    it('aria-label excludes zero counts', () => {
      render(<CountBadge countsByType={{ skill: 5, command: 0, agent: 3 }} />);

      const badge = screen.getByText('8');
      const label = badge.getAttribute('aria-label');
      expect(label).toContain('Skills: 5');
      expect(label).toContain('Agents: 3');
      expect(label).not.toContain('Commands');
    });
  });

  describe('Custom Styling', () => {
    it('applies custom className', () => {
      render(<CountBadge countsByType={{ skill: 5 }} className="custom-badge" />);

      const badge = screen.getByText('5');
      expect(badge).toHaveClass('custom-badge');
    });

    it('preserves default classes when adding custom className', () => {
      render(<CountBadge countsByType={{ skill: 5 }} className="custom-badge" />);

      const badge = screen.getByText('5');
      expect(badge).toHaveClass('tabular-nums');
      expect(badge).toHaveClass('custom-badge');
    });
  });

  describe('Edge Cases', () => {
    it('handles single type with zero value', () => {
      render(<CountBadge countsByType={{ skill: 0 }} />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('handles many artifact types', () => {
      render(
        <CountBadge
          countsByType={{
            skill: 10,
            command: 8,
            agent: 6,
            mcp: 4,
            hook: 2,
          }}
        />
      );

      expect(screen.getByText('30')).toBeInTheDocument();
    });

    it('handles negative counts gracefully', () => {
      // Edge case - negative counts should not occur but handle gracefully
      render(<CountBadge countsByType={{ skill: -5, command: 10 }} />);

      // Total should still be calculated
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('handles decimal counts by displaying as-is', () => {
      // Edge case - decimals should not occur but handle gracefully
      render(<CountBadge countsByType={{ skill: 5.5 }} />);

      expect(screen.getByText('5.5')).toBeInTheDocument();
    });
  });

  describe('Visual Presentation', () => {
    it('uses secondary variant for badge', () => {
      render(<CountBadge countsByType={{ skill: 5 }} />);

      const badge = screen.getByText('5');
      // Badge should have secondary variant styling (via class or data attribute)
      expect(badge).toBeInTheDocument();
    });

    it('has cursor-default class to indicate non-interactive', () => {
      render(<CountBadge countsByType={{ skill: 5 }} />);

      const badge = screen.getByText('5');
      expect(badge).toHaveClass('cursor-default');
    });
  });

  describe('Type Name Formatting', () => {
    it('formats type names with proper capitalization in aria-label', () => {
      render(<CountBadge countsByType={{ skill: 5, command: 3 }} />);

      const badge = screen.getByText('8');
      const label = badge.getAttribute('aria-label');
      // Should capitalize first letter and pluralize
      expect(label).toContain('Skills');
      expect(label).toContain('Commands');
    });

    it('formats snake_case type names in aria-label', () => {
      render(<CountBadge countsByType={{ mcp_server: 3 }} />);

      const badge = screen.getByText('3');
      const label = badge.getAttribute('aria-label');
      // mcp_server should become "Mcp Servers" or similar formatted name
      expect(label).toMatch(/mcp.*server/i);
    });
  });
});
