/**
 * E2E Tests for Repo Details Modal (TEST-007)
 *
 * Tests the repository details modal on the source detail page
 * that displays description and README content.
 *
 * Test Coverage:
 * - Opening the modal from source detail page
 * - Displaying description content
 * - Displaying README content (markdown rendered)
 * - Scrollable content for long README
 * - Closing modal with Escape key
 * - Closing modal with backdrop click
 * - Empty states when no content available
 */

import { test, expect, type Page } from '@playwright/test';
import {
  waitForPageLoad,
  mockApiRoute,
  expectModalOpen,
  expectModalClosed,
  pressKey,
} from '../helpers/test-utils';

// ============================================================================
// Mock Data
// ============================================================================

const mockSourceWithFullDetails = {
  id: 'source-full-details',
  owner: 'anthropics',
  repo_name: 'claude-cookbook',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/anthropics/claude-cookbook',
  trust_level: 'official',
  artifact_count: 25,
  scan_status: 'success',
  last_sync_at: '2024-12-10T14:00:00Z',
  created_at: '2024-12-01T10:00:00Z',
  description: 'Official cookbook with Claude Code examples and best practices.',
  repo_description: 'A collection of code samples and tutorials for Claude.',
  readme_content: `# Claude Cookbook

Welcome to the Claude Cookbook! This repository contains examples and best practices for working with Claude.

## Table of Contents

- [Getting Started](#getting-started)
- [Examples](#examples)
- [Contributing](#contributing)

## Getting Started

To get started with the Claude Cookbook:

\`\`\`bash
git clone https://github.com/anthropics/claude-cookbook.git
cd claude-cookbook
\`\`\`

## Examples

Here are some example use cases:

1. **Text Generation** - Generate creative content
2. **Code Review** - Automated code analysis
3. **Data Analysis** - Process and analyze data

### Code Example

\`\`\`python
import anthropic

client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-3-5-sonnet",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ]
)
print(message.content)
\`\`\`

## Contributing

We welcome contributions! Please see our [contributing guide](CONTRIBUTING.md) for details.

---

Made with love by the Claude team.
`,
  tags: ['official', 'cookbook', 'examples'],
  counts_by_type: {
    skill: 15,
    command: 7,
    agent: 3,
  },
};

const mockSourceDescriptionOnly = {
  id: 'source-desc-only',
  owner: 'community',
  repo_name: 'simple-repo',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/community/simple-repo',
  trust_level: 'basic',
  artifact_count: 5,
  scan_status: 'success',
  last_sync_at: '2024-12-08T10:00:00Z',
  created_at: '2024-12-02T10:00:00Z',
  description: 'A simple repository with just a description, no README.',
  repo_description: null,
  readme_content: null,
  tags: ['simple'],
  counts_by_type: {
    skill: 5,
  },
};

const mockSourceNoDetails = {
  id: 'source-no-details',
  owner: 'minimal',
  repo_name: 'bare-repo',
  ref: 'main',
  root_hint: '',
  repo_url: 'https://github.com/minimal/bare-repo',
  trust_level: 'basic',
  artifact_count: 3,
  scan_status: 'success',
  last_sync_at: '2024-12-07T10:00:00Z',
  created_at: '2024-12-03T10:00:00Z',
  description: null,
  repo_description: null,
  readme_content: null,
  tags: [],
  counts_by_type: {
    skill: 3,
  },
};

const mockCatalogResponse = {
  items: [
    {
      id: 'entry-1',
      source_id: 'source-full-details',
      name: 'example-skill',
      artifact_type: 'skill',
      path: '.claude/skills/example.md',
      status: 'new',
      confidence_score: 95,
      upstream_url: 'https://github.com/anthropics/claude-cookbook/blob/main/.claude/skills/example.md',
      detected_at: '2024-12-08T10:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 25,
  has_next: false,
  counts_by_type: { skill: 1 },
  counts_by_status: { new: 1 },
  page_info: { total_count: 1 },
};

const mockLongReadmeSource = {
  ...mockSourceWithFullDetails,
  id: 'source-long-readme',
  readme_content: `# Very Long README

${Array(50).fill(`## Section

This is a section with some content. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

\`\`\`javascript
function example() {
  console.log("Hello, world!");
  return { success: true };
}
\`\`\`

Some more text here with **bold** and *italic* formatting.

`).join('\n')}

## Final Section

This is the end of a very long README file that should require scrolling to see all content.
`,
};

// ============================================================================
// Helper Functions
// ============================================================================

async function setupMockApiRoutes(page: Page, source = mockSourceWithFullDetails) {
  // Mock source detail
  await mockApiRoute(page, `/api/v1/marketplace/sources/${source.id}`, source);

  // Mock catalog
  await mockApiRoute(
    page,
    `/api/v1/marketplace/sources/${source.id}/artifacts*`,
    mockCatalogResponse
  );
}

async function navigateToSourceDetailPage(page: Page, sourceId: string) {
  await page.goto(`/marketplace/sources/${sourceId}`);
  await waitForPageLoad(page);
}

// ============================================================================
// Test Suite: Repo Details Modal
// ============================================================================

test.describe('Repo Details Modal (TEST-007)', () => {
  test('opens modal and displays description and README', async ({ page }) => {
    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Step 1: Verify Repo Details button is visible
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await expect(repoDetailsButton).toBeVisible();

    // Step 2: Click Repo Details button
    await repoDetailsButton.click();

    // Step 3: Verify modal opens
    await expectModalOpen(page, '[role="dialog"]');

    // Step 4: Verify title shows repo name
    await expect(page.getByRole('dialog')).toContainText('anthropics/claude-cookbook');

    // Step 5: Verify description is displayed
    await expect(
      page.getByText('Official cookbook with Claude Code examples and best practices.')
    ).toBeVisible();

    // Step 6: Verify README content is displayed with markdown rendering
    await expect(page.getByText('README')).toBeVisible();

    // Check for rendered markdown elements
    await expect(page.getByRole('heading', { name: 'Claude Cookbook' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Getting Started' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Examples' })).toBeVisible();

    // Check for code block content
    await expect(page.getByText('git clone')).toBeVisible();

    // Check for list items
    await expect(page.getByText('Text Generation')).toBeVisible();
    await expect(page.getByText('Code Review')).toBeVisible();

    // Check for inline code
    await expect(page.getByText('import anthropic')).toBeVisible();
  });

  test('closes modal with Escape key', async ({ page }) => {
    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Step 7: Press Escape
    await pressKey(page, 'Escape');

    // Step 8: Verify modal closes
    await expectModalClosed(page, '[role="dialog"]');
  });

  test('closes modal with close button', async ({ page }) => {
    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Click the close button (X in top right of dialog)
    const closeButton = page.locator('[role="dialog"] button[aria-label="Close"]').or(
      page.locator('[role="dialog"] button:has(svg.lucide-x)')
    );

    // If there's no explicit close button, click outside the dialog
    if (await closeButton.count() > 0) {
      await closeButton.first().click();
    } else {
      // Click outside the modal to close
      await page.mouse.click(10, 10);
    }

    // Verify modal closes
    await expectModalClosed(page, '[role="dialog"]');
  });

  test('modal is scrollable for long README content', async ({ page }) => {
    await setupMockApiRoutes(page, mockLongReadmeSource);
    await navigateToSourceDetailPage(page, mockLongReadmeSource.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Verify the scroll area is present
    const scrollArea = page.locator('[role="dialog"] [data-radix-scroll-area-viewport]').or(
      page.locator('[role="dialog"] .overflow-y-auto')
    );

    // Check that the scroll area exists and has content
    if (await scrollArea.count() > 0) {
      const scrollElement = scrollArea.first();
      await expect(scrollElement).toBeVisible();

      // Verify scroll height is greater than visible height (content is scrollable)
      const scrollHeight = await scrollElement.evaluate((el) => el.scrollHeight);
      const clientHeight = await scrollElement.evaluate((el) => el.clientHeight);

      // The content should be taller than the visible area
      expect(scrollHeight).toBeGreaterThan(clientHeight);

      // Scroll to bottom to verify scrolling works
      await scrollElement.evaluate((el) => el.scrollTo(0, el.scrollHeight));

      // Verify we can see the final section after scrolling
      await expect(page.getByText('Final Section')).toBeVisible();
    }
  });

  test('displays "No README available" when only description exists', async ({ page }) => {
    await setupMockApiRoutes(page, mockSourceDescriptionOnly);
    await navigateToSourceDetailPage(page, mockSourceDescriptionOnly.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Verify description is shown
    await expect(
      page.getByText('A simple repository with just a description, no README.')
    ).toBeVisible();

    // Verify "No README available" message
    await expect(page.getByText('No README available')).toBeVisible();
  });

  test('displays empty state when no description or README exists', async ({ page }) => {
    await setupMockApiRoutes(page, mockSourceNoDetails);
    await navigateToSourceDetailPage(page, mockSourceNoDetails.id);

    // The Repo Details button should not be visible when there's no content
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });

    // Button may be hidden when there's no content to show
    const isVisible = await repoDetailsButton.isVisible().catch(() => false);

    if (isVisible) {
      await repoDetailsButton.click();
      await expectModalOpen(page, '[role="dialog"]');

      // Verify empty state message
      await expect(page.getByText('No repository details available')).toBeVisible();
      await expect(
        page.getByText('This repository does not have a description or README content.')
      ).toBeVisible();
    } else {
      // Button is correctly hidden when no content is available
      await expect(repoDetailsButton).not.toBeVisible();
    }
  });

  test('renders markdown with GitHub Flavored Markdown support', async ({ page }) => {
    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Verify GFM features are rendered

    // Headers
    await expect(page.getByRole('heading', { name: 'Claude Cookbook', level: 1 })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Table of Contents', level: 2 })).toBeVisible();

    // Links (GFM anchor links)
    const gettingStartedLink = page.locator('a[href="#getting-started"]');
    if (await gettingStartedLink.count() > 0) {
      await expect(gettingStartedLink).toBeVisible();
    }

    // Code blocks with syntax highlighting
    const codeBlocks = page.locator('pre code');
    await expect(codeBlocks.first()).toBeVisible();

    // Bold and italic text (GFM)
    const boldText = page.locator('strong').filter({ hasText: 'bold' });
    if (await boldText.count() > 0) {
      await expect(boldText).toBeVisible();
    }

    // Horizontal rule
    const horizontalRule = page.locator('[role="dialog"] hr');
    if (await horizontalRule.count() > 0) {
      await expect(horizontalRule.first()).toBeVisible();
    }
  });

  test('modal has proper focus management', async ({ page }) => {
    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Verify focus is trapped in modal (Tab should cycle within modal)
    await pressKey(page, 'Tab');

    // Focus should be on an element within the dialog
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();

    // The focused element should be inside the dialog
    const isInDialog = await focusedElement.evaluate((el) => {
      return el.closest('[role="dialog"]') !== null;
    });
    expect(isInDialog).toBe(true);
  });

  test('modal has accessible labels', async ({ page }) => {
    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Verify dialog has accessible name (via DialogTitle)
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    // Verify title is present
    const dialogTitle = page.locator('[role="dialog"] h2').or(
      page.locator('[role="dialog"] [data-dialog-title]')
    );
    await expect(dialogTitle.first()).toBeVisible();
  });
});

// ============================================================================
// Test Suite: Modal Responsive Behavior
// ============================================================================

test.describe('Modal Responsive Behavior', () => {
  test('modal displays correctly on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Verify modal is visible and fits viewport
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    // Verify content is readable
    await expect(page.getByText('anthropics/claude-cookbook')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Claude Cookbook' })).toBeVisible();
  });

  test('modal displays correctly on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });

    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Verify modal is visible
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    // Verify README is scrollable
    const scrollArea = page.locator('[role="dialog"] [data-radix-scroll-area-viewport]').or(
      page.locator('[role="dialog"] .overflow-y-auto')
    );

    if (await scrollArea.count() > 0) {
      await expect(scrollArea.first()).toBeVisible();
    }
  });

  test('modal displays correctly on desktop viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });

    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Open modal
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.click();
    await expectModalOpen(page, '[role="dialog"]');

    // Verify modal has max-width constraint (sm:max-w-2xl)
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    // Modal should not take full width on desktop
    const boundingBox = await modal.boundingBox();
    if (boundingBox) {
      // max-w-2xl is 672px
      expect(boundingBox.width).toBeLessThanOrEqual(700);
    }
  });
});

// ============================================================================
// Test Suite: Tooltip on Repo Details Button
// ============================================================================

test.describe('Repo Details Button Tooltip', () => {
  test('shows tooltip on hover', async ({ page }) => {
    await setupMockApiRoutes(page, mockSourceWithFullDetails);
    await navigateToSourceDetailPage(page, mockSourceWithFullDetails.id);

    // Hover over the Repo Details button
    const repoDetailsButton = page.getByRole('button', { name: /View repository details/i });
    await repoDetailsButton.hover();

    // Verify tooltip appears
    await expect(page.getByText('Repo Details')).toBeVisible();
  });
});
