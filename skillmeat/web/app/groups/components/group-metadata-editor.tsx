'use client';

import { TagEditor } from '@/components/shared/tag-editor';
import { ColorSelector } from '@/components/shared/color-selector';
import { IconPicker } from '@/components/shared/icon-picker';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import {
  getClosestColorToken,
  isPresetHex,
  normalizeHex,
  resolveColorHex,
  type GroupColor,
  type GroupIcon,
} from '@/lib/group-constants';

export type { GroupColor, GroupIcon };

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
  /**
   * Bridge: ColorSelector works with hex strings; GroupColor may be a token
   * name ('slate', 'blue', …) or a hex string. Resolve to hex for the picker
   * and map back to the closest token when the user picks a preset hex.
   */
  const colorHex = resolveColorHex(color);

  const handleColorChange = (hex: string) => {
    const normalized = normalizeHex(hex);
    if (isPresetHex(normalized)) {
      onColorChange(getClosestColorToken(normalized));
    } else {
      onColorChange(normalized);
    }
  };

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

      <ColorSelector
        value={colorHex}
        onChange={handleColorChange}
        disabled={disabled}
        label="Color"
      />

      <div className="space-y-2">
        <Label>Icon</Label>
        <IconPicker
          value={icon}
          onChange={(iconName) => onIconChange(iconName as GroupIcon)}
          disabled={disabled}
        />
      </div>
    </div>
  );
}
