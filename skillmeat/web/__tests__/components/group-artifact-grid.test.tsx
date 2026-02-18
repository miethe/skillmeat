/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GroupArtifactGrid } from '@/app/groups/components/group-artifact-grid';
import { useGroupArtifacts, useArtifact, useToast } from '@/hooks';
import type { GroupArtifact } from '@/types/groups';
import type { Artifact } from '@/types/artifact';

// Polyfill scrollIntoView for Radix UI components
Element.prototype.scrollIntoView = jest.fn();

// Mock IntersectionObserver
const mockObserve = jest.fn();
const mockUnobserve = jest.fn();
const mockDisconnect = jest.fn();

class MockIntersectionObserver {
  callback: IntersectionObserverCallback;

  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback;
  }

  observe = mockObserve;
  unobserve = mockUnobserve;
  disconnect = mockDisconnect;
}

window.IntersectionObserver = MockIntersectionObserver as any;

// Mock the hooks
const mockUseGroupArtifactsFn = jest.fn();
const mockUseArtifactFn = jest.fn();
const mockUseToastFn = jest.fn();

jest.mock('@/hooks', () => ({
  useGroupArtifacts: (...args: any[]) => mockUseGroupArtifactsFn(...args),
  useArtifact: (...args: any[]) => mockUseArtifactFn(...args),
  useToast: () => mockUseToastFn(),
  useCollectionContext: () => ({
    collections: [],
    selectedCollectionId: 'collection-1',
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
  }),
  useAddArtifactToCollection: () => ({
    mutate: jest.fn(),
    isPending: false,
  }),
  useRemoveArtifactFromCollection: () => ({
    mutate: jest.fn(),
    isPending: false,
  }),
  useDndAnimations: () => ({
    animState: { phase: 'idle', targetGroupId: null, sourceGroupId: null, targetRect: null },
    triggerDropIntoGroup: jest.fn(),
    triggerRemovePoof: jest.fn(),
    reset: jest.fn(),
  }),
  useCliCopy: () => ({
    copy: jest.fn(),
    isCopying: false,
  }),
}));

// Use the function references directly for configuration
const mockUseGroupArtifacts = mockUseGroupArtifactsFn;
const mockUseArtifact = mockUseArtifactFn;
const mockUseToast = mockUseToastFn;

describe('GroupArtifactGrid', () => {
  let queryClient: QueryClient;

  const mockGroupArtifacts: GroupArtifact[] = [
    { artifact_id: 'art-1', position: 0, added_at: '2024-01-01T00:00:00Z' },
    { artifact_id: 'art-2', position: 1, added_at: '2024-01-02T00:00:00Z' },
    { artifact_id: 'art-3', position: 2, added_at: '2024-01-03T00:00:00Z' },
  ];

  const mockArtifacts: Record<string, Artifact> = {
    'art-1': {
      id: 'art-1',
      name: 'Test Skill 1',
      type: 'skill',
      scope: 'user',
      syncStatus: 'synced',
      version: '1.0.0',
      description: 'A test skill',
      tags: ['test'],
      upstream: {
        enabled: false,
        updateAvailable: false,
      },
      usageStats: {
        totalDeployments: 0,
        activeProjects: 0,
        usageCount: 0,
      },
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    },
    'art-2': {
      id: 'art-2',
      name: 'Test Command',
      type: 'command',
      scope: 'user',
      syncStatus: 'synced',
      version: '2.0.0',
      description: 'A test command',
      tags: ['test', 'command'],
      upstream: {
        enabled: true,
        updateAvailable: false,
      },
      usageStats: {
        totalDeployments: 5,
        activeProjects: 2,
        usageCount: 10,
      },
      createdAt: '2024-01-02T00:00:00Z',
      updatedAt: '2024-01-02T00:00:00Z',
    },
    'art-3': {
      id: 'art-3',
      name: 'Test Agent',
      type: 'agent',
      scope: 'local',
      syncStatus: 'outdated',
      version: '0.5.0',
      description: 'A test agent',
      tags: ['agent'],
      upstream: {
        enabled: true,
        updateAvailable: true,
      },
      usageStats: {
        totalDeployments: 2,
        activeProjects: 1,
        usageCount: 3,
      },
      createdAt: '2024-01-03T00:00:00Z',
      updatedAt: '2024-01-03T00:00:00Z',
    },
  };

  const mockToast = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    mockUseToast.mockReturnValue({ toast: mockToast } as any);

    // Default mock for useArtifact - returns artifact based on ID
    mockUseArtifact.mockImplementation(
      (artifactId: string) =>
        ({
          data: mockArtifacts[artifactId],
          isLoading: false,
          error: null,
          isError: false,
          isSuccess: true,
        }) as any
    );

    // Clear localStorage
    localStorage.clear();
  });

  afterEach(() => {
    queryClient.clear();
    localStorage.clear();
  });

  const renderComponent = (props = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <GroupArtifactGrid groupId="group-1" collectionId="collection-1" {...props} />
      </QueryClientProvider>
    );
  };

  describe('loading state', () => {
    it('renders loading skeleton initially', () => {
      mockUseGroupArtifacts.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      renderComponent();

      expect(screen.getByTestId('group-artifact-grid-skeleton')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('renders error state on fetch failure', () => {
      mockUseGroupArtifacts.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
        isError: true,
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      renderComponent();

      expect(screen.getByText(/failed to load artifacts/i)).toBeInTheDocument();
      expect(screen.getByText('Failed to fetch')).toBeInTheDocument();
    });

    it('shows retry button on error state', () => {
      const mockRefetch = jest.fn();
      mockUseGroupArtifacts.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('API Error'),
        isError: true,
        isSuccess: false,
        refetch: mockRefetch,
      } as any);

      renderComponent();

      const retryButton = screen.getByRole('button', { name: /try again/i });
      expect(retryButton).toBeInTheDocument();

      fireEvent.click(retryButton);
      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe('empty state', () => {
    it('renders empty state when no artifacts in group', () => {
      mockUseGroupArtifacts.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      renderComponent();

      expect(screen.getByRole('status', { name: /no artifacts in group/i })).toBeInTheDocument();
      expect(screen.getByText(/no artifacts in this group/i)).toBeInTheDocument();
    });

    it('shows link to add artifacts in empty state', () => {
      mockUseGroupArtifacts.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      renderComponent({ collectionId: 'test-collection' });

      const addLink = screen.getByRole('link', { name: /add artifacts/i });
      expect(addLink).toHaveAttribute('href', '/collection?collection=test-collection');
    });
  });

  describe('success state', () => {
    beforeEach(() => {
      mockUseGroupArtifacts.mockReturnValue({
        data: mockGroupArtifacts,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);
    });

    it('renders artifacts in grid view by default', () => {
      renderComponent();

      const grid = screen.getByRole('grid', { name: /group artifacts/i });
      expect(grid).toBeInTheDocument();
      expect(grid).toHaveClass('grid');
    });

    it('displays artifact count in header', () => {
      renderComponent();

      expect(screen.getByText('3 artifacts')).toBeInTheDocument();
    });

    it('displays singular "artifact" for single item', () => {
      mockUseGroupArtifacts.mockReturnValue({
        data: [mockGroupArtifacts[0]],
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      renderComponent();

      expect(screen.getByText('1 artifact')).toBeInTheDocument();
    });
  });

  describe('view mode toggle', () => {
    beforeEach(() => {
      mockUseGroupArtifacts.mockReturnValue({
        data: mockGroupArtifacts,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);
    });

    it('toggles to list view when list button is clicked', async () => {
      renderComponent();

      const listViewButton = screen.getByRole('button', { name: /list view/i });
      fireEvent.click(listViewButton);

      await waitFor(() => {
        const grid = screen.getByRole('grid');
        expect(grid).toHaveClass('flex', 'flex-col');
      });
    });

    it('persists view mode to localStorage', async () => {
      renderComponent();

      const listViewButton = screen.getByRole('button', { name: /list view/i });
      fireEvent.click(listViewButton);

      await waitFor(() => {
        expect(localStorage.getItem('groups-artifact-view-mode')).toBe('list');
      });
    });

    it('restores view mode from localStorage on mount', async () => {
      localStorage.setItem('groups-artifact-view-mode', 'list');

      renderComponent();

      await waitFor(() => {
        const listViewButton = screen.getByRole('button', { name: /list view/i });
        expect(listViewButton).toHaveAttribute('aria-pressed', 'true');
      });
    });

    it('has correct aria-pressed state on view buttons', () => {
      renderComponent();

      const gridViewButton = screen.getByRole('button', { name: /grid view/i });
      const listViewButton = screen.getByRole('button', { name: /list view/i });

      expect(gridViewButton).toHaveAttribute('aria-pressed', 'true');
      expect(listViewButton).toHaveAttribute('aria-pressed', 'false');
    });
  });

  describe('sorting', () => {
    beforeEach(() => {
      mockUseGroupArtifacts.mockReturnValue({
        data: mockGroupArtifacts,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);
    });

    it('sorts artifacts by position by default', () => {
      renderComponent();

      // The sort selector should show "Position"
      expect(screen.getByRole('combobox', { name: /sort by/i })).toBeInTheDocument();
    });

    it('supports sorting by name', async () => {
      renderComponent();

      const sortSelect = screen.getByRole('combobox', { name: /sort by/i });
      fireEvent.click(sortSelect);

      await waitFor(() => {
        const nameOption = screen.getByRole('option', { name: /name/i });
        fireEvent.click(nameOption);
      });
    });

    it('supports sorting by date added', async () => {
      renderComponent();

      const sortSelect = screen.getByRole('combobox', { name: /sort by/i });
      fireEvent.click(sortSelect);

      await waitFor(() => {
        const dateOption = screen.getByRole('option', { name: /date added/i });
        fireEvent.click(dateOption);
      });
    });

    it('supports sorting by type', async () => {
      renderComponent();

      const sortSelect = screen.getByRole('combobox', { name: /sort by/i });
      fireEvent.click(sortSelect);

      await waitFor(() => {
        const typeOption = screen.getByRole('option', { name: /type/i });
        fireEvent.click(typeOption);
      });
    });

    it('toggles sort order when clicking order button', async () => {
      renderComponent();

      // Initially ascending, button label says what clicking will do (sort descending)
      const orderButton = screen.getByRole('button', { name: /sort descending/i });
      expect(orderButton).toHaveTextContent('Asc');

      fireEvent.click(orderButton);

      await waitFor(() => {
        // Now descending, button says clicking will sort ascending
        expect(screen.getByRole('button', { name: /sort ascending/i })).toHaveTextContent('Desc');
      });
    });
  });

  describe('pagination', () => {
    it('shows "All X artifacts loaded" when all items are displayed', () => {
      mockUseGroupArtifacts.mockReturnValue({
        data: mockGroupArtifacts,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      renderComponent();

      expect(screen.getByText(/all 3 artifacts loaded/i)).toBeInTheDocument();
    });

    it('sets up IntersectionObserver for infinite scroll', () => {
      mockUseGroupArtifacts.mockReturnValue({
        data: mockGroupArtifacts,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      renderComponent();

      // IntersectionObserver observe should be called
      expect(mockObserve).toHaveBeenCalled();
    });
  });

  describe('artifact error handling', () => {
    it('shows error card when individual artifact fails to load', () => {
      mockUseGroupArtifacts.mockReturnValue({
        data: mockGroupArtifacts,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      // Make one artifact fail to load
      mockUseArtifact.mockImplementation((artifactId: string) => {
        if (artifactId === 'art-2') {
          return {
            data: undefined,
            isLoading: false,
            error: new Error('Not found'),
            isError: true,
            isSuccess: false,
          } as any;
        }
        return {
          data: mockArtifacts[artifactId],
          isLoading: false,
          error: null,
          isError: false,
          isSuccess: true,
        } as any;
      });

      renderComponent();

      expect(screen.getByText(/failed to load artifact/i)).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    beforeEach(() => {
      mockUseGroupArtifacts.mockReturnValue({
        data: mockGroupArtifacts,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);
    });

    it('has accessible label on grid container', () => {
      renderComponent();

      expect(screen.getByRole('grid', { name: /group artifacts/i })).toBeInTheDocument();
    });

    it('has accessible labels on view toggle buttons', () => {
      renderComponent();

      expect(screen.getByRole('button', { name: /grid view/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /list view/i })).toBeInTheDocument();
    });

    it('has accessible label on sort selector', () => {
      renderComponent();

      expect(screen.getByRole('combobox', { name: /sort by/i })).toBeInTheDocument();
    });

    it('has accessible label on sort order button', () => {
      renderComponent();

      // Default sort order is ascending, so button shows what it will do (switch to descending)
      expect(screen.getByRole('button', { name: /sort descending/i })).toBeInTheDocument();
    });
  });

  describe('className prop', () => {
    it('applies custom className to container', () => {
      mockUseGroupArtifacts.mockReturnValue({
        data: mockGroupArtifacts,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      const { container } = renderComponent({ className: 'custom-class' });

      // The outer container should have the custom class
      expect(container.firstChild).toHaveClass('custom-class');
    });
  });
});
