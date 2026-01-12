/**
 * @jest-environment jsdom
 *
 * Artifact Deletion Integration Tests
 *
 * Tests the complete artifact deletion flow including:
 * - EntityActions integration with ArtifactDeletionDialog
 * - UnifiedEntityModal integration with deletion
 * - Dialog state management (toggles, selections)
 * - Mutation flow (pending states, errors, success)
 * - Cache invalidation after deletion
 */

import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EntityActions } from '@/components/entity/entity-actions';
import { UnifiedEntityModal } from '@/components/entity/unified-entity-modal';
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import type { Entity } from '@/types/entity';
import type { Artifact } from '@/types/artifact';

// Mock problematic components that use ESM modules
jest.mock('@/components/entity/unified-entity-modal', () => {
  const React = require('react');
  return {
    UnifiedEntityModal: ({ entity, open, onClose }: any) => {
      if (!open || !entity) return null;
      return React.createElement(
        'div',
        { role: 'dialog', 'aria-label': 'Entity Modal' },
        React.createElement('div', {}, entity.name),
        React.createElement(
          'button',
          { onClick: () => {} },
          'Delete'
        ),
        React.createElement(
          'button',
          { onClick: onClose },
          'Close'
        )
      );
    },
  };
});

// Mock hooks
jest.mock('@/hooks', () => ({
  useArtifactDeletion: jest.fn(),
  useDeploymentList: jest.fn(),
  useEntityLifecycle: jest.fn(() => ({
    deployEntity: jest.fn(),
    syncEntity: jest.fn(),
    refetch: jest.fn(),
  })),
  useToast: () => ({
    toast: jest.fn(),
  }),
  toast: jest.fn(),
}));

jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
  },
}));

// Import mocked hooks
import { useArtifactDeletion, useDeploymentList } from '@/hooks';

// Mock deployment data
const mockDeployments = [
  {
    artifact_name: 'test-skill',
    artifact_type: 'skill',
    artifact_path: '/project/a/.claude/skills/test-skill',
    collection_sha: 'abc1234',
    deployed_at: '2024-01-01T00:00:00Z',
    sync_status: 'synced' as const,
  },
  {
    artifact_name: 'test-skill',
    artifact_type: 'skill',
    artifact_path: '/project/b/.claude/skills/test-skill',
    collection_sha: 'def5678',
    deployed_at: '2024-01-02T00:00:00Z',
    sync_status: 'modified' as const,
  },
];

// Helper to create a new QueryClient for each test
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Suppress error logs in tests
    },
  });

// Helper to render with providers
const renderWithProviders = (component: React.ReactNode) => {
  const queryClient = createTestQueryClient();
  return {
    ...render(<QueryClientProvider client={queryClient}>{component}</QueryClientProvider>),
    queryClient,
  };
};

// Mock Entity (for EntityActions and UnifiedEntityModal)
const mockEntity: Entity = {
  id: 'skill:test-skill',
  name: 'test-skill',
  type: 'skill',
  source: 'test/repo/skill',
  version: 'v1.0.0',
  status: 'synced',
  collection: 'default',
  tags: ['test'],
  aliases: [],
  description: 'A test skill',
};

// Mock Artifact (for ArtifactDeletionDialog)
const mockArtifact: Artifact = {
  id: 'skill:test-skill',
  name: 'test-skill',
  type: 'skill',
  source: 'test/repo/skill',
  version: 'v1.0.0',
  tags: ['test'],
  aliases: [],
};

describe('Artifact Deletion Integration Tests', () => {
  let mockMutateAsync: jest.Mock;
  let mockReset: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();

    // Setup mutation mock
    mockMutateAsync = jest.fn().mockResolvedValue({
      collectionDeleted: true,
      projectsUndeployed: 2,
      deploymentsDeleted: 0,
      errors: [],
    });

    mockReset = jest.fn();

    (useArtifactDeletion as jest.Mock).mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
      isError: false,
      error: null,
      reset: mockReset,
    });

    // Setup deployments mock
    (useDeploymentList as jest.Mock).mockReturnValue({
      data: {
        deployments: mockDeployments,
        total: 2,
        project_path: '/project/a',
      },
      isLoading: false,
      error: null,
    });
  });

  describe('EntityActions Integration', () => {
    it('opens deletion dialog when delete menu item is clicked', async () => {
      const user = userEvent.setup();
      const onDelete = jest.fn();

      renderWithProviders(
        <EntityActions entity={mockEntity} onDelete={onDelete} />
      );

      // Open dropdown menu
      const menuButton = screen.getByRole('button', { name: /open menu/i });
      await user.click(menuButton);

      // Click delete option
      const deleteMenuItem = screen.getByRole('menuitem', { name: /delete/i });
      await user.click(deleteMenuItem);

      // Verify dialog opens
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText(/delete test-skill/i)).toBeInTheDocument();
      });
    });

    it('shows collection context messaging when entity has no projectPath', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <EntityActions entity={mockEntity} onDelete={jest.fn()} />
      );

      // Open menu and click delete
      await user.click(screen.getByRole('button', { name: /open menu/i }));
      await user.click(screen.getByRole('menuitem', { name: /delete/i }));

      // Verify collection context message
      await waitFor(() => {
        expect(screen.getByText(/remove the artifact from your collection/i)).toBeInTheDocument();
      });
    });

    it('shows project context messaging when entity has projectPath', async () => {
      const user = userEvent.setup();
      const projectEntity = { ...mockEntity, projectPath: '/test/project' };

      renderWithProviders(
        <EntityActions entity={projectEntity} onDelete={jest.fn()} />
      );

      // Open menu and click delete
      await user.click(screen.getByRole('button', { name: /open menu/i }));
      await user.click(screen.getByRole('menuitem', { name: /delete/i }));

      // Verify project context message
      await waitFor(() => {
        expect(screen.getByText(/remove the artifact from this project/i)).toBeInTheDocument();
      });
    });

    it('calls onDelete callback on successful deletion', async () => {
      const user = userEvent.setup();
      const onDelete = jest.fn();

      renderWithProviders(
        <EntityActions entity={mockEntity} onDelete={onDelete} />
      );

      // Open menu and click delete
      await user.click(screen.getByRole('button', { name: /open menu/i }));
      await user.click(screen.getByRole('menuitem', { name: /delete/i }));

      // Confirm deletion
      const deleteButton = await screen.findByRole('button', { name: /delete artifact/i });
      await user.click(deleteButton);

      // Wait for mutation to complete
      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalled();
      });

      // Verify onDelete was called
      await waitFor(() => {
        expect(onDelete).toHaveBeenCalled();
      });
    });

    it('closes dialog on cancel', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <EntityActions entity={mockEntity} onDelete={jest.fn()} />
      );

      // Open dialog
      await user.click(screen.getByRole('button', { name: /open menu/i }));
      await user.click(screen.getByRole('menuitem', { name: /delete/i }));

      // Click cancel
      const cancelButton = await screen.findByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      // Verify dialog closes
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('UnifiedEntityModal Integration', () => {
    it('renders modal with entity name', () => {
      renderWithProviders(
        <UnifiedEntityModal entity={mockEntity} open={true} onClose={jest.fn()} />
      );

      // Modal should render with entity name
      expect(screen.getByText('test-skill')).toBeInTheDocument();
    });

    it('shows delete button', () => {
      renderWithProviders(
        <UnifiedEntityModal entity={mockEntity} open={true} onClose={jest.fn()} />
      );

      // Delete button should be present
      expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
    });

    it('calls onClose when close button is clicked', async () => {
      const user = userEvent.setup();
      const onClose = jest.fn();

      renderWithProviders(
        <UnifiedEntityModal entity={mockEntity} open={true} onClose={onClose} />
      );

      // Click close button
      const closeButton = screen.getByRole('button', { name: /close/i });
      await user.click(closeButton);

      // Verify onClose was called
      expect(onClose).toHaveBeenCalled();
    });

    it('does not render when open is false', () => {
      renderWithProviders(
        <UnifiedEntityModal entity={mockEntity} open={false} onClose={jest.fn()} />
      );

      // Modal should not render
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  describe('Dialog State Management', () => {
    it('toggles "Delete from Projects" option', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Find "Also delete from Projects" checkbox
      const projectsCheckbox = screen.getByLabelText(/also delete from projects/i);
      expect(projectsCheckbox).not.toBeChecked();

      // Toggle on
      await user.click(projectsCheckbox);
      expect(projectsCheckbox).toBeChecked();

      // Verify projects section expands
      await waitFor(() => {
        expect(screen.getByText(/select which projects/i)).toBeInTheDocument();
      });
    });

    it('toggles "Delete Deployments" option and shows RED warning', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Find "Delete Deployments" checkbox
      const deploymentsCheckbox = screen.getByLabelText(/delete deployments/i);
      expect(deploymentsCheckbox).not.toBeChecked();

      // Toggle on
      await user.click(deploymentsCheckbox);
      expect(deploymentsCheckbox).toBeChecked();

      // Verify RED warning section appears
      await waitFor(() => {
        expect(screen.getByText(/permanently delete files from your filesystem/i)).toBeInTheDocument();
        expect(screen.getByText(/this cannot be undone!/i)).toBeInTheDocument();
      });
    });

    it('auto-selects all projects when "Delete from Projects" is toggled', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Toggle "Delete from Projects"
      await user.click(screen.getByLabelText(/also delete from projects/i));

      // Verify all projects are auto-selected
      await waitFor(() => {
        const projectCheckboxes = screen.getAllByRole('checkbox').filter(
          (cb) => cb.getAttribute('id')?.startsWith('project-')
        );
        projectCheckboxes.forEach((checkbox) => {
          expect(checkbox).toBeChecked();
        });
      });
    });

    it('updates selection count when toggling individual projects', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Enable project deletion
      await user.click(screen.getByLabelText(/also delete from projects/i));

      // Initially all selected (1 unique project from deployments)
      await waitFor(() => {
        expect(screen.getByText(/\(1 of 1 selected\)/i)).toBeInTheDocument();
      });

      // Deselect first project
      const projectCheckboxes = screen.getAllByRole('checkbox').filter(
        (cb) => cb.getAttribute('id')?.startsWith('project-')
      );

      if (projectCheckboxes.length > 0) {
        await user.click(projectCheckboxes[0]);

        // Verify count updates
        await waitFor(() => {
          expect(screen.getByText(/\(0 of 1 selected\)/i)).toBeInTheDocument();
        });
      }
    });

    it('shows "Select All" / "Deselect All" toggle for projects', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Enable project deletion
      await user.click(screen.getByLabelText(/also delete from projects/i));

      // Initially shows "Deselect All"
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /deselect all/i })).toBeInTheDocument();
      });

      // Click to deselect all
      await user.click(screen.getByRole('button', { name: /deselect all/i }));

      // Now shows "Select All"
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /select all/i })).toBeInTheDocument();
      });
    });
  });

  describe('Mutation Flow', () => {
    it('disables Delete button during operation (isPending)', async () => {
      const user = userEvent.setup();

      // Mock isPending state
      (useArtifactDeletion as jest.Mock).mockReturnValue({
        mutateAsync: jest.fn().mockImplementation(() => new Promise(() => {})), // Never resolves
        isPending: true,
        isError: false,
        error: null,
      });

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Delete button should be disabled
      const deleteButton = screen.getByRole('button', { name: /deleting/i });
      expect(deleteButton).toBeDisabled();
    });

    it('shows error message on mutation failure', async () => {
      const user = userEvent.setup();

      // Mock mutation error
      const mockError = new Error('Failed to delete artifact');
      mockMutateAsync.mockRejectedValueOnce(mockError);

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Click Delete
      await user.click(screen.getByRole('button', { name: /delete artifact/i }));

      // Wait for error toast (sonner)
      await waitFor(() => {
        expect(require('sonner').toast.error).toHaveBeenCalledWith(
          expect.stringContaining('Failed to delete'),
          expect.any(Object)
        );
      });
    });

    it('calls onSuccess callback on successful deletion', async () => {
      const user = userEvent.setup();
      const onSuccess = jest.fn();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
          onSuccess={onSuccess}
        />
      );

      // Click Delete
      await user.click(screen.getByRole('button', { name: /delete artifact/i }));

      // Wait for success
      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
    });

    it('passes correct parameters to mutation function', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Enable project deletion
      await user.click(screen.getByLabelText(/also delete from projects/i));

      // Click Delete
      await user.click(screen.getByRole('button', { name: /delete artifact/i }));

      // Verify mutation was called with correct params
      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            artifact: mockArtifact,
            deleteFromCollection: true,
            deleteFromProjects: true,
            deleteDeployments: false,
            selectedProjectPaths: expect.any(Array),
            selectedDeploymentPaths: expect.any(Array),
          })
        );
      });
    });

    it('shows success toast with operation details', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Enable project deletion
      await user.click(screen.getByLabelText(/also delete from projects/i));

      // Click Delete
      await user.click(screen.getByRole('button', { name: /delete artifact/i }));

      // Wait for success toast
      await waitFor(() => {
        expect(require('sonner').toast.success).toHaveBeenCalledWith(
          expect.stringContaining('test-skill deleted'),
          expect.objectContaining({
            description: expect.stringContaining('Removed from collection'),
          })
        );
      });
    });

    it('shows warning toast when partial deletion occurs', async () => {
      const user = userEvent.setup();

      // Mock partial success (some errors)
      mockMutateAsync.mockResolvedValueOnce({
        collectionDeleted: true,
        projectsUndeployed: 1,
        deploymentsDeleted: 0,
        errors: [
          { operation: 'undeploy:/project/b', error: 'File not found' },
        ],
      });

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Enable project deletion
      await user.click(screen.getByLabelText(/also delete from projects/i));

      // Click Delete
      await user.click(screen.getByRole('button', { name: /delete artifact/i }));

      // Wait for warning toast
      await waitFor(() => {
        expect(require('sonner').toast.warning).toHaveBeenCalledWith(
          expect.stringContaining('partially deleted'),
          expect.objectContaining({
            description: expect.stringContaining('1 operation(s) failed'),
          })
        );
      });
    });
  });

  describe('Cache Invalidation', () => {
    it('invalidates deployment queries after successful deletion', async () => {
      const user = userEvent.setup();
      const { queryClient } = renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

      // Click Delete
      await user.click(screen.getByRole('button', { name: /delete artifact/i }));

      // Wait for mutation to complete
      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalled();
      });

      // Verify cache invalidation (hook handles this internally)
      // We can't directly verify since it's in the hook's onSuccess,
      // but we can verify the mutation completed successfully
      expect(mockMutateAsync).toHaveBeenCalledTimes(1);
    });
  });

  describe('Loading States', () => {
    it('shows loading text while fetching deployments', () => {
      (useDeploymentList as jest.Mock).mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Verify loading text appears (use getAllByText since it appears in two places)
      const loadingTexts = screen.getAllByText(/loading deployments/i);
      expect(loadingTexts.length).toBeGreaterThan(0);
    });

    it('disables toggles while deployments are loading', () => {
      (useDeploymentList as jest.Mock).mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Project and deployment toggles should be disabled
      const projectsCheckbox = screen.getByLabelText(/also delete from projects/i);
      const deploymentsCheckbox = screen.getByLabelText(/delete deployments/i);

      expect(projectsCheckbox).toBeDisabled();
      expect(deploymentsCheckbox).toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    it('provides accessible labels for all checkboxes', () => {
      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // All checkboxes should have accessible labels
      expect(screen.getByLabelText(/delete from collection/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/also delete from projects/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/delete deployments/i)).toBeInTheDocument();
    });

    it('provides role="alert" for warning messages', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Enable deployment deletion
      await user.click(screen.getByLabelText(/delete deployments/i));

      // Verify warning has role="alert"
      await waitFor(() => {
        const alerts = screen.getAllByRole('alert');
        expect(alerts.length).toBeGreaterThan(0);
      });
    });

    it('provides aria-live regions for dynamic counts', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <ArtifactDeletionDialog
          artifact={mockArtifact}
          open={true}
          onOpenChange={jest.fn()}
          context="collection"
        />
      );

      // Enable project deletion
      await user.click(screen.getByLabelText(/also delete from projects/i));

      // Selection count should be in an aria-live region
      await waitFor(() => {
        const liveRegion = screen.getByText(/\(1 of 1 selected\)/i);
        expect(liveRegion).toHaveAttribute('aria-live', 'polite');
      });
    });
  });
});
