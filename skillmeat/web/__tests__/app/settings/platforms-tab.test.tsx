/**
 * @jest-environment jsdom
 *
 * Settings Page — Platforms Tab Tests (EPP-P4-04)
 *
 * Tests:
 * 1. Settings page renders with a Platforms tab trigger
 * 2. Clicking Platforms tab shows PlatformDefaultsSettings content
 * 3. "New Custom Profile" button is present in the Platforms tab
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SettingsPage from '@/app/settings/page';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    pathname: '/settings',
    query: {},
    asPath: '/settings',
  }),
  usePathname: () => '/settings',
  useSearchParams: () => new URLSearchParams(),
}));

// Platform defaults hooks
jest.mock('@/hooks', () => ({
  usePlatformDefaults: () => ({
    data: {
      defaults: {
        claude_code: {
          root_dir: '.claude',
          artifact_path_map: { skill: 'skills' },
          config_filenames: ['CLAUDE.md'],
          supported_artifact_types: ['skill'],
          context_prefixes: ['.claude/context/'],
        },
      },
    },
    isLoading: false,
  }),
  useUpdatePlatformDefault: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useResetPlatformDefault: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useCustomContextConfig: () => ({
    data: null,
    isLoading: false,
  }),
  useUpdateCustomContextConfig: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useCreateDeploymentProfile: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Stub out heavy settings components that are not under test here
jest.mock('@/components/settings/github-settings', () => ({
  GitHubSettings: () => <div data-testid="github-settings">GitHub Settings</div>,
}));

jest.mock('@/components/settings/custom-context-settings', () => ({
  CustomContextSettings: () => (
    <div data-testid="custom-context-settings">
      <h2>Custom Context Prefixes</h2>
    </div>
  ),
}));

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithProviders = (ui: React.ReactNode) => {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Settings Page — Platforms Tab', () => {
  describe('Tab navigation', () => {
    it('renders a "Platforms" tab trigger in the tablist', () => {
      renderWithProviders(<SettingsPage />);

      const platformsTab = screen.getByRole('tab', { name: /platforms/i });
      expect(platformsTab).toBeInTheDocument();
    });

    it('the Platforms tab is keyboard accessible (has role="tab")', () => {
      renderWithProviders(<SettingsPage />);

      const platformsTab = screen.getByRole('tab', { name: /platforms/i });
      expect(platformsTab).toHaveAttribute('role', 'tab');
    });

    it('clicking the Platforms tab makes it active', async () => {
      const user = userEvent.setup();
      renderWithProviders(<SettingsPage />);

      const platformsTab = screen.getByRole('tab', { name: /platforms/i });
      await user.click(platformsTab);

      expect(platformsTab).toHaveAttribute('data-state', 'active');
    });
  });

  describe('Platforms tab content', () => {
    it('renders PlatformDefaultsSettings content after clicking Platforms tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<SettingsPage />);

      const platformsTab = screen.getByRole('tab', { name: /platforms/i });
      await user.click(platformsTab);

      // PlatformDefaultsSettings renders a card with "Platform Defaults" heading
      await waitFor(() => {
        expect(screen.getByText('Platform Defaults')).toBeInTheDocument();
      });
    });

    it('shows accordion items for known platforms', async () => {
      const user = userEvent.setup();
      renderWithProviders(<SettingsPage />);

      const platformsTab = screen.getByRole('tab', { name: /platforms/i });
      await user.click(platformsTab);

      await waitFor(() => {
        expect(screen.getByText('Claude Code')).toBeInTheDocument();
      });
    });
  });

  describe('"New Custom Profile" button', () => {
    it('is present in the Platforms tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<SettingsPage />);

      const platformsTab = screen.getByRole('tab', { name: /platforms/i });
      await user.click(platformsTab);

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /new custom profile/i })
        ).toBeInTheDocument();
      });
    });

    it('opens a dialog when "New Custom Profile" is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<SettingsPage />);

      const platformsTab = screen.getByRole('tab', { name: /platforms/i });
      await user.click(platformsTab);

      const button = await screen.findByRole('button', { name: /new custom profile/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('dialog contains a "New Custom Profile" heading', async () => {
      const user = userEvent.setup();
      renderWithProviders(<SettingsPage />);

      const platformsTab = screen.getByRole('tab', { name: /platforms/i });
      await user.click(platformsTab);

      const button = await screen.findByRole('button', { name: /new custom profile/i });
      await user.click(button);

      await waitFor(() => {
        expect(
          screen.getByRole('heading', { name: /new custom profile/i })
        ).toBeInTheDocument();
      });
    });
  });

  describe('Other tabs unaffected', () => {
    it('PlatformDefaultsSettings is NOT present before clicking Platforms tab', () => {
      renderWithProviders(<SettingsPage />);

      // Default tab is "general" — Platform Defaults should not be visible
      expect(screen.queryByText('Platform Defaults')).not.toBeInTheDocument();
    });

    it('CustomContextSettings content is visible in the Context tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<SettingsPage />);

      const contextTab = screen.getByRole('tab', { name: /context/i });
      await user.click(contextTab);

      await waitFor(() => {
        expect(screen.getByText('Custom Context Prefixes')).toBeInTheDocument();
      });
    });

    it('CustomContextSettings is NOT visible in the Platforms tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<SettingsPage />);

      const platformsTab = screen.getByRole('tab', { name: /platforms/i });
      await user.click(platformsTab);

      await waitFor(() => {
        expect(screen.getByText('Platform Defaults')).toBeInTheDocument();
      });

      // Custom Context Prefixes should not be in the Platforms tab content
      expect(screen.queryByText('Custom Context Prefixes')).not.toBeInTheDocument();
    });
  });
});
