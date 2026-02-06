/**
 * @jest-environment jsdom
 *
 * Tests for ArtifactLinkingDialog component.
 *
 * Note: Complex interactions with Radix UI Select components (type filter, link type)
 * are better tested via E2E tests due to jsdom limitations with pointer capture and
 * scroll APIs. This test file focuses on core functionality that works reliably in jsdom.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ArtifactLinkingDialog } from '@/components/entity/artifact-linking-dialog';

// Mock useDebounce hook to return immediate value
jest.mock('@/hooks', () => ({
  useDebounce: (value: string, _delay: number) => value,
}));

// Mock DOM APIs that Radix UI components require in jsdom
beforeAll(() => {
  // @ts-ignore
  Element.prototype.hasPointerCapture = jest.fn(() => false);
  // @ts-ignore
  Element.prototype.setPointerCapture = jest.fn();
  // @ts-ignore
  Element.prototype.releasePointerCapture = jest.fn();
  // @ts-ignore
  Element.prototype.scrollIntoView = jest.fn();
});

// Create fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

// Wrapper with providers
function createWrapper() {
  const queryClient = createTestQueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('ArtifactLinkingDialog', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe('Dialog Open/Close', () => {
    it('renders dialog when open is true', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      expect(screen.getByText('Link Artifact')).toBeInTheDocument();
      expect(screen.getByText(/Search for an artifact to link/i)).toBeInTheDocument();
    });

    it('does not render dialog when open is false', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={false}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      expect(screen.queryByText('Link Artifact')).not.toBeInTheDocument();
    });

    it('calls onOpenChange when Cancel button is clicked', async () => {
      const user = userEvent.setup();
      const Wrapper = createWrapper();
      const handleOpenChange = jest.fn();

      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={handleOpenChange}
          />
        </Wrapper>
      );

      await user.click(screen.getByRole('button', { name: /Cancel/i }));
      expect(handleOpenChange).toHaveBeenCalledWith(false);
    });

    it('resets form state when dialog reopens', async () => {
      const Wrapper = createWrapper();
      const { rerender } = render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      // Type in search
      const searchInput = screen.getByPlaceholderText('Type to search artifacts...');
      fireEvent.change(searchInput, { target: { value: 'test search' } });
      expect(searchInput).toHaveValue('test search');

      // Close dialog
      rerender(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={false}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      // Reopen dialog
      rerender(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      // Search input should be cleared
      const newSearchInput = screen.getByPlaceholderText('Type to search artifacts...');
      expect(newSearchInput).toHaveValue('');
    });
  });

  describe('Search Input', () => {
    it('renders search input with correct placeholder', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      expect(screen.getByPlaceholderText('Type to search artifacts...')).toBeInTheDocument();
    });

    it('shows "Type to search" message before typing', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      expect(screen.getByText('Type to search for artifacts')).toBeInTheDocument();
    });

    it('triggers search API call when user types', async () => {
      const user = userEvent.setup();
      const Wrapper = createWrapper();

      // Mock a slow fetch to ensure we catch the call
      (global.fetch as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(() => {
              resolve({
                ok: true,
                json: () => Promise.resolve({ items: [], page_info: { total_count: 0 } }),
              });
            }, 100)
          )
      );

      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      const searchInput = screen.getByPlaceholderText('Type to search artifacts...');
      await user.type(searchInput, 'python');

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });

      // Verify the URL contains a search parameter (first character due to debounce mock)
      const fetchCall = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(fetchCall).toContain('search=');
    });

    it('shows "No artifacts found" when search returns empty', async () => {
      const user = userEvent.setup();
      const Wrapper = createWrapper();

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ items: [], page_info: { total_count: 0 } }),
      });

      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      const searchInput = screen.getByPlaceholderText('Type to search artifacts...');
      await user.type(searchInput, 'nonexistent');

      await waitFor(() => {
        expect(screen.getByText('No artifacts found')).toBeInTheDocument();
      });
    });
  });

  describe('Type Filter', () => {
    it('renders type filter dropdown with default "All Types"', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      expect(screen.getByText('All Types')).toBeInTheDocument();
    });
  });

  describe('Link Type Selector', () => {
    it('renders link type dropdown with default "Related"', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      // Find the link type trigger button and check its text
      const linkTypeTrigger = screen.getByRole('combobox', { name: /Relationship Type/i });
      expect(linkTypeTrigger).toHaveTextContent('Related');
    });
  });

  describe('Create Link Button', () => {
    it('Create Link button is disabled when no artifact is selected', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      const createButton = screen.getByRole('button', { name: /Create Link/i });
      expect(createButton).toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    it('has proper dialog title', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      expect(screen.getByText('Link Artifact')).toBeInTheDocument();
    });

    it('has proper dialog description', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      expect(
        screen.getByText(/Search for an artifact to link. Choose the relationship type/i)
      ).toBeInTheDocument();
    });

    it('form inputs have proper labels', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      expect(screen.getByLabelText('Search Artifacts')).toBeInTheDocument();
      expect(screen.getByLabelText('Filter by Type')).toBeInTheDocument();
      expect(screen.getByLabelText('Relationship Type')).toBeInTheDocument();
    });

    it('search input can receive focus', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ArtifactLinkingDialog
            artifactId="source-artifact"
            open={true}
            onOpenChange={jest.fn()}
          />
        </Wrapper>
      );

      const searchInput = screen.getByPlaceholderText('Type to search artifacts...');
      // The input should be focusable (no disabled attribute)
      expect(searchInput).not.toBeDisabled();
      expect(searchInput).toBeInTheDocument();
    });
  });
});
