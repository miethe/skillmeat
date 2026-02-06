/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryList, type MemoryListProps } from '@/components/memory/memory-list';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';

// ---------------------------------------------------------------------------
// Mock data factory
// ---------------------------------------------------------------------------

function createMockMemory(overrides: Partial<MemoryItemResponse> = {}): MemoryItemResponse {
  return {
    id: 'test-id-1',
    project_id: 'project-1',
    type: 'constraint',
    content: 'Do not use default exports in components',
    confidence: 0.87,
    status: 'candidate',
    provenance: { source_type: 'session-abc123' },
    anchors: ['skillmeat/web/components'],
    ttl_policy: null,
    content_hash: 'hash123',
    access_count: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deprecated_at: null,
    ...overrides,
  };
}

function createMockMemories(count: number): MemoryItemResponse[] {
  return Array.from({ length: count }, (_, i) =>
    createMockMemory({
      id: `test-id-${i + 1}`,
      content: `Memory content ${i + 1}`,
      type: ['constraint', 'decision', 'fix', 'pattern', 'learning'][i % 5],
    })
  );
}

// ---------------------------------------------------------------------------
// Default props factory
// ---------------------------------------------------------------------------

function createDefaultProps(overrides: Partial<MemoryListProps> = {}): MemoryListProps {
  return {
    memories: createMockMemories(3),
    isLoading: false,
    isError: false,
    error: null,
    refetch: jest.fn(),
    selectedIds: new Set<string>(),
    focusedIndex: -1,
    onToggleSelect: jest.fn(),
    onApprove: jest.fn(),
    onReject: jest.fn(),
    onEdit: jest.fn(),
    onMerge: jest.fn(),
    onCardClick: jest.fn(),
    onCreateMemory: jest.fn(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MemoryList', () => {
  describe('Loading state', () => {
    it('renders loading skeleton when isLoading is true', () => {
      const props = createDefaultProps({ isLoading: true });
      render(<MemoryList {...props} />);

      const loadingContainer = screen.getByRole('status');
      expect(loadingContainer).toBeInTheDocument();
      expect(loadingContainer).toHaveAttribute('aria-label', 'Loading memories');
    });

    it('renders screen reader loading message', () => {
      const props = createDefaultProps({ isLoading: true });
      render(<MemoryList {...props} />);

      expect(screen.getByText('Loading memory items...')).toBeInTheDocument();
    });

    it('renders 6 skeleton items when loading', () => {
      const props = createDefaultProps({ isLoading: true });
      const { container } = render(<MemoryList {...props} />);

      // MemoryCardSkeleton has aria-hidden="true" on the outer div with animate-pulse
      const skeletons = container.querySelectorAll('.animate-pulse');
      expect(skeletons).toHaveLength(6);
    });
  });

  describe('Error state', () => {
    it('renders error state with alert role when isError is true', () => {
      const props = createDefaultProps({
        isError: true,
        error: new Error('Network error'),
      });
      render(<MemoryList {...props} />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('displays the error heading', () => {
      const props = createDefaultProps({
        isError: true,
        error: new Error('Network error'),
      });
      render(<MemoryList {...props} />);

      expect(screen.getByText('Failed to load memories')).toBeInTheDocument();
    });

    it('displays the error message', () => {
      const props = createDefaultProps({
        isError: true,
        error: new Error('Network error'),
      });
      render(<MemoryList {...props} />);

      expect(screen.getByText('Network error')).toBeInTheDocument();
    });

    it('displays fallback message when error has no message', () => {
      const props = createDefaultProps({
        isError: true,
        error: null,
      });
      render(<MemoryList {...props} />);

      expect(
        screen.getByText('An unexpected error occurred.')
      ).toBeInTheDocument();
    });

    it('renders retry button in error state', () => {
      const props = createDefaultProps({ isError: true });
      render(<MemoryList {...props} />);

      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('calls refetch when retry button is clicked', async () => {
      const user = userEvent.setup();
      const refetch = jest.fn();
      const props = createDefaultProps({ isError: true, refetch });
      render(<MemoryList {...props} />);

      const retryButton = screen.getByRole('button', { name: /retry/i });
      await user.click(retryButton);

      expect(refetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('Empty state', () => {
    it('renders empty state when memories array is empty', () => {
      const props = createDefaultProps({ memories: [] });
      render(<MemoryList {...props} />);

      expect(screen.getByText('No memories yet')).toBeInTheDocument();
    });

    it('displays helpful description in empty state', () => {
      const props = createDefaultProps({ memories: [] });
      render(<MemoryList {...props} />);

      expect(
        screen.getByText(/Memories are automatically extracted from agent sessions/)
      ).toBeInTheDocument();
    });

    it('renders create button in empty state', () => {
      const props = createDefaultProps({ memories: [] });
      render(<MemoryList {...props} />);

      expect(
        screen.getByRole('button', { name: /create first memory/i })
      ).toBeInTheDocument();
    });

    it('calls onCreateMemory when create button is clicked', async () => {
      const user = userEvent.setup();
      const onCreateMemory = jest.fn();
      const props = createDefaultProps({ memories: [], onCreateMemory });
      render(<MemoryList {...props} />);

      const createButton = screen.getByRole('button', { name: /create first memory/i });
      await user.click(createButton);

      expect(onCreateMemory).toHaveBeenCalledTimes(1);
    });
  });

  describe('Data rendering', () => {
    it('renders memory cards when data is available', () => {
      const props = createDefaultProps();
      render(<MemoryList {...props} />);

      expect(screen.getByText('Memory content 1')).toBeInTheDocument();
      expect(screen.getByText('Memory content 2')).toBeInTheDocument();
      expect(screen.getByText('Memory content 3')).toBeInTheDocument();
    });

    it('shows correct number of cards', () => {
      const memories = createMockMemories(5);
      const props = createDefaultProps({ memories });
      render(<MemoryList {...props} />);

      const rows = screen.getAllByRole('row');
      expect(rows).toHaveLength(5);
    });

    it('passes selection state to cards', () => {
      const memories = createMockMemories(3);
      const selectedIds = new Set(['test-id-1', 'test-id-3']);
      const props = createDefaultProps({ memories, selectedIds });
      render(<MemoryList {...props} />);

      const rows = screen.getAllByRole('row');
      expect(rows[0]).toHaveAttribute('aria-selected', 'true');
      expect(rows[1]).toHaveAttribute('aria-selected', 'false');
      expect(rows[2]).toHaveAttribute('aria-selected', 'true');
    });

    it('passes focused state to the correct card', () => {
      const memories = createMockMemories(3);
      const props = createDefaultProps({ memories, focusedIndex: 1 });
      render(<MemoryList {...props} />);

      const rows = screen.getAllByRole('row');
      // Focused row has tabindex=0, others have tabindex=-1
      expect(rows[0]).toHaveAttribute('tabindex', '-1');
      expect(rows[1]).toHaveAttribute('tabindex', '0');
      expect(rows[2]).toHaveAttribute('tabindex', '-1');
    });
  });

  describe('Accessibility', () => {
    it('has role="grid" on the list container', () => {
      const props = createDefaultProps();
      render(<MemoryList {...props} />);

      expect(screen.getByRole('grid')).toBeInTheDocument();
    });

    it('has aria-rowcount matching number of memories', () => {
      const memories = createMockMemories(4);
      const props = createDefaultProps({ memories });
      render(<MemoryList {...props} />);

      const grid = screen.getByRole('grid');
      expect(grid).toHaveAttribute('aria-rowcount', '4');
    });

    it('has aria-label on the grid', () => {
      const props = createDefaultProps();
      render(<MemoryList {...props} />);

      const grid = screen.getByRole('grid');
      expect(grid).toHaveAttribute('aria-label', 'Memory items');
    });

    it('has aria-live region for item count', () => {
      const memories = createMockMemories(3);
      const props = createDefaultProps({ memories });
      const { container } = render(<MemoryList {...props} />);

      const liveRegion = container.querySelector('[aria-live="polite"]');
      expect(liveRegion).toBeInTheDocument();
      expect(liveRegion).toHaveTextContent('3 memory items displayed');
    });

    it('uses singular form for single item', () => {
      const memories = createMockMemories(1);
      const props = createDefaultProps({ memories });
      const { container } = render(<MemoryList {...props} />);

      const liveRegion = container.querySelector('[aria-live="polite"]');
      expect(liveRegion).toHaveTextContent('1 memory item displayed');
    });
  });
});
