'use client';

import * as React from 'react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, RotateCcw, Save } from 'lucide-react';
import {
  usePlatformDefaults,
  useUpdatePlatformDefault,
  useResetPlatformDefault,
  useToast,
} from '@/hooks';

// =============================================================================
// Constants
// =============================================================================

const PLATFORM_NAMES: Record<string, string> = {
  claude_code: 'Claude Code',
  codex: 'Codex',
  gemini: 'Gemini',
  cursor: 'Cursor',
  other: 'Other',
};

const PLATFORM_ORDER = ['claude_code', 'codex', 'gemini', 'cursor', 'other'];

function formatPlatformName(platform: string): string {
  return PLATFORM_NAMES[platform] || platform;
}

// =============================================================================
// Form State
// =============================================================================

interface FormState {
  root_dir: string;
  artifact_path_map_json: string;
  config_filenames: string;
  supported_artifact_types: string;
  context_prefixes: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * PlatformDefaultsSettings - Edit per-platform default configuration
 *
 * Displays an accordion with one section per platform. Each section contains
 * form fields for root directory, artifact path map, config filenames,
 * supported artifact types, and context prefixes. Users can save changes
 * or reset to built-in defaults.
 */
export function PlatformDefaultsSettings() {
  const { toast } = useToast();
  const { data, isLoading } = usePlatformDefaults();
  const updateDefault = useUpdatePlatformDefault();
  const resetDefault = useResetPlatformDefault();

  const [editingPlatform, setEditingPlatform] = React.useState<string | null>(null);
  const [formState, setFormState] = React.useState<FormState | null>(null);

  // Populate form state when accordion opens to a platform
  const handleAccordionChange = React.useCallback(
    (value: string) => {
      if (!value) {
        setEditingPlatform(null);
        setFormState(null);
        return;
      }

      setEditingPlatform(value);

      const platformData = data?.defaults?.[value];
      if (platformData) {
        setFormState({
          root_dir: platformData.root_dir,
          artifact_path_map_json: JSON.stringify(platformData.artifact_path_map, null, 2),
          config_filenames: platformData.config_filenames.join('\n'),
          supported_artifact_types: platformData.supported_artifact_types.join(', '),
          context_prefixes: platformData.context_prefixes.join('\n'),
        });
      }
    },
    [data]
  );

  // Save handler
  const handleSave = async () => {
    if (!editingPlatform || !formState) return;

    try {
      const payload = {
        root_dir: formState.root_dir.trim(),
        artifact_path_map: JSON.parse(formState.artifact_path_map_json || '{}'),
        config_filenames: formState.config_filenames
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
        supported_artifact_types: formState.supported_artifact_types
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        context_prefixes: formState.context_prefixes
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
      };

      await updateDefault.mutateAsync({ platform: editingPlatform, data: payload });

      toast({
        title: 'Defaults saved',
        description: `Updated defaults for ${formatPlatformName(editingPlatform)}`,
      });
    } catch (error) {
      toast({
        title: 'Failed to save defaults',
        description: error instanceof Error ? error.message : 'Save failed',
        variant: 'destructive',
      });
    }
  };

  // Reset handler
  const handleReset = async () => {
    if (!editingPlatform) return;

    try {
      const result = await resetDefault.mutateAsync(editingPlatform);

      // Update local form state with the reset values
      setFormState({
        root_dir: result.root_dir,
        artifact_path_map_json: JSON.stringify(result.artifact_path_map, null, 2),
        config_filenames: result.config_filenames.join('\n'),
        supported_artifact_types: result.supported_artifact_types.join(', '),
        context_prefixes: result.context_prefixes.join('\n'),
      });

      toast({
        title: 'Defaults reset',
        description: `Reset ${formatPlatformName(editingPlatform)} to built-in defaults`,
      });
    } catch (error) {
      toast({
        title: 'Failed to reset',
        description: error instanceof Error ? error.message : 'Reset failed',
        variant: 'destructive',
      });
    }
  };

  // Update a single form field
  const updateField = (field: keyof FormState, value: string) => {
    setFormState((prev) => (prev ? { ...prev, [field]: value } : null));
  };

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Platform Defaults</CardTitle>
          <CardDescription>Loading platform defaults...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Platform Defaults</CardTitle>
        <CardDescription>
          Customize default values for directory structures, artifact types, and configuration
          filenames across different AI coding platforms.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Accordion
          type="single"
          collapsible
          value={editingPlatform ?? ''}
          onValueChange={handleAccordionChange}
        >
          {PLATFORM_ORDER.map((platform) => (
            <AccordionItem key={platform} value={platform}>
              <AccordionTrigger>{formatPlatformName(platform)}</AccordionTrigger>
              <AccordionContent>
                {editingPlatform === platform && formState && (
                  <div className="space-y-4">
                    {/* Root Directory */}
                    <div className="space-y-2">
                      <Label htmlFor={`${platform}-root-dir`}>Root Directory</Label>
                      <Input
                        id={`${platform}-root-dir`}
                        value={formState.root_dir}
                        onChange={(e) => updateField('root_dir', e.target.value)}
                        placeholder=".claude"
                      />
                    </div>

                    {/* Artifact Path Map */}
                    <div className="space-y-2">
                      <Label htmlFor={`${platform}-artifact-path-map`}>
                        Artifact Path Map (JSON)
                      </Label>
                      <Textarea
                        id={`${platform}-artifact-path-map`}
                        value={formState.artifact_path_map_json}
                        onChange={(e) => updateField('artifact_path_map_json', e.target.value)}
                        rows={5}
                        className="font-mono text-sm"
                        placeholder='{"skill": "skills", "command": "commands"}'
                      />
                    </div>

                    {/* Config Filenames */}
                    <div className="space-y-2">
                      <Label htmlFor={`${platform}-config-filenames`}>
                        Config Filenames (one per line)
                      </Label>
                      <Textarea
                        id={`${platform}-config-filenames`}
                        value={formState.config_filenames}
                        onChange={(e) => updateField('config_filenames', e.target.value)}
                        rows={3}
                        placeholder="CLAUDE.md"
                      />
                    </div>

                    {/* Supported Artifact Types */}
                    <div className="space-y-2">
                      <Label htmlFor={`${platform}-artifact-types`}>
                        Supported Artifact Types (comma-separated)
                      </Label>
                      <Input
                        id={`${platform}-artifact-types`}
                        value={formState.supported_artifact_types}
                        onChange={(e) => updateField('supported_artifact_types', e.target.value)}
                        placeholder="skill, command, agent"
                      />
                    </div>

                    {/* Context Prefixes */}
                    <div className="space-y-2">
                      <Label htmlFor={`${platform}-context-prefixes`}>
                        Context Prefixes (one per line)
                      </Label>
                      <Textarea
                        id={`${platform}-context-prefixes`}
                        value={formState.context_prefixes}
                        onChange={(e) => updateField('context_prefixes', e.target.value)}
                        rows={3}
                        placeholder=".claude/context/"
                      />
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 pt-2">
                      <Button
                        onClick={handleSave}
                        disabled={updateDefault.isPending}
                        size="sm"
                      >
                        {updateDefault.isPending ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="mr-2 h-4 w-4" />
                            Save Changes
                          </>
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={handleReset}
                        disabled={resetDefault.isPending}
                        size="sm"
                      >
                        {resetDefault.isPending ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Resetting...
                          </>
                        ) : (
                          <>
                            <RotateCcw className="mr-2 h-4 w-4" />
                            Reset to Defaults
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </CardContent>
    </Card>
  );
}
