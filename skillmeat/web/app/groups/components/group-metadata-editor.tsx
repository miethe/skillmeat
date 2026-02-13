'use client';

import { Book, Check, Folder, Layers, Plus, Sparkles, Tag, Wrench, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState, type ComponentType } from 'react';
import type { ColorResult } from '@uiw/color-convert';
import Sketch from '@uiw/react-color-sketch';
import { TagEditor } from '@/components/shared/tag-editor';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select';
import { cn } from '@/lib/utils';

export const GROUP_COLORS = ['slate', 'blue', 'green', 'amber', 'rose'] as const;
export const GROUP_ICONS = ['layers', 'folder', 'tag', 'sparkles', 'book', 'wrench'] as const;

export type GroupColorToken = (typeof GROUP_COLORS)[number];
export type GroupColor = GroupColorToken | string;
export type GroupIcon = (typeof GROUP_ICONS)[number];

const GROUP_TAG_PATTERN = /^[a-z0-9_-]{1,32}$/;
const GROUP_TAG_LIMIT = 20;
const CUSTOM_COLORS_STORAGE_KEY = 'skillmeat-group-custom-colors-v1';
const MAX_CUSTOM_COLORS = 20;

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
  value: GroupColorToken;
  label: string;
  hex: string;
}> = [
  { value: 'slate', label: 'Slate', hex: '#64748b' },
  { value: 'blue', label: 'Blue', hex: '#3b82f6' },
  { value: 'green', label: 'Green', hex: '#22c55e' },
  { value: 'amber', label: 'Amber', hex: '#f59e0b' },
  { value: 'rose', label: 'Rose', hex: '#f43f5e' },
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

const COLOR_HEX_BY_TOKEN: Record<GroupColorToken, string> = Object.fromEntries(
  COLOR_OPTIONS.map((option) => [option.value, option.hex.toLowerCase()])
) as Record<GroupColorToken, string>;

function isColorToken(value: string): value is GroupColorToken {
  return value in COLOR_HEX_BY_TOKEN;
}

function normalizeHex(value: string): string {
  const hex = value.trim().replace(/^#/, '').toLowerCase();
  if (/^[0-9a-f]{8}$/.test(hex)) {
    return `#${hex.slice(0, 6)}`;
  }
  if (/^[0-9a-f]{3}$/.test(hex)) {
    return `#${hex
      .split('')
      .map((part) => `${part}${part}`)
      .join('')}`;
  }
  if (/^[0-9a-f]{6}$/.test(hex)) {
    return `#${hex}`;
  }
  return COLOR_HEX_BY_TOKEN.slate;
}

function resolveColorHex(value: GroupColor): string {
  if (isColorToken(value)) {
    return COLOR_HEX_BY_TOKEN[value];
  }
  return normalizeHex(value);
}

function dedupeHexColors(values: string[]): string[] {
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const value of values) {
    const next = normalizeHex(value);
    if (seen.has(next)) {
      continue;
    }
    seen.add(next);
    normalized.push(next);
  }
  return normalized;
}

function hexToRgb(hex: string): [number, number, number] {
  const normalized = normalizeHex(hex).replace('#', '');
  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);
  return [r, g, b];
}

function getClosestColorToken(hex: string): GroupColorToken {
  const normalizedHex = normalizeHex(hex);
  const normalizedRgb = hexToRgb(normalizedHex);

  let nearest: GroupColorToken = 'slate';
  let minDistance = Number.POSITIVE_INFINITY;

  for (const option of COLOR_OPTIONS) {
    const [r, g, b] = hexToRgb(option.hex);
    const distance =
      (normalizedRgb[0] - r) ** 2 + (normalizedRgb[1] - g) ** 2 + (normalizedRgb[2] - b) ** 2;
    if (distance < minDistance) {
      nearest = option.value;
      minDistance = distance;
    }
  }

  return nearest;
}

/** Returns true if `hex` exactly matches one of the preset COLOR_OPTIONS hex values. */
function isPresetHex(hex: string): boolean {
  return COLOR_OPTIONS.some((option) => normalizeHex(option.hex) === hex);
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
  const selectedIcon = ICON_OPTIONS.find((option) => option.value === icon) ?? ICON_OPTIONS[0];
  const [customColors, setCustomColors] = useState<string[]>([]);
  const [sketchColor, setSketchColor] = useState('#6366f1');
  const [pickerOpen, setPickerOpen] = useState(false);

  const selectedColorHex = resolveColorHex(color);
  const selectedColorLabel =
    COLOR_OPTIONS.find((option) => option.value === color)?.label ?? 'Custom';

  const persistCustomColors = useCallback((nextColors: string[]) => {
    const sanitized = dedupeHexColors(nextColors).slice(0, MAX_CUSTOM_COLORS);
    setCustomColors(sanitized);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(CUSTOM_COLORS_STORAGE_KEY, JSON.stringify(sanitized));
    }
  }, []);

  // Load custom colors from localStorage on mount.
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      const stored = window.localStorage.getItem(CUSTOM_COLORS_STORAGE_KEY);
      if (!stored) {
        return;
      }
      const parsed = JSON.parse(stored);
      if (!Array.isArray(parsed)) {
        return;
      }
      const sanitized = dedupeHexColors(parsed.filter((entry) => typeof entry === 'string')).slice(
        0,
        MAX_CUSTOM_COLORS
      );
      setCustomColors(sanitized);
    } catch {
      // Ignore malformed localStorage content.
    }
  }, []);

  const canAddCustomColor = customColors.length < MAX_CUSTOM_COLORS;

  /** Handle clicking a preset color token swatch. */
  const handlePresetClick = (option: (typeof COLOR_OPTIONS)[number]) => {
    onColorChange(option.value);
  };

  /** Handle clicking a custom color swatch. */
  const handleCustomClick = (hex: string) => {
    onColorChange(hex);
  };

  /** Handle removing a custom color swatch via right-click / long-press context. */
  const handleRemoveCustomColor = (hex: string) => {
    const filtered = customColors.filter((c) => c !== hex);
    persistCustomColors(filtered);
    // If the removed color was selected, fall back to slate.
    if (!isColorToken(color) && normalizeHex(color) === hex) {
      onColorChange('slate');
    }
  };

  /** Add a color from the Sketch picker to custom colors and select it. */
  const handleAddFromSketch = () => {
    const normalized = normalizeHex(sketchColor);

    // Don't add if it matches a preset token hex.
    if (isPresetHex(normalized)) {
      const token = getClosestColorToken(normalized);
      onColorChange(token);
      setPickerOpen(false);
      return;
    }

    // Add to custom colors if not already present.
    if (!customColors.includes(normalized) && canAddCustomColor) {
      persistCustomColors([...customColors, normalized]);
    }

    onColorChange(normalized);
    setPickerOpen(false);
  };

  /** Check if a given hex or token matches the currently selected color. */
  const isSelected = useMemo(() => {
    return (value: string) => {
      if (isColorToken(value)) {
        return color === value;
      }
      return !isColorToken(color) && normalizeHex(color) === value;
    };
  }, [color]);

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
        <div
          role="group"
          aria-label="Group color picker"
          className={cn(
            'rounded-md border p-3',
            disabled && 'pointer-events-none cursor-not-allowed opacity-60'
          )}
        >
          {/* Swatch grid */}
          <div className="flex flex-wrap gap-1.5">
            {/* Preset color token swatches */}
            {COLOR_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => handlePresetClick(option)}
                disabled={disabled}
                aria-label={`${option.label} color`}
                title={option.label}
                className={cn(
                  'relative flex h-6 w-6 items-center justify-center rounded-full transition-all',
                  isSelected(option.value)
                    ? 'ring-2 ring-primary ring-offset-2 ring-offset-background'
                    : 'hover:scale-110'
                )}
                style={{ backgroundColor: option.hex }}
              >
                {isSelected(option.value) && (
                  <Check className="h-3 w-3 text-white drop-shadow-[0_1px_1px_rgba(0,0,0,0.5)]" />
                )}
              </button>
            ))}

            {/* Custom color swatches */}
            {customColors.map((hex) => (
              <div key={hex} className="group relative">
                <button
                  type="button"
                  onClick={() => handleCustomClick(hex)}
                  disabled={disabled}
                  aria-label={`Custom color ${hex}`}
                  title={hex}
                  className={cn(
                    'relative flex h-6 w-6 items-center justify-center rounded-full border border-border/50 transition-all',
                    isSelected(hex)
                      ? 'ring-2 ring-primary ring-offset-2 ring-offset-background'
                      : 'hover:scale-110'
                  )}
                  style={{ backgroundColor: hex }}
                >
                  {isSelected(hex) && (
                    <Check className="h-3 w-3 text-white drop-shadow-[0_1px_1px_rgba(0,0,0,0.5)]" />
                  )}
                </button>
                {/* Remove button on hover */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveCustomColor(hex);
                  }}
                  disabled={disabled}
                  aria-label={`Remove custom color ${hex}`}
                  className="absolute -right-1 -top-1 hidden h-3.5 w-3.5 items-center justify-center rounded-full bg-destructive text-destructive-foreground shadow-sm group-hover:flex"
                >
                  <X className="h-2.5 w-2.5" />
                </button>
              </div>
            ))}

            {/* Add custom color button */}
            <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  disabled={disabled || !canAddCustomColor}
                  aria-label="Add custom group color"
                  title="Add custom color"
                  className={cn(
                    'flex h-6 w-6 items-center justify-center rounded-full border border-dashed border-muted-foreground/50 text-muted-foreground transition-colors hover:border-primary hover:text-primary',
                    (disabled || !canAddCustomColor) && 'cursor-not-allowed opacity-50'
                  )}
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
              </PopoverTrigger>
              <PopoverContent
                className="w-auto p-3"
                align="start"
                side="bottom"
                sideOffset={8}
              >
                <div className="flex flex-col gap-3">
                  <Sketch
                    color={sketchColor}
                    onChange={(nextColor: ColorResult) => {
                      setSketchColor(nextColor.hex);
                    }}
                    disableAlpha
                    style={{ width: 220 }}
                  />
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleAddFromSketch}
                      className="flex-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                    >
                      Add Color
                    </button>
                    <button
                      type="button"
                      onClick={() => setPickerOpen(false)}
                      className="rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </div>
        <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
          <span
            className="h-3.5 w-3.5 rounded-full border"
            style={{ backgroundColor: selectedColorHex }}
          />
          {selectedColorLabel}
        </div>
      </div>

      <div className="space-y-2">
        <Label>Icon</Label>
        <Select
          value={icon}
          onValueChange={(value) => onIconChange(value as GroupIcon)}
          disabled={disabled}
        >
          <SelectTrigger aria-label="Group icon" className="w-full sm:w-1/2">
            <span className="inline-flex items-center gap-2">
              <selectedIcon.Icon className="h-4 w-4" />
              {selectedIcon.label}
            </span>
          </SelectTrigger>
          <SelectContent>
            {ICON_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                <span className="inline-flex items-center gap-2">
                  <option.Icon className="h-4 w-4" />
                  {option.label}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
