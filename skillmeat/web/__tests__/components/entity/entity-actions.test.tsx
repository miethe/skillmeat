/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EntityActions } from '@/components/entity/entity-actions';
import type { Entity } from '@/types/entity';

const mockEntity: Entity = {
  id: 'skill:test',
  uuid: '00000000000000000000000000000001',
  name: 'test-skill',
  type: 'skill',
  scope: 'user',
  source: 'github:user/repo/skill',
  syncStatus: 'synced',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

describe('EntityActions', () => {
  it('renders dropdown menu trigger button', () => {
    render(<EntityActions entity={mockEntity} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    expect(menuButton).toBeInTheDocument();
  });

  it('opens dropdown menu when trigger is clicked', async () => {
    render(<EntityActions entity={mockEntity} onEdit={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });
  });

  it('shows Edit action when onEdit is provided', async () => {
    render(<EntityActions entity={mockEntity} onEdit={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });
  });

  it('calls onEdit when Edit is clicked', async () => {
    const handleEdit = jest.fn();
    render(<EntityActions entity={mockEntity} onEdit={handleEdit} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const editButton = screen.getByText('Edit');
      fireEvent.click(editButton);
    });

    expect(handleEdit).toHaveBeenCalled();
  });

  it('shows Deploy action when onDeploy is provided', async () => {
    render(<EntityActions entity={mockEntity} onDeploy={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('Deploy to Project')).toBeInTheDocument();
    });
  });

  it('calls onDeploy when Deploy is clicked', async () => {
    const handleDeploy = jest.fn();
    render(<EntityActions entity={mockEntity} onDeploy={handleDeploy} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const deployButton = screen.getByText('Deploy to Project');
      fireEvent.click(deployButton);
    });

    expect(handleDeploy).toHaveBeenCalled();
  });

  it('shows Sync action when onSync is provided', async () => {
    render(<EntityActions entity={mockEntity} onSync={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('Sync to Collection')).toBeInTheDocument();
    });
  });

  it('calls onSync when Sync is clicked', async () => {
    const handleSync = jest.fn();
    render(<EntityActions entity={mockEntity} onSync={handleSync} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const syncButton = screen.getByText('Sync to Collection');
      fireEvent.click(syncButton);
    });

    expect(handleSync).toHaveBeenCalled();
  });

  it('shows View Diff action when entity is modified', async () => {
    const modifiedEntity = { ...mockEntity, syncStatus: 'modified' as const };
    render(<EntityActions entity={modifiedEntity} onViewDiff={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('View Diff')).toBeInTheDocument();
    });
  });

  it('does not show View Diff when entity is not modified', async () => {
    render(<EntityActions entity={mockEntity} onViewDiff={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.queryByText('View Diff')).not.toBeInTheDocument();
    });
  });

  it('shows Rollback action when entity is modified', async () => {
    const modifiedEntity = { ...mockEntity, syncStatus: 'modified' as const };
    render(<EntityActions entity={modifiedEntity} onRollback={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('Rollback to Collection')).toBeInTheDocument();
    });
  });

  it('shows Rollback action when entity has conflict', async () => {
    const conflictEntity = { ...mockEntity, syncStatus: 'conflict' as const };
    render(<EntityActions entity={conflictEntity} onRollback={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('Rollback to Collection')).toBeInTheDocument();
    });
  });

  it('shows Delete action when onDelete is provided', async () => {
    render(<EntityActions entity={mockEntity} onDelete={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });
  });

  it('shows delete confirmation dialog when Delete is clicked', async () => {
    render(<EntityActions entity={mockEntity} onDelete={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const deleteButton = screen.getByText('Delete');
      fireEvent.click(deleteButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Delete test-skill\?/)).toBeInTheDocument();
    });
  });

  it('calls onDelete when delete is confirmed', async () => {
    const handleDelete = jest.fn().mockResolvedValue(undefined);
    render(<EntityActions entity={mockEntity} onDelete={handleDelete} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const deleteButton = screen.getByText('Delete');
      fireEvent.click(deleteButton);
    });

    await waitFor(() => {
      const confirmButton = screen.getByRole('button', { name: /^Delete$/ });
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(handleDelete).toHaveBeenCalled();
    });
  });

  it('closes delete dialog when Cancel is clicked', async () => {
    render(<EntityActions entity={mockEntity} onDelete={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const deleteButton = screen.getByText('Delete');
      fireEvent.click(deleteButton);
    });

    await waitFor(() => {
      const cancelButton = screen.getByRole('button', { name: /Cancel/ });
      fireEvent.click(cancelButton);
    });

    await waitFor(() => {
      expect(screen.queryByText(/Delete test-skill\?/)).not.toBeInTheDocument();
    });
  });

  it('shows loading state during delete', async () => {
    const handleDelete = jest
      .fn()
      .mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));
    render(<EntityActions entity={mockEntity} onDelete={handleDelete} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const deleteButton = screen.getByText('Delete');
      fireEvent.click(deleteButton);
    });

    await waitFor(() => {
      const confirmButton = screen.getByRole('button', { name: /^Delete$/ });
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(screen.getByText('Deleting...')).toBeInTheDocument();
    });
  });

  it('disables buttons during delete', async () => {
    const handleDelete = jest
      .fn()
      .mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));
    render(<EntityActions entity={mockEntity} onDelete={handleDelete} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const deleteButton = screen.getByText('Delete');
      fireEvent.click(deleteButton);
    });

    await waitFor(() => {
      const confirmButton = screen.getByRole('button', { name: /^Delete$/ });
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      const cancelButton = screen.getByRole('button', { name: /Cancel/ });
      expect(cancelButton).toBeDisabled();
    });
  });

  it('shows rollback confirmation dialog when Rollback is clicked', async () => {
    const modifiedEntity = { ...mockEntity, syncStatus: 'modified' as const };
    render(<EntityActions entity={modifiedEntity} onRollback={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const rollbackButton = screen.getByText('Rollback to Collection');
      fireEvent.click(rollbackButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Rollback to Collection Version\?/)).toBeInTheDocument();
    });
  });

  it('applies destructive styling to Delete action', async () => {
    render(<EntityActions entity={mockEntity} onDelete={jest.fn()} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const deleteButton = screen.getByText('Delete');
      expect(deleteButton.parentElement).toHaveClass('text-destructive');
    });
  });

  it('renders MoreVertical icon in trigger button', () => {
    const { container } = render(<EntityActions entity={mockEntity} />);

    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('handles error during delete gracefully', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    const handleDelete = jest.fn().mockRejectedValue(new Error('Delete failed'));

    render(<EntityActions entity={mockEntity} onDelete={handleDelete} />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);

    await waitFor(() => {
      const deleteButton = screen.getByText('Delete');
      fireEvent.click(deleteButton);
    });

    await waitFor(() => {
      const confirmButton = screen.getByRole('button', { name: /^Delete$/ });
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(consoleError).toHaveBeenCalled();
    });

    consoleError.mockRestore();
  });
});
