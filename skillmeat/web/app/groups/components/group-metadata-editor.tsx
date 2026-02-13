'use client';

import { Book, Folder, Layers, Plus, Sparkles, Tag, Wrench } from 'lucide-react';
import { useEffect, useMemo, useState, type ComponentType } from 'react';
import type { ColorResult } from '@uiw/color-convert';
import Compact from '@uiw/react-color-compact';
import { TagEditor } from '@/components/shared/tag-editor';
import { Label } from '@/components/ui/label';
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
const DEFAULT_CUSTOM_COLOR_HEX = '#ffffff';

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

  const selectedColorHex = resolveColorHex(color);
  const selectedColorLabel =
    COLOR_OPTIONS.find((option) => option.value === color)?.label ?? 'Custom';

  const persistCustomColors = (nextColors: string[]) => {
    const sanitized = dedupeHexColors(nextColors).slice(0, MAX_CUSTOM_COLORS);
    setCustomColors(sanitized);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(CUSTOM_COLORS_STORAGE_KEY, JSON.stringify(sanitized));
    }
  };

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

  useEffect(() => {
    if (isColorToken(color)) {
      return;
    }
    const normalized = normalizeHex(color);
    if (customColors.includes(normalized)) {
      return;
    }
    persistCustomColors([...customColors, normalized]);
  }, [color, customColors]);

  const swatchColors = useMemo(
    () => [...COLOR_OPTIONS.map((option) => option.hex), ...customColors],
    [customColors]
  );
  const canAddCustomColor = customColors.length < MAX_CUSTOM_COLORS;

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
            'rounded-md border p-2',
            disabled && 'pointer-events-none cursor-not-allowed opacity-60'
          )}
        >
          <Compact
            prefixCls="group-color-compact"
            color={selectedColorHex}
            colors={swatchColors}
            onChange={(nextColor: ColorResult) => {
              const nextHex = normalizeHex(nextColor.hex);
              const nextToken = getClosestColorToken(nextHex);
              const isPresetHex = COLOR_OPTIONS.some(
                (option) => normalizeHex(option.hex) === nextHex
              );

              if (isColorToken(color)) {
                if (!isPresetHex && !customColors.includes(nextHex)) {
                  persistCustomColors([...customColors, nextHex]);
                }
              } else {
                const currentHex = normalizeHex(color);
                if (customColors.includes(currentHex)) {
                  if (isPresetHex) {
                    persistCustomColors(customColors.filter((entry) => entry !== currentHex));
                  } else if (currentHex !== nextHex) {
                    const replaced = customColors.map((entry) =>
                      entry === currentHex ? nextHex : entry
                    );
                    persistCustomColors(replaced);
                  }
                } else if (!isPresetHex && !customColors.includes(nextHex)) {
                  persistCustomColors([...customColors, nextHex]);
                }
              }

              onColorChange(isPresetHex ? nextToken : nextHex);
            }}
            style={{
              width: 240,
              maxWidth: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              backgroundColor: 'transparent',
              padding: 0,
            }}
            addonAfter={
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  if (!canAddCustomColor) {
                    return;
                  }

                  const nextColors = customColors.includes(DEFAULT_CUSTOM_COLOR_HEX)
                    ? customColors
                    : [...customColors, DEFAULT_CUSTOM_COLOR_HEX];
                  persistCustomColors(nextColors);
                  onColorChange(DEFAULT_CUSTOM_COLOR_HEX);
                }}
                disabled={disabled || !canAddCustomColor}
                aria-label="Add custom group color"
                className={cn(
                  'flex h-[22px] w-[22px] items-center justify-center rounded-md border border-dashed text-muted-foreground transition-colors hover:border-primary hover:text-primary',
                  (disabled || !canAddCustomColor) && 'cursor-not-allowed opacity-50'
                )}
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
            }
            rectProps={{
              style: {
                width: 22,
                height: 22,
                borderRadius: 6,
              },
            }}
          />
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

      <style jsx global>{`
        .group-color-compact-input-wrapper {
          width: 100%;
          margin: 0 !important;
          display: flex !important;
          flex-direction: column !important;
          gap: 8px;
        }

        .group-color-compact-input-wrapper > * {
          width: 100%;
        }
      `}</style>
    </div>
  );
}
