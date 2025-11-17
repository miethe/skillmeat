/**
 * MarketplaceListingCatalog Component Tests
 *
 * Unit tests for the marketplace catalog component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MarketplaceListingCatalog } from '../MarketplaceListingCatalog';

// Mock the hooks
vi.mock('@/hooks/useMarketplace', () => ({
  useMarketplaceListings: vi.fn(() => ({
    data: {
      items: [
        {
          listing_id: '1',
          name: 'Test Listing',
          description: 'A test listing',
          category: 'skill',
          version: '1.0.0',
          publisher: {
            name: 'Test Publisher',
            verified: true,
          },
          license: 'MIT',
          tags: ['test', 'demo'],
          artifact_count: 3,
          downloads: 100,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      page_info: {
        has_next_page: false,
        has_previous_page: false,
        total_count: 1,
      },
    },
    isLoading: false,
    error: null,
  })),
}));

vi.mock('@/hooks/useMarketplaceFilters', () => ({
  useMarketplaceFilters: vi.fn(() => ({
    filters: {},
    sort: 'newest',
    page: 1,
    setFilters: vi.fn(),
    setSort: vi.fn(),
    setPage: vi.fn(),
    resetFilters: vi.fn(),
    clearSearch: vi.fn(),
  })),
}));

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('MarketplaceListingCatalog', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MarketplaceListingCatalog />
      </QueryClientProvider>
    );
  };

  it('renders the search input', () => {
    renderComponent();
    expect(screen.getByPlaceholderText('Search listings...')).toBeInTheDocument();
  });

  it('renders the sort dropdown', () => {
    renderComponent();
    expect(screen.getByLabelText('Sort listings')).toBeInTheDocument();
  });

  it('displays listing cards when data is loaded', () => {
    renderComponent();
    expect(screen.getByText('Test Listing')).toBeInTheDocument();
    expect(screen.getByText('A test listing')).toBeInTheDocument();
  });

  it('shows results count', () => {
    renderComponent();
    expect(screen.getByText(/1 result/)).toBeInTheDocument();
  });
});
