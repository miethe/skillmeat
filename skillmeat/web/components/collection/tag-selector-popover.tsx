/**
 * TagSelectorPopover Component
 *
 * A popover for managing tags on an artifact. Shows existing tags as colored
 * badges, allows toggling tags on/off, searching/filtering, and creating
 * new tags inline.
 *
 * Uses the same deterministic color hashing as tag-badge.tsx for consistency.
 */

'use client';

import * as React from 'react';
import { Check, Loader2, Plus } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { cn } from '@/lib/utils';
import {
  useTags,
  useArtifactTags,
  useAddTagToArtifact,
  useRemoveTagFromArtifact,
  useCreateTag,
} from '@/hooks';
import type { Tag } from '@/lib/api/tags';

// ============================================================================
// Types
// ============================================================================

export interface TagSelectorPopoverProps {
  /** Artifact ID to manage tags for */
  artifactId: string;
  /** The trigger element (typically the '+' button) */
  trigger: React.ReactNode;
  /** Optional callback after tags are changed */
  onTagsChanged?: () => void;
}

// ============================================================================
// Color Utilities (mirrored from tag-badge.tsx for consistency)
// ============================================================================

const TAG_COLORS = [
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#d946ef', // Fuchsia
  '#ec4899', // Pink
  '#f43f5e', // Rose
  '#ef4444', // Red
  '#f97316', // Orange
  '#eab308', // Yellow
  '#84cc16', // Lime
  '#22c55e', // Green
  '#14b8a6', // Teal
  '#06b6d4', // Cyan
  '#0ea5e9', // Sky
  '#3b82f6', // Blue
] as const;

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

function getTagColor(tag: string): string {
  const hash = hashString(tag.toLowerCase());
  return TAG_COLORS[hash % TAG_COLORS.length] ?? '#6366f1';
}

// ============================================================================
// Sub-components
// ============================================================================

interface TagItemProps {
  tag: Tag;
  isApplied: boolean;
  isPending: boolean;
  onToggle: (tag: Tag) => void;
}

function TagItem({ tag, isApplied, isPending, onToggle }: TagItemProps) {
  const color = getTagColor(tag.name);

  return (
    <CommandItem
      value={tag.name}
      onSelect={() => onToggle(tag)}
      className="flex items-center gap-2 px-2 py-1.5"
      disabled={isPending}
    >
      <div
        className={cn(
          'flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-sm border',
          isApplied
            ? 'border-primary bg-primary text-primary-foreground'
            : 'border-muted-foreground/30'
        )}
      >
        {isApplied && <Check className="h-3 w-3" />}
      </div>
      <Badge
        colorStyle={color}
        className="text-xs"
      >
        {tag.name}
      </Badge>
      {isPending && (
        <Loader2 className="ml-auto h-3 w-3 animate-spin text-muted-foreground" />
      )}
    </CommandItem>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * TagSelectorPopover - Popover for adding/removing tags from an artifact
 *
 * Shows all available tags with checkmarks for applied ones.
 * Includes search filtering and inline tag creation.
 *
 * @example
 * ```tsx
 * <TagSelectorPopover
 *   artifactId="skill:canvas-design"
 *   trigger={<Button size="icon" variant="ghost"><Plus /></Button>}
 *   onTagsChanged={() => console.log('tags updated')}
 * />
 * ```
 */
export function TagSelectorPopover({
  artifactId,
  trigger,
  onTagsChanged,
}: TagSelectorPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [pendingTagIds, setPendingTagIds] = React.useState<Set<string>>(new Set());

  // Data hooks
  const { data: allTagsResponse, isLoading: isLoadingAll } = useTags(100);
  const { data: artifactTags, isLoading: isLoadingArtifact } = useArtifactTags(
    open ? artifactId : undefined
  );

  // Mutation hooks
  const addTag = useAddTagToArtifact();
  const removeTag = useRemoveTagFromArtifact();
  const createTagMutation = useCreateTag();

  const allTags = React.useMemo(() => allTagsResponse?.items ?? [], [allTagsResponse?.items]);
  const appliedTagIds = React.useMemo(
    () => new Set((artifactTags ?? []).map((t) => t.id)),
    [artifactTags]
  );

  // Filter tags by search
  const filteredTags = React.useMemo(() => {
    if (!search.trim()) return allTags;
    const query = search.toLowerCase().trim();
    return allTags.filter((tag) => tag.name.toLowerCase().includes(query));
  }, [allTags, search]);

  // Check if search term matches any existing tag exactly
  const exactMatch = React.useMemo(() => {
    if (!search.trim()) return true;
    const query = search.toLowerCase().trim();
    return allTags.some((tag) => tag.name.toLowerCase() === query);
  }, [allTags, search]);

  const isLoading = isLoadingAll || isLoadingArtifact;

  // Toggle a tag on/off for this artifact
  const handleToggle = React.useCallback(
    async (tag: Tag) => {
      const isCurrentlyApplied = appliedTagIds.has(tag.id);
      setPendingTagIds((prev) => new Set(prev).add(tag.id));

      try {
        if (isCurrentlyApplied) {
          await removeTag.mutateAsync({ artifactId, tagId: tag.id });
        } else {
          await addTag.mutateAsync({ artifactId, tagId: tag.id });
        }
        onTagsChanged?.();
      } catch (err) {
        console.error('Failed to toggle tag:', err);
      } finally {
        setPendingTagIds((prev) => {
          const next = new Set(prev);
          next.delete(tag.id);
          return next;
        });
      }
    },
    [artifactId, appliedTagIds, addTag, removeTag, onTagsChanged]
  );

  // Create a new tag and apply it
  const handleCreate = React.useCallback(async () => {
    const name = search.trim();
    if (!name) return;

    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');

    try {
      const newTag = await createTagMutation.mutateAsync({
        name,
        slug,
        color: getTagColor(name),
      });
      // Also add it to the artifact
      await addTag.mutateAsync({ artifactId, tagId: newTag.id });
      setSearch('');
      onTagsChanged?.();
    } catch (err) {
      console.error('Failed to create tag:', err);
    }
  }, [search, artifactId, createTagMutation, addTag, onTagsChanged]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild onClick={(e) => e.stopPropagation()}>
        {trigger}
      </PopoverTrigger>
      <PopoverContent
        className="w-64 p-0"
        align="start"
        side="bottom"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search or create tags..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList className="max-h-56">
            {isLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">Loading tags...</span>
              </div>
            ) : (
              <>
                {filteredTags.length === 0 && !search.trim() && (
                  <CommandEmpty>No tags available.</CommandEmpty>
                )}
                {filteredTags.length === 0 && search.trim() && !exactMatch && (
                  <CommandEmpty>No matching tags found.</CommandEmpty>
                )}
                {filteredTags.length > 0 && (
                  <CommandGroup>
                    {filteredTags.map((tag) => (
                      <TagItem
                        key={tag.id}
                        tag={tag}
                        isApplied={appliedTagIds.has(tag.id)}
                        isPending={pendingTagIds.has(tag.id)}
                        onToggle={handleToggle}
                      />
                    ))}
                  </CommandGroup>
                )}
                {search.trim() && !exactMatch && (
                  <CommandGroup>
                    <CommandItem
                      value={`create:${search}`}
                      onSelect={handleCreate}
                      className="flex items-center gap-2 px-2 py-1.5"
                      disabled={createTagMutation.isPending}
                    >
                      <Plus className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                      <span className="text-sm">
                        Create{' '}
                        <Badge
                          colorStyle={getTagColor(search.trim())}
                          className="text-xs"
                        >
                          {search.trim()}
                        </Badge>
                      </span>
                      {createTagMutation.isPending && (
                        <Loader2 className="ml-auto h-3 w-3 animate-spin text-muted-foreground" />
                      )}
                    </CommandItem>
                  </CommandGroup>
                )}
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
