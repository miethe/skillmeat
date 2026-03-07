/**
 * Auth Flow E2E Tests
 *
 * Two suites:
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
 */

import { test, expect } from '@playwright/test';
import { navigateToPage, waitForElement } from './helpers/test-utils';

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
});
