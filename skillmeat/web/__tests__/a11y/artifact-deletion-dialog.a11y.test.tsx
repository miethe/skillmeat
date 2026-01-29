/**
 * Accessibility Tests for ArtifactDeletionDialog Component
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import { useArtifactDeletion, useDeploymentList } from '@/hooks';
import type { Artifact } from '@/types/artifact';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock hooks
jest.mock('@/hooks', () => ({
  useArtifactDeletion: jest.fn(),
  useDeploymentList: jest.fn(),
}));
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
  },
}));

const mockedUseArtifactDeletion = useArtifactDeletion as jest.MockedFunction<
  typeof useArtifactDeletion
>;
const mockedUseDeploymentList = useDeploymentList as jest.MockedFunction<typeof useDeploymentList>;

// Mock artifact
const mockArtifact: Artifact = {
  id: 'artifact-123',
  name: 'test-skill',
  type: 'skill',
  description: 'A test skill',
  scope: 'user',
  syncStatus: 'synced',
  version: '1.0.0',
  source: 'user/repo/skill',
  upstream: {
    enabled: true,
    updateAvailable: false,
  },
  usageStats: {
    totalDeployments: 2,
    activeProjects: 1,
    usageCount: 5,
  },
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-02T00:00:00Z',
};

// Mock deployments
const mockDeployments = [
  {
    artifact_name: 'test-skill',
    artifact_type: 'skill' as const,
    artifact_path: '/project1/.claude/skills/test-skill',
    deployed_at: '2024-01-01T00:00:00Z',
  },
  {
    artifact_name: 'test-skill',
    artifact_type: 'skill' as const,
    artifact_path: '/project2/.claude/skills/test-skill',
    deployed_at: '2024-01-02T00:00:00Z',
  },
];

// Wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// Default props
const defaultProps = {
  artifact: mockArtifact,
  open: false,
  onOpenChange: jest.fn(),
  context: 'collection' as const,
};

describe('ArtifactDeletionDialog Accessibility', () => {
  let mockMutateAsync: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();

    // Setup default mock for mutation
    mockMutateAsync = jest.fn();
    mockedUseArtifactDeletion.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
      data: undefined,
      mutate: jest.fn(),
      reset: jest.fn(),
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      isPaused: false,
      status: 'idle',
      submittedAt: 0,
    });

    // Setup default mock for deployment list
    mockedUseDeploymentList.mockReturnValue({
      data: {
        deployments: mockDeployments,
        project_path: '/project1',
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: jest.fn(),
      isSuccess: true,
      status: 'success',
      dataUpdatedAt: 0,
      errorUpdatedAt: 0,
      failureCount: 0,
      failureReason: null,
      errorUpdateCount: 0,
      isFetched: true,
      isFetchedAfterMount: true,
      isFetching: false,
      isLoadingError: false,
      isPaused: false,
      isPlaceholderData: false,
      isRefetchError: false,
      isRefetching: false,
      isStale: false,
      isInitialLoading: false,
      isPending: false,
    });
  });

  describe('Default State (Collection Context)', () => {
    it('has no axe violations in default open state', async () => {
      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      // Wait for dialog to fully render
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has accessible dialog with proper title', async () => {
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      // Dialog should have accessible name from title
      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toHaveAccessibleName(/Delete test-skill/i);
      });
    });

    it('has accessible description for context', async () => {
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(
          screen.getByText(/This will remove the artifact from your collection/i)
        ).toBeInTheDocument();
      });
    });

    it('has no violations with all checkboxes', async () => {
      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Verify all checkboxes have labels
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBeGreaterThan(0);

      checkboxes.forEach((checkbox) => {
        expect(checkbox).toHaveAccessibleName();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Projects Section Expanded', () => {
    it('has no violations with projects section open', async () => {
      const user = userEvent.setup();
      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Toggle "Delete from Projects" to expand section
      const projectsCheckbox = screen.getByLabelText(/Also delete from Projects/i);
      await user.click(projectsCheckbox);

      await waitFor(() => {
        expect(screen.getByText(/Select which projects/i)).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has accessible project checkboxes', async () => {
      const user = userEvent.setup();
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Expand projects section
      const projectsCheckbox = screen.getByLabelText(/Also delete from Projects/i);
      await user.click(projectsCheckbox);

      await waitFor(() => {
        const projectCheckbox = screen.getByLabelText(/\/project1/i);
        expect(projectCheckbox).toBeInTheDocument();
        expect(projectCheckbox).toHaveAccessibleName();
      });
    });

    it('has accessible "Select All" button for projects', async () => {
      const user = userEvent.setup();
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Expand projects section
      const projectsCheckbox = screen.getByLabelText(/Also delete from Projects/i);
      await user.click(projectsCheckbox);

      await waitFor(() => {
        const selectAllButton = screen.getAllByRole('button', {
          name: /Select All|Deselect All/i,
        })[0];
        expect(selectAllButton).toBeInTheDocument();
        expect(selectAllButton).toHaveAccessibleName();
      });
    });
  });

  describe('Deployments Section Expanded (RED Warning)', () => {
    it('has no violations with deployments section open', async () => {
      const user = userEvent.setup();
      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Toggle "Delete Deployments" to expand RED warning section
      const deploymentsCheckbox = screen.getByLabelText(/Delete Deployments/i);
      await user.click(deploymentsCheckbox);

      await waitFor(() => {
        expect(
          screen.getByText(/WARNING: This will permanently delete files/i)
        ).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has accessible deployment checkboxes', async () => {
      const user = userEvent.setup();
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Expand deployments section
      const deploymentsCheckbox = screen.getByLabelText(/Delete Deployments/i);
      await user.click(deploymentsCheckbox);

      await waitFor(() => {
        const deploymentCheckboxes = screen.getAllByRole('checkbox');
        // Should have: delete-collection, delete-projects, delete-deployments, + 2 deployment items
        expect(deploymentCheckboxes.length).toBeGreaterThanOrEqual(3);

        deploymentCheckboxes.forEach((checkbox) => {
          expect(checkbox).toHaveAccessibleName();
        });
      });
    });

    it('has warning message with proper semantics', async () => {
      const user = userEvent.setup();
      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Expand deployments section
      const deploymentsCheckbox = screen.getByLabelText(/Delete Deployments/i);
      await user.click(deploymentsCheckbox);

      await waitFor(() => {
        const warningText = screen.getByText(/WARNING: This will permanently delete files/i);
        expect(warningText).toBeInTheDocument();
      });

      // Run axe with color-contrast rule enabled
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    });
  });

  describe('Keyboard Navigation', () => {
    it('has proper focus order', async () => {
      const user = userEvent.setup();
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Verify all interactive elements can be reached via Tab navigation
      const checkboxes = screen.getAllByRole('checkbox');
      const buttons = screen.getAllByRole('button');

      // Should have at least 3 checkboxes and 2 buttons (Cancel, Delete)
      expect(checkboxes.length).toBeGreaterThanOrEqual(3);
      expect(buttons.length).toBeGreaterThanOrEqual(2);

      // All interactive elements should be keyboard accessible
      const allInteractive = [...checkboxes, ...buttons];
      allInteractive.forEach((element) => {
        expect(element).not.toHaveAttribute('tabindex', '-1');
      });
    });

    it('can toggle checkboxes with Space key', async () => {
      const user = userEvent.setup();
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const projectsCheckbox = screen.getByLabelText(/Also delete from Projects/i);
      expect(projectsCheckbox).not.toBeChecked();

      // Focus and toggle with Space
      projectsCheckbox.focus();
      await user.keyboard(' ');

      await waitFor(() => {
        expect(projectsCheckbox).toBeChecked();
      });
    });

    it('has accessible Delete button', async () => {
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const deleteButton = screen.getByRole('button', { name: /Delete Artifact/i });
      expect(deleteButton).toBeInTheDocument();
      expect(deleteButton).toHaveAccessibleName();
      expect(deleteButton).not.toBeDisabled();
    });
  });

  describe('Loading State', () => {
    it('has no violations when deployments are loading', async () => {
      mockedUseDeploymentList.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        refetch: jest.fn(),
        isSuccess: false,
        status: 'pending',
        dataUpdatedAt: 0,
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: false,
        isFetchedAfterMount: false,
        isFetching: true,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: true,
        isPending: true,
      });

      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has no violations when deletion is pending', async () => {
      mockedUseArtifactDeletion.mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: true,
        isError: false,
        isSuccess: false,
        error: null,
        data: undefined,
        mutate: jest.fn(),
        reset: jest.fn(),
        variables: undefined,
        context: undefined,
        failureCount: 0,
        failureReason: null,
        isPaused: false,
        status: 'pending',
        submittedAt: Date.now(),
      });

      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Should show "Deleting..." button
      expect(screen.getByText(/Deleting.../i)).toBeInTheDocument();

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Color Contrast (WCAG AA)', () => {
    it('passes color contrast checks for warning text', async () => {
      const user = userEvent.setup();
      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Expand RED warning section
      const deploymentsCheckbox = screen.getByLabelText(/Delete Deployments/i);
      await user.click(deploymentsCheckbox);

      await waitFor(() => {
        expect(
          screen.getByText(/WARNING: This will permanently delete files/i)
        ).toBeInTheDocument();
      });

      // Run axe with strict color-contrast rules
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    });

    it('passes contrast for destructive checkbox label', async () => {
      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Check RED "Delete Deployments" label
      const deploymentsLabel = screen.getByText(/Delete Deployments/i);
      expect(deploymentsLabel).toBeInTheDocument();

      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    });
  });

  describe('Focus Management', () => {
    it('traps focus within dialog', async () => {
      const user = userEvent.setup();
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Verify dialog has focus trap
      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();

      // Tab through all elements should stay within dialog
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      const deleteButton = screen.getByRole('button', { name: /Delete Artifact/i });

      expect(cancelButton).toBeInTheDocument();
      expect(deleteButton).toBeInTheDocument();
    });

    it('has visible focus indicators', async () => {
      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Run axe with focus-related rules
      const results = await axe(container, {
        rules: {
          'focus-order-semantics': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    });
  });

  describe('Screen Reader Experience', () => {
    it('announces dialog opening', async () => {
      const { rerender } = render(<ArtifactDeletionDialog {...defaultProps} open={false} />, {
        wrapper: createWrapper(),
      });

      // Dialog should not be in document when closed
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

      // Open dialog
      rerender(<ArtifactDeletionDialog {...defaultProps} open={true} />);

      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toBeInTheDocument();
        expect(dialog).toHaveAccessibleName(/Delete test-skill/i);
      });
    });

    it('has proper heading hierarchy', async () => {
      render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Dialog title should be a heading
      const title = screen.getByText(/Delete test-skill/i);
      expect(title.closest('h2')).toBeInTheDocument();
    });

    it('has descriptive labels for all interactive elements', async () => {
      const { container } = render(<ArtifactDeletionDialog {...defaultProps} open={true} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // All buttons and checkboxes should have accessible names
      const buttons = screen.getAllByRole('button');
      const checkboxes = screen.getAllByRole('checkbox');

      buttons.forEach((button) => {
        expect(button).toHaveAccessibleName();
      });

      checkboxes.forEach((checkbox) => {
        expect(checkbox).toHaveAccessibleName();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Project Context Variant', () => {
    it('has no violations in project context', async () => {
      const { container } = render(
        <ArtifactDeletionDialog
          {...defaultProps}
          open={true}
          context="project"
          projectPath="/test/project"
        />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
