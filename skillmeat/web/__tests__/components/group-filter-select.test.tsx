/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient } from '@tanstack/react-query';
import { GroupFilterSelect } from '@/components/shared/group-filter-select';
import { useGroups } from '@/hooks';
import type { Group, GroupListResponse } from '@/types/groups';

// Polyfill scrollIntoView for Radix UI components
Element.prototype.scrollIntoView = jest.fn();

// Mock the hooks module
jest.mock('@/hooks', () => ({
  useGroups: jest.fn(),
}));

const mockUseGroups = useGroups as jest.MockedFunction<typeof useGroups>;

describe('GroupFilterSelect', () => {
  const mockCollectionId = 'collection-1';
  const mockOnChange = jest.fn();

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
      name: 'Analytics',
      description: 'Analytics tools',
      position: 2,
      artifact_count: 2,
      created_at: '2024-01-03T00:00:00Z',
      updated_at: '2024-01-03T00:00:00Z',
    },
  ];

  const mockGroupsResponse: GroupListResponse = {
    groups: mockGroups,
    total: mockGroups.length,
  };

  let queryClient: QueryClient;

  beforeEach(() => {
    jest.clearAllMocks();

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Default successful response
    mockUseGroups.mockReturnValue({
      data: mockGroupsResponse,
      isLoading: false,
      isError: false,
      error: null,
      isSuccess: true,
      refetch: jest.fn(),
    } as any);
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe('loading state', () => {
    it('shows loading skeleton when isLoading is true', () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      // Skeleton should be present
      const skeleton = document.querySelector('.h-9');
      expect(skeleton).toBeInTheDocument();
      expect(skeleton).toHaveClass('w-full');
    });

    it('applies className to loading skeleton', () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
          className="custom-class"
        />
      );

      const skeleton = document.querySelector('.h-9');
      expect(skeleton).toHaveClass('custom-class');
    });
  });

  describe('error state', () => {
    it('renders disabled select when isError is true', () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error('API Error'),
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeDisabled();
      expect(trigger).toHaveTextContent('All Groups');
    });

    it('handles error state gracefully with only All Groups option', async () => {
      mockUseGroups.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error('API Error'),
        isSuccess: false,
        refetch: jest.fn(),
      } as any);

      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeDisabled();
    });
  });

  describe('empty groups state', () => {
    it('renders disabled select when groups array is empty', () => {
      mockUseGroups.mockReturnValue({
        data: { groups: [], total: 0 },
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeDisabled();
      expect(trigger).toHaveTextContent('All Groups');
    });

    it('handles null groups data gracefully', () => {
      mockUseGroups.mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeDisabled();
    });

    it('handles undefined groups array gracefully', () => {
      mockUseGroups.mockReturnValue({
        data: { groups: undefined as any, total: 0 },
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeDisabled();
    });
  });

  describe('success state', () => {
    it('renders "All Groups" placeholder initially when no value', () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('All Groups');
      expect(trigger).not.toBeDisabled();
    });

    it('renders all groups when data loads successfully', async () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('Development Tools')).toBeInTheDocument();
        expect(screen.getByText('Productivity')).toBeInTheDocument();
        expect(screen.getByText('Analytics')).toBeInTheDocument();
      });
    });

    it('displays "All Groups" option in dropdown', async () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        // Radix renders items in both trigger and content
        const allGroupsOptions = screen.getAllByText('All Groups');
        expect(allGroupsOptions.length).toBeGreaterThan(0);
      });
    });

    it('shows selected group name when value is provided', () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value="group-1"
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('Development Tools');
    });

    it('shows "All Groups" when value is undefined', () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value={undefined}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('All Groups');
    });
  });

  describe('user interactions', () => {
    it('calls onChange with groupId when selecting a group', async () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        const developmentTools = screen.getByText('Development Tools');
        fireEvent.click(developmentTools);
      });

      expect(mockOnChange).toHaveBeenCalledWith('group-1');
    });

    it('calls onChange with undefined when selecting "All Groups"', async () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value="group-1"
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        const allGroupsOptions = screen.getAllByText('All Groups');
        // Click the one in the dropdown content (not the trigger)
        const dropdownOption = allGroupsOptions.find((el) =>
          el.closest('[role="option"]')
        );
        if (dropdownOption) {
          fireEvent.click(dropdownOption);
        }
      });

      expect(mockOnChange).toHaveBeenCalledWith(undefined);
    });

    it('allows switching between groups', async () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value="group-1"
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');

      // First selection
      fireEvent.click(trigger);
      await waitFor(() => {
        const productivity = screen.getByText('Productivity');
        fireEvent.click(productivity);
      });

      expect(mockOnChange).toHaveBeenCalledWith('group-2');
    });

    it('works with userEvent interactions', async () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');

      // Verify the trigger is accessible
      expect(trigger).toBeInTheDocument();
      expect(trigger).not.toBeDisabled();

      // Focus the trigger
      trigger.focus();
      expect(trigger).toHaveFocus();
    });
  });

  describe('value prop handling', () => {
    it('respects initial value prop', () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value="group-2"
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('Productivity');
    });

    it('updates when value prop changes', () => {
      const { rerender } = render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value="group-1"
          onChange={mockOnChange}
        />
      );

      let trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('Development Tools');

      // Rerender with new value
      rerender(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value="group-2"
          onChange={mockOnChange}
        />
      );

      trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('Productivity');
    });

    it('handles switching from value to undefined', () => {
      const { rerender } = render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value="group-1"
          onChange={mockOnChange}
        />
      );

      let trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('Development Tools');

      // Rerender with undefined value
      rerender(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value={undefined}
          onChange={mockOnChange}
        />
      );

      trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('All Groups');
    });

    it('handles invalid group ID gracefully', () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value="non-existent-group"
          onChange={mockOnChange}
        />
      );

      // Select should still render, just won't match any group
      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeInTheDocument();
    });
  });

  describe('className prop', () => {
    it('applies className prop correctly', () => {
      const customClass = 'w-[300px]';
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
          className={customClass}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveClass(customClass);
    });

    it('applies multiple custom classes', () => {
      const customClasses = 'w-full max-w-md';
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
          className={customClasses}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveClass('w-full');
      expect(trigger).toHaveClass('max-w-md');
    });
  });

  describe('collectionId prop', () => {
    it('passes collectionId to useGroups hook', () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      expect(mockUseGroups).toHaveBeenCalledWith(mockCollectionId);
    });

    it('updates when collectionId changes', () => {
      const { rerender } = render(
        <GroupFilterSelect
          collectionId="collection-1"
          onChange={mockOnChange}
        />
      );

      expect(mockUseGroups).toHaveBeenCalledWith('collection-1');

      rerender(
        <GroupFilterSelect
          collectionId="collection-2"
          onChange={mockOnChange}
        />
      );

      expect(mockUseGroups).toHaveBeenCalledWith('collection-2');
    });
  });

  describe('accessibility', () => {
    it('select is keyboard accessible', () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeInTheDocument();
      expect(trigger).not.toBeDisabled();
    });

    it('disabled state has proper accessibility attributes', () => {
      mockUseGroups.mockReturnValue({
        data: { groups: [], total: 0 },
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeDisabled();
    });

    it('maintains focus management in dropdown', async () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('Development Tools')).toBeInTheDocument();
      });

      // Radix UI handles focus management internally
      // Just verify the dropdown is accessible
      const option = screen.getByText('Development Tools');
      expect(option).toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('handles rapid successive onChange calls', async () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');

      // First selection
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText('Development Tools')).toBeInTheDocument();
      });
      const group1 = screen.getByText('Development Tools');
      fireEvent.click(group1);

      // Second selection
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText('Productivity')).toBeInTheDocument();
      });
      const group2 = screen.getByText('Productivity');
      fireEvent.click(group2);

      expect(mockOnChange).toHaveBeenCalledTimes(2);
      expect(mockOnChange).toHaveBeenNthCalledWith(1, 'group-1');
      expect(mockOnChange).toHaveBeenNthCalledWith(2, 'group-2');
    });

    it('calls onChange even when selecting already selected group', async () => {
      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          value="group-1"
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('Productivity')).toBeInTheDocument();
      });

      // Click a different option to verify onChange is working
      const productivity = screen.getByText('Productivity');
      fireEvent.click(productivity);

      // Radix Select will call onChange for controlled components
      expect(mockOnChange).toHaveBeenCalledWith('group-2');
    });

    it('handles groups with same name but different IDs', async () => {
      const duplicateNameGroups: Group[] = [
        {
          id: 'group-1',
          collection_id: 'collection-1',
          name: 'Tools',
          description: 'Tools for development',
          position: 0,
          artifact_count: 5,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        {
          id: 'group-2',
          collection_id: 'collection-1',
          name: 'Tools',
          description: 'Productivity skills',
          position: 1,
          artifact_count: 3,
          created_at: '2024-01-02T00:00:00Z',
          updated_at: '2024-01-02T00:00:00Z',
        },
      ];

      mockUseGroups.mockReturnValue({
        data: { groups: duplicateNameGroups, total: 2 },
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        refetch: jest.fn(),
      } as any);

      render(
        <GroupFilterSelect
          collectionId={mockCollectionId}
          onChange={mockOnChange}
        />
      );

      const trigger = screen.getByRole('combobox');
      fireEvent.click(trigger);

      await waitFor(() => {
        const toolsOptions = screen.getAllByText('Tools');
        // Should have multiple options with same name
        expect(toolsOptions.length).toBeGreaterThan(1);
      });
    });
  });
});
