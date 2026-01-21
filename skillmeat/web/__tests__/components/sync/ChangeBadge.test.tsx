/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import { ChangeBadge } from '@/components/sync/ChangeBadge';
import type { ChangeOrigin } from '@/types/drift';

describe('ChangeBadge', () => {
  const variants: ChangeOrigin[] = ['upstream', 'local', 'both', 'none'];

  describe('renders all variants', () => {
    it.each(variants)('renders %s variant', (origin) => {
      render(<ChangeBadge origin={origin} />);
      expect(screen.getByText(getExpectedLabel(origin))).toBeInTheDocument();
    });

    it.each(variants)('renders %s variant with correct icon', (origin) => {
      render(<ChangeBadge origin={origin} />);
      const expectedIcon = getExpectedIcon(origin);
      expect(screen.getByText(expectedIcon)).toBeInTheDocument();
    });
  });

  describe('color classes', () => {
    it('applies blue colors for upstream', () => {
      const { container } = render(<ChangeBadge origin="upstream" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('bg-blue-100', 'text-blue-700', 'border-blue-200');
    });

    it('applies amber colors for local', () => {
      const { container } = render(<ChangeBadge origin="local" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('bg-amber-100', 'text-amber-700', 'border-amber-200');
    });

    it('applies red colors for conflict (both)', () => {
      const { container } = render(<ChangeBadge origin="both" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('bg-red-100', 'text-red-700', 'border-red-200');
    });

    it('applies gray colors for none', () => {
      const { container } = render(<ChangeBadge origin="none" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('bg-gray-100', 'text-gray-600', 'border-gray-200');
    });
  });

  describe('size variants', () => {
    it('applies small size classes', () => {
      const { container } = render(<ChangeBadge origin="upstream" size="sm" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-xs', 'px-1.5', 'py-0.5');
    });

    it('applies medium size classes (default)', () => {
      const { container } = render(<ChangeBadge origin="upstream" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-sm', 'px-2', 'py-1');
    });

    it('applies large size classes', () => {
      const { container } = render(<ChangeBadge origin="upstream" size="lg" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-base', 'px-3', 'py-1.5');
    });
  });

  describe('showLabel prop', () => {
    it('shows label by default', () => {
      render(<ChangeBadge origin="upstream" />);
      expect(screen.getByText('Upstream')).toBeInTheDocument();
    });

    it('hides label when showLabel=false', () => {
      render(<ChangeBadge origin="upstream" showLabel={false} />);
      expect(screen.queryByText('Upstream')).not.toBeInTheDocument();
    });

    it('still shows icon when label hidden', () => {
      render(<ChangeBadge origin="upstream" showLabel={false} />);
      // Icon should still be present (↓ for upstream)
      expect(screen.getByText('↓')).toBeInTheDocument();
    });

    it('hides label for all variants when showLabel=false', () => {
      variants.forEach((origin) => {
        const { unmount } = render(<ChangeBadge origin={origin} showLabel={false} />);
        const label = getExpectedLabel(origin);
        expect(screen.queryByText(label)).not.toBeInTheDocument();
        // But icon should still be visible
        const icon = getExpectedIcon(origin);
        expect(screen.getByText(icon)).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('showTooltip prop', () => {
    it('wraps badge in tooltip when enabled (default)', () => {
      const { container } = render(<ChangeBadge origin="upstream" />);
      // When tooltip is enabled, badge should be wrapped in TooltipTrigger
      // Check for Radix tooltip trigger attribute
      const tooltipTrigger = container.querySelector('[data-state]');
      expect(tooltipTrigger).toBeInTheDocument();
    });

    it('does not wrap badge in tooltip when disabled', () => {
      const { container } = render(<ChangeBadge origin="upstream" showTooltip={false} />);
      // When tooltip is disabled, badge should not have tooltip trigger attributes
      // The component structure should be simpler without tooltip wrappers
      const badge = container.firstChild;
      expect(badge).toBeInTheDocument();
      // Badge should not have tooltip-related attributes
      expect(badge).not.toHaveAttribute('data-state');
    });

    it('badge is still rendered when tooltip disabled', () => {
      render(<ChangeBadge origin="upstream" showTooltip={false} />);
      expect(screen.getByText('Upstream')).toBeInTheDocument();
      expect(screen.getByText('↓')).toBeInTheDocument();
    });
  });

  describe('icons', () => {
    it.each([
      ['upstream', '↓'],
      ['local', '✎'],
      ['both', '⚠'],
      ['none', '✓'],
    ] as const)('shows correct icon for %s', (origin, expectedIcon) => {
      render(<ChangeBadge origin={origin} />);
      expect(screen.getByText(expectedIcon)).toBeInTheDocument();
    });

    it('icon appears before label', () => {
      const { container } = render(<ChangeBadge origin="upstream" />);
      const badge = container.firstChild;
      const textContent = badge?.textContent || '';
      // Icon (↓) should come before label (Upstream)
      expect(textContent.indexOf('↓')).toBeLessThan(textContent.indexOf('Upstream'));
    });
  });

  describe('className prop', () => {
    it('accepts custom className', () => {
      const { container } = render(<ChangeBadge origin="upstream" className="custom-class" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('custom-class');
    });

    it('merges custom className with default classes', () => {
      const { container } = render(<ChangeBadge origin="upstream" className="custom-class" />);
      const badge = container.firstChild;
      // Should have both custom and default classes
      expect(badge).toHaveClass('custom-class');
      expect(badge).toHaveClass('bg-blue-100');
    });
  });

  describe('accessibility', () => {
    it('renders as a badge element', () => {
      const { container } = render(<ChangeBadge origin="upstream" />);
      // Badge component should render with proper role/attributes
      expect(container.firstChild).toBeInTheDocument();
    });

    it('badge content is readable', () => {
      render(<ChangeBadge origin="upstream" />);
      // Both icon and text should be present
      expect(screen.getByText('↓')).toBeInTheDocument();
      expect(screen.getByText('Upstream')).toBeInTheDocument();
    });

    it('badge without label still has icon for visual indication', () => {
      render(<ChangeBadge origin="upstream" showLabel={false} />);
      // Icon provides visual indication even without text
      expect(screen.getByText('↓')).toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('handles all ChangeOrigin values', () => {
      // Ensure all possible values work
      const allOrigins: ChangeOrigin[] = ['upstream', 'local', 'both', 'none'];
      allOrigins.forEach((origin) => {
        const { unmount } = render(<ChangeBadge origin={origin} />);
        expect(screen.getByText(getExpectedLabel(origin))).toBeInTheDocument();
        unmount();
      });
    });

    it('renders with minimal props (only origin)', () => {
      render(<ChangeBadge origin="upstream" />);
      expect(screen.getByText('Upstream')).toBeInTheDocument();
    });

    it('renders with all props', () => {
      render(
        <ChangeBadge
          origin="upstream"
          size="lg"
          showLabel={true}
          showTooltip={true}
          className="extra-class"
        />
      );
      expect(screen.getByText('Upstream')).toBeInTheDocument();
    });
  });

  describe('variant combinations', () => {
    it('combines size and showLabel props', () => {
      const { container } = render(<ChangeBadge origin="upstream" size="sm" showLabel={false} />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-xs'); // Small size
      expect(screen.queryByText('Upstream')).not.toBeInTheDocument(); // No label
      expect(screen.getByText('↓')).toBeInTheDocument(); // Icon still present
    });

    it('combines showLabel and showTooltip props', () => {
      render(<ChangeBadge origin="upstream" showLabel={false} showTooltip={false} />);
      expect(screen.queryByText('Upstream')).not.toBeInTheDocument();
      expect(screen.getByText('↓')).toBeInTheDocument();
    });
  });

  describe('visual consistency', () => {
    it('applies consistent base classes across all variants', () => {
      variants.forEach((origin) => {
        const { container, unmount } = render(<ChangeBadge origin={origin} />);
        const badge = container.firstChild;
        // All badges should have these base classes
        expect(badge).toHaveClass('font-medium', 'border', 'cursor-default');
        unmount();
      });
    });

    it('each variant has unique color scheme', () => {
      const upstreamBadge = render(<ChangeBadge origin="upstream" />).container.firstChild;
      const localBadge = render(<ChangeBadge origin="local" />).container.firstChild;
      const bothBadge = render(<ChangeBadge origin="both" />).container.firstChild;
      const noneBadge = render(<ChangeBadge origin="none" />).container.firstChild;

      // Each should have different background colors
      expect(upstreamBadge).toHaveClass('bg-blue-100');
      expect(localBadge).toHaveClass('bg-amber-100');
      expect(bothBadge).toHaveClass('bg-red-100');
      expect(noneBadge).toHaveClass('bg-gray-100');
    });
  });
});

// Helper functions
function getExpectedLabel(origin: ChangeOrigin): string {
  const labels: Record<ChangeOrigin, string> = {
    upstream: 'Upstream',
    local: 'Local',
    both: 'Conflict',
    none: 'No Changes',
  };
  return labels[origin];
}

function getExpectedIcon(origin: ChangeOrigin): string {
  const icons: Record<ChangeOrigin, string> = {
    upstream: '↓',
    local: '✎',
    both: '⚠',
    none: '✓',
  };
  return icons[origin];
}
