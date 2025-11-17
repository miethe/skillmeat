/**
 * MarketplaceListingDetail Component Tests
 *
 * Unit tests for the marketplace listing detail component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MarketplaceListingDetail } from '../MarketplaceListingDetail';
import type { ListingDetail } from '@/types/marketplace';

// Mock hooks
vi.mock('@/hooks/useMarketplace', () => ({
  useInstallListing: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: vi.fn(() => ({
    toast: vi.fn(),
  })),
}));

describe('MarketplaceListingDetail', () => {
  let queryClient: QueryClient;

  const mockListing: ListingDetail = {
    listing_id: 'test-1',
    name: 'Test Listing',
    description: 'A comprehensive test listing',
    category: 'skill',
    version: '1.0.0',
    publisher: {
      name: 'Test Publisher',
      email: 'test@example.com',
      website: 'https://example.com',
      verified: true,
    },
    license: 'MIT',
    tags: ['test', 'demo', 'example'],
    artifact_count: 5,
    downloads: 1000,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    homepage: 'https://example.com/project',
    repository: 'https://github.com/test/repo',
    source_url: 'https://marketplace.example.com/listing/test-1',
    bundle_url: 'https://marketplace.example.com/bundles/test-1.tar.gz',
    price: 0,
    signature: 'test-signature',
  };

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  const renderComponent = (listing = mockListing) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MarketplaceListingDetail listing={listing} />
      </QueryClientProvider>
    );
  };

  it('renders the listing name and version', () => {
    renderComponent();
    expect(screen.getByText('Test Listing')).toBeInTheDocument();
    expect(screen.getByText('v1.0.0')).toBeInTheDocument();
  });

  it('displays verified publisher badge', () => {
    renderComponent();
    expect(screen.getByText('Verified')).toBeInTheDocument();
  });

  it('shows the install button', () => {
    renderComponent();
    const installButton = screen.getByRole('button', { name: /install/i });
    expect(installButton).toBeInTheDocument();
  });

  it('displays listing description', () => {
    renderComponent();
    expect(screen.getByText('A comprehensive test listing')).toBeInTheDocument();
  });

  it('shows download count', () => {
    renderComponent();
    expect(screen.getByText('1K')).toBeInTheDocument();
  });

  it('displays artifact count', () => {
    renderComponent();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('shows license information', () => {
    renderComponent();
    expect(screen.getAllByText('MIT').length).toBeGreaterThan(0);
  });

  it('renders tags', () => {
    renderComponent();
    expect(screen.getByText('test')).toBeInTheDocument();
    expect(screen.getByText('demo')).toBeInTheDocument();
    expect(screen.getByText('example')).toBeInTheDocument();
  });

  it('displays free badge when price is 0', () => {
    renderComponent();
    expect(screen.getByText('Free')).toBeInTheDocument();
  });

  it('shows homepage link when available', () => {
    renderComponent();
    const homepageLink = screen.getByRole('link', { name: /homepage/i });
    expect(homepageLink).toHaveAttribute('href', 'https://example.com/project');
  });

  it('shows repository link when available', () => {
    renderComponent();
    const repoLink = screen.getByRole('link', { name: /repository/i });
    expect(repoLink).toHaveAttribute('href', 'https://github.com/test/repo');
  });

  it('opens trust prompt when install button is clicked', () => {
    renderComponent();
    const installButton = screen.getByRole('button', { name: /install/i });
    fireEvent.click(installButton);
    // Trust prompt should open
    expect(screen.getByText(/Install from Marketplace/i)).toBeInTheDocument();
  });
});
