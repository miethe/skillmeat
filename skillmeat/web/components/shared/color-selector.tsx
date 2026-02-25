'use client';

import { Check, Plus, X } from 'lucide-react';
import { useState } from 'react';
import Sketch from '@uiw/react-color-sketch';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { PRESET_COLORS, isValidHex } from '@/lib/color-constants';
import { useCustomColors, useCreateCustomColor, useDeleteCustomColor } from '@/hooks';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ColorSelectorProps {
  value: string;
  onChange: (hex: string) => void;
  disabled?: boolean;
  label?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeHex(hex: string): string {
  return hex.trim().toLowerCase();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Shared color selector with preset swatches, custom colors via API,
 * and an inline Sketch color picker for adding new custom colors.
 *
 * Uses `useCustomColors`, `useCreateCustomColor`, and `useDeleteCustomColor`
 * from the hooks barrel to manage server-persisted custom colors.
 */
export function ColorSelector({ value, onChange, disabled = false, label }: ColorSelectorProps) {
  const { data: customColors, isLoading: isLoadingColors } = useCustomColors();
  const createColor = useCreateCustomColor();
  const deleteColor = useDeleteCustomColor();

  const [sketchColor, setSketchColor] = useState('#6366f1');
  const [pickerOpen, setPickerOpen] = useState(false);

  const normalizedValue = normalizeHex(value);

  const isSelected = (hex: string) => normalizeHex(hex) === normalizedValue;

  const handleAddFromSketch = async () => {
    const normalized = normalizeHex(sketchColor);
    if (!isValidHex(normalized)) {
      return;
    }

    // Select and close immediately for responsiveness; persist in background.
    onChange(normalized);
    setPickerOpen(false);

    try {
      await createColor.mutateAsync({ hex: normalized });
    } catch {
      // Non-fatal — the color is still selected locally even if persistence fails.
    }
  };

  const handleDeleteCustomColor = async (id: string, hex: string) => {
    try {
      await deleteColor.mutateAsync(id);
      // If deleted color was selected, revert to first preset.
      if (isSelected(hex)) {
        onChange(PRESET_COLORS[0]!.hex);
      }
    } catch {
      // Non-fatal — surface via toast in a future iteration.
    }
  };

  return (
    <div className="space-y-2">
      {label && <Label>{label}</Label>}

      <div
        role="group"
        aria-label={label ? `${label} color picker` : 'Color picker'}
        className={cn(
          'rounded-md border p-3',
          disabled && 'pointer-events-none cursor-not-allowed opacity-60'
        )}
      >
        <div className="flex flex-wrap gap-1.5">
          {/* Preset swatches */}
          {PRESET_COLORS.map((option) => (
            <button
              key={option.hex}
              type="button"
              onClick={() => onChange(option.hex)}
              disabled={disabled}
              aria-label={option.name ? `${option.name} color` : option.hex}
              aria-pressed={isSelected(option.hex)}
              title={option.name ?? option.hex}
              className={cn(
                'relative flex h-6 w-6 items-center justify-center rounded-full transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                isSelected(option.hex)
                  ? 'ring-2 ring-primary ring-offset-2 ring-offset-background'
                  : 'hover:scale-110'
              )}
              style={{ backgroundColor: option.hex }}
            >
              {isSelected(option.hex) && (
                <Check className="h-3 w-3 text-white drop-shadow-[0_1px_1px_rgba(0,0,0,0.5)]" />
              )}
            </button>
          ))}

          {/* Custom color swatches */}
          {isLoadingColors
            ? Array.from({ length: 2 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-6 rounded-full" />
              ))
            : customColors?.map((colorEntry) => (
                <div key={colorEntry.id} className="group relative">
                  <button
                    type="button"
                    onClick={() => onChange(colorEntry.hex)}
                    disabled={disabled}
                    aria-label={colorEntry.name ? `${colorEntry.name} color` : `Custom color ${colorEntry.hex}`}
                    aria-pressed={isSelected(colorEntry.hex)}
                    title={colorEntry.name ?? colorEntry.hex}
                    className={cn(
                      'relative flex h-6 w-6 items-center justify-center rounded-full border border-border/50 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                      isSelected(colorEntry.hex)
                        ? 'ring-2 ring-primary ring-offset-2 ring-offset-background'
                        : 'hover:scale-110'
                    )}
                    style={{ backgroundColor: colorEntry.hex }}
                  >
                    {isSelected(colorEntry.hex) && (
                      <Check className="h-3 w-3 text-white drop-shadow-[0_1px_1px_rgba(0,0,0,0.5)]" />
                    )}
                  </button>

                  {/* Delete on hover */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteCustomColor(colorEntry.id, colorEntry.hex);
                    }}
                    disabled={disabled}
                    aria-label={`Remove custom color ${colorEntry.hex}`}
                    className="absolute -right-1 -top-1 hidden h-3.5 w-3.5 items-center justify-center rounded-full bg-destructive text-destructive-foreground shadow-sm group-hover:flex focus-visible:flex focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <X className="h-2.5 w-2.5" />
                  </button>
                </div>
              ))}

          {/* Add custom color */}
          <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
            <PopoverTrigger asChild>
              <button
                type="button"
                disabled={disabled}
                aria-label="Add custom color"
                title="Add custom color"
                className={cn(
                  'flex h-6 w-6 items-center justify-center rounded-full border border-dashed border-muted-foreground/50 text-muted-foreground transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                  disabled && 'cursor-not-allowed opacity-50'
                )}
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-3" align="start" side="bottom" sideOffset={8}>
              <div className="flex flex-col gap-3">
                <Sketch
                  color={sketchColor}
                  onChange={(nextColor) => setSketchColor(nextColor.hex)}
                  disableAlpha
                  style={{ width: 220 }}
                />
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleAddFromSketch}
                    disabled={createColor.isPending}
                    className="flex-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {createColor.isPending ? 'Saving…' : 'Add Color'}
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

        {/* Selected color preview */}
        {value && (
          <div className="mt-2 inline-flex items-center gap-2 text-xs text-muted-foreground">
            <span
              className="h-3.5 w-3.5 rounded-full border"
              style={{ backgroundColor: value }}
              aria-hidden="true"
            />
            {PRESET_COLORS.find((c) => normalizeHex(c.hex) === normalizedValue)?.name ??
              customColors?.find((c) => normalizeHex(c.hex) === normalizedValue)?.name ??
              value}
          </div>
        )}
      </div>
    </div>
  );
}
