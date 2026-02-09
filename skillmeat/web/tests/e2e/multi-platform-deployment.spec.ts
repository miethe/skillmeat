import { expect, test } from '@playwright/test';

test.describe('Multi-platform deployment workflow', () => {
  test('manages deployment profiles and shows sync comparison', async ({ page }) => {
    const projectId = 'project-123';
    const projectPath = '/tmp/multi-platform-project';
    const profilesState = [
      {
        id: 'p1',
        project_id: projectId,
        profile_id: 'claude_code',
        platform: 'claude_code',
        root_dir: '.claude',
        artifact_path_map: {},
        project_config_filenames: ['CLAUDE.md'],
        context_path_prefixes: ['.claude/context/'],
        supported_artifact_types: ['skill'],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    await page.route(`**/api/v1/projects/${projectId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: projectId,
          path: projectPath,
          name: 'Multi Platform Project',
          deployment_count: 2,
          last_deployment: new Date().toISOString(),
          deployments: [],
          stats: { by_type: {}, by_collection: {}, modified_count: 0 },
          deployment_profiles: profilesState,
        }),
      });
    });

    await page.route(`**/api/v1/projects/${projectId}/profiles`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(profilesState),
        });
        return;
      }
      if (route.request().method() === 'POST') {
        const payload = route.request().postDataJSON();
        profilesState.push({
          id: `p${profilesState.length + 1}`,
          project_id: projectId,
          profile_id: payload.profile_id,
          platform: payload.platform,
          root_dir: payload.root_dir,
          artifact_path_map: payload.artifact_path_map || {},
          project_config_filenames: payload.project_config_filenames || [],
          context_path_prefixes: payload.context_path_prefixes || [],
          supported_artifact_types: payload.supported_artifact_types || [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(profilesState[profilesState.length - 1]),
        });
      }
    });

    await page.route('**/api/v1/deploy', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          project_path: projectPath,
          deployments: [
            {
              artifact_name: 'api-rules',
              artifact_type: 'rule',
              from_collection: 'default',
              deployed_at: new Date().toISOString(),
              artifact_path: 'rules/api.md',
              project_path: projectPath,
              collection_sha: 'aaaa1111',
              local_modifications: false,
              sync_status: 'synced',
              deployment_profile_id: 'claude_code',
              platform: 'claude_code',
            },
            {
              artifact_name: 'api-rules',
              artifact_type: 'rule',
              from_collection: 'default',
              deployed_at: new Date().toISOString(),
              artifact_path: 'rules/api.md',
              project_path: projectPath,
              collection_sha: 'bbbb2222',
              local_modifications: false,
              sync_status: 'synced',
              deployment_profile_id: 'codex-default',
              platform: 'codex',
            },
          ],
          deployments_by_profile: {
            claude_code: [
              {
                artifact_name: 'api-rules',
                artifact_type: 'rule',
                from_collection: 'default',
                deployed_at: new Date().toISOString(),
                artifact_path: 'rules/api.md',
                project_path: projectPath,
                collection_sha: 'aaaa1111',
                local_modifications: false,
                sync_status: 'synced',
                deployment_profile_id: 'claude_code',
                platform: 'claude_code',
              },
            ],
            'codex-default': [
              {
                artifact_name: 'api-rules',
                artifact_type: 'rule',
                from_collection: 'default',
                deployed_at: new Date().toISOString(),
                artifact_path: 'rules/api.md',
                project_path: projectPath,
                collection_sha: 'bbbb2222',
                local_modifications: false,
                sync_status: 'synced',
                deployment_profile_id: 'codex-default',
                platform: 'codex',
              },
            ],
          },
          total: 2,
        }),
      });
    });

    await page.goto(`/projects/${projectId}/profiles`);
    await expect(page.getByText('Deployment Profiles')).toBeVisible();

    await page.getByLabel('Profile ID').fill('codex-default');
    await page.getByLabel('Platform').click();
    await page.getByRole('option', { name: 'Codex' }).click();
    await page.getByRole('button', { name: 'Create Profile' }).click();

    await expect(page.getByText('codex-default')).toBeVisible();

    await page.goto('/deployments');
    await expect(page.getByText('Cross-Platform Sync Comparison')).toBeVisible();
    await expect(page.getByText('rule:api-rules')).toBeVisible();
  });
});
