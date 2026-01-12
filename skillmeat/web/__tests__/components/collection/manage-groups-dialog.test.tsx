import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ManageGroupsDialog } from '@/components/collection/manage-groups-dialog';
import { useGroups, useCreateGroup, useUpdateGroup, useDeleteGroup, useToast } from '@/hooks';

// Mock hooks
jest.mock('@/hooks', () => ({
  useGroups: jest.fn(),
  useCreateGroup: jest.fn(),
  useUpdateGroup: jest.fn(),
  useDeleteGroup: jest.fn(),
  useToast: jest.fn(),
}));

const mockUseGroups = useGroups as jest.MockedFunction<typeof useGroups>;
const mockUseCreateGroup = useCreateGroup as jest.MockedFunction<typeof useCreateGroup>;
const mockUseUpdateGroup = useUpdateGroup as jest.MockedFunction<typeof useUpdateGroup>;
const mockUseDeleteGroup = useDeleteGroup as jest.MockedFunction<typeof useDeleteGroup>;
const mockUseToast = useToast as jest.MockedFunction<typeof useToast>;

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
      // Skeleton components are rendered (check for multiple skeleton elements)
      const skeletons = document.querySelectorAll('[class*="skeleton"]');
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
      const createButton = screen.getByText('Create Group');
      fireEvent.click(createButton);

      expect(screen.getByText('Create New Group')).toBeInTheDocument();
      expect(screen.getByLabelText(/Name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
    });

    it('validates required name field', async () => {
      renderDialog();
      fireEvent.click(screen.getByText('Create Group'));

      // Try to submit without name
      const submitButton = screen.getAllByText('Create Group')[1]; // Second one is in form
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Group name is required')).toBeInTheDocument();
      });
    });

    it('validates name length', async () => {
      renderDialog();
      fireEvent.click(screen.getByText('Create Group'));

      const nameInput = screen.getByLabelText(/Name/i);
      fireEvent.change(nameInput, { target: { value: 'a'.repeat(256) } });

      const submitButton = screen.getAllByText('Create Group')[1];
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/must be between 1 and 255 characters/i)).toBeInTheDocument();
      });
    });

    it('validates description length', async () => {
      renderDialog();
      fireEvent.click(screen.getByText('Create Group'));

      const nameInput = screen.getByLabelText(/Name/i);
      const descInput = screen.getByLabelText(/Description/i);

      fireEvent.change(nameInput, { target: { value: 'Test Group' } });
      fireEvent.change(descInput, { target: { value: 'a'.repeat(1001) } });

      const submitButton = screen.getAllByText('Create Group')[1];
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/must be less than 1000 characters/i)
        ).toBeInTheDocument();
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
      fireEvent.click(screen.getByText('Create Group'));

      const nameInput = screen.getByLabelText(/Name/i);
      const descInput = screen.getByLabelText(/Description/i);

      fireEvent.change(nameInput, { target: { value: 'Test Group' } });
      fireEvent.change(descInput, { target: { value: 'Test description' } });

      const submitButton = screen.getAllByText('Create Group')[1];
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
      fireEvent.click(screen.getByText('Create Group'));

      const nameInput = screen.getByLabelText(/Name/i);
      fireEvent.change(nameInput, { target: { value: 'Test Group' } });

      const submitButton = screen.getAllByText('Create Group')[1];
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

      // Find and click first edit button
      const editButtons = screen.getAllByRole('button', { name: '' });
      const editButton = editButtons.find((btn) =>
        btn.querySelector('svg[class*="lucide-edit"]')
      );

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
      const editButtons = screen.getAllByRole('button', { name: '' });
      const editButton = editButtons.find((btn) =>
        btn.querySelector('svg[class*="lucide-edit"]')
      );
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
      const editButtons = screen.getAllByRole('button', { name: '' });
      const editButton = editButtons.find((btn) =>
        btn.querySelector('svg[class*="lucide-edit"]')
      );
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

      // Find and click first delete button
      const deleteButtons = screen.getAllByRole('button', { name: '' });
      const deleteButton = deleteButtons.find((btn) =>
        btn.querySelector('svg[class*="lucide-trash"]')
      );

      fireEvent.click(deleteButton!);

      expect(screen.getByText('Delete Group?')).toBeInTheDocument();
      expect(
        screen.getByText('This will remove all artifacts from this group.')
      ).toBeInTheDocument();
      expect(
        screen.getByText(/The artifacts themselves will not be deleted/i)
      ).toBeInTheDocument();
    });

    it('deletes group successfully', async () => {
      const mutateAsync = jest.fn().mockResolvedValue(undefined);

      mockUseDeleteGroup.mockReturnValue({
        mutateAsync,
        isPending: false,
      } as any);

      renderDialog();

      // Click delete button
      const deleteButtons = screen.getAllByRole('button', { name: '' });
      const deleteButton = deleteButtons.find((btn) =>
        btn.querySelector('svg[class*="lucide-trash"]')
      );
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
});
