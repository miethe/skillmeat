/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GroupedArtifactView } from '@/components/collection/grouped-artifact-view';
import type { Artifact } from '@/types/artifact';

// ---------------------------------------------------------------------------
// Mock @dnd-kit (no-op wrappers so the tree renders without actual DnD)
// ---------------------------------------------------------------------------

jest.mock('@dnd-kit/core', () => ({
  __esModule: true,
  DndContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  DragOverlay: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  closestCenter: jest.fn(),
  KeyboardSensor: jest.fn(),
  PointerSensor: jest.fn(),
  useSensor: jest.fn(),
  useSensors: jest.fn(),
  useDroppable: jest.fn(),
}));

jest.mock('@dnd-kit/sortable', () => ({
  __esModule: true,
  SortableContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  sortableKeyboardCoordinates: jest.fn(),
  rectSortingStrategy: jest.fn(),
  useSortable: jest.fn(),
}));

jest.mock('@dnd-kit/utilities', () => ({
  __esModule: true,
  CSS: { Transform: { toString: () => undefined } },
}));

// ---------------------------------------------------------------------------
// Mock hooks (barrel import)
// ---------------------------------------------------------------------------

jest.mock('@/hooks', () => ({
  useGroups: jest.fn(),
  useGroupArtifacts: jest.fn(),
  useGroupsArtifacts: jest.fn(),
  useAddArtifactToGroup: jest.fn(),
  useRemoveArtifactFromGroup: jest.fn(),
  useReorderArtifactsInGroup: jest.fn(),
  useCreateGroup: jest.fn(),
  useArtifactGroups: jest.fn(),
  useTags: jest.fn(),
  useDndAnimations: () => ({
    animState: { phase: 'idle', targetGroupId: null, sourceGroupId: null, targetRect: null },
    triggerDropIntoGroup: jest.fn(),
    triggerRemovePoof: jest.fn(),
    reset: jest.fn(),
  }),
}));

// Mock sonner toast
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  },
}));

// Mock GroupFormDialog (it uses useToast internally which is not mocked here)
jest.mock('@/app/groups/components/group-form-dialog', () => ({
  GroupFormDialog: ({ open, onOpenChange, group }: { open: boolean; onOpenChange: (o: boolean) => void; group?: unknown }) => (
    open ? (
      <div data-testid={group ? 'edit-group-dialog' : 'create-group-dialog'}>
        <button onClick={() => onOpenChange(false)}>Close</button>
      </div>
    ) : null
  ),
}));

// Import mocked modules for beforeEach setup
import { useDroppable } from '@dnd-kit/core';
import { useSortable } from '@dnd-kit/sortable';
import {
  useGroups,
  useGroupArtifacts,
  useGroupsArtifacts,
  useAddArtifactToGroup,
  useRemoveArtifactFromGroup,
  useReorderArtifactsInGroup,
  useCreateGroup,
  useArtifactGroups,
  useTags,
} from '@/hooks';
import { useSensor, useSensors } from '@dnd-kit/core';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const makeArtifact = (overrides: Partial<Artifact> & { id: string; name: string }): Artifact => ({
  type: 'skill',
  scope: 'user',
  syncStatus: 'synced',
  version: '1.0.0',
  description: '',
  tags: [],
  upstream: { enabled: false, updateAvailable: false },
  usageStats: { totalDeployments: 0, activeProjects: 0, usageCount: 0 },
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  ...overrides,
});

const art1 = makeArtifact({ id: 'art-1', name: 'canvas-design', description: 'A design skill' });
const art2 = makeArtifact({ id: 'art-2', name: 'code-review', description: 'Reviews code' });
const art3 = makeArtifact({ id: 'art-3', name: 'doc-writer', description: 'Writes docs' });

const mockArtifacts: Artifact[] = [art1, art2, art3];

const testGroup = {
  id: 'group-1',
  collection_id: 'test-collection',
  name: 'Design Tools',
  description: 'Tools for design',
  tags: [],
  color: 'blue',
  icon: 'layers',
  position: 0,
  artifact_count: 1,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const secondGroup = {
  id: 'group-2',
  collection_id: 'test-collection',
  name: 'Dev Tools',
  description: 'Developer tools',
  tags: [],
  color: 'green',
  icon: 'code',
  position: 1,
  artifact_count: 1,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockMutateAsync = jest.fn();

function setupDndMocks() {
  (useDroppable as jest.Mock).mockReturnValue({ setNodeRef: jest.fn(), isOver: false });
  (useSortable as jest.Mock).mockReturnValue({
    attributes: {},
    listeners: {},
    setNodeRef: jest.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  });
  (useSensor as jest.Mock).mockReturnValue({});
  (useSensors as jest.Mock).mockReturnValue([]);
}

function setupHookDefaults() {
  (useAddArtifactToGroup as jest.Mock).mockReturnValue({ mutateAsync: mockMutateAsync });
  (useRemoveArtifactFromGroup as jest.Mock).mockReturnValue({ mutateAsync: mockMutateAsync });
  (useReorderArtifactsInGroup as jest.Mock).mockReturnValue({ mutateAsync: mockMutateAsync });
  (useCreateGroup as jest.Mock).mockReturnValue({ mutateAsync: mockMutateAsync });
  (useArtifactGroups as jest.Mock).mockReturnValue({ data: [], isLoading: false });
  (useTags as jest.Mock).mockReturnValue({ data: { items: [] }, isLoading: false });
}

function setupHooks(opts: {
  groups?: typeof testGroup[];
  groupArtifactMap?: Record<string, { artifact_id: string; position: number; added_at: string }[]>;
  isLoadingGroups?: boolean;
}) {
  (useGroups as jest.Mock).mockReturnValue({
    data: opts.isLoadingGroups
      ? undefined
      : {
          groups: opts.groups ?? [],
          total: opts.groups?.length ?? 0,
        },
    isLoading: opts.isLoadingGroups ?? false,
  });

  // Legacy single-group artifact hook (still exported but not used by GroupedArtifactView)
  (useGroupArtifacts as jest.Mock).mockImplementation((groupId: string) => {
    const map = opts.groupArtifactMap ?? {};
    return {
      data: map[groupId] ?? [],
      isLoading: false,
    };
  });

  // New batch hook using useQueries pattern
  (useGroupsArtifacts as jest.Mock).mockImplementation((groupIds: string[]) => {
    const map = opts.groupArtifactMap ?? {};
    return groupIds.map((groupId) => ({
      groupId,
      query: {
        data: map[groupId] ?? [],
        isLoading: false,
      },
    }));
  });
}

describe('GroupedArtifactView', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Re-apply mock return values (resetMocks: true clears them between tests)
    setupDndMocks();
    setupHookDefaults();
  });

  afterEach(() => {
    queryClient.clear();
  });

  const renderComponent = (props: Partial<React.ComponentProps<typeof GroupedArtifactView>> = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <GroupedArtifactView
          collectionId="test-collection"
          artifacts={mockArtifacts}
          {...props}
        />
      </QueryClientProvider>
    );
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Loading
  // ─────────────────────────────────────────────────────────────────────────

  it('renders loading skeleton while groups are loading', () => {
    setupHooks({ isLoadingGroups: true });

    renderComponent();

    expect(screen.getByTestId('grouped-view-skeleton')).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // Sidebar rendering
  // ─────────────────────────────────────────────────────────────────────────

  it('renders sidebar with "All Artifacts", "Ungrouped", and group items', () => {
    setupHooks({
      groups: [testGroup, secondGroup],
      groupArtifactMap: {
        'group-1': [{ artifact_id: 'art-1', position: 0, added_at: '2024-01-01T00:00:00Z' }],
        'group-2': [{ artifact_id: 'art-2', position: 0, added_at: '2024-01-01T00:00:00Z' }],
      },
    });

    renderComponent();

    // "All Artifacts" appears in sidebar and as pane header
    expect(screen.getAllByText('All Artifacts').length).toBeGreaterThanOrEqual(1);
    // "Ungrouped" appears in sidebar
    expect(screen.getAllByText('Ungrouped').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Design Tools')).toBeInTheDocument();
    expect(screen.getByText('Dev Tools')).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // "All Artifacts" pane (default)
  // ─────────────────────────────────────────────────────────────────────────

  it('shows all artifacts by default in the "All Artifacts" pane', () => {
    setupHooks({ groups: [testGroup], groupArtifactMap: {} });

    renderComponent();

    // Header shows "All Artifacts" with count (also appears in sidebar)
    expect(screen.getAllByText('All Artifacts').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('(3 artifacts)')).toBeInTheDocument();

    // All three artifact names should be visible
    expect(screen.getByText('canvas-design')).toBeInTheDocument();
    expect(screen.getByText('code-review')).toBeInTheDocument();
    expect(screen.getByText('doc-writer')).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // Pane selection — group pane
  // ─────────────────────────────────────────────────────────────────────────

  it('clicking a group in the sidebar shows only that group\'s artifacts', () => {
    setupHooks({
      groups: [testGroup],
      groupArtifactMap: {
        'group-1': [{ artifact_id: 'art-1', position: 0, added_at: '2024-01-01T00:00:00Z' }],
      },
    });

    renderComponent();

    // Click the group in sidebar
    fireEvent.click(screen.getByText('Design Tools'));

    // Should show only art-1
    expect(screen.getByText('canvas-design')).toBeInTheDocument();
    // art-2 and art-3 should not be visible (they are not in the group)
    expect(screen.queryByText('code-review')).not.toBeInTheDocument();
    expect(screen.queryByText('doc-writer')).not.toBeInTheDocument();

    // Header should reflect group name and count
    expect(screen.getByText('(1 artifact)')).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // Pane selection — ungrouped
  // ─────────────────────────────────────────────────────────────────────────

  it('clicking "Ungrouped" shows only artifacts not in any group', () => {
    setupHooks({
      groups: [testGroup],
      groupArtifactMap: {
        'group-1': [{ artifact_id: 'art-1', position: 0, added_at: '2024-01-01T00:00:00Z' }],
      },
    });

    renderComponent();

    // Click Ungrouped
    fireEvent.click(screen.getByText('Ungrouped'));

    // art-1 is grouped, so should not appear
    expect(screen.queryByText('canvas-design')).not.toBeInTheDocument();
    // art-2 and art-3 are ungrouped
    expect(screen.getByText('code-review')).toBeInTheDocument();
    expect(screen.getByText('doc-writer')).toBeInTheDocument();
    expect(screen.getByText('(2 artifacts)')).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // Empty states
  // ─────────────────────────────────────────────────────────────────────────

  it('shows "No artifacts in this collection" when "All Artifacts" pane is empty', () => {
    setupHooks({ groups: [] });

    renderComponent({ artifacts: [] });

    expect(screen.getByText('No artifacts in your collection yet')).toBeInTheDocument();
  });

  it('shows "All artifacts are assigned to groups" when ungrouped pane is empty', () => {
    // All artifacts are in the group
    setupHooks({
      groups: [testGroup],
      groupArtifactMap: {
        'group-1': [
          { artifact_id: 'art-1', position: 0, added_at: '2024-01-01T00:00:00Z' },
          { artifact_id: 'art-2', position: 1, added_at: '2024-01-01T00:00:00Z' },
          { artifact_id: 'art-3', position: 2, added_at: '2024-01-01T00:00:00Z' },
        ],
      },
    });

    renderComponent();

    // Click Ungrouped
    fireEvent.click(screen.getByText('Ungrouped'));

    expect(screen.getByText('All artifacts are organized into groups')).toBeInTheDocument();
  });

  it('shows drag hint when a group pane has no artifacts', () => {
    setupHooks({
      groups: [testGroup],
      groupArtifactMap: {
        'group-1': [],
      },
    });

    renderComponent();

    // Select the empty group
    fireEvent.click(screen.getByText('Design Tools'));

    expect(
      screen.getByText('No artifacts in this group yet. Drag artifacts here to add them.')
    ).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // Create Group button
  // ─────────────────────────────────────────────────────────────────────────

  it('"Create Group" button opens the GroupFormDialog', () => {
    setupHooks({ groups: [] });

    renderComponent();

    // Dialog should not be visible yet
    expect(screen.queryByTestId('create-group-dialog')).not.toBeInTheDocument();

    const createBtn = screen.getByRole('button', { name: /create group/i });
    fireEvent.click(createBtn);

    // Dialog should now be open
    expect(screen.getByTestId('create-group-dialog')).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // Artifact click handler
  // ─────────────────────────────────────────────────────────────────────────

  it('calls onArtifactClick when an artifact card is clicked', () => {
    const onArtifactClick = jest.fn();
    setupHooks({ groups: [], groupArtifactMap: {} });

    renderComponent({ onArtifactClick });

    // Find by accessible role (MiniArtifactCard uses role="button")
    const card = screen.getByRole('button', {
      name: /canvas-design/i,
    });
    fireEvent.click(card);

    expect(onArtifactClick).toHaveBeenCalledWith(art1);
  });

  // ─────────────────────────────────────────────────────────────────────────
  // Sidebar shows "No groups yet" when list is empty
  // ─────────────────────────────────────────────────────────────────────────

  it('shows "No groups yet" in sidebar when no groups exist', () => {
    setupHooks({ groups: [] });

    renderComponent();

    expect(screen.getByText('No groups yet')).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // Remove-from-group zone visibility
  // ─────────────────────────────────────────────────────────────────────────

  it('hides remove-from-group zone when not dragging, even on a specific group', () => {
    setupHooks({
      groups: [testGroup],
      groupArtifactMap: {
        'group-1': [{ artifact_id: 'art-1', position: 0, added_at: '2024-01-01T00:00:00Z' }],
      },
    });

    renderComponent();

    // On "All Artifacts" pane, no remove zone
    expect(screen.queryByText(/Remove from/i)).not.toBeInTheDocument();

    // Switch to group pane -- still hidden because activeId is null (no drag in progress)
    fireEvent.click(screen.getByText('Design Tools'));

    expect(screen.queryByText(/Remove from/i)).not.toBeInTheDocument();
  });
});
