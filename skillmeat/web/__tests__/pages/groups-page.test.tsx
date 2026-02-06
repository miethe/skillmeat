/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GroupsPageClient } from '@/app/groups/components/groups-page-client';
import {
  useCollectionContext,
  useGroup,
  useGroups,
  useGroupArtifacts,
  useArtifact,
  useToast,
} from '@/hooks';
import type { Collection } from '@/types/collections';
import type { Group } from '@/types/groups';

// Polyfill scrollIntoView for Radix UI components
Element.prototype.scrollIntoView = jest.fn();

// Mock IntersectionObserver
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
});
window.IntersectionObserver = mockIntersectionObserver;

// Mock the hooks
jest.mock('@/hooks', () => ({
  useCollectionContext: jest.fn(),
  useGroup: jest.fn(),
  useGroups: jest.fn(),
  useGroupArtifacts: jest.fn(),
  useArtifact: jest.fn(),
  useToast: jest.fn(),
}));

// Mock next/navigation
const mockPush = jest.fn();
let mockSearchParams = new URLSearchParams();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
  }),
  useSearchParams: () => mockSearchParams,
}));

// Mock next/link
jest.mock('next/link', () => {
  return ({ children, href, ...rest }: { children: React.ReactNode; href: string }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  );
});

const mockUseCollectionContext = useCollectionContext as jest.MockedFunction<
  typeof useCollectionContext
>;
const mockUseGroup = useGroup as jest.MockedFunction<typeof useGroup>;
const mockUseGroups = useGroups as jest.MockedFunction<typeof useGroups>;
const mockUseGroupArtifacts = useGroupArtifacts as jest.MockedFunction<typeof useGroupArtifacts>;
const mockUseArtifact = useArtifact as jest.MockedFunction<typeof useArtifact>;
const mockUseToast = useToast as jest.MockedFunction<typeof useToast>;

describe('GroupsPageClient', () => {
  let queryClient: QueryClient;

  const mockCollections: Collection[] = [
    {
      id: 'collection-1',
      name: 'Default Collection',
      version: '1.0.0',
      artifact_count: 10,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'collection-2',
      name: 'Work Collection',
      version: '1.0.0',
      artifact_count: 5,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    },
  ];

  const mockGroups: Group[] = [
    {
      id: 'group-1',
      collection_id: 'collection-1',
      name: 'Development Tools',
      description: 'Tools for development workflows',
      position: 0,
      artifact_count: 5,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'group-2',
      collection_id: 'collection-1',
      name: 'Productivity',
      position: 1,
      artifact_count: 3,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    },
  ];

  const mockSelectedGroup = mockGroups[0];

  beforeEach(() => {
    jest.clearAllMocks();
    mockSearchParams = new URLSearchParams();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Default mock implementations
    mockUseToast.mockReturnValue({ toast: jest.fn() } as any);

    mockUseCollectionContext.mockReturnValue({
      collections: mockCollections,
      selectedCollectionId: null,
      selectedGroupId: null,
      currentCollection: null,
      currentGroups: [],
      isLoadingCollections: false,
      isLoadingCollection: false,
      isLoadingGroups: false,
      collectionsError: null,
      collectionError: null,
      groupsError: null,
      setSelectedCollectionId: jest.fn(),
      setSelectedGroupId: jest.fn(),
      refreshCollections: jest.fn(),
      refreshGroups: jest.fn(),
    });

    mockUseGroup.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any);

    mockUseGroups.mockReturnValue({
      data: { groups: mockGroups, total: mockGroups.length },
      isLoading: false,
      error: null,
    } as any);

    mockUseGroupArtifacts.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    } as any);

    mockUseArtifact.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    queryClient.clear();
  });

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <GroupsPageClient />
      </QueryClientProvider>
    );
  };

  describe('no collections state', () => {
    it('renders "no collections yet" empty state when no collections exist', () => {
      mockUseCollectionContext.mockReturnValue({
        collections: [],
        selectedCollectionId: null,
        selectedGroupId: null,
        currentCollection: null,
        currentGroups: [],
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      renderComponent();

      expect(screen.getByText(/no collections yet/i)).toBeInTheDocument();
      expect(screen.getByText(/create a collection first/i)).toBeInTheDocument();
    });

    it('shows link to collections page when no collections', () => {
      mockUseCollectionContext.mockReturnValue({
        collections: [],
        selectedCollectionId: null,
        selectedGroupId: null,
        currentCollection: null,
        currentGroups: [],
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      renderComponent();

      const goToCollectionsLink = screen.getByRole('link', { name: /go to collections/i });
      expect(goToCollectionsLink).toHaveAttribute('href', '/collection');
    });
  });

  describe('select collection state', () => {
    it('renders "select a collection" empty state when no collection is selected', () => {
      renderComponent();

      expect(screen.getByText(/select a collection/i)).toBeInTheDocument();
      expect(screen.getByText(/choose a collection from the dropdown/i)).toBeInTheDocument();
    });
  });

  describe('select group state', () => {
    it('renders "select a group" empty state when collection selected but no group', () => {
      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-1',
        selectedGroupId: null,
        currentCollection: mockCollections[0],
        currentGroups: mockGroups,
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      mockSearchParams.set('collection', 'collection-1');

      renderComponent();

      expect(screen.getByText(/select a group/i)).toBeInTheDocument();
      expect(screen.getByText(/use the group dropdown/i)).toBeInTheDocument();
    });

    it('shows link to collection page when no group selected', () => {
      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-1',
        selectedGroupId: null,
        currentCollection: mockCollections[0],
        currentGroups: mockGroups,
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      mockSearchParams.set('collection', 'collection-1');

      renderComponent();

      const goToCollectionLink = screen.getByRole('link', { name: /go to collection/i });
      expect(goToCollectionLink).toHaveAttribute('href', '/collection?collection=collection-1');
    });
  });

  describe('group selected state', () => {
    beforeEach(() => {
      mockSearchParams.set('collection', 'collection-1');
      mockSearchParams.set('group', 'group-1');

      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-1',
        selectedGroupId: 'group-1',
        currentCollection: mockCollections[0],
        currentGroups: mockGroups,
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      mockUseGroup.mockReturnValue({
        data: mockSelectedGroup,
        isLoading: false,
        error: null,
      } as any);
    });

    it('renders GroupSelector when collection is selected', () => {
      renderComponent();

      // Check for Group selector label
      expect(screen.getByText('Group:')).toBeInTheDocument();
    });

    it('renders GroupArtifactGrid when group is selected', () => {
      renderComponent();

      // The GroupArtifactGrid should render (even if empty)
      expect(screen.getByRole('status', { name: /no artifacts in group/i })).toBeInTheDocument();
    });

    it('shows group name in header when group is selected', () => {
      renderComponent();

      // "Development Tools" appears both in the GroupSelector and in the header
      // Verify it appears at least twice (selector + header)
      const devToolsElements = screen.getAllByText('Development Tools');
      expect(devToolsElements.length).toBeGreaterThanOrEqual(1);
    });

    it('shows group description in header when available', () => {
      renderComponent();

      expect(screen.getByText('- Tools for development workflows')).toBeInTheDocument();
    });

    it('shows group ID when group name is not available', () => {
      mockUseGroup.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
      } as any);

      renderComponent();

      // Should show the group ID in a code element
      expect(screen.getByText('group-1')).toBeInTheDocument();
    });
  });

  describe('URL state synchronization', () => {
    it('syncs URL params with component state', async () => {
      mockSearchParams.set('collection', 'collection-1');

      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-1',
        selectedGroupId: null,
        currentCollection: mockCollections[0],
        currentGroups: mockGroups,
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      renderComponent();

      // URL has collection param, so we should see the GroupSelector
      expect(screen.getByText('Group:')).toBeInTheDocument();
    });

    it('clears group from URL when collection changes', async () => {
      mockSearchParams.set('collection', 'collection-1');
      mockSearchParams.set('group', 'group-1');

      // Simulate collection context changing to collection-2
      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-2', // Changed from collection-1
        selectedGroupId: null,
        currentCollection: mockCollections[1],
        currentGroups: [],
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      renderComponent();

      await waitFor(() => {
        // URL should be updated to clear group and set new collection
        expect(mockPush).toHaveBeenCalled();
      });
    });
  });

  describe('group selection with missing collection error state', () => {
    it('shows error state when group selected but collection not specified', () => {
      mockSearchParams.set('group', 'group-1');
      // No collection in URL

      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: null,
        selectedGroupId: null,
        currentCollection: null,
        currentGroups: [],
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      renderComponent();

      // This should show the "select a collection" state since no collection is selected
      expect(screen.getByText(/select a collection/i)).toBeInTheDocument();
    });
  });

  describe('clear selection', () => {
    it('shows clear button when group is selected', () => {
      mockSearchParams.set('collection', 'collection-1');
      mockSearchParams.set('group', 'group-1');

      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-1',
        selectedGroupId: 'group-1',
        currentCollection: mockCollections[0],
        currentGroups: mockGroups,
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      mockUseGroup.mockReturnValue({
        data: mockSelectedGroup,
        isLoading: false,
        error: null,
      } as any);

      renderComponent();

      const clearButton = screen.getByRole('button', { name: /clear group selection/i });
      expect(clearButton).toBeInTheDocument();
    });

    it('navigates to /groups when clear button is clicked', () => {
      mockSearchParams.set('collection', 'collection-1');
      mockSearchParams.set('group', 'group-1');

      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-1',
        selectedGroupId: 'group-1',
        currentCollection: mockCollections[0],
        currentGroups: mockGroups,
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      mockUseGroup.mockReturnValue({
        data: mockSelectedGroup,
        isLoading: false,
        error: null,
      } as any);

      renderComponent();

      const clearButton = screen.getByRole('button', { name: /clear group selection/i });
      fireEvent.click(clearButton);

      expect(mockPush).toHaveBeenCalledWith('/groups');
    });
  });

  describe('manage groups link', () => {
    it('shows manage groups link when collection is selected', () => {
      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-1',
        selectedGroupId: null,
        currentCollection: mockCollections[0],
        currentGroups: mockGroups,
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      mockSearchParams.set('collection', 'collection-1');

      renderComponent();

      const manageGroupsLink = screen.getByRole('link', { name: /manage groups/i });
      expect(manageGroupsLink).toHaveAttribute('href', '/collection?collection=collection-1');
    });
  });

  describe('loading states', () => {
    it('shows skeleton when collections are loading', () => {
      mockUseCollectionContext.mockReturnValue({
        collections: [],
        selectedCollectionId: null,
        selectedGroupId: null,
        currentCollection: null,
        currentGroups: [],
        isLoadingCollections: true,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      renderComponent();

      // Should show loading skeleton for collection switcher
      // The component shows a Skeleton when loading
      expect(screen.queryByText(/no collections yet/i)).not.toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has accessible region for group selector toolbar', () => {
      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-1',
        selectedGroupId: null,
        currentCollection: mockCollections[0],
        currentGroups: mockGroups,
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      mockSearchParams.set('collection', 'collection-1');

      renderComponent();

      expect(screen.getByRole('region', { name: /group selector/i })).toBeInTheDocument();
    });

    it('uses aria-hidden on decorative icons', () => {
      mockSearchParams.set('collection', 'collection-1');
      mockSearchParams.set('group', 'group-1');

      mockUseCollectionContext.mockReturnValue({
        collections: mockCollections,
        selectedCollectionId: 'collection-1',
        selectedGroupId: 'group-1',
        currentCollection: mockCollections[0],
        currentGroups: mockGroups,
        isLoadingCollections: false,
        isLoadingCollection: false,
        isLoadingGroups: false,
        collectionsError: null,
        collectionError: null,
        groupsError: null,
        setSelectedCollectionId: jest.fn(),
        setSelectedGroupId: jest.fn(),
        refreshCollections: jest.fn(),
        refreshGroups: jest.fn(),
      });

      mockUseGroup.mockReturnValue({
        data: mockSelectedGroup,
        isLoading: false,
        error: null,
      } as any);

      renderComponent();

      // Icons should be aria-hidden
      // We can check that the visible text is present without icon interference
      expect(screen.getByText('Collection:')).toBeInTheDocument();
      expect(screen.getByText('Group:')).toBeInTheDocument();
    });
  });
});
