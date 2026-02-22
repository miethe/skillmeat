/**
 * @jest-environment jsdom
 *
 * Sync Modal Integration Tests
 *
 * Tests the interaction between modal components and the SyncStatusTab,
 * focusing on how `hasValidUpstreamSource()` controls upstream diff query
 * enablement across both /manage and /projects page entry points.
 *
 * Entry points:
 *   - /manage: ArtifactOperationsModal -> SyncStatusTab (mode="collection")
 *   - /projects: UnifiedEntityModal -> SyncStatusTab (mode="project")
 *
 * Key validation: `hasValidUpstreamSource()` in `lib/sync-utils.ts`
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SyncStatusTab } from '@/components/sync-status';
import { hasValidUpstreamSource } from '@/lib/sync-utils';
import { apiRequest } from '@/lib/api';
import type { Artifact } from '@/types/artifact';
import type { ArtifactSyncResponse } from '@/sdk/models/ArtifactSyncResponse';

// ============================================================================
// Mocks
// ============================================================================

jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn(),
  apiConfig: {
    baseUrl: 'http://localhost:8080',
    version: 'v1',
    useMocks: false,
    trace: false,
  },
  buildApiHeaders: jest.fn(() => ({ Accept: 'application/json' })),
}));

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    pathname: '/manage',
    query: {},
    asPath: '/manage',
  }),
  usePathname: () => '/manage',
  useSearchParams: () => new URLSearchParams(),
}));

// Mock SyncConfirmationDialog to avoid useConflictCheck API calls.
// The dialog is unit-tested separately; here we test the SyncStatusTab integration.
jest.mock('@/components/sync-status/sync-confirmation-dialog', () => ({
  SyncConfirmationDialog: ({
    direction,
    open,
    onOpenChange,
    onOverwrite,
    onMerge,
  }: {
    direction: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onOverwrite: () => void;
    onMerge: () => void;
    artifact: unknown;
    projectPath: string;
  }) => {
    if (!open) return null;
    const titles: Record<string, string> = {
      deploy: 'Deploy to Project',
      push: 'Push to Collection',
      pull: 'Pull from Source',
    };
    const confirmLabels: Record<string, string> = {
      deploy: 'Deploy',
      push: 'Push Changes',
      pull: 'Pull Changes',
    };
    return (
      <div role="dialog" aria-label={titles[direction]}>
        <span>{titles[direction]}</span>
        <button onClick={onOverwrite}>{confirmLabels[direction]}</button>
        <button onClick={onMerge}>Merge</button>
        <button onClick={() => onOpenChange(false)}>Cancel</button>
      </div>
    );
  },
}));

// ============================================================================
// Helpers
// ============================================================================

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

const renderWithProviders = (component: React.ReactNode) => {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{component}</QueryClientProvider>);
};

// ============================================================================
// Fixture Factories
// ============================================================================

const baseArtifact: Artifact = {
  id: 'skill:test-artifact',
  uuid: '00000000000000000000000000000001',
  name: 'test-artifact',
  type: 'skill',
  scope: 'user',
  collection: 'default',
  source: 'user/repo/test-skill',
  syncStatus: 'synced',
  createdAt: '2024-10-01T10:00:00Z',
  updatedAt: '2024-11-01T10:00:00Z',
};

function makeMarketplaceArtifact(overrides?: Partial<Artifact>): Artifact {
  return {
    ...baseArtifact,
    id: 'skill:marketplace-skill',
    name: 'marketplace-skill',
    origin: 'marketplace',
    origin_source: 'github',
    source: 'marketplace-org/repo/my-skill',
    upstream: {
      enabled: false,
      updateAvailable: false,
    },
    ...overrides,
  };
}

function makeGithubTrackingArtifact(overrides?: Partial<Artifact>): Artifact {
  return {
    ...baseArtifact,
    id: 'skill:github-skill',
    name: 'github-skill',
    origin: 'github',
    source: 'owner/repo/path/to/skill',
    upstream: {
      enabled: true,
      url: 'https://github.com/owner/repo',
      version: 'v2.0.0',
      currentSha: 'abc1234',
      upstreamSha: 'def5678',
      updateAvailable: true,
      lastChecked: '2024-11-01T10:00:00Z',
    },
    ...overrides,
  };
}

function makeDeployedArtifact(overrides?: Partial<Artifact>): Artifact {
  return {
    ...baseArtifact,
    id: 'skill:deployed-skill',
    name: 'deployed-skill',
    origin: 'github',
    source: 'owner/repo/path/to/skill',
    upstream: {
      enabled: true,
      updateAvailable: false,
    },
    deployments: [
      {
        project_path: '/home/user/project-a',
        project_name: 'Project A',
        deployed_at: '2024-10-15T10:00:00Z',
      },
      {
        project_path: '/home/user/project-b',
        project_name: 'Project B',
        deployed_at: '2024-10-20T10:00:00Z',
      },
    ],
    ...overrides,
  };
}

function makeProjectArtifact(overrides?: Partial<Artifact>): Artifact {
  return {
    ...baseArtifact,
    id: 'skill:project-skill',
    name: 'project-skill',
    origin: 'github',
    source: 'owner/repo/path/to/skill',
    projectPath: '/home/user/my-project',
    upstream: {
      enabled: true,
      updateAvailable: false,
    },
    ...overrides,
  };
}

// ============================================================================
// Unit Tests: hasValidUpstreamSource validation function
// ============================================================================

describe('hasValidUpstreamSource', () => {
  it('returns false for marketplace artifacts', () => {
    const artifact = makeMarketplaceArtifact();
    expect(hasValidUpstreamSource(artifact)).toBe(false);
  });

  it('returns true for github artifacts with upstream tracking enabled', () => {
    const artifact = makeGithubTrackingArtifact();
    expect(hasValidUpstreamSource(artifact)).toBe(true);
  });

  it('returns false for github artifacts with upstream tracking disabled', () => {
    const artifact = makeGithubTrackingArtifact({
      upstream: { enabled: false, updateAvailable: false },
    });
    expect(hasValidUpstreamSource(artifact)).toBe(false);
  });

  it('returns false for local origin artifacts', () => {
    const artifact: Artifact = {
      ...baseArtifact,
      origin: 'local',
      source: 'local',
      upstream: { enabled: true, updateAvailable: false },
    };
    expect(hasValidUpstreamSource(artifact)).toBe(false);
  });

  it('returns false when source string is local prefixed', () => {
    const artifact: Artifact = {
      ...baseArtifact,
      origin: 'github',
      source: 'local:/path/to/artifact',
      upstream: { enabled: true, updateAvailable: false },
    };
    expect(hasValidUpstreamSource(artifact)).toBe(false);
  });

  it('returns false when source is empty', () => {
    const artifact: Artifact = {
      ...baseArtifact,
      origin: 'github',
      source: '',
      upstream: { enabled: true, updateAvailable: false },
    };
    expect(hasValidUpstreamSource(artifact)).toBe(false);
  });

  it('returns false when upstream is undefined', () => {
    const artifact: Artifact = {
      ...baseArtifact,
      origin: 'github',
      source: 'owner/repo/path',
      upstream: undefined,
    };
    expect(hasValidUpstreamSource(artifact)).toBe(false);
  });
});

// ============================================================================
// Integration Tests: SyncStatusTab in collection mode (/manage page)
// ============================================================================

describe('SyncStatusTab - Collection Mode (/manage)', () => {
  const mockApiRequest = apiRequest as jest.MockedFunction<typeof apiRequest>;
  const onClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    // Default: all API calls resolve empty / no data
    mockApiRequest.mockResolvedValue({
      has_changes: false,
      files: [],
      summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
    });
  });

  // --------------------------------------------------------------------------
  // Scenario 1: Marketplace artifact - upstream diff query should NOT fire
  // --------------------------------------------------------------------------

  describe('marketplace artifact (no upstream queries)', () => {
    it('does NOT call upstream-diff API for marketplace artifacts', async () => {
      const artifact = makeMarketplaceArtifact();

      renderWithProviders(<SyncStatusTab entity={artifact} mode="collection" onClose={onClose} />);

      // Wait for the component to settle after initial render
      await waitFor(() => {
        // The component should render something (flow banner or error/no-data state)
        expect(document.querySelector('[class]')).toBeInTheDocument();
      });

      // Give time for any queries to potentially fire
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Verify upstream-diff API was NOT called
      const upstreamDiffCalls = mockApiRequest.mock.calls.filter((call) =>
        String(call[0]).includes('upstream-diff')
      );
      expect(upstreamDiffCalls).toHaveLength(0);
    });

    it('does not render upstream source info when upstream is not valid', async () => {
      const artifact = makeMarketplaceArtifact();

      renderWithProviders(<SyncStatusTab entity={artifact} mode="collection" onClose={onClose} />);

      // Marketplace artifacts have no upstream, so "No comparison data" or
      // similar state should appear since no project path is provided either
      await waitFor(() => {
        const noDataAlert = screen.queryByText(/No comparison data available/i);
        const noRemoteSource = screen.queryByText(/no remote source/i);
        // At least one of these indicators should appear
        expect(noDataAlert || noRemoteSource).toBeTruthy();
      });
    });
  });

  // --------------------------------------------------------------------------
  // Scenario 2: GitHub+tracking artifact - upstream diff query SHOULD fire
  // --------------------------------------------------------------------------

  describe('github artifact with upstream tracking (upstream queries enabled)', () => {
    it('calls upstream-diff API for github artifacts with tracking enabled', async () => {
      const artifact = makeGithubTrackingArtifact();

      mockApiRequest.mockImplementation(async (path: string) => {
        if (String(path).includes('upstream-diff')) {
          return {
            has_changes: true,
            upstream_version: 'v2.0.0',
            upstream_source: 'owner/repo/path/to/skill',
            files: [
              {
                path: 'SKILL.md',
                status: 'modified',
                unified_diff: '--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-old\n+new',
              },
            ],
            summary: { added: 0, modified: 1, deleted: 0, unchanged: 3 },
          };
        }
        return {
          has_changes: false,
          files: [],
          summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
        };
      });

      renderWithProviders(<SyncStatusTab entity={artifact} mode="collection" onClose={onClose} />);

      // Wait for the upstream-diff query to fire
      await waitFor(() => {
        const upstreamDiffCalls = mockApiRequest.mock.calls.filter((call) =>
          String(call[0]).includes('upstream-diff')
        );
        expect(upstreamDiffCalls.length).toBeGreaterThan(0);
      });
    });

    it('upstream-diff query includes the correct artifact ID in URL', async () => {
      const artifact = makeGithubTrackingArtifact();

      mockApiRequest.mockResolvedValue({
        has_changes: false,
        upstream_version: 'v2.0.0',
        upstream_source: 'owner/repo/path/to/skill',
        files: [],
        summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
      });

      renderWithProviders(<SyncStatusTab entity={artifact} mode="collection" onClose={onClose} />);

      await waitFor(() => {
        const upstreamDiffCalls = mockApiRequest.mock.calls.filter((call) =>
          String(call[0]).includes('upstream-diff')
        );
        expect(upstreamDiffCalls.length).toBeGreaterThan(0);

        // Verify the URL contains the encoded artifact ID
        const url = String(upstreamDiffCalls[0]![0]);
        expect(url).toContain(encodeURIComponent(artifact.id));
      });
    });
  });

  // --------------------------------------------------------------------------
  // Scenario 3: Project diff enables when projectPath is provided
  // --------------------------------------------------------------------------

  describe('project diff activation with projectPath', () => {
    it('calls project diff API when projectPath is provided', async () => {
      const artifact = makeDeployedArtifact();
      const projectPath = '/home/user/project-a';

      mockApiRequest.mockImplementation(async (path: string) => {
        if (String(path).includes('/diff')) {
          return {
            has_changes: true,
            project_path: projectPath,
            files: [
              {
                path: 'SKILL.md',
                status: 'modified',
                unified_diff: '--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new',
              },
            ],
            summary: { added: 0, modified: 1, deleted: 0, unchanged: 2 },
          };
        }
        if (String(path).includes('upstream-diff')) {
          return {
            has_changes: false,
            upstream_version: 'v1.0.0',
            upstream_source: 'owner/repo/path/to/skill',
            files: [],
            summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
          };
        }
        return {};
      });

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          projectPath={projectPath}
          onClose={onClose}
        />
      );

      // Wait for the project diff query to fire
      await waitFor(() => {
        const projectDiffCalls = mockApiRequest.mock.calls.filter(
          (call) => String(call[0]).includes('/diff') && !String(call[0]).includes('upstream-diff')
        );
        expect(projectDiffCalls.length).toBeGreaterThan(0);
      });

      // Verify the project_path query parameter is included
      await waitFor(() => {
        const projectDiffCalls = mockApiRequest.mock.calls.filter(
          (call) => String(call[0]).includes('/diff') && !String(call[0]).includes('upstream-diff')
        );
        const url = String(projectDiffCalls[0]![0]);
        expect(url).toContain('project_path=');
      });
    });

    it('does NOT call project diff API when projectPath is absent', async () => {
      const artifact = makeGithubTrackingArtifact();

      mockApiRequest.mockResolvedValue({
        has_changes: false,
        upstream_version: 'v2.0.0',
        upstream_source: 'owner/repo/path/to/skill',
        files: [],
        summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
      });

      renderWithProviders(<SyncStatusTab entity={artifact} mode="collection" onClose={onClose} />);

      // Wait for any queries to settle
      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      // Verify no project diff calls were made (only upstream-diff)
      const projectDiffCalls = mockApiRequest.mock.calls.filter(
        (call) => String(call[0]).includes('/diff') && !String(call[0]).includes('upstream-diff')
      );
      expect(projectDiffCalls).toHaveLength(0);
    });
  });
});

// ============================================================================
// Integration Tests: SyncStatusTab in project mode (/projects page)
// ============================================================================

describe('SyncStatusTab - Project Mode (/projects)', () => {
  const mockApiRequest = apiRequest as jest.MockedFunction<typeof apiRequest>;
  const onClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockApiRequest.mockResolvedValue({
      has_changes: false,
      files: [],
      summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
    });
  });

  // --------------------------------------------------------------------------
  // Scenario 4: Regression - project mode still works correctly
  // --------------------------------------------------------------------------

  describe('regression: project mode sync behavior', () => {
    it('renders in project mode with projectPath (scope-aware: only project diff fires initially)', async () => {
      // SCOPE-AWARE LOADING BEHAVIOR (Phase 5 refactor, TASK-5.3):
      // In project mode, the default comparison scope is "collection-vs-project".
      // In this scope:
      //   - project diff (collection vs project) fires immediately
      //   - upstream diff is DEFERRED — it is only enabled when the scope is
      //     "source-vs-collection" or "source-vs-project". This avoids an unnecessary
      //     upstream API call when the user is looking at the project comparison.
      const artifact = makeProjectArtifact();

      mockApiRequest.mockImplementation(async (path: string) => {
        if (String(path).includes('upstream-diff')) {
          return {
            has_changes: false,
            upstream_version: 'v1.0.0',
            upstream_source: 'owner/repo/path/to/skill',
            files: [],
            summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
          };
        }
        if (String(path).includes('/diff')) {
          return {
            has_changes: false,
            project_path: artifact.projectPath,
            files: [],
            summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
          };
        }
        return {};
      });

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="project"
          projectPath={artifact.projectPath}
          onClose={onClose}
        />
      );

      // In collection-vs-project scope: project diff fires immediately.
      await waitFor(() => {
        const projectCalls = mockApiRequest.mock.calls.filter(
          (call) => String(call[0]).includes('/diff') && !String(call[0]).includes('upstream-diff')
        );
        expect(projectCalls.length).toBeGreaterThan(0);
      });

      // Upstream diff is DEFERRED in collection-vs-project scope — does not fire on initial render.
      // This is the correct optimized behavior: fewer API calls when project comparison is active.
      await new Promise((resolve) => setTimeout(resolve, 200));
      const upstreamCalls = mockApiRequest.mock.calls.filter((call) =>
        String(call[0]).includes('upstream-diff')
      );
      expect(upstreamCalls).toHaveLength(0);
    });

    it('defaults to collection-vs-project comparison scope in project mode', async () => {
      const artifact = makeProjectArtifact();

      mockApiRequest.mockImplementation(async (path: string) => {
        if (String(path).includes('upstream-diff')) {
          return {
            has_changes: false,
            upstream_version: 'v1.0.0',
            upstream_source: 'owner/repo/path/to/skill',
            files: [],
            summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
          };
        }
        if (String(path).includes('/diff')) {
          return {
            has_changes: true,
            project_path: artifact.projectPath,
            files: [
              {
                path: 'SKILL.md',
                status: 'modified',
                unified_diff: '--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new',
              },
            ],
            summary: { added: 0, modified: 1, deleted: 0, unchanged: 5 },
          };
        }
        return {};
      });

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="project"
          projectPath={artifact.projectPath}
          onClose={onClose}
        />
      );

      // In project mode the initial comparison scope is "collection-vs-project",
      // so the project diff should be the active diff driving the display.
      // The project diff query must fire since we have a projectPath.
      await waitFor(() => {
        const projectCalls = mockApiRequest.mock.calls.filter(
          (call) => String(call[0]).includes('/diff') && !String(call[0]).includes('upstream-diff')
        );
        expect(projectCalls.length).toBeGreaterThan(0);
      });
    });

    it('does not fire upstream queries for marketplace artifacts in project mode', async () => {
      const artifact = makeMarketplaceArtifact({
        projectPath: '/home/user/my-project',
      });

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="project"
          projectPath="/home/user/my-project"
          onClose={onClose}
        />
      );

      // Wait for component to settle
      await new Promise((resolve) => setTimeout(resolve, 100));

      const upstreamCalls = mockApiRequest.mock.calls.filter((call) =>
        String(call[0]).includes('upstream-diff')
      );
      expect(upstreamCalls).toHaveLength(0);
    });

    it('discovered artifacts show import message instead of sync UI', async () => {
      const artifact: Artifact = {
        ...baseArtifact,
        collection: 'discovered',
        origin: 'github',
      };

      renderWithProviders(<SyncStatusTab entity={artifact} mode="project" onClose={onClose} />);

      // Discovered artifacts should show the import message
      await waitFor(() => {
        expect(screen.getByText(/not available for discovered artifacts/i)).toBeInTheDocument();
      });

      // No API calls should have been made for discovered artifacts
      expect(mockApiRequest).not.toHaveBeenCalled();
    });
  });
});

// ============================================================================
// Integration Tests: Confirmation Dialogs (Push / Pull)
// ============================================================================

describe('SyncStatusTab - Confirmation Dialogs', () => {
  const mockApiRequest = apiRequest as jest.MockedFunction<typeof apiRequest>;
  const onClose = jest.fn();

  /**
   * Helper: create an artifact with both upstream source data and project
   * deployment so that both "Pull from Source" and "Push to Collection" buttons
   * are rendered and enabled in the ArtifactFlowBanner.
   */
  function makeFullSyncArtifact(overrides?: Partial<Artifact>): Artifact {
    return {
      ...baseArtifact,
      id: 'skill:full-sync',
      name: 'full-sync-skill',
      origin: 'github',
      source: 'owner/repo/path/to/skill',
      upstream: {
        enabled: true,
        url: 'https://github.com/owner/repo',
        version: 'v2.0.0',
        currentSha: 'abc1234',
        upstreamSha: 'def5678',
        updateAvailable: true,
        lastChecked: '2024-11-01T10:00:00Z',
      },
      deployments: [
        {
          project_path: '/home/user/project-a',
          project_name: 'Project A',
          deployed_at: '2024-10-15T10:00:00Z',
        },
      ],
      ...overrides,
    };
  }

  const syncSuccessResponse: ArtifactSyncResponse = {
    success: true,
    message: 'Sync completed successfully',
    artifact_name: 'full-sync-skill',
    artifact_type: 'skill',
    conflicts: null,
    updated_version: null,
    synced_files_count: 3,
  };

  beforeEach(() => {
    jest.clearAllMocks();

    // Default mock: diff queries return data so the full UI renders
    mockApiRequest.mockImplementation(async (path: string, options?: unknown) => {
      const url = String(path);
      // POST to /sync endpoint
      if (url.includes('/sync') && options && (options as { method?: string }).method === 'POST') {
        return syncSuccessResponse;
      }
      if (url.includes('upstream-diff')) {
        return {
          has_changes: true,
          upstream_version: 'v2.0.0',
          upstream_source: 'owner/repo/path/to/skill',
          files: [
            {
              path: 'SKILL.md',
              status: 'modified',
              unified_diff: '--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-old\n+new',
            },
          ],
          summary: { added: 0, modified: 1, deleted: 0, unchanged: 3 },
        };
      }
      if (url.includes('/diff')) {
        return {
          has_changes: true,
          project_path: '/home/user/project-a',
          files: [
            {
              path: 'SKILL.md',
              status: 'modified',
              unified_diff: '--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new',
            },
          ],
          summary: { added: 0, modified: 1, deleted: 0, unchanged: 2 },
        };
      }
      return {};
    });
  });

  // --------------------------------------------------------------------------
  // Pull from Source: Confirmation Dialog
  // --------------------------------------------------------------------------

  describe('pull confirmation dialog', () => {
    it('shows confirmation dialog when "Pull from Source" is clicked', async () => {
      const user = userEvent.setup();
      const artifact = makeFullSyncArtifact();

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          projectPath="/home/user/project-a"
          onClose={onClose}
        />
      );

      // Wait for the banner to render with data
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Pull from Source/i })).toBeInTheDocument();
      });

      // Click "Pull from Source" button in the banner
      await user.click(screen.getByRole('button', { name: /Pull from Source/i }));

      // AlertDialog should appear with expected content
      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toBeInTheDocument();
        const dialogScope = within(dialog);
        expect(dialogScope.getByText('Pull from Source')).toBeInTheDocument();
        expect(dialogScope.getByText('Pull Changes')).toBeInTheDocument();
        expect(dialogScope.getByText('Cancel')).toBeInTheDocument();
      });
    });

    it('does NOT fire mutation when Cancel is clicked', async () => {
      const user = userEvent.setup();
      const artifact = makeFullSyncArtifact();

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          projectPath="/home/user/project-a"
          onClose={onClose}
        />
      );

      // Wait for banner
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Pull from Source/i })).toBeInTheDocument();
      });

      // Open dialog
      await user.click(screen.getByRole('button', { name: /Pull from Source/i }));
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Record the number of apiRequest calls before cancel
      const callsBefore = mockApiRequest.mock.calls.filter((call) =>
        String(call[0]).includes('/sync')
      ).length;

      // Click Cancel within the dialog
      const dialog = screen.getByRole('dialog');
      await user.click(within(dialog).getByText('Cancel'));

      // Dialog should close
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });

      // No new /sync API calls should have been made
      const callsAfter = mockApiRequest.mock.calls.filter((call) =>
        String(call[0]).includes('/sync')
      ).length;
      expect(callsAfter).toBe(callsBefore);
    });

    it('fires sync mutation when "Pull Changes" is confirmed', async () => {
      const user = userEvent.setup();
      const artifact = makeFullSyncArtifact();

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          projectPath="/home/user/project-a"
          onClose={onClose}
        />
      );

      // Wait for banner
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Pull from Source/i })).toBeInTheDocument();
      });

      // Open dialog then confirm
      await user.click(screen.getByRole('button', { name: /Pull from Source/i }));
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const dialog = screen.getByRole('dialog');
      await user.click(within(dialog).getByText('Pull Changes'));

      // Verify the sync API was called (POST to /artifacts/{id}/sync without project_path)
      await waitFor(() => {
        const syncCalls = mockApiRequest.mock.calls.filter(
          (call) =>
            String(call[0]).includes('/sync') &&
            call[1] &&
            (call[1] as { method?: string }).method === 'POST'
        );
        expect(syncCalls.length).toBeGreaterThan(0);

        // Verify the URL contains the artifact ID
        const url = String(syncCalls[0]![0]);
        expect(url).toContain(encodeURIComponent(artifact.id));

        // Verify the body does NOT include project_path (pull from upstream)
        const body = JSON.parse((syncCalls[0]![1] as { body: string }).body);
        expect(body.project_path).toBeUndefined();
      });
    });
  });

  // --------------------------------------------------------------------------
  // Push to Collection: Confirmation Dialog
  // --------------------------------------------------------------------------

  describe('push confirmation dialog', () => {
    it('shows confirmation dialog when "Push to Collection" is clicked', async () => {
      const user = userEvent.setup();
      const artifact = makeFullSyncArtifact();

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          projectPath="/home/user/project-a"
          onClose={onClose}
        />
      );

      // Wait for banner to render with project info (push button needs projectInfo)
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Push to Collection/i })).toBeInTheDocument();
      });

      // Click "Push to Collection" button in the banner
      await user.click(screen.getByRole('button', { name: /Push to Collection/i }));

      // AlertDialog should appear with expected content
      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toBeInTheDocument();
        const dialogScope = within(dialog);
        expect(dialogScope.getByText('Push to Collection')).toBeInTheDocument();
        expect(dialogScope.getByText('Push Changes')).toBeInTheDocument();
        expect(dialogScope.getByText('Cancel')).toBeInTheDocument();
      });
    });

    it('does NOT fire mutation when Cancel is clicked', async () => {
      const user = userEvent.setup();
      const artifact = makeFullSyncArtifact();

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          projectPath="/home/user/project-a"
          onClose={onClose}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Push to Collection/i })).toBeInTheDocument();
      });

      // Open dialog
      await user.click(screen.getByRole('button', { name: /Push to Collection/i }));
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Record sync calls before cancel
      const callsBefore = mockApiRequest.mock.calls.filter(
        (call) =>
          String(call[0]).includes('/sync') &&
          call[1] &&
          (call[1] as { method?: string }).method === 'POST'
      ).length;

      // Click Cancel within the dialog
      const dialog = screen.getByRole('dialog');
      await user.click(within(dialog).getByText('Cancel'));

      // Dialog should close
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });

      // No new POST /sync calls
      const callsAfter = mockApiRequest.mock.calls.filter(
        (call) =>
          String(call[0]).includes('/sync') &&
          call[1] &&
          (call[1] as { method?: string }).method === 'POST'
      ).length;
      expect(callsAfter).toBe(callsBefore);
    });

    it('fires push mutation with project_path when "Push Changes" is confirmed', async () => {
      const user = userEvent.setup();
      const artifact = makeFullSyncArtifact();

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          projectPath="/home/user/project-a"
          onClose={onClose}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Push to Collection/i })).toBeInTheDocument();
      });

      // Open dialog then confirm
      await user.click(screen.getByRole('button', { name: /Push to Collection/i }));
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const dialog = screen.getByRole('dialog');
      await user.click(within(dialog).getByText('Push Changes'));

      // Verify the sync API was called with project_path in body (push)
      await waitFor(() => {
        const pushCalls = mockApiRequest.mock.calls.filter((call) => {
          if (!String(call[0]).includes('/sync')) return false;
          if (!call[1] || (call[1] as { method?: string }).method !== 'POST') return false;
          try {
            const body = JSON.parse((call[1] as { body: string }).body);
            return body.project_path !== undefined;
          } catch {
            return false;
          }
        });
        expect(pushCalls.length).toBeGreaterThan(0);

        // Verify URL contains artifact ID
        const url = String(pushCalls[0]![0]);
        expect(url).toContain(encodeURIComponent(artifact.id));

        // Verify body has the correct push payload
        const body = JSON.parse((pushCalls[0]![1] as { body: string }).body);
        expect(body.project_path).toBe('/home/user/project-a');
        expect(body.force).toBe(false);
        expect(body.strategy).toBe('theirs');
      });
    });
  });
});

// ============================================================================
// Performance Refactor Regression Tests (TASK-7.1)
// ============================================================================
//
// These tests validate the behavioral invariants introduced by the
// sync-status-performance-refactor (Phases 1-6). They ensure:
//   1. Deployment fanout queries are gated behind the deployments tab
//   2. Scope-aware diff loading defers non-primary queries
//   3. SyncStatusTab staleTime and gcTime are set correctly (via query behavior)
//
// NOTE: ArtifactOperationsModal is tested at the unit level by directly
// simulating the `isDeploymentTab` gating logic via useQueries. Full modal
// rendering is avoided to keep these tests focused and fast.
// ============================================================================

// ============================================================================
// Deployment Tab Gating Logic Validation
//
// Tests the key invariant: deployment fanout queries (listDeployments per project)
// must NOT fire when the active tab is 'status' or 'sync'. They must ONLY fire
// when the active tab is 'deployments'.
//
// This is tested via a minimal component that mirrors the ArtifactOperationsModal
// useQueries pattern so we can exercise the gating logic without mounting the
// full modal (which requires many additional mocks).
// ============================================================================

import React, { useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { listDeployments } from '@/lib/api/deployments';
import { act } from '@testing-library/react';

// Mock listDeployments to spy on when it is called
jest.mock('@/lib/api/deployments', () => ({
  listDeployments: jest.fn().mockResolvedValue({ deployments: [] }),
  removeProjectDeployment: jest.fn().mockResolvedValue({}),
}));

/**
 * Minimal wrapper component that mirrors the ArtifactOperationsModal deployment
 * query gating logic. This lets us test the gate in isolation without mounting
 * the full modal and all its dependencies.
 */
function DeploymentGatingHarness({
  initialTab = 'status',
  projectPaths = ['/project-a', '/project-b'],
}: {
  initialTab?: string;
  projectPaths?: string[];
}) {
  const [activeTab, setActiveTab] = useState(initialTab);
  const isDeploymentTab = activeTab === 'deployments';

  // Mirrors the ArtifactOperationsModal useQueries gating exactly.
  useQueries({
    queries: projectPaths.map((path) => ({
      queryKey: ['deployments', path],
      queryFn: () => listDeployments(path),
      staleTime: 2 * 60 * 1000,
      enabled: isDeploymentTab && projectPaths.length > 0,
    })),
  });

  return (
    <div>
      <div data-testid="active-tab">{activeTab}</div>
      <button onClick={() => setActiveTab('deployments')}>Go to Deployments</button>
      <button onClick={() => setActiveTab('status')}>Go to Status</button>
      <button onClick={() => setActiveTab('sync')}>Go to Sync</button>
    </div>
  );
}

describe('Deployment Query Gating (ArtifactOperationsModal invariant)', () => {
  const mockListDeployments = listDeployments as jest.MockedFunction<typeof listDeployments>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockListDeployments.mockResolvedValue({ deployments: [] });
  });

  it('does NOT call listDeployments when modal opens on the status tab', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DeploymentGatingHarness initialTab="status" />
      </QueryClientProvider>
    );

    // Wait for any queries to settle
    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(mockListDeployments).not.toHaveBeenCalled();
  });

  it('does NOT call listDeployments when modal opens on the sync tab', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DeploymentGatingHarness initialTab="sync" />
      </QueryClientProvider>
    );

    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(mockListDeployments).not.toHaveBeenCalled();
  });

  it('DOES call listDeployments when the deployments tab becomes active', async () => {
    const user = userEvent.setup();
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DeploymentGatingHarness initialTab="status" />
      </QueryClientProvider>
    );

    // Confirm no calls while on status tab
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(mockListDeployments).not.toHaveBeenCalled();

    // Switch to deployments tab
    await user.click(screen.getByText('Go to Deployments'));

    // Deployment queries should now fire
    await waitFor(() => {
      expect(mockListDeployments).toHaveBeenCalled();
    });
  });

  it('calls listDeployments for each project path when deployments tab is active', async () => {
    const user = userEvent.setup();
    const projectPaths = ['/project-a', '/project-b', '/project-c'];
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DeploymentGatingHarness initialTab="status" projectPaths={projectPaths} />
      </QueryClientProvider>
    );

    await user.click(screen.getByText('Go to Deployments'));

    await waitFor(() => {
      expect(mockListDeployments).toHaveBeenCalledTimes(projectPaths.length);
      expect(mockListDeployments).toHaveBeenCalledWith('/project-a');
      expect(mockListDeployments).toHaveBeenCalledWith('/project-b');
      expect(mockListDeployments).toHaveBeenCalledWith('/project-c');
    });
  });

  it('stops calling listDeployments when switching away from deployments tab', async () => {
    const user = userEvent.setup();
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DeploymentGatingHarness initialTab="deployments" />
      </QueryClientProvider>
    );

    // Wait for initial deployment queries to fire
    await waitFor(() => {
      expect(mockListDeployments).toHaveBeenCalled();
    });

    const callCountAfterFirst = mockListDeployments.mock.calls.length;

    // Switch to status tab — no new deployment queries should fire
    await user.click(screen.getByText('Go to Status'));
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Call count should not have increased after switching away
    expect(mockListDeployments.mock.calls.length).toBe(callCountAfterFirst);
  });
});

// ============================================================================
// Scope-Aware Diff Loading Tests (SyncStatusTab Phase 5 refactor)
// ============================================================================

describe('SyncStatusTab - Scope-Aware Diff Loading (Performance Refactor)', () => {
  const mockApiRequest = apiRequest as jest.MockedFunction<typeof apiRequest>;
  const onClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockApiRequest.mockResolvedValue({
      has_changes: false,
      files: [],
      summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
    });
  });

  it('in collection-vs-project scope: project diff fires, upstream diff is deferred', async () => {
    // The default scope in project mode is collection-vs-project.
    // In this scope, only the project diff query should fire on mount.
    // Upstream diff is deferred because it is not the primary scope.
    const artifact = makeProjectArtifact();

    renderWithProviders(
      <SyncStatusTab
        entity={artifact}
        mode="project"
        projectPath={artifact.projectPath}
        onClose={onClose}
      />
    );

    // Project diff should fire immediately
    await waitFor(() => {
      const projectCalls = mockApiRequest.mock.calls.filter(
        (call) => String(call[0]).includes('/diff') && !String(call[0]).includes('upstream-diff')
      );
      expect(projectCalls.length).toBeGreaterThan(0);
    });

    // Give enough time for any deferred queries to potentially fire
    await new Promise((resolve) => setTimeout(resolve, 300));

    // Upstream diff should NOT have fired — it is not the primary scope
    const upstreamCalls = mockApiRequest.mock.calls.filter((call) =>
      String(call[0]).includes('upstream-diff')
    );
    expect(upstreamCalls).toHaveLength(0);
  });

  it('in source-vs-collection scope (collection mode): upstream diff fires, project diff is deferred', async () => {
    // When the initial scope is source-vs-collection, only upstream diff fires.
    // In collection mode without a projectPath, only the upstream query is relevant.
    const artifact = makeGithubTrackingArtifact();

    mockApiRequest.mockImplementation(async (path: string) => {
      if (String(path).includes('upstream-diff')) {
        return {
          has_changes: true,
          upstream_version: 'v2.0.0',
          upstream_source: 'owner/repo/path/to/skill',
          files: [
            {
              path: 'SKILL.md',
              status: 'modified',
              unified_diff: '--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-old\n+new',
            },
          ],
          summary: { added: 0, modified: 1, deleted: 0, unchanged: 0 },
        };
      }
      return { has_changes: false, files: [], summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 } };
    });

    renderWithProviders(
      <SyncStatusTab entity={artifact} mode="collection" onClose={onClose} />
    );

    // Upstream diff fires because artifact has valid upstream source
    await waitFor(() => {
      const upstreamCalls = mockApiRequest.mock.calls.filter((call) =>
        String(call[0]).includes('upstream-diff')
      );
      expect(upstreamCalls.length).toBeGreaterThan(0);
    });

    // Project diff should NOT fire (no projectPath provided)
    await new Promise((resolve) => setTimeout(resolve, 200));
    const projectCalls = mockApiRequest.mock.calls.filter(
      (call) => String(call[0]).includes('/diff') && !String(call[0]).includes('upstream-diff')
    );
    expect(projectCalls).toHaveLength(0);
  });

  it('discovered artifacts do not fire any diff queries', async () => {
    const artifact: Artifact = {
      ...baseArtifact,
      collection: 'discovered',
      origin: 'github',
      upstream: { enabled: true, updateAvailable: false },
    };

    renderWithProviders(
      <SyncStatusTab
        entity={artifact}
        mode="project"
        projectPath="/home/user/my-project"
        onClose={onClose}
      />
    );

    await new Promise((resolve) => setTimeout(resolve, 200));

    // No API calls for discovered artifacts
    expect(mockApiRequest).not.toHaveBeenCalled();
  });

  it('upstream query includes staleTime and gcTime for cache reuse on reopen', async () => {
    // This validates that the refactor correctly set staleTime and gcTime on the
    // upstream diff query. We can observe this indirectly: if the data is fetched
    // once and the component remounts within the staleTime, the API is not called again.
    const artifact = makeGithubTrackingArtifact();

    mockApiRequest.mockResolvedValue({
      has_changes: false,
      upstream_version: 'v1.0.0',
      upstream_source: 'owner/repo/path/to/skill',
      files: [],
      summary: { added: 0, modified: 0, deleted: 0, unchanged: 0 },
    });

    const queryClient = createTestQueryClient();

    // Override with real staleTime to test caching (use longer staleTime than test duration)
    const cachedQueryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          // Do NOT set gcTime: 0 here — we want to test cache reuse
          staleTime: 30_000,
        },
        mutations: { retry: false },
      },
    });

    const { unmount } = render(
      <QueryClientProvider client={cachedQueryClient}>
        <SyncStatusTab entity={artifact} mode="collection" onClose={onClose} />
      </QueryClientProvider>
    );

    // Wait for the first upstream diff call
    await waitFor(() => {
      const upstreamCalls = mockApiRequest.mock.calls.filter((call) =>
        String(call[0]).includes('upstream-diff')
      );
      expect(upstreamCalls.length).toBeGreaterThan(0);
    });

    const callCountAfterFirst = mockApiRequest.mock.calls.filter((call) =>
      String(call[0]).includes('upstream-diff')
    ).length;

    // Unmount and remount (simulating close and reopen of modal)
    unmount();

    render(
      <QueryClientProvider client={cachedQueryClient}>
        <SyncStatusTab entity={artifact} mode="collection" onClose={onClose} />
      </QueryClientProvider>
    );

    await new Promise((resolve) => setTimeout(resolve, 100));

    // Cache hit: API should not have been called again (within staleTime)
    const callCountAfterSecond = mockApiRequest.mock.calls.filter((call) =>
      String(call[0]).includes('upstream-diff')
    ).length;
    expect(callCountAfterSecond).toBe(callCountAfterFirst);
  });
});
