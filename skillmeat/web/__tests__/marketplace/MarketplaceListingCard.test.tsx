/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { MarketplaceListingCard } from '@/components/marketplace/MarketplaceListingCard';
import type { MarketplaceListing } from '@/types/marketplace';

const mockListing: MarketplaceListing = {
  listing_id: 'test-listing-123',
  name: 'Test Bundle',
  publisher: 'Test Publisher',
  license: 'MIT',
  artifact_count: 5,
  tags: ['testing', 'python', 'productivity'],
  created_at: '2025-01-15T10:00:00Z',
  source_url: 'https://marketplace.test/listings/123',
  description: 'A test bundle for unit testing',
  version: '1.0.0',
  downloads: 42,
  rating: 4.5,
  price: 0,
};

describe('MarketplaceListingCard', () => {
  it('renders listing data correctly', () => {
    render(<MarketplaceListingCard listing={mockListing} />);

    expect(screen.getByText('Test Bundle')).toBeInTheDocument();
    expect(screen.getByText('by Test Publisher')).toBeInTheDocument();
    expect(screen.getByText('MIT')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('4.5')).toBeInTheDocument();
    expect(screen.getByText('Free')).toBeInTheDocument();
  });

  it('displays description', () => {
    render(<MarketplaceListingCard listing={mockListing} />);

    expect(screen.getByText('A test bundle for unit testing')).toBeInTheDocument();
  });

  it('displays tags (limited to 3)', () => {
    render(<MarketplaceListingCard listing={mockListing} />);

    expect(screen.getByText('testing')).toBeInTheDocument();
    expect(screen.getByText('python')).toBeInTheDocument();
    expect(screen.getByText('productivity')).toBeInTheDocument();
  });

  it('shows +N more badge when more than 3 tags', () => {
    const listingWithManyTags = {
      ...mockListing,
      tags: ['tag1', 'tag2', 'tag3', 'tag4', 'tag5'],
    };

    render(<MarketplaceListingCard listing={listingWithManyTags} />);

    expect(screen.getByText('+2 more')).toBeInTheDocument();
  });

  it('calls onClick when card is clicked', () => {
    const handleClick = jest.fn();
    render(<MarketplaceListingCard listing={mockListing} onClick={handleClick} />);

    const card = screen.getByRole('button', { name: /view listing/i });
    fireEvent.click(card);

    expect(handleClick).toHaveBeenCalledWith(mockListing);
  });

  it('calls onClick when Enter key is pressed', () => {
    const handleClick = jest.fn();
    render(<MarketplaceListingCard listing={mockListing} onClick={handleClick} />);

    const card = screen.getByRole('button', { name: /view listing/i });
    fireEvent.keyDown(card, { key: 'Enter' });

    expect(handleClick).toHaveBeenCalledWith(mockListing);
  });

  it('displays price for paid listings', () => {
    const paidListing = { ...mockListing, price: 999 };
    render(<MarketplaceListingCard listing={paidListing} />);

    expect(screen.getByText('$9.99')).toBeInTheDocument();
    expect(screen.queryByText('Free')).not.toBeInTheDocument();
  });

  it('has accessible button label', () => {
    render(<MarketplaceListingCard listing={mockListing} />);

    expect(screen.getByRole('button', { name: 'View listing: Test Bundle' })).toBeInTheDocument();
  });
});
