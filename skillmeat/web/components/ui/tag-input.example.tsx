/**
 * TagInput Component - Usage Examples
 *
 * This file demonstrates how to use the TagInput component in different scenarios.
 * Copy the examples below into your components as needed.
 */

'use client';

import { useState } from 'react';
import { TagInput, type Tag } from '@/components/ui/tag-input';

// Example 1: Basic usage with static suggestions
export function BasicTagInputExample() {
  const [tags, setTags] = useState<string[]>([]);

  const suggestions: Tag[] = [
    { id: '1', name: 'React', slug: 'react', color: '#61DAFB' },
    { id: '2', name: 'TypeScript', slug: 'typescript', color: '#3178C6' },
    { id: '3', name: 'Next.js', slug: 'nextjs', color: '#000000' },
    { id: '4', name: 'Tailwind', slug: 'tailwind', color: '#06B6D4' },
  ];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Basic Tag Input</h3>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        placeholder="Type to search tags..."
        allowCreate={true}
      />
      <div className="text-sm text-muted-foreground">
        Selected tags: {tags.length > 0 ? tags.join(', ') : 'None'}
      </div>
    </div>
  );
}

// Example 2: With max tags limit
export function MaxTagsExample() {
  const [tags, setTags] = useState<string[]>([]);

  const suggestions: Tag[] = [
    { id: 'skill', name: 'Skill', slug: 'skill' },
    { id: 'command', name: 'Command', slug: 'command' },
    { id: 'agent', name: 'Agent', slug: 'agent' },
    { id: 'mcp', name: 'MCP Server', slug: 'mcp' },
  ];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Max 3 Tags</h3>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        placeholder="Add up to 3 tags..."
        maxTags={3}
      />
    </div>
  );
}

// Example 3: With search callback (for dynamic suggestions)
export function SearchableTagInputExample() {
  const [tags, setTags] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<Tag[]>([]);

  const handleSearch = (query: string) => {
    // Simulate API call to fetch suggestions
    console.log('Searching for:', query);

    // In a real app, you would fetch from an API
    const mockResults: Tag[] = [
      { id: '1', name: 'Frontend', slug: 'frontend', color: '#FF5733' },
      { id: '2', name: 'Backend', slug: 'backend', color: '#33FF57' },
      { id: '3', name: 'Full Stack', slug: 'full-stack', color: '#3357FF' },
    ].filter((tag) => tag.name.toLowerCase().includes(query.toLowerCase()));

    setSuggestions(mockResults);
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Dynamic Search</h3>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        onSearch={handleSearch}
        placeholder="Search tags..."
      />
    </div>
  );
}

// Example 4: Disabled state
export function DisabledTagInputExample() {
  const [tags] = useState<string[]>(['React', 'TypeScript']);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Disabled Tag Input</h3>
      <TagInput
        value={tags}
        onChange={() => {}}
        suggestions={[]}
        placeholder="Disabled..."
        disabled={true}
      />
    </div>
  );
}

// Example 5: Without create new tags (suggestions only)
export function SuggestionsOnlyExample() {
  const [tags, setTags] = useState<string[]>([]);

  const suggestions: Tag[] = [
    { id: 'bug', name: 'Bug', slug: 'bug', color: '#DC2626' },
    { id: 'feature', name: 'Feature', slug: 'feature', color: '#16A34A' },
    { id: 'docs', name: 'Documentation', slug: 'docs', color: '#2563EB' },
  ];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Suggestions Only (No Custom Tags)</h3>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={suggestions}
        placeholder="Select from suggestions..."
        allowCreate={false}
      />
    </div>
  );
}

// Example 6: Form integration
export function FormExample() {
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
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-lg font-semibold">Form Integration</h3>

      <div>
        <label className="mb-1 block text-sm font-medium">Title</label>
        <input
          type="text"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          className="w-full rounded-md border px-3 py-2"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Tags</label>
        <TagInput
          value={formData.tags}
          onChange={(tags) => setFormData({ ...formData, tags })}
          suggestions={suggestions}
          placeholder="Add tags..."
        />
      </div>

      <button
        type="submit"
        className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
      >
        Submit
      </button>
    </form>
  );
}

// Example 7: CSV paste support
export function CSVPasteExample() {
  const [tags, setTags] = useState<string[]>([]);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">CSV Paste Support</h3>
      <p className="text-sm text-muted-foreground">
        Try pasting: "tag1, tag2, tag3" or copy-paste from Excel/CSV
      </p>
      <TagInput
        value={tags}
        onChange={setTags}
        suggestions={[]}
        placeholder="Paste CSV tags here..."
        allowCreate={true}
      />
    </div>
  );
}
