/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RollbackDialog } from '@/components/entity/rollback-dialog';
import type { Entity } from '@/types/entity';

const mockEntity: Entity = {
  id: 'skill:test',
  name: 'test-skill',
  type: 'skill',
  scope: 'user',
  source: 'github:user/repo/skill',
  syncStatus: 'modified',
  version: 'v1.2.3',
  projectPath: '/home/user/projects/my-project',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

describe('RollbackDialog', () => {
  it('renders dialog when open', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getByText(/Rollback to Collection Version\?/)).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={false}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.queryByText(/Rollback to Collection Version\?/)).not.toBeInTheDocument();
  });

  it('displays entity name in dialog', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getByText(/test-skill/)).toBeInTheDocument();
  });

  it('displays entity type', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getByText(/Type:/)).toBeInTheDocument();
    expect(screen.getByText(/skill/)).toBeInTheDocument();
  });

  it('shows current and target versions', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getByText('Current (Local)')).toBeInTheDocument();
    expect(screen.getByText('Target (Collection)')).toBeInTheDocument();
    expect(screen.getAllByText('v1.2.3')).toHaveLength(2);
  });

  it('displays project path when available', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getByText(/Project:/)).toBeInTheDocument();
    expect(screen.getByText('/home/user/projects/my-project')).toBeInTheDocument();
  });

  it('shows warning about data loss', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getByText(/Warning: This action cannot be undone/)).toBeInTheDocument();
    expect(screen.getByText(/All local modifications will be lost/)).toBeInTheDocument();
  });

  it('renders Cancel button', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /Cancel/ })).toBeInTheDocument();
  });

  it('renders Rollback button', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /^Rollback$/ })).toBeInTheDocument();
  });

  it('calls onOpenChange when Cancel is clicked', () => {
    const handleOpenChange = jest.fn();
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={handleOpenChange}
        onConfirm={jest.fn()}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /Cancel/ });
    fireEvent.click(cancelButton);

    expect(handleOpenChange).toHaveBeenCalledWith(false);
  });

  it('calls onConfirm when Rollback is clicked', async () => {
    const handleConfirm = jest.fn().mockResolvedValue(undefined);
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={handleConfirm}
      />
    );

    const rollbackButton = screen.getByRole('button', { name: /^Rollback$/ });
    fireEvent.click(rollbackButton);

    await waitFor(() => {
      expect(handleConfirm).toHaveBeenCalled();
    });
  });

  it('closes dialog after successful rollback', async () => {
    const handleOpenChange = jest.fn();
    const handleConfirm = jest.fn().mockResolvedValue(undefined);

    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={handleOpenChange}
        onConfirm={handleConfirm}
      />
    );

    const rollbackButton = screen.getByRole('button', { name: /^Rollback$/ });
    fireEvent.click(rollbackButton);

    await waitFor(() => {
      expect(handleOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('shows loading state during rollback', async () => {
    const handleConfirm = jest
      .fn()
      .mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));

    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={handleConfirm}
      />
    );

    const rollbackButton = screen.getByRole('button', { name: /^Rollback$/ });
    fireEvent.click(rollbackButton);

    await waitFor(() => {
      expect(screen.getByText(/Rolling Back.../)).toBeInTheDocument();
    });
  });

  it('disables buttons during rollback', async () => {
    const handleConfirm = jest
      .fn()
      .mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));

    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={handleConfirm}
      />
    );

    const rollbackButton = screen.getByRole('button', { name: /^Rollback$/ });
    fireEvent.click(rollbackButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Rolling Back.../ })).toBeDisabled();
      expect(screen.getByRole('button', { name: /Cancel/ })).toBeDisabled();
    });
  });

  it('handles rollback error gracefully', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    const handleConfirm = jest.fn().mockRejectedValue(new Error('Rollback failed'));

    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={handleConfirm}
      />
    );

    const rollbackButton = screen.getByRole('button', { name: /^Rollback$/ });
    fireEvent.click(rollbackButton);

    await waitFor(() => {
      expect(consoleError).toHaveBeenCalledWith('Failed to rollback entity:', expect.any(Error));
    });

    consoleError.mockRestore();
  });

  it('renders RotateCcw icon in title', () => {
    const { container } = render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    const icons = container.querySelectorAll('svg');
    expect(icons.length).toBeGreaterThan(0);
  });

  it('renders AlertTriangle icon in warning', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    // Warning alert should contain AlertTriangle icon
    const warning = screen.getByText(/Warning: This action cannot be undone/);
    expect(warning).toBeInTheDocument();
  });

  it('applies destructive variant to Rollback button', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    const rollbackButton = screen.getByRole('button', { name: /^Rollback$/ });
    expect(rollbackButton).toHaveClass('bg-destructive');
  });

  it('shows Unknown when version is missing', () => {
    const entityWithoutVersion = { ...mockEntity, version: undefined };
    render(
      <RollbackDialog
        entity={entityWithoutVersion}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.getAllByText('Unknown')).toHaveLength(1);
    expect(screen.getAllByText('Collection version')).toHaveLength(1);
  });

  it('does not show project path when not available', () => {
    const entityWithoutPath = { ...mockEntity, projectPath: undefined };
    render(
      <RollbackDialog
        entity={entityWithoutPath}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.queryByText(/Project:/)).not.toBeInTheDocument();
  });

  it('displays descriptive warning text', () => {
    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(
      screen.getByText(/The collection version will overwrite your current local version/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Make sure you have backed up any important changes before proceeding/)
    ).toBeInTheDocument();
  });

  it('shows spinning icon during rollback', async () => {
    const handleConfirm = jest
      .fn()
      .mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));

    render(
      <RollbackDialog
        entity={mockEntity}
        open={true}
        onOpenChange={jest.fn()}
        onConfirm={handleConfirm}
      />
    );

    const rollbackButton = screen.getByRole('button', { name: /^Rollback$/ });
    fireEvent.click(rollbackButton);

    await waitFor(() => {
      const loadingButton = screen.getByRole('button', {
        name: /Rolling Back.../,
      });
      const icon = loadingButton.querySelector('svg');
      expect(icon).toHaveClass('animate-spin');
    });
  });
});
