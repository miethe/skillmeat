'use client';

import * as React from 'react';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export interface ConfidenceFilterProps {
  minConfidence: number;
  maxConfidence: number;
  includeBelowThreshold: boolean;
  onMinChange: (value: number) => void;
  onMaxChange: (value: number) => void;
  onIncludeBelowThresholdChange: (value: boolean) => void;
  className?: string;
}

/**
 * Filter component for confidence score range filtering.
 *
 * Allows users to filter artifacts by confidence score (0-100) with:
 * - Min/max range inputs (debounced to reduce API calls)
 * - Toggle for including low-confidence artifacts (below 30% threshold)
 */
export function ConfidenceFilter({
  minConfidence,
  maxConfidence,
  includeBelowThreshold,
  onMinChange,
  onMaxChange,
  onIncludeBelowThresholdChange,
  className,
}: ConfidenceFilterProps) {
  // Local state for input values (for debouncing)
  const [localMin, setLocalMin] = React.useState(minConfidence);
  const [localMax, setLocalMax] = React.useState(maxConfidence);

  // Update local state when props change (e.g., clear filters)
  React.useEffect(() => {
    setLocalMin(minConfidence);
  }, [minConfidence]);

  React.useEffect(() => {
    setLocalMax(maxConfidence);
  }, [maxConfidence]);

  // Debounce callbacks
  const debounceTimerMin = React.useRef<NodeJS.Timeout>();
  const debounceTimerMax = React.useRef<NodeJS.Timeout>();

  const handleMinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0 && value <= 100) {
      setLocalMin(value);

      // Debounce API call
      if (debounceTimerMin.current) {
        clearTimeout(debounceTimerMin.current);
      }
      debounceTimerMin.current = setTimeout(() => {
        onMinChange(value);
      }, 300);
    }
  };

  const handleMaxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0 && value <= 100) {
      setLocalMax(value);

      // Debounce API call
      if (debounceTimerMax.current) {
        clearTimeout(debounceTimerMax.current);
      }
      debounceTimerMax.current = setTimeout(() => {
        onMaxChange(value);
      }, 300);
    }
  };

  // Cleanup timers on unmount
  React.useEffect(() => {
    return () => {
      if (debounceTimerMin.current) clearTimeout(debounceTimerMin.current);
      if (debounceTimerMax.current) clearTimeout(debounceTimerMax.current);
    };
  }, []);

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Range Inputs */}
      <div className="flex items-center gap-2">
        <Label htmlFor="min-confidence" className="text-sm font-medium">
          Confidence:
        </Label>
        <div className="flex items-center gap-2">
          <Input
            id="min-confidence"
            type="number"
            min={0}
            max={100}
            value={localMin}
            onChange={handleMinChange}
            className="w-20 text-sm"
            aria-label="Minimum confidence score"
            aria-describedby="confidence-help"
          />
          <span className="text-sm text-muted-foreground">to</span>
          <Input
            id="max-confidence"
            type="number"
            min={0}
            max={100}
            value={localMax}
            onChange={handleMaxChange}
            className="w-20 text-sm"
            aria-label="Maximum confidence score"
            aria-describedby="confidence-help"
          />
          <span className="text-sm text-muted-foreground">%</span>
        </div>
      </div>

      {/* Visual Separator */}
      <div className="border-t border-border" />

      {/* Below Threshold Toggle */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Checkbox
            id="include-below-threshold"
            checked={includeBelowThreshold}
            onCheckedChange={(checked) => onIncludeBelowThresholdChange(checked === true)}
            aria-describedby="threshold-help"
          />
          <Label
            htmlFor="include-below-threshold"
            className="text-sm font-medium cursor-pointer"
          >
            Include low-confidence artifacts
          </Label>
        </div>
        <p id="threshold-help" className="text-xs text-muted-foreground ml-6">
          Shows artifacts below the 30% confidence threshold
        </p>
      </div>

      {/* Hidden Helper Text for Screen Readers */}
      <p id="confidence-help" className="sr-only">
        Filter artifacts by confidence score from 0 to 100 percent
      </p>
    </div>
  );
}
