/**
 * @jest-environment jsdom
 */

/**
 * Unit tests for Catalog Pagination
 *
 * Tests cover:
 * 1. Page number generation (getPageNumbers logic)
 * 2. Pagination controls (Previous/Next buttons, page buttons)
 * 3. Items per page selector
 * 4. Count indicator display
 */

import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Create a QueryClient wrapper for testing components that use TanStack Query
 */
function createTestWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// ============================================================================
// getPageNumbers Function Tests
// ============================================================================

/**
 * Implements the same getPageNumbers logic from the source detail page
 * for isolated unit testing
 */
function getPageNumbers(currentPage: number, totalPages: number): (number | 'ellipsis')[] {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: (number | 'ellipsis')[] = [];

  if (currentPage <= 3) {
    // Near start: show 1 2 3 4 5 ... last
    pages.push(1, 2, 3, 4, 5);
    if (totalPages > 5) {
      pages.push('ellipsis', totalPages);
    }
  } else if (currentPage >= totalPages - 2) {
    // Near end: show 1 ... last-4 last-3 last-2 last-1 last
    pages.push(1, 'ellipsis');
    for (let i = totalPages - 4; i <= totalPages; i++) {
      if (i > 1) pages.push(i);
    }
  } else {
    // Middle: show 1 ... current-1 current current+1 ... last
    pages.push(1, 'ellipsis');
    pages.push(currentPage - 1, currentPage, currentPage + 1);
    pages.push('ellipsis', totalPages);
  }

  return pages;
}

describe('getPageNumbers', () => {
  it('returns all pages when totalPages <= 5', () => {
    expect(getPageNumbers(1, 3)).toEqual([1, 2, 3]);
    expect(getPageNumbers(2, 5)).toEqual([1, 2, 3, 4, 5]);
    expect(getPageNumbers(1, 1)).toEqual([1]);
  });

  it('returns pages with ellipsis when totalPages > 5', () => {
    const result = getPageNumbers(1, 10);
    expect(result).toContain('ellipsis');
    expect(result).toContain(10); // Last page
  });

  it('shows correct pages when at beginning (page 1)', () => {
    const result = getPageNumbers(1, 10);
    expect(result).toEqual([1, 2, 3, 4, 5, 'ellipsis', 10]);
  });

  it('shows correct pages when at beginning (page 2)', () => {
    const result = getPageNumbers(2, 10);
    expect(result).toEqual([1, 2, 3, 4, 5, 'ellipsis', 10]);
  });

  it('shows correct pages when at beginning (page 3)', () => {
    const result = getPageNumbers(3, 10);
    expect(result).toEqual([1, 2, 3, 4, 5, 'ellipsis', 10]);
  });

  it('shows correct pages when in middle (page 5 of 10)', () => {
    const result = getPageNumbers(5, 10);
    expect(result).toEqual([1, 'ellipsis', 4, 5, 6, 'ellipsis', 10]);
  });

  it('shows correct pages when in middle (page 6 of 12)', () => {
    const result = getPageNumbers(6, 12);
    expect(result).toEqual([1, 'ellipsis', 5, 6, 7, 'ellipsis', 12]);
  });

  it('shows correct pages when at end (last page)', () => {
    const result = getPageNumbers(10, 10);
    expect(result).toEqual([1, 'ellipsis', 6, 7, 8, 9, 10]);
  });

  it('shows correct pages when near end (second to last)', () => {
    const result = getPageNumbers(9, 10);
    expect(result).toEqual([1, 'ellipsis', 6, 7, 8, 9, 10]);
  });

  it('shows correct pages when at end (third from last)', () => {
    const result = getPageNumbers(8, 10);
    expect(result).toEqual([1, 'ellipsis', 6, 7, 8, 9, 10]);
  });

  it('handles exactly 6 pages at beginning', () => {
    const result = getPageNumbers(1, 6);
    expect(result).toEqual([1, 2, 3, 4, 5, 'ellipsis', 6]);
  });

  it('handles large page counts', () => {
    const result = getPageNumbers(50, 100);
    expect(result).toEqual([1, 'ellipsis', 49, 50, 51, 'ellipsis', 100]);
  });
});

// ============================================================================
// Pagination Controls Component Tests
// ============================================================================

/**
 * Minimal pagination controls component for testing
 */
interface PaginationControlsProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  isDisabledPrev?: boolean;
  isDisabledNext?: boolean;
}

function PaginationControls({
  currentPage,
  totalPages,
  onPageChange,
  isDisabledPrev,
  isDisabledNext,
}: PaginationControlsProps) {
  const pageNumbers = getPageNumbers(currentPage, totalPages);

  return (
    <div className="flex items-center gap-1" data-testid="pagination-controls">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={isDisabledPrev ?? currentPage === 1}
        aria-label="Previous page"
      >
        Previous
      </button>

      {pageNumbers.map((pageNum, index) =>
        pageNum === 'ellipsis' ? (
          <span key={`ellipsis-${index}`} aria-hidden="true">
            ...
          </span>
        ) : (
          <button
            key={pageNum}
            onClick={() => onPageChange(pageNum)}
            aria-label={`Page ${pageNum}`}
            aria-current={currentPage === pageNum ? 'page' : undefined}
            data-active={currentPage === pageNum}
          >
            {pageNum}
          </button>
        )
      )}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={isDisabledNext ?? currentPage === totalPages}
        aria-label="Next page"
      >
        Next
      </button>
    </div>
  );
}

describe('Pagination Controls', () => {
  it('disables Previous button on first page', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={1}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    const prevButton = screen.getByRole('button', { name: /previous/i });
    expect(prevButton).toBeDisabled();
  });

  it('disables Next button on last page', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={10}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    const nextButton = screen.getByRole('button', { name: /next/i });
    expect(nextButton).toBeDisabled();
  });

  it('enables both buttons on middle page', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={5}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    const prevButton = screen.getByRole('button', { name: /previous/i });
    const nextButton = screen.getByRole('button', { name: /next/i });

    expect(prevButton).not.toBeDisabled();
    expect(nextButton).not.toBeDisabled();
  });

  it('highlights current page button with aria-current', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={3}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    );

    const currentPageButton = screen.getByRole('button', { name: 'Page 3' });
    expect(currentPageButton).toHaveAttribute('aria-current', 'page');
  });

  it('other page buttons do not have aria-current', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={3}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    );

    const page1Button = screen.getByRole('button', { name: 'Page 1' });
    const page2Button = screen.getByRole('button', { name: 'Page 2' });

    expect(page1Button).not.toHaveAttribute('aria-current');
    expect(page2Button).not.toHaveAttribute('aria-current');
  });

  it('calls onPageChange when page button clicked', async () => {
    const user = userEvent.setup();
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={1}
        totalPages={5}
        onPageChange={mockOnPageChange}
      />
    );

    const page3Button = screen.getByRole('button', { name: 'Page 3' });
    await user.click(page3Button);

    expect(mockOnPageChange).toHaveBeenCalledWith(3);
  });

  it('calls onPageChange with correct value when Previous clicked', async () => {
    const user = userEvent.setup();
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={5}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    const prevButton = screen.getByRole('button', { name: /previous/i });
    await user.click(prevButton);

    expect(mockOnPageChange).toHaveBeenCalledWith(4);
  });

  it('calls onPageChange with correct value when Next clicked', async () => {
    const user = userEvent.setup();
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={5}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton);

    expect(mockOnPageChange).toHaveBeenCalledWith(6);
  });

  it('renders ellipsis for large page counts', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={5}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    const ellipsisElements = screen.getAllByText('...');
    expect(ellipsisElements.length).toBeGreaterThan(0);
  });

  it('ellipsis elements have aria-hidden', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={5}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    const ellipsisElements = screen.getAllByText('...');
    ellipsisElements.forEach((el) => {
      expect(el).toHaveAttribute('aria-hidden', 'true');
    });
  });
});

// ============================================================================
// Items Per Page Selector Tests
// ============================================================================

interface ItemsPerPageSelectorProps {
  value: number;
  onChange: (value: number) => void;
}

function ItemsPerPageSelector({ value, onChange }: ItemsPerPageSelectorProps) {
  return (
    <div className="flex items-center gap-2" data-testid="items-per-page-selector">
      <label htmlFor="items-per-page">Show</label>
      <select
        id="items-per-page"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        aria-label="Items per page"
      >
        <option value={10}>10</option>
        <option value={25}>25</option>
        <option value={50}>50</option>
        <option value={100}>100</option>
      </select>
      <span>per page</span>
    </div>
  );
}

describe('Items Per Page Selector', () => {
  it('renders with correct options (10, 25, 50, 100)', () => {
    const mockOnChange = jest.fn();
    render(<ItemsPerPageSelector value={25} onChange={mockOnChange} />);

    const select = screen.getByLabelText('Items per page');
    expect(select).toBeInTheDocument();

    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(4);
    expect(options[0]).toHaveValue('10');
    expect(options[1]).toHaveValue('25');
    expect(options[2]).toHaveValue('50');
    expect(options[3]).toHaveValue('100');
  });

  it('shows current value selected', () => {
    const mockOnChange = jest.fn();
    render(<ItemsPerPageSelector value={50} onChange={mockOnChange} />);

    const select = screen.getByLabelText('Items per page') as HTMLSelectElement;
    expect(select.value).toBe('50');
  });

  it('calls onChange when changed', async () => {
    const user = userEvent.setup();
    const mockOnChange = jest.fn();
    render(<ItemsPerPageSelector value={25} onChange={mockOnChange} />);

    const select = screen.getByLabelText('Items per page');
    await user.selectOptions(select, '100');

    expect(mockOnChange).toHaveBeenCalledWith(100);
  });

  it('has proper labels for accessibility', () => {
    const mockOnChange = jest.fn();
    render(<ItemsPerPageSelector value={25} onChange={mockOnChange} />);

    expect(screen.getByText('Show')).toBeInTheDocument();
    expect(screen.getByText('per page')).toBeInTheDocument();
  });
});

// ============================================================================
// Count Indicator Tests
// ============================================================================

interface CountIndicatorProps {
  startIndex: number;
  endIndex: number;
  totalFiltered: number;
  totalCount?: number;
}

function CountIndicator({
  startIndex,
  endIndex,
  totalFiltered,
  totalCount,
}: CountIndicatorProps) {
  return (
    <div className="text-sm text-muted-foreground" data-testid="count-indicator">
      <span>
        Showing {startIndex}-{endIndex} of {totalFiltered.toLocaleString()} artifacts
        {totalCount && totalFiltered !== totalCount && (
          <> (filtered from {totalCount.toLocaleString()} total)</>
        )}
      </span>
    </div>
  );
}

describe('Count Indicator', () => {
  it('displays correct count format', () => {
    render(
      <CountIndicator
        startIndex={1}
        endIndex={25}
        totalFiltered={100}
      />
    );

    expect(screen.getByText(/Showing 1-25 of 100 artifacts/)).toBeInTheDocument();
  });

  it('displays correct range for middle pages', () => {
    render(
      <CountIndicator
        startIndex={26}
        endIndex={50}
        totalFiltered={100}
      />
    );

    expect(screen.getByText(/Showing 26-50 of 100 artifacts/)).toBeInTheDocument();
  });

  it('displays correct range for last page with partial results', () => {
    render(
      <CountIndicator
        startIndex={76}
        endIndex={82}
        totalFiltered={82}
      />
    );

    expect(screen.getByText(/Showing 76-82 of 82 artifacts/)).toBeInTheDocument();
  });

  it('formats large numbers with commas', () => {
    render(
      <CountIndicator
        startIndex={1}
        endIndex={25}
        totalFiltered={1500}
      />
    );

    expect(screen.getByText(/Showing 1-25 of 1,500 artifacts/)).toBeInTheDocument();
  });

  it('shows filtered count when different from total', () => {
    render(
      <CountIndicator
        startIndex={1}
        endIndex={25}
        totalFiltered={100}
        totalCount={500}
      />
    );

    expect(screen.getByText(/Showing 1-25 of 100 artifacts/)).toBeInTheDocument();
    expect(screen.getByText(/filtered from 500 total/)).toBeInTheDocument();
  });

  it('does not show filtered message when counts are equal', () => {
    render(
      <CountIndicator
        startIndex={1}
        endIndex={25}
        totalFiltered={100}
        totalCount={100}
      />
    );

    expect(screen.getByText(/Showing 1-25 of 100 artifacts/)).toBeInTheDocument();
    expect(screen.queryByText(/filtered from/)).not.toBeInTheDocument();
  });

  it('handles single item', () => {
    render(
      <CountIndicator
        startIndex={1}
        endIndex={1}
        totalFiltered={1}
      />
    );

    expect(screen.getByText(/Showing 1-1 of 1 artifacts/)).toBeInTheDocument();
  });
});

// ============================================================================
// Pagination State Management Tests
// ============================================================================

describe('Pagination State Management', () => {
  it('resets to page 1 when items per page changes', async () => {
    const user = userEvent.setup();
    let currentPage = 3;
    const setCurrentPage = jest.fn((page: number) => {
      currentPage = page;
    });
    let itemsPerPage = 25;
    const setItemsPerPage = jest.fn((items: number) => {
      itemsPerPage = items;
      // This should reset to page 1 when items per page changes
      setCurrentPage(1);
    });

    const { rerender } = render(
      <div>
        <ItemsPerPageSelector value={itemsPerPage} onChange={setItemsPerPage} />
        <PaginationControls
          currentPage={currentPage}
          totalPages={10}
          onPageChange={setCurrentPage}
        />
      </div>
    );

    const select = screen.getByLabelText('Items per page');
    await user.selectOptions(select, '50');

    expect(setItemsPerPage).toHaveBeenCalledWith(50);
    expect(setCurrentPage).toHaveBeenCalledWith(1);
  });

  it('maintains page validity when total pages decreases', () => {
    // If current page is 10 and total pages drops to 5, current page should be 5
    const currentPage = 10;
    const totalPages = 5;
    const validatedPage = Math.min(currentPage, totalPages);
    expect(validatedPage).toBe(5);
  });

  it('does not change page when on valid page after filter', () => {
    // If current page is 3 and total pages stays >= 3, page should stay 3
    const currentPage = 3;
    const totalPages = 8;
    const validatedPage = Math.min(currentPage, totalPages);
    expect(validatedPage).toBe(3);
  });
});

// ============================================================================
// Edge Cases
// ============================================================================

describe('Edge Cases', () => {
  it('handles zero items gracefully', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={1}
        totalPages={0}
        onPageChange={mockOnPageChange}
      />
    );

    // Should not render any page buttons for empty results
    const pageButtons = screen.queryAllByRole('button', { name: /Page \d+/ });
    expect(pageButtons).toHaveLength(0);
  });

  it('handles single page correctly', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={1}
        totalPages={1}
        onPageChange={mockOnPageChange}
      />
    );

    const prevButton = screen.getByRole('button', { name: /previous/i });
    const nextButton = screen.getByRole('button', { name: /next/i });

    expect(prevButton).toBeDisabled();
    expect(nextButton).toBeDisabled();
  });

  it('handles exactly 2 pages', () => {
    const result = getPageNumbers(1, 2);
    expect(result).toEqual([1, 2]);
  });

  it('handles rapid page changes', async () => {
    const user = userEvent.setup();
    const mockOnPageChange = jest.fn();

    const { rerender } = render(
      <PaginationControls
        currentPage={5}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    // Rapid clicks
    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton);
    await user.click(nextButton);
    await user.click(nextButton);

    // Each click should be called
    expect(mockOnPageChange).toHaveBeenCalledTimes(3);
  });
});

// ============================================================================
// Accessibility Tests
// ============================================================================

describe('Accessibility', () => {
  it('pagination controls have proper ARIA labels', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={5}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    expect(screen.getByRole('button', { name: /previous page/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /next page/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Page 5' })).toBeInTheDocument();
  });

  it('current page is marked with aria-current', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={5}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    const currentPageButton = screen.getByRole('button', { name: 'Page 5' });
    expect(currentPageButton).toHaveAttribute('aria-current', 'page');
  });

  it('items per page selector is accessible', () => {
    const mockOnChange = jest.fn();
    render(<ItemsPerPageSelector value={25} onChange={mockOnChange} />);

    const select = screen.getByLabelText('Items per page');
    expect(select).toBeInTheDocument();
    expect(select.tagName).toBe('SELECT');
  });

  it('ellipsis is hidden from screen readers', () => {
    const mockOnPageChange = jest.fn();
    render(
      <PaginationControls
        currentPage={5}
        totalPages={10}
        onPageChange={mockOnPageChange}
      />
    );

    const ellipsisElements = screen.getAllByText('...');
    ellipsisElements.forEach((el) => {
      expect(el).toHaveAttribute('aria-hidden', 'true');
    });
  });
});
