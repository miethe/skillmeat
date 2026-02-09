import { render, screen } from '@testing-library/react';
import { SyncComparisonView } from '@/components/deployments/sync-comparison-view';
import { Platform } from '@/types/enums';

describe('SyncComparisonView', () => {
  it('shows out-of-sync artifacts across profiles', () => {
    render(
      <SyncComparisonView
        deploymentsByProfile={{
          claude_code: [
            {
              artifact_name: 'api-rules',
              artifact_type: 'rule',
              from_collection: 'default',
              deployed_at: '2026-02-09T00:00:00Z',
              artifact_path: 'rules/api.md',
              project_path: '/tmp/project',
              collection_sha: 'aaaa1111',
              local_modifications: false,
              sync_status: 'synced',
              deployment_profile_id: 'claude_code',
              platform: Platform.CLAUDE_CODE,
            },
          ],
          'codex-default': [
            {
              artifact_name: 'api-rules',
              artifact_type: 'rule',
              from_collection: 'default',
              deployed_at: '2026-02-09T00:00:00Z',
              artifact_path: 'rules/api.md',
              project_path: '/tmp/project',
              collection_sha: 'bbbb2222',
              local_modifications: false,
              sync_status: 'synced',
              deployment_profile_id: 'codex-default',
              platform: Platform.CODEX,
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Cross-Platform Sync Comparison')).toBeInTheDocument();
    expect(screen.getByText('rule:api-rules')).toBeInTheDocument();
    expect(screen.getByText(/claude_code: aaaa111/)).toBeInTheDocument();
    expect(screen.getByText(/codex-default: bbbb222/)).toBeInTheDocument();
  });

  it('shows in-sync message when all profiles match', () => {
    render(
      <SyncComparisonView
        deploymentsByProfile={{
          claude_code: [
            {
              artifact_name: 'api-rules',
              artifact_type: 'rule',
              from_collection: 'default',
              deployed_at: '2026-02-09T00:00:00Z',
              artifact_path: 'rules/api.md',
              project_path: '/tmp/project',
              collection_sha: 'aaaa1111',
              local_modifications: false,
              sync_status: 'synced',
              deployment_profile_id: 'claude_code',
              platform: Platform.CLAUDE_CODE,
            },
          ],
          codex: [
            {
              artifact_name: 'api-rules',
              artifact_type: 'rule',
              from_collection: 'default',
              deployed_at: '2026-02-09T00:00:00Z',
              artifact_path: 'rules/api.md',
              project_path: '/tmp/project',
              collection_sha: 'aaaa1111',
              local_modifications: false,
              sync_status: 'synced',
              deployment_profile_id: 'codex',
              platform: Platform.CODEX,
            },
          ],
        }}
      />
    );

    expect(screen.getByText('All compared profiles are in sync.')).toBeInTheDocument();
  });
});
