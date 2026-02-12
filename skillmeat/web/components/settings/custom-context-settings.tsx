'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Loader2, Save } from 'lucide-react';
import { useCustomContextConfig, useUpdateCustomContextConfig, useToast } from '@/hooks';

const ALL_PLATFORMS = ['claude_code', 'codex', 'gemini', 'cursor', 'other'] as const;

const PLATFORM_LABELS: Record<string, string> = {
  claude_code: 'Claude Code',
  codex: 'Codex',
  gemini: 'Gemini',
  cursor: 'Cursor',
  other: 'Other',
};

export function CustomContextSettings() {
  const { toast } = useToast();
  const { data: configData, isLoading } = useCustomContextConfig();
  const updateConfig = useUpdateCustomContextConfig();

  const [enabled, setEnabled] = useState(false);
  const [prefixes, setPrefixes] = useState('');
  const [mode, setMode] = useState<'override' | 'addendum'>('addendum');
  const [platforms, setPlatforms] = useState<string[]>([]);

  useEffect(() => {
    if (configData) {
      setEnabled(configData.enabled);
      setPrefixes(configData.prefixes.join('\n'));
      setMode(configData.mode as 'override' | 'addendum');
      setPlatforms(configData.platforms);
    }
  }, [configData]);

  const handleTogglePlatform = (platform: string) => {
    setPlatforms((prev) =>
      prev.includes(platform) ? prev.filter((p) => p !== platform) : [...prev, platform]
    );
  };

  const handleSelectAll = () => {
    if (platforms.length === ALL_PLATFORMS.length) {
      setPlatforms([]);
    } else {
      setPlatforms([...ALL_PLATFORMS]);
    }
  };

  const selectAllChecked: boolean | 'indeterminate' =
    platforms.length === ALL_PLATFORMS.length
      ? true
      : platforms.length > 0
        ? 'indeterminate'
        : false;

  const handleSave = async () => {
    try {
      await updateConfig.mutateAsync({
        enabled,
        prefixes: prefixes
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
        mode,
        platforms,
      });
      toast({
        title: 'Configuration saved',
        description: 'Custom context settings updated successfully',
      });
    } catch (error) {
      toast({
        title: 'Failed to save',
        description: error instanceof Error ? error.message : 'Save failed',
        variant: 'destructive',
      });
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Custom Context Prefixes</CardTitle>
          <CardDescription>Loading configuration...</CardDescription>
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
        <CardTitle>Custom Context Prefixes</CardTitle>
        <CardDescription>
          Configure custom context directory prefixes for platform-specific artifact resolution
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center space-x-3">
          <Switch
            id="custom-context-enabled"
            checked={enabled}
            onCheckedChange={setEnabled}
          />
          <Label htmlFor="custom-context-enabled">Enable custom context prefixes</Label>
        </div>

        {enabled && (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="custom-prefixes">Custom Prefixes</Label>
              <Textarea
                id="custom-prefixes"
                rows={4}
                placeholder={'docs/context/\nnotes/'}
                value={prefixes}
                onChange={(e) => setPrefixes(e.target.value)}
              />
              <p className="text-sm text-muted-foreground">
                Enter one prefix per line. These directory paths will be used for context resolution.
              </p>
            </div>

            <div className="space-y-3">
              <Label>Application Mode</Label>
              <RadioGroup value={mode} onValueChange={(v) => setMode(v as 'override' | 'addendum')}>
                <div className="flex items-start space-x-3">
                  <RadioGroupItem value="override" id="mode-override" />
                  <div className="space-y-0.5">
                    <Label htmlFor="mode-override" className="font-normal">
                      Override
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Replace platform context prefixes with custom ones
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <RadioGroupItem value="addendum" id="mode-addendum" />
                  <div className="space-y-0.5">
                    <Label htmlFor="mode-addendum" className="font-normal">
                      Addendum
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Append custom prefixes after platform defaults
                    </p>
                  </div>
                </div>
              </RadioGroup>
            </div>

            <div className="space-y-3">
              <Label>Apply to Platforms</Label>
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="select-all-platforms"
                    checked={selectAllChecked}
                    onCheckedChange={handleSelectAll}
                  />
                  <Label htmlFor="select-all-platforms" className="font-normal">
                    Select All
                  </Label>
                </div>
                <div className="ml-6 space-y-2">
                  {ALL_PLATFORMS.map((platform) => (
                    <div key={platform} className="flex items-center space-x-2">
                      <Checkbox
                        id={`platform-${platform}`}
                        checked={platforms.includes(platform)}
                        onCheckedChange={() => handleTogglePlatform(platform)}
                      />
                      <Label htmlFor={`platform-${platform}`} className="font-normal">
                        {PLATFORM_LABELS[platform]}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <Button onClick={handleSave} disabled={updateConfig.isPending}>
              {updateConfig.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Configuration
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
