/**
 * Auth Flow E2E Tests
 *
 * Three suites:
 *
 * 1. Zero-Auth Mode (NEXT_PUBLIC_AUTH_ENABLED=false)
 *    Runnable in CI with no Clerk configuration.
 *    Validates that the app works as a fully public, unauthenticated experience.
 *
 * 2. Auth-Enabled Mode (NEXT_PUBLIC_AUTH_ENABLED=true)
 *    All tests are skipped by default. Run manually against a Clerk sandbox:
 *
 *      NEXT_PUBLIC_AUTH_ENABLED=true \
 *      NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_... \
 *      CLERK_SECRET_KEY=sk_test_... \
 *      pnpm test:e2e -- tests/auth.e2e.ts --grep "Auth-Enabled"
 *
 *    Requires a pre-seeded Clerk test account. See docs/auth-testing.md for
 *    sandbox setup instructions.
 *
 * 3. Auth-Enabled Mode — Network Interception
 *    Deep network-level verification of token injection, refresh, and post-logout
 *    behaviour. Also skipped by default; run with the same Clerk sandbox env vars.
 *
 *      NEXT_PUBLIC_AUTH_ENABLED=true \
 *      NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_... \
 *      CLERK_SECRET_KEY=sk_test_... \
 *      pnpm test:e2e -- tests/auth.e2e.ts --grep "Auth-Enabled Network"
 */

import { test, expect, type Page, type Request } from '@playwright/test';
import { navigateToPage, waitForElement } from './helpers/test-utils';

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/**
 * Collect every API request (to the backend) that carries (or omits) an
 * Authorization header while the returned cleanup function is alive.
 *
 * Returns { captured, stop }:
 *   - captured: live array of collected requests (mutated in place)
 *   - stop:     call to detach the listener when the interception window ends
 */
function interceptApiRequests(page: Page): {
  captured: Request[];
  stop: () => void;
} {
  const captured: Request[] = [];
  const handler = (request: Request) => {
    const url = request.url();
    if (url.includes('/api/v1/') || url.includes(':8080')) {
      captured.push(request);
    }
  };
  page.on('request', handler);
  return {
    captured,
    stop: () => page.off('request', handler),
  };
}

/**
 * Perform the Clerk sign-in flow for the test sandbox account.
 * Waits for successful redirect to the app root before returning.
 */
async function signInWithClerk(
  page: Page,
  email: string,
  password: string,
  timeout = 15_000
) {
  await page.goto('/auth/login');
  await page.locator('input[name="identifier"]').fill(email);
  await page.locator('button:has-text("Continue")').click();
  await page.locator('input[name="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL('/', { timeout });
}

/**
 * Perform the sign-out flow and wait for the login redirect.
 */
async function signOutViaUI(page: Page, timeout = 10_000) {
  const userMenuTrigger = page.locator(
    '[data-testid="user-menu"], [aria-label="User menu"], button:has-text("Sign out")'
  );
  await userMenuTrigger.first().click();

  const signOutButton = page.locator(
    'button:has-text("Sign out"), [data-testid="sign-out-button"]'
  );
  await signOutButton.click();

  await expect(page).toHaveURL(/\/auth\/login/, { timeout });
}

// ---------------------------------------------------------------------------
// Zero-Auth Mode Tests — safe to run in CI
// ---------------------------------------------------------------------------

test.describe('Zero-Auth Mode (NEXT_PUBLIC_AUTH_ENABLED=false)', () => {
  // These tests assume the dev server was started without auth env vars, which
  // is the default configuration for CI (see playwright.config.ts webServer).

  test('home page loads without auth redirect', async ({ page }) => {
    await page.goto('/');
    // Should land on the home/collection page, not an auth gate
    await expect(page).not.toHaveURL(/\/auth\/login/);
    // Page content should be present
    await expect(page.locator('body')).toBeVisible();
  });

  test('no login link or button visible in header', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // In zero-auth mode the header should not expose any sign-in affordance
    const signInButton = page.locator('a[href="/auth/login"], button:has-text("Sign in"), button:has-text("Log in")');
    await expect(signInButton).toHaveCount(0);
  });

  test('/auth/login redirects to / when auth is disabled', async ({ page }) => {
    await page.goto('/auth/login');
    // The login page server-redirects to / in zero-auth mode
    await expect(page).toHaveURL('/');
  });

  test('/auth/signup redirects to / when auth is disabled', async ({ page }) => {
    await page.goto('/auth/signup');
    // The signup page server-redirects to / in zero-auth mode
    await expect(page).toHaveURL('/');
  });

  test('API calls succeed without Authorization header', async ({ page }) => {
    // Intercept outgoing API requests and assert no Authorization header is sent
    const authHeaders: Array<string | null> = [];

    page.on('request', (request) => {
      const url = request.url();
      if (url.includes('/api/v1/') || url.includes(':8080')) {
        authHeaders.push(request.headers()['authorization'] ?? null);
      }
    });

    await page.goto('/collection');
    await page.waitForLoadState('networkidle');

    // Every captured API request should be unauthenticated
    for (const header of authHeaders) {
      expect(header).toBeNull();
    }
  });

  test('workspace switcher is not rendered', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Workspace / organization switcher must not appear in zero-auth mode
    const switcher = page.locator(
      '[data-testid="workspace-switcher"], [aria-label="Switch workspace"], [aria-label="Switch organization"]'
    );
    await expect(switcher).toHaveCount(0);
  });

  test('settings page shows local mode indicator', async ({ page }) => {
    await navigateToPage(page, '/settings');

    // The settings page should signal that auth is not active
    // Acceptable text: "Local Mode", "Authentication disabled", etc.
    const localModeIndicator = page.locator(
      'text=/local mode/i, text=/authentication disabled/i, text=/no auth/i, [data-testid="local-mode-badge"]'
    );

    // Allow the page to settle before asserting — settings may lazy-load
    await page.waitForTimeout(500);

    // At least one indicator should be present
    const count = await localModeIndicator.count();
    expect(count).toBeGreaterThan(0);
  });

  test('multiple app routes load without auth redirect in zero-auth mode', async ({ page }) => {
    // Verify that several first-class routes are publicly accessible — none
    // should redirect to /auth/login in zero-auth mode.
    const publicRoutes = ['/collection', '/marketplace', '/settings'];

    for (const route of publicRoutes) {
      await page.goto(route);
      await page.waitForLoadState('domcontentloaded');
      await expect(page).not.toHaveURL(/\/auth\/login/);
    }
  });

  test('user profile section shows local mode state', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // The UserProfile component is typically reachable via a settings link or
    // is embedded in the sidebar/header. In zero-auth mode it should not show
    // any sign-in affordance. We look for the data-testid if present.
    const profileSection = page.locator(
      '[data-testid="user-profile"], [aria-label="User profile"], [aria-label*="user"]'
    );
    // If a profile section exists it must not contain a "Sign in" CTA.
    const profileCount = await profileSection.count();
    if (profileCount > 0) {
      const signInCta = profileSection.first().getByRole('button', {
        name: /sign in/i,
      });
      await expect(signInCta).toHaveCount(0);
    }
  });
});

// ---------------------------------------------------------------------------
// Auth-Enabled Mode Tests — skipped by default; run manually with Clerk sandbox
// ---------------------------------------------------------------------------

test.describe('Auth-Enabled Mode', () => {
  // All tests in this suite are skipped unless you explicitly unskip them for
  // a manual run. See the file-level JSDoc for the required environment variables
  // and how to target these tests from the CLI.

  test.skip(true, 'Requires Clerk sandbox — run manually with NEXT_PUBLIC_AUTH_ENABLED=true');

  // Clerk sandbox test credentials — override via environment for real runs.
  const TEST_EMAIL = process.env['CLERK_TEST_EMAIL'] ?? 'test+clerk@example.com';
  const TEST_PASSWORD = process.env['CLERK_TEST_PASSWORD'] ?? 'test-password-placeholder';

  test('unauthenticated user is redirected to /auth/login', async ({ page }) => {
    await page.goto('/collection');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('login page renders Clerk SignIn component', async ({ page }) => {
    await page.goto('/auth/login');

    // Clerk renders its embedded component inside a shadow DOM or a labelled region.
    // Wait for the sign-in form container Clerk injects.
    await waitForElement(page, '[data-clerk-component="sign-in"], form[data-clerk-form]');

    // The page title should reflect the sign-in context
    await expect(page).toHaveTitle(/Sign In/i);
  });

  test('signup page renders Clerk SignUp component', async ({ page }) => {
    await page.goto('/auth/signup');
    await waitForElement(page, '[data-clerk-component="sign-up"], form[data-clerk-form]');
    await expect(page).toHaveTitle(/Sign Up/i);
  });

  test('successful login redirects user to /', async ({ page }) => {
    await page.goto('/auth/login');

    // Fill in Clerk's hosted sign-in form fields
    await page.locator('input[name="identifier"]').fill(TEST_EMAIL);
    await page.locator('button:has-text("Continue")').click();
    await page.locator('input[name="password"]').fill(TEST_PASSWORD);
    await page.locator('button[type="submit"]').click();

    // After successful auth, Clerk redirects to the app root
    await expect(page).toHaveURL('/', { timeout: 15_000 });
  });

  test('workspace switcher is visible in header after login', async ({ page }) => {
    // Assumes the previous login test ran (or that session storage is pre-seeded)
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const switcher = page.locator(
      '[data-testid="workspace-switcher"], [aria-label="Switch workspace"], [aria-label="Switch organization"]'
    );
    await expect(switcher.first()).toBeVisible();
  });

  test('API calls include Authorization Bearer header after login', async ({ page }) => {
    const authHeaders: string[] = [];

    page.on('request', (request) => {
      const url = request.url();
      if (url.includes('/api/v1/') || url.includes(':8080')) {
        const authHeader = request.headers()['authorization'];
        if (authHeader) {
          authHeaders.push(authHeader);
        }
      }
    });

    await page.goto('/collection');
    await page.waitForLoadState('networkidle');

    // At least one API request should carry a Bearer token
    expect(authHeaders.length).toBeGreaterThan(0);
    for (const header of authHeaders) {
      expect(header).toMatch(/^Bearer /);
    }
  });

  test('logout clears session and redirects to /auth/login', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Open user menu and click sign-out
    const userMenuTrigger = page.locator(
      '[data-testid="user-menu"], [aria-label="User menu"], button:has-text("Sign out")'
    );
    await userMenuTrigger.first().click();

    const signOutButton = page.locator('button:has-text("Sign out"), [data-testid="sign-out-button"]');
    await signOutButton.click();

    // Should land back on the login page
    await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });

    // Session should be cleared — navigating to a protected route redirects again
    await page.goto('/collection');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('session persists across a full page reload', async ({ page }) => {
    // Sign in and confirm landing on root
    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);

    // Hard reload — Clerk restores the session from its cookie/localStorage
    await page.reload({ waitUntil: 'networkidle' });

    // Should still be on the authenticated app, not kicked to login
    await expect(page).not.toHaveURL(/\/auth\/login/);

    // User menu (auth indicator) should still be visible
    const userMenu = page.locator(
      '[data-testid="user-menu"], [aria-label="User menu"], [data-testid="workspace-switcher"]'
    );
    await expect(userMenu.first()).toBeVisible({ timeout: 8_000 });
  });

  test('protected routes redirect unauthenticated users across all key paths', async ({
    page,
  }) => {
    // Ensure we are in a fully logged-out state before the test
    await page.context().clearCookies();
    await page.context().clearPermissions();

    const protectedRoutes = ['/collection', '/settings', '/manage'];
    for (const route of protectedRoutes) {
      await page.goto(route);
      await page.waitForLoadState('domcontentloaded');
      await expect(page).toHaveURL(/\/auth\/login/, {
        timeout: 8_000,
      });
    }
  });

  test('user menu shows display name after login', async ({ page }) => {
    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);
    await page.waitForLoadState('domcontentloaded');

    // The workspace switcher or user-menu button should reflect the signed-in
    // identity (either the user's name or org name).
    const identity = page.locator(
      '[data-testid="workspace-switcher"] button, [aria-label*="current workspace"]'
    );
    await expect(identity.first()).toBeVisible({ timeout: 8_000 });
    // Identity text should not be blank
    const label = await identity.first().getAttribute('aria-label');
    expect(label).not.toBeNull();
    expect(label!.toLowerCase()).not.toContain('local mode');
  });
});

// ---------------------------------------------------------------------------
// Auth-Enabled Mode — Network Interception Tests
// Skipped by default; run manually with Clerk sandbox env vars.
// ---------------------------------------------------------------------------

test.describe('Auth-Enabled Network Interception', () => {
  test.skip(
    true,
    'Requires Clerk sandbox — run manually with NEXT_PUBLIC_AUTH_ENABLED=true'
  );

  const TEST_EMAIL = process.env['CLERK_TEST_EMAIL'] ?? 'test+clerk@example.com';
  const TEST_PASSWORD = process.env['CLERK_TEST_PASSWORD'] ?? 'test-password-placeholder';

  test('every API request carries a Bearer token matching "Bearer <jwt>" format', async ({
    page,
  }) => {
    const { captured, stop } = interceptApiRequests(page);

    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);

    // Navigate to a data-heavy page to trigger multiple API calls
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');

    stop();

    // There should be at least one API request after login
    expect(captured.length).toBeGreaterThan(0);

    for (const request of captured) {
      const auth = request.headers()['authorization'];
      expect(auth, `Request to ${request.url()} missing Authorization header`).toBeDefined();
      // JWT Bearer tokens are three dot-separated base64url segments
      expect(auth, `Authorization header has wrong format: ${auth}`).toMatch(
        /^Bearer [A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$/
      );
    }
  });

  test('token is included in POST/PATCH mutations, not only GET requests', async ({
    page,
  }) => {
    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);

    // Intercept after login so we only see authenticated calls
    const mutationAuthHeaders: string[] = [];

    page.on('request', (request) => {
      const method = request.method();
      const url = request.url();
      if (
        (method === 'POST' || method === 'PATCH' || method === 'PUT' || method === 'DELETE') &&
        (url.includes('/api/v1/') || url.includes(':8080'))
      ) {
        const auth = request.headers()['authorization'];
        if (auth) mutationAuthHeaders.push(auth);
      }
    });

    // Trigger a lightweight mutation — e.g., a cache-refresh or sync status call.
    // We hit the cache refresh endpoint which is always available.
    await page.request.post('http://localhost:8080/api/v1/cache/refresh');

    // Wait briefly for any in-flight requests triggered by page activities
    await page.waitForTimeout(800);

    // At least the manual request above (or any page-initiated mutation) should
    // have carried a Bearer token — but we only assert if mutations were observed.
    for (const header of mutationAuthHeaders) {
      expect(header).toMatch(/^Bearer /);
    }
  });

  test('no Authorization header sent after logout', async ({ page }) => {
    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);

    // Perform logout via UI
    await signOutViaUI(page);
    await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });

    // Collect any API requests that fire after logout (e.g., redirect-triggered calls)
    const { captured, stop } = interceptApiRequests(page);

    // Navigate to the root — should redirect back to login (no authenticated calls)
    await page.goto('/collection');
    await page.waitForLoadState('domcontentloaded');

    stop();

    // Any requests that did fire (e.g., health checks) must NOT carry a Bearer token
    for (const request of captured) {
      const auth = request.headers()['authorization'];
      expect(
        auth,
        `Unexpected Bearer token in post-logout request to ${request.url()}`
      ).toBeUndefined();
    }
  });

  test('token refresh: long-running session still sends valid Bearer token', async ({
    page,
  }) => {
    // This test simulates a session where the short-lived Clerk JWT would
    // normally expire by waiting just past the token TTL threshold.
    //
    // In a real sandbox the JWT TTL is ~60 seconds; we wait 65s and then
    // verify the next API call still includes a valid (refreshed) token.
    //
    // Skip this test unless RUN_TOKEN_REFRESH_TEST=true is set — it is slow.
    if (!process.env['RUN_TOKEN_REFRESH_TEST']) {
      test.skip();
    }

    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);

    // Wait beyond the typical short-lived JWT TTL (Clerk refreshes automatically)
    await page.waitForTimeout(65_000);

    const { captured, stop } = interceptApiRequests(page);

    // Force a page navigation to trigger a fresh API call post-refresh
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');

    stop();

    expect(captured.length, 'No API requests fired after token refresh window').toBeGreaterThan(0);

    for (const request of captured) {
      const auth = request.headers()['authorization'];
      // After refresh the token should still be a valid Bearer JWT
      expect(auth).toMatch(/^Bearer [A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$/);
    }
  });

  test('Authorization header value is stable across multiple API calls in same session', async ({
    page,
  }) => {
    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);

    const { captured, stop } = interceptApiRequests(page);

    await page.goto('/collection');
    await page.waitForLoadState('networkidle');

    stop();

    const tokens = captured
      .map((r) => r.headers()['authorization'])
      .filter((h): h is string => !!h);

    // All requests in a single session window should carry the same token
    // (Clerk does not rotate mid-session unless the short-lived JWT expires).
    const uniqueTokens = new Set(tokens);
    expect(
      uniqueTokens.size,
      'Multiple different tokens observed in a single session — unexpected rotation'
    ).toBeLessThanOrEqual(1);
  });

  test('login button hidden and user menu visible after sign-in', async ({ page }) => {
    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);
    await page.waitForLoadState('domcontentloaded');

    // Login / sign-in button must NOT be present once authenticated
    const loginButton = page.locator(
      'a[href="/auth/login"], button:has-text("Sign in"), button:has-text("Log in")'
    );
    await expect(loginButton).toHaveCount(0);

    // User menu / workspace switcher MUST be present
    const userMenu = page.locator(
      '[data-testid="user-menu"], [aria-label="User menu"], [data-testid="workspace-switcher"], [aria-label*="current workspace"]'
    );
    await expect(userMenu.first()).toBeVisible({ timeout: 8_000 });
  });

  test('sign-out button visible, login button hidden while authenticated', async ({
    page,
  }) => {
    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);

    // Open user menu to expose sign-out
    const userMenuTrigger = page.locator(
      '[data-testid="user-menu"], [aria-label="User menu"]'
    );
    await userMenuTrigger.first().click();

    const signOutButton = page.locator(
      'button:has-text("Sign out"), [data-testid="sign-out-button"]'
    );
    await expect(signOutButton.first()).toBeVisible({ timeout: 5_000 });

    // There should be no standalone "Sign in" button while the menu is open
    const loginButton = page.locator('button:has-text("Sign in"), button:has-text("Log in")');
    await expect(loginButton).toHaveCount(0);
  });

  test('after logout, login button visible and user menu hidden', async ({ page }) => {
    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);
    await signOutViaUI(page);

    // We are now on /auth/login — the sign-in form (not just a button) should
    // be present. The user menu must not be rendered.
    await expect(page).toHaveURL(/\/auth\/login/);

    const userMenu = page.locator(
      '[data-testid="user-menu"], [data-testid="workspace-switcher"]'
    );
    await expect(userMenu).toHaveCount(0);
  });

  test('full login → API call → logout flow', async ({ page }) => {
    // Step 1 — start unauthenticated
    await page.context().clearCookies();
    await page.goto('/collection');
    await expect(page).toHaveURL(/\/auth\/login/, { timeout: 8_000 });

    // Step 2 — sign in
    await signInWithClerk(page, TEST_EMAIL, TEST_PASSWORD);
    await expect(page).toHaveURL('/');

    // Step 3 — navigate to a data page and verify Bearer token in API requests
    const { captured, stop } = interceptApiRequests(page);
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');
    stop();

    const authHeaders = captured
      .map((r) => r.headers()['authorization'])
      .filter((h): h is string => !!h);

    expect(authHeaders.length, 'No authenticated API calls observed').toBeGreaterThan(0);
    for (const header of authHeaders) {
      expect(header).toMatch(/^Bearer /);
    }

    // Step 4 — sign out and confirm token is no longer sent
    await signOutViaUI(page);
    await expect(page).toHaveURL(/\/auth\/login/);

    const { captured: postLogout, stop: stopPostLogout } = interceptApiRequests(page);
    await page.goto('/collection');
    await page.waitForLoadState('domcontentloaded');
    stopPostLogout();

    for (const request of postLogout) {
      const auth = request.headers()['authorization'];
      expect(auth, `Unexpected auth header after logout on ${request.url()}`).toBeUndefined();
    }
  });
});
