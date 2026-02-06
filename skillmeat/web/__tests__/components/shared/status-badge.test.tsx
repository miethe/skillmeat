/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '@/components/shared/status-badge';
import type { SyncStatus } from '@/types/artifact';

describe('StatusBadge', () => {
  const allStatuses: SyncStatus[] = ['synced', 'modified', 'outdated', 'conflict', 'error'];

  describe('renders all status types', () => {
    it.each(allStatuses)('renders %s status correctly', (status) => {
      render(<StatusBadge status={status} />);
      const badge = screen.getByLabelText(`Status: ${getExpectedLabel(status)}`);
      expect(badge).toBeInTheDocument();
    });

    it.each(allStatuses)('displays correct label for %s status', (status) => {
      render(<StatusBadge status={status} />);
      expect(screen.getByText(getExpectedLabel(status))).toBeInTheDocument();
    });
  });

  describe('icon display', () => {
    it('shows icon by default', () => {
      render(<StatusBadge status="synced" />);
      // Icon should be present (aria-hidden, so we check for the badge structure)
      const badge = screen.getByLabelText('Status: Synced');
      expect(badge).toBeInTheDocument();
      // Icon is rendered with aria-hidden="true"
      expect(badge.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
    });

    it('hides icon when showIcon=false', () => {
      render(<StatusBadge status="synced" showIcon={false} />);
      const badge = screen.getByLabelText('Status: Synced');
      // Should not have hidden icon element
      expect(badge.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
    });

    it('still shows label when icon hidden', () => {
      render(<StatusBadge status="modified" showIcon={false} />);
      expect(screen.getByText('Modified')).toBeInTheDocument();
    });
  });

  describe('label display', () => {
    it('shows label by default', () => {
      render(<StatusBadge status="outdated" />);
      expect(screen.getByText('Outdated')).toBeInTheDocument();
    });

    it('hides label when showLabel=false', () => {
      render(<StatusBadge status="outdated" showLabel={false} />);
      expect(screen.queryByText('Outdated')).not.toBeInTheDocument();
    });

    it('still shows icon when label hidden', () => {
      render(<StatusBadge status="conflict" showLabel={false} />);
      const badge = screen.getByLabelText('Status: Conflict');
      expect(badge.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
    });
  });

  describe('returns null when both icon and label are hidden', () => {
    it('returns null when showIcon=false and showLabel=false', () => {
      const { container } = render(
        <StatusBadge status="synced" showIcon={false} showLabel={false} />
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe('size variants', () => {
    it('renders with small size', () => {
      render(<StatusBadge status="synced" size="sm" />);
      expect(screen.getByLabelText('Status: Synced')).toBeInTheDocument();
    });

    it('renders with medium size (default)', () => {
      render(<StatusBadge status="synced" />);
      expect(screen.getByLabelText('Status: Synced')).toBeInTheDocument();
    });

    it('renders with large size', () => {
      render(<StatusBadge status="synced" size="lg" />);
      expect(screen.getByLabelText('Status: Synced')).toBeInTheDocument();
    });

    it.each(['sm', 'md', 'lg'] as const)('applies %s size correctly', (size) => {
      const { container } = render(<StatusBadge status="synced" size={size} />);
      const badge = container.firstChild;
      expect(badge).toBeInTheDocument();
    });
  });

  describe('color coding per status', () => {
    it('applies green colors for synced', () => {
      const { container } = render(<StatusBadge status="synced" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-green-600');
    });

    it('applies yellow colors for modified', () => {
      const { container } = render(<StatusBadge status="modified" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-yellow-600');
    });

    it('applies orange colors for outdated', () => {
      const { container } = render(<StatusBadge status="outdated" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-orange-600');
    });

    it('applies destructive colors for conflict', () => {
      const { container } = render(<StatusBadge status="conflict" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-destructive');
    });

    it('applies red colors for error', () => {
      const { container } = render(<StatusBadge status="error" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-red-600');
    });
  });

  describe('accessibility', () => {
    it('has aria-label with status information', () => {
      render(<StatusBadge status="synced" />);
      expect(screen.getByLabelText('Status: Synced')).toBeInTheDocument();
    });

    it.each(allStatuses)('has correct aria-label for %s status', (status) => {
      render(<StatusBadge status={status} />);
      const expectedLabel = `Status: ${getExpectedLabel(status)}`;
      expect(screen.getByLabelText(expectedLabel)).toBeInTheDocument();
    });

    it('icon has aria-hidden="true"', () => {
      render(<StatusBadge status="synced" />);
      const badge = screen.getByLabelText('Status: Synced');
      const icon = badge.querySelector('[aria-hidden="true"]');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('custom className', () => {
    it('applies custom className', () => {
      const { container } = render(<StatusBadge status="synced" className="custom-class" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('custom-class');
    });

    it('merges custom className with default classes', () => {
      const { container } = render(<StatusBadge status="synced" className="custom-class" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('custom-class');
      expect(badge).toHaveClass('text-green-600');
    });
  });

  describe('prop combinations', () => {
    it('renders with size and showLabel props', () => {
      render(<StatusBadge status="synced" size="lg" showLabel={false} />);
      const badge = screen.getByLabelText('Status: Synced');
      expect(badge).toBeInTheDocument();
      expect(screen.queryByText('Synced')).not.toBeInTheDocument();
    });

    it('renders with size and showIcon props', () => {
      render(<StatusBadge status="modified" size="sm" showIcon={false} />);
      const badge = screen.getByLabelText('Status: Modified');
      expect(badge).toBeInTheDocument();
      expect(badge.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
    });

    it('renders with all props', () => {
      render(
        <StatusBadge
          status="error"
          size="md"
          showIcon={true}
          showLabel={true}
          className="extra-class"
        />
      );
      const badge = screen.getByLabelText('Status: Error');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('extra-class');
    });
  });

  describe('edge cases', () => {
    it('handles all SyncStatus values', () => {
      allStatuses.forEach((status) => {
        const { unmount } = render(<StatusBadge status={status} />);
        expect(screen.getByText(getExpectedLabel(status))).toBeInTheDocument();
        unmount();
      });
    });

    it('renders with minimal props (only status)', () => {
      render(<StatusBadge status="synced" />);
      expect(screen.getByText('Synced')).toBeInTheDocument();
    });
  });
});

// Helper function
function getExpectedLabel(status: SyncStatus): string {
  const labels: Record<SyncStatus, string> = {
    synced: 'Synced',
    modified: 'Modified',
    outdated: 'Outdated',
    conflict: 'Conflict',
    error: 'Error',
  };
  return labels[status];
}
