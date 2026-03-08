/**
 * @jest-environment jsdom
 *
 * Auth component tests — covers:
 *   - UserProfile (local mode, unauthenticated, authenticated views)
 *   - WorkspaceSwitcher (hidden in zero-auth, personal/org switching)
 *   - AuthContextProvider + useAuth / useAuthUser hooks
 *   - useAuthFetch token injection
 *   - AuthWrapper noop path (zero-auth mode)
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { AuthContextProvider, useAuth, useAuthUser } from '@/lib/auth/auth-context';
import { noopAuthProvider, NoopAuthWrapper } from '@/lib/auth/noop-provider';
import { useAuthFetch } from '@/lib/auth/api-helpers';
import { UserProfile } from '@/components/auth/user-profile';
import { WorkspaceSwitcher } from '@/components/auth/workspace-switcher';

import type { AuthProvider, AuthUser } from '@/lib/auth/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Builds a minimal AuthUser. Accepts partial overrides. */
function makeUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'user_test',
    email: 'test@example.com',
    name: 'Test User',
    imageUrl: null,
    organizationId: null,
    organizations: [],
    ...overrides,
  };
}

/** Builds a mock AuthProvider. getUser/isAuthenticated/getToken default to a
 *  signed-in state unless overridden. */
function makeProvider(overrides: Partial<AuthProvider> = {}): AuthProvider {
  const defaultUser = makeUser();
  return {
    isEnabled: true,
    getUser: () => defaultUser,
    isAuthenticated: () => true,
    getToken: async () => 'test-bearer-token',
    signOut: jest.fn().mockResolvedValue(undefined),
    switchOrganization: jest.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

/** Wraps children in AuthContextProvider with the given provider. */
function AuthWrapper({
  provider,
  children,
}: {
  provider: AuthProvider;
  children: React.ReactNode;
}) {
  return <AuthContextProvider provider={provider}>{children}</AuthContextProvider>;
}

// ---------------------------------------------------------------------------
// AuthContextProvider + hooks
// ---------------------------------------------------------------------------

describe('AuthContextProvider / useAuth / useAuthUser', () => {
  it('provides auth context to children', () => {
    const provider = makeProvider();
    const Spy = () => {
      const auth = useAuth();
      return <div data-testid="enabled">{String(auth.isEnabled)}</div>;
    };

    render(
      <AuthWrapper provider={provider}>
        <Spy />
      </AuthWrapper>
    );

    expect(screen.getByTestId('enabled')).toHaveTextContent('true');
  });

  it('useAuthUser returns the current user', () => {
    const user = makeUser({ name: 'Alice' });
    const provider = makeProvider({ getUser: () => user });

    const Spy = () => {
      const u = useAuthUser();
      return <div data-testid="name">{u?.name ?? 'null'}</div>;
    };

    render(
      <AuthWrapper provider={provider}>
        <Spy />
      </AuthWrapper>
    );

    expect(screen.getByTestId('name')).toHaveTextContent('Alice');
  });

  it('useAuthUser returns null when provider returns null', () => {
    const provider = makeProvider({ getUser: () => null });

    const Spy = () => {
      const u = useAuthUser();
      return <div data-testid="name">{u?.name ?? 'null'}</div>;
    };

    render(
      <AuthWrapper provider={provider}>
        <Spy />
      </AuthWrapper>
    );

    expect(screen.getByTestId('name')).toHaveTextContent('null');
  });

  it('useAuth throws when called outside provider', () => {
    const Spy = () => {
      useAuth();
      return null;
    };

    // Silence the expected console error from React
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<Spy />)).toThrow(
      'useAuth must be used within an auth wrapper (AuthContextProvider)'
    );
    consoleSpy.mockRestore();
  });
});

// ---------------------------------------------------------------------------
// NoopAuthWrapper / noopAuthProvider
// ---------------------------------------------------------------------------

describe('noopAuthProvider (zero-auth mode)', () => {
  it('isEnabled is false', () => {
    expect(noopAuthProvider.isEnabled).toBe(false);
  });

  it('getUser returns a local_admin user', () => {
    const user = noopAuthProvider.getUser();
    expect(user).not.toBeNull();
    expect(user!.id).toBe('local_admin');
  });

  it('isAuthenticated returns true', () => {
    expect(noopAuthProvider.isAuthenticated()).toBe(true);
  });

  it('getToken resolves to null', async () => {
    await expect(noopAuthProvider.getToken()).resolves.toBeNull();
  });

  it('signOut is a no-op that resolves', async () => {
    await expect(noopAuthProvider.signOut()).resolves.toBeUndefined();
  });

  it('NoopAuthWrapper renders children', () => {
    render(
      <NoopAuthWrapper>
        <span data-testid="child">hello</span>
      </NoopAuthWrapper>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// useAuthFetch — Bearer token injection
// ---------------------------------------------------------------------------

/** Minimal fetch response stub — avoids relying on `Response` which is
 *  unavailable in the Jest/jsdom environment without a polyfill. */
function makeFetchResponse(status = 200) {
  return { status, ok: status >= 200 && status < 300, json: async () => ({}) } as unknown as Response;
}

describe('useAuthFetch', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue(makeFetchResponse(200));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('injects Bearer token when auth is enabled and token exists', async () => {
    const provider = makeProvider({ getToken: async () => 'my-secret-token' });

    let capturedHeaders: Headers | undefined;

    (global.fetch as jest.Mock).mockImplementation((_url: string, init?: RequestInit) => {
      capturedHeaders = new Headers(init?.headers);
      return Promise.resolve(makeFetchResponse(200));
    });

    const Spy = () => {
      const fetchWithAuth = useAuthFetch();
      React.useEffect(() => {
        fetchWithAuth('http://api.test/resource');
      }, [fetchWithAuth]);
      return null;
    };

    await act(async () => {
      render(
        <AuthWrapper provider={provider}>
          <Spy />
        </AuthWrapper>
      );
    });

    await waitFor(() => {
      expect(capturedHeaders?.get('Authorization')).toBe('Bearer my-secret-token');
    });
  });

  it('omits Authorization header when token is null (local/noop mode)', async () => {
    const provider = makeProvider({
      isEnabled: false,
      getToken: async () => null,
    });

    let capturedHeaders: Headers | undefined;

    (global.fetch as jest.Mock).mockImplementation((_url: string, init?: RequestInit) => {
      capturedHeaders = new Headers(init?.headers);
      return Promise.resolve(makeFetchResponse(200));
    });

    const Spy = () => {
      const fetchWithAuth = useAuthFetch();
      React.useEffect(() => {
        fetchWithAuth('http://api.test/resource');
      }, [fetchWithAuth]);
      return null;
    };

    await act(async () => {
      render(
        <AuthWrapper provider={provider}>
          <Spy />
        </AuthWrapper>
      );
    });

    await waitFor(() => {
      expect(capturedHeaders?.get('Authorization')).toBeNull();
    });
  });

  it('passes through custom options to fetch', async () => {
    const provider = makeProvider({ getToken: async () => null });
    let capturedInit: RequestInit | undefined;

    (global.fetch as jest.Mock).mockImplementation((_url: string, init?: RequestInit) => {
      capturedInit = init;
      return Promise.resolve(makeFetchResponse(200));
    });

    const Spy = () => {
      const fetchWithAuth = useAuthFetch();
      React.useEffect(() => {
        fetchWithAuth('http://api.test/resource', {
          method: 'POST',
          body: JSON.stringify({ key: 'value' }),
        });
      }, [fetchWithAuth]);
      return null;
    };

    await act(async () => {
      render(
        <AuthWrapper provider={provider}>
          <Spy />
        </AuthWrapper>
      );
    });

    await waitFor(() => {
      expect(capturedInit?.method).toBe('POST');
      expect(capturedInit?.body).toBe(JSON.stringify({ key: 'value' }));
    });
  });

  it('returns the fetch Response', async () => {
    const provider = makeProvider({ getToken: async () => 'token' });
    let result: Response | undefined;

    (global.fetch as jest.Mock).mockResolvedValue(makeFetchResponse(201));

    const Spy = () => {
      const fetchWithAuth = useAuthFetch();
      React.useEffect(() => {
        fetchWithAuth('http://api.test/resource').then((r) => {
          result = r;
        });
      }, [fetchWithAuth]);
      return null;
    };

    await act(async () => {
      render(
        <AuthWrapper provider={provider}>
          <Spy />
        </AuthWrapper>
      );
    });

    await waitFor(() => {
      expect(result?.status).toBe(201);
    });
  });
});

// ---------------------------------------------------------------------------
// UserProfile component
// ---------------------------------------------------------------------------

describe('UserProfile', () => {
  describe('zero-auth / local mode', () => {
    it('renders Local Mode indicator when auth is disabled', () => {
      const provider = makeProvider({ isEnabled: false, getUser: () => null });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByText('Local Mode')).toBeInTheDocument();
    });

    it('does not render sign-out button in local mode', () => {
      const provider = makeProvider({ isEnabled: false, getUser: () => null });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.queryByRole('button', { name: /sign out/i })).not.toBeInTheDocument();
    });

    it('shows authentication-disabled description', () => {
      const provider = makeProvider({ isEnabled: false, getUser: () => null });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByText(/single-user local mode/i)).toBeInTheDocument();
    });
  });

  describe('unauthenticated (auth enabled but no user)', () => {
    it('renders "Not signed in" when user is null', () => {
      const provider = makeProvider({ isEnabled: true, getUser: () => null });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByText('Not signed in.')).toBeInTheDocument();
    });
  });

  describe('authenticated view', () => {
    it('displays user name in identity section', () => {
      const user = makeUser({ name: 'Jane Doe', email: 'jane@example.com' });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      // Name appears in the identity section heading (title attribute) as well as
      // the personal-workspace row. Use getAllByText and assert at least one exists.
      const matches = screen.getAllByText('Jane Doe');
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });

    it('displays user email', () => {
      const user = makeUser({ name: 'Jane Doe', email: 'jane@example.com' });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByText('jane@example.com')).toBeInTheDocument();
    });

    it('shows "Authenticated" status', () => {
      const user = makeUser();
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByText('Authenticated')).toBeInTheDocument();
    });

    it('renders sign-out button', () => {
      const user = makeUser();
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();
    });

    it('shows personal workspace when no active org', () => {
      const user = makeUser({ organizationId: null });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByText('Personal workspace')).toBeInTheDocument();
    });

    it('shows team workspace when active org is set', () => {
      const user = makeUser({
        organizationId: 'org-1',
        organizations: [{ id: 'org-1', name: 'Acme Corp', role: 'admin' }],
      });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByText('Team workspace')).toBeInTheDocument();
      // "Acme Corp" appears both in the active-workspace row and the org list;
      // assert it appears at least once.
      expect(screen.getAllByText('Acme Corp').length).toBeGreaterThanOrEqual(1);
    });

    it('lists organizations', () => {
      const user = makeUser({
        organizations: [
          { id: 'org-1', name: 'Alpha Inc', role: 'admin' },
          { id: 'org-2', name: 'Beta Ltd', role: 'member' },
        ],
      });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByRole('list')).toBeInTheDocument();
      expect(screen.getByText('Alpha Inc')).toBeInTheDocument();
      expect(screen.getByText('Beta Ltd')).toBeInTheDocument();
    });

    it('shows org count in section heading', () => {
      const user = makeUser({
        organizations: [
          { id: 'org-1', name: 'Alpha Inc', role: 'member' },
          { id: 'org-2', name: 'Beta Ltd', role: 'member' },
        ],
      });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByText('(2)')).toBeInTheDocument();
    });

    it('marks active org with Active badge', () => {
      const user = makeUser({
        organizationId: 'org-1',
        organizations: [{ id: 'org-1', name: 'Alpha Inc', role: 'member' }],
      });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByText('Active')).toBeInTheDocument();
    });
  });

  describe('sign-out interaction', () => {
    it('calls auth.signOut when sign-out button is clicked', async () => {
      const signOut = jest.fn().mockResolvedValue(undefined);
      const user = makeUser();
      const provider = makeProvider({ getUser: () => user, signOut });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      await userEvent.click(screen.getByRole('button', { name: /sign out/i }));

      await waitFor(() => {
        expect(signOut).toHaveBeenCalledTimes(1);
      });
    });

    it('shows "Signing out…" while sign-out is in progress', async () => {
      let resolveSignOut!: () => void;
      const signOut = jest.fn(
        () => new Promise<void>((resolve) => { resolveSignOut = resolve; })
      );
      const user = makeUser();
      const provider = makeProvider({ getUser: () => user, signOut });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      fireEvent.click(screen.getByRole('button', { name: /sign out/i }));

      expect(await screen.findByText('Signing out…')).toBeInTheDocument();

      // Clean up: resolve the sign-out promise
      await act(async () => { resolveSignOut(); });
    });

    it('disables sign-out button while signing out', async () => {
      let resolveSignOut!: () => void;
      const signOut = jest.fn(
        () => new Promise<void>((resolve) => { resolveSignOut = resolve; })
      );
      const user = makeUser();
      const provider = makeProvider({ getUser: () => user, signOut });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      const btn = screen.getByRole('button', { name: /sign out/i });
      fireEvent.click(btn);

      await waitFor(() => {
        expect(btn).toBeDisabled();
      });

      await act(async () => { resolveSignOut(); });
    });
  });

  describe('accessibility', () => {
    it('user identity section has aria-label', () => {
      const user = makeUser();
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByRole('region', { name: /user identity/i })).toBeInTheDocument();
    });

    it('sign-out button has descriptive aria-label', () => {
      const user = makeUser();
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(
        screen.getByRole('button', { name: 'Sign out of SkillMeat' })
      ).toBeInTheDocument();
    });

    it('org list uses role="list" for semantics', () => {
      const user = makeUser({
        organizations: [{ id: 'org-1', name: 'Alpha Inc', role: 'member' }],
      });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <UserProfile />
        </AuthWrapper>
      );

      expect(screen.getByRole('list')).toBeInTheDocument();
      expect(screen.getAllByRole('listitem').length).toBeGreaterThanOrEqual(1);
    });
  });
});

// ---------------------------------------------------------------------------
// WorkspaceSwitcher component
// ---------------------------------------------------------------------------

describe('WorkspaceSwitcher', () => {
  describe('zero-auth mode', () => {
    it('renders nothing when auth is disabled', () => {
      const provider = makeProvider({ isEnabled: false, getUser: () => null });

      const { container } = render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      expect(container).toBeEmptyDOMElement();
    });

    it('renders nothing when user is null even with auth enabled', () => {
      const provider = makeProvider({ isEnabled: true, getUser: () => null });

      const { container } = render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      expect(container).toBeEmptyDOMElement();
    });
  });

  describe('personal workspace', () => {
    it('renders trigger button with user name', () => {
      const user = makeUser({ name: 'Jane Doe', organizationId: null });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      expect(
        screen.getByRole('button', { name: /current workspace: jane doe/i })
      ).toBeInTheDocument();
    });

    it('shows "Personal" when user has no name', () => {
      const user = makeUser({ name: null, organizationId: null });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      // The button aria-label uses the derived workspace name
      const btn = screen.getByRole('button', { name: /current workspace: personal/i });
      expect(btn).toBeInTheDocument();
    });
  });

  describe('team workspace', () => {
    it('shows org name in trigger button when org is active', () => {
      const user = makeUser({
        name: 'Jane',
        organizationId: 'org-1',
        organizations: [{ id: 'org-1', name: 'Acme Corp', role: 'admin' }],
      });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      expect(
        screen.getByRole('button', { name: /current workspace: acme corp/i })
      ).toBeInTheDocument();
    });
  });

  describe('org selection', () => {
    it('calls switchOrganization with null when personal workspace selected', async () => {
      const switchOrganization = jest.fn().mockResolvedValue(undefined);
      const user = makeUser({
        name: 'Jane',
        organizationId: 'org-1',
        organizations: [{ id: 'org-1', name: 'Acme Corp', role: 'admin' }],
      });
      const provider = makeProvider({ getUser: () => user, switchOrganization });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      // Open the dropdown
      await userEvent.click(
        screen.getByRole('button', { name: /current workspace/i })
      );

      // Click the personal workspace item (displays user name "Jane")
      const personalItem = await screen.findByRole('menuitem', { name: /jane/i });
      await userEvent.click(personalItem);

      await waitFor(() => {
        expect(switchOrganization).toHaveBeenCalledWith('');
      });
    });

    it('calls switchOrganization with org id when org selected', async () => {
      const switchOrganization = jest.fn().mockResolvedValue(undefined);
      const user = makeUser({
        name: 'Jane',
        organizationId: null,
        organizations: [{ id: 'org-99', name: 'Globex', role: 'member' }],
      });
      const provider = makeProvider({ getUser: () => user, switchOrganization });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /current workspace/i })
      );

      const globexItem = await screen.findByRole('menuitem', { name: /globex/i });
      await userEvent.click(globexItem);

      await waitFor(() => {
        expect(switchOrganization).toHaveBeenCalledWith('org-99');
      });
    });

    it('does not call switchOrganization when already on selected workspace', async () => {
      const switchOrganization = jest.fn().mockResolvedValue(undefined);
      const user = makeUser({
        name: 'Jane',
        organizationId: null,
        organizations: [],
      });
      const provider = makeProvider({ getUser: () => user, switchOrganization });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /current workspace/i })
      );

      // Click the already-active personal workspace
      const personalItem = await screen.findByRole('menuitem', { name: /jane/i });
      await userEvent.click(personalItem);

      // switchOrganization should NOT have been called (same workspace)
      expect(switchOrganization).not.toHaveBeenCalled();
    });

    it('disables trigger button while switch is in progress', async () => {
      let resolveSwitchOrg!: () => void;
      const switchOrganization = jest.fn(
        () => new Promise<void>((resolve) => { resolveSwitchOrg = resolve; })
      );
      const user = makeUser({
        name: 'Jane',
        organizationId: null,
        organizations: [{ id: 'org-1', name: 'Acme', role: 'member' }],
      });
      const provider = makeProvider({ getUser: () => user, switchOrganization });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      const triggerBtn = screen.getByRole('button', { name: /current workspace/i });
      await userEvent.click(triggerBtn);

      const acmeItem = await screen.findByRole('menuitem', { name: /acme/i });
      fireEvent.click(acmeItem);

      await waitFor(() => {
        expect(triggerBtn).toBeDisabled();
      });

      await act(async () => { resolveSwitchOrg(); });
    });
  });

  describe('dropdown content', () => {
    it('lists all organizations in dropdown', async () => {
      const user = makeUser({
        name: 'Jane',
        organizationId: null,
        organizations: [
          { id: 'org-1', name: 'Alpha', role: 'admin' },
          { id: 'org-2', name: 'Beta', role: 'member' },
        ],
      });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      await userEvent.click(screen.getByRole('button', { name: /current workspace/i }));

      expect(await screen.findByRole('menuitem', { name: /alpha/i })).toBeInTheDocument();
      expect(screen.getByRole('menuitem', { name: /beta/i })).toBeInTheDocument();
    });

    it('shows "Workspaces" menu label', async () => {
      const user = makeUser();
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      await userEvent.click(screen.getByRole('button', { name: /current workspace/i }));

      expect(await screen.findByText('Workspaces')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('trigger button has descriptive aria-label', () => {
      const user = makeUser({ name: 'Jane Doe', organizationId: null });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      const btn = screen.getByRole('button', { name: /current workspace: jane doe/i });
      expect(btn).toHaveAttribute(
        'aria-label',
        'Current workspace: Jane Doe. Click to switch workspace.'
      );
    });

    it('marks the currently active workspace with aria-current', async () => {
      const user = makeUser({
        name: 'Jane',
        organizationId: 'org-1',
        organizations: [{ id: 'org-1', name: 'Acme Corp', role: 'admin' }],
      });
      const provider = makeProvider({ getUser: () => user });

      render(
        <AuthWrapper provider={provider}>
          <WorkspaceSwitcher />
        </AuthWrapper>
      );

      await userEvent.click(screen.getByRole('button', { name: /current workspace/i }));

      const acmeItem = await screen.findByRole('menuitem', { name: /acme corp/i });
      expect(acmeItem).toHaveAttribute('aria-current', 'true');
    });
  });
});
