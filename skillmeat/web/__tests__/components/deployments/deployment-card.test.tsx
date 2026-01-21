/**
 * Unit tests for DeploymentCard component
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import {
  DeploymentCard,
  DeploymentCardSkeleton,
  type Deployment,
} from '@/components/deployments/deployment-card';

// Mock the clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn(() => Promise.resolve()),
  },
});

describe('DeploymentCard', () => {
  const mockDeployment: Deployment = {
    id: 'deploy-1',
    artifact_name: 'pdf-extractor',
    artifact_type: 'skill',
    from_collection: 'my-collection',
    deployed_at: '2024-12-10T10:00:00Z',
    artifact_path: '.claude/skills/user/pdf-extractor.md',
    collection_sha: 'abc123def456',
    local_modifications: false,
    sync_status: 'synced',
    deployed_version: '1.2.0',
    latest_version: '1.2.0',
    status: 'current',
  };

  const mockCallbacks = {
    onUpdate: jest.fn(),
    onRemove: jest.fn(),
    onViewSource: jest.fn(),
    onViewDiff: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders deployment name', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      expect(screen.getByText('pdf-extractor')).toBeInTheDocument();
    });

    it('renders artifact type', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      expect(screen.getByText('skill')).toBeInTheDocument();
    });

    it('renders deployment path', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      expect(screen.getByText('.claude/skills/user/pdf-extractor.md')).toBeInTheDocument();
    });

    it('renders collection source', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      expect(screen.getByText('my-collection')).toBeInTheDocument();
    });

    it('renders deployed version', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      expect(screen.getByText('1.2.0')).toBeInTheDocument();
    });

    it('renders truncated commit SHA', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      expect(screen.getByText('abc123d')).toBeInTheDocument();
    });
  });

  describe('Status Indicators', () => {
    it('shows "Up to date" status for current deployments', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      expect(screen.getByText('Up to date')).toBeInTheDocument();
    });

    it('shows "Update available" status for outdated deployments', () => {
      const outdatedDeployment: Deployment = {
        ...mockDeployment,
        deployed_version: '1.0.0',
        latest_version: '1.2.0',
        status: 'outdated',
        sync_status: 'outdated',
      };

      render(<DeploymentCard deployment={outdatedDeployment} />);
      expect(screen.getByText('Update available')).toBeInTheDocument();
    });

    it('shows "Error" status for error deployments', () => {
      const errorDeployment: Deployment = {
        ...mockDeployment,
        status: 'error',
      };

      render(<DeploymentCard deployment={errorDeployment} />);
      expect(screen.getByText('Error')).toBeInTheDocument();
    });

    it('displays local modifications warning', () => {
      const modifiedDeployment: Deployment = {
        ...mockDeployment,
        local_modifications: true,
      };

      render(<DeploymentCard deployment={modifiedDeployment} />);
      expect(screen.getByText('Local modifications detected')).toBeInTheDocument();
    });

    it('displays sync status when not synced', () => {
      const modifiedDeployment: Deployment = {
        ...mockDeployment,
        sync_status: 'modified',
      };

      render(<DeploymentCard deployment={modifiedDeployment} />);
      expect(screen.getByText('Modified')).toBeInTheDocument();
    });

    it('displays update available warning for outdated deployments', () => {
      const outdatedDeployment: Deployment = {
        ...mockDeployment,
        status: 'outdated',
      };

      render(<DeploymentCard deployment={outdatedDeployment} />);
      expect(screen.getByText('Update available in collection')).toBeInTheDocument();
    });
  });

  describe('Version Display', () => {
    it('shows only deployed version when versions match', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      expect(screen.getByText(/Deployed:/)).toBeInTheDocument();
      expect(screen.queryByText(/Available:/)).not.toBeInTheDocument();
    });

    it('shows both deployed and latest version when different', () => {
      const outdatedDeployment: Deployment = {
        ...mockDeployment,
        deployed_version: '1.0.0',
        latest_version: '1.2.0',
        status: 'outdated',
      };

      render(<DeploymentCard deployment={outdatedDeployment} />);
      expect(screen.getByText(/Deployed:/)).toBeInTheDocument();
      expect(screen.getByText(/Available:/)).toBeInTheDocument();
      expect(screen.getByText('1.0.0')).toBeInTheDocument();
      expect(screen.getByText('1.2.0')).toBeInTheDocument();
    });
  });

  describe('Actions Menu', () => {
    it('opens actions menu on click', async () => {
      render(<DeploymentCard deployment={mockDeployment} {...mockCallbacks} />);

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.getByText('View in Collection')).toBeInTheDocument();
        expect(screen.getByText('Copy Path')).toBeInTheDocument();
        expect(screen.getByText('Remove')).toBeInTheDocument();
      });
    });

    it('shows update action for outdated deployments', async () => {
      const outdatedDeployment: Deployment = {
        ...mockDeployment,
        status: 'outdated',
      };

      render(<DeploymentCard deployment={outdatedDeployment} {...mockCallbacks} />);

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.getByText('Update to Latest')).toBeInTheDocument();
      });
    });

    it('shows view diff action for deployments with local modifications', async () => {
      const modifiedDeployment: Deployment = {
        ...mockDeployment,
        local_modifications: true,
      };

      render(<DeploymentCard deployment={modifiedDeployment} {...mockCallbacks} />);

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.getByText('View Diff')).toBeInTheDocument();
      });
    });

    it('calls onViewSource when View in Collection clicked', async () => {
      render(<DeploymentCard deployment={mockDeployment} {...mockCallbacks} />);

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const viewSourceButton = screen.getByText('View in Collection');
        fireEvent.click(viewSourceButton);
      });

      expect(mockCallbacks.onViewSource).toHaveBeenCalled();
    });

    it('copies path to clipboard when Copy Path clicked', async () => {
      render(<DeploymentCard deployment={mockDeployment} {...mockCallbacks} />);

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const copyButton = screen.getByText('Copy Path');
        fireEvent.click(copyButton);
      });

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        '.claude/skills/user/pdf-extractor.md'
      );
    });

    it('shows confirmation dialog before removing deployment', async () => {
      render(<DeploymentCard deployment={mockDeployment} {...mockCallbacks} />);

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Remove Deployment?')).toBeInTheDocument();
        expect(screen.getByText(/This will remove "pdf-extractor"/)).toBeInTheDocument();
      });
    });

    it('calls onRemove when removal confirmed', async () => {
      render(<DeploymentCard deployment={mockDeployment} {...mockCallbacks} />);

      // Open menu
      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      // Click remove
      await waitFor(() => {
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
      });

      // Confirm removal
      await waitFor(() => {
        const confirmButton = screen.getAllByText('Remove').find((el) => el.tagName === 'BUTTON');
        if (confirmButton) fireEvent.click(confirmButton);
      });

      await waitFor(() => {
        expect(mockCallbacks.onRemove).toHaveBeenCalled();
      });
    });
  });

  describe('Type-specific Styling', () => {
    it.each([
      ['skill', 'border-l-blue-500', 'bg-blue-500/[0.02]'],
      ['command', 'border-l-purple-500', 'bg-purple-500/[0.02]'],
      ['agent', 'border-l-green-500', 'bg-green-500/[0.02]'],
      ['mcp', 'border-l-orange-500', 'bg-orange-500/[0.02]'],
      ['hook', 'border-l-pink-500', 'bg-pink-500/[0.02]'],
    ])('applies correct styling for %s type', (type, borderClass, bgClass) => {
      const deployment: Deployment = {
        ...mockDeployment,
        artifact_type: type as any,
      };

      const { container } = render(<DeploymentCard deployment={deployment} />);
      const card = container.querySelector('[class*="border-l-4"]');

      expect(card).toHaveClass(borderClass);
      expect(card).toHaveClass(bgClass);
    });
  });

  describe('Skeleton Loading State', () => {
    it('renders skeleton correctly', () => {
      const { container } = render(<DeploymentCardSkeleton />);
      const skeletonElements = container.querySelectorAll('.animate-pulse');

      expect(skeletonElements.length).toBeGreaterThan(0);
    });
  });

  describe('Accessibility', () => {
    it('has accessible menu button', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      const menuButton = screen.getByRole('button', { name: /open menu/i });

      expect(menuButton).toBeInTheDocument();
    });

    it('provides title tooltips for truncated content', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      const nameElement = screen.getByTitle('pdf-extractor');

      expect(nameElement).toBeInTheDocument();
    });

    it('provides full SHA in commit tooltip', () => {
      render(<DeploymentCard deployment={mockDeployment} />);
      const commitElement = screen.getByTitle('Commit: abc123def456');

      expect(commitElement).toBeInTheDocument();
    });
  });
});
