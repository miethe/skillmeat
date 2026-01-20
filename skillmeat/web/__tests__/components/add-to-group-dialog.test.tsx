import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AddToGroupDialog } from '@/components/collection/add-to-group-dialog';
import {
  useGroups,
  useAddArtifactToGroup,
  useCreateGroup,
  useToast,
  useCollections,
} from '@/hooks';
import type { Artifact } from '@/types/artifact';

// Mock hooks
jest.mock('@/hooks', () => ({
  useGroups: jest.fn(),
  useAddArtifactToGroup: jest.fn(),
  useCreateGroup: jest.fn(),
  useToast: jest.fn(),
  useCollections: jest.fn(),
}));

const mockUseGroups = useGroups as jest.MockedFunction<typeof useGroups>;
const mockUseAddArtifactToGroup = useAddArtifactToGroup as jest.MockedFunction<
  typeof useAddArtifactToGroup
>;
const mockUseCreateGroup = useCreateGroup as jest.MockedFunction<typeof useCreateGroup>;
const mockUseToast = useToast as jest.MockedFunction<typeof useToast>;
const mockUseCollections = useCollections as jest.MockedFunction<typeof useCollections>;

describe('AddToGroupDialog', () => {
  const mockToast = jest.fn();
  const mockOnOpenChange = jest.fn();
  const mockOnSuccess = jest.fn();
  const mockMutateAsync = jest.fn();

  // Mock artifact with multiple collections
  const mockArtifact: Artifact = {
    id: 'artifact-1',
    name: 'Test Artifact',
    type: 'skill',
    scope: 'user',
    status: 'active',
    source: 'github.com/test/repo',
    metadata: {
      title: 'Test Artifact',
      description: 'A test artifact',
      tags: ['test'],
    },
    upstreamStatus: {
      hasUpstream: false,
      isOutdated: false,
    },
    usageStats: {
      totalDeployments: 0,
      activeProjects: 0,
      usageCount: 0,
    },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    aliases: [],
    collections: [
      { id: 'c1', name: 'Collection A', artifact_count: 5 },
      { id: 'c2', name: 'Collection B', artifact_count: 3 },
    ],
  };

  // Mock artifact with no collections
  const mockArtifactNoCollections: Artifact = {
    ...mockArtifact,
    id: 'artifact-no-collections',
    name: 'Orphan Artifact',
    collections: [],
  };

  const mockGroups = [
    {
      id: 'g1',
      collection_id: 'c1',
      name: 'Development',
      description: 'Dev tools',
      position: 0,
      artifact_count: 2,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'g2',
      collection_id: 'c1',
      name: 'Production',
      description: 'Prod skills',
      position: 1,
      artifact_count: 5,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-02-02T00:00:00Z',
    },
  ];

  const mockAllCollections = [
    { id: 'c1', name: 'Collection A', artifact_count: 5 },
    { id: 'c2', name: 'Collection B', artifact_count: 3 },
    { id: 'c3', name: 'Collection C', artifact_count: 1 },
  ];

  const createQueryClient = () =>
    new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

  const renderDialog = (props: Partial<React.ComponentProps<typeof AddToGroupDialog>> = {}) => {
    const queryClient = createQueryClient();
    return render(
      <QueryClientProvider client={queryClient}>
        <AddToGroupDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          artifact={mockArtifact}
          onSuccess={mockOnSuccess}
          {...props}
        />
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();

    mockUseToast.mockReturnValue({ toast: mockToast } as any);

    mockUseGroups.mockReturnValue({
      data: { groups: mockGroups, total: mockGroups.length },
      isLoading: false,
      error: null,
    } as any);

    mockUseAddArtifactToGroup.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    } as any);

    mockUseCreateGroup.mockReturnValue({
      mutateAsync: jest.fn().mockResolvedValue({ id: 'new-group', name: 'New Group' }),
      isPending: false,
    } as any);

    mockUseCollections.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any);
  });

  describe('Collection Picker Step', () => {
    it('shows collection picker when collectionId not provided', () => {
      renderDialog();

      expect(screen.getByText('Add to Group')).toBeInTheDocument();
      expect(
        screen.getByText(/Select a collection to add "Test Artifact" to one of its groups/)
      ).toBeInTheDocument();
      expect(screen.getByText('Select a collection')).toBeInTheDocument();
    });

    it('filters to only artifact collections', () => {
      renderDialog();

      // Should show the artifact's collections
      expect(screen.getByText('Collection A')).toBeInTheDocument();
      expect(screen.getByText('Collection B')).toBeInTheDocument();

      // Should show artifact counts
      expect(screen.getByText('5 artifacts')).toBeInTheDocument();
      expect(screen.getByText('3 artifacts')).toBeInTheDocument();
    });

    it('fetches all collections when artifact has no collection info', () => {
      // Mock useCollections to return all available collections
      mockUseCollections.mockReturnValue({
        data: { items: mockAllCollections, total: mockAllCollections.length },
        isLoading: false,
        error: null,
      } as any);

      renderDialog({ artifact: mockArtifactNoCollections });

      // Should stay on collection picker step and show all collections
      expect(screen.getByText('Select a collection')).toBeInTheDocument();
      expect(screen.getByText('Collection A')).toBeInTheDocument();
      expect(screen.getByText('Collection B')).toBeInTheDocument();
      expect(screen.getByText('Collection C')).toBeInTheDocument();
    });

    it('shows loading state when fetching all collections', () => {
      // Mock useCollections to be in loading state
      mockUseCollections.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as any);

      renderDialog({ artifact: mockArtifactNoCollections });

      // Should show loading skeletons
      expect(screen.getByText('Select a collection')).toBeInTheDocument();
      const container = document.querySelector('[class*="animate-pulse"]');
      expect(container).toBeInTheDocument();
    });

    it('shows empty state when no collections exist anywhere', () => {
      // Mock useCollections to return empty collections
      mockUseCollections.mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
        error: null,
      } as any);

      renderDialog({ artifact: mockArtifactNoCollections });

      // Should show empty state
      expect(screen.getByText('Select a collection')).toBeInTheDocument();
      expect(screen.getByText('No collections available.')).toBeInTheDocument();
      expect(
        screen.getByText('Create a collection first to organize artifacts into groups.')
      ).toBeInTheDocument();
    });

    it('shows Next button disabled until collection selected', async () => {
      const user = userEvent.setup();
      renderDialog();

      const nextButton = screen.getByRole('button', { name: 'Next' });
      expect(nextButton).toBeDisabled();

      // Select a collection
      await user.click(screen.getByText('Collection A'));

      expect(nextButton).toBeEnabled();
    });

    it('shows Next button disabled while loading all collections', () => {
      // Mock useCollections to be in loading state
      mockUseCollections.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as any);

      renderDialog({ artifact: mockArtifactNoCollections });

      const nextButton = screen.getByRole('button', { name: 'Loading...' });
      expect(nextButton).toBeDisabled();
    });

    it('can select from all collections when artifact has no collections', async () => {
      const user = userEvent.setup();

      // Mock useCollections to return all available collections
      mockUseCollections.mockReturnValue({
        data: { items: mockAllCollections, total: mockAllCollections.length },
        isLoading: false,
        error: null,
      } as any);

      renderDialog({ artifact: mockArtifactNoCollections });

      // Should be able to select any collection
      await user.click(screen.getByText('Collection C'));

      const nextButton = screen.getByRole('button', { name: 'Next' });
      expect(nextButton).toBeEnabled();

      // Click Next to advance to groups
      await user.click(nextButton);

      // Should now be on groups step
      await waitFor(() => {
        expect(screen.getByText('Development')).toBeInTheDocument();
      });
    });

    it('advances to groups step after selecting collection and clicking Next', async () => {
      const user = userEvent.setup();
      renderDialog();

      // Select a collection
      await user.click(screen.getByText('Collection A'));

      // Click Next
      await user.click(screen.getByRole('button', { name: 'Next' }));

      // Should now be on groups step - check for group names
      await waitFor(() => {
        expect(screen.getByText('Development')).toBeInTheDocument();
        expect(screen.getByText('Production')).toBeInTheDocument();
      });
    });
  });

  describe('Groups Selection Step', () => {
    it('skips to groups when collectionId provided', () => {
      renderDialog({ collectionId: 'c1' });

      // Should show groups directly, not collection picker
      expect(screen.getByText('Development')).toBeInTheDocument();
      expect(screen.getByText('Production')).toBeInTheDocument();
      expect(screen.queryByText('Select a collection')).not.toBeInTheDocument();
    });

    it('shows loading state while fetching groups', () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as any);

      renderDialog({ collectionId: 'c1' });

      // Skeletons use data-slot="skeleton" or have animate-pulse class
      // Check for presence of skeleton UI by looking for the Skeleton component's output
      const container = document.querySelector('[class*="animate-pulse"]');
      expect(container).toBeInTheDocument();
    });

    it('shows empty state when no groups exist', () => {
      mockUseGroups.mockReturnValue({
        data: { groups: [], total: 0 },
        isLoading: false,
        error: null,
      } as any);

      renderDialog({ collectionId: 'c1' });

      expect(screen.getByText('No groups in this collection yet.')).toBeInTheDocument();
      expect(screen.getByText('Create a group to organize your artifacts.')).toBeInTheDocument();
    });

    it('displays group list with checkboxes', () => {
      renderDialog({ collectionId: 'c1' });

      expect(screen.getByText('Development')).toBeInTheDocument();
      expect(screen.getByText('Dev tools')).toBeInTheDocument();
      expect(screen.getByText('Production')).toBeInTheDocument();
      expect(screen.getByText('Prod skills')).toBeInTheDocument();

      // Should have checkboxes
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes).toHaveLength(2);
    });

    it('enables Add to Group button when groups are selected', async () => {
      const user = userEvent.setup();
      renderDialog({ collectionId: 'c1' });

      const addButton = screen.getByRole('button', { name: /Add to Group/i });
      expect(addButton).toBeDisabled();

      // Select a group using getAllByRole instead of getByRole with empty name
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      expect(addButton).toBeEnabled();
    });

    it('allows selecting multiple groups', async () => {
      const user = userEvent.setup();
      renderDialog({ collectionId: 'c1' });

      const checkboxes = screen.getAllByRole('checkbox');

      // Select both groups
      await user.click(checkboxes[0]);
      await user.click(checkboxes[1]);

      // Button should say "Add to Groups" (plural)
      expect(screen.getByRole('button', { name: /Add to Groups/i })).toBeEnabled();
    });
  });

  describe('Back Navigation', () => {
    it('shows back button after selecting collection', async () => {
      const user = userEvent.setup();
      renderDialog();

      // Select a collection and advance
      await user.click(screen.getByText('Collection A'));
      await user.click(screen.getByRole('button', { name: 'Next' }));

      // Should show back button with collection name
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Collection A/i })).toBeInTheDocument();
      });
    });

    it('back button returns to collection picker', async () => {
      const user = userEvent.setup();
      renderDialog();

      // Select a collection and advance
      await user.click(screen.getByText('Collection A'));
      await user.click(screen.getByRole('button', { name: 'Next' }));

      // Click back button
      await waitFor(async () => {
        const backButton = screen.getByRole('button', { name: /Collection A/i });
        await user.click(backButton);
      });

      // Should be back at collection picker
      await waitFor(() => {
        expect(screen.getByText('Select a collection')).toBeInTheDocument();
      });
    });

    it('does not show back button when collectionId provided', () => {
      renderDialog({ collectionId: 'c1' });

      // Should not have a back button since we skipped collection picker
      const backButtons = screen
        .queryAllByRole('button')
        .filter((btn) => btn.textContent?.includes('Collection'));
      expect(backButtons).toHaveLength(0);
    });
  });

  describe('Dialog State Reset', () => {
    it('resets state when dialog closes', async () => {
      const user = userEvent.setup();
      const { rerender } = renderDialog();

      // Select a collection and advance
      await user.click(screen.getByText('Collection A'));
      await user.click(screen.getByRole('button', { name: 'Next' }));

      // Select a group
      await waitFor(async () => {
        const checkbox = screen.getAllByRole('checkbox')[0];
        await user.click(checkbox);
      });

      // Close dialog
      rerender(
        <QueryClientProvider client={createQueryClient()}>
          <AddToGroupDialog
            open={false}
            onOpenChange={mockOnOpenChange}
            artifact={mockArtifact}
            onSuccess={mockOnSuccess}
          />
        </QueryClientProvider>
      );

      // Reopen dialog
      rerender(
        <QueryClientProvider client={createQueryClient()}>
          <AddToGroupDialog
            open={true}
            onOpenChange={mockOnOpenChange}
            artifact={mockArtifact}
            onSuccess={mockOnSuccess}
          />
        </QueryClientProvider>
      );

      // Should be back at collection picker step
      expect(screen.getByText('Select a collection')).toBeInTheDocument();
    });
  });

  describe('Submission', () => {
    it('adds artifact to selected groups', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({});

      renderDialog({ collectionId: 'c1' });

      // Select a group
      const checkbox = screen.getAllByRole('checkbox')[0];
      await user.click(checkbox);

      // Submit
      await user.click(screen.getByRole('button', { name: /Add to Group$/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          groupId: 'g1',
          artifactId: 'artifact-1',
        });
      });

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Added to group',
        description: '"Test Artifact" has been added to the group.',
      });

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      expect(mockOnSuccess).toHaveBeenCalled();
    });

    it('adds artifact to multiple groups', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({});

      renderDialog({ collectionId: 'c1' });

      // Select both groups
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);
      await user.click(checkboxes[1]);

      // Submit
      await user.click(screen.getByRole('button', { name: /Add to Groups$/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledTimes(2);
        expect(mockMutateAsync).toHaveBeenCalledWith({
          groupId: 'g1',
          artifactId: 'artifact-1',
        });
        expect(mockMutateAsync).toHaveBeenCalledWith({
          groupId: 'g2',
          artifactId: 'artifact-1',
        });
      });

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Added to groups',
        description: '"Test Artifact" has been added to 2 groups.',
      });
    });

    it('handles submission error', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockRejectedValue(new Error('Network error'));

      renderDialog({ collectionId: 'c1' });

      // Select a group
      const checkbox = screen.getAllByRole('checkbox')[0];
      await user.click(checkbox);

      // Submit
      await user.click(screen.getByRole('button', { name: /Add to Group$/i }));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Failed to add to group',
          description: 'Network error',
          variant: 'destructive',
        });
      });
    });

    it('shows loading state during submission', async () => {
      const user = userEvent.setup();

      // Make mutateAsync hang
      mockMutateAsync.mockImplementation(() => new Promise(() => {}));

      mockUseAddArtifactToGroup.mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: true,
      } as any);

      renderDialog({ collectionId: 'c1' });

      // Select a group
      const checkbox = screen.getAllByRole('checkbox')[0];
      await user.click(checkbox);

      // Check for loading state
      expect(screen.getByText('Adding...')).toBeInTheDocument();
    });

    it('disables cancel button during submission', async () => {
      mockUseAddArtifactToGroup.mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: true,
      } as any);

      renderDialog({ collectionId: 'c1' });

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      expect(cancelButton).toBeDisabled();
    });
  });

  describe('Cancel Behavior', () => {
    it('closes dialog on cancel', async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.click(screen.getByRole('button', { name: 'Cancel' }));

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('does not close during pending submission', async () => {
      mockUseAddArtifactToGroup.mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: true,
      } as any);

      renderDialog({ collectionId: 'c1' });

      // Try to close via callback
      const closeHandler = mockOnOpenChange.mock.calls.find(
        (call) => typeof call[0] === 'boolean' && call[0] === false
      );
      expect(closeHandler).toBeUndefined();
    });
  });
});
