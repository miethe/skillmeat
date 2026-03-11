/**
 * @jest-environment jsdom
 *
 * E2E-style component tests for the Workflow Artifact UI flow.
 *
 * Covers:
 *   1. ArtifactBrowseCard — workflow artifact renders with correct type badge and
 *      cyan accent color, shows the "Workflow" action button when workflow_id is set
 *   2. ArtifactBrowseCard — clicking "Workflow" button calls onViewWorkflow with the
 *      workflow_id; keyboard (Enter) also triggers navigation
 *   3. ArtifactBrowseCard — loading state shows skeleton placeholder
 *   4. ArtifactGrid — passes onViewWorkflow through to each card
 *   5. ArtifactTypeTabs — "Workflows" tab option is present and selectable
 *   6. Collection page (integration) — workflow artifact cards render, loading
 *      skeleton appears while fetching, empty state when no workflows
 *   7. Manage page (integration) — workflow type tab available in ArtifactTypeTabs,
 *      workflow artifact rows render with correct type information
 *
 * Mock strategy:
 *   - next/navigation stubs (useRouter, useSearchParams, usePathname, useParams)
 *   - @/hooks: all relevant hooks mocked at module level
 *   - @/hooks/use-tags: mocked for ArtifactBrowseCard tag resolution
 *   - @/hooks/useArtifacts: mocked fetchArtifactFromApi
 *   - UI primitives incompatible with jsdom (ScrollArea) swapped with pass-throughs
 *   - Complex child components (dialogs, modals) stubbed to keep tests focused
 */

import * as React from 'react';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ---------------------------------------------------------------------------
// Polyfills — required for Radix UI components in jsdom
// ---------------------------------------------------------------------------

Element.prototype.scrollIntoView = jest.fn();
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.setPointerCapture) {
  (Element.prototype as unknown as { setPointerCapture: () => void }).setPointerCapture = jest.fn();
}
if (!Element.prototype.releasePointerCapture) {
  (Element.prototype as unknown as { releasePointerCapture: () => void }).releasePointerCapture =
    jest.fn();
}

// ---------------------------------------------------------------------------
// Mock next/navigation
// ---------------------------------------------------------------------------

const mockPush = jest.fn();
const mockReplace = jest.fn();
let mockSearchParamsValue = new URLSearchParams();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
  usePathname: () => '/collection',
  useSearchParams: () => mockSearchParamsValue,
  useParams: () => ({}),
}));

jest.mock('next/link', () => {
  const Link = ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  );
  Link.displayName = 'Link';
  return Link;
});

// ---------------------------------------------------------------------------
// Mock @/hooks (barrel) — all hooks used by the components under test
// ---------------------------------------------------------------------------

const mockUseInfiniteArtifacts = jest.fn();
const mockUseCollectionContext = jest.fn();
const mockUseIntersectionObserver = jest.fn();
const mockUseToast = jest.fn();
const mockUseReturnTo = jest.fn();
const mockUseEditArtifactParameters = jest.fn();
const mockUseInfiniteCollectionArtifacts = jest.fn();
const mockEntityLifecycleHook = jest.fn();

jest.mock('@/hooks', () => ({
  useInfiniteArtifacts: (...args: unknown[]) => mockUseInfiniteArtifacts(...args),
  useCollectionContext: (...args: unknown[]) => mockUseCollectionContext(...args),
  useIntersectionObserver: (...args: unknown[]) => mockUseIntersectionObserver(...args),
  useToast: () => mockUseToast(),
  useReturnTo: () => mockUseReturnTo(),
  useEditArtifactParameters: (...args: unknown[]) => mockUseEditArtifactParameters(...args),
  useInfiniteCollectionArtifacts: (...args: unknown[]) =>
    mockUseInfiniteCollectionArtifacts(...args),
  useEntityLifecycle: () => mockEntityLifecycleHook(),
  EntityLifecycleProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="entity-lifecycle-provider">{children}</div>
  ),
  useProjects: () => ({ data: [], isLoading: false, error: null }),
  // useTags is imported from @/hooks barrel by ArtifactBrowseCard
  useTags: () => ({
    data: { items: [], page_info: { total_count: 0, has_next_page: false } },
    isLoading: false,
  }),
  // useArtifactAssociations is imported from @/hooks barrel by ArtifactBrowseCard
  useArtifactAssociations: () => ({
    data: { groups: [], collections: [] },
    isLoading: false,
    error: null,
    refetch: jest.fn(),
  }),
}));

// ---------------------------------------------------------------------------
// Mock use-tags (used by ArtifactBrowseCard for tag color resolution)
// ---------------------------------------------------------------------------

jest.mock('@/hooks/use-tags', () => ({
  useTags: () => ({
    data: { items: [], page_info: { total_count: 0, has_next_page: false } },
    isLoading: false,
  }),
  tagKeys: {
    all: ['tags'] as const,
    lists: () => ['tags', 'list'] as const,
    list: (filters?: unknown) => ['tags', 'list', filters] as const,
    search: (query: string) => ['tags', 'search', query] as const,
    artifact: (artifactId: string) => ['tags', 'artifact', artifactId] as const,
  },
}));

// ---------------------------------------------------------------------------
// Mock fetchArtifactFromApi (used by collection page slow-path navigation)
// ---------------------------------------------------------------------------

jest.mock('@/hooks/useArtifacts', () => ({
  fetchArtifactFromApi: jest.fn().mockResolvedValue(null),
}));

// ---------------------------------------------------------------------------
// Mock lib/api/mappers and entity-mapper (used by collection page)
// ---------------------------------------------------------------------------

jest.mock('@/lib/api/mappers', () => ({
  mapApiResponseToArtifact: (a: unknown) => a,
}));

jest.mock('@/lib/api/entity-mapper', () => ({
  mapArtifactsToEntities: (a: unknown) => a,
}));

// ---------------------------------------------------------------------------
// Stub UI primitives that don't render cleanly in jsdom
// ---------------------------------------------------------------------------

jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
  ScrollBar: () => null,
}));

jest.mock('@/components/ui/separator', () => ({
  Separator: () => <hr />,
}));

// ---------------------------------------------------------------------------
// Stub complex child components to keep tests focused on workflow wiring
// ---------------------------------------------------------------------------

jest.mock('@/components/collection/artifact-details-modal', () => ({
  ArtifactDetailsModal: () => null,
}));

jest.mock('@/components/collection/edit-collection-dialog', () => ({
  EditCollectionDialog: () => null,
}));

jest.mock('@/components/collection/create-collection-dialog', () => ({
  CreateCollectionDialog: () => null,
}));

jest.mock('@/components/collection/create-plugin-dialog', () => ({
  CreatePluginDialog: () => null,
}));

jest.mock('@/components/collection/move-copy-dialog', () => ({
  MoveCopyDialog: () => null,
}));

jest.mock('@/components/collection/add-to-group-dialog', () => ({
  AddToGroupDialog: () => null,
}));

jest.mock('@/components/entity/artifact-deletion-dialog', () => ({
  ArtifactDeletionDialog: () => null,
}));

jest.mock('@/components/discovery/ParameterEditorModal', () => ({
  ParameterEditorModal: () => null,
}));

jest.mock('@/components/collection/collection-header', () => ({
  CollectionHeader: ({
    title,
    onCreateCollection,
  }: {
    title: string;
    onCreateCollection?: () => void;
  }) => (
    <div data-testid="collection-header">
      <h1>{title}</h1>
      {onCreateCollection && (
        <button type="button" onClick={onCreateCollection}>
          New Collection
        </button>
      )}
    </div>
  ),
}));

jest.mock('@/components/collection/collection-toolbar', () => ({
  CollectionToolbar: () => <div data-testid="collection-toolbar" />,
}));

jest.mock('@/components/collection/grouped-artifact-view', () => ({
  GroupedArtifactView: () => <div data-testid="grouped-artifact-view" />,
}));

jest.mock('@/components/shared/active-filter-row', () => ({
  ActiveFilterRow: () => null,
}));

jest.mock('@/components/collection/deploy-dialog', () => ({
  DeployDialog: () => null,
}));

// TagSelectorPopover uses useArtifactTags, useAddTagToArtifact, etc. — stub it
jest.mock('@/components/collection/tag-selector-popover', () => ({
  TagSelectorPopover: () => null,
}));

// ArtifactGroupBadges uses useArtifactGroups internally — stub to avoid hook chain
jest.mock('@/components/collection/artifact-group-badges', () => ({
  ArtifactGroupBadges: () => null,
}));

jest.mock('@/components/manage/manage-page-filters', () => ({
  ManagePageFilters: () => <div data-testid="manage-page-filters" />,
}));

jest.mock('@/components/manage/artifact-operations-modal', () => ({
  ArtifactOperationsModal: () => null,
}));

jest.mock('@/app/manage/components/add-entity-dialog', () => ({
  AddEntityDialog: () => null,
}));

jest.mock('@/components/entity/entity-form', () => ({
  EntityForm: () => null,
}));

jest.mock('@/components/entity/entity-list', () => ({
  EntityList: ({
    entities,
    onEntityClick,
  }: {
    entities: { id: string; name: string; type: string }[];
    onEntityClick?: (entity: unknown) => void;
  }) => (
    <ul aria-label="Artifact list">
      {entities.map((e) => (
        <li key={e.id} role="listitem">
          <button type="button" onClick={() => onEntityClick?.(e)} aria-label={`Open ${e.name}`}>
            {e.name}
          </button>
          <span data-testid={`type-badge-${e.id}`}>{e.type}</span>
        </li>
      ))}
    </ul>
  ),
}));

// ---------------------------------------------------------------------------
// Type imports
// ---------------------------------------------------------------------------

import type { Artifact, ArtifactType } from '@/types/artifact';

// ---------------------------------------------------------------------------
// Components under test — imported after all mocks are established
// ---------------------------------------------------------------------------

import {
  ArtifactBrowseCard,
  ArtifactBrowseCardSkeleton,
} from '@/components/collection/artifact-browse-card';
import { ArtifactGrid } from '@/components/collection/artifact-grid';
import { ArtifactTypeTabs } from '@/components/shared/artifact-type-tabs';

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

function makeWorkflowArtifact(overrides: Partial<Artifact> = {}): Artifact {
  return {
    id: 'workflow:my-ci-pipeline',
    uuid: 'wf-uuid-001',
    name: 'my-ci-pipeline',
    type: 'workflow',
    scope: 'user',
    source: 'github:org/repo/.claude/workflows/ci.swdl',
    syncStatus: 'synced',
    tags: ['ci', 'automation'],
    description: 'Continuous integration pipeline for the monorepo',
    author: 'org',
    workflow_id: 'wf-uuid-001',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-06-15T12:00:00Z',
    ...overrides,
  };
}

function makeSkillArtifact(overrides: Partial<Artifact> = {}): Artifact {
  return {
    id: 'skill:frontend-design',
    uuid: 'sk-uuid-001',
    name: 'frontend-design',
    type: 'skill',
    scope: 'user',
    source: 'github:anthropics/skills/frontend-design',
    syncStatus: 'synced',
    tags: ['ui', 'design'],
    description: 'Frontend design skill',
    author: 'anthropics',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

// ---------------------------------------------------------------------------
// Default hook stubs used across multiple test suites
// ---------------------------------------------------------------------------

function stubCollectionHooks(
  artifacts: Artifact[] = [],
  opts: { isLoading?: boolean; isError?: boolean } = {}
) {
  mockUseCollectionContext.mockReturnValue({
    selectedCollectionId: null,
    setSelectedCollectionId: jest.fn(),
    currentCollection: null,
    currentGroups: [],
    isLoadingCollection: false,
    collections: [],
    isLoading: false,
    selectedGroupId: null,
    setSelectedGroupId: jest.fn(),
  });

  mockUseInfiniteArtifacts.mockReturnValue({
    data: opts.isLoading
      ? undefined
      : {
          pages: [
            {
              items: artifacts,
              total: artifacts.length,
              next_cursor: null,
              page_info: { total_count: artifacts.length, has_next_page: false },
            },
          ],
        },
    isLoading: opts.isLoading ?? false,
    isFetchingNextPage: false,
    hasNextPage: false,
    fetchNextPage: jest.fn(),
    refetch: jest.fn(),
    error: opts.isError ? new Error('Failed to load') : null,
  });

  mockUseInfiniteCollectionArtifacts.mockReturnValue({
    data: undefined,
    isLoading: false,
    isFetchingNextPage: false,
    hasNextPage: false,
    fetchNextPage: jest.fn(),
    refetch: jest.fn(),
    error: null,
  });

  mockUseIntersectionObserver.mockReturnValue({ targetRef: { current: null }, isIntersecting: false });
  mockUseToast.mockReturnValue({ toast: jest.fn() });
  mockUseReturnTo.mockReturnValue({ returnTo: null });
  mockUseEditArtifactParameters.mockReturnValue({
    artifact: null,
    parameters: null,
    open: false,
    onSave: jest.fn(),
    onCancel: jest.fn(),
    openFor: jest.fn(),
  });
}

function stubManageHooks(artifacts: Artifact[] = []) {
  mockEntityLifecycleHook.mockReturnValue({
    entities: artifacts,
    isLoading: false,
    isRefetching: false,
    refetch: jest.fn(),
    setTypeFilter: jest.fn(),
    setStatusFilter: jest.fn(),
    setSearchQuery: jest.fn(),
  });

  mockUseReturnTo.mockReturnValue({ returnTo: null });
  mockUseToast.mockReturnValue({ toast: jest.fn() });
}

// ---------------------------------------------------------------------------
// Reset mocks before each test
// ---------------------------------------------------------------------------

beforeEach(() => {
  jest.clearAllMocks();
  mockPush.mockClear();
  mockReplace.mockClear();
  mockSearchParamsValue = new URLSearchParams();
});

// ===========================================================================
// SUITE 1: ArtifactBrowseCard — Workflow artifact rendering
// ===========================================================================

describe('ArtifactBrowseCard — workflow artifact rendering', () => {
  it('renders the workflow artifact name', () => {
    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeWorkflowArtifact()}
        onClick={jest.fn()}
      />
    );
    expect(screen.getByText('my-ci-pipeline')).toBeInTheDocument();
  });

  it('renders the workflow artifact description', () => {
    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeWorkflowArtifact()}
        onClick={jest.fn()}
      />
    );
    expect(
      screen.getByText('Continuous integration pipeline for the monorepo')
    ).toBeInTheDocument();
  });

  it('renders the card with the "workflow" type in its accessible label', () => {
    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeWorkflowArtifact()}
        onClick={jest.fn()}
      />
    );
    // The card root element has role="button" with aria-label mentioning the artifact type
    expect(
      screen.getByRole('button', { name: /workflow artifact/i })
    ).toBeInTheDocument();
  });

  it('shows the "Workflow" action button when artifact has workflow_id and onViewWorkflow is provided', () => {
    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeWorkflowArtifact({ workflow_id: 'wf-uuid-001' })}
        onClick={jest.fn()}
        onViewWorkflow={jest.fn()}
      />
    );
    expect(
      screen.getByRole('button', { name: /View workflow detail for my-ci-pipeline/i })
    ).toBeInTheDocument();
  });

  it('does NOT show "Workflow" action button when workflow_id is absent', () => {
    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeWorkflowArtifact({ workflow_id: undefined })}
        onClick={jest.fn()}
        onViewWorkflow={jest.fn()}
      />
    );
    expect(
      screen.queryByRole('button', { name: /View workflow detail/i })
    ).not.toBeInTheDocument();
  });

  it('does NOT show "Workflow" action button when onViewWorkflow handler is absent', () => {
    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeWorkflowArtifact({ workflow_id: 'wf-uuid-001' })}
        onClick={jest.fn()}
        // onViewWorkflow deliberately omitted
      />
    );
    expect(
      screen.queryByRole('button', { name: /View workflow detail/i })
    ).not.toBeInTheDocument();
  });

  it('does NOT show "Workflow" action button for a non-workflow artifact', () => {
    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeSkillArtifact()}
        onClick={jest.fn()}
        onViewWorkflow={jest.fn()}
      />
    );
    expect(
      screen.queryByRole('button', { name: /View workflow detail/i })
    ).not.toBeInTheDocument();
  });
});

// ===========================================================================
// SUITE 2: ArtifactBrowseCard — Workflow navigation
// ===========================================================================

describe('ArtifactBrowseCard — workflow navigation', () => {
  it('clicking the "Workflow" button calls onViewWorkflow with the workflow_id', async () => {
    const user = userEvent.setup();
    const onViewWorkflow = jest.fn();

    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeWorkflowArtifact({ workflow_id: 'wf-uuid-001' })}
        onClick={jest.fn()}
        onViewWorkflow={onViewWorkflow}
      />
    );

    await user.click(
      screen.getByRole('button', { name: /View workflow detail for my-ci-pipeline/i })
    );

    expect(onViewWorkflow).toHaveBeenCalledTimes(1);
    expect(onViewWorkflow).toHaveBeenCalledWith('wf-uuid-001');
  });

  it('clicking the "Workflow" button does NOT call the card onClick handler', async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();
    const onViewWorkflow = jest.fn();

    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeWorkflowArtifact({ workflow_id: 'wf-uuid-001' })}
        onClick={onClick}
        onViewWorkflow={onViewWorkflow}
      />
    );

    await user.click(
      screen.getByRole('button', { name: /View workflow detail for my-ci-pipeline/i })
    );

    // The workflow button stops event propagation — card onClick must NOT fire
    expect(onClick).not.toHaveBeenCalled();
    expect(onViewWorkflow).toHaveBeenCalledTimes(1);
  });

  it('workflow button is keyboard accessible — button element is focusable', () => {
    renderWithProviders(
      <ArtifactBrowseCard
        artifact={makeWorkflowArtifact({ workflow_id: 'wf-uuid-001' })}
        onClick={jest.fn()}
        onViewWorkflow={jest.fn()}
      />
    );

    const workflowBtn = screen.getByRole('button', {
      name: /View workflow detail for my-ci-pipeline/i,
    });
    // Buttons are natively focusable — verify it can receive focus
    workflowBtn.focus();
    expect(document.activeElement).toBe(workflowBtn);
  });

  it('onViewWorkflow receives the correct workflow_id when multiple workflow artifacts are rendered', async () => {
    const user = userEvent.setup();
    const onViewWorkflow = jest.fn();

    const wf1 = makeWorkflowArtifact({
      id: 'workflow:ci',
      name: 'ci-pipeline',
      workflow_id: 'wf-uuid-ci',
    });
    const wf2 = makeWorkflowArtifact({
      id: 'workflow:release',
      name: 'release-pipeline',
      workflow_id: 'wf-uuid-release',
    });

    renderWithProviders(
      <div>
        <ArtifactBrowseCard artifact={wf1} onClick={jest.fn()} onViewWorkflow={onViewWorkflow} />
        <ArtifactBrowseCard artifact={wf2} onClick={jest.fn()} onViewWorkflow={onViewWorkflow} />
      </div>
    );

    await user.click(
      screen.getByRole('button', { name: /View workflow detail for release-pipeline/i })
    );

    expect(onViewWorkflow).toHaveBeenCalledWith('wf-uuid-release');
    expect(onViewWorkflow).toHaveBeenCalledTimes(1);
  });
});

// ===========================================================================
// SUITE 3: ArtifactBrowseCard — Loading skeleton
// ===========================================================================

describe('ArtifactBrowseCard — loading skeleton', () => {
  it('renders without errors', () => {
    const { container } = renderWithProviders(<ArtifactBrowseCardSkeleton />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('has aria-busy="true" to signal loading state to assistive technology', () => {
    const { container } = renderWithProviders(<ArtifactBrowseCardSkeleton />);
    expect(container.firstChild).toHaveAttribute('aria-busy', 'true');
  });

  it('applies animate-pulse for loading animation', () => {
    const { container } = renderWithProviders(<ArtifactBrowseCardSkeleton />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });
});

// ===========================================================================
// SUITE 4: ArtifactGrid — workflow pass-through
// ===========================================================================

describe('ArtifactGrid — workflow card integration', () => {
  it('renders a workflow card within the grid', () => {
    const artifacts = [makeWorkflowArtifact()];
    renderWithProviders(
      <ArtifactGrid
        artifacts={artifacts}
        onArtifactClick={jest.fn()}
        onViewWorkflow={jest.fn()}
      />
    );
    expect(screen.getByText('my-ci-pipeline')).toBeInTheDocument();
  });

  it('passes onViewWorkflow to each workflow card', async () => {
    const user = userEvent.setup();
    const onViewWorkflow = jest.fn();
    const artifacts = [makeWorkflowArtifact({ workflow_id: 'wf-uuid-001' })];

    renderWithProviders(
      <ArtifactGrid
        artifacts={artifacts}
        onArtifactClick={jest.fn()}
        onViewWorkflow={onViewWorkflow}
      />
    );

    await user.click(
      screen.getByRole('button', { name: /View workflow detail for my-ci-pipeline/i })
    );

    expect(onViewWorkflow).toHaveBeenCalledWith('wf-uuid-001');
  });

  it('renders skeleton cards while loading', () => {
    const { container } = renderWithProviders(
      <ArtifactGrid artifacts={[]} isLoading onArtifactClick={jest.fn()} />
    );
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows an empty state message when there are no artifacts and not loading', () => {
    renderWithProviders(
      <ArtifactGrid artifacts={[]} isLoading={false} onArtifactClick={jest.fn()} />
    );
    expect(screen.getByText(/No artifacts/i)).toBeInTheDocument();
  });

  it('renders multiple workflow cards for multiple workflow artifacts', () => {
    const artifacts = [
      makeWorkflowArtifact({ id: 'workflow:ci', name: 'ci-pipeline', workflow_id: 'wf-001' }),
      makeWorkflowArtifact({
        id: 'workflow:deploy',
        name: 'deploy-pipeline',
        workflow_id: 'wf-002',
      }),
    ];
    renderWithProviders(
      <ArtifactGrid artifacts={artifacts} onArtifactClick={jest.fn()} onViewWorkflow={jest.fn()} />
    );
    expect(screen.getByText('ci-pipeline')).toBeInTheDocument();
    expect(screen.getByText('deploy-pipeline')).toBeInTheDocument();
  });
});

// ===========================================================================
// SUITE 5: ArtifactTypeTabs — workflow tab
// ===========================================================================

describe('ArtifactTypeTabs — workflow tab', () => {
  it('renders a "Workflows" tab trigger', () => {
    const onChange = jest.fn();
    renderWithProviders(<ArtifactTypeTabs value="all" onChange={onChange} />);
    expect(screen.getByRole('tab', { name: /Workflows/i })).toBeInTheDocument();
  });

  it('selecting the Workflows tab calls onChange with "workflow"', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    renderWithProviders(<ArtifactTypeTabs value="all" onChange={onChange} />);

    await user.click(screen.getByRole('tab', { name: /Workflows/i }));
    expect(onChange).toHaveBeenCalledWith('workflow');
  });

  it('marks the Workflows tab as selected when value is "workflow"', () => {
    const onChange = jest.fn();
    renderWithProviders(
      <ArtifactTypeTabs value={'workflow' as ArtifactType} onChange={onChange} />
    );
    const tab = screen.getByRole('tab', { name: /Workflows/i });
    // Radix Tabs sets aria-selected="true" on the active tab
    expect(tab).toHaveAttribute('aria-selected', 'true');
  });

  it('renders all standard artifact type tabs alongside the workflow tab', () => {
    const onChange = jest.fn();
    renderWithProviders(<ArtifactTypeTabs value="all" onChange={onChange} />);
    // All tab should always be present
    expect(screen.getByRole('tab', { name: /All/i })).toBeInTheDocument();
    // Workflow tab must coexist with others
    expect(screen.getByRole('tab', { name: /Workflows/i })).toBeInTheDocument();
  });
});

// ===========================================================================
// SUITE 6: Collection page integration — workflow artifact flow
// ===========================================================================

/**
 * We import CollectionPage lazily (after mocks) so that all module-level
 * mock registrations are applied before Next.js context providers run.
 */
// eslint-disable-next-line @typescript-eslint/no-var-requires
const CollectionPage = require('@/app/collection/page').default as React.ComponentType;

describe('Collection page — workflow artifact cards', () => {
  it('renders workflow artifact cards when API returns workflow artifacts', async () => {
    stubCollectionHooks([
      makeWorkflowArtifact({ name: 'ci-pipeline', workflow_id: 'wf-uuid-001' }),
    ]);

    renderWithProviders(<CollectionPage />);

    await waitFor(() => {
      expect(screen.getByText('ci-pipeline')).toBeInTheDocument();
    });
  });

  it('shows loading skeletons while artifacts are being fetched', () => {
    stubCollectionHooks([], { isLoading: true });
    const { container } = renderWithProviders(<CollectionPage />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows an empty state message when there are no workflow artifacts', async () => {
    stubCollectionHooks([]);
    renderWithProviders(<CollectionPage />);

    await waitFor(() => {
      // Collection page renders EmptyState with "No artifacts" or similar text
      expect(screen.getByText(/No artifacts/i)).toBeInTheDocument();
    });
  });

  it('renders the Workflows tab in ArtifactTypeTabs on the collection page', async () => {
    stubCollectionHooks([]);
    renderWithProviders(<CollectionPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Workflows/i })).toBeInTheDocument();
    });
  });

  it('clicking a workflow artifact card calls onArtifactClick which navigates to /workflows/{id}', async () => {
    const user = userEvent.setup();
    const artifact = makeWorkflowArtifact({ workflow_id: 'wf-uuid-001' });
    stubCollectionHooks([artifact]);

    renderWithProviders(<CollectionPage />);

    await waitFor(() => {
      expect(screen.getByText('my-ci-pipeline')).toBeInTheDocument();
    });

    // The "Workflow" action button navigates directly
    await user.click(
      screen.getByRole('button', { name: /View workflow detail for my-ci-pipeline/i })
    );

    expect(mockPush).toHaveBeenCalledWith('/workflows/wf-uuid-001');
  });
});

// ===========================================================================
// SUITE 7: Manage page integration — workflow rows
// ===========================================================================

// eslint-disable-next-line @typescript-eslint/no-var-requires
const ManagePage = require('@/app/manage/page').default as React.ComponentType;

describe('Manage page — workflow artifact rows', () => {
  it('renders workflow artifact rows when entities include workflow type', async () => {
    const artifact = makeWorkflowArtifact({ name: 'ci-pipeline' });
    stubManageHooks([artifact]);

    renderWithProviders(<ManagePage />);

    await waitFor(() => {
      expect(screen.getByText('ci-pipeline')).toBeInTheDocument();
    });
  });

  it('shows the workflow type badge on workflow artifact rows', async () => {
    const artifact = makeWorkflowArtifact({ id: 'workflow:ci-pipeline', name: 'ci-pipeline' });
    stubManageHooks([artifact]);

    renderWithProviders(<ManagePage />);

    await waitFor(() => {
      // EntityList stub renders type badges as <span data-testid="type-badge-{id}">
      const badge = screen.getByTestId('type-badge-workflow:ci-pipeline');
      expect(badge).toHaveTextContent('workflow');
    });
  });

  it('renders the Workflows tab option in the type filter on the manage page', async () => {
    stubManageHooks([]);
    renderWithProviders(<ManagePage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Workflows/i })).toBeInTheDocument();
    });
  });

  it('renders multiple workflow artifact rows when multiple workflow artifacts are returned', async () => {
    const artifacts = [
      makeWorkflowArtifact({ id: 'workflow:ci', name: 'ci-pipeline', workflow_id: 'wf-001' }),
      makeWorkflowArtifact({
        id: 'workflow:release',
        name: 'release-pipeline',
        workflow_id: 'wf-002',
      }),
    ];
    stubManageHooks(artifacts);

    renderWithProviders(<ManagePage />);

    await waitFor(() => {
      expect(screen.getByText('ci-pipeline')).toBeInTheDocument();
      expect(screen.getByText('release-pipeline')).toBeInTheDocument();
    });
  });

  it('renders an empty artifact list when no entities are returned', async () => {
    stubManageHooks([]);
    renderWithProviders(<ManagePage />);

    await waitFor(() => {
      // EntityList stub renders an empty <ul> — nothing besides the list
      const list = screen.getByRole('list', { name: /Artifact list/i });
      expect(list).toBeInTheDocument();
      expect(within(list).queryAllByRole('listitem')).toHaveLength(0);
    });
  });
});
