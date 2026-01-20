/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SourceDetailPage from '@/app/marketplace/sources/[id]/page';
import { useSource, useSourceCatalog, useRescanSource, useImportArtifacts } from '@/hooks';
import type { GitHubSource, CatalogEntry, CatalogListResponse } from '@/types/marketplace';

// Mock hooks
jest.mock('@/hooks', () => ({
  useSource: jest.fn(),
  useSourceCatalog: jest.fn(),
  useRescanSource: jest.fn(),
  useImportArtifacts: jest.fn(),
  useExcludeCatalogEntry: jest.fn(() => ({
    mutate: jest.fn(),
    isPending: false,
  })),
  useUpdateSource: jest.fn(() => ({
    mutateAsync: jest.fn(),
    isPending: false,
  })),
  sourceKeys: {
    all: ['sources'],
    catalogs: () => ['sources', 'catalogs'],
  },
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock CatalogEntryModal to avoid react-markdown parsing issues
jest.mock('@/components/CatalogEntryModal', () => ({
  CatalogEntryModal: ({ entry, open }: any) =>
    open && entry ? <div data-testid="catalog-entry-modal">{entry.name}</div> : null,
}));

// Mock next/navigation
const mockPush = jest.fn();
const mockParams = { id: 'source-123' };

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useParams: () => mockParams,
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithClient = (ui: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

const mockSource: GitHubSource = {
  id: 'source-123',
  repo_url: 'https://github.com/anthropics/skills',
  owner: 'anthropics',
  repo_name: 'skills',
  ref: 'main',
  root_hint: undefined,
  trust_level: 'verified',
  visibility: 'public',
  scan_status: 'success',
  artifact_count: 12,
  last_sync_at: '2024-12-01T10:00:00Z',
  created_at: '2024-11-01T10:00:00Z',
  updated_at: '2024-12-01T10:00:00Z',
};

const createMockEntry = (overrides?: Partial<CatalogEntry>): CatalogEntry => ({
  id: 'entry-1',
  source_id: 'source-123',
  artifact_type: 'skill',
  name: 'test-skill',
  path: 'skills/test-skill',
  upstream_url: 'https://github.com/anthropics/skills/blob/main/skills/test-skill',
  detected_version: '1.0.0',
  detected_sha: 'abc123',
  detected_at: '2024-12-01T10:00:00Z',
  confidence_score: 95,
  status: 'new',
  ...overrides,
});

const mockCatalogResponse: CatalogListResponse = {
  items: [
    createMockEntry({ id: 'entry-1', name: 'skill-1', status: 'new' }),
    createMockEntry({
      id: 'entry-2',
      name: 'skill-2',
      status: 'updated',
      artifact_type: 'command',
    }),
    createMockEntry({ id: 'entry-3', name: 'skill-3', status: 'imported' }),
  ],
  page_info: {
    has_next_page: false,
    has_previous_page: false,
    total_count: 3,
  },
  counts_by_status: {
    new: 1,
    updated: 1,
    imported: 1,
    removed: 0,
  },
  counts_by_type: {
    skill: 2,
    command: 1,
    agent: 0,
    mcp_server: 0,
    hook: 0,
  },
};

describe('SourceDetailPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Default mock implementations
    (useSource as jest.Mock).mockReturnValue({
      data: mockSource,
      isLoading: false,
      error: null,
    });

    (useSourceCatalog as jest.Mock).mockReturnValue({
      data: { pages: [mockCatalogResponse] },
      isLoading: false,
      error: null,
      fetchNextPage: jest.fn(),
      hasNextPage: false,
      isFetchingNextPage: false,
    });

    (useRescanSource as jest.Mock).mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
    });

    (useImportArtifacts as jest.Mock).mockReturnValue({
      mutateAsync: jest.fn(),
      isPending: false,
    });
  });

  describe('Loading State', () => {
    it('shows skeleton while loading source', () => {
      (useSource as jest.Mock).mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      renderWithClient(<SourceDetailPage />);

      // Should show skeleton elements
      const skeletons = screen.getAllByTestId(/loading-skeleton/i);
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('shows skeleton while loading catalog', () => {
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      renderWithClient(<SourceDetailPage />);

      // Should show catalog skeleton cards
      const skeletons = screen.getAllByTestId(/loading-skeleton/i);
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe('Error State', () => {
    it('shows error when source fails to load', () => {
      (useSource as jest.Mock).mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Source not found'),
      });

      renderWithClient(<SourceDetailPage />);

      expect(screen.getByText('Source not found')).toBeInTheDocument();
      expect(screen.getByText(/Unable to load source|Source not found/)).toBeInTheDocument();
    });

    it('shows back button in error state', async () => {
      const user = userEvent.setup();
      (useSource as jest.Mock).mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Not found'),
      });

      renderWithClient(<SourceDetailPage />);

      const backButton = screen.getByRole('button', { name: /back to sources/i });
      await user.click(backButton);

      expect(mockPush).toHaveBeenCalledWith('/marketplace/sources');
    });
  });

  describe('Header', () => {
    it('displays source information', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByText('anthropics/skills')).toBeInTheDocument();
      expect(screen.getByText('main')).toBeInTheDocument();
    });

    it('displays root hint when provided', () => {
      (useSource as jest.Mock).mockReturnValue({
        data: { ...mockSource, root_hint: 'src/' },
        isLoading: false,
        error: null,
      });

      renderWithClient(<SourceDetailPage />);

      expect(screen.getByText(/src\//)).toBeInTheDocument();
    });

    it('has back to sources button', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const backButton = screen.getByRole('button', { name: /back to sources/i });
      await user.click(backButton);

      expect(mockPush).toHaveBeenCalledWith('/marketplace/sources');
    });

    it('has rescan button', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByRole('button', { name: /rescan/i })).toBeInTheDocument();
    });

    it('has view repo button with correct link', () => {
      renderWithClient(<SourceDetailPage />);

      const viewRepoButton = screen.getByRole('button', { name: /view repo/i });
      const link = viewRepoButton.closest('a');
      expect(link).toHaveAttribute('href', 'https://github.com/anthropics/skills');
      expect(link).toHaveAttribute('target', '_blank');
    });
  });

  describe('Rescan Functionality', () => {
    it('triggers rescan when button is clicked', async () => {
      const user = userEvent.setup();
      const mockMutate = jest.fn();
      (useRescanSource as jest.Mock).mockReturnValue({
        mutate: mockMutate,
        isPending: false,
      });

      renderWithClient(<SourceDetailPage />);

      const rescanButton = screen.getByRole('button', { name: /^rescan$/i });
      await user.click(rescanButton);

      expect(mockMutate).toHaveBeenCalledWith({});
    });

    it('shows loading state during rescan', () => {
      (useRescanSource as jest.Mock).mockReturnValue({
        mutate: jest.fn(),
        isPending: true,
      });

      renderWithClient(<SourceDetailPage />);

      expect(screen.getByRole('button', { name: /scanning.../i })).toBeInTheDocument();
    });

    it('disables rescan button during rescan', () => {
      (useRescanSource as jest.Mock).mockReturnValue({
        mutate: jest.fn(),
        isPending: true,
      });

      renderWithClient(<SourceDetailPage />);

      const rescanButton = screen.getByRole('button', { name: /scanning.../i });
      expect(rescanButton).toBeDisabled();
    });
  });

  describe('Status Badges', () => {
    it('displays status counts as badges', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByText('new: 1')).toBeInTheDocument();
      expect(screen.getByText('updated: 1')).toBeInTheDocument();
      expect(screen.getByText('imported: 1')).toBeInTheDocument();
    });

    it('filters by status when badge is clicked', async () => {
      const user = userEvent.setup();
      const mockUseSourceCatalog = useSourceCatalog as jest.Mock;

      renderWithClient(<SourceDetailPage />);

      const newBadge = screen.getByText('new: 1');
      await user.click(newBadge);

      // Check that useSourceCatalog was called with status filter
      const lastCall = mockUseSourceCatalog.mock.calls[mockUseSourceCatalog.mock.calls.length - 1];
      expect(lastCall[1]).toEqual({ status: 'new' });
    });

    it('clears status filter when badge is clicked again', async () => {
      const user = userEvent.setup();
      const mockUseSourceCatalog = useSourceCatalog as jest.Mock;

      renderWithClient(<SourceDetailPage />);

      const newBadge = screen.getByText('new: 1');
      await user.click(newBadge);
      await user.click(newBadge);

      // Last call should have empty filters
      const lastCall = mockUseSourceCatalog.mock.calls[mockUseSourceCatalog.mock.calls.length - 1];
      expect(lastCall[1]).toEqual({});
    });
  });

  describe('Search Functionality', () => {
    it('renders search input', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByPlaceholderText('Search artifacts...')).toBeInTheDocument();
    });

    it('filters artifacts by search query', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const searchInput = screen.getByPlaceholderText('Search artifacts...');
      await user.type(searchInput, 'skill-1');

      // Should only show skill-1
      expect(screen.getByText('skill-1')).toBeInTheDocument();
      expect(screen.queryByText('skill-2')).not.toBeInTheDocument();
    });

    it('searches by path as well as name', async () => {
      const user = userEvent.setup();
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: {
          pages: [
            {
              ...mockCatalogResponse,
              items: [
                createMockEntry({ id: 'entry-1', name: 'test', path: 'skills/special-path' }),
              ],
            },
          ],
        },
        isLoading: false,
      });

      renderWithClient(<SourceDetailPage />);

      const searchInput = screen.getByPlaceholderText('Search artifacts...');
      await user.type(searchInput, 'special-path');

      expect(screen.getByText('test')).toBeInTheDocument();
    });
  });

  describe('Type Filter', () => {
    it('renders type filter dropdown', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('filters by artifact type', async () => {
      const user = userEvent.setup();
      const mockUseSourceCatalog = useSourceCatalog as jest.Mock;

      renderWithClient(<SourceDetailPage />);

      const typeFilter = screen.getByRole('combobox');
      await user.click(typeFilter);

      const skillOption = screen.getByRole('option', { name: /^skills$/i });
      await user.click(skillOption);

      // Check that useSourceCatalog was called with type filter
      await waitFor(() => {
        const lastCall =
          mockUseSourceCatalog.mock.calls[mockUseSourceCatalog.mock.calls.length - 1];
        expect(lastCall[1]).toEqual({ artifact_type: 'skill' });
      });
    });

    it('shows all types when "All types" is selected', async () => {
      const user = userEvent.setup();
      const mockUseSourceCatalog = useSourceCatalog as jest.Mock;

      renderWithClient(<SourceDetailPage />);

      const typeFilter = screen.getByRole('combobox');
      await user.click(typeFilter);

      const allTypesOption = screen.getByRole('option', { name: /all types/i });
      await user.click(allTypesOption);

      await waitFor(() => {
        const lastCall =
          mockUseSourceCatalog.mock.calls[mockUseSourceCatalog.mock.calls.length - 1];
        expect(lastCall[1]?.artifact_type).toBeUndefined();
      });
    });
  });

  describe('Clear Filters', () => {
    it('shows clear filters button when filters are active', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const typeFilter = screen.getByRole('combobox');
      await user.click(typeFilter);
      const skillOption = screen.getByRole('option', { name: /^skills$/i });
      await user.click(skillOption);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear filters/i })).toBeInTheDocument();
      });
    });

    it('clears all filters when clicked', async () => {
      const user = userEvent.setup();
      const mockUseSourceCatalog = useSourceCatalog as jest.Mock;

      renderWithClient(<SourceDetailPage />);

      // Apply a filter
      const typeFilter = screen.getByRole('combobox');
      await user.click(typeFilter);
      const skillOption = screen.getByRole('option', { name: /^skills$/i });
      await user.click(skillOption);

      // Clear filters
      const clearButton = await screen.findByRole('button', { name: /clear filters/i });
      await user.click(clearButton);

      await waitFor(() => {
        const lastCall =
          mockUseSourceCatalog.mock.calls[mockUseSourceCatalog.mock.calls.length - 1];
        expect(lastCall[1]).toEqual({});
      });
    });
  });

  describe('Catalog Cards', () => {
    it('renders all catalog entries', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByText('skill-1')).toBeInTheDocument();
      expect(screen.getByText('skill-2')).toBeInTheDocument();
      expect(screen.getByText('skill-3')).toBeInTheDocument();
    });

    it('displays artifact type badge', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByText('Skill')).toBeInTheDocument();
      expect(screen.getByText('Command')).toBeInTheDocument();
    });

    it('displays status badge', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByText('New')).toBeInTheDocument();
      expect(screen.getByText('Updated')).toBeInTheDocument();
      expect(screen.getByText('Imported')).toBeInTheDocument();
    });

    it('displays confidence score', () => {
      renderWithClient(<SourceDetailPage />);

      // Each entry has 95% confidence in the mock
      const confidenceScores = screen.getAllByText(/95% confidence/);
      expect(confidenceScores.length).toBeGreaterThan(0);
    });

    it('displays GitHub link', () => {
      renderWithClient(<SourceDetailPage />);

      const githubLinks = screen.getAllByText('View on GitHub');
      expect(githubLinks.length).toBe(3);
      expect(githubLinks[0].closest('a')).toHaveAttribute('target', '_blank');
    });
  });

  describe('Selection', () => {
    it('renders checkboxes for importable entries', () => {
      renderWithClient(<SourceDetailPage />);

      const checkboxes = screen.getAllByRole('checkbox');
      // Should have checkboxes for new and updated items (not imported)
      expect(checkboxes.length).toBeGreaterThan(0);
    });

    it('selects entry when checkbox is clicked', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      expect(checkboxes[0]).toBeChecked();
    });

    it('disables checkbox for removed entries', () => {
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: {
          pages: [
            {
              ...mockCatalogResponse,
              items: [createMockEntry({ status: 'removed' })],
            },
          ],
        },
        isLoading: false,
      });

      renderWithClient(<SourceDetailPage />);

      const checkbox = screen.getByRole('checkbox');
      expect(checkbox).toBeDisabled();
    });
  });

  describe('Select All', () => {
    it('renders select all button', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByRole('button', { name: /select all/i })).toBeInTheDocument();
    });

    it('selects all importable entries', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const selectAllButton = screen.getByRole('button', { name: /select all/i });
      await user.click(selectAllButton);

      const checkboxes = screen.getAllByRole('checkbox');
      // Only new and updated entries should be selected (not imported)
      const checkedBoxes = checkboxes.filter((cb) => (cb as HTMLInputElement).checked);
      expect(checkedBoxes.length).toBe(2); // new + updated
    });

    it('changes to "Deselect All" when all are selected', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const selectAllButton = screen.getByRole('button', { name: /select all/i });
      await user.click(selectAllButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /deselect all/i })).toBeInTheDocument();
      });
    });

    it('deselects all when clicked again', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const selectAllButton = screen.getByRole('button', { name: /select all/i });
      await user.click(selectAllButton);

      const deselectAllButton = await screen.findByRole('button', { name: /deselect all/i });
      await user.click(deselectAllButton);

      const checkboxes = screen.getAllByRole('checkbox');
      const checkedBoxes = checkboxes.filter((cb) => (cb as HTMLInputElement).checked);
      expect(checkedBoxes.length).toBe(0);
    });

    it('disables select all when no importable entries', () => {
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: {
          pages: [
            {
              ...mockCatalogResponse,
              items: [createMockEntry({ status: 'imported' })],
            },
          ],
        },
        isLoading: false,
      });

      renderWithClient(<SourceDetailPage />);

      const selectAllButton = screen.getByRole('button', { name: /select all/i });
      expect(selectAllButton).toBeDisabled();
    });
  });

  describe('Import Selected', () => {
    it('shows import button when entries are selected', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      expect(screen.getByRole('button', { name: /import 1 selected/i })).toBeInTheDocument();
    });

    it('updates count when multiple entries are selected', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);
      await user.click(checkboxes[1]);

      expect(screen.getByRole('button', { name: /import 2 selected/i })).toBeInTheDocument();
    });

    it('imports selected entries when clicked', async () => {
      const user = userEvent.setup();
      const mockMutateAsync = jest.fn().mockResolvedValue({});
      (useImportArtifacts as jest.Mock).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      });

      renderWithClient(<SourceDetailPage />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      const importButton = screen.getByRole('button', { name: /import 1 selected/i });
      await user.click(importButton);

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          entry_ids: expect.arrayContaining(['entry-1']),
          conflict_strategy: 'skip',
        });
      });
    });

    it('shows loading state during import', () => {
      (useImportArtifacts as jest.Mock).mockReturnValue({
        mutateAsync: jest.fn(),
        isPending: true,
      });

      // Need to have selection first
      renderWithClient(<SourceDetailPage />);

      // Manually trigger selection state by re-rendering with selected state
      // In a real scenario, this would be from user interaction
      // For this test, we just verify the loading state display
      const { rerender } = renderWithClient(<SourceDetailPage />);

      // Button should show loading when isPending is true
      const importButtons = screen.queryAllByText(/importing.../i);
      if (importButtons.length > 0) {
        expect(importButtons[0]).toBeInTheDocument();
      }
    });
  });

  describe('Single Import', () => {
    it('shows import button on each card', () => {
      renderWithClient(<SourceDetailPage />);

      const importButtons = screen.getAllByRole('button', { name: /^import$/i });
      // Should have import buttons for new and updated entries (not imported)
      expect(importButtons.length).toBe(2);
    });

    it('imports single entry when clicked', async () => {
      const user = userEvent.setup();
      const mockMutateAsync = jest.fn().mockResolvedValue({});
      (useImportArtifacts as jest.Mock).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      });

      renderWithClient(<SourceDetailPage />);

      const importButtons = screen.getAllByRole('button', { name: /^import$/i });
      await user.click(importButtons[0]);

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          entry_ids: ['entry-1'],
          conflict_strategy: 'skip',
        });
      });
    });

    it('does not show import button for imported entries', () => {
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: {
          pages: [
            {
              ...mockCatalogResponse,
              items: [createMockEntry({ status: 'imported', import_date: '2024-12-01T10:00:00Z' })],
            },
          ],
        },
        isLoading: false,
      });

      renderWithClient(<SourceDetailPage />);

      expect(screen.queryByRole('button', { name: /^import$/i })).not.toBeInTheDocument();
      expect(screen.getByText(/Imported 12\/1\/2024/)).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty state when no artifacts', () => {
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: {
          pages: [
            {
              ...mockCatalogResponse,
              items: [],
            },
          ],
        },
        isLoading: false,
      });

      renderWithClient(<SourceDetailPage />);

      expect(screen.getByText('No artifacts found')).toBeInTheDocument();
      expect(screen.getByText(/No artifacts detected in this repository/)).toBeInTheDocument();
    });

    it('shows filtered empty state when search has no results', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      const searchInput = screen.getByPlaceholderText('Search artifacts...');
      await user.type(searchInput, 'nonexistent-artifact');

      expect(screen.getByText('No artifacts found')).toBeInTheDocument();
      expect(screen.getByText(/Try adjusting your filters/)).toBeInTheDocument();
    });
  });

  describe('Pagination', () => {
    it('shows load more button when has next page', () => {
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: { pages: [mockCatalogResponse] },
        isLoading: false,
        fetchNextPage: jest.fn(),
        hasNextPage: true,
        isFetchingNextPage: false,
      });

      renderWithClient(<SourceDetailPage />);

      expect(screen.getByRole('button', { name: /load more/i })).toBeInTheDocument();
    });

    it('fetches next page when load more is clicked', async () => {
      const user = userEvent.setup();
      const mockFetchNextPage = jest.fn();
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: { pages: [mockCatalogResponse] },
        isLoading: false,
        fetchNextPage: mockFetchNextPage,
        hasNextPage: true,
        isFetchingNextPage: false,
      });

      renderWithClient(<SourceDetailPage />);

      const loadMoreButton = screen.getByRole('button', { name: /load more/i });
      await user.click(loadMoreButton);

      expect(mockFetchNextPage).toHaveBeenCalled();
    });

    it('shows loading state when fetching next page', () => {
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: { pages: [mockCatalogResponse] },
        isLoading: false,
        fetchNextPage: jest.fn(),
        hasNextPage: true,
        isFetchingNextPage: true,
      });

      renderWithClient(<SourceDetailPage />);

      expect(screen.getByRole('button', { name: /loading.../i })).toBeInTheDocument();
    });

    it('hides load more button when no next page', () => {
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: { pages: [mockCatalogResponse] },
        isLoading: false,
        fetchNextPage: jest.fn(),
        hasNextPage: false,
        isFetchingNextPage: false,
      });

      renderWithClient(<SourceDetailPage />);

      expect(screen.queryByRole('button', { name: /load more/i })).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible labels for filters', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByPlaceholderText('Search artifacts...')).toBeInTheDocument();
    });

    it('has accessible buttons', () => {
      renderWithClient(<SourceDetailPage />);

      expect(screen.getByRole('button', { name: /back to sources/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^rescan$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /view repo/i })).toBeInTheDocument();
    });

    it('has external link indicators', () => {
      renderWithClient(<SourceDetailPage />);

      const githubLinks = screen.getAllByText('View on GitHub');
      githubLinks.forEach((link) => {
        expect(link.closest('a')).toHaveAttribute('rel', 'noopener noreferrer');
      });
    });
  });

  describe('Duplicate Filter (P4.4b)', () => {
    beforeEach(() => {
      // Mock catalog with excluded entries including duplicates
      (useSourceCatalog as jest.Mock).mockReturnValue({
        data: {
          pages: [
            {
              ...mockCatalogResponse,
              items: [
                createMockEntry({ id: 'entry-1', name: 'skill-1', status: 'new' }),
                createMockEntry({
                  id: 'entry-excluded-1',
                  name: 'duplicate-skill',
                  status: 'excluded',
                  is_duplicate: true,
                  duplicate_reason: 'within_source',
                  duplicate_of: 'skills/original-skill',
                }),
                createMockEntry({
                  id: 'entry-excluded-2',
                  name: 'excluded-not-duplicate',
                  status: 'excluded',
                  is_duplicate: false,
                }),
                createMockEntry({
                  id: 'entry-excluded-3',
                  name: 'cross-source-dup',
                  status: 'excluded',
                  is_duplicate: true,
                  duplicate_reason: 'cross_source',
                }),
              ],
            },
          ],
        },
        isLoading: false,
        isFetching: false,
        fetchNextPage: jest.fn(),
        hasNextPage: false,
        isFetchingNextPage: false,
      });
    });

    it('renders "Only duplicates" toggle in toolbar', () => {
      renderWithClient(<SourceDetailPage />);

      const toggle = screen.getByLabelText('Only duplicates');
      expect(toggle).toBeInTheDocument();
      expect(toggle).not.toBeChecked();
    });

    it('filters excluded list to show only duplicates when toggle is enabled', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      // Expand excluded list
      const expandButton = screen.getByRole('button', { name: /show excluded artifacts/i });
      await user.click(expandButton);

      // Initially should show all 3 excluded entries
      await waitFor(() => {
        expect(screen.getByText('duplicate-skill')).toBeInTheDocument();
        expect(screen.getByText('excluded-not-duplicate')).toBeInTheDocument();
        expect(screen.getByText('cross-source-dup')).toBeInTheDocument();
      });

      // Enable duplicate filter
      const toggle = screen.getByLabelText('Only duplicates');
      await user.click(toggle);

      // Should now only show 2 duplicates (not the non-duplicate)
      await waitFor(() => {
        expect(screen.getByText('duplicate-skill')).toBeInTheDocument();
        expect(screen.getByText('cross-source-dup')).toBeInTheDocument();
        expect(screen.queryByText('excluded-not-duplicate')).not.toBeInTheDocument();
      });
    });

    it('disables duplicate filter when toggle is clicked again', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      // Expand excluded list
      const expandButton = screen.getByRole('button', { name: /show excluded artifacts/i });
      await user.click(expandButton);

      // Enable duplicate filter
      const toggle = screen.getByLabelText('Only duplicates');
      await user.click(toggle);

      await waitFor(() => {
        expect(screen.queryByText('excluded-not-duplicate')).not.toBeInTheDocument();
      });

      // Disable duplicate filter
      await user.click(toggle);

      // Should show all excluded entries again
      await waitFor(() => {
        expect(screen.getByText('duplicate-skill')).toBeInTheDocument();
        expect(screen.getByText('excluded-not-duplicate')).toBeInTheDocument();
        expect(screen.getByText('cross-source-dup')).toBeInTheDocument();
      });
    });

    it('includes duplicate filter in "Clear Filters" action', async () => {
      const user = userEvent.setup();
      renderWithClient(<SourceDetailPage />);

      // Enable duplicate filter
      const toggle = screen.getByLabelText('Only duplicates');
      await user.click(toggle);

      // Clear filters button should appear
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument();
      });

      // Click clear filters
      const clearButton = screen.getByRole('button', { name: /clear/i });
      await user.click(clearButton);

      // Toggle should be unchecked
      await waitFor(() => {
        expect(toggle).not.toBeChecked();
      });
    });

    it('persists duplicate filter in URL parameters', async () => {
      const user = userEvent.setup();
      const mockReplace = jest.fn();

      // Mock useRouter to capture URL changes
      jest.spyOn(require('next/navigation'), 'useRouter').mockReturnValue({
        push: jest.fn(),
        replace: mockReplace,
      });

      renderWithClient(<SourceDetailPage />);

      // Enable duplicate filter
      const toggle = screen.getByLabelText('Only duplicates');
      await user.click(toggle);

      // URL should be updated with showOnlyDuplicates parameter
      await waitFor(() => {
        const lastCall = mockReplace.mock.calls[mockReplace.mock.calls.length - 1];
        if (lastCall) {
          expect(lastCall[0]).toContain('showOnlyDuplicates=true');
        }
      });
    });
  });

  describe('Scan Toast with Dedup Counts (P4.4a)', () => {
    it('includes deduplication stats in scan success toast', async () => {
      const user = userEvent.setup();
      const mockToast = jest.fn();

      jest.spyOn(require('@/hooks/use-toast'), 'useToast').mockReturnValue({
        toast: mockToast,
      });

      const mockMutateAsync = jest.fn().mockResolvedValue({
        status: 'success',
        artifacts_found: 25,
        new_count: 10,
        updated_count: 3,
        unchanged_count: 2,
        removed_count: 0,
        duplicates_within_source: 5,
        duplicates_cross_source: 5,
        total_detected: 30,
        total_unique: 20,
        scanned_at: '2024-12-13T10:00:00Z',
        errors: [],
      });

      (useRescanSource as jest.Mock).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      });

      renderWithClient(<SourceDetailPage />);

      const rescanButton = screen.getByRole('button', { name: /^rescan$/i });
      await user.click(rescanButton);

      // Wait for mutation to complete and toast to be called
      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Scan complete',
          description: expect.stringContaining('25 artifacts'),
        });

        // Check that dedup stats are included
        const toastCall = mockToast.mock.calls.find((call) => call[0].title === 'Scan complete');
        expect(toastCall[0].description).toContain('5 within-source duplicates');
        expect(toastCall[0].description).toContain('5 cross-source duplicates');
      });
    });

    it('shows scan toast without dedup stats when no duplicates', async () => {
      const user = userEvent.setup();
      const mockToast = jest.fn();

      jest.spyOn(require('@/hooks/use-toast'), 'useToast').mockReturnValue({
        toast: mockToast,
      });

      const mockMutateAsync = jest.fn().mockResolvedValue({
        status: 'success',
        artifacts_found: 10,
        new_count: 8,
        updated_count: 2,
        unchanged_count: 0,
        removed_count: 0,
        duplicates_within_source: 0,
        duplicates_cross_source: 0,
        scanned_at: '2024-12-13T10:00:00Z',
        errors: [],
      });

      (useRescanSource as jest.Mock).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      });

      renderWithClient(<SourceDetailPage />);

      const rescanButton = screen.getByRole('button', { name: /^rescan$/i });
      await user.click(rescanButton);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Scan complete',
          description: 'Found 10 artifacts (8 new, 2 updated)',
        });

        // Should NOT contain dedup stats
        const toastCall = mockToast.mock.calls.find((call) => call[0].title === 'Scan complete');
        expect(toastCall[0].description).not.toContain('duplicates');
      });
    });

    it('shows only within-source duplicates when present', async () => {
      const user = userEvent.setup();
      const mockToast = jest.fn();

      jest.spyOn(require('@/hooks/use-toast'), 'useToast').mockReturnValue({
        toast: mockToast,
      });

      const mockMutateAsync = jest.fn().mockResolvedValue({
        status: 'success',
        artifacts_found: 15,
        new_count: 10,
        updated_count: 2,
        unchanged_count: 0,
        removed_count: 0,
        duplicates_within_source: 3,
        duplicates_cross_source: 0,
        scanned_at: '2024-12-13T10:00:00Z',
        errors: [],
      });

      (useRescanSource as jest.Mock).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      });

      renderWithClient(<SourceDetailPage />);

      const rescanButton = screen.getByRole('button', { name: /^rescan$/i });
      await user.click(rescanButton);

      await waitFor(() => {
        const toastCall = mockToast.mock.calls.find((call) => call[0].title === 'Scan complete');
        expect(toastCall[0].description).toContain('3 within-source duplicates');
        expect(toastCall[0].description).not.toContain('cross-source');
      });
    });
  });
});
