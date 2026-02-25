'use client';

/**
 * DeploymentSetTagEditor
 *
 * Shared inline tag editor for deployment sets. Renders the current tags as
 * removable badges and provides a popover command palette to toggle existing
 * tags from the API or create new ones on the fly.
 *
 * Designed to work both inside the details modal (flat surface) and inside
 * clickable cards — all interactive elements stop event propagation so the
 * parent card click handler never fires inadvertently.
 */

import * as React from 'react';
import { useState, useMemo, useCallback } from 'react';
import { Loader2, Check, Plus, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
import { useTags, useUpdateDeploymentSet, useCreateTag } from '@/hooks';
import { cn } from '@/lib/utils';
import { getTagColor } from '@/lib/utils/tag-colors';
import type { DeploymentSet } from '@/types/deployment-sets';

// ============================================================================
// Types
// ============================================================================

export interface DeploymentSetTagEditorProps {
  deploymentSet: DeploymentSet;
}

// ============================================================================
// Component
// ============================================================================

export function DeploymentSetTagEditor({ deploymentSet }: DeploymentSetTagEditorProps) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [pendingTags, setPendingTags] = useState<Set<string>>(new Set());

  const { data: allTagsResponse, isLoading: isLoadingAllTags } = useTags(100);
  const updateSet = useUpdateDeploymentSet();
  const createTagMutation = useCreateTag();

  const allTags = useMemo(
    () => [...(allTagsResponse?.items ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [allTagsResponse?.items],
  );

  const currentTagNames = useMemo(() => new Set(deploymentSet.tags), [deploymentSet.tags]);

  const filteredTags = useMemo(() => {
    if (!search.trim()) return allTags;
    const q = search.toLowerCase().trim();
    return allTags.filter((t) => t.name.toLowerCase().includes(q));
  }, [allTags, search]);

  const exactMatch = useMemo(() => {
    if (!search.trim()) return true;
    const q = search.toLowerCase().trim();
    return allTags.some((t) => t.name.toLowerCase() === q);
  }, [allTags, search]);

  const handleToggle = useCallback(
    async (tagName: string) => {
      const isApplied = currentTagNames.has(tagName);
      setPendingTags((prev) => new Set(prev).add(tagName));

      const updatedTags = isApplied
        ? deploymentSet.tags.filter((t) => t !== tagName)
        : [...deploymentSet.tags, tagName];

      try {
        await updateSet.mutateAsync({ id: deploymentSet.id, data: { tags: updatedTags } });
      } catch (err) {
        console.error('Failed to toggle tag:', err);
      } finally {
        setPendingTags((prev) => {
          const next = new Set(prev);
          next.delete(tagName);
          return next;
        });
      }
    },
    [deploymentSet.id, deploymentSet.tags, currentTagNames, updateSet],
  );

  const handleRemoveTag = useCallback(
    async (tagName: string) => {
      const updatedTags = deploymentSet.tags.filter((t) => t !== tagName);
      try {
        await updateSet.mutateAsync({ id: deploymentSet.id, data: { tags: updatedTags } });
      } catch (err) {
        console.error('Failed to remove tag:', err);
      }
    },
    [deploymentSet.id, deploymentSet.tags, updateSet],
  );

  const handleCreate = useCallback(async () => {
    const name = search.trim();
    if (!name) return;
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    try {
      await createTagMutation.mutateAsync({ name, slug, color: getTagColor(name) });
      const updatedTags = [...deploymentSet.tags, name];
      await updateSet.mutateAsync({ id: deploymentSet.id, data: { tags: updatedTags } });
      setSearch('');
    } catch (err) {
      console.error('Failed to create tag:', err);
    }
  }, [search, deploymentSet.id, deploymentSet.tags, createTagMutation, updateSet]);

  const sortedCurrentTags = useMemo(
    () => [...deploymentSet.tags].sort((a, b) => a.localeCompare(b)),
    [deploymentSet.tags],
  );

  return (
    <div>
      <div className="flex flex-wrap items-center gap-1.5" role="list" aria-label="Tags">
        {sortedCurrentTags.map((tag) => {
          const color = getTagColor(tag);
          return (
            <div key={tag} className="group relative flex items-center" role="listitem">
              <Badge colorStyle={color} className="pr-5 text-xs">
                {tag}
              </Badge>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  void handleRemoveTag(tag);
                }}
                className="absolute right-0.5 top-1/2 -translate-y-1/2 rounded-sm p-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                aria-label={`Remove tag ${tag}`}
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </div>
          );
        })}

        {sortedCurrentTags.length === 0 && (
          <p className="text-sm text-muted-foreground">No tags</p>
        )}

        {/* Add tag popover trigger */}
        <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 rounded-full p-0"
              aria-label="Add tag"
              onClick={(e) => e.stopPropagation()}
            >
              <Plus className="h-3.5 w-3.5" />
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
                placeholder="Search or create tags..."
                value={search}
                onValueChange={setSearch}
              />
              <CommandList className="max-h-56">
                {isLoadingAllTags ? (
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
                        {filteredTags.map((tag) => {
                          const isApplied = currentTagNames.has(tag.name);
                          const isPending = pendingTags.has(tag.name);
                          const color = tag.color || getTagColor(tag.name);
                          return (
                            <CommandItem
                              key={tag.id}
                              value={tag.name}
                              onSelect={() => void handleToggle(tag.name)}
                              className="flex items-center gap-2 px-2 py-1.5"
                              disabled={isPending}
                            >
                              <div
                                className={cn(
                                  'flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-sm border',
                                  isApplied
                                    ? 'border-primary bg-primary text-primary-foreground'
                                    : 'border-muted-foreground/30',
                                )}
                              >
                                {isApplied && <Check className="h-3 w-3" />}
                              </div>
                              <Badge colorStyle={color} className="text-xs">
                                {tag.name}
                              </Badge>
                              {isPending && (
                                <Loader2 className="ml-auto h-3 w-3 animate-spin text-muted-foreground" />
                              )}
                            </CommandItem>
                          );
                        })}
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
                            <Badge colorStyle={getTagColor(search.trim())} className="text-xs">
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
      </div>
    </div>
  );
}
