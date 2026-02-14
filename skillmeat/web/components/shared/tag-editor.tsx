/**
 * Tag Editor Component
 *
 * Editable tag component with add/remove functionality and autocomplete.
 * Displays tags as badges with remove buttons, and provides a popover
 * for adding new tags from available options or creating custom tags.
 */

'use client';

import * as React from 'react';
import { X, Plus } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { cn } from '@/lib/utils';
import { normalizeTagForStorage } from '@/lib/utils/tag-suggestions';

// ============================================================================
// Types
// ============================================================================

export interface TagEditorProps {
  /** Current tags to display */
  tags: string[];
  /** Callback when tags change (add/remove) */
  onTagsChange: (tags: string[]) => void;
  /** Available tags for autocomplete suggestions */
  availableTags?: string[];
  /** Show loading state */
  isLoading?: boolean;
  /** Disable editing */
  disabled?: boolean;
  /** Additional CSS classes for the container */
  className?: string;
}

// ============================================================================
// Color Utilities (from tag-badge.tsx)
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
  return TAG_COLORS[hash % TAG_COLORS.length] as string;
}

// ============================================================================
// Sub-components
// ============================================================================

interface EditableTagBadgeProps {
  tag: string;
  onRemove: (tag: string) => void;
  disabled?: boolean;
}

function EditableTagBadge({ tag, onRemove, disabled }: EditableTagBadgeProps) {
  const color = getTagColor(tag);

  const handleRemove = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      onRemove(tag);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!disabled && (e.key === 'Enter' || e.key === ' ' || e.key === 'Backspace')) {
      e.preventDefault();
      onRemove(tag);
    }
  };

  return (
    <Badge
      colorStyle={color}
      className={cn('group gap-1 pr-1 text-xs transition-all', !disabled && 'hover:pr-0.5')}
    >
      {tag}
      {!disabled && (
        <button
          type="button"
          onClick={handleRemove}
          onKeyDown={handleKeyDown}
          className={cn(
            'ml-0.5 rounded-full p-0.5 opacity-0 transition-opacity hover:bg-black/20 focus:opacity-100 focus:outline-none group-hover:opacity-100'
          )}
          aria-label={`Remove tag: ${tag}`}
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </Badge>
  );
}

interface AddTagPopoverProps {
  availableTags: string[];
  currentTags: string[];
  onAddTag: (tag: string) => void;
  disabled?: boolean;
}

function AddTagPopover({ availableTags, currentTags, onAddTag, disabled }: AddTagPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');

  // Filter out already-selected tags and filter by search
  const filteredTags = React.useMemo(() => {
    const currentTagsLower = new Set(currentTags.map((t) => t.toLowerCase()));
    return availableTags.filter((tag) => {
      const tagLower = tag.toLowerCase();
      // Exclude already selected tags
      if (currentTagsLower.has(tagLower)) return false;
      // Filter by search
      if (search && !tagLower.includes(search.toLowerCase())) return false;
      return true;
    }).sort((a, b) => a.localeCompare(b));
  }, [availableTags, currentTags, search]);

  // Check if search text matches an existing available tag (case-insensitive)
  const searchMatchesExisting = React.useMemo(() => {
    if (!search) return false;
    const searchLower = search.toLowerCase();
    return availableTags.some((tag) => tag.toLowerCase() === searchLower);
  }, [availableTags, search]);

  // Check if search text is already in current tags
  const searchAlreadySelected = React.useMemo(() => {
    if (!search) return false;
    const normalizedSearch = normalizeTagForStorage(search);
    return currentTags.some((tag) => tag.toLowerCase() === normalizedSearch);
  }, [currentTags, search]);

  // Show create option when:
  // - Search has text
  // - Doesn't match existing available tag
  // - Not already in current tags
  const showCreateOption = search.trim() && !searchMatchesExisting && !searchAlreadySelected;

  const handleSelectTag = (tag: string) => {
    onAddTag(tag);
    setSearch('');
    setOpen(false);
  };

  const handleCreateTag = () => {
    const normalizedTag = normalizeTagForStorage(search);
    if (normalizedTag) {
      onAddTag(normalizedTag);
      setSearch('');
      setOpen(false);
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="h-6 w-6 rounded-full p-0"
          disabled={disabled}
          aria-label="Add tag"
        >
          <Plus className="h-3 w-3" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search or create tag..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>
              {search.trim() ? (
                <span className="text-muted-foreground">No matching tags</span>
              ) : (
                <span className="text-muted-foreground">Type to search or create</span>
              )}
            </CommandEmpty>

            {filteredTags.length > 0 && (
              <CommandGroup heading="Available tags">
                {filteredTags.map((tag) => (
                  <CommandItem
                    key={tag}
                    value={tag}
                    onSelect={() => handleSelectTag(tag)}
                    className="cursor-pointer"
                  >
                    <Badge colorStyle={getTagColor(tag)} className="text-xs">
                      {tag}
                    </Badge>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}

            {showCreateOption && (
              <>
                {filteredTags.length > 0 && <CommandSeparator />}
                <CommandGroup heading="Create new">
                  <CommandItem
                    value={`create-${search}`}
                    onSelect={handleCreateTag}
                    className="cursor-pointer"
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Create &quot;{normalizeTagForStorage(search)}&quot;
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function TagEditor({
  tags,
  onTagsChange,
  availableTags = [],
  isLoading = false,
  disabled = false,
  className,
}: TagEditorProps) {
  const handleRemoveTag = React.useCallback(
    (tagToRemove: string) => {
      onTagsChange(tags.filter((tag) => tag !== tagToRemove));
    },
    [tags, onTagsChange]
  );

  const handleAddTag = React.useCallback(
    (newTag: string) => {
      // Normalize the tag before adding
      const normalizedTag = normalizeTagForStorage(newTag);

      // Check if tag already exists (case-insensitive)
      const tagExists = tags.some((t) => t.toLowerCase() === normalizedTag.toLowerCase());

      if (!tagExists && normalizedTag) {
        onTagsChange([...tags, normalizedTag]);
      }
    },
    [tags, onTagsChange]
  );

  if (isLoading) {
    return (
      <div className={cn('flex items-center gap-1', className)}>
        <div className="h-5 w-16 animate-pulse rounded-md bg-muted" />
        <div className="h-5 w-12 animate-pulse rounded-md bg-muted" />
      </div>
    );
  }

  return (
    <div
      className={cn('flex flex-wrap items-center gap-1.5', className)}
      role="group"
      aria-label="Tag editor"
    >
      {[...tags].sort((a, b) => a.localeCompare(b)).map((tag) => (
        <EditableTagBadge key={tag} tag={tag} onRemove={handleRemoveTag} disabled={disabled} />
      ))}
      <AddTagPopover
        availableTags={availableTags}
        currentTags={tags}
        onAddTag={handleAddTag}
        disabled={disabled}
      />
    </div>
  );
}
