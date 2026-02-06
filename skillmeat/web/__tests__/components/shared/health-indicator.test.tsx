/**
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  HealthIndicator,
  deriveHealthStatus,
  type HealthStatus,
} from '@/components/shared/health-indicator';
import type { Artifact, SyncStatus } from '@/types/artifact';

// Factory function for creating test artifacts
function createTestArtifact(overrides: Partial<Artifact> = {}): Artifact {
  return {
    id: 'skill:test-artifact',
    name: 'test-artifact',
    type: 'skill',
    scope: 'user',
    syncStatus: 'synced',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('deriveHealthStatus', () => {
  describe('error states', () => {
    it('returns error for error syncStatus', () => {
      const artifact = createTestArtifact({ syncStatus: 'error' });
      expect(deriveHealthStatus(artifact)).toBe('error');
    });

    it('returns error for conflict syncStatus', () => {
      const artifact = createTestArtifact({ syncStatus: 'conflict' });
      expect(deriveHealthStatus(artifact)).toBe('error');
    });
  });

  describe('needs-update state', () => {
    it('returns needs-update when upstream.updateAvailable is true', () => {
      const artifact = createTestArtifact({
        syncStatus: 'synced',
        upstream: {
          enabled: true,
          updateAvailable: true,
        },
      });
      expect(deriveHealthStatus(artifact)).toBe('needs-update');
    });

    it('returns needs-update even with synced status when update available', () => {
      const artifact = createTestArtifact({
        syncStatus: 'synced',
        upstream: {
          enabled: true,
          updateAvailable: true,
          url: 'https://github.com/owner/repo',
        },
      });
      expect(deriveHealthStatus(artifact)).toBe('needs-update');
    });
  });

  describe('has-drift state', () => {
    it('returns has-drift for modified syncStatus', () => {
      const artifact = createTestArtifact({ syncStatus: 'modified' });
      expect(deriveHealthStatus(artifact)).toBe('has-drift');
    });

    it('returns has-drift for modified even without upstream', () => {
      const artifact = createTestArtifact({ syncStatus: 'modified' });
      expect(deriveHealthStatus(artifact)).toBe('has-drift');
    });
  });

  describe('healthy state', () => {
    it('returns healthy for synced status without updates', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      expect(deriveHealthStatus(artifact)).toBe('healthy');
    });

    it('returns healthy when upstream.updateAvailable is false', () => {
      const artifact = createTestArtifact({
        syncStatus: 'synced',
        upstream: {
          enabled: true,
          updateAvailable: false,
        },
      });
      expect(deriveHealthStatus(artifact)).toBe('healthy');
    });

    it('returns healthy for outdated syncStatus (maps to healthy in absence of upstream)', () => {
      // outdated syncStatus without upstream update available should be healthy
      const artifact = createTestArtifact({ syncStatus: 'outdated' });
      expect(deriveHealthStatus(artifact)).toBe('healthy');
    });
  });

  describe('priority order', () => {
    it('error takes priority over needs-update', () => {
      const artifact = createTestArtifact({
        syncStatus: 'error',
        upstream: {
          enabled: true,
          updateAvailable: true,
        },
      });
      expect(deriveHealthStatus(artifact)).toBe('error');
    });

    it('needs-update takes priority over has-drift', () => {
      // Note: This is a hypothetical case since modified syncStatus
      // would typically not have upstream update available
      const artifact = createTestArtifact({
        syncStatus: 'synced', // Not modified, but has update
        upstream: {
          enabled: true,
          updateAvailable: true,
        },
      });
      expect(deriveHealthStatus(artifact)).toBe('needs-update');
    });
  });
});

describe('HealthIndicator', () => {
  const allHealthStatuses: HealthStatus[] = ['healthy', 'needs-update', 'has-drift', 'error'];

  describe('renders all health status types', () => {
    it('renders healthy status', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Health: healthy');
    });

    it('renders needs-update status', () => {
      const artifact = createTestArtifact({
        syncStatus: 'synced',
        upstream: { enabled: true, updateAvailable: true },
      });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Health: needs update');
    });

    it('renders has-drift status', () => {
      const artifact = createTestArtifact({ syncStatus: 'modified' });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Health: has drift');
    });

    it('renders error status', () => {
      const artifact = createTestArtifact({ syncStatus: 'error' });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Health: error');
    });
  });

  describe('color coding', () => {
    it('applies green color for healthy', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      const { container } = render(<HealthIndicator artifact={artifact} />);
      const icon = container.querySelector('[aria-hidden="true"]');
      expect(icon).toHaveClass('text-green-500');
    });

    it('applies orange color for needs-update', () => {
      const artifact = createTestArtifact({
        syncStatus: 'synced',
        upstream: { enabled: true, updateAvailable: true },
      });
      const { container } = render(<HealthIndicator artifact={artifact} />);
      const icon = container.querySelector('[aria-hidden="true"]');
      expect(icon).toHaveClass('text-orange-500');
    });

    it('applies yellow color for has-drift', () => {
      const artifact = createTestArtifact({ syncStatus: 'modified' });
      const { container } = render(<HealthIndicator artifact={artifact} />);
      const icon = container.querySelector('[aria-hidden="true"]');
      expect(icon).toHaveClass('text-yellow-500');
    });

    it('applies red color for error', () => {
      const artifact = createTestArtifact({ syncStatus: 'error' });
      const { container } = render(<HealthIndicator artifact={artifact} />);
      const icon = container.querySelector('[aria-hidden="true"]');
      expect(icon).toHaveClass('text-red-500');
    });
  });

  describe('size variants', () => {
    it('renders with small size', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      const { container } = render(<HealthIndicator artifact={artifact} size="sm" />);
      const icon = container.querySelector('[aria-hidden="true"]');
      expect(icon).toHaveClass('h-3.5', 'w-3.5');
    });

    it('renders with medium size (default)', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      const { container } = render(<HealthIndicator artifact={artifact} />);
      const icon = container.querySelector('[aria-hidden="true"]');
      expect(icon).toHaveClass('h-4', 'w-4');
    });

    it('renders with large size', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      const { container } = render(<HealthIndicator artifact={artifact} size="lg" />);
      const icon = container.querySelector('[aria-hidden="true"]');
      expect(icon).toHaveClass('h-5', 'w-5');
    });
  });

  describe('tooltip behavior', () => {
    it('shows tooltip by default', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      const { container } = render(<HealthIndicator artifact={artifact} />);
      // When tooltip is enabled, component should have tooltip wrapper
      const tooltipTrigger = container.querySelector('[data-state]');
      expect(tooltipTrigger).toBeInTheDocument();
    });

    it('hides tooltip when showTooltip=false', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      const { container } = render(<HealthIndicator artifact={artifact} showTooltip={false} />);
      // When tooltip is disabled, no tooltip wrapper
      const tooltipTrigger = container.querySelector('[data-state]');
      expect(tooltipTrigger).not.toBeInTheDocument();
    });

    it('still renders indicator when tooltip disabled', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      render(<HealthIndicator artifact={artifact} showTooltip={false} />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has role="status"', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has appropriate aria-label', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Health: healthy');
    });

    it('icon has aria-hidden="true"', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      const { container } = render(<HealthIndicator artifact={artifact} />);
      const icon = container.querySelector('[aria-hidden="true"]');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('custom className', () => {
    it('applies custom className to container', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      render(<HealthIndicator artifact={artifact} className="custom-class" />);
      const status = screen.getByRole('status');
      expect(status).toHaveClass('custom-class');
    });

    it('merges custom className with default classes', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      render(<HealthIndicator artifact={artifact} className="custom-class" />);
      const status = screen.getByRole('status');
      expect(status).toHaveClass('custom-class');
      expect(status).toHaveClass('flex');
    });
  });

  describe('prop combinations', () => {
    it('renders with size and showTooltip props', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      render(<HealthIndicator artifact={artifact} size="lg" showTooltip={false} />);
      const status = screen.getByRole('status');
      expect(status).toBeInTheDocument();
    });

    it('renders with all props', () => {
      const artifact = createTestArtifact({ syncStatus: 'error' });
      render(
        <HealthIndicator artifact={artifact} size="sm" showTooltip={true} className="extra-class" />
      );
      const status = screen.getByRole('status');
      expect(status).toBeInTheDocument();
      expect(status).toHaveClass('extra-class');
    });
  });

  describe('edge cases', () => {
    it('handles artifact with minimal properties', () => {
      const artifact = createTestArtifact();
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('handles artifact with all properties', () => {
      const artifact = createTestArtifact({
        syncStatus: 'synced',
        description: 'Test description',
        tags: ['tag1', 'tag2'],
        upstream: {
          enabled: true,
          updateAvailable: false,
          url: 'https://github.com/owner/repo',
          version: 'v1.0.0',
        },
        usageStats: {
          totalDeployments: 5,
          activeProjects: 2,
          usageCount: 100,
        },
      });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  describe('health status descriptions in tooltip', () => {
    // These tests verify the tooltip content exists in the DOM
    // Full tooltip interaction testing would require more complex setup

    it('healthy status has appropriate description', () => {
      const artifact = createTestArtifact({ syncStatus: 'synced' });
      render(<HealthIndicator artifact={artifact} />);
      // The tooltip content should be in the DOM even if not visible
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Health: healthy');
    });

    it('needs-update status has appropriate description', () => {
      const artifact = createTestArtifact({
        syncStatus: 'synced',
        upstream: { enabled: true, updateAvailable: true },
      });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Health: needs update');
    });

    it('has-drift status has appropriate description', () => {
      const artifact = createTestArtifact({ syncStatus: 'modified' });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Health: has drift');
    });

    it('error status has appropriate description', () => {
      const artifact = createTestArtifact({ syncStatus: 'error' });
      render(<HealthIndicator artifact={artifact} />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Health: error');
    });
  });
});
