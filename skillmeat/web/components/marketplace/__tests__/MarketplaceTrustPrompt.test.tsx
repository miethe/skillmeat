/**
 * MarketplaceTrustPrompt Component Tests
 *
 * Unit tests for the security trust prompt dialog
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MarketplaceTrustPrompt } from '../MarketplaceTrustPrompt';
import type { ListingDetail } from '@/types/marketplace';

describe('MarketplaceTrustPrompt', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnConfirm = vi.fn();

  const createMockListing = (overrides = {}): ListingDetail => ({
    listing_id: 'test-1',
    name: 'Test Listing',
    description: 'A test listing',
    category: 'skill',
    version: '1.0.0',
    publisher: {
      name: 'Test Publisher',
      verified: true,
    },
    license: 'MIT',
    tags: ['test'],
    artifact_count: 3,
    downloads: 100,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    source_url: 'https://marketplace.example.com/listing/test-1',
    bundle_url: 'https://marketplace.example.com/bundles/test-1.tar.gz',
    price: 0,
    signature: 'test-signature',
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (listing: ListingDetail, open = true) => {
    return render(
      <MarketplaceTrustPrompt
        listing={listing}
        open={open}
        onOpenChange={mockOnOpenChange}
        onConfirm={mockOnConfirm}
      />
    );
  };

  it('displays high trust level for verified publisher with signature', () => {
    const listing = createMockListing({
      publisher: { name: 'Test', verified: true },
      signature: 'test-sig',
    });
    renderComponent(listing);
    expect(screen.getByText('High Trust Level')).toBeInTheDocument();
  });

  it('displays medium trust level for verified publisher without signature', () => {
    const listing = createMockListing({
      publisher: { name: 'Test', verified: true },
      signature: undefined,
    });
    renderComponent(listing);
    expect(screen.getByText('Medium Trust Level')).toBeInTheDocument();
  });

  it('displays low trust level for unverified publisher without signature', () => {
    const listing = createMockListing({
      publisher: { name: 'Test', verified: false },
      signature: undefined,
    });
    renderComponent(listing);
    expect(screen.getByText('Low Trust Level')).toBeInTheDocument();
  });

  it('shows publisher information', () => {
    const listing = createMockListing({
      publisher: {
        name: 'Awesome Publisher',
        verified: true,
        website: 'https://example.com',
      },
    });
    renderComponent(listing);
    expect(screen.getByText('Awesome Publisher')).toBeInTheDocument();
    expect(screen.getByText('example.com')).toBeInTheDocument();
  });

  it('displays license information', () => {
    const listing = createMockListing({ license: 'Apache-2.0' });
    renderComponent(listing);
    expect(screen.getByText('Apache-2.0')).toBeInTheDocument();
  });

  it('shows signature verification checkbox when signature exists', () => {
    const listing = createMockListing({ signature: 'test-sig' });
    renderComponent(listing);
    expect(screen.getByLabelText(/Verify cryptographic signature/i)).toBeInTheDocument();
  });

  it('does not show signature verification checkbox when no signature', () => {
    const listing = createMockListing({ signature: undefined });
    renderComponent(listing);
    expect(screen.queryByLabelText(/Verify cryptographic signature/i)).not.toBeInTheDocument();
  });

  it('requires acknowledgment checkbox to be checked before installing', () => {
    const listing = createMockListing();
    renderComponent(listing);

    const installButton = screen.getByRole('button', { name: /^Install$/ });
    expect(installButton).toBeDisabled();

    const acknowledgmentCheckbox = screen.getByLabelText(/I understand the risks/i);
    fireEvent.click(acknowledgmentCheckbox);

    expect(installButton).not.toBeDisabled();
  });

  it('calls onConfirm with signature verification when install is clicked', () => {
    const listing = createMockListing({ signature: 'test-sig' });
    renderComponent(listing);

    // Check acknowledgment
    const acknowledgmentCheckbox = screen.getByLabelText(/I understand the risks/i);
    fireEvent.click(acknowledgmentCheckbox);

    // Click install
    const installButton = screen.getByRole('button', { name: /^Install$/ });
    fireEvent.click(installButton);

    expect(mockOnConfirm).toHaveBeenCalledWith(true);
  });

  it('allows disabling signature verification', () => {
    const listing = createMockListing({ signature: 'test-sig' });
    renderComponent(listing);

    // Uncheck signature verification
    const signatureCheckbox = screen.getByLabelText(/Verify cryptographic signature/i);
    fireEvent.click(signatureCheckbox);

    // Check acknowledgment
    const acknowledgmentCheckbox = screen.getByLabelText(/I understand the risks/i);
    fireEvent.click(acknowledgmentCheckbox);

    // Click install
    const installButton = screen.getByRole('button', { name: /^Install$/ });
    fireEvent.click(installButton);

    expect(mockOnConfirm).toHaveBeenCalledWith(false);
  });

  it('displays security warnings', () => {
    const listing = createMockListing();
    renderComponent(listing);
    expect(screen.getByText(/Important Security Notice/i)).toBeInTheDocument();
    expect(screen.getByText(/Artifacts can execute code/i)).toBeInTheDocument();
    expect(screen.getByText(/Only install from publishers you trust/i)).toBeInTheDocument();
  });

  it('shows cancel button that calls onOpenChange', () => {
    const listing = createMockListing();
    renderComponent(listing);

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('disables buttons when installing', () => {
    const listing = createMockListing();
    render(
      <MarketplaceTrustPrompt
        listing={listing}
        open={true}
        onOpenChange={mockOnOpenChange}
        onConfirm={mockOnConfirm}
        isInstalling={true}
      />
    );

    // Check acknowledgment first
    const acknowledgmentCheckbox = screen.getByLabelText(/I understand the risks/i);
    fireEvent.click(acknowledgmentCheckbox);

    const installButton = screen.getByRole('button', { name: /Installing/i });
    const cancelButton = screen.getByRole('button', { name: /Cancel/i });

    expect(installButton).toBeDisabled();
    expect(cancelButton).toBeDisabled();
  });

  it('shows free indicator when price is 0', () => {
    const listing = createMockListing({ price: 0 });
    renderComponent(listing);
    expect(screen.getByText('✓')).toBeInTheDocument();
  });
});
