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
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SyncStatusTab } from '@/components/sync-status';
import { hasValidUpstreamSource } from '@/lib/sync-utils';
import { apiRequest } from '@/lib/api';
import type { Artifact } from '@/types/artifact';

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

jest.mock('@/lib/api/context-sync', () => ({
  pullChanges: jest.fn().mockResolvedValue({}),
  pushChanges: jest.fn().mockResolvedValue({}),
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

// ============================================================================
// Helpers
// ============================================================================

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Suppress error logs in tests
    },
  });

const renderWithProviders = (component: React.ReactNode) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
};

// ============================================================================
// Fixture Factories
// ============================================================================

const baseArtifact: Artifact = {
  id: 'skill:test-artifact',
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

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          onClose={onClose}
        />
      );

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

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          onClose={onClose}
        />
      );

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

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          onClose={onClose}
        />
      );

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

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          onClose={onClose}
        />
      );

      await waitFor(() => {
        const upstreamDiffCalls = mockApiRequest.mock.calls.filter((call) =>
          String(call[0]).includes('upstream-diff')
        );
        expect(upstreamDiffCalls.length).toBeGreaterThan(0);

        // Verify the URL contains the encoded artifact ID
        const url = String(upstreamDiffCalls[0][0]);
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
          (call) =>
            String(call[0]).includes('/diff') &&
            !String(call[0]).includes('upstream-diff')
        );
        expect(projectDiffCalls.length).toBeGreaterThan(0);
      });

      // Verify the project_path query parameter is included
      await waitFor(() => {
        const projectDiffCalls = mockApiRequest.mock.calls.filter(
          (call) =>
            String(call[0]).includes('/diff') &&
            !String(call[0]).includes('upstream-diff')
        );
        const url = String(projectDiffCalls[0][0]);
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

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="collection"
          onClose={onClose}
        />
      );

      // Wait for any queries to settle
      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalled();
      });

      // Verify no project diff calls were made (only upstream-diff)
      const projectDiffCalls = mockApiRequest.mock.calls.filter(
        (call) =>
          String(call[0]).includes('/diff') &&
          !String(call[0]).includes('upstream-diff')
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
    it('renders in project mode with projectPath', async () => {
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

      // Both queries should fire: upstream-diff (github+tracking) and project diff
      await waitFor(() => {
        const upstreamCalls = mockApiRequest.mock.calls.filter((call) =>
          String(call[0]).includes('upstream-diff')
        );
        const projectCalls = mockApiRequest.mock.calls.filter(
          (call) =>
            String(call[0]).includes('/diff') &&
            !String(call[0]).includes('upstream-diff')
        );

        expect(upstreamCalls.length).toBeGreaterThan(0);
        expect(projectCalls.length).toBeGreaterThan(0);
      });
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
          (call) =>
            String(call[0]).includes('/diff') &&
            !String(call[0]).includes('upstream-diff')
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

      renderWithProviders(
        <SyncStatusTab
          entity={artifact}
          mode="project"
          onClose={onClose}
        />
      );

      // Discovered artifacts should show the import message
      await waitFor(() => {
        expect(
          screen.getByText(/not available for discovered artifacts/i)
        ).toBeInTheDocument();
      });

      // No API calls should have been made for discovered artifacts
      expect(mockApiRequest).not.toHaveBeenCalled();
    });
  });
});
