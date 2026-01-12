/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PathTagReview, PathTagReviewSkeleton } from '@/components/marketplace/path-tag-review';
import { usePathTags, useUpdatePathTagStatus } from '@/hooks';
import type { PathSegmentsResponse, ExtractedSegment } from '@/types/path-tags';

// Mock hooks
jest.mock('@/hooks', () => ({
  usePathTags: jest.fn(),
  useUpdatePathTagStatus: jest.fn(),
}));

const mockUsePathTags = usePathTags as jest.MockedFunction<typeof usePathTags>;
const mockUseUpdatePathTagStatus = useUpdatePathTagStatus as jest.MockedFunction<
  typeof useUpdatePathTagStatus
>;

// Test data factory
const createSegment = (
  segment: string,
  normalized: string,
  status: ExtractedSegment['status'],
  reason?: string
): ExtractedSegment => ({
  segment,
  normalized,
  status,
  ...(reason && { reason }),
});

const createPathTagsResponse = (segments: ExtractedSegment[]): PathSegmentsResponse => ({
  entry_id: 'entry-123',
  raw_path: 'categories/05-data-ai/skills/canvas.md',
  extracted: segments,
  extracted_at: '2025-01-05T00:00:00Z',
});

// Test wrapper with QueryClientProvider
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe('PathTagReview', () => {
  const mockProps = {
    sourceId: 'source-123',
    entryId: 'entry-456',
  };

  const mockMutate = jest.fn();
  const mockRefetch = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    // Default mutation mock
    mockUseUpdatePathTagStatus.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isError: false,
      isSuccess: false,
      error: null,
      data: undefined,
      reset: jest.fn(),
      mutateAsync: jest.fn(),
      status: 'idle',
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      isIdle: true,
      isPaused: false,
      submittedAt: 0,
    });
  });

  // ============================================================================
  // Loading State Tests
  // ============================================================================

  describe('loading state', () => {
    it('displays loading skeleton when isLoading is true', () => {
      mockUsePathTags.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: false,
        status: 'pending',
        fetchStatus: 'fetching',
        dataUpdatedAt: 0,
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: false,
        isFetchedAfterMount: false,
        isFetching: true,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: true,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByLabelText('Loading segments')).toBeInTheDocument();
      expect(screen.getByLabelText('Loading segments')).toHaveAttribute('aria-busy', 'true');
    });

    it('renders PathTagReviewSkeleton correctly', () => {
      render(
        <TestWrapper>
          <PathTagReviewSkeleton />
        </TestWrapper>
      );

      expect(screen.getByLabelText('Loading segments')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Error State Tests
  // ============================================================================

  describe('error state', () => {
    it('displays error alert when error is present', () => {
      const testError = new Error('Failed to fetch segments');

      mockUsePathTags.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: testError,
        isError: true,
        refetch: mockRefetch,
        isSuccess: false,
        status: 'error',
        fetchStatus: 'idle',
        dataUpdatedAt: 0,
        errorUpdatedAt: Date.now(),
        failureCount: 1,
        failureReason: testError,
        errorUpdateCount: 1,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: true,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByText('Failed to load path segments')).toBeInTheDocument();
      expect(screen.getByText('Failed to fetch segments')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('calls refetch when retry button is clicked', () => {
      const testError = new Error('Test error');

      mockUsePathTags.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: testError,
        isError: true,
        refetch: mockRefetch,
        isSuccess: false,
        status: 'error',
        fetchStatus: 'idle',
        dataUpdatedAt: 0,
        errorUpdatedAt: Date.now(),
        failureCount: 1,
        failureReason: testError,
        errorUpdateCount: 1,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: true,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      const retryButton = screen.getByRole('button', { name: /retry/i });
      fireEvent.click(retryButton);

      expect(mockRefetch).toHaveBeenCalledTimes(1);
    });

    it('displays generic message when error has no message', () => {
      const emptyError = new Error();

      mockUsePathTags.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: emptyError,
        isError: true,
        refetch: mockRefetch,
        isSuccess: false,
        status: 'error',
        fetchStatus: 'idle',
        dataUpdatedAt: 0,
        errorUpdatedAt: Date.now(),
        failureCount: 1,
        failureReason: emptyError,
        errorUpdateCount: 1,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: true,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Empty State Tests
  // ============================================================================

  describe('empty state', () => {
    it('displays empty message when extracted array is empty', () => {
      const emptyData = createPathTagsResponse([]);

      mockUsePathTags.mockReturnValue({
        data: emptyData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByText('No segments extracted')).toBeInTheDocument();
      expect(
        screen.getByText('This entry does not have any path segments to review.')
      ).toBeInTheDocument();
    });

    it('displays empty state when data is undefined', () => {
      mockUsePathTags.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByText('No segments extracted')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Data Rendering Tests
  // ============================================================================

  describe('data rendering', () => {
    it('displays raw path', () => {
      const testData = createPathTagsResponse([
        createSegment('05-data-ai', 'data-ai', 'pending'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByText(/Path:/i)).toBeInTheDocument();
      expect(screen.getByText('categories/05-data-ai/skills/canvas.md')).toBeInTheDocument();
    });

    it('renders all segments with correct statuses', () => {
      const testData = createPathTagsResponse([
        createSegment('05-data-ai', 'data-ai', 'pending'),
        createSegment('skills', 'skills', 'approved'),
        createSegment('test', 'test', 'rejected'),
        createSegment('excluded-item', 'excluded-item', 'excluded', 'Matches exclude pattern'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      // Check segments are rendered
      expect(screen.getByText('05-data-ai')).toBeInTheDocument();
      expect(screen.getByText('skills')).toBeInTheDocument();
      expect(screen.getByText('test')).toBeInTheDocument();
      expect(screen.getByText('excluded-item')).toBeInTheDocument();

      // Check status badges
      expect(screen.getByText('Pending')).toBeInTheDocument();
      expect(screen.getByText('Approved')).toBeInTheDocument();
      expect(screen.getByText('Rejected')).toBeInTheDocument();
      expect(screen.getByText('Excluded')).toBeInTheDocument();
    });

    it('shows normalized values when different from segment', () => {
      const testData = createPathTagsResponse([
        createSegment('05-data-ai', 'data-ai', 'pending'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByText('05-data-ai')).toBeInTheDocument();
      expect(screen.getByText('data-ai')).toBeInTheDocument();
    });

    it('does not show arrow when normalized equals segment', () => {
      const testData = createPathTagsResponse([createSegment('skills', 'skills', 'pending')]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      // Original segment and normalized should be the same (no arrow rendered)
      expect(screen.getByText('skills')).toBeInTheDocument();
      // Arrow icon (ArrowRight) should NOT be rendered between segment and normalized
      // We verify this by checking that there's only the segment text, not a separate normalized text
      const skillsElements = screen.getAllByText('skills');
      expect(skillsElements).toHaveLength(1); // Only one instance (not showing segment + normalized)
    });
  });

  // ============================================================================
  // Action Tests
  // ============================================================================

  describe('approve action', () => {
    it('calls mutate with correct params when approve button is clicked', () => {
      const testData = createPathTagsResponse([
        createSegment('05-data-ai', 'data-ai', 'pending'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      const approveButton = screen.getByLabelText('Approve segment');
      fireEvent.click(approveButton);

      expect(mockMutate).toHaveBeenCalledWith({
        sourceId: 'source-123',
        entryId: 'entry-456',
        segment: '05-data-ai',
        status: 'approved',
      });
    });
  });

  describe('reject action', () => {
    it('calls mutate with correct params when reject button is clicked', () => {
      const testData = createPathTagsResponse([
        createSegment('test-segment', 'test-segment', 'pending'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      const rejectButton = screen.getByLabelText('Reject segment');
      fireEvent.click(rejectButton);

      expect(mockMutate).toHaveBeenCalledWith({
        sourceId: 'source-123',
        entryId: 'entry-456',
        segment: 'test-segment',
        status: 'rejected',
      });
    });
  });

  describe('buttons disabled during mutation', () => {
    it('disables approve and reject buttons when isPending is true', () => {
      const testData = createPathTagsResponse([
        createSegment('test-segment', 'test-segment', 'pending'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      mockUseUpdatePathTagStatus.mockReturnValue({
        mutate: mockMutate,
        isPending: true,
        isError: false,
        isSuccess: false,
        error: null,
        data: undefined,
        reset: jest.fn(),
        mutateAsync: jest.fn(),
        status: 'pending',
        variables: undefined,
        context: undefined,
        failureCount: 0,
        failureReason: null,
        isIdle: false,
        isPaused: false,
        submittedAt: Date.now(),
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      const approveButton = screen.getByLabelText('Approve segment');
      const rejectButton = screen.getByLabelText('Reject segment');

      expect(approveButton).toBeDisabled();
      expect(rejectButton).toBeDisabled();
    });
  });

  // ============================================================================
  // Excluded Segments Tests
  // ============================================================================

  describe('excluded segments', () => {
    it('does not render approve/reject buttons for excluded segments', () => {
      const testData = createPathTagsResponse([
        createSegment('excluded-item', 'excluded-item', 'excluded', 'Matches exclude pattern'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.queryByLabelText('Approve segment')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Reject segment')).not.toBeInTheDocument();
    });

    it('displays exclusion reason when present', () => {
      const testData = createPathTagsResponse([
        createSegment('excluded-item', 'excluded-item', 'excluded', 'Matches exclude pattern'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByText('Matches exclude pattern')).toBeInTheDocument();
    });

    it('does not render action buttons for approved segments', () => {
      const testData = createPathTagsResponse([
        createSegment('approved-item', 'approved-item', 'approved'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.queryByLabelText('Approve segment')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Reject segment')).not.toBeInTheDocument();
    });

    it('does not render action buttons for rejected segments', () => {
      const testData = createPathTagsResponse([
        createSegment('rejected-item', 'rejected-item', 'rejected'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.queryByLabelText('Approve segment')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Reject segment')).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // Summary Tests
  // ============================================================================

  describe('summary counts', () => {
    it('displays correct counts for mixed statuses', () => {
      const testData = createPathTagsResponse([
        createSegment('segment-1', 'segment-1', 'approved'),
        createSegment('segment-2', 'segment-2', 'approved'),
        createSegment('segment-3', 'segment-3', 'rejected'),
        createSegment('segment-4', 'segment-4', 'pending'),
        createSegment('segment-5', 'segment-5', 'pending'),
        createSegment('segment-6', 'segment-6', 'pending'),
        createSegment('segment-7', 'segment-7', 'excluded'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByText('2 approved')).toBeInTheDocument();
      expect(screen.getByText('1 rejected')).toBeInTheDocument();
      expect(screen.getByText('3 pending')).toBeInTheDocument();
      expect(screen.getByText('1 excluded')).toBeInTheDocument();
    });

    it('shows 0 counts for missing statuses', () => {
      const testData = createPathTagsResponse([
        createSegment('segment-1', 'segment-1', 'pending'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      render(
        <TestWrapper>
          <PathTagReview {...mockProps} />
        </TestWrapper>
      );

      expect(screen.getByText('0 approved')).toBeInTheDocument();
      expect(screen.getByText('0 rejected')).toBeInTheDocument();
      expect(screen.getByText('1 pending')).toBeInTheDocument();
      expect(screen.getByText('0 excluded')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // CSS Class Tests
  // ============================================================================

  describe('className prop', () => {
    it('applies custom className to root element', () => {
      const testData = createPathTagsResponse([
        createSegment('test-segment', 'test-segment', 'pending'),
      ]);

      mockUsePathTags.mockReturnValue({
        data: testData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: mockRefetch,
        isSuccess: true,
        status: 'success',
        fetchStatus: 'idle',
        dataUpdatedAt: Date.now(),
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoadingError: false,
        isPaused: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isInitialLoading: false,
        refetchInterval: false,
        refetchIntervalInBackground: false,
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      });

      const { container } = render(
        <TestWrapper>
          <PathTagReview {...mockProps} className="custom-class" />
        </TestWrapper>
      );

      expect(container.firstChild).toHaveClass('custom-class');
    });
  });
});
