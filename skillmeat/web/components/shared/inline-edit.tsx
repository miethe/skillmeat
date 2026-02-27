/**
 * InlineEdit Component
 *
 * A click-to-edit text field that displays as plain text in view mode
 * and transitions to an input field on click.
 *
 * @example Basic usage
 * ```tsx
 * <InlineEdit value={name} onChange={setName} placeholder="Enter name..." />
 * ```
 *
 * @example As a heading
 * ```tsx
 * <InlineEdit
 *   value={title}
 *   onChange={setTitle}
 *   as="h2"
 *   placeholder="Untitled"
 *   className="text-xl font-semibold"
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface InlineEditProps {
  /** Current text value */
  value: string;
  /** Callback fired when the value is saved (Enter or blur) */
  onChange: (value: string) => void;
  /** Placeholder shown in both view and edit mode when value is empty */
  placeholder?: string;
  /** Additional CSS classes for the outer wrapper */
  className?: string;
  /** HTML element to render the text display as (default: 'span') */
  as?: 'h1' | 'h2' | 'h3' | 'p' | 'span';
  /** Additional CSS classes forwarded to the Input element in edit mode */
  inputClassName?: string;
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * InlineEdit - Click-to-edit plain text field
 *
 * Behavior:
 * - Display mode: renders as the chosen element with hover affordance
 * - Edit mode: auto-focused input; Enter saves, Escape cancels, blur saves
 * - Empty value shows placeholder in muted color
 * - Accessible: display element has role="button" and aria-label
 */
export function InlineEdit({
  value,
  onChange,
  placeholder = 'Click to edit...',
  className,
  as: Tag = 'span',
  inputClassName,
}: InlineEditProps) {
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(value);

  // Keep draft in sync when the external value changes while not editing
  React.useEffect(() => {
    if (!editing) {
      setDraft(value);
    }
  }, [value, editing]);

  const inputRef = React.useRef<HTMLInputElement>(null);

  // Enter edit mode and select all text
  const handleEnterEdit = React.useCallback(() => {
    setDraft(value);
    setEditing(true);
  }, [value]);

  // Focus + select all once the input mounts
  React.useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const save = React.useCallback(() => {
    setEditing(false);
    if (draft !== value) {
      onChange(draft);
    }
  }, [draft, value, onChange]);

  const cancel = React.useCallback(() => {
    setDraft(value);
    setEditing(false);
  }, [value]);

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        save();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        cancel();
      }
    },
    [save, cancel]
  );

  // Allow keyboard activation of the display element (Space / Enter)
  const handleDisplayKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleEnterEdit();
      }
    },
    [handleEnterEdit]
  );

  if (editing) {
    return (
      <Input
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={save}
        placeholder={placeholder}
        className={cn('inline-edit-input', inputClassName)}
        aria-label="Edit text"
      />
    );
  }

  const isEmpty = !value;

  return (
    <Tag
      role="button"
      tabIndex={0}
      onClick={handleEnterEdit}
      onKeyDown={handleDisplayKeyDown}
      aria-label={`Edit: ${isEmpty ? placeholder : value}`}
      className={cn(
        // Layout
        'inline-block cursor-pointer rounded-sm px-0.5 -mx-0.5',
        // Transition
        'transition-colors duration-150',
        // Hover: subtle background highlight
        'hover:bg-accent/50',
        // Focus ring for keyboard navigation
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
        // Empty / placeholder styling
        isEmpty && 'text-muted-foreground italic',
        className
      )}
    >
      {isEmpty ? placeholder : value}
    </Tag>
  );
}
