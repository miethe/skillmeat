import { generateDeployCommandWithOptions } from '@/lib/cli-commands';

describe('cli-commands profile flags', () => {
  it('adds --profile when profileId is provided', () => {
    const command = generateDeployCommandWithOptions('api-rules', { profileId: 'codex-default' });
    expect(command).toBe('skillmeat deploy api-rules --profile codex-default');
  });

  it('adds --all-profiles when allProfiles is true', () => {
    const command = generateDeployCommandWithOptions('api-rules', { allProfiles: true });
    expect(command).toBe('skillmeat deploy api-rules --all-profiles');
  });
});
