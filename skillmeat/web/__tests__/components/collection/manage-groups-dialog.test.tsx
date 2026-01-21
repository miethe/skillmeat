import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ManageGroupsDialog } from '@/components/collection/manage-groups-dialog';
import {
  useGroups,
  useCreateGroup,
  useUpdateGroup,
  useDeleteGroup,
  useToast,
  useCollections,
  useCopyGroup,
} from '@/hooks';

// Mock hooks
jest.mock('@/hooks', () => ({
  useGroups: jest.fn(),
  useCreateGroup: jest.fn(),
  useUpdateGroup: jest.fn(),
  useDeleteGroup: jest.fn(),
  useToast: jest.fn(),
  useCollections: jest.fn(),
  useCopyGroup: jest.fn(),
}));

const mockUseGroups = useGroups as jest.MockedFunction<typeof useGroups>;
const mockUseCreateGroup = useCreateGroup as jest.MockedFunction<typeof useCreateGroup>;
const mockUseUpdateGroup = useUpdateGroup as jest.MockedFunction<typeof useUpdateGroup>;
const mockUseDeleteGroup = useDeleteGroup as jest.MockedFunction<typeof useDeleteGroup>;
const mockUseToast = useToast as jest.MockedFunction<typeof useToast>;
const mockUseCollections = useCollections as jest.MockedFunction<typeof useCollections>;
const mockUseCopyGroup = useCopyGroup as jest.MockedFunction<typeof useCopyGroup>;

describe('ManageGroupsDialog', () => {
  const mockToast = jest.fn();
  const mockOnOpenChange = jest.fn();
  const collectionId = 'test-collection-1';

  const mockGroups = [
    {
      id: 'group-1',
      collection_id: collectionId,
      name: 'Development',
      description: 'Dev tools and utilities',
      position: 0,
      artifact_count: 5,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'group-2',
      collection_id: collectionId,
      name: 'Production',
      description: 'Production-ready skills',
      position: 1,
      artifact_count: 3,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    },
  ];

  const mockCollections = [
    {
      id: collectionId,
      name: 'Current Collection',
      artifact_count: 10,
    },
    {
      id: 'other-collection-1',
      name: 'Other Collection',
      artifact_count: 5,
    },
    {
      id: 'other-collection-2',
      name: 'Another Collection',
      artifact_count: 3,
    },
  ];

  const createQueryClient = () =>
    new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

  beforeEach(() => {
    jest.clearAllMocks();

    mockUseToast.mockReturnValue({ toast: mockToast } as any);

    mockUseGroups.mockReturnValue({
      data: { groups: mockGroups, total: mockGroups.length },
      isLoading: false,
      error: null,
    } as any);

    mockUseCreateGroup.mockReturnValue({
      mutateAsync: jest.fn(),
      isPending: false,
    } as any);

    mockUseUpdateGroup.mockReturnValue({
      mutateAsync: jest.fn(),
      isPending: false,
    } as any);

    mockUseDeleteGroup.mockReturnValue({
      mutateAsync: jest.fn(),
      isPending: false,
    } as any);

    mockUseCollections.mockReturnValue({
      data: { items: mockCollections, total: mockCollections.length },
      isLoading: false,
      error: null,
    } as any);

    mockUseCopyGroup.mockReturnValue({
      mutateAsync: jest.fn(),
      isPending: false,
    } as any);
  });

  const renderDialog = (open = true) => {
    const queryClient = createQueryClient();
    return render(
      <QueryClientProvider client={queryClient}>
        <ManageGroupsDialog
          open={open}
          onOpenChange={mockOnOpenChange}
          collectionId={collectionId}
        />
      </QueryClientProvider>
    );
  };

  // Find the first group's action buttons container
  const findFirstGroupActions = () => {
    // Find group cards by looking for the group name
    const devGroup = screen.getByText('Development').closest('[class*="card"]');
    if (devGroup) {
      const actionContainer = devGroup.querySelector('.flex.gap-1');
      if (actionContainer) {
        return within(actionContainer as HTMLElement).getAllByRole('button');
      }
    }
    return [];
  };

  describe('Rendering', () => {
    it('renders dialog title and description', () => {
      renderDialog();
      expect(screen.getByText('Manage Groups')).toBeInTheDocument();
      expect(
        screen.getByText('Organize artifacts into groups within this collection')
      ).toBeInTheDocument();
    });

    it('displays loading state while fetching groups', () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as any);

      renderDialog();
      // Skeleton components use animate-pulse class
      const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('displays empty state when no groups exist', () => {
      mockUseGroups.mockReturnValue({
        data: { groups: [], total: 0 },
        isLoading: false,
        error: null,
      } as any);

      renderDialog();
      expect(screen.getByText('No groups yet. Create one below.')).toBeInTheDocument();
    });

    it('displays list of groups', () => {
      renderDialog();
      expect(screen.getByText('Development')).toBeInTheDocument();
      expect(screen.getByText('Dev tools and utilities')).toBeInTheDocument();
      expect(screen.getByText('Production')).toBeInTheDocument();
      expect(screen.getByText('Production-ready skills')).toBeInTheDocument();
    });

    it('displays artifact count badges', () => {
      renderDialog();
      // Should show artifact counts (5 and 3)
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  describe('Create Group', () => {
    it('shows create form when Create Group button is clicked', () => {
      renderDialog();
      const createButton = screen.getByRole('button', { name: /Create Group/i });
      fireEvent.click(createButton);

      expect(screen.getByText('Create New Group')).toBeInTheDocument();
      expect(screen.getByLabelText(/Name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
    });

    it('validates required name field', async () => {
      renderDialog();
      // Click the outline button to open form
      fireEvent.click(screen.getByRole('button', { name: /Create Group/i }));

      // Find the submit button in the form by its text content
      const formButtons = screen
        .getAllByRole('button')
        .filter((btn) => btn.textContent === 'Create Group' && !btn.classList.contains('w-full'));
      const submitButton = formButtons[formButtons.length - 1];
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Group name is required')).toBeInTheDocument();
      });
    });

    it('validates name length', async () => {
      renderDialog();
      fireEvent.click(screen.getByRole('button', { name: /Create Group/i }));

      const nameInput = screen.getByLabelText(/Name/i);
      fireEvent.change(nameInput, { target: { value: 'a'.repeat(256) } });

      const formButtons = screen
        .getAllByRole('button')
        .filter((btn) => btn.textContent === 'Create Group' && !btn.classList.contains('w-full'));
      const submitButton = formButtons[formButtons.length - 1];
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/must be between 1 and 255 characters/i)).toBeInTheDocument();
      });
    });

    it('validates description length', async () => {
      renderDialog();
      fireEvent.click(screen.getByRole('button', { name: /Create Group/i }));

      const nameInput = screen.getByLabelText(/Name/i);
      const descInput = screen.getByLabelText(/Description/i);

      fireEvent.change(nameInput, { target: { value: 'Test Group' } });
      fireEvent.change(descInput, { target: { value: 'a'.repeat(1001) } });

      const formButtons = screen
        .getAllByRole('button')
        .filter((btn) => btn.textContent === 'Create Group' && !btn.classList.contains('w-full'));
      const submitButton = formButtons[formButtons.length - 1];
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/must be less than 1000 characters/i)).toBeInTheDocument();
      });
    });

    it('creates group successfully', async () => {
      const mutateAsync = jest.fn().mockResolvedValue({
        id: 'new-group',
        name: 'Test Group',
        description: 'Test description',
      });

      mockUseCreateGroup.mockReturnValue({
        mutateAsync,
        isPending: false,
      } as any);

      renderDialog();
      fireEvent.click(screen.getByRole('button', { name: /Create Group/i }));

      const nameInput = screen.getByLabelText(/Name/i);
      const descInput = screen.getByLabelText(/Description/i);

      fireEvent.change(nameInput, { target: { value: 'Test Group' } });
      fireEvent.change(descInput, { target: { value: 'Test description' } });

      const formButtons = screen
        .getAllByRole('button')
        .filter((btn) => btn.textContent === 'Create Group' && !btn.classList.contains('w-full'));
      const submitButton = formButtons[formButtons.length - 1];
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mutateAsync).toHaveBeenCalledWith({
          collection_id: collectionId,
          name: 'Test Group',
          description: 'Test description',
          position: 2, // After existing 2 groups
        });
      });

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Group created',
        description: 'Successfully created group "Test Group"',
      });
    });

    it('handles create error', async () => {
      const mutateAsync = jest.fn().mockRejectedValue(new Error('Failed to create'));

      mockUseCreateGroup.mockReturnValue({
        mutateAsync,
        isPending: false,
      } as any);

      renderDialog();
      fireEvent.click(screen.getByRole('button', { name: /Create Group/i }));

      const nameInput = screen.getByLabelText(/Name/i);
      fireEvent.change(nameInput, { target: { value: 'Test Group' } });

      const formButtons = screen
        .getAllByRole('button')
        .filter((btn) => btn.textContent === 'Create Group' && !btn.classList.contains('w-full'));
      const submitButton = formButtons[formButtons.length - 1];
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Failed to create group',
          description: 'Failed to create',
          variant: 'destructive',
        });
      });
    });
  });

  describe('Edit Group', () => {
    it('enters edit mode when edit button is clicked', () => {
      renderDialog();

      // Get the first group's action buttons (Copy, Edit, Delete)
      const actionButtons = findFirstGroupActions();
      // Edit button is second (index 1): Copy=0, Edit=1, Delete=2
      const editButton = actionButtons[1];

      expect(editButton).toBeTruthy();
      fireEvent.click(editButton!);

      // Should show Save and Cancel buttons
      expect(screen.getByText('Save')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('updates group successfully', async () => {
      const mutateAsync = jest.fn().mockResolvedValue({});

      mockUseUpdateGroup.mockReturnValue({
        mutateAsync,
        isPending: false,
      } as any);

      renderDialog();

      // Enter edit mode
      const actionButtons = findFirstGroupActions();
      const editButton = actionButtons[1];
      fireEvent.click(editButton!);

      // Change name
      const nameInput = screen.getByDisplayValue('Development');
      fireEvent.change(nameInput, { target: { value: 'Development Updated' } });

      // Save
      const saveButton = screen.getByText('Save');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mutateAsync).toHaveBeenCalledWith({
          id: 'group-1',
          data: {
            name: 'Development Updated',
            description: undefined,
          },
        });
      });

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Group updated',
        description: 'Successfully updated group "Development Updated"',
      });
    });

    it('shows "No changes" message when nothing changed', async () => {
      renderDialog();

      // Enter edit mode
      const actionButtons = findFirstGroupActions();
      const editButton = actionButtons[1];
      fireEvent.click(editButton!);

      // Save without changes
      const saveButton = screen.getByText('Save');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'No changes',
          description: 'No changes were made to the group',
        });
      });
    });
  });

  describe('Delete Group', () => {
    it('shows confirmation dialog when delete button is clicked', () => {
      renderDialog();

      // Get the first group's action buttons
      const actionButtons = findFirstGroupActions();
      // Delete button is third (index 2)
      const deleteButton = actionButtons[2];

      expect(deleteButton).toBeTruthy();
      fireEvent.click(deleteButton!);

      expect(screen.getByText('Delete Group?')).toBeInTheDocument();
      expect(
        screen.getByText('This will remove all artifacts from this group.')
      ).toBeInTheDocument();
      expect(screen.getByText(/The artifacts themselves will not be deleted/i)).toBeInTheDocument();
    });

    it('deletes group successfully', async () => {
      const mutateAsync = jest.fn().mockResolvedValue(undefined);

      mockUseDeleteGroup.mockReturnValue({
        mutateAsync,
        isPending: false,
      } as any);

      renderDialog();

      // Click delete button
      const actionButtons = findFirstGroupActions();
      const deleteButton = actionButtons[2];
      fireEvent.click(deleteButton!);

      // Confirm deletion
      const confirmButton = screen.getByText('Delete Group');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mutateAsync).toHaveBeenCalledWith({
          id: 'group-1',
          collectionId: collectionId,
        });
      });

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Group deleted',
        description: 'Successfully deleted group "Development"',
      });
    });
  });

  describe('Copy Group', () => {
    it('shows copy button for each group', () => {
      renderDialog();

      // Find copy buttons by aria-label
      const copyButtons = screen.getAllByRole('button', { name: /Copy group/i });
      expect(copyButtons).toHaveLength(2); // One for each group
    });

    it('opens copy dialog when copy button is clicked', () => {
      renderDialog();

      // Find and click first copy button
      const copyButton = screen.getByRole('button', {
        name: /Copy group "Development" to another collection/i,
      });
      fireEvent.click(copyButton);

      // Copy dialog should open
      expect(screen.getByText('Copy Group to Collection')).toBeInTheDocument();
    });

    it('shows available collections in copy dialog (excluding source)', () => {
      renderDialog();

      // Open copy dialog
      const copyButton = screen.getByRole('button', {
        name: /Copy group "Development" to another collection/i,
      });
      fireEvent.click(copyButton);

      // Should show other collections but not the source collection
      expect(screen.getByText('Other Collection')).toBeInTheDocument();
      expect(screen.getByText('Another Collection')).toBeInTheDocument();
      // Source collection should not be in the list
      expect(screen.queryByText('Current Collection')).not.toBeInTheDocument();
    });

    it('copy button is disabled when editing a group', () => {
      renderDialog();

      // Enter edit mode on first group
      const actionButtons = findFirstGroupActions();
      const editButton = actionButtons[1];
      fireEvent.click(editButton!);

      // Copy buttons should be disabled
      const copyButtons = screen.getAllByRole('button', { name: /Copy group/i });
      copyButtons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });

    it('copies group successfully', async () => {
      const copyMutateAsync = jest.fn().mockResolvedValue({
        id: 'copied-group',
        name: 'Development',
      });

      mockUseCopyGroup.mockReturnValue({
        mutateAsync: copyMutateAsync,
        isPending: false,
      } as any);

      renderDialog();

      // Open copy dialog
      const copyButton = screen.getByRole('button', {
        name: /Copy group "Development" to another collection/i,
      });
      fireEvent.click(copyButton);

      // Select a target collection
      const targetOption = screen.getByLabelText(/Select Other Collection/i);
      fireEvent.click(targetOption);

      // Click Copy Group button
      const submitButton = screen.getByRole('button', {
        name: /Copy group to selected collection/i,
      });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(copyMutateAsync).toHaveBeenCalledWith({
          groupId: 'group-1',
          targetCollectionId: 'other-collection-1',
        });
      });

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Group copied',
        description: '"Development" has been copied to Other Collection.',
      });
    });
  });
});
