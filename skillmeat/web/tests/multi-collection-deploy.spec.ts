/**
 * Multi-Collection Deployment Integration Tests
 *
 * Tests for verifying correct collection tracking and artifact type handling
 * during deployments from multiple collections.
 *
 * Key scenarios:
 * - Deploying from specific collections (not 'default')
 * - Same-name artifacts with different types
 * - Collection ID tracking in deployment records
 */

import { test, expect } from '@playwright/test';
import {
  mockApiRoute,
  navigateToPage,
  waitForElement,
  expectSuccessMessage,
  expectErrorMessage,
} from './helpers/test-utils';
import { buildApiResponse, mockArtifacts } from './helpers/fixtures';

/** Mock collections with distinct IDs */
const mockCollections = [
  {
    id: 'collection-a',
    name: 'Collection A',
    description: 'First test collection',
    artifact_count: 3,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'collection-b',
    name: 'Collection B',
    description: 'Second test collection',
    artifact_count: 2,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
  {
    id: 'default',
    name: 'Default Collection',
    description: 'Default collection',
    artifact_count: 1,
    created_at: '2024-01-03T00:00:00Z',
    updated_at: '2024-01-03T00:00:00Z',
  },
];

/** Mock artifacts with same names but different types */
const mockCollectionArtifacts = {
  'collection-a': [
    {
      id: 'artifact-skill-1',
      name: 'test-artifact',
      type: 'skill',
      scope: 'user',
      status: 'active',
      version: '1.0.0',
      source: 'user/repo/skills/test-artifact',
      metadata: {
        title: 'Test Skill',
        description: 'A test skill artifact',
        author: 'Test User',
        license: 'MIT',
        version: '1.0.0',
        tags: ['test', 'skill'],
      },
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    },
    {
      id: 'artifact-command-1',
      name: 'test-artifact',
      type: 'command',
      scope: 'user',
      status: 'active',
      version: '1.0.0',
      source: 'user/repo/commands/test-artifact',
      metadata: {
        title: 'Test Command',
        description: 'A test command artifact',
        author: 'Test User',
        license: 'MIT',
        version: '1.0.0',
        tags: ['test', 'command'],
      },
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    },
    {
      id: 'artifact-unique-1',
      name: 'unique-skill',
      type: 'skill',
      scope: 'user',
      status: 'active',
      version: '2.0.0',
      source: 'user/repo/skills/unique-skill',
      metadata: {
        title: 'Unique Skill',
        description: 'A unique skill artifact',
        author: 'Test User',
        license: 'MIT',
        version: '2.0.0',
        tags: ['unique'],
      },
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    },
  ],
  'collection-b': [
    {
      id: 'artifact-skill-2',
      name: 'test-artifact',
      type: 'skill',
      scope: 'user',
      status: 'active',
      version: '2.0.0',
      source: 'user/repo/skills/test-artifact-v2',
      metadata: {
        title: 'Test Skill v2',
        description: 'Updated test skill artifact',
        author: 'Test User',
        license: 'MIT',
        version: '2.0.0',
        tags: ['test', 'skill'],
      },
      createdAt: '2024-01-02T00:00:00Z',
      updatedAt: '2024-01-02T00:00:00Z',
    },
    {
      id: 'artifact-agent-1',
      name: 'test-artifact',
      type: 'agent',
      scope: 'user',
      status: 'active',
      version: '1.0.0',
      source: 'user/repo/agents/test-artifact',
      metadata: {
        title: 'Test Agent',
        description: 'A test agent artifact',
        author: 'Test User',
        license: 'MIT',
        version: '1.0.0',
        tags: ['test', 'agent'],
      },
      createdAt: '2024-01-02T00:00:00Z',
      updatedAt: '2024-01-02T00:00:00Z',
    },
  ],
  default: [
    {
      id: 'artifact-default-1',
      name: 'default-skill',
      type: 'skill',
      scope: 'user',
      status: 'active',
      version: '1.0.0',
      source: 'user/repo/skills/default-skill',
      metadata: {
        title: 'Default Skill',
        description: 'A skill in default collection',
        author: 'Test User',
        license: 'MIT',
        version: '1.0.0',
        tags: ['default'],
      },
      createdAt: '2024-01-03T00:00:00Z',
      updatedAt: '2024-01-03T00:00:00Z',
    },
  ],
};

/** Mock project for deployments */
const mockProject = {
  id: 'test-project-1',
  name: 'test-project',
  path: '/home/user/test-project',
  artifacts: [],
  lastSync: '2024-01-01T00:00:00Z',
};

test.describe('Multi-Collection Deployment', () => {
  test.beforeEach(async ({ page }) => {
    // Mock collections API
    await mockApiRoute(page, '/api/v1/collections*', {
      collections: mockCollections,
      total: mockCollections.length,
    });

    // Mock projects API
    await mockApiRoute(page, '/api/v1/projects*', {
      projects: [mockProject],
      total: 1,
    });

    // Mock analytics API
    await mockApiRoute(page, '/api/v1/analytics*', buildApiResponse.analytics());
  });

  test.describe('Collection ID Tracking', () => {
    test('should include collection ID when deploying from collection-a', async ({ page }) => {
      // Mock artifacts for collection-a
      await mockApiRoute(
        page,
        '/api/v1/collections/collection-a/artifacts*',
        mockCollectionArtifacts['collection-a']
      );

      // Capture deploy request
      let deployRequest: any = null;
      await page.route('**/api/v1/deploy', async (route) => {
        const request = route.request();
        deployRequest = JSON.parse(request.postData() || '{}');

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Deployed successfully',
            artifact_name: deployRequest.artifact_name,
            artifact_type: deployRequest.artifact_type,
            project_path: mockProject.path,
            deployed_path: `${mockProject.path}/.claude/skills/${deployRequest.artifact_name}`,
            deployed_at: new Date().toISOString(),
          }),
        });
      });

      // Navigate to collection-a
      await navigateToPage(page, '/collection?collection_id=collection-a');

      // Open artifact detail for unique-skill
      const artifactCard = page.locator('[data-testid="artifact-card"]', {
        hasText: 'unique-skill',
      });
      await artifactCard.click();
      await waitForElement(page, '[role="dialog"]');

      // Click deploy button
      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();
      await waitForElement(page, '[data-testid="deploy-modal"]');

      // Select project
      const projectSelect = page.locator('select[name="project"]');
      await projectSelect.selectOption(mockProject.id);

      // Confirm deployment
      const confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      // Wait for request to be captured
      await page.waitForTimeout(500);

      // Verify request includes correct collection_name
      expect(deployRequest).not.toBeNull();
      expect(deployRequest.collection_name).toBe('collection-a');
      expect(deployRequest.artifact_name).toBe('unique-skill');
      expect(deployRequest.artifact_type).toBe('skill');
    });

    test('should include collection ID when deploying from collection-b', async ({ page }) => {
      // Mock artifacts for collection-b
      await mockApiRoute(
        page,
        '/api/v1/collections/collection-b/artifacts*',
        mockCollectionArtifacts['collection-b']
      );

      // Capture deploy request
      let deployRequest: any = null;
      await page.route('**/api/v1/deploy', async (route) => {
        const request = route.request();
        deployRequest = JSON.parse(request.postData() || '{}');

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Deployed successfully',
            artifact_name: deployRequest.artifact_name,
            artifact_type: deployRequest.artifact_type,
            project_path: mockProject.path,
            deployed_path: `${mockProject.path}/.claude/skills/${deployRequest.artifact_name}`,
            deployed_at: new Date().toISOString(),
          }),
        });
      });

      // Navigate to collection-b
      await navigateToPage(page, '/collection?collection_id=collection-b');

      // Open artifact detail for test-artifact (skill v2)
      const artifactCards = page.locator('[data-testid="artifact-card"]', {
        hasText: 'test-artifact',
      });
      // Select the skill type (first one)
      await artifactCards.first().click();
      await waitForElement(page, '[role="dialog"]');

      // Click deploy button
      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();
      await waitForElement(page, '[data-testid="deploy-modal"]');

      // Select project
      const projectSelect = page.locator('select[name="project"]');
      await projectSelect.selectOption(mockProject.id);

      // Confirm deployment
      const confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      // Wait for request to be captured
      await page.waitForTimeout(500);

      // Verify request includes correct collection_name
      expect(deployRequest).not.toBeNull();
      expect(deployRequest.collection_name).toBe('collection-b');
      expect(deployRequest.artifact_name).toBe('test-artifact');
      expect(deployRequest.artifact_type).toBe('skill');
    });

    test('should not use "default" as fallback for specific collections', async ({ page }) => {
      // Mock artifacts for collection-a
      await mockApiRoute(
        page,
        '/api/v1/collections/collection-a/artifacts*',
        mockCollectionArtifacts['collection-a']
      );

      // Capture deploy request
      let deployRequest: any = null;
      await page.route('**/api/v1/deploy', async (route) => {
        const request = route.request();
        deployRequest = JSON.parse(request.postData() || '{}');

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Deployed successfully',
            artifact_name: deployRequest.artifact_name,
            artifact_type: deployRequest.artifact_type,
            project_path: mockProject.path,
            deployed_path: `${mockProject.path}/.claude/skills/${deployRequest.artifact_name}`,
            deployed_at: new Date().toISOString(),
          }),
        });
      });

      // Navigate to collection-a
      await navigateToPage(page, '/collection?collection_id=collection-a');

      // Deploy any artifact
      const artifactCard = page.locator('[data-testid="artifact-card"]').first();
      await artifactCard.click();
      await waitForElement(page, '[role="dialog"]');

      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();
      await waitForElement(page, '[data-testid="deploy-modal"]');

      const projectSelect = page.locator('select[name="project"]');
      await projectSelect.selectOption(mockProject.id);

      const confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      await page.waitForTimeout(500);

      // Verify collection_name is NOT 'default'
      expect(deployRequest).not.toBeNull();
      expect(deployRequest.collection_name).not.toBe('default');
      expect(deployRequest.collection_name).toBe('collection-a');
    });
  });

  test.describe('Same-Name Different-Type Artifacts', () => {
    test('should distinguish test-artifact skill from test-artifact command', async ({ page }) => {
      // Mock artifacts for collection-a
      await mockApiRoute(
        page,
        '/api/v1/collections/collection-a/artifacts*',
        mockCollectionArtifacts['collection-a']
      );

      // Capture both deploy requests
      const deployRequests: any[] = [];
      await page.route('**/api/v1/deploy', async (route) => {
        const request = route.request();
        const deployRequest = JSON.parse(request.postData() || '{}');
        deployRequests.push(deployRequest);

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Deployed successfully',
            artifact_name: deployRequest.artifact_name,
            artifact_type: deployRequest.artifact_type,
            project_path: mockProject.path,
            deployed_path: `${mockProject.path}/.claude/${deployRequest.artifact_type}s/${deployRequest.artifact_name}`,
            deployed_at: new Date().toISOString(),
          }),
        });
      });

      // Navigate to collection-a
      await navigateToPage(page, '/collection?collection_id=collection-a');

      // Deploy test-artifact skill (first occurrence)
      const skillCard = page.locator('[data-testid="artifact-card"]', {
        hasText: 'test-artifact',
      }).filter({ has: page.locator('text=skill') });

      await skillCard.click();
      await waitForElement(page, '[role="dialog"]');

      let deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();
      await waitForElement(page, '[data-testid="deploy-modal"]');

      let projectSelect = page.locator('select[name="project"]');
      await projectSelect.selectOption(mockProject.id);

      let confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      await page.waitForTimeout(500);

      // Close dialog/modal
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);

      // Deploy test-artifact command (second occurrence)
      const commandCard = page.locator('[data-testid="artifact-card"]', {
        hasText: 'test-artifact',
      }).filter({ has: page.locator('text=command') });

      await commandCard.click();
      await waitForElement(page, '[role="dialog"]');

      deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();
      await waitForElement(page, '[data-testid="deploy-modal"]');

      projectSelect = page.locator('select[name="project"]');
      await projectSelect.selectOption(mockProject.id);

      confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      await page.waitForTimeout(500);

      // Verify both deployments captured with correct types
      expect(deployRequests.length).toBe(2);

      const skillDeploy = deployRequests.find((r) => r.artifact_type === 'skill');
      const commandDeploy = deployRequests.find((r) => r.artifact_type === 'command');

      expect(skillDeploy).toBeDefined();
      expect(skillDeploy?.artifact_name).toBe('test-artifact');
      expect(skillDeploy?.artifact_type).toBe('skill');

      expect(commandDeploy).toBeDefined();
      expect(commandDeploy?.artifact_name).toBe('test-artifact');
      expect(commandDeploy?.artifact_type).toBe('command');

      // Verify they don't collide (different types = different deployments)
      expect(skillDeploy?.artifact_id).not.toBe(commandDeploy?.artifact_id);
    });

    test('should list deployments with correct artifact type matching', async ({ page }) => {
      // Mock existing deployments with same names but different types
      await mockApiRoute(page, '/api/v1/deploy?project_path=*', {
        project_path: mockProject.path,
        deployments: [
          {
            artifact_name: 'test-artifact',
            artifact_type: 'skill',
            from_collection: 'collection-a',
            deployed_at: '2024-01-01T10:00:00Z',
            artifact_path: '.claude/skills/test-artifact',
            project_path: mockProject.path,
            collection_sha: 'abc123',
            local_modifications: false,
            sync_status: 'synced',
          },
          {
            artifact_name: 'test-artifact',
            artifact_type: 'command',
            from_collection: 'collection-a',
            deployed_at: '2024-01-01T11:00:00Z',
            artifact_path: '.claude/commands/test-artifact',
            project_path: mockProject.path,
            collection_sha: 'def456',
            local_modifications: false,
            sync_status: 'synced',
          },
          {
            artifact_name: 'test-artifact',
            artifact_type: 'agent',
            from_collection: 'collection-b',
            deployed_at: '2024-01-01T12:00:00Z',
            artifact_path: '.claude/agents/test-artifact',
            project_path: mockProject.path,
            collection_sha: 'ghi789',
            local_modifications: false,
            sync_status: 'synced',
          },
        ],
        total: 3,
      });

      // Navigate to project deployments page
      await navigateToPage(page, '/projects/test-project-1/deployments');

      // Verify all three deployments are listed separately
      const deploymentRows = page.locator('[data-testid="deployment-row"]');
      const count = await deploymentRows.count();
      expect(count).toBe(3);

      // Verify skill deployment shows correct collection
      const skillRow = page.locator('[data-testid="deployment-row"]', {
        hasText: 'skill',
      }).filter({ hasText: 'test-artifact' });
      await expect(skillRow).toContainText('collection-a');

      // Verify command deployment shows correct collection
      const commandRow = page.locator('[data-testid="deployment-row"]', {
        hasText: 'command',
      }).filter({ hasText: 'test-artifact' });
      await expect(commandRow).toContainText('collection-a');

      // Verify agent deployment shows correct collection
      const agentRow = page.locator('[data-testid="deployment-row"]', {
        hasText: 'agent',
      }).filter({ hasText: 'test-artifact' });
      await expect(agentRow).toContainText('collection-b');
    });

    test('should match deployment by both name AND type when checking status', async ({ page }) => {
      // Mock artifacts for collection-a
      await mockApiRoute(
        page,
        '/api/v1/collections/collection-a/artifacts*',
        mockCollectionArtifacts['collection-a']
      );

      // Mock existing deployments (only skill deployed, not command)
      await mockApiRoute(page, '/api/v1/deploy?project_path=*', {
        project_path: mockProject.path,
        deployments: [
          {
            artifact_name: 'test-artifact',
            artifact_type: 'skill',
            from_collection: 'collection-a',
            deployed_at: '2024-01-01T10:00:00Z',
            artifact_path: '.claude/skills/test-artifact',
            project_path: mockProject.path,
            collection_sha: 'abc123',
            local_modifications: false,
            sync_status: 'synced',
          },
        ],
        total: 1,
      });

      await navigateToPage(page, '/collection?collection_id=collection-a');

      // Check status of test-artifact skill (should show as deployed)
      const skillCard = page.locator('[data-testid="artifact-card"]', {
        hasText: 'test-artifact',
      }).filter({ has: page.locator('text=skill') });

      await expect(skillCard.locator('[data-testid="deployment-status"]')).toHaveText(
        /deployed|active/i
      );

      // Check status of test-artifact command (should NOT show as deployed)
      const commandCard = page.locator('[data-testid="artifact-card"]', {
        hasText: 'test-artifact',
      }).filter({ has: page.locator('text=command') });

      // Command should not have deployed status (or should show as "not deployed")
      const commandStatus = commandCard.locator('[data-testid="deployment-status"]');
      await expect(commandStatus).not.toHaveText(/deployed|active/i);
    });
  });

  test.describe('Error Handling', () => {
    test('should handle deployment error with collection context', async ({ page }) => {
      // Mock artifacts for collection-a
      await mockApiRoute(
        page,
        '/api/v1/collections/collection-a/artifacts*',
        mockCollectionArtifacts['collection-a']
      );

      // Mock deployment error
      await page.route('**/api/v1/deploy', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Artifact not found in collection collection-a',
          }),
        });
      });

      await navigateToPage(page, '/collection?collection_id=collection-a');

      const artifactCard = page.locator('[data-testid="artifact-card"]').first();
      await artifactCard.click();
      await waitForElement(page, '[role="dialog"]');

      const deployButton = page.locator('button:has-text("Deploy")');
      await deployButton.click();
      await waitForElement(page, '[data-testid="deploy-modal"]');

      const projectSelect = page.locator('select[name="project"]');
      await projectSelect.selectOption(mockProject.id);

      const confirmButton = page.locator('[data-testid="deploy-modal"] button:has-text("Deploy")');
      await confirmButton.click();

      // Should show error message with collection context
      await expectErrorMessage(page, /collection-a/i);
    });
  });
});
