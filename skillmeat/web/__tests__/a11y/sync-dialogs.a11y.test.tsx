/**
 * Accessibility Tests for Sync Dialogs (SyncConfirmationDialog, DriftAlertBanner)
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Artifact } from '@/types/artifact';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock useConflictCheck hook BEFORE importing components
jest.mock('@/hooks', () => ({
  useConflictCheck: jest.fn(),
}));

// Mock DiffViewer to avoid deep rendering
jest.mock('@/components/entity/diff-viewer', () => ({
  DiffViewer: ({ files, leftLabel, rightLabel }: any) => (
    <div data-testid="diff-viewer" role="region" aria-label="Diff preview">
      <span>{leftLabel}</span>
      <span>{rightLabel}</span>
      <span>{files.length} files</span>
    </div>
  ),
}));

// Mock Skeleton for loading states
jest.mock('@/components/ui/skeleton', () => ({
  Skeleton: ({ className }: any) => (
    <div data-testid="skeleton" className={className} aria-busy="true" />
  ),
}));

// Now import components after mocks are set up
import { SyncConfirmationDialog } from '@/components/sync-status/sync-confirmation-dialog';
import { DriftAlertBanner } from '@/components/sync-status/drift-alert-banner';
import { useConflictCheck } from '@/hooks';
import type { ConflictCheckResult } from '@/hooks/use-conflict-check';

const mockUseConflictCheck = useConflictCheck as jest.MockedFunction<typeof useConflictCheck>;

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const mockArtifact: Artifact = {
  id: 'skill:test-skill',
  uuid: '00000000000000000000000000000001',
  name: 'test-skill',
  type: 'skill',
  scope: 'user',
  syncStatus: 'synced',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

const baseDialogProps = {
  artifact: mockArtifact,
  projectPath: '/path/to/project',
  open: true,
  onOpenChange: jest.fn(),
  onOverwrite: jest.fn(),
  onMerge: jest.fn(),
  onCancel: jest.fn(),
};

/** Hook return for loading state */
const loadingState: ConflictCheckResult = {
  diffData: undefined,
  hasChanges: false,
  hasConflicts: false,
  targetHasChanges: false,
  isLoading: true,
  error: null,
};

/** Hook return for error state */
const errorState: ConflictCheckResult = {
  diffData: undefined,
  hasChanges: false,
  hasConflicts: false,
  targetHasChanges: false,
  isLoading: false,
  error: new Error('Network error'),
};

/** Hook return for no-changes state */
const noChangesState: ConflictCheckResult = {
  diffData: {
    artifact_id: 'skill:test-skill',
    artifact_name: 'test-skill',
    artifact_type: 'skill',
    collection_name: 'default',
    project_path: '/path/to/project',
    has_changes: false,
    files: [],
    summary: {},
  },
  hasChanges: false,
  hasConflicts: false,
  targetHasChanges: false,
  isLoading: false,
  error: null,
};

/** Hook return for has-changes state */
const hasChangesState: ConflictCheckResult = {
  diffData: {
    artifact_id: 'skill:test-skill',
    artifact_name: 'test-skill',
    artifact_type: 'skill',
    collection_name: 'default',
    project_path: '/path/to/project',
    has_changes: true,
    files: [
      {
        file_path: 'SKILL.md',
        status: 'modified',
        collection_hash: 'aaa',
        project_hash: 'bbb',
        unified_diff: '- old\n+ new',
      },
    ],
    summary: { modified: 1 },
  },
  hasChanges: true,
  hasConflicts: false,
  targetHasChanges: true,
  isLoading: false,
  error: null,
};

const baseBannerProps = {
  summary: { added: 1, modified: 2, deleted: 0, unchanged: 5 },
  onViewDiffs: jest.fn(),
  onMerge: jest.fn(),
  onTakeUpstream: jest.fn(),
  onKeepLocal: jest.fn(),
};

// Axe rule overrides for known non-violations in dialog context.
// Dialog heading order may not match page-level h1, and Radix uses
// aria-describedby on DialogContent which can trigger region rules.
const dialogAxeRules = {
  rules: {
    'heading-order': { enabled: false },
  },
};

// ==========================================================================
// SyncConfirmationDialog — Accessibility Tests
// ==========================================================================

describe('SyncConfirmationDialog Accessibility', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient = createQueryClient();
  });

  // -----------------------------------------------------------------------
  // Direction variants — axe scans
  // -----------------------------------------------------------------------

  describe.each<'deploy' | 'push' | 'pull'>(['deploy', 'push', 'pull'])(
    'direction=%s',
    (direction) => {
      it('should have no axe violations with no changes', async () => {
        mockUseConflictCheck.mockReturnValue(noChangesState);

        const { container } = render(
          <SyncConfirmationDialog {...baseDialogProps} direction={direction} />,
          { wrapper: createWrapper(queryClient) }
        );

        const results = await axe(container, dialogAxeRules);
        expect(results).toHaveNoViolations();
      });

      it('should have no axe violations with changes present', async () => {
        mockUseConflictCheck.mockReturnValue(hasChangesState);

        const { container } = render(
          <SyncConfirmationDialog {...baseDialogProps} direction={direction} />,
          { wrapper: createWrapper(queryClient) }
        );

        const results = await axe(container, dialogAxeRules);
        expect(results).toHaveNoViolations();
      });
    }
  );

  // -----------------------------------------------------------------------
  // Loading state
  // -----------------------------------------------------------------------

  it('should have no axe violations in loading state', async () => {
    mockUseConflictCheck.mockReturnValue(loadingState);

    const { container } = render(
      <SyncConfirmationDialog {...baseDialogProps} direction="deploy" />,
      { wrapper: createWrapper(queryClient) }
    );

    const results = await axe(container, dialogAxeRules);
    expect(results).toHaveNoViolations();
  });

  // -----------------------------------------------------------------------
  // Error state
  // -----------------------------------------------------------------------

  it('should have no axe violations in error state', async () => {
    mockUseConflictCheck.mockReturnValue(errorState);

    const { container } = render(
      <SyncConfirmationDialog {...baseDialogProps} direction="deploy" />,
      { wrapper: createWrapper(queryClient) }
    );

    const results = await axe(container, dialogAxeRules);
    expect(results).toHaveNoViolations();
  });

  // -----------------------------------------------------------------------
  // Focus management
  // -----------------------------------------------------------------------

  it('should move focus into the dialog when opened', async () => {
    mockUseConflictCheck.mockReturnValue(noChangesState);

    render(<SyncConfirmationDialog {...baseDialogProps} direction="deploy" />, {
      wrapper: createWrapper(queryClient),
    });

    // Radix Dialog moves focus to the first focusable element inside DialogContent.
    // Wait for the dialog to be fully rendered and focus to settle.
    await waitFor(() => {
      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
      // Active element should be inside the dialog
      expect(dialog.contains(document.activeElement)).toBe(true);
    });
  });

  it('should close dialog when Escape key is pressed', async () => {
    const user = userEvent.setup();
    mockUseConflictCheck.mockReturnValue(noChangesState);

    render(<SyncConfirmationDialog {...baseDialogProps} direction="deploy" />, {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    await user.keyboard('{Escape}');

    // Radix Dialog calls onOpenChange(false) on Escape
    expect(baseDialogProps.onOpenChange).toHaveBeenCalledWith(false);
  });

  // -----------------------------------------------------------------------
  // Button accessible labels
  // -----------------------------------------------------------------------

  it('should have accessible labels on all buttons (no changes)', async () => {
    mockUseConflictCheck.mockReturnValue(noChangesState);

    render(<SyncConfirmationDialog {...baseDialogProps} direction="deploy" />, {
      wrapper: createWrapper(queryClient),
    });

    // Cancel button
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    expect(cancelButton).toBeInTheDocument();

    // Confirm button (when no changes, shows "Confirm")
    const confirmButton = screen.getByRole('button', { name: /confirm/i });
    expect(confirmButton).toBeInTheDocument();

    // Close button (Radix renders a close X button)
    const closeButton = screen.getByRole('button', { name: /close/i });
    expect(closeButton).toBeInTheDocument();
  });

  it('should have accessible labels on all buttons (with changes)', async () => {
    mockUseConflictCheck.mockReturnValue(hasChangesState);

    render(<SyncConfirmationDialog {...baseDialogProps} direction="deploy" />, {
      wrapper: createWrapper(queryClient),
    });

    // Cancel button
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();

    // Deploy/overwrite button
    expect(screen.getByRole('button', { name: /deploy/i })).toBeInTheDocument();

    // Merge button (shown when hasChanges and targetHasChanges)
    expect(screen.getByRole('button', { name: /merge/i })).toBeInTheDocument();
  });

  it('should have accessible labels on push direction buttons', async () => {
    mockUseConflictCheck.mockReturnValue(hasChangesState);

    render(<SyncConfirmationDialog {...baseDialogProps} direction="push" />, {
      wrapper: createWrapper(queryClient),
    });

    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /push changes/i })).toBeInTheDocument();
  });

  it('should have accessible labels on pull direction buttons', async () => {
    mockUseConflictCheck.mockReturnValue(hasChangesState);

    render(<SyncConfirmationDialog {...baseDialogProps} direction="pull" />, {
      wrapper: createWrapper(queryClient),
    });

    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /pull changes/i })).toBeInTheDocument();
  });
});

// ==========================================================================
// DriftAlertBanner — Accessibility Tests
// ==========================================================================

describe('DriftAlertBanner Accessibility', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // -----------------------------------------------------------------------
  // Status variants — axe scans
  // -----------------------------------------------------------------------

  describe.each<'none' | 'modified' | 'conflict' | 'outdated'>([
    'none',
    'modified',
    'conflict',
    'outdated',
  ])('driftStatus=%s', (driftStatus) => {
    it('should have no axe violations', async () => {
      const { container } = render(
        <DriftAlertBanner
          {...baseBannerProps}
          driftStatus={driftStatus}
          comparisonScope="collection-vs-project"
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // -----------------------------------------------------------------------
  // Alert role
  // -----------------------------------------------------------------------

  it('should have an alert role element present', () => {
    render(
      <DriftAlertBanner
        {...baseBannerProps}
        driftStatus="modified"
        comparisonScope="collection-vs-project"
      />
    );

    // Radix Alert renders with role="alert" for destructive or default variant
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Action button accessible names — modified status
  // -----------------------------------------------------------------------

  it('should have accessible names on action buttons for modified status', () => {
    render(
      <DriftAlertBanner
        {...baseBannerProps}
        driftStatus="modified"
        comparisonScope="collection-vs-project"
      />
    );

    // modified shows: View Diffs, Take Upstream, Keep Local
    expect(screen.getByRole('button', { name: /view diffs/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /take upstream/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /keep local/i })).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Action button accessible names — conflict status
  // -----------------------------------------------------------------------

  it('should have accessible names on action buttons for conflict status', () => {
    render(
      <DriftAlertBanner
        {...baseBannerProps}
        driftStatus="conflict"
        comparisonScope="source-vs-collection"
      />
    );

    // conflict shows: View Diffs, Merge..., Take Upstream, Keep Local
    expect(screen.getByRole('button', { name: /view diffs/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /merge/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /take upstream/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /keep local/i })).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Action button accessible names — outdated status
  // -----------------------------------------------------------------------

  it('should have accessible names on action buttons for outdated status', () => {
    render(
      <DriftAlertBanner
        {...baseBannerProps}
        driftStatus="outdated"
        comparisonScope="source-vs-project"
      />
    );

    // outdated shows: View Diffs, Pull Updates (not "Take Upstream")
    expect(screen.getByRole('button', { name: /view diffs/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /pull updates/i })).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // No action buttons for "none" status
  // -----------------------------------------------------------------------

  it('should not render action buttons when driftStatus is none', () => {
    render(
      <DriftAlertBanner
        {...baseBannerProps}
        driftStatus="none"
        comparisonScope="collection-vs-project"
      />
    );

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Axe across all comparison scopes
  // -----------------------------------------------------------------------

  describe.each<'collection-vs-project' | 'source-vs-collection' | 'source-vs-project'>([
    'collection-vs-project',
    'source-vs-collection',
    'source-vs-project',
  ])('comparisonScope=%s', (scope) => {
    it('should have no axe violations with conflict status', async () => {
      const { container } = render(
        <DriftAlertBanner {...baseBannerProps} driftStatus="conflict" comparisonScope={scope} />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
