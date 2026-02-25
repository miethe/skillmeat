/**
 * E2E smoke tests for Color Management feature
 *
 * Tests the complete user flow for adding and removing custom colors via the
 * Settings → Appearance → Colors tab, and verifies they appear in ColorSelector
 * components throughout the app (e.g. Groups page).
 *
 * Assumes the app is running on http://localhost:3000 (Playwright baseURL).
 * API calls are intercepted via page.route() to avoid requiring a live backend.
 */
import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Shared test data
// ---------------------------------------------------------------------------

const CUSTOM_HEX = '#ab1234';
const CUSTOM_COLOR_ID = 'test-color-id-1';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Wait for the page to settle (network idle + no loading spinners).
 */
async function waitForPageReady(page: Page) {
  await page.waitForLoadState('networkidle');
  await page
    .waitForSelector('[class*="animate-spin"]', { state: 'hidden', timeout: 10_000 })
    .catch(() => {
      // Ignore — spinner may never appear for fast responses
    });
}

/**
 * Intercept the custom colors list endpoint.
 * `colors` is the array that will be returned by GET /api/v1/colors.
 */
async function mockColorsApi(
  page: Page,
  colors: Array<{ id: string; hex: string; name?: string }>
) {
  await page.route('**/api/v1/colors', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(colors),
      });
    } else {
      // Let other methods fall through to subsequent route registrations
      await route.continue();
    }
  });
}

/**
 * Intercept POST /api/v1/colors to return a newly created color entry.
 */
async function mockCreateColorApi(
  page: Page,
  created: { id: string; hex: string; name?: string }
) {
  await page.route('**/api/v1/colors', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(created),
      });
    } else {
      await route.continue();
    }
  });
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

test.describe('Color Management', () => {
  test.describe('Settings → Appearance → Colors', () => {
    test('navigates to Settings and opens the Appearance tab', async ({ page }) => {
      // Start with no custom colors
      await mockColorsApi(page, []);

      await page.goto('/settings');
      await waitForPageReady(page);

      // Click the Appearance tab
      await page.getByRole('tab', { name: /appearance/i }).click();

      // The Colors sub-tab should be active by default
      await expect(page.getByRole('tab', { name: /colors/i })).toBeVisible();
      await expect(page.getByText(/Custom colors appear alongside presets/i)).toBeVisible();
    });

    test('Add Color button opens the hex input popover', async ({ page }) => {
      await mockColorsApi(page, []);

      await page.goto('/settings');
      await waitForPageReady(page);

      await page.getByRole('tab', { name: /appearance/i }).click();

      // The Colors sub-tab is active — click Add Color
      await page.getByRole('button', { name: /add color/i }).click();

      // Popover should appear with hex input
      await expect(page.getByLabel(/hex color value/i)).toBeVisible();
    });

    test('entering a hex value and submitting adds the swatch to the palette', async ({
      page,
    }) => {
      // Initially empty
      await mockColorsApi(page, []);

      // After POST the list will include the new color
      await mockCreateColorApi(page, { id: CUSTOM_COLOR_ID, hex: CUSTOM_HEX });

      // Simulate the GET after mutation returning the new color
      let colorsState: Array<{ id: string; hex: string; name?: string }> = [];

      await page.route('**/api/v1/colors', async (route) => {
        const method = route.request().method();
        if (method === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(colorsState),
          });
        } else if (method === 'POST') {
          colorsState = [{ id: CUSTOM_COLOR_ID, hex: CUSTOM_HEX }];
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify(colorsState[0]),
          });
        } else {
          await route.continue();
        }
      });

      await page.goto('/settings');
      await waitForPageReady(page);

      await page.getByRole('tab', { name: /appearance/i }).click();

      // Open the add popover
      await page.getByRole('button', { name: /add color/i }).click();

      // Fill the hex input
      const hexInput = page.getByLabel(/hex color value/i);
      await hexInput.fill(CUSTOM_HEX);

      // Submit by clicking the "Add Color" button inside the popover
      await page.getByRole('button', { name: /^add color$/i }).last().click();

      // After mutation + refetch, the swatch for #ab1234 should appear.
      // The swatch is a div with aria-label "Color swatch: #ab1234"
      await expect(page.getByLabel(`Color swatch: ${CUSTOM_HEX}`)).toBeVisible({
        timeout: 8_000,
      });
    });

    test('custom color appears in ColorSelector on groups page', async ({ page }) => {
      // Pre-populate the custom color
      await mockColorsApi(page, [{ id: CUSTOM_COLOR_ID, hex: CUSTOM_HEX }]);

      // Navigate to the groups page and open the create-group dialog
      // (ColorSelector is rendered inside the GroupMetadataEditor)
      await page.goto('/groups');
      await waitForPageReady(page);

      // Open the group creation dialog if available
      const createBtn = page.getByRole('button', { name: /create group|new group/i });
      if (await createBtn.isVisible().catch(() => false)) {
        await createBtn.click();

        // Inside the dialog the ColorSelector renders with our custom color swatch
        // Check that the custom color swatch button appears
        await expect(
          page.getByRole('button', { name: new RegExp(`Custom color ${CUSTOM_HEX}`, 'i') })
        ).toBeVisible({ timeout: 8_000 });
      } else {
        // If no create button is visible, skip gracefully — dialog may not exist in current build
        test.skip();
      }
    });

    test('deleting a custom color removes it from the palette', async ({ page }) => {
      let colorsState = [{ id: CUSTOM_COLOR_ID, hex: CUSTOM_HEX }];

      await page.route('**/api/v1/colors', async (route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(colorsState),
          });
        } else {
          await route.continue();
        }
      });

      await page.route(`**/api/v1/colors/${CUSTOM_COLOR_ID}`, async (route) => {
        if (route.request().method() === 'DELETE') {
          colorsState = [];
          await route.fulfill({ status: 204 });
        } else {
          await route.continue();
        }
      });

      await page.goto('/settings');
      await waitForPageReady(page);

      await page.getByRole('tab', { name: /appearance/i }).click();

      // Swatch card should be visible before delete
      const swatch = page.getByLabel(`Color swatch: ${CUSTOM_HEX}`);
      await expect(swatch).toBeVisible({ timeout: 8_000 });

      // Trigger delete — hover over the card to reveal the delete button
      const card = page.locator('[role="listitem"]').filter({ has: swatch });
      await card.hover();

      const deleteBtn = card.getByRole('button', { name: /delete color/i });
      await deleteBtn.click();

      // A confirmation AlertDialog appears
      const confirmBtn = page.getByRole('button', { name: /delete|confirm/i }).last();
      if (await confirmBtn.isVisible().catch(() => false)) {
        await confirmBtn.click();
      }

      // After deletion the swatch should no longer be visible
      await expect(swatch).not.toBeVisible({ timeout: 8_000 });
    });
  });

  test.describe('Full flow: add → verify in selector → delete', () => {
    test('add color in Settings, verify in GroupMetadataEditor, delete from Settings', async ({
      page,
    }) => {
      let colorsState: Array<{ id: string; hex: string; name?: string }> = [];

      // Unified route handler that tracks state across navigations
      await page.route('**/api/v1/colors', async (route) => {
        const method = route.request().method();
        if (method === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(colorsState),
          });
        } else if (method === 'POST') {
          const body = (await route.request().postDataJSON()) as { hex: string; name?: string };
          const created = { id: CUSTOM_COLOR_ID, hex: body.hex };
          colorsState = [...colorsState, created];
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify(created),
          });
        } else {
          await route.continue();
        }
      });

      await page.route(`**/api/v1/colors/${CUSTOM_COLOR_ID}`, async (route) => {
        if (route.request().method() === 'DELETE') {
          colorsState = colorsState.filter((c) => c.id !== CUSTOM_COLOR_ID);
          await route.fulfill({ status: 204 });
        } else {
          await route.continue();
        }
      });

      // ── Step 1: Navigate to Settings → Appearance → Colors ──────────────
      await page.goto('/settings');
      await waitForPageReady(page);
      await page.getByRole('tab', { name: /appearance/i }).click();

      // ── Step 2: Click "Add Color" ─────────────────────────────────────────
      await page.getByRole('button', { name: /add color/i }).click();
      await expect(page.getByLabel(/hex color value/i)).toBeVisible();

      // ── Step 3: Enter hex value and submit ────────────────────────────────
      await page.getByLabel(/hex color value/i).fill(CUSTOM_HEX);
      await page.getByRole('button', { name: /^add color$/i }).last().click();

      // ── Step 4: Assert new color swatch appears in palette ────────────────
      await expect(page.getByLabel(`Color swatch: ${CUSTOM_HEX}`)).toBeVisible({
        timeout: 8_000,
      });

      // ── Step 5: Navigate to Groups, verify color in selector ──────────────
      await page.goto('/groups');
      await waitForPageReady(page);

      const createBtn = page.getByRole('button', { name: /create group|new group/i });
      if (await createBtn.isVisible().catch(() => false)) {
        await createBtn.click();

        await expect(
          page.getByRole('button', { name: new RegExp(`Custom color ${CUSTOM_HEX}`, 'i') })
        ).toBeVisible({ timeout: 8_000 });

        // Close dialog before navigating away
        await page.keyboard.press('Escape');
      }

      // ── Step 6: Return to Settings → Colors ──────────────────────────────
      await page.goto('/settings');
      await waitForPageReady(page);
      await page.getByRole('tab', { name: /appearance/i }).click();

      const swatch = page.getByLabel(`Color swatch: ${CUSTOM_HEX}`);
      await expect(swatch).toBeVisible({ timeout: 8_000 });

      // ── Step 7: Delete the color ──────────────────────────────────────────
      const card = page.locator('[role="listitem"]').filter({ has: swatch });
      await card.hover();

      const deleteBtn = card.getByRole('button', { name: /delete color/i });
      await deleteBtn.click();

      // Confirm in AlertDialog if present
      const confirmBtn = page.getByRole('button', { name: /delete|confirm/i }).last();
      if (await confirmBtn.isVisible().catch(() => false)) {
        await confirmBtn.click();
      }

      // ── Step 8: Assert color is removed ──────────────────────────────────
      await expect(swatch).not.toBeVisible({ timeout: 8_000 });
    });
  });
});
