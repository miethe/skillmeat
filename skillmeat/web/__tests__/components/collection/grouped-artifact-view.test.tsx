/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GroupedArtifactView } from '@/components/collection/grouped-artifact-view';
import type { Artifact } from '@/types/artifact';

// Mock the hooks
jest.mock('@/hooks/use-groups', () => ({
  useGroups: jest.fn(),
  useGroupArtifacts: jest.fn(),
  useReorderGroups: jest.fn(),
  useReorderArtifactsInGroup: jest.fn(),
}));

const mockArtifacts: Artifact[] = [
  {
    id: 'art-1',
    name: 'test-skill',
    type: 'skill',
    scope: 'user',
    status: 'active',
    version: '1.0.0',
    metadata: {
      title: 'Test Skill',
      description: 'A test skill',
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
  },
];

describe('GroupedArtifactView', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  afterEach(() => {
    queryClient.clear();
    jest.clearAllMocks();
  });

  const renderComponent = (props: any = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <GroupedArtifactView collectionId="test-collection" artifacts={mockArtifacts} {...props} />
      </QueryClientProvider>
    );
  };

  it('renders loading state initially', () => {
    const { useGroups } = require('@/hooks/use-groups');
    useGroups.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    renderComponent();

    expect(screen.getByTestId('grouped-view-skeleton')).toBeInTheDocument();
  });

  it('renders empty state when no groups', async () => {
    const { useGroups } = require('@/hooks/use-groups');
    useGroups.mockReturnValue({
      data: { groups: [], total: 0 },
      isLoading: false,
    });

    renderComponent({ artifacts: [] });

    await waitFor(() => {
      expect(screen.getByText(/no groups or artifacts/i)).toBeInTheDocument();
    });
  });

  it('renders groups with artifacts', async () => {
    const { useGroups, useGroupArtifacts } = require('@/hooks/use-groups');

    useGroups.mockReturnValue({
      data: {
        groups: [
          {
            id: 'group-1',
            collection_id: 'test-collection',
            name: 'Test Group',
            description: 'A test group',
            position: 0,
            artifact_count: 1,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      },
      isLoading: false,
    });

    useGroupArtifacts.mockReturnValue({
      data: [
        {
          artifact_id: 'art-1',
          position: 0,
          added_at: '2024-01-01T00:00:00Z',
        },
      ],
      isLoading: false,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Group')).toBeInTheDocument();
      expect(screen.getByText(/1 artifact/i)).toBeInTheDocument();
    });
  });

  it('renders ungrouped artifacts', async () => {
    const { useGroups, useGroupArtifacts } = require('@/hooks/use-groups');

    useGroups.mockReturnValue({
      data: { groups: [], total: 0 },
      isLoading: false,
    });

    useGroupArtifacts.mockReturnValue({
      data: [],
      isLoading: false,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Ungrouped')).toBeInTheDocument();
      expect(screen.getByText(/1 artifact/i)).toBeInTheDocument();
    });
  });

  it('calls onArtifactClick when artifact is clicked', async () => {
    const { useGroups, useGroupArtifacts } = require('@/hooks/use-groups');
    const onArtifactClick = jest.fn();

    useGroups.mockReturnValue({
      data: { groups: [], total: 0 },
      isLoading: false,
    });

    useGroupArtifacts.mockReturnValue({
      data: [],
      isLoading: false,
    });

    renderComponent({ onArtifactClick });

    await waitFor(() => {
      expect(screen.getByText('Ungrouped')).toBeInTheDocument();
    });

    // Click on the artifact card
    const artifactCard = screen.getByText('Test Skill').closest('div[role="button"]');
    if (artifactCard) {
      artifactCard.click();
      expect(onArtifactClick).toHaveBeenCalledWith(mockArtifacts[0]);
    }
  });

  it('handles group reordering', async () => {
    const { useGroups, useGroupArtifacts, useReorderGroups } = require('@/hooks/use-groups');
    const mutateAsync = jest.fn();

    useGroups.mockReturnValue({
      data: {
        groups: [
          {
            id: 'group-1',
            collection_id: 'test-collection',
            name: 'Group 1',
            position: 0,
            artifact_count: 0,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
          {
            id: 'group-2',
            collection_id: 'test-collection',
            name: 'Group 2',
            position: 1,
            artifact_count: 0,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 2,
      },
      isLoading: false,
    });

    useGroupArtifacts.mockReturnValue({
      data: [],
      isLoading: false,
    });

    useReorderGroups.mockReturnValue({
      mutateAsync,
    });

    renderComponent({ artifacts: [] });

    await waitFor(() => {
      expect(screen.getByText('Group 1')).toBeInTheDocument();
      expect(screen.getByText('Group 2')).toBeInTheDocument();
    });

    // Note: Drag-and-drop testing requires more complex setup with DndContext
    // This is a placeholder for future implementation
  });
});
