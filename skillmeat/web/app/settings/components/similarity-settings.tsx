'use client';

import * as React from 'react';
import { useSimilaritySettings } from '@/hooks';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import type { SimilarityThresholds, SimilarityColors } from '@/types/similarity';

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function SimilaritySettingsSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading similarity settings">
      <div className="space-y-4">
        <Skeleton className="h-5 w-40" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-3 w-3/4" />
          </div>
        ))}
      </div>
      <Skeleton className="h-px w-full" />
      <div className="space-y-4">
        <Skeleton className="h-5 w-36" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4">
            <Skeleton className="h-9 w-9 rounded-md" />
            <Skeleton className="h-4 w-28" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Threshold slider row
// ---------------------------------------------------------------------------

interface ThresholdSliderProps {
  id: string;
  label: string;
  value: number;
  helpText: string;
  onChange: (value: number) => void;
  disabled?: boolean;
}

function ThresholdSlider({
  id,
  label,
  value,
  helpText,
  onChange,
  disabled = false,
}: ThresholdSliderProps) {
  const displayValue = value.toFixed(2);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(parseFloat(e.target.value));
  };

  // Map 0–1 to a percentage for the track fill
  const fillPercent = `${(value * 100).toFixed(1)}%`;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor={id} className="text-sm font-medium">
          {label}
        </Label>
        <span
          className="tabular-nums font-mono text-sm font-semibold text-foreground"
          aria-live="polite"
          aria-label={`${label} value: ${displayValue}`}
        >
          {displayValue}
        </span>
      </div>

      {/* Native range input with custom track styling via CSS custom properties */}
      <div className="relative">
        <input
          id={id}
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          aria-label={label}
          aria-valuemin={0}
          aria-valuemax={1}
          aria-valuenow={value}
          aria-valuetext={displayValue}
          style={
            {
              '--fill': fillPercent,
            } as React.CSSProperties
          }
          className={cn(
            'h-1.5 w-full cursor-pointer appearance-none rounded-full',
            'bg-muted',
            // WebKit track fill via CSS gradient trick
            '[&::-webkit-slider-runnable-track]:h-1.5 [&::-webkit-slider-runnable-track]:rounded-full',
            '[&::-webkit-slider-thumb]:mt-[-3px] [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4',
            '[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full',
            '[&::-webkit-slider-thumb]:border [&::-webkit-slider-thumb]:border-border',
            '[&::-webkit-slider-thumb]:bg-background [&::-webkit-slider-thumb]:shadow-sm',
            '[&::-webkit-slider-thumb]:ring-offset-background',
            '[&::-webkit-slider-thumb]:transition-colors',
            '[&::-webkit-slider-thumb]:hover:border-primary',
            '[&::-webkit-slider-thumb]:focus-visible:outline-none [&::-webkit-slider-thumb]:focus-visible:ring-2',
            '[&::-webkit-slider-thumb]:focus-visible:ring-ring [&::-webkit-slider-thumb]:focus-visible:ring-offset-2',
            // Moz
            '[&::-moz-range-track]:h-1.5 [&::-moz-range-track]:rounded-full [&::-moz-range-track]:bg-muted',
            '[&::-moz-range-progress]:h-1.5 [&::-moz-range-progress]:rounded-full [&::-moz-range-progress]:bg-primary',
            '[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full',
            '[&::-moz-range-thumb]:border [&::-moz-range-thumb]:border-border [&::-moz-range-thumb]:bg-background',
            disabled && 'cursor-not-allowed opacity-50'
          )}
        />
        {/* WebKit progress fill overlay (gradient from left to thumb position) */}
        <div
          className="pointer-events-none absolute inset-y-0 left-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-primary transition-all"
          style={{ width: fillPercent }}
          aria-hidden="true"
        />
      </div>

      <p className="text-xs text-muted-foreground">{helpText}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Color picker row
// ---------------------------------------------------------------------------

interface ColorPickerRowProps {
  id: string;
  label: string;
  value: string;
  helpText: string;
  onChange: (color: string) => void;
  disabled?: boolean;
}

function ColorPickerRow({
  id,
  label,
  value,
  helpText,
  onChange,
  disabled = false,
}: ColorPickerRowProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };

  return (
    <div className="flex items-start gap-4">
      {/* Color swatch + native color input */}
      <div className="relative mt-0.5 shrink-0">
        <div
          className="h-9 w-9 rounded-md border border-border shadow-sm transition-shadow hover:shadow"
          style={{ backgroundColor: value }}
          aria-hidden="true"
        />
        <input
          id={id}
          type="color"
          value={value}
          onChange={handleChange}
          disabled={disabled}
          aria-label={label}
          // Position the native picker over the swatch, fully transparent so the
          // colored div shows through.  Cursor pointer makes it feel clickable.
          className={cn(
            'absolute inset-0 h-full w-full cursor-pointer rounded-md opacity-0',
            disabled && 'cursor-not-allowed'
          )}
          title={`Pick a color for ${label}`}
        />
      </div>

      {/* Label + hex + help text */}
      <div className="min-w-0 flex-1 space-y-0.5">
        <Label htmlFor={id} className="text-sm font-medium">
          {label}
        </Label>
        <p
          className="font-mono text-xs text-muted-foreground"
          aria-label={`Current color: ${value}`}
        >
          {value.toUpperCase()}
        </p>
        <p className="text-xs text-muted-foreground">{helpText}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section heading
// ---------------------------------------------------------------------------

interface SectionHeadingProps {
  title: string;
  description: string;
}

function SectionHeading({ title, description }: SectionHeadingProps) {
  return (
    <div className="space-y-0.5">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Save button row with pending / saved feedback
// ---------------------------------------------------------------------------

interface SaveRowProps {
  isSaving: boolean;
  onSave: () => void;
  isDirty: boolean;
}

function SaveRow({ isSaving, onSave, isDirty }: SaveRowProps) {
  return (
    <div className="flex items-center justify-end gap-3 pt-2">
      {!isDirty && !isSaving && (
        <span className="text-xs text-muted-foreground" role="status">
          All changes saved
        </span>
      )}
      <Button
        size="sm"
        onClick={onSave}
        disabled={!isDirty || isSaving}
        aria-label="Save similarity settings"
      >
        {isSaving ? 'Saving…' : 'Save Changes'}
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Threshold meta: label, description per key
// ---------------------------------------------------------------------------

const THRESHOLD_META: Record<
  keyof SimilarityThresholds,
  { label: string; help: string }
> = {
  high: {
    label: 'High match',
    help:
      'Artifacts scoring at or above this value are flagged as near-duplicates. ' +
      'Lowering this broadens the "high" band.',
  },
  partial: {
    label: 'Partial match',
    help:
      'Scores between "partial" and "high" indicate meaningful overlap. ' +
      'Good candidates for consolidation or tagging.',
  },
  low: {
    label: 'Low match',
    help:
      'Scores between "low" and "partial" share some concepts. ' +
      'Useful as related-artifacts references.',
  },
  floor: {
    label: 'Visibility floor',
    help:
      'Results below this score are hidden entirely. ' +
      'Raise the floor to suppress weak matches from appearing.',
  },
};

const THRESHOLD_ORDER: (keyof SimilarityThresholds)[] = [
  'high',
  'partial',
  'low',
  'floor',
];

// ---------------------------------------------------------------------------
// Color meta
// ---------------------------------------------------------------------------

const COLOR_META: Record<
  keyof SimilarityColors,
  { label: string; help: string }
> = {
  high: {
    label: 'High match color',
    help: 'Badge color for artifacts in the "high" similarity band.',
  },
  partial: {
    label: 'Partial match color',
    help: 'Badge color for artifacts in the "partial" similarity band.',
  },
  low: {
    label: 'Low match color',
    help: 'Badge color for artifacts in the "low" similarity band.',
  },
};

const COLOR_ORDER: (keyof SimilarityColors)[] = ['high', 'partial', 'low'];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * SimilaritySettings — threshold sliders and band-color pickers for the
 * Similar Artifacts feature.
 *
 * Rendered as a sub-tab under Settings > Appearance.
 *
 * All mutations are applied optimistically via `useSimilaritySettings()`.
 * A "Save Changes" button batches the local edits into a single PUT to
 * avoid firing a request on every slider tick.
 */
export function SimilaritySettings() {
  const {
    thresholds,
    colors,
    isLoading,
    updateThresholds,
    updateColors,
    isUpdatingThresholds,
    isUpdatingColors,
  } = useSimilaritySettings();

  // Local draft state — user edits are staged here before saving
  const [draftThresholds, setDraftThresholds] = React.useState<SimilarityThresholds | null>(null);
  const [draftColors, setDraftColors] = React.useState<SimilarityColors | null>(null);

  // Sync draft to server state on initial load (or after a successful save resets it)
  const prevThresholds = React.useRef(thresholds);
  const prevColors = React.useRef(colors);

  React.useEffect(() => {
    if (
      !draftThresholds ||
      JSON.stringify(thresholds) !== JSON.stringify(prevThresholds.current)
    ) {
      setDraftThresholds(thresholds);
      prevThresholds.current = thresholds;
    }
  }, [thresholds, draftThresholds]);

  React.useEffect(() => {
    if (
      !draftColors ||
      JSON.stringify(colors) !== JSON.stringify(prevColors.current)
    ) {
      setDraftColors(colors);
      prevColors.current = colors;
    }
  }, [colors, draftColors]);

  const effectiveThresholds = draftThresholds ?? thresholds;
  const effectiveColors = draftColors ?? colors;

  // Dirty checks
  const thresholdsDirty =
    JSON.stringify(effectiveThresholds) !== JSON.stringify(thresholds);
  const colorsDirty =
    JSON.stringify(effectiveColors) !== JSON.stringify(colors);
  const isDirty = thresholdsDirty || colorsDirty;

  const isSaving = isUpdatingThresholds || isUpdatingColors;

  const handleThresholdChange = (key: keyof SimilarityThresholds, value: number) => {
    setDraftThresholds((prev) => ({
      ...(prev ?? thresholds),
      [key]: value,
    }));
  };

  const handleColorChange = (key: keyof SimilarityColors, value: string) => {
    setDraftColors((prev) => ({
      ...(prev ?? colors),
      [key]: value,
    }));
  };

  const handleSave = async () => {
    const saves: Promise<void>[] = [];

    if (thresholdsDirty) {
      saves.push(updateThresholds(effectiveThresholds));
    }
    if (colorsDirty) {
      saves.push(updateColors(effectiveColors));
    }

    if (saves.length > 0) {
      await Promise.all(saves);
      // After successful save, reset dirty state by aligning draft to new server values
      setDraftThresholds(null);
      setDraftColors(null);
    }
  };

  if (isLoading) {
    return <SimilaritySettingsSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* ── Threshold section ─────────────────────────────────────── */}
      <section aria-labelledby="similarity-thresholds-heading">
        <SectionHeading
          title="Score thresholds"
          description="Control which similarity scores are surfaced and how they are classified into match bands."
        />

        <div className="mt-4 space-y-5" id="similarity-thresholds-heading" role="group" aria-label="Score thresholds">
          {THRESHOLD_ORDER.map((key) => (
            <ThresholdSlider
              key={key}
              id={`threshold-${key}`}
              label={THRESHOLD_META[key].label}
              value={effectiveThresholds[key]}
              helpText={THRESHOLD_META[key].help}
              onChange={(v) => handleThresholdChange(key, v)}
              disabled={isSaving}
            />
          ))}
        </div>
      </section>

      <Separator />

      {/* ── Color section ─────────────────────────────────────────── */}
      <section aria-labelledby="similarity-colors-heading">
        <SectionHeading
          title="Band colors"
          description="Choose the badge colors used to represent each similarity band in the Similar Artifacts tab."
        />

        <div
          className="mt-4 space-y-4"
          id="similarity-colors-heading"
          role="group"
          aria-label="Band colors"
        >
          {COLOR_ORDER.map((key) => (
            <ColorPickerRow
              key={key}
              id={`color-${key}`}
              label={COLOR_META[key].label}
              value={effectiveColors[key]}
              helpText={COLOR_META[key].help}
              onChange={(v) => handleColorChange(key, v)}
              disabled={isSaving}
            />
          ))}
        </div>
      </section>

      <Separator />

      {/* ── Save ──────────────────────────────────────────────────── */}
      <SaveRow isSaving={isSaving} onSave={() => void handleSave()} isDirty={isDirty} />
    </div>
  );
}
