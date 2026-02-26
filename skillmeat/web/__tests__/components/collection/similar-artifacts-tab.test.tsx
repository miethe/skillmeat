/**
 * @jest-environment jsdom
 *
 * Tests for SimilarArtifactsTab and MiniArtifactCard score badge rendering.
 *
 * Coverage:
 * - SimilarArtifactsTab: loading, empty, results, error, retry, card click
 * - MiniArtifactCard: showScore badge visibility, percentage formatting, color tiers
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SimilarArtifactsTab } from '@/components/collection/similar-artifacts-tab';
import { MiniArtifactCard } from '@/components/collection/mini-artifact-card';
import type { SimilarArtifact, SimilarityBreakdown } from '@/types/similarity';
import type { Artifact } from '@/types/artifact';

// ---------------------------------------------------------------------------
// Mock @dnd-kit — required by MiniArtifactCard's DraggableMiniArtifactCard
// sibling which shares the same module
// ---------------------------------------------------------------------------

jest.mock('@dnd-kit/sortable', () => ({
  __esModule: true,
  SortableContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  sortableKeyboardCoordinates: jest.fn(),
  rectSortingStrategy: jest.fn(),
  useSortable: jest.fn(() => ({
    attributes: {},
    listeners: {},
    setNodeRef: jest.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  })),
}));

jest.mock('@dnd-kit/utilities', () => ({
  __esModule: true,
  CSS: { Transform: { toString: () => undefined } },
}));

// ---------------------------------------------------------------------------
// Mock @/hooks barrel (useSimilarArtifacts + useTags + ArtifactGroupBadges deps)
// ---------------------------------------------------------------------------

jest.mock('@/hooks', () => ({
  useSimilarArtifacts: jest.fn(),
  useTags: jest.fn(),
  useGroups: jest.fn(),
  useArtifactGroups: jest.fn(),
}));

// ArtifactGroupBadges lives inside MiniArtifactCard. Stub it to avoid group
// query complexity that is not relevant to these tests.
jest.mock('@/components/collection/artifact-group-badges', () => ({
  ArtifactGroupBadges: () => null,
}));

import {
  useSimilarArtifacts,
  useTags,
} from '@/hooks';

const mockUseSimilarArtifacts = useSimilarArtifacts as jest.MockedFunction<typeof useSimilarArtifacts>;
const mockUseTags = useTags as jest.MockedFunction<typeof useTags>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={createQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

/** Minimal SimilarArtifact fixture */
function makeSimilarArtifact(overrides: Partial<SimilarArtifact> = {}): SimilarArtifact {
  return {
    artifact_id: 'art-uuid-1',
    name: 'canvas-design',
    artifact_type: 'skill',
    source: 'anthropics/skills/canvas-design',
    description: 'A design skill for canvas workflows',
    tags: ['design', 'canvas'],
    composite_score: 0.9,
    match_type: 'similar',
    breakdown: {
      content_score: 0.9,
      structure_score: 0.85,
      metadata_score: 0.8,
      keyword_score: 0.75,
      semantic_score: null,
    },
    ...overrides,
  };
}

/** Minimal Artifact fixture for MiniArtifactCard */
function makeArtifact(overrides: Partial<Artifact> = {}): Artifact {
  return {
    id: 'skill:canvas-design',
    uuid: 'art-uuid-1',
    name: 'canvas-design',
    type: 'skill',
    source: 'anthropics/skills/canvas-design',
    version: 'latest',
    scope: 'user',
    path: '/path/to/canvas-design',
    collection: 'default',
    status: 'synced',
    deployments: [],
    collections: [],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  } as unknown as Artifact;
}

// Default useTags mock — empty, so MiniArtifactCard gets no tag colors from DB
function setupTagsMock() {
  mockUseTags.mockReturnValue({
    data: { items: [], total: 0 },
    isLoading: false,
    isError: false,
  } as any);
}

// ---------------------------------------------------------------------------
// SimilarArtifactsTab tests
// ---------------------------------------------------------------------------

describe('SimilarArtifactsTab', () => {
  const ARTIFACT_ID = 'source-artifact-uuid';

  beforeEach(() => {
    jest.clearAllMocks();
    setupTagsMock();
  });

  // -------------------------------------------------------------------------
  // 1. Loading state
  // -------------------------------------------------------------------------
  describe('loading state', () => {
    it('renders skeleton grid with aria-busy when isLoading is true', () => {
      mockUseSimilarArtifacts.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      // The loading grid carries aria-busy="true"
      const loadingGrid = document.querySelector('[aria-busy="true"]');
      expect(loadingGrid).toBeInTheDocument();

      // Accessible label for screen readers
      expect(loadingGrid).toHaveAttribute('aria-label', 'Loading similar artifacts');
    });

    it('renders 6 skeleton placeholder cards while loading', () => {
      mockUseSimilarArtifacts.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      // Each skeleton card is aria-hidden; the loading grid wraps 6 of them
      const hiddenSkeletons = document.querySelectorAll('[aria-hidden="true"]');
      // At least 6 skeleton placeholders (each SimilarCardSkeleton is aria-hidden)
      expect(hiddenSkeletons.length).toBeGreaterThanOrEqual(6);
    });
  });

  // -------------------------------------------------------------------------
  // 2. Empty state
  // -------------------------------------------------------------------------
  describe('empty state', () => {
    it('renders "No similar artifacts found" when items array is empty', () => {
      mockUseSimilarArtifacts.mockReturnValue({
        data: { artifact_id: ARTIFACT_ID, items: [], total: 0 },
        isLoading: false,
        isError: false,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      expect(screen.getByText('No similar artifacts found')).toBeInTheDocument();
    });

    it('renders threshold guidance text in empty state', () => {
      mockUseSimilarArtifacts.mockReturnValue({
        data: { artifact_id: ARTIFACT_ID, items: [], total: 0 },
        isLoading: false,
        isError: false,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      expect(
        screen.getByText(/try adjusting the similarity threshold/i)
      ).toBeInTheDocument();
    });

    it('renders empty state when data is undefined (no response yet)', () => {
      mockUseSimilarArtifacts.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: false,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      expect(screen.getByText('No similar artifacts found')).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 3. Results state
  // -------------------------------------------------------------------------
  describe('results state', () => {
    const items: SimilarArtifact[] = [
      makeSimilarArtifact({ artifact_id: 'id-1', name: 'canvas-design', composite_score: 0.92 }),
      makeSimilarArtifact({ artifact_id: 'id-2', name: 'document-skills', composite_score: 0.75 }),
      makeSimilarArtifact({ artifact_id: 'id-3', name: 'code-reviewer', composite_score: 0.55 }),
    ];

    beforeEach(() => {
      mockUseSimilarArtifacts.mockReturnValue({
        data: { artifact_id: ARTIFACT_ID, items, total: items.length },
        isLoading: false,
        isError: false,
        refetch: jest.fn(),
      } as any);
    });

    it('renders a card for each result', () => {
      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      expect(screen.getByText('canvas-design')).toBeInTheDocument();
      expect(screen.getByText('document-skills')).toBeInTheDocument();
      expect(screen.getByText('code-reviewer')).toBeInTheDocument();
    });

    it('renders results list with accessible label showing count', () => {
      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      const list = screen.getByRole('list', { name: /3 similar artifacts/i });
      expect(list).toBeInTheDocument();
    });

    it('renders 3 list items matching the result count', () => {
      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      // Each card renders as role="button" inside a role="listitem" wrapper.
      // Use button count to verify the 3 artifact cards are present without
      // accidentally counting nested tag-badge listitems.
      const cards = screen.getAllByRole('button');
      expect(cards).toHaveLength(3);
    });

    it('uses singular label when exactly 1 result', () => {
      const singleItem = [makeSimilarArtifact({ artifact_id: 'id-1', name: 'solo-skill' })];
      mockUseSimilarArtifacts.mockReturnValue({
        data: { artifact_id: ARTIFACT_ID, items: singleItem, total: 1 },
        isLoading: false,
        isError: false,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      const list = screen.getByRole('list', { name: /1 similar artifact$/i });
      expect(list).toBeInTheDocument();
    });

    it('renders score badges for each card (showScore=true is always set)', () => {
      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      // Each card should have a score badge with aria-label "Similarity score: X%"
      expect(screen.getByLabelText('Similarity score: 92%')).toBeInTheDocument();
      expect(screen.getByLabelText('Similarity score: 75%')).toBeInTheDocument();
      expect(screen.getByLabelText('Similarity score: 55%')).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 4. Card click triggers onArtifactClick
  // -------------------------------------------------------------------------
  describe('card click interaction', () => {
    it('calls onArtifactClick with the correct artifact_id when a card is clicked', () => {
      const items: SimilarArtifact[] = [
        makeSimilarArtifact({ artifact_id: 'target-id', name: 'my-skill' }),
      ];

      mockUseSimilarArtifacts.mockReturnValue({
        data: { artifact_id: ARTIFACT_ID, items, total: 1 },
        isLoading: false,
        isError: false,
        refetch: jest.fn(),
      } as any);

      const onArtifactClick = jest.fn();

      render(
        <Wrapper>
          <SimilarArtifactsTab
            artifactId={ARTIFACT_ID}
            onArtifactClick={onArtifactClick}
          />
        </Wrapper>
      );

      const card = screen.getByRole('button', { name: /my-skill/i });
      fireEvent.click(card);

      expect(onArtifactClick).toHaveBeenCalledTimes(1);
      expect(onArtifactClick).toHaveBeenCalledWith('target-id');
    });

    it('does not throw when onArtifactClick is not provided', () => {
      const items: SimilarArtifact[] = [
        makeSimilarArtifact({ artifact_id: 'x', name: 'test-skill' }),
      ];

      mockUseSimilarArtifacts.mockReturnValue({
        data: { artifact_id: ARTIFACT_ID, items, total: 1 },
        isLoading: false,
        isError: false,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      const card = screen.getByRole('button', { name: /test-skill/i });
      expect(() => fireEvent.click(card)).not.toThrow();
    });

    it('calls onArtifactClick for the correct card when multiple cards rendered', () => {
      const items: SimilarArtifact[] = [
        makeSimilarArtifact({ artifact_id: 'first-id', name: 'first-skill' }),
        makeSimilarArtifact({ artifact_id: 'second-id', name: 'second-skill' }),
      ];

      mockUseSimilarArtifacts.mockReturnValue({
        data: { artifact_id: ARTIFACT_ID, items, total: 2 },
        isLoading: false,
        isError: false,
        refetch: jest.fn(),
      } as any);

      const onArtifactClick = jest.fn();

      render(
        <Wrapper>
          <SimilarArtifactsTab
            artifactId={ARTIFACT_ID}
            onArtifactClick={onArtifactClick}
          />
        </Wrapper>
      );

      fireEvent.click(screen.getByRole('button', { name: /second-skill/i }));
      expect(onArtifactClick).toHaveBeenCalledWith('second-id');
    });
  });

  // -------------------------------------------------------------------------
  // 5. Error state
  // -------------------------------------------------------------------------
  describe('error state', () => {
    it('renders error message when isError is true', () => {
      mockUseSimilarArtifacts.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      expect(screen.getByText('Failed to load similar artifacts')).toBeInTheDocument();
    });

    it('renders a retry button in the error state', () => {
      mockUseSimilarArtifacts.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('renders the error container with role="alert" for screen readers', () => {
      mockUseSimilarArtifacts.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 6. Retry button calls refetch
  // -------------------------------------------------------------------------
  describe('retry button', () => {
    it('calls refetch when retry button is clicked', () => {
      const refetch = jest.fn();

      mockUseSimilarArtifacts.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        refetch,
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={ARTIFACT_ID} />
        </Wrapper>
      );

      fireEvent.click(screen.getByRole('button', { name: /retry/i }));

      expect(refetch).toHaveBeenCalledTimes(1);
    });
  });

  // -------------------------------------------------------------------------
  // Hook integration: passes artifactId to useSimilarArtifacts
  // -------------------------------------------------------------------------
  describe('hook integration', () => {
    it('passes the correct artifactId to useSimilarArtifacts', () => {
      const specificId = 'specific-artifact-uuid-abc123';

      mockUseSimilarArtifacts.mockReturnValue({
        data: { artifact_id: specificId, items: [], total: 0 },
        isLoading: false,
        isError: false,
        refetch: jest.fn(),
      } as any);

      render(
        <Wrapper>
          <SimilarArtifactsTab artifactId={specificId} />
        </Wrapper>
      );

      expect(mockUseSimilarArtifacts).toHaveBeenCalledWith(specificId);
    });
  });
});

// ---------------------------------------------------------------------------
// MiniArtifactCard score badge tests
// ---------------------------------------------------------------------------

describe('MiniArtifactCard score badge', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupTagsMock();
  });

  // -------------------------------------------------------------------------
  // 7. Score badge visible when showScore=true
  // -------------------------------------------------------------------------
  it('shows score badge with formatted percentage when showScore=true and similarityScore provided', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard
          artifact={artifact}
          onClick={jest.fn()}
          showScore
          similarityScore={0.85}
        />
      </Wrapper>
    );

    expect(screen.getByLabelText('Similarity score: 85%')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('rounds score correctly (0.854 → 85%, 0.856 → 86%)', () => {
    const artifact = makeArtifact();

    const { rerender } = render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} showScore similarityScore={0.854} />
      </Wrapper>
    );
    expect(screen.getByText('85%')).toBeInTheDocument();

    rerender(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} showScore similarityScore={0.856} />
      </Wrapper>
    );
    expect(screen.getByText('86%')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // 8. No badge when showScore=false or omitted
  // -------------------------------------------------------------------------
  it('does not render a score badge when showScore is not set', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} similarityScore={0.85} />
      </Wrapper>
    );

    expect(screen.queryByLabelText(/Similarity score/i)).not.toBeInTheDocument();
    expect(screen.queryByText('85%')).not.toBeInTheDocument();
  });

  it('does not render a score badge when showScore=false', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard
          artifact={artifact}
          onClick={jest.fn()}
          showScore={false}
          similarityScore={0.85}
        />
      </Wrapper>
    );

    expect(screen.queryByLabelText(/Similarity score/i)).not.toBeInTheDocument();
  });

  it('does not render a score badge when showScore=true but similarityScore is undefined', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} showScore />
      </Wrapper>
    );

    expect(screen.queryByLabelText(/Similarity score/i)).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // 9. Score badge color varies by score tier
  // -------------------------------------------------------------------------
  it('applies emerald color classes for high scores (>= 0.8)', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} showScore similarityScore={0.9} />
      </Wrapper>
    );

    const badge = screen.getByLabelText('Similarity score: 90%');
    // High score: emerald variant
    expect(badge.className).toMatch(/emerald/);
  });

  it('applies amber color classes for mid-range scores (0.5 – 0.79)', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} showScore similarityScore={0.65} />
      </Wrapper>
    );

    const badge = screen.getByLabelText('Similarity score: 65%');
    expect(badge.className).toMatch(/amber/);
  });

  it('applies muted/neutral color classes for low scores (< 0.5)', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} showScore similarityScore={0.3} />
      </Wrapper>
    );

    const badge = screen.getByLabelText('Similarity score: 30%');
    // Low score: muted neutral variant (bg-muted text-muted-foreground)
    expect(badge.className).toMatch(/muted/);
    // Should NOT contain emerald or amber
    expect(badge.className).not.toMatch(/emerald/);
    expect(badge.className).not.toMatch(/amber/);
  });

  it('applies emerald at exactly the 0.8 boundary', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} showScore similarityScore={0.8} />
      </Wrapper>
    );

    const badge = screen.getByLabelText('Similarity score: 80%');
    expect(badge.className).toMatch(/emerald/);
  });

  it('applies amber at exactly the 0.5 boundary', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} showScore similarityScore={0.5} />
      </Wrapper>
    );

    const badge = screen.getByLabelText('Similarity score: 50%');
    expect(badge.className).toMatch(/amber/);
  });

  // -------------------------------------------------------------------------
  // Score badge with breakdown (tooltip trigger variant)
  // -------------------------------------------------------------------------
  it('renders score badge as a tooltip trigger when scoreBreakdown is provided', () => {
    const artifact = makeArtifact();
    const breakdown: SimilarityBreakdown = {
      content_score: 0.9,
      structure_score: 0.85,
      metadata_score: 0.8,
      keyword_score: 0.75,
      semantic_score: null,
    };

    render(
      <Wrapper>
        <MiniArtifactCard
          artifact={artifact}
          onClick={jest.fn()}
          showScore
          similarityScore={0.85}
          scoreBreakdown={breakdown}
        />
      </Wrapper>
    );

    // Badge still renders the percentage and aria-label
    const badge = screen.getByLabelText('Similarity score: 85%');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('85%');
  });

  // -------------------------------------------------------------------------
  // Card accessibility
  // -------------------------------------------------------------------------
  it('renders with role="button" and tabIndex=0 for keyboard navigation', () => {
    const artifact = makeArtifact();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} />
      </Wrapper>
    );

    const card = screen.getByRole('button');
    expect(card).toHaveAttribute('tabIndex', '0');
  });

  it('includes artifact name and type in the accessible label', () => {
    const artifact = makeArtifact({ name: 'canvas-design', type: 'skill' });

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={jest.fn()} />
      </Wrapper>
    );

    const card = screen.getByRole('button', { name: /canvas-design.*skill/i });
    expect(card).toBeInTheDocument();
  });

  it('calls onClick when the card is clicked', () => {
    const artifact = makeArtifact();
    const onClick = jest.fn();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={onClick} />
      </Wrapper>
    );

    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('calls onClick when Enter key is pressed on the card', () => {
    const artifact = makeArtifact();
    const onClick = jest.fn();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={onClick} />
      </Wrapper>
    );

    const card = screen.getByRole('button');
    fireEvent.keyDown(card, { key: 'Enter' });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('calls onClick when Space key is pressed on the card', () => {
    const artifact = makeArtifact();
    const onClick = jest.fn();

    render(
      <Wrapper>
        <MiniArtifactCard artifact={artifact} onClick={onClick} />
      </Wrapper>
    );

    const card = screen.getByRole('button');
    fireEvent.keyDown(card, { key: ' ' });
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
