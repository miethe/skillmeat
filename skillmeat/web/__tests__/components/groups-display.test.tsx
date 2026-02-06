/**
 * Tests for GroupsDisplay component
 *
 * Tests the component that fetches and displays an artifact's group membership
 * within a collection. Covers loading, empty, error, and success states.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ============================================================================
// Mock Setup
// ============================================================================

// Mock the specific hook file to avoid circular dependency issues with the barrel export
const mockUseArtifactGroups = jest.fn();

jest.mock('@/hooks/use-artifact-groups', () => ({
  useArtifactGroups: (...args: unknown[]) => mockUseArtifactGroups(...args),
  artifactGroupKeys: {
    all: ['artifact-groups'],
    lists: () => ['artifact-groups', 'list'],
    list: (artifactId?: string, collectionId?: string) => [
      'artifact-groups',
      'list',
      { artifactId, collectionId },
    ],
  },
}));

// Import component after mock is set up
import { GroupsDisplay } from '@/components/entity/groups-display';

// ============================================================================
// Test Utilities
// ============================================================================

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

// ============================================================================
// Test Data
// ============================================================================

const mockGroups = [
  { id: '1', name: 'Priority Tasks', position: 0, collection_id: 'c1' },
  { id: '2', name: 'Review Queue', position: 1, collection_id: 'c1' },
  { id: '3', name: 'Archive', position: 2, collection_id: 'c1' },
];

const singleGroup = [{ id: '1', name: 'Priority Tasks', position: 0, collection_id: 'c1' }];

// ============================================================================
// Tests
// ============================================================================

describe('GroupsDisplay', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ============================================================================
  // Loading State Tests
  // ============================================================================

  describe('Loading State', () => {
    it('shows skeleton during loading', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isPending: true,
        isSuccess: false,
        status: 'pending',
      } as any);

      const { container } = renderWithProviders(
        <GroupsDisplay collectionId="c1" artifactId="a1" />
      );

      // Check for skeleton elements (uses animate-pulse class from shadcn Skeleton)
      const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('applies className to skeleton wrapper', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isPending: true,
        isSuccess: false,
        status: 'pending',
      } as any);

      const { container } = renderWithProviders(
        <GroupsDisplay collectionId="c1" artifactId="a1" className="custom-class" />
      );

      // The wrapper div should have the custom class
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass('custom-class');
    });
  });

  // ============================================================================
  // Empty State Tests
  // ============================================================================

  describe('Empty State', () => {
    it('shows "No groups" message when groups is empty array', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      renderWithProviders(<GroupsDisplay collectionId="c1" artifactId="a1" />);

      expect(screen.getByText('No groups')).toBeInTheDocument();
    });

    it('shows "No groups" message when groups is undefined', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      renderWithProviders(<GroupsDisplay collectionId="c1" artifactId="a1" />);

      expect(screen.getByText('No groups')).toBeInTheDocument();
    });

    it('applies className to empty state', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      renderWithProviders(
        <GroupsDisplay collectionId="c1" artifactId="a1" className="custom-class" />
      );

      const emptyMessage = screen.getByText('No groups');
      expect(emptyMessage).toHaveClass('custom-class');
    });
  });

  // ============================================================================
  // Error State Tests
  // ============================================================================

  describe('Error State', () => {
    it('returns null on error', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch groups'),
        isError: true,
        isPending: false,
        isSuccess: false,
        status: 'error',
      } as any);

      const { container } = renderWithProviders(
        <GroupsDisplay collectionId="c1" artifactId="a1" />
      );

      expect(container.firstChild).toBeNull();
    });

    it('gracefully handles network errors', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Network error'),
        isError: true,
        isPending: false,
        isSuccess: false,
        status: 'error',
      } as any);

      const { container } = renderWithProviders(
        <GroupsDisplay collectionId="c1" artifactId="a1" />
      );

      // Should not crash, just return null
      expect(container.firstChild).toBeNull();
    });
  });

  // ============================================================================
  // Success State Tests
  // ============================================================================

  describe('Success State', () => {
    it('renders GroupBadgeRow with fetched groups', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: mockGroups,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      renderWithProviders(<GroupsDisplay collectionId="c1" artifactId="a1" />);

      // First two groups should be visible (default maxBadges=3 for GroupsDisplay)
      expect(screen.getByText('Priority Tasks')).toBeInTheDocument();
      expect(screen.getByText('Review Queue')).toBeInTheDocument();
      expect(screen.getByText('Archive')).toBeInTheDocument();
    });

    it('renders single group correctly', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: singleGroup,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      renderWithProviders(<GroupsDisplay collectionId="c1" artifactId="a1" />);

      expect(screen.getByText('Priority Tasks')).toBeInTheDocument();
      // No overflow badge
      expect(screen.queryByText(/more\.\.\./)).not.toBeInTheDocument();
    });

    it('passes maxBadges prop to GroupBadgeRow', () => {
      const manyGroups = [
        { id: '1', name: 'One', position: 0, collection_id: 'c1' },
        { id: '2', name: 'Two', position: 1, collection_id: 'c1' },
        { id: '3', name: 'Three', position: 2, collection_id: 'c1' },
        { id: '4', name: 'Four', position: 3, collection_id: 'c1' },
        { id: '5', name: 'Five', position: 4, collection_id: 'c1' },
      ];

      mockUseArtifactGroups.mockReturnValue({
        data: manyGroups,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      renderWithProviders(<GroupsDisplay collectionId="c1" artifactId="a1" maxBadges={2} />);

      // Only 2 visible with custom maxBadges
      expect(screen.getByText('One')).toBeInTheDocument();
      expect(screen.getByText('Two')).toBeInTheDocument();
      // 3 hidden
      expect(screen.getByText('+3 more...')).toBeInTheDocument();
    });

    it('applies className to GroupBadgeRow', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: singleGroup,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      renderWithProviders(
        <GroupsDisplay collectionId="c1" artifactId="a1" className="custom-class" />
      );

      // GroupBadgeRow container should have the custom class
      const container = screen.getByRole('list');
      expect(container).toHaveClass('custom-class');
    });
  });

  // ============================================================================
  // Hook Integration Tests
  // ============================================================================

  describe('Hook Integration', () => {
    it('calls useArtifactGroups with correct params', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      renderWithProviders(
        <GroupsDisplay collectionId="collection-123" artifactId="artifact-456" />
      );

      expect(mockUseArtifactGroups).toHaveBeenCalledWith('artifact-456', 'collection-123');
    });

    it('calls hook with different IDs on prop change', () => {
      mockUseArtifactGroups.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      const { rerender } = renderWithProviders(<GroupsDisplay collectionId="c1" artifactId="a1" />);

      expect(mockUseArtifactGroups).toHaveBeenLastCalledWith('a1', 'c1');

      // Rerender with new IDs
      rerender(
        <QueryClientProvider client={createQueryClient()}>
          <GroupsDisplay collectionId="c2" artifactId="a2" />
        </QueryClientProvider>
      );

      expect(mockUseArtifactGroups).toHaveBeenLastCalledWith('a2', 'c2');
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('handles transition from loading to success', () => {
      // Start with loading
      mockUseArtifactGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isPending: true,
        isSuccess: false,
        status: 'pending',
      } as any);

      const { rerender, container } = renderWithProviders(
        <GroupsDisplay collectionId="c1" artifactId="a1" />
      );

      // Should show skeleton (uses animate-pulse class from shadcn Skeleton)
      expect(container.querySelectorAll('[class*="animate-pulse"]').length).toBeGreaterThan(0);

      // Transition to success
      mockUseArtifactGroups.mockReturnValue({
        data: singleGroup,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      rerender(
        <QueryClientProvider client={createQueryClient()}>
          <GroupsDisplay collectionId="c1" artifactId="a1" />
        </QueryClientProvider>
      );

      // Should show group badge
      expect(screen.getByText('Priority Tasks')).toBeInTheDocument();
    });

    it('handles transition from loading to error', () => {
      // Start with loading
      mockUseArtifactGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isPending: true,
        isSuccess: false,
        status: 'pending',
      } as any);

      const { rerender, container } = renderWithProviders(
        <GroupsDisplay collectionId="c1" artifactId="a1" />
      );

      // Should show skeleton (uses animate-pulse class from shadcn Skeleton)
      expect(container.querySelectorAll('[class*="animate-pulse"]').length).toBeGreaterThan(0);

      // Transition to error
      mockUseArtifactGroups.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed'),
        isError: true,
        isPending: false,
        isSuccess: false,
        status: 'error',
      } as any);

      rerender(
        <QueryClientProvider client={createQueryClient()}>
          <GroupsDisplay collectionId="c1" artifactId="a1" />
        </QueryClientProvider>
      );

      // Should return null (no content)
      expect(container.firstChild).toBeNull();
    });

    it('handles groups with extra properties', () => {
      const groupsWithExtras = [
        {
          id: '1',
          name: 'Priority Tasks',
          position: 0,
          collection_id: 'c1',
          description: 'Extra field',
          created_at: '2024-01-01',
        },
      ];

      mockUseArtifactGroups.mockReturnValue({
        data: groupsWithExtras,
        isLoading: false,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
      } as any);

      renderWithProviders(<GroupsDisplay collectionId="c1" artifactId="a1" />);

      // Should still render correctly, extracting only id and name
      expect(screen.getByText('Priority Tasks')).toBeInTheDocument();
    });
  });
});
