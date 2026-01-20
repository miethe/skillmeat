/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GroupSelector } from '@/app/groups/components/group-selector';
import { useGroups } from '@/hooks';
import type { Group, GroupListResponse } from '@/types/groups';

// Polyfill scrollIntoView for Radix UI components
Element.prototype.scrollIntoView = jest.fn();

// Mock the hooks module
jest.mock('@/hooks', () => ({
  useGroups: jest.fn(),
}));

// Mock next/navigation
const mockPush = jest.fn();
const mockSearchParams = new URLSearchParams();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
  }),
  useSearchParams: () => mockSearchParams,
}));

const mockUseGroups = useGroups as jest.MockedFunction<typeof useGroups>;

describe('GroupSelector', () => {
  const mockGroups: Group[] = [
    {
      id: 'group-1',
      collection_id: 'collection-1',
      name: 'Development Tools',
      description: 'Tools for development',
      position: 0,
      artifact_count: 5,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'group-2',
      collection_id: 'collection-1',
      name: 'Productivity',
      description: 'Productivity skills',
      position: 1,
      artifact_count: 3,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    },
    {
      id: 'group-3',
      collection_id: 'collection-1',
      name: 'Empty Group',
      position: 2,
      artifact_count: 0,
      created_at: '2024-01-03T00:00:00Z',
      updated_at: '2024-01-03T00:00:00Z',
    },
  ];

  const mockGroupsResponse: GroupListResponse = {
    groups: mockGroups,
    total: mockGroups.length,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockSearchParams.delete('group');
    mockUseGroups.mockReturnValue({
      data: mockGroupsResponse,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      refetch: jest.fn(),
    } as any);
  });

  describe('loading state', () => {
    it('renders loading state while fetching groups', () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      render(<GroupSelector collectionId="collection-1" />);

      expect(screen.getByRole('status', { name: /loading groups/i })).toBeInTheDocument();
      expect(screen.getByText(/loading groups/i)).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('renders error state when fetch fails', () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('API Error'),
        isError: true,
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      render(<GroupSelector collectionId="collection-1" />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/failed to load groups/i)).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('renders empty state when no groups exist', () => {
      mockUseGroups.mockReturnValue({
        data: { groups: [], total: 0 },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      render(<GroupSelector collectionId="collection-1" />);

      expect(screen.getByRole('status', { name: /no groups available/i })).toBeInTheDocument();
      expect(screen.getByText(/no groups in this collection/i)).toBeInTheDocument();
    });
  });

  describe('success state', () => {
    it('renders all groups in dropdown', async () => {
      render(<GroupSelector collectionId="collection-1" />);

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        // Use getAllByText since Radix renders items in both trigger and dropdown
        expect(screen.getAllByText('All artifacts').length).toBeGreaterThan(0);
        expect(screen.getByText('Development Tools')).toBeInTheDocument();
        expect(screen.getByText('Productivity')).toBeInTheDocument();
        expect(screen.getByText('Empty Group')).toBeInTheDocument();
      });
    });

    it('displays artifact count for each group with artifacts', async () => {
      render(<GroupSelector collectionId="collection-1" />);

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        // Groups with artifacts show count in parentheses
        expect(screen.getByText('(5)')).toBeInTheDocument();
        expect(screen.getByText('(3)')).toBeInTheDocument();
        // Empty group should not show count
        expect(screen.queryByText('(0)')).not.toBeInTheDocument();
      });
    });
  });

  describe('selection behavior', () => {
    it('calls onGroupSelect when selection changes', async () => {
      const mockOnGroupSelect = jest.fn();

      render(
        <GroupSelector collectionId="collection-1" onGroupSelect={mockOnGroupSelect} />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        const developmentTools = screen.getByText('Development Tools');
        fireEvent.click(developmentTools);
      });

      expect(mockOnGroupSelect).toHaveBeenCalledWith('group-1');
    });

    it('updates URL when selection changes', async () => {
      render(<GroupSelector collectionId="collection-1" />);

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        const developmentTools = screen.getByText('Development Tools');
        fireEvent.click(developmentTools);
      });

      expect(mockPush).toHaveBeenCalledWith('/groups?group=group-1');
    });

    it('clears group from URL when "All artifacts" is selected', async () => {
      // Set initial group in URL
      mockSearchParams.set('group', 'group-1');

      render(
        <GroupSelector
          collectionId="collection-1"
          selectedGroupId="group-1"
        />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        const allArtifacts = screen.getByText('All artifacts');
        fireEvent.click(allArtifacts);
      });

      expect(mockPush).toHaveBeenCalledWith('/groups?');
    });

    it('shows current selection from URL', async () => {
      mockSearchParams.set('group', 'group-1');

      render(<GroupSelector collectionId="collection-1" />);

      // The trigger should show the selected group name via SelectValue
      const trigger = screen.getByRole('combobox');

      // With group-1 selected, the trigger should show Development Tools
      // (Radix may show it in the trigger span before opening)
      await waitFor(() => {
        // Check that the trigger contains the selected group text
        expect(trigger).toHaveTextContent('Development Tools');
      });
    });

    it('uses selectedGroupId prop over URL param when provided', async () => {
      mockSearchParams.set('group', 'group-1'); // URL has group-1

      render(
        <GroupSelector
          collectionId="collection-1"
          selectedGroupId="group-2" // But prop says group-2
        />
      );

      const trigger = screen.getByRole('combobox');

      // Should use selectedGroupId from props (group-2 = Productivity)
      await waitFor(() => {
        expect(trigger).toHaveTextContent('Productivity');
      });
    });

    it('calls onGroupSelect with null when "All artifacts" is clicked', async () => {
      const mockOnGroupSelect = jest.fn();

      render(
        <GroupSelector
          collectionId="collection-1"
          selectedGroupId="group-1"
          onGroupSelect={mockOnGroupSelect}
        />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        const allArtifacts = screen.getByText('All artifacts');
        fireEvent.click(allArtifacts);
      });

      expect(mockOnGroupSelect).toHaveBeenCalledWith(null);
    });
  });

  describe('accessibility', () => {
    it('has accessible label on select trigger', () => {
      render(<GroupSelector collectionId="collection-1" />);

      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveAttribute('aria-label', 'Select group');
    });

    it('has proper aria attributes on loading state', () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      render(<GroupSelector collectionId="collection-1" />);

      const loadingElement = screen.getByRole('status');
      expect(loadingElement).toHaveAttribute('aria-label', 'Loading groups');
    });

    it('has proper aria attributes on error state', () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('API Error'),
        isError: true,
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      render(<GroupSelector collectionId="collection-1" />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('has proper aria attributes on empty state', () => {
      mockUseGroups.mockReturnValue({
        data: { groups: [], total: 0 },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      render(<GroupSelector collectionId="collection-1" />);

      const emptyState = screen.getByRole('status');
      expect(emptyState).toHaveAttribute('aria-label', 'No groups available');
    });
  });

  describe('className prop', () => {
    it('applies custom className to trigger', () => {
      const customClass = 'custom-width';
      render(<GroupSelector collectionId="collection-1" className={customClass} />);

      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveClass(customClass);
    });
  });
});
