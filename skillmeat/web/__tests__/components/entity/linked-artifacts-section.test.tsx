/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  LinkedArtifactsSection,
  type LinkedArtifactReference,
} from '@/components/entity/linked-artifacts-section';

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

// Mock linked artifacts
const mockLinkedArtifacts: LinkedArtifactReference[] = [
  {
    artifact_id: 'artifact-1',
    artifact_name: 'python-utils',
    artifact_type: 'skill',
    link_type: 'requires',
    source_name: 'user/repo/python-utils',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    artifact_id: 'artifact-2',
    artifact_name: 'documentation-helper',
    artifact_type: 'command',
    link_type: 'enables',
    source_name: 'user/repo/doc-helper',
  },
  {
    artifact_id: 'artifact-3',
    artifact_name: 'testing-framework',
    artifact_type: 'agent',
    link_type: 'related',
  },
];

// Mock unlinked references
const mockUnlinkedReferences = ['unknown-tool', 'missing-skill', 'deprecated-helper'];

describe('LinkedArtifactsSection', () => {
  // Mock fetch for delete operations
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe('Rendering', () => {
    it('renders linked artifacts grid correctly', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      // Check section heading
      expect(screen.getByText('Linked Artifacts')).toBeInTheDocument();
      expect(screen.getByText('(3)')).toBeInTheDocument();

      // Check all artifacts are rendered
      expect(screen.getByText('python-utils')).toBeInTheDocument();
      expect(screen.getByText('documentation-helper')).toBeInTheDocument();
      expect(screen.getByText('testing-framework')).toBeInTheDocument();
    });

    it('displays artifact types correctly', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      expect(screen.getByText('skill')).toBeInTheDocument();
      expect(screen.getByText('command')).toBeInTheDocument();
      expect(screen.getByText('agent')).toBeInTheDocument();
    });

    it('displays link types with correct labels', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      expect(screen.getByText('Requires')).toBeInTheDocument();
      expect(screen.getByText('Enables')).toBeInTheDocument();
      expect(screen.getByText('Related')).toBeInTheDocument();
    });

    it('renders artifact names as links when artifact_id is present', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      // All three have artifact_ids, so should be links
      const artifactLinks = screen.getAllByRole('link');
      expect(artifactLinks).toHaveLength(3);
      expect(artifactLinks[0]).toHaveAttribute('href', '/artifacts/artifact-1');
    });

    it('renders artifact names as plain text when artifact_id is missing', () => {
      const Wrapper = createWrapper();
      const artifactsWithoutIds: LinkedArtifactReference[] = [
        {
          artifact_name: 'unresolved-artifact',
          artifact_type: 'skill',
          link_type: 'requires',
        },
      ];

      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={artifactsWithoutIds} />
        </Wrapper>
      );

      // Should not be a link
      expect(screen.queryByRole('link', { name: /unresolved-artifact/i })).not.toBeInTheDocument();
      expect(screen.getByText('unresolved-artifact')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty state when no linked artifacts', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={[]} />
        </Wrapper>
      );

      expect(screen.getByText('No linked artifacts')).toBeInTheDocument();
      expect(
        screen.getByText('This artifact has no dependencies or relationships with other artifacts.')
      ).toBeInTheDocument();
    });

    it('shows empty state when linkedArtifacts is undefined', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" />
        </Wrapper>
      );

      expect(screen.getByText('No linked artifacts')).toBeInTheDocument();
    });

    it('shows "Add First Link" button in empty state when onAddLinkClick provided', () => {
      const Wrapper = createWrapper();
      const handleAddLink = jest.fn();

      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            linkedArtifacts={[]}
            onAddLinkClick={handleAddLink}
          />
        </Wrapper>
      );

      const addButton = screen.getByRole('button', { name: /Add First Link/i });
      expect(addButton).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('displays skeleton cards when loading', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" isLoading={true} />
        </Wrapper>
      );

      // Should show loading skeleton with aria-busy
      const loadingContainer = screen.getByLabelText('Loading linked artifacts');
      expect(loadingContainer).toHaveAttribute('aria-busy', 'true');

      // Should show 3 skeleton cards
      const skeletonCards = loadingContainer.querySelectorAll('.animate-pulse');
      expect(skeletonCards).toHaveLength(3);
    });

    it('does not show artifacts during loading state', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            linkedArtifacts={mockLinkedArtifacts}
            isLoading={true}
          />
        </Wrapper>
      );

      // Artifacts should not be visible when loading
      expect(screen.queryByText('python-utils')).not.toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('shows error message when error prop is provided', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            error="Failed to load linked artifacts"
          />
        </Wrapper>
      );

      expect(screen.getByText('Failed to load linked artifacts')).toBeInTheDocument();
    });

    it('shows retry button when onRetry is provided', () => {
      const Wrapper = createWrapper();
      const handleRetry = jest.fn();

      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            error="Failed to load"
            onRetry={handleRetry}
          />
        </Wrapper>
      );

      const retryButton = screen.getByRole('button', { name: /Retry loading linked artifacts/i });
      expect(retryButton).toBeInTheDocument();
    });

    it('calls onRetry when retry button is clicked', async () => {
      const user = userEvent.setup();
      const Wrapper = createWrapper();
      const handleRetry = jest.fn();

      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            error="Failed to load"
            onRetry={handleRetry}
          />
        </Wrapper>
      );

      await user.click(screen.getByRole('button', { name: /Retry/i }));
      expect(handleRetry).toHaveBeenCalledTimes(1);
    });

    it('does not show retry button when onRetry is not provided', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" error="Failed to load" />
        </Wrapper>
      );

      expect(screen.queryByRole('button', { name: /Retry/i })).not.toBeInTheDocument();
    });
  });

  describe('Add Link Button', () => {
    it('shows "Add Link" button when onAddLinkClick is provided', () => {
      const Wrapper = createWrapper();
      const handleAddLink = jest.fn();

      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            linkedArtifacts={mockLinkedArtifacts}
            onAddLinkClick={handleAddLink}
          />
        </Wrapper>
      );

      const addButton = screen.getByRole('button', { name: /Add artifact link/i });
      expect(addButton).toBeInTheDocument();
    });

    it('calls onAddLinkClick when Add Link button is clicked', async () => {
      const user = userEvent.setup();
      const Wrapper = createWrapper();
      const handleAddLink = jest.fn();

      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            linkedArtifacts={mockLinkedArtifacts}
            onAddLinkClick={handleAddLink}
          />
        </Wrapper>
      );

      await user.click(screen.getByRole('button', { name: /Add artifact link/i }));
      expect(handleAddLink).toHaveBeenCalledTimes(1);
    });

    it('does not show Add Link button when onAddLinkClick is not provided', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            linkedArtifacts={mockLinkedArtifacts}
          />
        </Wrapper>
      );

      expect(screen.queryByRole('button', { name: /Add artifact link/i })).not.toBeInTheDocument();
    });
  });

  describe('Delete Link Functionality', () => {
    it('shows delete button on each artifact card with artifact_id', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      // Each artifact with an ID should have a delete button
      const deleteButtons = screen.getAllByRole('button', { name: /Remove link to/i });
      expect(deleteButtons).toHaveLength(3);
    });

    it('opens confirmation dialog when delete button is clicked', async () => {
      const user = userEvent.setup();
      const Wrapper = createWrapper();

      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      // Click delete button for first artifact
      const deleteButton = screen.getByRole('button', { name: /Remove link to python-utils/i });
      await user.click(deleteButton);

      // Confirmation dialog should appear
      expect(screen.getByText('Remove Artifact Link')).toBeInTheDocument();
      expect(screen.getByText(/Are you sure you want to remove the link to/)).toBeInTheDocument();
      // python-utils appears twice: once in list, once in dialog - use getAllByText
      const pythonUtilsElements = screen.getAllByText('python-utils');
      expect(pythonUtilsElements.length).toBeGreaterThanOrEqual(2);
    });

    it('calls delete API and onLinkDeleted when confirmed', async () => {
      const user = userEvent.setup();
      const Wrapper = createWrapper();
      const handleLinkDeleted = jest.fn();

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      });

      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            linkedArtifacts={mockLinkedArtifacts}
            onLinkDeleted={handleLinkDeleted}
          />
        </Wrapper>
      );

      // Open delete dialog
      await user.click(screen.getByRole('button', { name: /Remove link to python-utils/i }));

      // Confirm deletion
      const removeButton = screen.getByRole('button', { name: /Remove Link/i });
      await user.click(removeButton);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/artifacts/source-artifact/linked-artifacts/artifact-1'),
          expect.objectContaining({ method: 'DELETE' })
        );
      });

      await waitFor(() => {
        expect(handleLinkDeleted).toHaveBeenCalled();
      });
    });

    it('closes dialog when Cancel is clicked', async () => {
      const user = userEvent.setup();
      const Wrapper = createWrapper();

      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      // Open delete dialog
      await user.click(screen.getByRole('button', { name: /Remove link to python-utils/i }));
      expect(screen.getByText('Remove Artifact Link')).toBeInTheDocument();

      // Click cancel
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      await user.click(cancelButton);

      // Dialog should close
      await waitFor(() => {
        expect(screen.queryByText('Remove Artifact Link')).not.toBeInTheDocument();
      });
    });

    it('handles API error during deletion', async () => {
      const user = userEvent.setup();
      const Wrapper = createWrapper();

      // Mock fetch to return an error
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Failed to delete link' }),
      });

      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      // Open delete dialog
      await user.click(screen.getByRole('button', { name: /Remove link to python-utils/i }));

      // Confirm deletion - this starts the mutation which will fail
      const removeButton = screen.getByRole('button', { name: /^Remove Link$/i });
      await user.click(removeButton);

      // The dialog should still be present (doesn't close on error)
      // and the artifact should still be in the list
      await waitFor(() => {
        expect(screen.getByText('python-utils')).toBeInTheDocument();
      });
    });
  });

  describe('Unlinked References Section', () => {
    it('displays unlinked references when provided', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            linkedArtifacts={mockLinkedArtifacts}
            unlinkedReferences={mockUnlinkedReferences}
          />
        </Wrapper>
      );

      expect(screen.getByText('Unresolved References')).toBeInTheDocument();
      // There are two (3) counts: one for linked artifacts, one for unlinked references
      const countElements = screen.getAllByText('(3)');
      expect(countElements.length).toBe(2);
      expect(screen.getByText('unknown-tool')).toBeInTheDocument();
      expect(screen.getByText('missing-skill')).toBeInTheDocument();
      expect(screen.getByText('deprecated-helper')).toBeInTheDocument();
    });

    it('shows explanation text for unlinked references', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            unlinkedReferences={mockUnlinkedReferences}
          />
        </Wrapper>
      );

      expect(
        screen.getByText(/These references were found but could not be matched/i)
      ).toBeInTheDocument();
    });

    it('does not show unlinked references section when array is empty', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            linkedArtifacts={mockLinkedArtifacts}
            unlinkedReferences={[]}
          />
        </Wrapper>
      );

      expect(screen.queryByText('Unresolved References')).not.toBeInTheDocument();
    });

    it('unlinked references have proper accessibility', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection
            artifactId="source-artifact"
            unlinkedReferences={mockUnlinkedReferences}
          />
        </Wrapper>
      );

      const referencesList = screen.getByRole('list', { name: /Unresolved artifact references/i });
      expect(referencesList).toBeInTheDocument();

      const listItems = within(referencesList).getAllByRole('listitem');
      expect(listItems).toHaveLength(3);
    });
  });

  describe('Accessibility', () => {
    it('has proper section heading', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      const heading = screen.getByRole('heading', { name: /Linked Artifacts/i });
      expect(heading).toBeInTheDocument();
    });

    it('linked artifacts list has proper role and label', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      const list = screen.getByRole('list', { name: /Linked artifacts/i });
      expect(list).toBeInTheDocument();
    });

    it('artifact links have descriptive aria-labels', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      const link = screen.getByRole('link', { name: /View python-utils artifact/i });
      expect(link).toBeInTheDocument();
    });

    it('delete buttons have descriptive aria-labels', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      const deleteButton = screen.getByRole('button', { name: /Remove link to python-utils/i });
      expect(deleteButton).toBeInTheDocument();
    });
  });

  describe('Navigation', () => {
    it('artifact link navigates to correct URL', () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <LinkedArtifactsSection artifactId="source-artifact" linkedArtifacts={mockLinkedArtifacts} />
        </Wrapper>
      );

      const links = screen.getAllByRole('link');
      expect(links[0]).toHaveAttribute('href', '/artifacts/artifact-1');
      expect(links[1]).toHaveAttribute('href', '/artifacts/artifact-2');
      expect(links[2]).toHaveAttribute('href', '/artifacts/artifact-3');
    });
  });
});
