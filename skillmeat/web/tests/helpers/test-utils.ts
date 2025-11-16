/**
 * Test Utilities
 *
 * Common helper functions for E2E tests
 */

import { Page, expect } from '@playwright/test';

/**
 * Wait for page to be fully loaded including network idle
 */
export async function waitForPageLoad(page: Page) {
  await page.waitForLoadState('networkidle');
  await page.waitForLoadState('domcontentloaded');
}

/**
 * Mock API route with custom response
 */
export async function mockApiRoute(
  page: Page,
  route: string,
  response: any,
  status: number = 200
) {
  await page.route(`**${route}`, async (route) => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

/**
 * Mock all common API routes with default responses
 */
export async function mockAllApiRoutes(page: Page, fixtures: any) {
  // Artifacts list
  await mockApiRoute(page, '/api/artifacts*', fixtures.artifacts());

  // Analytics
  await mockApiRoute(page, '/api/analytics*', fixtures.analytics());

  // Projects
  await mockApiRoute(page, '/api/projects*', fixtures.projects());
}

/**
 * Navigate to a page and wait for it to load
 */
export async function navigateToPage(page: Page, path: string) {
  await page.goto(path);
  await waitForPageLoad(page);
}

/**
 * Check if an element is visible and has expected text
 */
export async function expectTextVisible(
  page: Page,
  selector: string,
  text: string | RegExp
) {
  const element = page.locator(selector);
  await expect(element).toBeVisible();
  await expect(element).toContainText(text);
}

/**
 * Check if button is in expected state
 */
export async function expectButtonState(
  page: Page,
  selector: string,
  options: {
    visible?: boolean;
    disabled?: boolean;
    pressed?: boolean;
  }
) {
  const button = page.locator(selector);

  if (options.visible !== undefined) {
    if (options.visible) {
      await expect(button).toBeVisible();
    } else {
      await expect(button).toBeHidden();
    }
  }

  if (options.disabled !== undefined) {
    if (options.disabled) {
      await expect(button).toBeDisabled();
    } else {
      await expect(button).toBeEnabled();
    }
  }

  if (options.pressed !== undefined) {
    const pressed = await button.getAttribute('aria-pressed');
    expect(pressed).toBe(options.pressed.toString());
  }
}

/**
 * Wait for an element to appear with timeout
 */
export async function waitForElement(
  page: Page,
  selector: string,
  timeout: number = 5000
) {
  await page.waitForSelector(selector, { timeout, state: 'visible' });
}

/**
 * Click element and wait for navigation
 */
export async function clickAndWaitForNavigation(page: Page, selector: string) {
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle' }),
    page.click(selector),
  ]);
}

/**
 * Type in input field and verify value
 */
export async function typeInInput(
  page: Page,
  selector: string,
  text: string,
  verify: boolean = true
) {
  const input = page.locator(selector);
  await input.fill(text);

  if (verify) {
    await expect(input).toHaveValue(text);
  }
}

/**
 * Select option from dropdown
 */
export async function selectDropdownOption(
  page: Page,
  selector: string,
  value: string
) {
  await page.selectOption(selector, value);
}

/**
 * Check if modal/dialog is open
 */
export async function expectModalOpen(page: Page, modalSelector: string) {
  const modal = page.locator(modalSelector);
  await expect(modal).toBeVisible();
  const ariaHidden = await modal.getAttribute('aria-hidden');
  expect(ariaHidden).not.toBe('true');
}

/**
 * Check if modal/dialog is closed
 */
export async function expectModalClosed(page: Page, modalSelector: string) {
  const modal = page.locator(modalSelector);
  await expect(modal).toBeHidden();
}

/**
 * Press keyboard key
 */
export async function pressKey(page: Page, key: string) {
  await page.keyboard.press(key);
}

/**
 * Check element has focus
 */
export async function expectFocused(page: Page, selector: string) {
  const element = page.locator(selector);
  await expect(element).toBeFocused();
}

/**
 * Tab through elements and verify order
 */
export async function verifyTabOrder(page: Page, selectors: string[]) {
  for (const selector of selectors) {
    await pressKey(page, 'Tab');
    await expectFocused(page, selector);
  }
}

/**
 * Get text content of element
 */
export async function getTextContent(
  page: Page,
  selector: string
): Promise<string> {
  const element = page.locator(selector);
  return (await element.textContent()) || '';
}

/**
 * Count number of elements matching selector
 */
export async function countElements(page: Page, selector: string): Promise<number> {
  return await page.locator(selector).count();
}

/**
 * Scroll element into view
 */
export async function scrollIntoView(page: Page, selector: string) {
  await page.locator(selector).scrollIntoViewIfNeeded();
}

/**
 * Take screenshot with name
 */
export async function takeScreenshot(page: Page, name: string) {
  await page.screenshot({
    path: `test-results/screenshots/${name}.png`,
    fullPage: true,
  });
}

/**
 * Wait for API response
 */
export async function waitForApiResponse(page: Page, urlPattern: string) {
  return await page.waitForResponse((response) =>
    response.url().includes(urlPattern)
  );
}

/**
 * Check loading state
 */
export async function expectLoadingState(
  page: Page,
  selector: string,
  isLoading: boolean
) {
  const element = page.locator(selector);
  const ariaLive = await element.getAttribute('aria-live');
  const ariaBusy = await element.getAttribute('aria-busy');

  if (isLoading) {
    expect(ariaLive || ariaBusy).toBeTruthy();
  } else {
    const text = await getTextContent(page, selector);
    expect(text).not.toContain('Loading');
  }
}

/**
 * Verify error message is displayed
 */
export async function expectErrorMessage(page: Page, message: string | RegExp) {
  const errorElement = page.locator('[role="alert"], .error, .destructive');
  await expect(errorElement).toBeVisible();
  await expect(errorElement).toContainText(message);
}

/**
 * Verify success message is displayed
 */
export async function expectSuccessMessage(page: Page, message: string | RegExp) {
  const successElement = page.locator('[role="status"], .success');
  await expect(successElement).toBeVisible();
  await expect(successElement).toContainText(message);
}
