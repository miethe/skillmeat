/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CollectionSwitcher } from '@/components/collection/collection-switcher';
import { useCollectionContext } from '@/hooks';
import type { Collection } from '@/types/collections';

// Polyfill scrollIntoView for Radix UI components
Element.prototype.scrollIntoView = jest.fn();

// Mock the useCollectionContext hook
jest.mock('@/hooks', () => ({
  useCollectionContext: jest.fn(),
}));

const mockUseCollectionContext = useCollectionContext as jest.MockedFunction<
  typeof useCollectionContext
>;

describe('CollectionSwitcher', () => {
  const mockCollections: Collection[] = [
    {
      id: 'default',
      name: 'Default Collection',
      version: '1.0.0',
      artifact_count: 5,
      created: '2024-01-01T00:00:00Z',
      updated: '2024-01-01T00:00:00Z',
    },
    {
      id: 'work',
      name: 'Work Collection',
      version: '1.0.0',
      artifact_count: 3,
      created: '2024-01-02T00:00:00Z',
      updated: '2024-01-02T00:00:00Z',
    },
    {
      id: 'personal',
      name: 'Personal Collection',
      version: '1.0.0',
      artifact_count: 0,
      created: '2024-01-03T00:00:00Z',
      updated: '2024-01-03T00:00:00Z',
    },
  ];

  const mockSetSelectedCollectionId = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
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
      setSelectedCollectionId: mockSetSelectedCollectionId,
      setSelectedGroupId: jest.fn(),
      refreshCollections: jest.fn(),
      refreshGroups: jest.fn(),
    });
  });

  it('renders with "All Collections" as default display', () => {
    render(<CollectionSwitcher />);
    expect(screen.getByRole('combobox')).toHaveTextContent('All Collections');
  });

  it('displays selected collection name when collection is selected', () => {
    mockUseCollectionContext.mockReturnValue({
      ...mockUseCollectionContext(),
      selectedCollectionId: 'work',
      currentCollection: mockCollections[1],
    });

    render(<CollectionSwitcher />);
    expect(screen.getByRole('combobox')).toHaveTextContent('Work Collection');
  });

  it('opens dropdown when trigger button is clicked', async () => {
    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search collections...')).toBeInTheDocument();
    });
  });

  it('displays all collections in the dropdown', async () => {
    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('Default Collection')).toBeInTheDocument();
      expect(screen.getByText('Work Collection')).toBeInTheDocument();
      expect(screen.getByText('Personal Collection')).toBeInTheDocument();
    });
  });

  it('shows artifact count for collections with artifacts', async () => {
    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    await waitFor(() => {
      // Collections with artifact_count > 0 should show the count
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  it('calls setSelectedCollectionId when "All Collections" is selected', async () => {
    mockUseCollectionContext.mockReturnValue({
      ...mockUseCollectionContext(),
      selectedCollectionId: 'work',
      currentCollection: mockCollections[1],
    });

    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    await waitFor(() => {
      const allCollectionsOption = screen.getByText('All Collections');
      fireEvent.click(allCollectionsOption);
    });

    expect(mockSetSelectedCollectionId).toHaveBeenCalledWith(null);
  });

  it('calls setSelectedCollectionId when a collection is selected', async () => {
    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    await waitFor(() => {
      const workCollection = screen.getByText('Work Collection');
      fireEvent.click(workCollection);
    });

    expect(mockSetSelectedCollectionId).toHaveBeenCalledWith('work');
  });

  it('shows "Add Collection" option when onCreateCollection is provided', async () => {
    const mockOnCreateCollection = jest.fn();
    render(<CollectionSwitcher onCreateCollection={mockOnCreateCollection} />);

    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('Add Collection')).toBeInTheDocument();
    });
  });

  it('calls onCreateCollection when "Add Collection" is clicked', async () => {
    const mockOnCreateCollection = jest.fn();
    render(<CollectionSwitcher onCreateCollection={mockOnCreateCollection} />);

    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    await waitFor(() => {
      const addCollectionOption = screen.getByText('Add Collection');
      fireEvent.click(addCollectionOption);
    });

    expect(mockOnCreateCollection).toHaveBeenCalled();
  });

  it('does not show "Add Collection" option when onCreateCollection is not provided', async () => {
    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.queryByText('Add Collection')).not.toBeInTheDocument();
    });
  });

  it('is disabled when collections are loading', () => {
    mockUseCollectionContext.mockReturnValue({
      ...mockUseCollectionContext(),
      isLoadingCollections: true,
    });

    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toBeDisabled();
  });

  it('shows "No collection found" when search has no results', async () => {
    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('Search collections...');
      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });
    });

    await waitFor(() => {
      expect(screen.getByText('No collection found.')).toBeInTheDocument();
    });
  });

  it('applies custom className to trigger button', () => {
    const customClass = 'w-[300px]';
    render(<CollectionSwitcher className={customClass} />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toHaveClass(customClass);
  });

  it('has proper accessibility attributes', () => {
    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toHaveAttribute('aria-label', 'Select collection');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  it('updates aria-expanded when dropdown is opened', async () => {
    render(<CollectionSwitcher />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(trigger);

    await waitFor(() => {
      expect(trigger).toHaveAttribute('aria-expanded', 'true');
    });
  });
});
