---
title: TagInput Component
description: A multi-tag input component with autocomplete, keyboard navigation, and CSV paste support for managing collections of tags in forms and filters.
audience: developers
tags: [component, form, input, tags, autocomplete]
created: 2025-12-18
updated: 2025-12-18
category: Components
status: active
related:
  - docs/components/badge.md
  - docs/components/input.md
---

# TagInput Component

A flexible, accessible multi-tag input component with autocomplete suggestions, keyboard navigation, and CSV paste support. Perfect for tagging artifacts, managing collections, and filtering content with predefined or custom tags.

## Overview

The TagInput component enables users to add and manage multiple tags through:

- **Autocomplete suggestions** - Filter predefined tags as users type
- **Keyboard navigation** - Arrow keys, Enter, Backspace for full navigation
- **CSV paste support** - Add multiple tags at once by pasting comma-separated values
- **Custom tag creation** - Allow users to create new tags beyond suggestions
- **Max tags limit** - Enforce maximum number of tags when needed
- **Full accessibility** - WCAG 2.1 AA compliant with proper ARIA attributes
- **Flexible styling** - Integrates with Radix UI Badge component and Tailwind CSS

## Installation

### Import

```tsx
import { TagInput, type Tag } from '@/components/ui/tag-input';
```

### With Form

```tsx
import { TagInput } from '@/components/ui/tag-input';
import { Button } from '@/components/ui/button';
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `value` | `string[]` | `[]` | Array of selected tag IDs or names |
| `onChange` | `(tags: string[]) => void` | required | Callback when tags change |
| `suggestions` | `Tag[]` | `[]` | Available tags for autocomplete dropdown |
| `onSearch` | `(query: string) => void` | - | Optional callback for search queries (useful for dynamic suggestions) |
| `placeholder` | `string` | `"Add tags..."` | Input placeholder text shown when no tags selected |
| `disabled` | `boolean` | `false` | Disable input and all interactions |
| `maxTags` | `number` | - | Maximum number of tags allowed (input disabled when reached) |
| `allowCreate` | `boolean` | `true` | Allow creating new tags by typing and pressing Enter |
| `className` | `string` | - | Additional CSS classes for the container |

## Tag Interface

```typescript
interface Tag {
  id: string;           // Unique identifier
  name: string;         // Display name
  slug: string;         // URL-friendly identifier
  color?: string;       // Optional hex color for badge styling
}
```

## Basic Usage

### Simple Tag Selection

```tsx
import { useState } from 'react';
import { TagInput, type Tag } from '@/components/ui/tag-input';

export function BasicExample() {
  const [tags, setTags] = useState<string[]>([]);

  const suggestions: Tag[] = [
    { id: '1', name: 'React', slug: 'react', color: '#61DAFB' },
    { id: '2', name: 'TypeScript', slug: 'typescript', color: '#3178C6' },
    { id: '3', name: 'Next.js', slug: 'nextjs', color: '#000000' },
  ];

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">Technologies</label>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        placeholder="Add technologies..."
      />
      <p className="text-sm text-muted-foreground">
        Selected: {tags.length > 0 ? tags.join(', ') : 'None'}
      </p>
    </div>
  );
}
```

### With Maximum Tags Limit

```tsx
export function MaxTagsExample() {
  const [tags, setTags] = useState<string[]>([]);

  const suggestions: Tag[] = [
    { id: 'bug', name: 'Bug', slug: 'bug', color: '#DC2626' },
    { id: 'feature', name: 'Feature', slug: 'feature', color: '#16A34A' },
    { id: 'enhancement', name: 'Enhancement', slug: 'enhancement', color: '#2563EB' },
    { id: 'docs', name: 'Documentation', slug: 'docs', color: '#8B5CF6' },
  ];

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">Priority Tags (Max 3)</label>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        maxTags={3}
        placeholder="Add up to 3 tags..."
      />
    </div>
  );
}
```

### With Dynamic Search

```tsx
import { useState } from 'react';
import { TagInput, type Tag } from '@/components/ui/tag-input';

export function DynamicSearchExample() {
  const [tags, setTags] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<Tag[]>([]);

  const handleSearch = (query: string) => {
    // Fetch suggestions from API based on query
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }

    // Example: fetch from backend
    fetch(`/api/tags?search=${query}`)
      .then(res => res.json())
      .then(data => setSuggestions(data.tags))
      .catch(err => console.error('Search failed:', err));
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">Search Tags</label>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        onSearch={handleSearch}
        placeholder="Type to search tags..."
      />
    </div>
  );
}
```

### Suggestions Only (No Custom Tags)

```tsx
export function SuggestionsOnlyExample() {
  const [tags, setTags] = useState<string[]>([]);

  const suggestions: Tag[] = [
    { id: 'skill', name: 'Skill', slug: 'skill' },
    { id: 'command', name: 'Command', slug: 'command' },
    { id: 'agent', name: 'Agent', slug: 'agent' },
    { id: 'mcp', name: 'MCP Server', slug: 'mcp' },
  ];

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">Artifact Types</label>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        allowCreate={false}
        placeholder="Select from available types..."
      />
    </div>
  );
}
```

### In a Form

```tsx
import { useState } from 'react';
import { TagInput, type Tag } from '@/components/ui/tag-input';
import { Button } from '@/components/ui/button';

export function FormIntegrationExample() {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    tags: [] as string[],
  });

  const suggestions: Tag[] = [
    { id: 'urgent', name: 'Urgent', slug: 'urgent', color: '#EF4444' },
    { id: 'review', name: 'Needs Review', slug: 'review', color: '#F59E0B' },
    { id: 'approved', name: 'Approved', slug: 'approved', color: '#10B981' },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Form submitted:', formData);
    // Send to API
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">Title</label>
        <input
          type="text"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          className="w-full px-3 py-2 border rounded-md"
          placeholder="Enter title..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Description</label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full px-3 py-2 border rounded-md"
          placeholder="Enter description..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Tags</label>
        <TagInput
          value={formData.tags}
          onChange={(tags) => setFormData({ ...formData, tags })}
          suggestions={suggestions}
          placeholder="Add tags..."
        />
      </div>

      <Button type="submit">Submit</Button>
    </form>
  );
}
```

### CSV Paste Support

```tsx
export function CSVPasteExample() {
  const [tags, setTags] = useState<string[]>([]);

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">Import Tags (CSV)</label>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={[]}
        placeholder="Paste comma-separated tags..."
        allowCreate={true}
      />
      <p className="text-xs text-muted-foreground">
        Try pasting: react, typescript, nextjs, tailwind
      </p>
    </div>
  );
}
```

### Disabled State

```tsx
export function DisabledExample() {
  const tags = ['typescript', 'react'];

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">Read-Only Tags</label>
      <TagInput
        value={tags}
        onChange={() => {}}
        suggestions={[]}
        disabled={true}
        placeholder="Read-only..."
      />
    </div>
  );
}
```

## Keyboard Shortcuts

Full keyboard support for accessibility and power users:

| Key | Action |
|-----|--------|
| <kbd>Enter</kbd> | Add highlighted suggestion or create new tag from typed text |
| <kbd>Backspace</kbd> | Delete last tag when input is empty |
| <kbd>Arrow Down</kbd> | Move highlight down in suggestions dropdown |
| <kbd>Arrow Up</kbd> | Move highlight up in suggestions dropdown |
| <kbd>Escape</kbd> | Close suggestions dropdown and clear highlight |
| <kbd>Tab</kbd> | Move focus to next element (browser default) |
| <kbd>Shift+Tab</kbd> | Move focus to previous element (browser default) |

### Keyboard Example

```
1. Focus the TagInput (click or tab to it)
2. Type "react" to filter suggestions
3. Press Arrow Down to highlight "React"
4. Press Enter to add it
5. Type "type" to search again
6. Press Enter to create custom tag "type"
7. Press Backspace to remove "type" (removes last tag)
8. Press Escape to close suggestions
```

## Accessibility

The TagInput component implements full WCAG 2.1 AA accessibility compliance:

### ARIA Attributes

- **`role="combobox"`** - Input role indicating it opens a dropdown
- **`aria-label="Tag input"`** - Identifies the input for screen readers
- **`aria-expanded`** - Indicates whether suggestions dropdown is open/closed
- **`aria-controls="tag-suggestions"`** - Links input to suggestions list
- **`aria-activedescendant`** - Tracks currently highlighted suggestion
- **`role="listbox"`** - Suggestions container role
- **`role="option"`** - Individual suggestion role
- **`aria-selected`** - Indicates which suggestion is highlighted

### Screen Reader Support

```tsx
// The component announces:
// - "Tag input, combobox, collapsed"
// When typing "react":
// - "Tag input, combobox, expanded"
// When navigating suggestions:
// - "React, option 1 of 3, selected"

// Remove button announces:
// - "Remove tag React"
```

### Keyboard Navigation

All interactions are fully keyboard accessible:

- Navigate suggestions with arrow keys
- Add tags with Enter
- Delete tags with Backspace or by clicking X
- Close dropdown with Escape
- Tab through remove buttons

### Visual Indicators

- Focus state with ring on container
- Highlighted suggestion with accent background
- Disabled state with reduced opacity
- Status message when max tags reached with `aria-live="polite"`

### Example: Accessible Implementation

```tsx
import { TagInput, type Tag } from '@/components/ui/tag-input';
import { useId } from 'react';

export function AccessibleTagInput() {
  const [tags, setTags] = useState<string[]>([]);
  const labelId = useId();

  const suggestions: Tag[] = [
    { id: '1', name: 'React', slug: 'react' },
    { id: '2', name: 'Vue', slug: 'vue' },
  ];

  return (
    <div>
      <label id={labelId} className="block text-sm font-medium mb-2">
        Choose frameworks
        <span className="text-red-500 ml-1" aria-label="required">*</span>
      </label>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        placeholder="Type to add frameworks..."
        // Note: aria-labelledby could be added if using a custom wrapper
      />
      <p className="text-xs text-muted-foreground mt-1">
        Select one or more frameworks. Use arrow keys to navigate, Enter to select.
      </p>
    </div>
  );
}
```

## Styling & Customization

### Default Styling

The component uses Tailwind CSS and integrates with the Badge component:

```tsx
// Container styling
"flex flex-wrap gap-1 p-2 border rounded-md min-h-[42px] bg-background"
"focus-within:ring-1 focus-within:ring-ring focus-within:outline-none"

// Input styling
"flex-1 min-w-[100px] outline-none bg-transparent text-sm"

// Badges
<Badge variant="secondary" colorStyle={tag.color} />

// Suggestions dropdown
"absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-md"
"max-h-[300px] overflow-y-auto"
```

### Custom Styling

```tsx
<TagInput
  value={tags}
  onChange={setTags}
  suggestions={suggestions}
  className="max-w-2xl"  // Add custom classes
/>
```

### Color Customization

Tags support optional hex color values for visual categorization:

```tsx
const suggestions: Tag[] = [
  {
    id: 'priority-high',
    name: 'High Priority',
    slug: 'priority-high',
    color: '#DC2626', // Red - high priority
  },
  {
    id: 'priority-medium',
    name: 'Medium Priority',
    slug: 'priority-medium',
    color: '#F59E0B', // Amber - medium priority
  },
  {
    id: 'priority-low',
    name: 'Low Priority',
    slug: 'priority-low',
    color: '#10B981', // Green - low priority
  },
];
```

## Behavior Details

### Suggestion Filtering

- Shows up to 10 suggestions at a time
- Filters by tag name or slug (case-insensitive)
- Excludes already-selected tags
- Opens dropdown when input has text
- Closes dropdown when clicking outside or pressing Escape

### Adding Tags

- **From suggestions** - Arrow Down, then Enter
- **Custom tags** - Type text and press Enter (if `allowCreate=true`)
- **From paste** - Paste comma-separated values (respects maxTags)
- **From click** - Click a suggestion to add it
- Only adds non-empty, non-duplicate tags

### Removing Tags

- **Click X button** - Remove tag immediately
- **Backspace** - Remove last tag when input is empty
- Focus returns to input after removal

### CSV Paste Behavior

When pasting comma-separated values:
- Values are trimmed (whitespace removed)
- Empty values are skipped
- maxTags limit is respected
- Input is cleared after paste
- Suggestions dropdown closes

### Max Tags Enforcement

When `maxTags` is set:
- Input disables when limit is reached
- Message appears: "Maximum N tags reached"
- Message has `aria-live="polite"` for screen reader notification
- CSV paste respects limit (won't exceed it)

## Common Patterns

### With React Hook Form

```tsx
import { useController } from 'react-hook-form';
import { TagInput, type Tag } from '@/components/ui/tag-input';

interface FormData {
  tags: string[];
}

export function FormWithController({ control }: { control: any }) {
  const { field } = useController({
    control,
    name: 'tags',
    defaultValue: [],
  });

  const suggestions: Tag[] = [
    { id: '1', name: 'React', slug: 'react' },
    { id: '2', name: 'Vue', slug: 'vue' },
  ];

  return (
    <TagInput
      value={field.value}
      onChange={field.onChange}
      suggestions={suggestions}
      placeholder="Select tags..."
    />
  );
}
```

### With Validation

```tsx
export function ValidatedTagInput() {
  const [tags, setTags] = useState<string[]>([]);
  const [error, setError] = useState<string>('');

  const handleChange = (newTags: string[]) => {
    if (newTags.length === 0) {
      setError('At least one tag is required');
    } else if (newTags.length > 5) {
      setError('Maximum 5 tags allowed');
    } else {
      setError('');
    }
    setTags(newTags);
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">Tags (required)</label>
      <TagInput
        value={tags}
        onChange={handleChange}
        suggestions={[
          { id: '1', name: 'Tag 1', slug: 'tag-1' },
          { id: '2', name: 'Tag 2', slug: 'tag-2' },
        ]}
      />
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}
```

## API Integration

### Fetching Suggestions from API

```tsx
import { useEffect, useState } from 'react';
import { TagInput, type Tag } from '@/components/ui/tag-input';

export function APISuggestions() {
  const [tags, setTags] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (query: string) => {
    if (!query) {
      setSuggestions([]);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`/api/tags/search?q=${query}`);
      const data = await response.json();
      setSuggestions(data.tags);
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">Tags</label>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        onSearch={handleSearch}
        placeholder="Search tags..."
      />
      {loading && <p className="text-xs text-muted-foreground">Loading...</p>}
    </div>
  );
}
```

## Performance Considerations

- **Memoization**: Component uses `useMemo` to avoid recomputing filtered suggestions
- **Debouncing**: Consider debouncing `onSearch` callback for API calls
- **Limit suggestions**: Component limits dropdown to 10 suggestions to prevent performance issues
- **Large lists**: Test with 100+ suggestions to ensure acceptable performance

```tsx
// Example: Debounced search
import { useMemo } from 'react';
import debounce from 'lodash/debounce';

const debouncedSearch = useMemo(
  () => debounce((query: string) => {
    // Fetch from API
  }, 300),
  []
);
```

## Best Practices

1. **Always provide tag IDs** - Use tag `id` field for data consistency
2. **Supply name and slug** - Required fields for display and filtering
3. **Include colors when relevant** - Use colors to categorize tags visually
4. **Handle edge cases** - Empty results, network errors, max tags reached
5. **Test keyboard navigation** - Ensure full keyboard support works
6. **Provide helper text** - Guide users on tag selection rules
7. **Clear error states** - Show validation feedback clearly
8. **Debounce search** - Prevent excessive API calls

## Troubleshooting

### Suggestions Not Showing

- Ensure `suggestions` array is populated
- Check that input value is not empty
- Verify tag names/slugs match search query (case-insensitive)
- Check if already-selected tags are being filtered out

### Tags Not Adding

- Check if `allowCreate=false` (prevents custom tags)
- Verify max tags limit hasn't been reached
- Ensure input is not empty or whitespace-only
- Check for duplicate tags in current value

### Accessibility Issues

- Test with screen reader (NVDA, JAWS, VoiceOver)
- Verify keyboard navigation works with arrow keys
- Check ARIA attributes are present and correct
- Test with high contrast mode enabled

## Related Components

- **Badge** - Used to display individual tags
- **Input** - Base input component
- **Select** - Alternative for non-tag selection
- **ComboBox** - Radix UI component underlying the suggestions

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Android)

Fully keyboard and screen reader accessible on all modern browsers.
