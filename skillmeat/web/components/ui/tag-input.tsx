"use client";

import * as React from "react";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface Tag {
  id: string;
  name: string;
  slug: string;
  color?: string;
}

export interface TagInputProps {
  /**
   * Current tag IDs or names
   */
  value: string[];
  /**
   * Callback when tags change
   */
  onChange: (tags: string[]) => void;
  /**
   * Available tags to suggest in dropdown
   */
  suggestions?: Tag[];
  /**
   * Search callback for autocomplete (optional)
   */
  onSearch?: (query: string) => void;
  /**
   * Placeholder text when input is empty
   */
  placeholder?: string;
  /**
   * Disable input
   */
  disabled?: boolean;
  /**
   * Maximum number of tags allowed
   */
  maxTags?: number;
  /**
   * Allow creating new tags by typing
   */
  allowCreate?: boolean;
  /**
   * Additional CSS classes
   */
  className?: string;
}

export function TagInput({
  value = [],
  onChange,
  suggestions = [],
  onSearch,
  placeholder = "Add tags...",
  disabled = false,
  maxTags,
  allowCreate = true,
  className,
}: TagInputProps) {
  const [inputValue, setInputValue] = React.useState("");
  const [isOpen, setIsOpen] = React.useState(false);
  const [highlightedIndex, setHighlightedIndex] = React.useState(-1);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Filter suggestions based on input
  const filteredSuggestions = React.useMemo(() => {
    if (!inputValue.trim()) return [];

    const query = inputValue.toLowerCase();
    return suggestions
      .filter((tag) => {
        // Don't show already selected tags
        if (value.includes(tag.id) || value.includes(tag.name)) return false;
        // Match by name or slug
        return tag.name.toLowerCase().includes(query) || tag.slug.toLowerCase().includes(query);
      })
      .slice(0, 10); // Limit to 10 suggestions
  }, [suggestions, inputValue, value]);

  // Get tag object from ID or name
  const getTag = React.useCallback(
    (idOrName: string): Tag | undefined => {
      return suggestions.find((tag) => tag.id === idOrName || tag.name === idOrName);
    },
    [suggestions]
  );

  // Add a tag
  const addTag = React.useCallback(
    (tagIdOrName: string) => {
      if (!tagIdOrName.trim()) return;

      // Check max tags limit
      if (maxTags && value.length >= maxTags) {
        return;
      }

      // Check if tag already exists
      const tag = getTag(tagIdOrName);
      const tagToAdd = tag ? tag.id : tagIdOrName.trim();

      if (!value.includes(tagToAdd)) {
        onChange([...value, tagToAdd]);
        setInputValue("");
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
    },
    [value, onChange, maxTags, getTag]
  );

  // Remove a tag
  const removeTag = React.useCallback(
    (tagIdOrName: string) => {
      onChange(value.filter((t) => t !== tagIdOrName));
      inputRef.current?.focus();
    },
    [value, onChange]
  );

  // Handle input change
  const handleInputChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value;
      setInputValue(newValue);
      setIsOpen(newValue.trim().length > 0);
      setHighlightedIndex(-1);
      onSearch?.(newValue);
    },
    [onSearch]
  );

  // Handle keyboard navigation
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (highlightedIndex >= 0 && filteredSuggestions[highlightedIndex]) {
          // Select highlighted suggestion
          addTag(filteredSuggestions[highlightedIndex].id);
        } else if (inputValue.trim() && allowCreate) {
          // Create new tag from input
          addTag(inputValue.trim());
        }
      } else if (e.key === "Backspace" && !inputValue) {
        // Remove last tag when backspace on empty input
        if (value.length > 0) {
          removeTag(value[value.length - 1]);
        }
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : prev
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : -1));
      } else if (e.key === "Escape") {
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
    },
    [inputValue, highlightedIndex, filteredSuggestions, allowCreate, value, addTag, removeTag]
  );

  // Handle paste (support CSV - comma-separated values)
  const handlePaste = React.useCallback(
    (e: React.ClipboardEvent<HTMLInputElement>) => {
      const pastedText = e.clipboardData.getData("text");

      // Check if pasted text contains commas (CSV format)
      if (pastedText.includes(",")) {
        e.preventDefault();

        const tags = pastedText
          .split(",")
          .map((tag) => tag.trim())
          .filter((tag) => tag.length > 0);

        // Add each tag, respecting maxTags limit
        let added = 0;
        for (const tag of tags) {
          if (maxTags && value.length + added >= maxTags) break;
          if (!value.includes(tag)) {
            addTag(tag);
            added++;
          }
        }

        setInputValue("");
        setIsOpen(false);
      }
    },
    [value, maxTags, addTag]
  );

  // Handle suggestion click
  const handleSuggestionClick = React.useCallback(
    (tag: Tag) => {
      addTag(tag.id);
      inputRef.current?.focus();
    },
    [addTag]
  );

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isMaxTagsReached = maxTags && value.length >= maxTags;

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <div
        className={cn(
          "flex flex-wrap gap-1 p-2 border rounded-md min-h-[42px] bg-background",
          "focus-within:ring-1 focus-within:ring-ring focus-within:outline-none",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        {value.map((tagIdOrName) => {
          const tag = getTag(tagIdOrName);
          return (
            <Badge
              key={tagIdOrName}
              variant="secondary"
              colorStyle={tag?.color}
              className="gap-1 h-6"
            >
              {tag?.name || tagIdOrName}
              {!disabled && (
                <button
                  type="button"
                  className="ml-1 hover:bg-black/10 rounded-full p-0.5 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeTag(tagIdOrName);
                  }}
                  aria-label={`Remove tag ${tag?.name || tagIdOrName}`}
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </Badge>
          );
        })}
        <input
          ref={inputRef}
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          onFocus={() => inputValue.trim() && setIsOpen(true)}
          placeholder={value.length === 0 ? placeholder : ""}
          disabled={disabled || isMaxTagsReached}
          className={cn(
            "flex-1 min-w-[100px] outline-none bg-transparent text-sm",
            "placeholder:text-muted-foreground",
            "disabled:cursor-not-allowed"
          )}
          aria-label="Tag input"
          aria-expanded={isOpen}
          aria-controls="tag-suggestions"
          aria-activedescendant={
            highlightedIndex >= 0 ? `tag-suggestion-${highlightedIndex}` : undefined
          }
          role="combobox"
        />
      </div>

      {/* Suggestions dropdown */}
      {isOpen && filteredSuggestions.length > 0 && (
        <div
          id="tag-suggestions"
          role="listbox"
          className={cn(
            "absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-md",
            "animate-in fade-in-0 zoom-in-95 slide-in-from-top-2",
            "max-h-[300px] overflow-y-auto"
          )}
        >
          {filteredSuggestions.map((tag, index) => (
            <div
              key={tag.id}
              id={`tag-suggestion-${index}`}
              role="option"
              aria-selected={index === highlightedIndex}
              className={cn(
                "px-3 py-2 cursor-pointer transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                index === highlightedIndex && "bg-accent text-accent-foreground"
              )}
              onClick={() => handleSuggestionClick(tag)}
              onMouseEnter={() => setHighlightedIndex(index)}
            >
              <Badge variant="secondary" colorStyle={tag.color} className="pointer-events-none">
                {tag.name}
              </Badge>
            </div>
          ))}
        </div>
      )}

      {/* Max tags reached message */}
      {isMaxTagsReached && (
        <p className="text-xs text-muted-foreground mt-1" role="status" aria-live="polite">
          Maximum {maxTags} tags reached
        </p>
      )}
    </div>
  );
}
