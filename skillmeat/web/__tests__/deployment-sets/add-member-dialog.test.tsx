/**
 * Tests for AddMemberDialog
 *
 * Covers:
 *  - Three tabs render (Artifacts, Groups, Sets)
 *  - Selecting an artifact calls the add-member mutation
 *  - A 422 / "circular" error shows a circular-reference error toast
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AddMemberDialog } from '@/components/deployment-sets/add-member-dialog';
import {
  useAddMember,
  useArtifacts,
  useDeploymentSets,
  useToast,
} from '@/hooks';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('@/hooks', () => ({
  useAddMember: jest.fn(),
  useArtifacts: jest.fn(),
  useDeploymentSets: jest.fn(),
  useToast: jest.fn(),
}));

// GroupTab uses raw fetch — mock it globally
global.fetch = jest.fn();

const mockUseAddMember = useAddMember as jest.MockedFunction<typeof useAddMember>;
const mockUseArtifacts = useArtifacts as jest.MockedFunction<typeof useArtifacts>;
const mockUseDeploymentSets = useDeploymentSets as jest.MockedFunction<typeof useDeploymentSets>;
const mockUseToast = useToast as jest.MockedFunction<typeof useToast>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

interface RenderOptions {
  open?: boolean;
  setId?: string;
}

function renderDialog({ open = true, setId = 'set-abc-123' }: RenderOptions = {}) {
  const onOpenChange = jest.fn();
  const queryClient = createQueryClient();

  const utils = render(
    <QueryClientProvider client={queryClient}>
      <AddMemberDialog open={open} onOpenChange={onOpenChange} setId={setId} />
    </QueryClientProvider>,
  );

  return { ...utils, onOpenChange };
}

// Minimal mock artifacts
const mockArtifacts = [
  {
    id: 'skill:canvas',
    uuid: 'aaaa-0001',
    name: 'Canvas Design',
    type: 'skill' as const,
    scope: 'user' as const,
    syncStatus: 'synced' as const,
    source: 'anthropics/skills/canvas-design',
    description: 'Design canvas skill',
    tags: [],
    upstream: { enabled: false, updateAvailable: false },
    usageStats: { totalDeployments: 0, activeProjects: 0, usageCount: 0 },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    aliases: [],
    collections: [],
  },
  {
    id: 'command:git-commit',
    uuid: 'bbbb-0002',
    name: 'Git Commit',
    type: 'command' as const,
    scope: 'user' as const,
    syncStatus: 'synced' as const,
    source: 'anthropics/commands/git-commit',
    description: 'Git commit command',
    tags: [],
    upstream: { enabled: false, updateAvailable: false },
    usageStats: { totalDeployments: 0, activeProjects: 0, usageCount: 0 },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    aliases: [],
    collections: [],
  },
];

// Minimal mock deployment sets
const mockSets = [
  {
    id: 'set-other-1',
    name: 'Production Set',
    description: 'Prod artifacts',
    icon: null,
    color: '#3b82f6',
    tags: [],
    owner_id: null,
    member_count: 3,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'set-other-2',
    name: 'Staging Set',
    description: null,
    icon: '🚀',
    color: null,
    tags: [],
    owner_id: null,
    member_count: 1,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
];

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

const mockMutateAsync = jest.fn();
const mockToast = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();

  mockUseToast.mockReturnValue({ toast: mockToast } as any);

  mockUseAddMember.mockReturnValue({
    mutateAsync: mockMutateAsync,
    isPending: false,
  } as any);

  mockUseArtifacts.mockReturnValue({
    data: { artifacts: mockArtifacts, total: mockArtifacts.length },
    isLoading: false,
    error: null,
  } as any);

  mockUseDeploymentSets.mockReturnValue({
    data: { items: mockSets, total: mockSets.length },
    isLoading: false,
    error: null,
  } as any);

  // Default fetch mock for GroupTab (returns empty groups)
  (global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    json: async () => ({ groups: [], total: 0 }),
  });
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AddMemberDialog', () => {
  describe('Tab structure', () => {
    it('renders the dialog with Artifacts, Groups, and Sets tabs', async () => {
      renderDialog();

      expect(screen.getByRole('dialog')).toBeInTheDocument();

      // All three tab triggers should be visible
      expect(screen.getByRole('tab', { name: /artifacts/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /groups/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /sets/i })).toBeInTheDocument();
    });

    it('shows the Artifacts tab as active by default', () => {
      renderDialog();

      const artifactsTab = screen.getByRole('tab', { name: /artifacts/i });
      expect(artifactsTab).toHaveAttribute('data-state', 'active');
    });

    it('switches to the Groups tab when clicked', async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.click(screen.getByRole('tab', { name: /groups/i }));

      const groupsTab = screen.getByRole('tab', { name: /groups/i });
      expect(groupsTab).toHaveAttribute('data-state', 'active');
    });

    it('switches to the Sets tab when clicked', async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.click(screen.getByRole('tab', { name: /sets/i }));

      const setsTab = screen.getByRole('tab', { name: /sets/i });
      expect(setsTab).toHaveAttribute('data-state', 'active');
    });

    it('renders the dialog title "Add Member"', () => {
      renderDialog();
      expect(screen.getByText('Add Member')).toBeInTheDocument();
    });

    it('renders a Done button to close', () => {
      renderDialog();
      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument();
    });
  });

  describe('Artifacts tab', () => {
    it('renders artifact list items', async () => {
      renderDialog();

      await waitFor(() => {
        expect(screen.getByText('Canvas Design')).toBeInTheDocument();
        expect(screen.getByText('Git Commit')).toBeInTheDocument();
      });
    });

    it('shows artifact type badges', async () => {
      renderDialog();

      await waitFor(() => {
        expect(screen.getByText('Skill')).toBeInTheDocument();
        expect(screen.getByText('Command')).toBeInTheDocument();
      });
    });

    it('shows loading skeletons when artifacts are loading', () => {
      mockUseArtifacts.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as any);

      renderDialog();

      expect(screen.getByRole('list', { name: /loading artifacts/i })).toBeInTheDocument();
    });

    it('shows empty state when no artifacts exist', () => {
      mockUseArtifacts.mockReturnValue({
        data: { artifacts: [], total: 0 },
        isLoading: false,
        error: null,
      } as any);

      renderDialog();

      expect(screen.getByText('No artifacts in your collection.')).toBeInTheDocument();
    });

    it('calls addMember mutation when an artifact is selected', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({});

      renderDialog({ setId: 'set-abc-123' });

      await waitFor(() => {
        expect(screen.getByText('Canvas Design')).toBeInTheDocument();
      });

      const item = screen.getByRole('listitem', { name: /add canvas design/i });
      await user.click(item);

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          setId: 'set-abc-123',
          data: { artifact_uuid: 'aaaa-0001' },
        });
      });
    });

    it('shows a success toast after adding an artifact', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({});

      renderDialog();

      await waitFor(() => expect(screen.getByText('Canvas Design')).toBeInTheDocument());
      await user.click(screen.getByRole('listitem', { name: /add canvas design/i }));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Member added',
          }),
        );
      });
    });

    it('shows a generic error toast when a non-circular add fails', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockRejectedValue(new Error('Network error'));

      renderDialog();

      await waitFor(() => expect(screen.getByText('Canvas Design')).toBeInTheDocument());
      await user.click(screen.getByRole('listitem', { name: /add canvas design/i }));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Failed to add member',
            variant: 'destructive',
          }),
        );
      });
    });
  });

  describe('Circular reference error handling (Artifact tab)', () => {
    it('shows a circular reference toast when error message contains "circular"', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockRejectedValue(new Error('circular reference detected'));

      renderDialog();

      await waitFor(() => expect(screen.getByText('Canvas Design')).toBeInTheDocument());
      await user.click(screen.getByRole('listitem', { name: /add canvas design/i }));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Circular reference',
            description: 'This would create a circular reference.',
            variant: 'destructive',
          }),
        );
      });
    });

    it('shows a circular reference toast when error has status 422', async () => {
      const user = userEvent.setup();
      const err422 = Object.assign(new Error('Unprocessable Entity'), { status: 422 });
      mockMutateAsync.mockRejectedValue(err422);

      renderDialog();

      await waitFor(() => expect(screen.getByText('Canvas Design')).toBeInTheDocument());
      await user.click(screen.getByRole('listitem', { name: /add canvas design/i }));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Circular reference',
            description: 'This would create a circular reference.',
            variant: 'destructive',
          }),
        );
      });
    });
  });

  describe('Groups tab', () => {
    const mockGroups = [
      { id: 'g-1', name: 'Core Tools', artifact_count: 4, color: '#10b981' },
      { id: 'g-2', name: 'Dev Utilities', artifact_count: 7 },
    ];

    beforeEach(() => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ groups: mockGroups, total: mockGroups.length }),
      });
    });

    it('renders groups after switching to the Groups tab', async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.click(screen.getByRole('tab', { name: /groups/i }));

      await waitFor(() => {
        expect(screen.getByText('Core Tools')).toBeInTheDocument();
        expect(screen.getByText('Dev Utilities')).toBeInTheDocument();
      });
    });

    it('shows artifact counts on group items', async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.click(screen.getByRole('tab', { name: /groups/i }));

      await waitFor(() => {
        expect(screen.getByText('4 artifacts')).toBeInTheDocument();
        expect(screen.getByText('7 artifacts')).toBeInTheDocument();
      });
    });

    it('calls addMember mutation with group_id when a group is selected', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({});

      renderDialog({ setId: 'set-abc-123' });

      await user.click(screen.getByRole('tab', { name: /groups/i }));

      await waitFor(() => expect(screen.getByText('Core Tools')).toBeInTheDocument());

      await user.click(screen.getByRole('listitem', { name: /add group core tools/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          setId: 'set-abc-123',
          data: { group_id: 'g-1' },
        });
      });
    });

    it('shows empty state when no groups exist', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ groups: [], total: 0 }),
      });

      const user = userEvent.setup();
      renderDialog();

      await user.click(screen.getByRole('tab', { name: /groups/i }));

      await waitFor(() => {
        expect(screen.getByText('No groups found.')).toBeInTheDocument();
      });
    });
  });

  describe('Sets tab', () => {
    it('renders other deployment sets after switching to the Sets tab', async () => {
      const user = userEvent.setup();
      renderDialog({ setId: 'set-abc-123' });

      await user.click(screen.getByRole('tab', { name: /sets/i }));

      await waitFor(() => {
        expect(screen.getByText('Production Set')).toBeInTheDocument();
        expect(screen.getByText('Staging Set')).toBeInTheDocument();
      });
    });

    it('excludes the current set from the picker', async () => {
      // Add the current set's ID into the mock list
      mockUseDeploymentSets.mockReturnValue({
        data: {
          items: [
            ...mockSets,
            {
              id: 'set-abc-123',
              name: 'Current Set',
              description: null,
              icon: null,
              color: null,
              tags: [],
              owner_id: null,
              member_count: 0,
              created_at: '2024-01-03T00:00:00Z',
              updated_at: '2024-01-03T00:00:00Z',
            },
          ],
          total: 3,
        },
        isLoading: false,
        error: null,
      } as any);

      const user = userEvent.setup();
      renderDialog({ setId: 'set-abc-123' });

      await user.click(screen.getByRole('tab', { name: /sets/i }));

      await waitFor(() => {
        expect(screen.getByText('Production Set')).toBeInTheDocument();
      });

      expect(screen.queryByText('Current Set')).not.toBeInTheDocument();
    });

    it('calls addMember mutation with nested_set_id when a set is selected', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({});

      renderDialog({ setId: 'set-abc-123' });

      await user.click(screen.getByRole('tab', { name: /sets/i }));

      await waitFor(() => expect(screen.getByText('Production Set')).toBeInTheDocument());

      await user.click(screen.getByRole('listitem', { name: /add deployment set production set/i }));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          setId: 'set-abc-123',
          data: { nested_set_id: 'set-other-1' },
        });
      });
    });

    it('shows member count badges on set items', async () => {
      const user = userEvent.setup();
      renderDialog();

      await user.click(screen.getByRole('tab', { name: /sets/i }));

      await waitFor(() => {
        expect(screen.getByText('3 members')).toBeInTheDocument();
        expect(screen.getByText('1 member')).toBeInTheDocument();
      });
    });

    it('shows a circular reference toast when a set addition returns 422', async () => {
      const user = userEvent.setup();
      const err422 = Object.assign(new Error('Unprocessable Entity'), { status: 422 });
      mockMutateAsync.mockRejectedValue(err422);

      renderDialog();

      await user.click(screen.getByRole('tab', { name: /sets/i }));

      await waitFor(() => expect(screen.getByText('Production Set')).toBeInTheDocument());

      await user.click(
        screen.getByRole('listitem', { name: /add deployment set production set/i }),
      );

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Circular reference',
            description: 'This would create a circular reference.',
            variant: 'destructive',
          }),
        );
      });
    });

    it('shows empty state when no other sets exist', async () => {
      mockUseDeploymentSets.mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
        error: null,
      } as any);

      const user = userEvent.setup();
      renderDialog({ setId: 'set-abc-123' });

      await user.click(screen.getByRole('tab', { name: /sets/i }));

      await waitFor(() => {
        expect(screen.getByText('No other deployment sets exist.')).toBeInTheDocument();
      });
    });
  });

  describe('Done button', () => {
    it('calls onOpenChange(false) when Done is clicked', async () => {
      const user = userEvent.setup();
      const { onOpenChange } = renderDialog();

      await user.click(screen.getByRole('button', { name: /done/i }));

      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });
});
