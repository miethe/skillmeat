/**
 * Add Source Modal
 *
 * Wizard for adding a new GitHub source with smart URL auto-import
 */

'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useState, useEffect, useRef } from 'react';
import { useCreateSource, useInferUrl } from '@/hooks/useMarketplaceSources';
import { Loader2, AlertCircle } from 'lucide-react';
import type { TrustLevel } from '@/types/marketplace';

interface AddSourceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function AddSourceModal({
  open,
  onOpenChange,
  onSuccess,
}: AddSourceModalProps) {
  // Quick import state
  const [quickImportUrl, setQuickImportUrl] = useState('');
  const [inferError, setInferError] = useState<string | null>(null);

  // Manual entry state
  const [repoUrl, setRepoUrl] = useState('');
  const [ref, setRef] = useState('main');
  const [rootHint, setRootHint] = useState('');

  // Shared settings
  const [trustLevel, setTrustLevel] = useState<TrustLevel>('basic');
  const [enableFrontmatterDetection, setEnableFrontmatterDetection] = useState(false);

  const createSource = useCreateSource();
  const inferUrl = useInferUrl();

  // Stable reference to mutation function to avoid infinite loop
  const inferUrlRef = useRef(inferUrl.mutateAsync);
  useEffect(() => {
    inferUrlRef.current = inferUrl.mutateAsync;
  });

  // Debounced inference - only triggers when quickImportUrl changes
  useEffect(() => {
    if (!quickImportUrl) {
      setInferError(null);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setInferError(null);
        const result = await inferUrlRef.current(quickImportUrl);

        if (result.success && result.repo_url) {
          // Auto-populate manual fields
          setRepoUrl(result.repo_url);
          setRef(result.ref || 'main');
          setRootHint(result.root_hint || '');
        } else if (result.error) {
          setInferError(result.error);
        }
      } catch (error) {
        setInferError(error instanceof Error ? error.message : 'Failed to infer URL');
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [quickImportUrl]);

  const handleQuickImport = async () => {
    if (!repoUrl) return;

    try {
      await createSource.mutateAsync({
        repo_url: repoUrl,
        ref,
        root_hint: rootHint || undefined,
        trust_level: trustLevel,
        enable_frontmatter_detection: enableFrontmatterDetection,
      });

      // Reset form
      resetForm();
      onSuccess?.();
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await createSource.mutateAsync({
        repo_url: repoUrl,
        ref,
        root_hint: rootHint || undefined,
        trust_level: trustLevel,
        enable_frontmatter_detection: enableFrontmatterDetection,
      });

      // Reset form
      resetForm();
      onSuccess?.();
    } catch (error) {
      // Error handled by mutation
    }
  };

  const resetForm = () => {
    setQuickImportUrl('');
    setRepoUrl('');
    setRef('main');
    setRootHint('');
    setTrustLevel('basic');
    setEnableFrontmatterDetection(false);
    setInferError(null);
  };

  const isValidUrl = repoUrl.match(/^https:\/\/github\.com\/[^/]+\/[^/]+$/);
  const canQuickImport = isValidUrl && !inferUrl.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add GitHub Source</DialogTitle>
          <DialogDescription>
            Add a GitHub repository to scan for Claude Code artifacts.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* Quick Import Section */}
          <div className="grid gap-3">
            <div className="space-y-1">
              <Label htmlFor="quick-import-url" className="text-base font-semibold">
                Quick Import from GitHub URL
              </Label>
              <p className="text-xs text-muted-foreground">
                Paste any GitHub URL to auto-detect repository structure
              </p>
            </div>
            <div className="grid gap-2">
              <Input
                id="quick-import-url"
                placeholder="https://github.com/owner/repo/tree/main/path"
                value={quickImportUrl}
                onChange={(e) => setQuickImportUrl(e.target.value)}
              />
              {inferUrl.isPending && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Analyzing URL...
                </div>
              )}
              {inferError && (
                <div className="flex items-center gap-2 text-xs text-destructive">
                  <AlertCircle className="h-3 w-3" />
                  {inferError}
                </div>
              )}
              <Button
                onClick={handleQuickImport}
                disabled={!canQuickImport || createSource.isPending}
              >
                {createSource.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Adding...
                  </>
                ) : (
                  'Add Source'
                )}
              </Button>
            </div>
          </div>

          {/* Or Separator */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">Or</span>
            </div>
          </div>

          {/* Manual Entry Section */}
          <form onSubmit={handleManualSubmit}>
            <div className="grid gap-4">
              <div className="space-y-1">
                <Label className="text-base font-semibold">Manual Entry</Label>
                <p className="text-xs text-muted-foreground">
                  Enter repository details manually
                </p>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="repo-url">Repository URL</Label>
                <Input
                  id="repo-url"
                  placeholder="https://github.com/owner/repo"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  required
                />
                {repoUrl && !isValidUrl && (
                  <p className="text-xs text-destructive">
                    Enter a valid GitHub URL (https://github.com/owner/repo)
                  </p>
                )}
              </div>

              <div className="grid gap-2">
                <Label htmlFor="ref">Branch / Tag</Label>
                <Input
                  id="ref"
                  placeholder="main"
                  value={ref}
                  onChange={(e) => setRef(e.target.value)}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="root-hint">Root Directory (optional)</Label>
                <Input
                  id="root-hint"
                  placeholder="skills/"
                  value={rootHint}
                  onChange={(e) => setRootHint(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Subdirectory to start scanning from
                </p>
              </div>

              {/* Shared Settings */}
              <div className="border-t pt-4 mt-2">
                <div className="space-y-1 mb-3">
                  <Label className="text-base font-semibold">Settings</Label>
                  <p className="text-xs text-muted-foreground">
                    Applied to the source
                  </p>
                </div>

                <div className="grid gap-4">
                  <div className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <Label htmlFor="frontmatter-detection" className="text-sm">
                        Enable frontmatter detection
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        Scan markdown files for artifact type hints in YAML frontmatter
                      </p>
                    </div>
                    <Switch
                      id="frontmatter-detection"
                      checked={enableFrontmatterDetection}
                      onCheckedChange={setEnableFrontmatterDetection}
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="trust-level">Trust Level</Label>
                    <Select value={trustLevel} onValueChange={(v) => setTrustLevel(v as TrustLevel)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="basic">Basic</SelectItem>
                        <SelectItem value="verified">Verified</SelectItem>
                        <SelectItem value="official">Official</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!isValidUrl || createSource.isPending}
                >
                  {createSource.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    'Add Source'
                  )}
                </Button>
              </DialogFooter>
            </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  );
}
