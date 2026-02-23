'use client';

import { useCallback, useState } from 'react';
import { Info, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Platform } from '@/types/enums';
import { PLATFORM_DEFAULTS } from '@/lib/constants/platform-defaults';
import type { PlatformDefaults } from '@/lib/constants/platform-defaults';
import type { CreateDeploymentProfileRequest } from '@/types/deployments';

// EPP-P2-03: All valid artifact type options
const ARTIFACT_TYPE_OPTIONS = ['skill', 'command', 'agent', 'mcp', 'hook', 'composite'] as const;

// EPP-P2-02: Props interface
export interface CreateProfileFormProps {
  onSubmit: (data: CreateDeploymentProfileRequest) => void;
  onCancel?: () => void;
  defaultValues?: Partial<CreateDeploymentProfileRequest>;
  contextMode: 'page' | 'dialog';
  platformLock?: Platform;
  isSubmitting?: boolean;
}

// Internal form state — artifact_path_map stored as JSON string for editing
type FormState = {
  platform: Platform;
  profile_id: string;
  root_dir: string;
  supported_artifact_types: string[];
  artifact_path_map_json: string;
  config_filenames: string;
  context_prefixes: string;
  description: string;
};

function toList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function defaultsToFormFields(defaults: PlatformDefaults): Omit<FormState, 'profile_id' | 'platform' | 'description'> {
  return {
    root_dir: defaults.root_dir,
    supported_artifact_types: defaults.supported_artifact_types,
    artifact_path_map_json: JSON.stringify(defaults.artifact_path_map, null, 2),
    config_filenames: defaults.config_filenames.join('\n'),
    context_prefixes: defaults.context_prefixes.join('\n'),
  };
}

function buildInitialState(
  defaultValues: Partial<CreateDeploymentProfileRequest> | undefined,
  platformLock: Platform | undefined
): FormState {
  const platform = platformLock ?? (defaultValues?.platform ?? Platform.CLAUDE_CODE);
  const platformKey = platform as string;
  const platformDefaults = PLATFORM_DEFAULTS[platformKey] ?? PLATFORM_DEFAULTS['other']!;

  return {
    platform,
    profile_id: defaultValues?.profile_id ?? '',
    root_dir: defaultValues?.root_dir ?? platformDefaults.root_dir,
    supported_artifact_types:
      defaultValues?.supported_artifact_types ?? platformDefaults.supported_artifact_types,
    artifact_path_map_json: JSON.stringify(
      defaultValues?.artifact_path_map ?? platformDefaults.artifact_path_map,
      null,
      2
    ),
    config_filenames: (defaultValues?.project_config_filenames ?? platformDefaults.config_filenames).join('\n'),
    context_prefixes: (defaultValues?.context_path_prefixes ?? platformDefaults.context_prefixes).join('\n'),
    description: defaultValues?.description ?? '',
  };
}

// EPP-P2-07: Field tooltip definitions
const FIELD_TOOLTIPS: Record<string, { label: string; description: string; example?: string }> = {
  platform: {
    label: 'Platform',
    description: 'The AI coding assistant platform this profile targets.',
    example: 'e.g. Claude Code, Codex, Gemini',
  },
  profile_id: {
    label: 'Profile ID',
    description: 'A unique identifier for this deployment profile within the project.',
    example: 'e.g. codex-default, claude-main',
  },
  root_dir: {
    label: 'Root Dir',
    description: 'The platform root directory relative to the project root where artifacts are deployed.',
    example: 'e.g. .claude, .codex, .gemini',
  },
  supported_artifact_types: {
    label: 'Supported Artifact Types',
    description: 'The artifact types this platform supports. Only selected types will be deployed.',
    example: 'e.g. skill, command, agent',
  },
  artifact_path_map: {
    label: 'Artifact Path Map',
    description: 'JSON map of artifact type to subdirectory name under the platform root.',
    example: '{"skill": "skills", "command": "commands"}',
  },
  config_filenames: {
    label: 'Config Filenames',
    description: 'Platform configuration files, one per line. Used for context and sync operations.',
    example: 'e.g. CLAUDE.md, AGENTS.md',
  },
  context_prefixes: {
    label: 'Context Path Prefixes',
    description: 'Path prefixes scanned for context files during sync, one per line.',
    example: 'e.g. .claude/context/, .claude/',
  },
  description: {
    label: 'Description',
    description: 'Optional human-readable description of this deployment profile.',
    example: 'e.g. Primary Claude Code profile for production project',
  },
};

function FieldTooltip({ field }: { field: string }) {
  const info = FIELD_TOOLTIPS[field];
  if (!info) return null;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label={`Info: ${info.label}`}
            className="inline-flex h-4 w-4 items-center justify-center rounded-full text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <Info className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="font-medium">{info.description}</p>
          {info.example && (
            <p className="mt-1 text-xs text-muted-foreground">{info.example}</p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function CreateProfileForm({
  onSubmit,
  onCancel,
  defaultValues,
  contextMode,
  platformLock,
  isSubmitting = false,
}: CreateProfileFormProps) {
  const [form, setForm] = useState<FormState>(() =>
    buildInitialState(defaultValues, platformLock)
  );

  // EPP-P2-04: Track which fields have been manually edited by the user
  const [touchedFields, setTouchedFields] = useState<Set<keyof FormState>>(new Set());

  const markTouched = useCallback((field: keyof FormState) => {
    setTouchedFields((prev) => new Set(prev).add(field));
  }, []);

  // EPP-P2-04: Apply platform defaults when platform changes, respecting touched fields
  const handlePlatformChange = useCallback(
    (newPlatform: string) => {
      const platform = newPlatform as Platform;
      const platformKey = newPlatform;
      const defaults = PLATFORM_DEFAULTS[platformKey] ?? PLATFORM_DEFAULTS['other']!;
      const newFields = defaultsToFormFields(defaults);

      setForm((prev) => {
        const updated: FormState = { ...prev, platform };
        // Only overwrite fields the user hasn't manually touched
        if (!touchedFields.has('root_dir')) updated.root_dir = newFields.root_dir;
        if (!touchedFields.has('supported_artifact_types'))
          updated.supported_artifact_types = newFields.supported_artifact_types;
        if (!touchedFields.has('artifact_path_map_json'))
          updated.artifact_path_map_json = newFields.artifact_path_map_json;
        if (!touchedFields.has('config_filenames')) updated.config_filenames = newFields.config_filenames;
        if (!touchedFields.has('context_prefixes')) updated.context_prefixes = newFields.context_prefixes;
        return updated;
      });
    },
    [touchedFields]
  );

  // EPP-P2-05: When artifact types change and artifact_path_map hasn't been manually edited,
  // auto-update the path map with defaults for selected types
  const handleArtifactTypesChange = useCallback(
    (types: string[]) => {
      markTouched('supported_artifact_types');
      setForm((prev) => {
        const updated = { ...prev, supported_artifact_types: types };
        // Only sync path map if not manually touched
        if (!touchedFields.has('artifact_path_map_json')) {
          const platformKey = prev.platform as string;
          const platformDefaults = PLATFORM_DEFAULTS[platformKey] ?? PLATFORM_DEFAULTS['other']!;
          const newMap: Record<string, string> = {};
          for (const type of types) {
            if (platformDefaults.artifact_path_map[type]) {
              newMap[type] = platformDefaults.artifact_path_map[type];
            }
          }
          updated.artifact_path_map_json = JSON.stringify(newMap, null, 2);
        }
        return updated;
      });
    },
    [markTouched, touchedFields]
  );

  const handleSubmit = useCallback(() => {
    let artifact_path_map: Record<string, string> = {};
    try {
      artifact_path_map = JSON.parse(form.artifact_path_map_json || '{}');
    } catch {
      artifact_path_map = {};
    }

    const payload: CreateDeploymentProfileRequest = {
      profile_id: form.profile_id.trim(),
      platform: form.platform,
      root_dir: form.root_dir.trim(),
      artifact_path_map,
      project_config_filenames: toList(form.config_filenames),
      context_path_prefixes: toList(form.context_prefixes),
      supported_artifact_types: form.supported_artifact_types,
      description: form.description.trim() || undefined,
    };

    onSubmit(payload);
  }, [form, onSubmit]);

  const isValid = form.profile_id.trim().length > 0;
  const descriptionLength = form.description.length;
  const descriptionAtLimit = descriptionLength >= 500;

  return (
    // EPP-P2-06: Field render order:
    // platform → profile_id → root_dir → supported_artifact_types →
    // artifact_path_map → config_filenames → context_prefixes → description
    <div className="grid gap-4 md:grid-cols-2">
      {/* Platform */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5">
          <Label htmlFor="cpf-platform">Platform</Label>
          <FieldTooltip field="platform" />
        </div>
        <Select
          value={form.platform}
          onValueChange={handlePlatformChange}
          disabled={!!platformLock}
        >
          <SelectTrigger id="cpf-platform">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={Platform.CLAUDE_CODE}>Claude Code</SelectItem>
            <SelectItem value={Platform.CODEX}>Codex</SelectItem>
            <SelectItem value={Platform.GEMINI}>Gemini</SelectItem>
            <SelectItem value={Platform.CURSOR}>Cursor</SelectItem>
            <SelectItem value={Platform.OTHER}>Other</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Profile ID */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5">
          <Label htmlFor="cpf-profile-id">Profile ID</Label>
          <FieldTooltip field="profile_id" />
        </div>
        <Input
          id="cpf-profile-id"
          placeholder="codex-default"
          value={form.profile_id}
          onChange={(e) =>
            setForm((prev) => ({ ...prev, profile_id: e.target.value }))
          }
        />
      </div>

      {/* Root Dir */}
      <div className="space-y-2 md:col-span-2">
        <div className="flex items-center gap-1.5">
          <Label htmlFor="cpf-root-dir">Root Dir</Label>
          <FieldTooltip field="root_dir" />
        </div>
        <Input
          id="cpf-root-dir"
          value={form.root_dir}
          onChange={(e) => {
            markTouched('root_dir');
            setForm((prev) => ({ ...prev, root_dir: e.target.value }));
          }}
        />
      </div>

      {/* Supported Artifact Types — EPP-P2-03: checkbox group */}
      <div className="space-y-2 md:col-span-2">
        <div className="flex items-center gap-1.5">
          <Label>Supported Artifact Types</Label>
          <FieldTooltip field="supported_artifact_types" />
        </div>
        <div
          role="group"
          aria-label="Supported artifact types"
          className="flex flex-wrap gap-x-6 gap-y-2 pt-1"
        >
          {ARTIFACT_TYPE_OPTIONS.map((type) => {
            const checked = form.supported_artifact_types.includes(type);
            const checkboxId = `cpf-type-${type}`;
            return (
              <div key={type} className="flex items-center gap-2">
                <Checkbox
                  id={checkboxId}
                  checked={checked}
                  onCheckedChange={(checkedState) => {
                    const newTypes = checkedState
                      ? [...form.supported_artifact_types, type]
                      : form.supported_artifact_types.filter((t) => t !== type);
                    handleArtifactTypesChange(newTypes);
                  }}
                />
                <Label
                  htmlFor={checkboxId}
                  className="cursor-pointer font-normal capitalize"
                >
                  {type}
                </Label>
              </div>
            );
          })}
        </div>
      </div>

      {/* Artifact Path Map */}
      <div className="space-y-2 md:col-span-2">
        <div className="flex items-center gap-1.5">
          <Label htmlFor="cpf-artifact-map">Artifact Path Map (JSON)</Label>
          <FieldTooltip field="artifact_path_map" />
        </div>
        <Textarea
          id="cpf-artifact-map"
          rows={5}
          value={form.artifact_path_map_json}
          onChange={(e) => {
            markTouched('artifact_path_map_json');
            setForm((prev) => ({ ...prev, artifact_path_map_json: e.target.value }));
          }}
          className="font-mono text-sm"
        />
      </div>

      {/* Config Filenames */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5">
          <Label htmlFor="cpf-config-filenames">Config Filenames</Label>
          <FieldTooltip field="config_filenames" />
        </div>
        <Textarea
          id="cpf-config-filenames"
          rows={3}
          placeholder="One per line"
          value={form.config_filenames}
          onChange={(e) => {
            markTouched('config_filenames');
            setForm((prev) => ({ ...prev, config_filenames: e.target.value }));
          }}
        />
      </div>

      {/* Context Prefixes */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5">
          <Label htmlFor="cpf-context-prefixes">Context Path Prefixes</Label>
          <FieldTooltip field="context_prefixes" />
        </div>
        <Textarea
          id="cpf-context-prefixes"
          rows={3}
          placeholder="One per line"
          value={form.context_prefixes}
          onChange={(e) => {
            markTouched('context_prefixes');
            setForm((prev) => ({ ...prev, context_prefixes: e.target.value }));
          }}
        />
      </div>

      {/* EPP-P2-08: Description textarea */}
      <div className="space-y-2 md:col-span-2">
        <div className="flex items-center gap-1.5">
          <Label htmlFor="cpf-description">Description</Label>
          <FieldTooltip field="description" />
          <span className="ml-auto text-xs text-muted-foreground">
            <span className={descriptionAtLimit ? 'text-destructive' : ''}>
              {descriptionLength}
            </span>
            /500
          </span>
        </div>
        <Textarea
          id="cpf-description"
          rows={3}
          placeholder="Optional description of this deployment profile"
          maxLength={500}
          value={form.description}
          onChange={(e) =>
            setForm((prev) => ({ ...prev, description: e.target.value }))
          }
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 md:col-span-2">
        <Button onClick={handleSubmit} disabled={isSubmitting || !isValid}>
          <Plus className="mr-2 h-4 w-4" />
          Create Profile
        </Button>
        {contextMode === 'page' && onCancel && (
          <Button variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        )}
      </div>
    </div>
  );
}
