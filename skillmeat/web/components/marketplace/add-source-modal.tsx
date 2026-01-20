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
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useState, useEffect, useRef, useCallback, KeyboardEvent } from 'react';
import { useCreateSource, useInferUrl } from '@/hooks';
import { Loader2, AlertCircle, X, HelpCircle } from 'lucide-react';
import type { TrustLevel } from '@/types/marketplace';

interface AddSourceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const MAX_TAGS = 20;
const MAX_TAG_LENGTH = 50;
const TAG_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/;

function validateTag(tag: string): { valid: boolean; error?: string } {
  if (tag.length < 1) {
    return { valid: false, error: 'Tag cannot be empty' };
  }
  if (tag.length > MAX_TAG_LENGTH) {
    return { valid: false, error: `Tag must be ${MAX_TAG_LENGTH} characters or less` };
  }
  if (!TAG_PATTERN.test(tag)) {
    return {
      valid: false,
      error:
        'Tag must start with alphanumeric and contain only letters, numbers, hyphens, and underscores',
    };
  }
  return { valid: true };
}

export function AddSourceModal({ open, onOpenChange, onSuccess }: AddSourceModalProps) {
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
  const [importRepoDescription, setImportRepoDescription] = useState(false);
  const [importRepoReadme, setImportRepoReadme] = useState(false);

  // Tags state
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [tagError, setTagError] = useState<string | null>(null);

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

  const addTag = useCallback(
    (value: string) => {
      const trimmedTag = value.trim().toLowerCase();
      if (!trimmedTag) {
        setTagInput('');
        return;
      }

      // Check max tags limit
      if (tags.length >= MAX_TAGS) {
        setTagError(`Maximum ${MAX_TAGS} tags allowed`);
        return;
      }

      // Validate tag format
      const validation = validateTag(trimmedTag);
      if (!validation.valid) {
        setTagError(validation.error || 'Invalid tag');
        return;
      }

      // Check for duplicates
      if (tags.includes(trimmedTag)) {
        setTagError('Tag already added');
        setTagInput('');
        return;
      }

      setTags([...tags, trimmedTag]);
      setTagInput('');
      setTagError(null);
    },
    [tags]
  );

  const removeTag = useCallback(
    (tagToRemove: string) => {
      setTags(tags.filter((tag) => tag !== tagToRemove));
      setTagError(null);
    },
    [tags]
  );

  const handleTagInputKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addTag(tagInput);
      } else if (e.key === 'Backspace' && !tagInput && tags.length > 0) {
        // Remove last tag when backspace is pressed on empty input
        const lastTag = tags[tags.length - 1];
        if (lastTag) {
          removeTag(lastTag);
        }
      }
    },
    [tagInput, tags, addTag, removeTag]
  );

  const handleTagInputBlur = useCallback(() => {
    if (tagInput.trim()) {
      addTag(tagInput);
    }
  }, [tagInput, addTag]);

  const handleQuickImport = async () => {
    if (!repoUrl) return;

    try {
      await createSource.mutateAsync({
        repo_url: repoUrl,
        ref,
        root_hint: rootHint || undefined,
        trust_level: trustLevel,
        enable_frontmatter_detection: enableFrontmatterDetection,
        import_repo_description: importRepoDescription,
        import_repo_readme: importRepoReadme,
        tags: tags.length > 0 ? tags : undefined,
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
        import_repo_description: importRepoDescription,
        import_repo_readme: importRepoReadme,
        tags: tags.length > 0 ? tags : undefined,
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
    setImportRepoDescription(false);
    setImportRepoReadme(false);
    setTags([]);
    setTagInput('');
    setTagError(null);
    setInferError(null);
  };

  const isValidUrl = repoUrl.match(/^https:\/\/github\.com\/[^/]+\/[^/]+$/);
  const canQuickImport = isValidUrl && !inferUrl.isPending;
  const hasValidationErrors = !!tagError;
  const canSubmit = isValidUrl && !createSource.isPending && !hasValidationErrors;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add GitHub Source</DialogTitle>
          <DialogDescription>
            Add a GitHub repository to scan for Claude Code artifacts.
          </DialogDescription>
        </DialogHeader>

        <TooltipProvider>
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
                  disabled={!canQuickImport || createSource.isPending || hasValidationErrors}
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
                  <p className="text-xs text-muted-foreground">Enter repository details manually</p>
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
                <div className="mt-2 border-t pt-4">
                  <div className="mb-3 space-y-1">
                    <Label className="text-base font-semibold">Settings</Label>
                    <p className="text-xs text-muted-foreground">Applied to the source</p>
                  </div>

                  <div className="grid gap-4">
                    {/* Frontmatter Detection Toggle */}
                    <div className="flex flex-row items-center justify-between rounded-lg border p-4">
                      <div className="flex-1 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <Label htmlFor="frontmatter-detection" className="text-sm">
                            Enable frontmatter detection
                          </Label>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent side="top" className="max-w-xs">
                              <p>
                                When enabled, markdown files will be scanned for YAML frontmatter
                                containing artifact type hints (e.g., type: skill). This can improve
                                detection accuracy for well-structured repositories.
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
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

                    {/* Import Repository Description Toggle */}
                    <div className="flex flex-row items-center justify-between rounded-lg border p-4">
                      <div className="flex-1 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <Label htmlFor="import-repo-description" className="text-sm">
                            Include repository description
                          </Label>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent side="top" className="max-w-xs">
                              <p>
                                Repository description will be fetched from the GitHub API and
                                stored as source metadata. Useful for understanding the purpose of
                                the source at a glance.
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Fetch and store the GitHub repository description
                        </p>
                      </div>
                      <Switch
                        id="import-repo-description"
                        checked={importRepoDescription}
                        onCheckedChange={setImportRepoDescription}
                      />
                    </div>

                    {/* Import Repository README Toggle */}
                    <div className="flex flex-row items-center justify-between rounded-lg border p-4">
                      <div className="flex-1 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <Label htmlFor="import-repo-readme" className="text-sm">
                            Include repository README
                          </Label>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent side="top" className="max-w-xs">
                              <p>
                                README content will be fetched from GitHub and stored locally (up to
                                50KB). This provides documentation context for the source without
                                needing to visit GitHub.
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Fetch and store the repository README content (up to 50KB)
                        </p>
                      </div>
                      <Switch
                        id="import-repo-readme"
                        checked={importRepoReadme}
                        onCheckedChange={setImportRepoReadme}
                      />
                    </div>

                    {/* Tags Input */}
                    <div className="grid gap-2">
                      <div className="flex items-center gap-2">
                        <Label htmlFor="tags">Tags</Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs">
                            <p>
                              Tags help organize sources for discovery and filtering. Add tags like
                              "official", "testing", or "work" to group related sources together.
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <div
                        className={`flex min-h-[42px] flex-wrap gap-2 rounded-lg border p-2 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 ${tagError ? 'border-destructive' : ''}`}
                      >
                        {tags.map((tag) => (
                          <Badge
                            key={tag}
                            variant="secondary"
                            className="flex items-center gap-1 pr-1"
                          >
                            {tag}
                            <button
                              type="button"
                              onClick={() => removeTag(tag)}
                              className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20"
                              aria-label={`Remove tag ${tag}`}
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </Badge>
                        ))}
                        <Input
                          id="tags"
                          value={tagInput}
                          onChange={(e) => {
                            setTagInput(e.target.value);
                            setTagError(null);
                          }}
                          onKeyDown={handleTagInputKeyDown}
                          onBlur={handleTagInputBlur}
                          placeholder={
                            tags.length === 0 ? 'Type and press Enter or comma to add' : ''
                          }
                          className="h-auto min-w-[120px] flex-1 border-0 p-0 focus-visible:ring-0 focus-visible:ring-offset-0"
                          disabled={tags.length >= MAX_TAGS}
                          aria-describedby={tagError ? 'tag-error' : 'tag-help'}
                        />
                      </div>
                      {tagError && (
                        <p
                          id="tag-error"
                          className="flex items-center gap-1 text-xs text-destructive"
                        >
                          <AlertCircle className="h-3 w-3" />
                          {tagError}
                        </p>
                      )}
                      <p id="tag-help" className="text-xs text-muted-foreground">
                        {tags.length}/{MAX_TAGS} tags. Use letters, numbers, hyphens, and
                        underscores. Press Enter or comma to add.
                      </p>
                    </div>

                    {/* Trust Level */}
                    <div className="grid gap-2">
                      <div className="flex items-center gap-2">
                        <Label htmlFor="trust-level">Trust Level</Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs">
                            <p>
                              Trust level indicates the verification status of the source. Basic is
                              for unverified sources, Verified for sources you have reviewed, and
                              Official for first-party or well-known sources.
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Select
                        value={trustLevel}
                        onValueChange={(v) => setTrustLevel(v as TrustLevel)}
                      >
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
                  <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={!canSubmit}>
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
        </TooltipProvider>
      </DialogContent>
    </Dialog>
  );
}
