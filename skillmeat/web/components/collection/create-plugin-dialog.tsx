'use client';

/**
 * CreatePluginDialog — Form dialog for creating a new composite plugin artifact.
 *
 * Provides fields for plugin name, description, tags, and an interactive member
 * list backed by MemberSearchInput + MemberList.  Submits via useCreateComposite
 * and calls the onSuccess callback with the created CompositeResponse.
 *
 * Accessibility (WCAG 2.1 AA):
 * - All form fields have explicit <Label> / aria-label associations
 * - Errors are announced via aria-describedby on the relevant input
 * - Loading state disables all interactive elements
 * - Escape dismisses dialog; Enter in name/description submits when valid
 *
 * @example
 * ```tsx
 * <CreatePluginDialog
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   initialMembers={selectedArtifacts}
 *   onSuccess={(composite) => router.push(`/plugins/${composite.id}`)}
 * />
 * ```
 */

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Blocks, Loader2, PuzzleIcon } from 'lucide-react';
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
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MemberSearchInput } from '@/components/shared/member-search-input';
import { MemberList } from '@/components/shared/member-list';
import { TagEditor } from '@/components/shared/tag-editor';
import {
  useCreateComposite,
  useCollectionContext,
  useToast,
  useTags,
} from '@/hooks';
import type { Artifact } from '@/types/artifact';
import type { CompositeResponse } from '@/lib/api/composites';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Convert a human-readable plugin display name to a slug-safe composite_id.
 *
 * e.g. "My Cool Plugin" → "my-cool-plugin"
 */
function toCompositeId(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CreatePluginDialogProps {
  /** Controls dialog visibility. */
  open: boolean;
  /** Called when the dialog requests an open-state change (e.g. Escape key). */
  onOpenChange: (open: boolean) => void;
  /**
   * Optional pre-populated member list (e.g. from bulk-select flow).
   * Duplicates are silently ignored.
   */
  initialMembers?: Artifact[];
  /** Called with the server-created composite when creation succeeds. */
  onSuccess?: (composite: CompositeResponse) => void;
}

interface FormErrors {
  name?: string;
  description?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CreatePluginDialog({
  open,
  onOpenChange,
  initialMembers,
  onSuccess,
}: CreatePluginDialogProps) {
  // ------------------------------------------------------------------
  // Form state
  // ------------------------------------------------------------------
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [members, setMembers] = useState<Artifact[]>([]);
  const [errors, setErrors] = useState<FormErrors>({});

  const nameInputRef = useRef<HTMLInputElement>(null);

  // Unique IDs for ARIA error descriptions
  const nameErrorId = useId();
  const descErrorId = useId();

  // ------------------------------------------------------------------
  // Hooks
  // ------------------------------------------------------------------
  const { toast } = useToast();
  const createMutation = useCreateComposite();

  // Collection context — need collection_id for the API payload
  const { selectedCollectionId } = useCollectionContext();

  // Available tags for the tag editor autocomplete
  const { data: tagsData } = useTags();
  const availableTagNames: string[] = tagsData?.items.map((t) => t.name) ?? [];

  // ------------------------------------------------------------------
  // Sync initialMembers → local state when dialog opens
  // ------------------------------------------------------------------
  useEffect(() => {
    if (!open) return;

    if (initialMembers && initialMembers.length > 0) {
      // Deduplicate by id
      const seen = new Set<string>();
      const deduped = initialMembers.filter((a) => {
        if (seen.has(a.id)) return false;
        seen.add(a.id);
        return true;
      });
      setMembers(deduped);
    }
  }, [open, initialMembers]);

  // ------------------------------------------------------------------
  // Reset form when dialog closes
  // ------------------------------------------------------------------
  const resetForm = useCallback(() => {
    setName('');
    setDescription('');
    setTags([]);
    setMembers([]);
    setErrors({});
  }, []);

  useEffect(() => {
    if (!open) {
      resetForm();
    }
  }, [open, resetForm]);

  // Auto-focus name field when dialog opens
  useEffect(() => {
    if (open) {
      // Short delay to let dialog animation settle
      const t = setTimeout(() => nameInputRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
  }, [open]);

  // ------------------------------------------------------------------
  // Validation
  // ------------------------------------------------------------------
  const validate = (): boolean => {
    const next: FormErrors = {};

    if (!name.trim()) {
      next.name = 'Plugin name is required.';
    } else if (name.trim().length > 120) {
      next.name = 'Name must be 120 characters or fewer.';
    } else if (!/^[a-zA-Z0-9 _\-().]+$/.test(name.trim())) {
      next.name = 'Name may only contain letters, numbers, spaces, and - _ ( ) .';
    }

    if (description.length > 1000) {
      next.description = 'Description must be 1000 characters or fewer.';
    }

    setErrors(next);
    return Object.keys(next).length === 0;
  };

  // Clear individual field errors on change
  const handleNameChange = (value: string) => {
    setName(value);
    if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }));
  };

  const handleDescriptionChange = (value: string) => {
    setDescription(value);
    if (errors.description) setErrors((prev) => ({ ...prev, description: undefined }));
  };

  // ------------------------------------------------------------------
  // Member handlers
  // ------------------------------------------------------------------
  const handleMemberAdd = useCallback((artifact: Artifact) => {
    setMembers((prev) => {
      if (prev.some((m) => m.id === artifact.id)) return prev;
      return [...prev, artifact];
    });
  }, []);

  const handleMemberRemove = useCallback((artifactId: string) => {
    setMembers((prev) => prev.filter((m) => m.id !== artifactId));
  }, []);

  const handleMemberReorder = useCallback((reordered: Artifact[]) => {
    setMembers(reordered);
  }, []);

  // ------------------------------------------------------------------
  // Submit
  // ------------------------------------------------------------------
  const handleCreate = async () => {
    if (!validate()) return;

    const collectionId = selectedCollectionId ?? 'default';
    const compositeId = `composite:${toCompositeId(name)}`;

    try {
      const created = await createMutation.mutateAsync({
        composite_id: compositeId,
        collection_id: collectionId,
        composite_type: 'plugin',
        display_name: name.trim(),
        description: description.trim() || null,
        initial_members: members.map((m) => m.id),
      });

      toast({
        title: 'Plugin created',
        description: `"${name.trim()}" has been created with ${members.length} member${members.length !== 1 ? 's' : ''}.`,
      });

      onOpenChange(false);
      onSuccess?.(created);
    } catch (error) {
      // useCreateComposite already fires a toast on error via useToastNotification;
      // we only need to handle any additional inline feedback here.
      console.error('CreatePluginDialog: failed to create plugin', error);
    }
  };

  // Allow Enter key in name field to submit
  const handleNameKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCreate();
    }
  };

  // ------------------------------------------------------------------
  // Close guard — prevent accidental close during submission
  // ------------------------------------------------------------------
  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen && createMutation.isPending) return;
    onOpenChange(nextOpen);
  };

  const isPending = createMutation.isPending;

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="flex max-h-[90vh] flex-col sm:max-w-[580px]"
        aria-label="Create plugin dialog"
      >
        {/* ---------------------------------------------------------------- */}
        {/* Header                                                            */}
        {/* ---------------------------------------------------------------- */}
        <DialogHeader className="shrink-0">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
                'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'
              )}
              aria-hidden="true"
            >
              <Blocks className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle>Create Plugin</DialogTitle>
              <DialogDescription>
                Bundle artifacts into a reusable plugin package.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* ---------------------------------------------------------------- */}
        {/* Scrollable form body                                              */}
        {/* ---------------------------------------------------------------- */}
        <ScrollArea className="min-h-0 flex-1 overflow-y-auto pr-1">
          <div className="space-y-5 py-2">
            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="plugin-name">
                Name{' '}
                <span className="text-destructive" aria-hidden="true">
                  *
                </span>
              </Label>
              <Input
                id="plugin-name"
                ref={nameInputRef}
                placeholder="e.g. Canvas Design Suite"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                onKeyDown={handleNameKeyDown}
                disabled={isPending}
                aria-required="true"
                aria-describedby={errors.name ? nameErrorId : undefined}
                aria-invalid={errors.name ? 'true' : undefined}
                className={cn(errors.name && 'border-destructive focus-visible:ring-destructive')}
              />
              {errors.name && (
                <p id={nameErrorId} role="alert" className="text-sm text-destructive">
                  {errors.name}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                This becomes the plugin&apos;s identifier (slug) in the collection.
              </p>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="plugin-description">Description</Label>
              <Textarea
                id="plugin-description"
                placeholder="What does this plugin provide? What problems does it solve?"
                value={description}
                onChange={(e) => handleDescriptionChange(e.target.value)}
                disabled={isPending}
                rows={3}
                aria-describedby={errors.description ? descErrorId : undefined}
                aria-invalid={errors.description ? 'true' : undefined}
                className={cn(
                  'resize-none',
                  errors.description && 'border-destructive focus-visible:ring-destructive'
                )}
              />
              {errors.description ? (
                <p id={descErrorId} role="alert" className="text-sm text-destructive">
                  {errors.description}
                </p>
              ) : (
                <p className="text-right text-xs text-muted-foreground">
                  {description.length}
                  <span aria-hidden="true"> / 1000</span>
                  <span className="sr-only"> of 1000 characters used</span>
                </p>
              )}
            </div>

            {/* Tags */}
            <div className="space-y-2">
              <Label>Tags</Label>
              <TagEditor
                tags={tags}
                onTagsChange={setTags}
                availableTags={availableTagNames}
                disabled={isPending}
              />
              <p className="text-xs text-muted-foreground">
                Tags help with discovery and filtering.
              </p>
            </div>

            <Separator />

            {/* Members section */}
            <div className="space-y-3">
              <div>
                <Label
                  id="members-label"
                  className="mb-1.5 block text-sm font-medium"
                >
                  Members
                  {members.length > 0 && (
                    <span
                      className={cn(
                        'ml-2 inline-flex items-center justify-center rounded-full px-2 py-0.5',
                        'bg-indigo-500/10 text-xs font-semibold text-indigo-600 dark:text-indigo-400'
                      )}
                      aria-label={`${members.length} member${members.length !== 1 ? 's' : ''} added`}
                    >
                      {members.length}
                    </span>
                  )}
                </Label>
                <p className="text-xs text-muted-foreground">
                  Search your collection to add artifacts as plugin members.
                </p>
              </div>

              {/* Search picker */}
              <MemberSearchInput
                excludeIds={members.map((m) => m.id)}
                onSelect={handleMemberAdd}
                placeholder="Search artifacts to add..."
                disabled={isPending}
                inputAriaLabel="Search artifacts to add as plugin members"
              />

              {/* Sortable member list */}
              <MemberList
                members={members}
                onReorder={handleMemberReorder}
                onRemove={handleMemberRemove}
                disabled={isPending}
                className="min-h-[80px]"
                aria-labelledby="members-label"
              />
            </div>
          </div>
        </ScrollArea>

        {/* ---------------------------------------------------------------- */}
        {/* Footer                                                            */}
        {/* ---------------------------------------------------------------- */}
        <DialogFooter className="shrink-0 border-t pt-4">
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isPending}
            aria-label="Cancel plugin creation"
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={isPending || !name.trim()}
            className="bg-indigo-600 hover:bg-indigo-700 focus-visible:ring-indigo-500 dark:bg-indigo-500 dark:hover:bg-indigo-400"
            aria-label={isPending ? 'Creating plugin, please wait' : 'Create plugin'}
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                <span>Creating...</span>
              </>
            ) : (
              <>
                <PuzzleIcon className="mr-2 h-4 w-4" aria-hidden="true" />
                <span>Create Plugin</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
