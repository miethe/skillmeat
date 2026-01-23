/**
 * Edit Source Modal
 *
 * Modal for editing GitHub source configuration with pre-populated fields.
 * Includes toggles for import options and tags management.
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
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useEffect, useState, useCallback, KeyboardEvent } from 'react';
import { useUpdateSource, useRescanSource, useIndexingMode } from '@/hooks';
import { Loader2, X, Plus, HelpCircle, AlertCircle } from 'lucide-react';
import type { GitHubSource, TrustLevel } from '@/types/marketplace';

interface EditSourceModalProps {
  source: GitHubSource | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const MAX_TAGS = 20;
const MAX_TAG_LENGTH = 50;
const TAG_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/;

export function EditSourceModal({ source, open, onOpenChange, onSuccess }: EditSourceModalProps) {
  const [ref, setRef] = useState('');
  const [rootHint, setRootHint] = useState('');
  const [trustLevel, setTrustLevel] = useState<TrustLevel>('basic');
  const [description, setDescription] = useState('');
  const [notes, setNotes] = useState('');
  const [enableFrontmatterDetection, setEnableFrontmatterDetection] = useState(false);
  const [importRepoDescription, setImportRepoDescription] = useState(false);
  const [importRepoReadme, setImportRepoReadme] = useState(false);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [tagError, setTagError] = useState<string | null>(null);

  // Indexing mode state
  const { indexingMode, showToggle } = useIndexingMode();
  const [indexingEnabled, setIndexingEnabled] = useState<boolean | null>(
    source?.indexing_enabled ?? (indexingMode === 'on' ? true : false)
  );

  const updateSource = useUpdateSource(source?.id || '');
  const rescanSource = useRescanSource(source?.id || '');

  // Pre-populate form when source changes
  useEffect(() => {
    if (source) {
      setRef(source.ref || 'main');
      setRootHint(source.root_hint || '');
      setTrustLevel(source.trust_level);
      setDescription(source.description || '');
      setNotes(source.notes || '');
      setEnableFrontmatterDetection(source.enable_frontmatter_detection || false);
      // Note: These are action flags, not stored state - default to false for edit
      // If user wants to re-fetch, they toggle on
      setImportRepoDescription(false);
      setImportRepoReadme(false);
      // Initialize tags from source
      setTags(source.tags || []);
      setTagInput('');
      setTagError(null);
      // Initialize indexing state from source
      setIndexingEnabled(source.indexing_enabled ?? (indexingMode === 'on' ? true : false));
    }
  }, [source, indexingMode]);

  // Tag validation: alphanumeric with hyphens/underscores, 1-50 chars
  const validateTag = useCallback(
    (tag: string): string | null => {
      if (tag.length < 1) {
        return 'Tag cannot be empty';
      }
      if (tag.length > MAX_TAG_LENGTH) {
        return `Tag must be ${MAX_TAG_LENGTH} characters or less`;
      }
      if (!TAG_PATTERN.test(tag)) {
        return 'Tag must start with alphanumeric and contain only letters, numbers, hyphens, and underscores';
      }
      if (tags.length >= MAX_TAGS) {
        return `Maximum ${MAX_TAGS} tags allowed`;
      }
      if (tags.includes(tag.toLowerCase())) {
        return 'Tag already exists';
      }
      return null;
    },
    [tags]
  );

  const addTag = useCallback(() => {
    const trimmedTag = tagInput.trim();
    if (!trimmedTag) return;

    const error = validateTag(trimmedTag);
    if (error) {
      setTagError(error);
      return;
    }

    setTags((prev) => [...prev, trimmedTag.toLowerCase()]);
    setTagInput('');
    setTagError(null);
  }, [tagInput, validateTag]);

  const removeTag = useCallback((tagToRemove: string) => {
    setTags((prev) => prev.filter((tag) => tag !== tagToRemove));
    setTagError(null);
  }, []);

  const handleTagInputKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addTag();
      } else if (e.key === 'Backspace' && !tagInput && tags.length > 0) {
        // Remove last tag on backspace when input is empty
        const lastTag = tags[tags.length - 1];
        if (lastTag) {
          removeTag(lastTag);
        }
      }
    },
    [addTag, tagInput, tags, removeTag]
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!source) return;

    // Prevent submission if there are validation errors
    if (tagError) return;

    try {
      await updateSource.mutateAsync({
        ref,
        root_hint: rootHint || undefined,
        trust_level: trustLevel,
        description: description || undefined,
        notes: notes || undefined,
        enable_frontmatter_detection: enableFrontmatterDetection,
        import_repo_description: importRepoDescription,
        import_repo_readme: importRepoReadme,
        tags: tags.length > 0 ? tags : undefined,
        indexing_enabled: showToggle ? indexingEnabled : undefined,
      });

      // Auto-trigger rescan after successful edit
      rescanSource.mutate({});

      onSuccess?.();
      onOpenChange(false);
    } catch (error) {
      // Error handled by mutation
    }
  };

  if (!source) return null;

  const isPending = updateSource.isPending || rescanSource.isPending;
  const hasValidationErrors = !!tagError;
  const canSubmit = !isPending && !hasValidationErrors;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Edit Source</DialogTitle>
            <DialogDescription>
              Edit {source.owner}/{source.repo_name} configuration. A rescan will be triggered after
              saving.
            </DialogDescription>
          </DialogHeader>

          <TooltipProvider>
            <div className="grid gap-4 py-4">
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
                <Label htmlFor="root-hint">Root Directory</Label>
                <Input
                  id="root-hint"
                  placeholder="skills/"
                  value={rootHint}
                  onChange={(e) => setRootHint(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Subdirectory to start scanning from (optional)
                </p>
              </div>

              {/* Detection Settings */}
              <div className="mt-2 border-t pt-4">
                <div className="mb-3 space-y-1">
                  <Label className="text-base font-semibold">Detection Settings</Label>
                  <p className="text-xs text-muted-foreground">
                    Configure how artifacts are detected in this source
                  </p>
                </div>

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
              </div>

              {/* Import Options */}
              <div className="mt-2 border-t pt-4">
                <div className="mb-3 space-y-1">
                  <Label className="text-base font-semibold">Import Options</Label>
                  <p className="text-xs text-muted-foreground">
                    Control what metadata to fetch from GitHub on next scan
                  </p>
                </div>

                <div className="grid gap-3">
                  <div className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="flex-1 space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Label htmlFor="import-repo-description" className="text-sm">
                          Re-fetch repository description
                        </Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs">
                            <p>
                              Repository description will be fetched from the GitHub API and stored
                              as source metadata. Enable this to update the cached description from
                              GitHub.
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Fetch the repository description from GitHub API
                      </p>
                    </div>
                    <Switch
                      id="import-repo-description"
                      checked={importRepoDescription}
                      onCheckedChange={setImportRepoDescription}
                    />
                  </div>

                  <div className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="flex-1 space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Label htmlFor="import-repo-readme" className="text-sm">
                          Re-fetch README content
                        </Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs">
                            <p>
                              README content will be fetched from GitHub and stored locally (up to
                              50KB). Enable this to update the cached README from the repository.
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Fetch README content from GitHub (up to 50KB)
                      </p>
                    </div>
                    <Switch
                      id="import-repo-readme"
                      checked={importRepoReadme}
                      onCheckedChange={setImportRepoReadme}
                    />
                  </div>
                </div>
              </div>

              {/* Search Indexing Toggle (shown when mode is "on" or "opt_in") */}
              {showToggle && (
                <div className="mt-2 border-t pt-4">
                  <div className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="flex-1 space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Label htmlFor="indexing-enabled" className="text-sm">
                          Enable artifact search indexing
                        </Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs">
                            <p>
                              Index artifacts for cross-source search. Adds approximately 850
                              bytes per artifact to enable fast full-text search across all your
                              sources.
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Enable full-text search across artifacts from this source
                      </p>
                    </div>
                    <Switch
                      id="indexing-enabled"
                      checked={indexingEnabled ?? false}
                      onCheckedChange={setIndexingEnabled}
                      aria-label="Enable artifact search indexing"
                    />
                  </div>
                </div>
              )}

              {/* Tags Management */}
              <div className="mt-2 border-t pt-4">
                <div className="mb-3 space-y-1">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-semibold">Tags</Label>
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
                  <p className="text-xs text-muted-foreground">
                    Add tags to categorize and filter this source (max {MAX_TAGS})
                  </p>
                </div>

                <div className="grid gap-2">
                  <div className="flex gap-2">
                    <Input
                      id="tag-input"
                      placeholder="Add a tag..."
                      value={tagInput}
                      onChange={(e) => {
                        setTagInput(e.target.value);
                        setTagError(null);
                      }}
                      onKeyDown={handleTagInputKeyDown}
                      disabled={tags.length >= MAX_TAGS}
                      className={`flex-1 ${tagError ? 'border-destructive' : ''}`}
                      aria-label="New tag"
                      aria-describedby={tagError ? 'tag-error' : 'tag-help'}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={addTag}
                      disabled={!tagInput.trim() || tags.length >= MAX_TAGS}
                      aria-label="Add tag"
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  {tagError && (
                    <p id="tag-error" className="flex items-center gap-1 text-xs text-destructive">
                      <AlertCircle className="h-3 w-3" />
                      {tagError}
                    </p>
                  )}

                  {tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="gap-1 pr-1">
                          {tag}
                          <button
                            type="button"
                            className="ml-1 rounded-full p-0.5 transition-colors hover:bg-black/10"
                            onClick={() => removeTag(tag)}
                            aria-label={`Remove tag ${tag}`}
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  )}
                  <p id="tag-help" className="text-xs text-muted-foreground">
                    {tags.length}/{MAX_TAGS} tags. Use letters, numbers, hyphens, and underscores.
                    Press Enter or comma to add.
                  </p>
                </div>
              </div>

              {/* Trust and Metadata */}
              <div className="mt-2 border-t pt-4">
                <div className="mb-3 space-y-1">
                  <Label className="text-base font-semibold">Trust and Metadata</Label>
                </div>

                <div className="grid gap-4">
                  <div className="grid gap-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="trust-level">Trust Level</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>
                            Trust level indicates the verification status. Untrusted for unknown
                            sources, Basic for community sources, Verified for sources you have
                            reviewed, and Official for first-party sources.
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
                        <SelectItem value="untrusted">Untrusted</SelectItem>
                        <SelectItem value="basic">Basic</SelectItem>
                        <SelectItem value="verified">Verified</SelectItem>
                        <SelectItem value="official">Official</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      placeholder="Short description for this source"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      maxLength={500}
                    />
                    <p className="text-xs text-muted-foreground">
                      {description.length}/500 characters
                    </p>
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="notes">Notes</Label>
                    <Textarea
                      id="notes"
                      placeholder="Internal notes about this source..."
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      rows={3}
                      maxLength={2000}
                    />
                    <p className="text-xs text-muted-foreground">{notes.length}/2000 characters</p>
                  </div>
                </div>
              </div>
            </div>
          </TooltipProvider>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!canSubmit}>
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
