'use client';

import { Check, Plus, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Sketch from '@uiw/react-color-sketch';
import { TagEditor } from '@/components/shared/tag-editor';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select';
import { cn } from '@/lib/utils';
import {
  COLOR_OPTIONS,
  ICON_OPTIONS,
  dedupeHexColors,
  getClosestColorToken,
  isColorToken,
  isPresetHex,
  normalizeHex,
  resolveColorHex,
  type GroupColor,
  type GroupIcon,
} from '@/lib/group-constants';

export type { GroupColor, GroupIcon };

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
  const selectedIcon = ICON_OPTIONS.find((option) => option.value === icon) ?? ICON_OPTIONS[0]!;
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
                    onChange={(nextColor) => {
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
              <selectedIcon.Icon className="h-4 w-4 shrink-0" />
              {selectedIcon.label}
            </span>
          </SelectTrigger>
          <SelectContent>
            {ICON_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                <span className="inline-flex items-center gap-2">
                  <option.Icon className="h-4 w-4 shrink-0" />
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
