'use client';

import { Book, Check, Folder, Layers, Sparkles, Tag, Wrench } from 'lucide-react';
import type { ComponentType } from 'react';
import { TagEditor } from '@/components/shared/tag-editor';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export const GROUP_COLORS = ['slate', 'blue', 'green', 'amber', 'rose'] as const;
export const GROUP_ICONS = ['layers', 'folder', 'tag', 'sparkles', 'book', 'wrench'] as const;

export type GroupColor = (typeof GROUP_COLORS)[number];
export type GroupIcon = (typeof GROUP_ICONS)[number];

const GROUP_TAG_PATTERN = /^[a-z0-9_-]{1,32}$/;
const GROUP_TAG_LIMIT = 20;

export interface SanitizedGroupTagsResult {
  tags: string[];
  invalidTags: string[];
  truncated: boolean;
}

export function sanitizeGroupTags(values: string[]): SanitizedGroupTagsResult {
  const tags: string[] = [];
  const invalidTags: string[] = [];
  const seen = new Set<string>();
  let truncated = false;

  for (const rawValue of values) {
    const normalized = rawValue.trim().toLowerCase();

    if (!normalized) {
      continue;
    }

    if (!GROUP_TAG_PATTERN.test(normalized)) {
      invalidTags.push(rawValue);
      continue;
    }

    if (seen.has(normalized)) {
      continue;
    }

    if (tags.length >= GROUP_TAG_LIMIT) {
      truncated = true;
      continue;
    }

    seen.add(normalized);
    tags.push(normalized);
  }

  return { tags, invalidTags, truncated };
}

const COLOR_OPTIONS: Array<{
  value: GroupColor;
  label: string;
  swatchClassName: string;
}> = [
  { value: 'slate', label: 'Slate', swatchClassName: 'bg-slate-500 border-slate-600' },
  { value: 'blue', label: 'Blue', swatchClassName: 'bg-blue-500 border-blue-600' },
  { value: 'green', label: 'Green', swatchClassName: 'bg-green-500 border-green-600' },
  { value: 'amber', label: 'Amber', swatchClassName: 'bg-amber-500 border-amber-600' },
  { value: 'rose', label: 'Rose', swatchClassName: 'bg-rose-500 border-rose-600' },
];

const ICON_OPTIONS: Array<{
  value: GroupIcon;
  label: string;
  Icon: ComponentType<{ className?: string }>;
}> = [
  { value: 'layers', label: 'Layers', Icon: Layers },
  { value: 'folder', label: 'Folder', Icon: Folder },
  { value: 'tag', label: 'Tag', Icon: Tag },
  { value: 'sparkles', label: 'Sparkles', Icon: Sparkles },
  { value: 'book', label: 'Book', Icon: Book },
  { value: 'wrench', label: 'Wrench', Icon: Wrench },
];

interface GroupMetadataEditorProps {
  tags: string[];
  onTagsChange: (tags: string[]) => void;
  color: GroupColor;
  onColorChange: (color: GroupColor) => void;
  icon: GroupIcon;
  onIconChange: (icon: GroupIcon) => void;
  availableTags?: string[];
  disabled?: boolean;
  className?: string;
}

export function GroupMetadataEditor({
  tags,
  onTagsChange,
  color,
  onColorChange,
  icon,
  onIconChange,
  availableTags = [],
  disabled = false,
  className,
}: GroupMetadataEditorProps) {
  return (
    <div className={cn('space-y-5', className)}>
      <div className="space-y-2">
        <Label>Tags</Label>
        <TagEditor
          tags={tags}
          onTagsChange={onTagsChange}
          availableTags={availableTags}
          isLoading={disabled}
          disabled={disabled}
        />
        <p className="text-xs text-muted-foreground">
          Up to 20 tags. Use lowercase letters, numbers, hyphen, or underscore.
        </p>
      </div>

      <div className="space-y-2">
        <Label>Color</Label>
        <div className="flex flex-wrap gap-2">
          {COLOR_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onColorChange(option.value)}
              disabled={disabled}
              className={cn(
                'inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm transition-colors',
                color === option.value
                  ? 'border-primary bg-primary/10 text-foreground'
                  : 'border-border hover:bg-muted/60',
                disabled && 'cursor-not-allowed opacity-60'
              )}
              aria-pressed={color === option.value}
              aria-label={`Set group color to ${option.label}`}
            >
              <span className={cn('h-3.5 w-3.5 rounded-full border', option.swatchClassName)} />
              <span>{option.label}</span>
              {color === option.value && <Check className="h-3.5 w-3.5" />}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label>Icon</Label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {ICON_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onIconChange(option.value)}
              disabled={disabled}
              className={cn(
                'inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm transition-colors',
                icon === option.value
                  ? 'border-primary bg-primary/10 text-foreground'
                  : 'border-border hover:bg-muted/60',
                disabled && 'cursor-not-allowed opacity-60'
              )}
              aria-pressed={icon === option.value}
              aria-label={`Set group icon to ${option.label}`}
            >
              <option.Icon className="h-4 w-4" />
              <span>{option.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
