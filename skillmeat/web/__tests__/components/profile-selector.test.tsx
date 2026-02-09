import { fireEvent, render, screen } from '@testing-library/react';
import { ProfileSelector } from '@/components/profile-selector';
import { Platform } from '@/types/enums';
import type { DeploymentProfile } from '@/types/deployments';

const profiles: DeploymentProfile[] = [
  {
    id: '1',
    project_id: 'proj-1',
    profile_id: 'claude_code',
    platform: Platform.CLAUDE_CODE,
    root_dir: '.claude',
    artifact_path_map: {},
    project_config_filenames: ['CLAUDE.md'],
    context_path_prefixes: ['.claude/context/'],
    supported_artifact_types: [],
    created_at: '',
    updated_at: '',
  },
  {
    id: '2',
    project_id: 'proj-1',
    profile_id: 'codex-default',
    platform: Platform.CODEX,
    root_dir: '.codex',
    artifact_path_map: {},
    project_config_filenames: ['CODEX.md'],
    context_path_prefixes: ['.codex/context/'],
    supported_artifact_types: [],
    created_at: '',
    updated_at: '',
  },
];

describe('ProfileSelector', () => {
  it('renders provided profile options and all-profiles toggle', () => {
    const onAllProfilesChange = jest.fn();
    render(
      <ProfileSelector
        profiles={profiles}
        value="claude_code"
        onValueChange={jest.fn()}
        allProfiles={false}
        onAllProfilesChange={onAllProfilesChange}
      />
    );

    expect(screen.getByText('Deployment Profile')).toBeInTheDocument();
    expect(screen.getByRole('switch')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('switch'));
    expect(onAllProfilesChange).toHaveBeenCalled();
  });

  it('calls onValueChange when a profile option is selected', () => {
    const onValueChange = jest.fn();
    render(
      <ProfileSelector
        profiles={profiles}
        value="claude_code"
        onValueChange={onValueChange}
        allProfiles={false}
      />
    );

    fireEvent.click(screen.getByLabelText('Select deployment profile'));
    const codexLabels = screen.getAllByText('codex-default');
    const codexOption = codexLabels.find((node) => node.closest('[role="option"]'));
    expect(codexOption).toBeTruthy();
    fireEvent.click(codexOption!);

    expect(onValueChange).toHaveBeenCalledWith('codex-default');
  });
});
