'use client';

import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PlatformBadge } from '@/components/platform-badge';
import { Platform } from '@/types/enums';
import type { DeploymentProfile } from '@/types/deployments';

export interface ProfileSelectorProps {
  profiles?: DeploymentProfile[];
  value?: string | null;
  onValueChange: (profileId: string) => void;
  allProfiles?: boolean;
  onAllProfilesChange?: (value: boolean) => void;
  disabled?: boolean;
  label?: string;
}

const FALLBACK_PROFILES: DeploymentProfile[] = [
  {
    id: 'fallback-claude',
    project_id: '',
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
    id: 'fallback-codex',
    project_id: '',
    profile_id: 'codex',
    platform: Platform.CODEX,
    root_dir: '.codex',
    artifact_path_map: {},
    project_config_filenames: ['CODEX.md'],
    context_path_prefixes: ['.codex/context/'],
    supported_artifact_types: [],
    created_at: '',
    updated_at: '',
  },
  {
    id: 'fallback-gemini',
    project_id: '',
    profile_id: 'gemini',
    platform: Platform.GEMINI,
    root_dir: '.gemini',
    artifact_path_map: {},
    project_config_filenames: ['GEMINI.md'],
    context_path_prefixes: ['.gemini/context/'],
    supported_artifact_types: [],
    created_at: '',
    updated_at: '',
  },
];

export function ProfileSelector({
  profiles,
  value,
  onValueChange,
  allProfiles = false,
  onAllProfilesChange,
  disabled = false,
  label = 'Deployment Profile',
}: ProfileSelectorProps) {
  const effectiveProfiles = profiles && profiles.length > 0 ? profiles : FALLBACK_PROFILES;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        {onAllProfilesChange && (
          <div className="flex items-center gap-2">
            <Label htmlFor="all-profiles-toggle" className="text-xs text-muted-foreground">
              Deploy to all profiles
            </Label>
            <Switch
              id="all-profiles-toggle"
              checked={allProfiles}
              disabled={disabled}
              onCheckedChange={onAllProfilesChange}
            />
          </div>
        )}
      </div>

      <Select
        value={value || effectiveProfiles[0]?.profile_id}
        onValueChange={onValueChange}
        disabled={disabled || allProfiles}
      >
        <SelectTrigger aria-label="Select deployment profile">
          <SelectValue placeholder="Select profile" />
        </SelectTrigger>
        <SelectContent>
          {effectiveProfiles.map((profile) => (
            <SelectItem key={profile.profile_id} value={profile.profile_id}>
              <div className="flex items-center gap-2">
                <PlatformBadge platform={profile.platform} compact />
                <span>{profile.profile_id}</span>
                <span className="text-xs text-muted-foreground">({profile.root_dir})</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
