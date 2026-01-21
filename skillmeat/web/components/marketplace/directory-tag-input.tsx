/**
 * Directory Tag Input Component
 *
 * A reusable tag input component with autocomplete functionality.
 * Fetches existing tags from the API and shows them in a dropdown
 * as the user types. Supports keyboard navigation and click selection.
 *
 * Features:
 * - Autocomplete from existing tags in the system
 * - Debounced search for performance
 * - Keyboard navigation (arrow keys, Enter, Escape)
 * - Click to select from dropdown
 * - Still allows creating new tags (Enter on custom text)
 * - Full accessibility support
 *
 * @example
 * ```tsx
 * <DirectoryTagInput
 *   directoryPath="skills/canvas"
 *   currentTags={['design', 'ui']}
 *   suggestedTags={['skills', 'canvas']}
 *   onAddTag={(tag) => console.log('Added:', tag)}
 *   onRemoveTag={(tag) => console.log('Removed:', tag)}
 *   onAddSuggestedTag={(tag) => console.log('Added suggested:', tag)}
 * />
 * ```
 */

'use client';

import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Tag, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useDebounce, useSearchTags } from '@/hooks';

export interface DirectoryTagInputProps {
  /** Directory path for context (used in labels and IDs) */
  directoryPath: string;
  /** Currently applied tags for this directory */
  currentTags: string[];
  /** Path-based suggested tags */
  suggestedTags: string[];
  /** Callback when a tag is added */
  onAddTag: (tag: string) => void;
  /** Callback when a tag is removed */
  onRemoveTag: (tag: string) => void;
  /** Callback when a suggested tag is added */
  onAddSuggestedTag: (tag: string) => void;
  /** Additional class name for the container */
  className?: string;
}

/**
 * DirectoryTagInput - Tag input with autocomplete from existing tags
 */
export function DirectoryTagInput({
  directoryPath,
  currentTags,
  suggestedTags,
  onAddTag,
  onRemoveTag,
  onAddSuggestedTag,
  className,
}: DirectoryTagInputProps) {
  // Input state
  const [inputValue, setInputValue] = useState('');
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  // Refs
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounce the search query for performance (150ms delay)
  const debouncedQuery = useDebounce(inputValue, 150);

  // Search for existing tags using the API
  const { data: searchResults, isLoading: isSearching } = useSearchTags(
    debouncedQuery,
    debouncedQuery.length >= 1
  );

  // Filter out tags that are already applied
  const filteredResults = useMemo(() => {
    if (!searchResults) return [];

    return searchResults.filter((tag) => !currentTags.includes(tag.name.toLowerCase()));
  }, [searchResults, currentTags]);

  // Filter suggested tags that aren't already applied
  const availableSuggestedTags = useMemo(() => {
    return suggestedTags.filter((tag) => !currentTags.includes(tag.toLowerCase()));
  }, [suggestedTags, currentTags]);

  // Reset highlighted index when results change
  useEffect(() => {
    setHighlightedIndex(-1);
  }, [filteredResults]);

  // Close popover when input loses focus (with delay for click handling)
  const handleBlur = useCallback(() => {
    // Delay closing to allow click events on dropdown items
    setTimeout(() => {
      setIsPopoverOpen(false);
    }, 150);
  }, []);

  // Handle input changes
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInputValue(value);

    // Open popover when typing
    if (value.length >= 1) {
      setIsPopoverOpen(true);
    } else {
      setIsPopoverOpen(false);
    }
  }, []);

  // Add tag from input or selection
  const addTag = useCallback(
    (tag: string) => {
      const trimmedTag = tag.trim().toLowerCase();
      if (!trimmedTag) return;

      // Check if tag is already added
      if (currentTags.includes(trimmedTag)) {
        setInputValue('');
        setIsPopoverOpen(false);
        return;
      }

      onAddTag(trimmedTag);
      setInputValue('');
      setIsPopoverOpen(false);
      setHighlightedIndex(-1);

      // Keep focus on input for quick successive additions
      inputRef.current?.focus();
    },
    [currentTags, onAddTag]
  );

  // Select a tag from the autocomplete dropdown
  const selectFromDropdown = useCallback(
    (tagName: string) => {
      addTag(tagName);
    },
    [addTag]
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      const hasResults = filteredResults.length > 0;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          if (!isPopoverOpen && inputValue.length >= 1) {
            setIsPopoverOpen(true);
          }
          if (hasResults) {
            setHighlightedIndex((prev) => (prev < filteredResults.length - 1 ? prev + 1 : 0));
          }
          break;

        case 'ArrowUp':
          e.preventDefault();
          if (hasResults) {
            setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : filteredResults.length - 1));
          }
          break;

        case 'Enter':
          e.preventDefault();
          if (highlightedIndex >= 0 && filteredResults[highlightedIndex]) {
            // Select highlighted item from dropdown
            selectFromDropdown(filteredResults[highlightedIndex].name);
          } else if (inputValue.trim()) {
            // Add as new tag
            addTag(inputValue);
          }
          break;

        case 'Escape':
          e.preventDefault();
          setIsPopoverOpen(false);
          setHighlightedIndex(-1);
          break;

        case 'Tab':
          // Close popover on tab, allow normal tab behavior
          setIsPopoverOpen(false);
          break;
      }
    },
    [isPopoverOpen, inputValue, filteredResults, highlightedIndex, addTag, selectFromDropdown]
  );

  // Handle click on add button
  const handleAddClick = useCallback(() => {
    if (inputValue.trim()) {
      addTag(inputValue);
    }
  }, [inputValue, addTag]);

  // Generate unique ID for accessibility
  const inputId = `tag-input-${directoryPath.replace(/\//g, '-')}`;
  const listId = `tag-list-${directoryPath.replace(/\//g, '-')}`;

  return (
    <div className={cn('space-y-2', className)}>
      {/* Tag Input with Autocomplete */}
      <div className="flex items-center gap-2">
        <Label htmlFor={inputId} className="shrink-0 text-sm text-muted-foreground">
          Tags:
        </Label>
        <div className="flex flex-1 items-center gap-2">
          <Popover open={isPopoverOpen && filteredResults.length > 0}>
            <PopoverTrigger asChild>
              <div className="relative flex-1">
                <Input
                  ref={inputRef}
                  id={inputId}
                  type="text"
                  placeholder="Add tag and press Enter"
                  value={inputValue}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  onFocus={() => {
                    if (inputValue.length >= 1) {
                      setIsPopoverOpen(true);
                    }
                  }}
                  onBlur={handleBlur}
                  className="h-8 pr-8 text-sm"
                  aria-label={`Add tag for ${directoryPath}`}
                  aria-autocomplete="list"
                  aria-expanded={isPopoverOpen && filteredResults.length > 0}
                  aria-controls={listId}
                  aria-activedescendant={
                    highlightedIndex >= 0 ? `${listId}-option-${highlightedIndex}` : undefined
                  }
                  autoComplete="off"
                />
                {isSearching && (
                  <Loader2
                    className="absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground"
                    aria-hidden="true"
                  />
                )}
              </div>
            </PopoverTrigger>
            <PopoverContent
              className="w-[--radix-popover-trigger-width] p-0"
              align="start"
              side="bottom"
              onOpenAutoFocus={(e) => e.preventDefault()}
              onCloseAutoFocus={(e) => e.preventDefault()}
            >
              <Command shouldFilter={false}>
                <CommandList id={listId} role="listbox">
                  {filteredResults.length === 0 ? (
                    <CommandEmpty className="px-3 py-2 text-sm text-muted-foreground">
                      {isSearching ? 'Searching...' : 'No matching tags found'}
                    </CommandEmpty>
                  ) : (
                    <CommandGroup>
                      {filteredResults.map((tag, index) => (
                        <CommandItem
                          key={tag.id}
                          id={`${listId}-option-${index}`}
                          value={tag.name}
                          onSelect={() => selectFromDropdown(tag.name)}
                          className={cn(
                            'cursor-pointer',
                            highlightedIndex === index && 'bg-accent'
                          )}
                          role="option"
                          aria-selected={highlightedIndex === index}
                        >
                          <Tag className="mr-2 h-3 w-3" aria-hidden="true" />
                          <span>{tag.name}</span>
                          {tag.artifact_count !== undefined && (
                            <span className="ml-auto text-xs text-muted-foreground">
                              {tag.artifact_count} artifacts
                            </span>
                          )}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  )}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddClick}
            disabled={!inputValue.trim()}
            aria-label={`Add tag to ${directoryPath}`}
          >
            <Tag className="h-3 w-3" aria-hidden="true" />
            <span className="sr-only">Add tag</span>
          </Button>
        </div>
      </div>

      {/* Current Tags */}
      {currentTags.length > 0 && (
        <div
          className="flex flex-wrap gap-1"
          role="list"
          aria-label={`Applied tags for ${directoryPath}`}
        >
          {currentTags.map((tag) => (
            <Badge
              key={tag}
              variant="default"
              className="cursor-pointer hover:bg-destructive hover:text-destructive-foreground"
              onClick={() => onRemoveTag(tag)}
              role="listitem"
              aria-label={`Remove tag ${tag}`}
            >
              {tag}
              <span className="ml-1" aria-hidden="true">
                x
              </span>
            </Badge>
          ))}
        </div>
      )}

      {/* Suggested Tags (from path) */}
      {availableSuggestedTags.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="shrink-0 text-xs text-muted-foreground">Suggested:</span>
          <div
            className="flex flex-wrap gap-1"
            role="list"
            aria-label={`Suggested tags for ${directoryPath}`}
          >
            {availableSuggestedTags.map((tag) => (
              <Badge
                key={tag}
                variant="outline"
                className="cursor-pointer hover:bg-secondary"
                onClick={() => onAddSuggestedTag(tag)}
                role="listitem"
                aria-label={`Add suggested tag ${tag}`}
              >
                {tag}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
