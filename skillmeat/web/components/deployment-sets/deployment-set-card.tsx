'use client';

import * as React from 'react';
import { Check, Copy, Edit3, Layers3, Loader2, Plus, Rocket, Trash2, X } from 'lucide-react';
import type { DeploymentSet } from '@/types/deployment-sets';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import { COLOR_TAILWIND_CLASSES } from '@/lib/group-constants';
import { cn } from '@/lib/utils';
import { getTagColor } from '@/lib/utils/tag-colors';
import { useUpdateDeploymentSet } from '@/hooks';

/**
 * Normalize a color value (token name or hex) to a valid hex string,
 * returning null when the input is not a valid hex.
 */
function normalizeHexColor(value: string): string | null {
  const hex = value.trim().replace(/^#/, '').toLowerCase();
  if (/^[0-9a-f]{3}$/.test(hex)) {
    return `#${hex
      .split('')
      .map((part) => `${part}${part}`)
      .join('')}`;
  }
  if (/^[0-9a-f]{6}$/.test(hex)) {
    return `#${hex}`;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Inline tag editing popover for deployment sets
// ---------------------------------------------------------------------------

interface DeploymentSetTagPopoverProps {
  set: DeploymentSet;
}

function DeploymentSetTagPopover({ set }: DeploymentSetTagPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [isPending, setIsPending] = React.useState(false);
  const updateSet = useUpdateDeploymentSet();

  const currentTags = set.tags ?? [];

  // Filter to tags matching search (plus show current tags)
  const filteredTags = React.useMemo(() => {
    if (!search.trim()) return currentTags;
    const q = search.toLowerCase().trim();
    return currentTags.filter((t) => t.toLowerCase().includes(q));
  }, [currentTags, search]);

  const exactMatch = React.useMemo(() => {
    if (!search.trim()) return true;
    return currentTags.some((t) => t.toLowerCase() === search.toLowerCase().trim());
  }, [currentTags, search]);

  const handleRemoveTag = React.useCallback(
    async (tag: string) => {
      setIsPending(true);
      try {
        await updateSet.mutateAsync({
          id: set.id,
          data: { tags: currentTags.filter((t) => t !== tag) },
        });
      } catch (err) {
        console.error('[DeploymentSetTagPopover] Failed to remove tag:', err);
      } finally {
        setIsPending(false);
      }
    },
    [set.id, currentTags, updateSet],
  );

  const handleAddTag = React.useCallback(
    async (tag: string) => {
      const trimmed = tag.trim();
      if (!trimmed || currentTags.includes(trimmed)) return;
      setIsPending(true);
      try {
        await updateSet.mutateAsync({
          id: set.id,
          data: { tags: [...currentTags, trimmed] },
        });
        setSearch('');
      } catch (err) {
        console.error('[DeploymentSetTagPopover] Failed to add tag:', err);
      } finally {
        setIsPending(false);
      }
    },
    [set.id, currentTags, updateSet],
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-5 w-5 rounded-full"
          aria-label="Edit tags"
          onClick={(e) => e.stopPropagation()}
        >
          <Plus className="h-3 w-3" aria-hidden="true" />
        </Button>
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
            placeholder="Search or add tags..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList className="max-h-56">
            {currentTags.length === 0 && !search.trim() ? (
              <CommandEmpty>No tags yet. Type to add one.</CommandEmpty>
            ) : (
              <>
                {filteredTags.length > 0 && (
                  <CommandGroup heading="Current tags">
                    {filteredTags.map((tag) => (
                      <CommandItem
                        key={tag}
                        value={tag}
                        onSelect={() => void handleRemoveTag(tag)}
                        className="flex items-center gap-2 px-2 py-1.5"
                        disabled={isPending}
                      >
                        <div className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-sm border border-primary bg-primary text-primary-foreground">
                          <Check className="h-3 w-3" aria-hidden="true" />
                        </div>
                        <Badge colorStyle={getTagColor(tag)} className="text-xs">
                          {tag}
                        </Badge>
                        <X className="ml-auto h-3 w-3 text-muted-foreground" aria-hidden="true" />
                        {isPending && (
                          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                        )}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                )}
                {search.trim() && !exactMatch && (
                  <CommandGroup>
                    <CommandItem
                      value={`create:${search}`}
                      onSelect={() => void handleAddTag(search)}
                      className="flex items-center gap-2 px-2 py-1.5"
                      disabled={isPending}
                    >
                      <Plus className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                      <span className="text-sm">
                        Add{' '}
                        <Badge colorStyle={getTagColor(search.trim())} className="text-xs">
                          {search.trim()}
                        </Badge>
                      </span>
                      {isPending && (
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

interface DeploymentSetCardProps {
  set: DeploymentSet;
  onOpen?: (setId: string) => void;
  onEdit: (set: DeploymentSet) => void;
  onDelete: (set: DeploymentSet) => void;
  onClone: (set: DeploymentSet) => void;
  onDeploy?: (set: DeploymentSet) => void;
}

export function DeploymentSetCard({ set, onOpen, onEdit, onDelete, onClone, onDeploy }: DeploymentSetCardProps) {
  const tags = set.tags ?? [];
  const tokenColorClass =
    set.color && !set.color.startsWith('#')
      ? (COLOR_TAILWIND_CLASSES[set.color] ?? COLOR_TAILWIND_CLASSES.slate)
      : COLOR_TAILWIND_CLASSES.slate;
  const customColor = set.color ? normalizeHexColor(set.color) : null;
  const borderColorClass = customColor ? 'border-l-border' : tokenColorClass;

  // Handle card click, avoiding trigger when clicking action buttons or dropdowns
  const handleCardClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('[role="menuitem"]')) {
      return;
    }
    onOpen?.(set.id);
  };

  // Handle keyboard navigation for the card surface
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onOpen?.(set.id);
    }
  };

  return (
    <Card
      className={cn(
        'border-l-4 transition-all',
        borderColorClass,
        onOpen && 'cursor-pointer hover:border-primary/50 hover:shadow-md',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
      )}
      style={customColor ? { borderLeftColor: customColor } : undefined}
      role={onOpen ? 'button' : undefined}
      tabIndex={onOpen ? 0 : undefined}
      onClick={onOpen ? handleCardClick : undefined}
      onKeyDown={onOpen ? handleKeyDown : undefined}
      aria-label={onOpen ? `Open ${set.name} deployment set` : undefined}
    >
      <CardHeader className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            {set.icon ? (
              <span className="shrink-0 text-base" aria-hidden="true">
                {set.icon}
              </span>
            ) : (
              <Layers3 className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            )}
            <CardTitle className="truncate text-base">{set.name}</CardTitle>
          </div>
          <Badge variant="secondary" aria-label={`${set.member_count} members`}>
            {set.member_count}
          </Badge>
        </div>
        <CardDescription className="line-clamp-2 min-h-[2.5rem]">
          {set.description || 'No description provided.'}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Tags row */}
        <div className="flex min-h-[1.5rem] flex-wrap items-center gap-1">
          {tags.length > 0 ? (
            tags.map((tag) => (
              <Badge key={tag} colorStyle={getTagColor(tag)} className="text-xs">
                {tag}
              </Badge>
            ))
          ) : (
            <span className="text-xs text-muted-foreground">No tags</span>
          )}
          <DeploymentSetTagPopover set={set} />
        </div>

        <div className="text-xs text-muted-foreground">
          Updated {new Date(set.updated_at).toLocaleDateString()}
        </div>

        {/* Action buttons — stopPropagation so they don't trigger card click */}
        <div
          className="flex flex-wrap gap-2"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          {onDeploy && (
            <Button size="sm" onClick={() => onDeploy(set)} aria-label={`Deploy ${set.name}`}>
              <Rocket className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
              Deploy
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => onEdit(set)}>
            <Edit3 className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            Edit
          </Button>
          <Button variant="outline" size="sm" onClick={() => onClone(set)}>
            <Copy className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            Clone
          </Button>
          <Button variant="outline" size="sm" onClick={() => onDelete(set)}>
            <Trash2 className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
