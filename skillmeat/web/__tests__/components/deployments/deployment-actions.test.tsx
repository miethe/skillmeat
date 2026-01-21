/**
 * @jest-environment jsdom
 */

/**
 * Unit tests for DeploymentActions component
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DeploymentActions } from '@/components/deployments/deployment-actions';
import type { Deployment } from '@/components/deployments/deployment-card';

// Mock the clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn(() => Promise.resolve()),
  },
});

describe('DeploymentActions', () => {
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
    onCopyPath: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Menu Rendering', () => {
    it('renders menu trigger button', () => {
      render(<DeploymentActions deployment={mockDeployment} />);
      const menuButton = screen.getByRole('button', { name: /open menu/i });

      expect(menuButton).toBeInTheDocument();
    });

    it('opens menu when trigger clicked', async () => {
      render(
        <DeploymentActions deployment={mockDeployment} onViewSource={mockCallbacks.onViewSource} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.getByText('View in Collection')).toBeInTheDocument();
      });
    });
  });

  describe('Conditional Actions', () => {
    it('shows Update action only for outdated deployments', async () => {
      const outdatedDeployment: Deployment = {
        ...mockDeployment,
        status: 'outdated',
      };

      render(
        <DeploymentActions deployment={outdatedDeployment} onUpdate={mockCallbacks.onUpdate} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.getByText('Update to Latest')).toBeInTheDocument();
      });
    });

    it('does not show Update action for current deployments', async () => {
      render(<DeploymentActions deployment={mockDeployment} onUpdate={mockCallbacks.onUpdate} />);

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.queryByText('Update to Latest')).not.toBeInTheDocument();
      });
    });

    it('shows View Diff action only when local modifications exist', async () => {
      const modifiedDeployment: Deployment = {
        ...mockDeployment,
        local_modifications: true,
      };

      render(
        <DeploymentActions deployment={modifiedDeployment} onViewDiff={mockCallbacks.onViewDiff} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.getByText('View Diff')).toBeInTheDocument();
      });
    });

    it('does not show View Diff when no local modifications', async () => {
      render(
        <DeploymentActions deployment={mockDeployment} onViewDiff={mockCallbacks.onViewDiff} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.queryByText('View Diff')).not.toBeInTheDocument();
      });
    });

    it('shows View in Collection when callback provided', async () => {
      render(
        <DeploymentActions deployment={mockDeployment} onViewSource={mockCallbacks.onViewSource} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.getByText('View in Collection')).toBeInTheDocument();
      });
    });

    it('shows Copy Path when callback provided', async () => {
      render(
        <DeploymentActions deployment={mockDeployment} onCopyPath={mockCallbacks.onCopyPath} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.getByText('Copy Path')).toBeInTheDocument();
      });
    });

    it('shows Remove when callback provided', async () => {
      render(<DeploymentActions deployment={mockDeployment} onRemove={mockCallbacks.onRemove} />);

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        expect(screen.getByText('Remove')).toBeInTheDocument();
      });
    });
  });

  describe('Action Callbacks', () => {
    it('calls onUpdate when Update clicked', async () => {
      const outdatedDeployment: Deployment = {
        ...mockDeployment,
        status: 'outdated',
      };

      render(
        <DeploymentActions deployment={outdatedDeployment} onUpdate={mockCallbacks.onUpdate} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const updateButton = screen.getByText('Update to Latest');
        fireEvent.click(updateButton);
      });

      expect(mockCallbacks.onUpdate).toHaveBeenCalled();
    });

    it('calls onViewDiff when View Diff clicked', async () => {
      const modifiedDeployment: Deployment = {
        ...mockDeployment,
        local_modifications: true,
      };

      render(
        <DeploymentActions deployment={modifiedDeployment} onViewDiff={mockCallbacks.onViewDiff} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const viewDiffButton = screen.getByText('View Diff');
        fireEvent.click(viewDiffButton);
      });

      expect(mockCallbacks.onViewDiff).toHaveBeenCalled();
    });

    it('calls onViewSource when View in Collection clicked', async () => {
      render(
        <DeploymentActions deployment={mockDeployment} onViewSource={mockCallbacks.onViewSource} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const viewSourceButton = screen.getByText('View in Collection');
        fireEvent.click(viewSourceButton);
      });

      expect(mockCallbacks.onViewSource).toHaveBeenCalled();
    });

    it('calls onCopyPath when Copy Path clicked', async () => {
      render(
        <DeploymentActions deployment={mockDeployment} onCopyPath={mockCallbacks.onCopyPath} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const copyButton = screen.getByText('Copy Path');
        fireEvent.click(copyButton);
      });

      expect(mockCallbacks.onCopyPath).toHaveBeenCalled();
    });

    it('shows "Copied!" feedback after copying path', async () => {
      render(
        <DeploymentActions deployment={mockDeployment} onCopyPath={mockCallbacks.onCopyPath} />
      );

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const copyButton = screen.getByText('Copy Path');
        fireEvent.click(copyButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Copied!')).toBeInTheDocument();
      });
    });
  });

  describe('Remove Confirmation Dialog', () => {
    it('shows confirmation dialog when Remove clicked', async () => {
      render(<DeploymentActions deployment={mockDeployment} onRemove={mockCallbacks.onRemove} />);

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

    it('displays deployment path in confirmation dialog', async () => {
      render(<DeploymentActions deployment={mockDeployment} onRemove={mockCallbacks.onRemove} />);

      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
      });

      await waitFor(() => {
        expect(screen.getByText('.claude/skills/user/pdf-extractor.md')).toBeInTheDocument();
      });
    });

    it('calls onRemove with filesystem flag when confirmed', async () => {
      render(<DeploymentActions deployment={mockDeployment} onRemove={mockCallbacks.onRemove} />);

      // Open menu
      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      // Click Remove
      await waitFor(() => {
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
      });

      // Check that filesystem removal checkbox is checked by default
      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).toBeChecked();
      });

      // Click confirmation button
      await waitFor(() => {
        const confirmButtons = screen.getAllByText('Remove');
        const confirmButton = confirmButtons.find((el) => el.tagName === 'BUTTON');
        if (confirmButton) fireEvent.click(confirmButton);
      });

      await waitFor(() => {
        expect(mockCallbacks.onRemove).toHaveBeenCalledWith(true);
      });
    });

    it('does not call onRemove when cancelled', async () => {
      render(<DeploymentActions deployment={mockDeployment} onRemove={mockCallbacks.onRemove} />);

      // Open menu
      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      // Click Remove
      await waitFor(() => {
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
      });

      // Click Cancel
      await waitFor(() => {
        const cancelButton = screen.getByText('Cancel');
        fireEvent.click(cancelButton);
      });

      expect(mockCallbacks.onRemove).not.toHaveBeenCalled();
    });

    it('closes dialog after successful removal', async () => {
      render(<DeploymentActions deployment={mockDeployment} onRemove={mockCallbacks.onRemove} />);

      // Open menu and trigger remove
      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
      });

      // Confirm removal
      await waitFor(() => {
        const confirmButtons = screen.getAllByText('Remove');
        const confirmButton = confirmButtons.find((el) => el.tagName === 'BUTTON');
        if (confirmButton) fireEvent.click(confirmButton);
      });

      await waitFor(() => {
        expect(screen.queryByText('Remove Deployment?')).not.toBeInTheDocument();
      });
    });

    it('shows "Removing..." text during removal', async () => {
      // Mock onRemove to delay completion
      const delayedRemove = jest.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));

      render(<DeploymentActions deployment={mockDeployment} onRemove={delayedRemove} />);

      // Open menu and trigger remove
      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
      });

      // Confirm removal
      await waitFor(() => {
        const confirmButtons = screen.getAllByText('Remove');
        const confirmButton = confirmButtons.find((el) => el.tagName === 'BUTTON');
        if (confirmButton) fireEvent.click(confirmButton);
      });

      // Check for "Removing..." text
      await waitFor(() => {
        expect(screen.getByText('Removing...')).toBeInTheDocument();
      });
    });

    it('calls onRemove with false when filesystem checkbox is unchecked', async () => {
      render(<DeploymentActions deployment={mockDeployment} onRemove={mockCallbacks.onRemove} />);

      // Open menu and click Remove
      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
      });

      // Uncheck the filesystem removal checkbox
      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox');
        fireEvent.click(checkbox);
      });

      // Click confirmation button
      await waitFor(() => {
        const confirmButtons = screen.getAllByText('Remove');
        const confirmButton = confirmButtons.find((el) => el.tagName === 'BUTTON');
        if (confirmButton) fireEvent.click(confirmButton);
      });

      await waitFor(() => {
        expect(mockCallbacks.onRemove).toHaveBeenCalledWith(false);
      });
    });

    it('shows filesystem removal checkbox with correct label', async () => {
      render(<DeploymentActions deployment={mockDeployment} onRemove={mockCallbacks.onRemove} />);

      // Open menu and click Remove
      const menuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(menuButton);

      await waitFor(() => {
        const removeButton = screen.getByText('Remove');
        fireEvent.click(removeButton);
      });

      // Check that the checkbox and label are present
      await waitFor(() => {
        expect(screen.getByRole('checkbox')).toBeInTheDocument();
        expect(
          screen.getByText('Remove files from local filesystem at project path')
        ).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has accessible menu trigger', () => {
      render(<DeploymentActions deployment={mockDeployment} />);
      const menuButton = screen.getByRole('button', { name: /open menu/i });

      expect(menuButton).toHaveAttribute('aria-expanded');
    });

    it('provides screen reader text for menu trigger', () => {
      render(<DeploymentActions deployment={mockDeployment} />);
      const srText = screen.getByText('Open menu');

      expect(srText).toHaveClass('sr-only');
    });
  });
});
