'use client';

import * as React from 'react';
import { Filter, X, Check, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useTags } from '@/hooks/use-tags';

interface TagFilterPopoverProps {
  selectedTags: string[];
  onChange: (tags: string[]) => void;
  className?: string;
}

/**
 * Tag filter popover component with search and multi-select
 *
 * Shows a popover with all available tags and their artifact counts.
 * Allows multi-select of tags for filtering with a search box.
 *
 * @example
 * ```tsx
 * const [selectedTags, setSelectedTags] = useState<string[]>([]);
 * <TagFilterPopover selectedTags={selectedTags} onChange={setSelectedTags} />
 * ```
 */
export function TagFilterPopover({ selectedTags, onChange, className }: TagFilterPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const { data: tagsData, isLoading } = useTags(100);

  const tags = tagsData?.items || [];

  // Filter tags by search
  const filteredTags = React.useMemo(() => {
    if (!search) return tags;
    return tags.filter((tag) => tag.name.toLowerCase().includes(search.toLowerCase()));
  }, [tags, search]);

  const toggleTag = (tagId: string) => {
    if (selectedTags.includes(tagId)) {
      onChange(selectedTags.filter((id) => id !== tagId));
    } else {
      onChange([...selectedTags, tagId]);
    }
  };

  const clearAll = () => {
    onChange([]);
    setSearch('');
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className={cn('gap-2', className)}>
          <Filter className="h-4 w-4" />
          Tags
          {selectedTags.length > 0 && (
            <Badge variant="secondary" className="ml-1 rounded-full px-2">
              {selectedTags.length}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-0" align="start">
        <div className="border-b p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium">Filter by tags</span>
            {selectedTags.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearAll} className="h-6 px-2 text-xs">
                Clear all
              </Button>
            )}
          </div>
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tags..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 pl-8"
            />
          </div>
        </div>
        <ScrollArea className="h-60">
          <div className="p-2">
            {isLoading ? (
              <div className="py-4 text-center text-sm text-muted-foreground">Loading tags...</div>
            ) : filteredTags.length === 0 ? (
              <div className="py-4 text-center text-sm text-muted-foreground">No tags found</div>
            ) : (
              filteredTags.map((tag) => {
                const isSelected = selectedTags.includes(tag.id);
                return (
                  <div
                    key={tag.id}
                    className={cn(
                      'flex cursor-pointer items-center justify-between rounded-md px-2 py-1.5 hover:bg-accent',
                      isSelected && 'bg-accent'
                    )}
                    onClick={() => toggleTag(tag.id)}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={cn(
                          'flex h-4 w-4 items-center justify-center rounded border',
                          isSelected ? 'border-primary bg-primary' : 'border-input'
                        )}
                      >
                        {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                      </div>
                      <Badge variant="secondary" colorStyle={tag.color}>
                        {tag.name}
                      </Badge>
                    </div>
                    {tag.artifact_count !== undefined && (
                      <span className="text-xs text-muted-foreground">{tag.artifact_count}</span>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}

/**
 * Inline filter bar showing selected tags with remove buttons
 *
 * Only visible when tags are selected. Shows each selected tag
 * with an X button to remove it, plus a "Clear all" button.
 *
 * @example
 * ```tsx
 * const [selectedTags, setSelectedTags] = useState<string[]>(['tag1', 'tag2']);
 * <TagFilterBar selectedTags={selectedTags} onChange={setSelectedTags} />
 * ```
 */
export function TagFilterBar({ selectedTags, onChange, className }: TagFilterPopoverProps) {
  const { data: tagsData } = useTags(100);
  const tags = tagsData?.items || [];

  const selectedTagDetails = tags.filter((t) => selectedTags.includes(t.id));

  if (selectedTags.length === 0) return null;

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <span className="text-sm text-muted-foreground">Filtering by:</span>
      {selectedTagDetails.map((tag) => (
        <Badge key={tag.id} variant="secondary" colorStyle={tag.color} className="gap-1">
          {tag.name}
          <X
            className="h-3 w-3 cursor-pointer hover:opacity-70"
            onClick={() => onChange(selectedTags.filter((id) => id !== tag.id))}
          />
        </Badge>
      ))}
      <Button variant="ghost" size="sm" onClick={() => onChange([])} className="h-6 text-xs">
        Clear all
      </Button>
    </div>
  );
}
