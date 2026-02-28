/**
 * @jest-environment jsdom
 *
 * E2E-style workflow frontend tests.
 *
 * Covers the following user journeys:
 *   1. Library page — workflow list renders, empty state, error state
 *   2. Library page — filter/search interactions
 *   3. Library page — navigate to workflow detail via card link
 *   4. Library page — duplicate and delete actions
 *   5. Builder page (create mode) — renders empty canvas
 *   6. Builder page — stage addition opens editor
 *   7. Workflow detail page — loading and error states
 *   8. Workflow detail page — stages tab renders
 *   9. Workflow detail page — executions tab renders
 *  10. Workflow detail page — Run button visible for active workflows
 *  11. All Executions page — table renders, sort toggle, filter
 *  12. All Executions page — empty state (no data, filtered)
 *  13. All Executions page — error state
 *  14. Mobile viewport — library page renders at narrow width
 *  15. Mobile viewport — detail page renders at narrow width
 *
 * Mock strategy:
 *   - next/navigation: useRouter / useParams / usePathname stubs
 *   - @/hooks: all workflow hooks mocked at the module level
 *   - UI primitives that jsdom cannot handle (ScrollArea, Separator) are swapped
 *     with simple pass-through wrappers
 *   - Radix UI Select polyfills applied for jsdom compatibility
 */

import * as React from 'react';
import { render, screen, within, fireEvent, waitFor, act } from '@testing-library/react';
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
  (Element.prototype as unknown as { setPointerCapture: () => void }).setPointerCapture =
    jest.fn();
}
if (!Element.prototype.releasePointerCapture) {
  (Element.prototype as unknown as {
    releasePointerCapture: () => void;
  }).releasePointerCapture = jest.fn();
}

// ---------------------------------------------------------------------------
// Mock next/navigation
// ---------------------------------------------------------------------------

const mockPush = jest.fn();
const mockBack = jest.fn();
const mockReplace = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: jest.fn(),
    back: mockBack,
    forward: jest.fn(),
    refresh: jest.fn(),
    pathname: '/workflows',
    query: {},
    asPath: '/workflows',
  }),
  usePathname: () => '/workflows',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: 'wf-001' }),
}));

// ---------------------------------------------------------------------------
// Mock @/hooks — all workflow hooks
// ---------------------------------------------------------------------------

const mockUseWorkflows = jest.fn();
const mockUseWorkflow = jest.fn();
const mockUseWorkflowExecutions = jest.fn();
const mockUseWorkflowBuilder = jest.fn();
const mockUseCreateWorkflow = jest.fn();
const mockUseUpdateWorkflow = jest.fn();
const mockUseDeleteWorkflow = jest.fn();
const mockUseDuplicateWorkflow = jest.fn();
const mockUseDebounce = jest.fn((v: string) => v);
const mockUseContextModules = jest.fn();
const mockUseRunWorkflow = jest.fn();
const mockUseToast = jest.fn();

jest.mock('@/hooks', () => ({
  useWorkflows: (...args: unknown[]) => mockUseWorkflows(...args),
  useWorkflow: (...args: unknown[]) => mockUseWorkflow(...args),
  useWorkflowExecutions: (...args: unknown[]) => mockUseWorkflowExecutions(...args),
  useWorkflowBuilder: (...args: unknown[]) => mockUseWorkflowBuilder(...args),
  useCreateWorkflow: () => mockUseCreateWorkflow(),
  useUpdateWorkflow: () => mockUseUpdateWorkflow(),
  useDeleteWorkflow: () => mockUseDeleteWorkflow(),
  useDuplicateWorkflow: () => mockUseDuplicateWorkflow(),
  useDebounce: (v: string, _d: number) => mockUseDebounce(v),
  useContextModules: (...args: unknown[]) => mockUseContextModules(...args),
  useRunWorkflow: () => mockUseRunWorkflow(),
  useToast: () => mockUseToast(),
}));

// ---------------------------------------------------------------------------
// Mock UI primitives that are incompatible with jsdom
// ---------------------------------------------------------------------------

jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
}));

jest.mock('@/components/ui/separator', () => ({
  Separator: () => <hr />,
}));

// BuilderSidebar is a complex metadata panel with ContextModulePicker which
// requires many hook dependencies. Stub it to keep builder tests focused on
// the canvas and top bar.
jest.mock('@/components/workflow/builder-sidebar', () => ({
  BuilderSidebar: () => <aside data-testid="builder-sidebar" aria-label="Workflow settings sidebar" />,
}));

// StageEditor slide-over — requires complex stage hook wiring; stub for builder tests
jest.mock('@/components/workflow/stage-editor', () => ({
  StageEditor: () => null,
}));

// ---------------------------------------------------------------------------
// Type imports
// ---------------------------------------------------------------------------

import type { Workflow, WorkflowExecution, WorkflowStage } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Pages under test (imported after mocks)
// ---------------------------------------------------------------------------

import WorkflowsPage from '@/app/workflows/page';
// WorkflowDetailPage uses useParams internally — import after mock
// eslint-disable-next-line @typescript-eslint/no-var-requires
const WorkflowDetailPage = require('@/app/workflows/[id]/page').default as React.ComponentType;

import AllExecutionsPage from '@/app/workflows/executions/page';
import { WorkflowBuilderView } from '@/components/workflow/workflow-builder-view';

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

function makeStage(overrides: Partial<WorkflowStage> = {}): WorkflowStage {
  return {
    id: 's-001',
    stageIdRef: 'stage-ref-001',
    name: 'Build',
    orderIndex: 0,
    stageType: 'agent',
    dependsOn: [],
    inputs: {},
    outputs: {},
    ...overrides,
  };
}

function makeWorkflow(overrides: Partial<Workflow> = {}): Workflow {
  return {
    id: 'wf-001',
    uuid: 'wf-uuid-001',
    name: 'My Test Workflow',
    description: 'Runs the test suite end-to-end',
    version: '1.0.0',
    status: 'active',
    definition: '',
    tags: ['ci', 'testing'],
    stages: [
      makeStage({ id: 's-001', name: 'Build', orderIndex: 0 }),
      makeStage({ id: 's-002', name: 'Test', orderIndex: 1 }),
    ],
    parameters: {},
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-06-15T12:00:00Z',
    ...overrides,
  };
}

function makeExecution(overrides: Partial<WorkflowExecution> = {}): WorkflowExecution {
  return {
    id: 'exec-001',
    workflowId: 'wf-001',
    workflowName: 'My Test Workflow',
    status: 'completed',
    trigger: 'manual',
    stages: [],
    startedAt: new Date(Date.now() - 300_000).toISOString(),
    completedAt: new Date(Date.now() - 60_000).toISOString(),
    durationMs: 240_000,
    progressPct: 100,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// QueryClient helpers
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
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Default mutation stubs
// ---------------------------------------------------------------------------

function stubMutations() {
  mockUseDeleteWorkflow.mockReturnValue({ mutateAsync: jest.fn().mockResolvedValue(undefined) });
  mockUseDuplicateWorkflow.mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue(makeWorkflow({ id: 'wf-dup' })),
  });
  mockUseCreateWorkflow.mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue(undefined),
    isPending: false,
  });
  mockUseUpdateWorkflow.mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue(undefined),
    isPending: false,
  });
  mockUseRunWorkflow.mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue({ id: 'exec-new', workflowId: 'wf-001' }),
    isPending: false,
  });
  mockUseContextModules.mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  });
  mockUseToast.mockReturnValue({ toast: jest.fn() });
}

// ---------------------------------------------------------------------------
// beforeEach reset
// ---------------------------------------------------------------------------

beforeEach(() => {
  jest.clearAllMocks();
  mockPush.mockClear();
  mockBack.mockClear();
  mockReplace.mockClear();
  mockUseDebounce.mockImplementation((v: string) => v);
  stubMutations();
});

// ===========================================================================
// JOURNEY 1: Library Page — workflow list renders
// ===========================================================================

describe('Journey 1: Workflow Library — list renders', () => {
  it('renders the page heading "Workflows"', () => {
    mockUseWorkflows.mockReturnValue({
      data: { items: [makeWorkflow()] },
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<WorkflowsPage />);
    expect(screen.getByRole('heading', { name: /Workflows/i })).toBeInTheDocument();
  });

  it('renders workflow cards for each workflow returned by the hook', () => {
    mockUseWorkflows.mockReturnValue({
      data: { items: [makeWorkflow({ id: 'wf-1', name: 'Alpha' }), makeWorkflow({ id: 'wf-2', name: 'Beta' })] },
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<WorkflowsPage />);
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
  });

  it('renders loading skeletons while data is loading', () => {
    mockUseWorkflows.mockReturnValue({ data: undefined, isLoading: true, isError: false });
    const { container } = renderWithProviders(<WorkflowsPage />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('each workflow card has a link to the workflow detail page', () => {
    mockUseWorkflows.mockReturnValue({
      data: { items: [makeWorkflow({ id: 'wf-001', name: 'My Test Workflow' })] },
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<WorkflowsPage />);
    const detailLink = screen.getByRole('link', {
      name: /View details for My Test Workflow/i,
    });
    expect(detailLink).toHaveAttribute('href', '/workflows/wf-001');
  });
});

// ===========================================================================
// JOURNEY 2: Library Page — empty states
// ===========================================================================

describe('Journey 2: Workflow Library — empty states', () => {
  it('shows "No workflows yet" when the collection is empty and no filters are active', () => {
    mockUseWorkflows.mockReturnValue({ data: { items: [] }, isLoading: false, isError: false });
    renderWithProviders(<WorkflowsPage />);
    expect(screen.getByText(/No workflows yet/i)).toBeInTheDocument();
  });

  it('shows a "New Workflow" CTA link in the no-data empty state', () => {
    mockUseWorkflows.mockReturnValue({ data: { items: [] }, isLoading: false, isError: false });
    renderWithProviders(<WorkflowsPage />);
    // Multiple "New Workflow" links appear (header + empty state CTA) — all point to /workflows/new
    const links = screen.getAllByRole('link', { name: /New Workflow/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    links.forEach((link) => expect(link).toHaveAttribute('href', '/workflows/new'));
  });

  it('shows "No workflows match your filters" when search returns nothing', async () => {
    // Start with empty results AND a search filter active
    mockUseWorkflows.mockReturnValue({ data: { items: [] }, isLoading: false, isError: false });
    const user = userEvent.setup();
    renderWithProviders(<WorkflowsPage />);

    const searchBox = screen.getByRole('searchbox', { name: /Search workflows/i });
    await user.type(searchBox, 'nonexistent');

    await waitFor(() => {
      expect(screen.getByText(/No workflows match your filters/i)).toBeInTheDocument();
    });
  });

  it('shows "Clear filters" button in filter empty state', async () => {
    mockUseWorkflows.mockReturnValue({ data: { items: [] }, isLoading: false, isError: false });
    const user = userEvent.setup();
    renderWithProviders(<WorkflowsPage />);

    const searchBox = screen.getByRole('searchbox', { name: /Search workflows/i });
    await user.type(searchBox, 'ghost');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Clear filters/i })).toBeInTheDocument();
    });
  });
});

// ===========================================================================
// JOURNEY 3: Library Page — error state
// ===========================================================================

describe('Journey 3: Workflow Library — error state', () => {
  it('shows an error message when the hook returns isError=true', () => {
    mockUseWorkflows.mockReturnValue({ data: undefined, isLoading: false, isError: true });
    renderWithProviders(<WorkflowsPage />);
    expect(
      screen.getByRole('alert')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Failed to load workflows/i)
    ).toBeInTheDocument();
  });
});

// ===========================================================================
// JOURNEY 4: Library Page — card actions
// ===========================================================================

describe('Journey 4: Workflow Library — card actions', () => {
  function setup() {
    mockUseWorkflows.mockReturnValue({
      data: { items: [makeWorkflow({ id: 'wf-001', name: 'My Test Workflow' })] },
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<WorkflowsPage />);
  }

  it('clicking Edit navigates to the workflow edit page', async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole('button', { name: /Edit workflow/i }));
    expect(mockPush).toHaveBeenCalledWith('/workflows/wf-001/edit');
  });

  it('clicking Duplicate calls the duplicate mutation', async () => {
    const user = userEvent.setup();
    const mutateAsync = jest.fn().mockResolvedValue(makeWorkflow({ id: 'wf-dup' }));
    mockUseDuplicateWorkflow.mockReturnValue({ mutateAsync });
    setup();

    await user.click(screen.getByRole('button', { name: /More options/i }));
    const duplicateItem = await screen.findByText('Duplicate');
    await user.click(duplicateItem);

    expect(mutateAsync).toHaveBeenCalledWith({ id: 'wf-001' });
  });

  it('clicking Delete with confirmation calls the delete mutation', async () => {
    const user = userEvent.setup();
    const mutateAsync = jest.fn().mockResolvedValue(undefined);
    mockUseDeleteWorkflow.mockReturnValue({ mutateAsync });
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    setup();

    await user.click(screen.getByRole('button', { name: /More options/i }));
    const deleteItem = await screen.findByText('Delete');
    await user.click(deleteItem);

    expect(mutateAsync).toHaveBeenCalledWith('wf-001');
    (window.confirm as jest.Mock).mockRestore();
  });

  it('clicking Delete without confirmation does NOT call the delete mutation', async () => {
    const user = userEvent.setup();
    const mutateAsync = jest.fn();
    mockUseDeleteWorkflow.mockReturnValue({ mutateAsync });
    jest.spyOn(window, 'confirm').mockReturnValue(false);
    setup();

    await user.click(screen.getByRole('button', { name: /More options/i }));
    const deleteItem = await screen.findByText('Delete');
    await user.click(deleteItem);

    expect(mutateAsync).not.toHaveBeenCalled();
    (window.confirm as jest.Mock).mockRestore();
  });
});

// ===========================================================================
// JOURNEY 5: Library Page — view toggle (grid / list)
// ===========================================================================

describe('Journey 5: Workflow Library — view toggle', () => {
  function setup() {
    mockUseWorkflows.mockReturnValue({
      data: { items: [makeWorkflow({ id: 'wf-001', name: 'Alpha' })] },
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<WorkflowsPage />);
  }

  it('renders Grid view by default', () => {
    setup();
    expect(
      screen.getByRole('button', { name: /Grid view/i })
    ).toHaveAttribute('aria-pressed', 'true');
  });

  it('clicking List view renders a list', async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole('button', { name: /List view/i }));
    await waitFor(() => {
      expect(screen.getByRole('list', { name: 'Workflows' })).toBeInTheDocument();
    });
  });
});

// ===========================================================================
// JOURNEY 6: Workflow Detail Page — loading, error, not-found
// ===========================================================================

describe('Journey 6: Workflow Detail Page — states', () => {
  it('renders a loading skeleton while the workflow is being fetched', () => {
    mockUseWorkflow.mockReturnValue({ data: undefined, isLoading: true, error: null, refetch: jest.fn() });
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, error: null, refetch: jest.fn() });
    renderWithProviders(<WorkflowDetailPage />);
    expect(screen.getByLabelText(/Loading workflow detail/i)).toBeInTheDocument();
  });

  it('renders an error alert when the hook returns an error', () => {
    mockUseWorkflow.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      refetch: jest.fn(),
    });
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, error: null, refetch: jest.fn() });
    renderWithProviders(<WorkflowDetailPage />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Failed to load workflow/i)).toBeInTheDocument();
  });

  it('renders a not-found message when data is null', () => {
    mockUseWorkflow.mockReturnValue({ data: null, isLoading: false, error: null, refetch: jest.fn() });
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, error: null, refetch: jest.fn() });
    renderWithProviders(<WorkflowDetailPage />);
    expect(screen.getByText(/Workflow not found/i)).toBeInTheDocument();
  });
});

// ===========================================================================
// JOURNEY 7: Workflow Detail Page — stages tab
// ===========================================================================

describe('Journey 7: Workflow Detail Page — stages tab', () => {
  function setup(wf?: Workflow) {
    const workflow = wf ?? makeWorkflow();
    mockUseWorkflow.mockReturnValue({ data: workflow, isLoading: false, error: null, refetch: jest.fn() });
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, error: null, refetch: jest.fn() });
    renderWithProviders(<WorkflowDetailPage />);
    return workflow;
  }

  it('renders the workflow name as a heading', () => {
    setup();
    expect(screen.getByRole('heading', { name: 'My Test Workflow' })).toBeInTheDocument();
  });

  it('shows the active status badge for an active workflow', () => {
    setup(makeWorkflow({ status: 'active' }));
    expect(screen.getByLabelText(/Workflow status: Active/i)).toBeInTheDocument();
  });

  it('renders the Stages tab content as the default active panel', () => {
    setup(makeWorkflow({
      stages: [makeStage({ id: 's-1', name: 'Build', orderIndex: 0 })],
    }));
    // The stages tab is active by default — verify its content is rendered
    // (Radix tabpanel aria-label may vary; query by visible content instead)
    const stagesList = screen.getByRole('list', { name: /Workflow stages/i });
    expect(stagesList).toBeInTheDocument();
  });

  it('lists all stages in order', () => {
    setup(
      makeWorkflow({
        stages: [
          makeStage({ id: 's-1', name: 'Build', orderIndex: 0 }),
          makeStage({ id: 's-2', name: 'Test', orderIndex: 1 }),
          makeStage({ id: 's-3', name: 'Deploy', orderIndex: 2 }),
        ],
      })
    );
    const stageList = screen.getByRole('list', { name: /Workflow stages/i });
    const items = within(stageList).getAllByRole('listitem');
    expect(items).toHaveLength(3);
  });

  it('shows "No stages defined" when the workflow has no stages', () => {
    setup(makeWorkflow({ stages: [] }));
    expect(screen.getByText(/No stages defined/i)).toBeInTheDocument();
  });

  it('shows the Run button for active workflows', () => {
    setup(makeWorkflow({ status: 'active' }));
    expect(
      screen.getByRole('button', { name: /Run workflow/i })
    ).toBeInTheDocument();
  });

  it('does NOT show the Run button for archived workflows', () => {
    setup(makeWorkflow({ status: 'archived' }));
    expect(
      screen.queryByRole('button', { name: /Run workflow/i })
    ).not.toBeInTheDocument();
  });

  it('clicking Edit navigates to the edit page', async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole('button', { name: /Edit workflow/i }));
    expect(mockPush).toHaveBeenCalledWith('/workflows/wf-001/edit');
  });

  it('has a back navigation link to /workflows', () => {
    setup();
    const backLink = screen.getByRole('button', { name: /Back to workflows/i });
    expect(backLink).toBeInTheDocument();
  });
});

// ===========================================================================
// JOURNEY 8: Workflow Detail Page — executions tab
// ===========================================================================

describe('Journey 8: Workflow Detail Page — executions tab', () => {
  function setup(executions: WorkflowExecution[]) {
    mockUseWorkflow.mockReturnValue({
      data: makeWorkflow(),
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    mockUseWorkflowExecutions.mockReturnValue({
      data: executions,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    renderWithProviders(<WorkflowDetailPage />);
  }

  it('renders execution list after clicking Executions tab', async () => {
    const user = userEvent.setup();
    setup([makeExecution({ status: 'completed' })]);
    await user.click(screen.getByRole('tab', { name: /Executions/i }));
    await waitFor(() => {
      // The executions list renders with aria-label
      expect(screen.getByRole('list', { name: /Workflow execution history/i })).toBeInTheDocument();
    });
  });

  it('shows "No executions yet" when there are no runs', async () => {
    const user = userEvent.setup();
    setup([]);
    await user.click(screen.getByRole('tab', { name: /Executions/i }));
    await waitFor(() => {
      expect(screen.getByText(/No executions yet/i)).toBeInTheDocument();
    });
  });

  it('shows execution status in the list', async () => {
    const user = userEvent.setup();
    setup([makeExecution({ status: 'completed' })]);
    await user.click(screen.getByRole('tab', { name: /Executions/i }));
    await waitFor(() => {
      expect(screen.getByText(/Completed/i)).toBeInTheDocument();
    });
  });
});

// ===========================================================================
// JOURNEY 9: All Executions Page — renders and interacts
// ===========================================================================

describe('Journey 9: All Executions Page — table renders and interactions', () => {
  it('renders the "All Executions" heading', () => {
    mockUseWorkflowExecutions.mockReturnValue({
      data: [makeExecution()],
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<AllExecutionsPage />);
    expect(screen.getByRole('heading', { name: /All Executions/i })).toBeInTheDocument();
  });

  it('renders table rows for each execution', () => {
    mockUseWorkflowExecutions.mockReturnValue({
      data: [
        makeExecution({ id: 'exec-001', workflowName: 'Workflow Alpha' }),
        makeExecution({ id: 'exec-002', workflowName: 'Workflow Beta' }),
      ],
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<AllExecutionsPage />);
    expect(screen.getByText('Workflow Alpha')).toBeInTheDocument();
    expect(screen.getByText('Workflow Beta')).toBeInTheDocument();
  });

  it('renders table skeleton while loading', () => {
    mockUseWorkflowExecutions.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    const { container } = renderWithProviders(<AllExecutionsPage />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('clicking a row navigates to the execution detail page', async () => {
    const user = userEvent.setup();
    mockUseWorkflowExecutions.mockReturnValue({
      data: [makeExecution({ id: 'exec-001', workflowId: 'wf-001', workflowName: 'Alpha' })],
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<AllExecutionsPage />);

    const row = screen.getByRole('link', { name: /View execution .+ for Alpha/i });
    await user.click(row);
    expect(mockPush).toHaveBeenCalledWith('/workflows/wf-001/executions/exec-001');
  });

  it('shows the sort toggle button', () => {
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, isError: false });
    renderWithProviders(<AllExecutionsPage />);
    expect(
      screen.getByRole('button', { name: /Sort by started date/i })
    ).toBeInTheDocument();
  });

  it('clicking the sort toggle changes sort order label', async () => {
    const user = userEvent.setup();
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, isError: false });
    renderWithProviders(<AllExecutionsPage />);

    const sortBtn = screen.getByRole('button', { name: /Sort by started date/i });
    expect(screen.getByText(/Newest first/i)).toBeInTheDocument();
    await user.click(sortBtn);
    await waitFor(() => {
      expect(screen.getByText(/Oldest first/i)).toBeInTheDocument();
    });
  });

  it('renders the status filter combobox', () => {
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, isError: false });
    renderWithProviders(<AllExecutionsPage />);
    expect(screen.getByRole('combobox', { name: /Filter by status/i })).toBeInTheDocument();
  });
});

// ===========================================================================
// JOURNEY 10: All Executions Page — empty states
// ===========================================================================

describe('Journey 10: All Executions Page — empty states', () => {
  it('shows "No executions yet" empty state when list is empty and no filter', () => {
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, isError: false });
    renderWithProviders(<AllExecutionsPage />);
    expect(screen.getByText(/No executions yet/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Browse Workflows/i })).toBeInTheDocument();
  });

  it('shows "No executions found" when filtered results are empty', async () => {
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, isError: false });
    renderWithProviders(<AllExecutionsPage />);

    // Open the status filter and choose a specific status
    fireEvent.click(screen.getByRole('combobox', { name: /Filter by status/i }));
    await waitFor(() => screen.getByRole('option', { name: 'Running' }));
    fireEvent.click(screen.getByRole('option', { name: 'Running' }));

    await waitFor(() => {
      expect(screen.getByText(/No executions found/i)).toBeInTheDocument();
    });
  });

  it('shows Clear filters buttons in the filter empty state', async () => {
    mockUseWorkflowExecutions.mockReturnValue({ data: [], isLoading: false, isError: false });
    renderWithProviders(<AllExecutionsPage />);

    fireEvent.click(screen.getByRole('combobox', { name: /Filter by status/i }));
    await waitFor(() => screen.getByRole('option', { name: 'Failed' }));
    fireEvent.click(screen.getByRole('option', { name: 'Failed' }));

    await waitFor(() => {
      // Multiple "Clear filters" buttons may appear (toolbar + empty state)
      const clearBtns = screen.getAllByRole('button', { name: /Clear filters/i });
      expect(clearBtns.length).toBeGreaterThanOrEqual(1);
    });
  });
});

// ===========================================================================
// JOURNEY 11: All Executions Page — error state
// ===========================================================================

describe('Journey 11: All Executions Page — error state', () => {
  it('shows an error alert when the hook returns isError=true', () => {
    mockUseWorkflowExecutions.mockReturnValue({ data: undefined, isLoading: false, isError: true });
    renderWithProviders(<AllExecutionsPage />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Failed to load executions/i)).toBeInTheDocument();
  });
});

// ===========================================================================
// JOURNEY 12: Workflow Builder — create mode
// ===========================================================================

/**
 * useWorkflowBuilder returns: { state, dispatch, createNewStage, toCreateRequest, toUpdateRequest }
 * BuilderState shape: { name, description, stages, parameters, tags, contextPolicy,
 *   selectedStageIndex, isEditorOpen, isDirty, isSaving, originalWorkflow }
 */
function makeBuilderState(overrides: Record<string, unknown> = {}) {
  return {
    state: {
      name: '',
      description: '',
      stages: [],
      parameters: [],
      tags: [],
      contextPolicy: { globalModules: [] },
      selectedStageIndex: null,
      isEditorOpen: false,
      isDirty: false,
      isSaving: false,
      originalWorkflow: null,
      ...overrides,
    },
    dispatch: jest.fn(),
    createNewStage: jest.fn().mockReturnValue(makeStage()),
    toCreateRequest: jest.fn(),
    toUpdateRequest: jest.fn(),
  };
}

describe('Journey 12: Workflow Builder — create mode', () => {
  function setupBuilder(stateOverrides: Record<string, unknown> = {}) {
    mockUseWorkflowBuilder.mockReturnValue(makeBuilderState(stateOverrides));
    renderWithProviders(<WorkflowBuilderView />);
  }

  it('renders the InlineEdit field for the workflow name', () => {
    setupBuilder();
    // InlineEdit renders a button-like display element in view mode
    // with aria-label "Edit: Untitled Workflow" (placeholder text)
    const nameElement = screen.getByRole('button', { name: /Edit:/i });
    expect(nameElement).toBeInTheDocument();
  });

  it('renders the empty canvas with "Add your first stage" prompt when no stages exist', () => {
    setupBuilder();
    expect(
      screen.getByLabelText(/Empty workflow canvas/i)
    ).toBeInTheDocument();
  });

  it('shows the Save Draft button in the top bar', () => {
    setupBuilder();
    // aria-label is dynamic (depends on isDirty/isSaving) — query by visible text
    expect(screen.getByText('Save Draft')).toBeInTheDocument();
  });

  it('shows the Add Stage button in the empty canvas', () => {
    setupBuilder();
    const addBtn = screen.getByRole('button', { name: /Add your first stage/i });
    expect(addBtn).toBeInTheDocument();
  });

  it('clicking Add Stage dispatches an ADD_STAGE action', async () => {
    const user = userEvent.setup();
    const dispatch = jest.fn();
    const createNewStage = jest.fn().mockReturnValue(makeStage());
    mockUseWorkflowBuilder.mockReturnValue({
      ...makeBuilderState(),
      dispatch,
      createNewStage,
    });
    renderWithProviders(<WorkflowBuilderView />);

    await user.click(screen.getByRole('button', { name: /Add your first stage/i }));
    expect(dispatch).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'ADD_STAGE' })
    );
  });
});

// ===========================================================================
// JOURNEY 13: Workflow Builder — edit mode with existing stages
// ===========================================================================

describe('Journey 13: Workflow Builder — edit mode', () => {
  function setupBuilderWithStages(stages: WorkflowStage[]) {
    mockUseWorkflowBuilder.mockReturnValue(
      makeBuilderState({ name: 'My Workflow', stages, isDirty: false })
    );
    renderWithProviders(
      <WorkflowBuilderView existingWorkflow={makeWorkflow({ stages })} />
    );
  }

  it('renders stage cards for each existing stage', () => {
    setupBuilderWithStages([
      makeStage({ id: 's-1', name: 'Build', orderIndex: 0 }),
      makeStage({ id: 's-2', name: 'Deploy', orderIndex: 1 }),
    ]);
    expect(screen.getByText('Build')).toBeInTheDocument();
    expect(screen.getByText('Deploy')).toBeInTheDocument();
  });

  it('does NOT show the empty canvas when stages are present', () => {
    setupBuilderWithStages([makeStage({ id: 's-1', name: 'Build', orderIndex: 0 })]);
    expect(screen.queryByLabelText(/Empty workflow canvas/i)).not.toBeInTheDocument();
  });
});

// ===========================================================================
// JOURNEY 14: Mobile viewport — library page
// ===========================================================================

describe('Journey 14: Mobile viewport — library page', () => {
  const MOBILE_WIDTH = 375;
  const MOBILE_HEIGHT = 812;

  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: MOBILE_WIDTH,
    });
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: MOBILE_HEIGHT,
    });
    window.dispatchEvent(new Event('resize'));
  });

  afterEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: 768,
    });
  });

  it('renders the Workflows heading at mobile width', () => {
    mockUseWorkflows.mockReturnValue({
      data: { items: [makeWorkflow()] },
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<WorkflowsPage />);
    expect(screen.getByRole('heading', { name: /Workflows/i })).toBeInTheDocument();
  });

  it('renders the New Workflow button at mobile width', () => {
    mockUseWorkflows.mockReturnValue({ data: { items: [] }, isLoading: false, isError: false });
    renderWithProviders(<WorkflowsPage />);
    // The "New Workflow" CTA in the empty state or page header
    const newBtn = screen.getAllByRole('link', { name: /New Workflow/i });
    expect(newBtn.length).toBeGreaterThanOrEqual(1);
  });

  it('renders the search bar at mobile width', () => {
    mockUseWorkflows.mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
    });
    renderWithProviders(<WorkflowsPage />);
    expect(
      screen.getByRole('searchbox', { name: /Search workflows/i })
    ).toBeInTheDocument();
  });
});

// ===========================================================================
// JOURNEY 15: Mobile viewport — detail page
// ===========================================================================

describe('Journey 15: Mobile viewport — workflow detail page', () => {
  const MOBILE_WIDTH = 375;

  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: MOBILE_WIDTH,
    });
    window.dispatchEvent(new Event('resize'));
  });

  afterEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  it('renders the workflow name heading at mobile width', () => {
    mockUseWorkflow.mockReturnValue({
      data: makeWorkflow({ name: 'Mobile Workflow' }),
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    mockUseWorkflowExecutions.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    renderWithProviders(<WorkflowDetailPage />);
    expect(screen.getByRole('heading', { name: 'Mobile Workflow' })).toBeInTheDocument();
  });

  it('renders tab navigation at mobile width', () => {
    mockUseWorkflow.mockReturnValue({
      data: makeWorkflow(),
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    mockUseWorkflowExecutions.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
    renderWithProviders(<WorkflowDetailPage />);
    expect(screen.getByRole('tab', { name: /Stages/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Executions/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Settings/i })).toBeInTheDocument();
  });
});
