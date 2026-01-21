'use client';

import * as React from 'react';
import { GitCompare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';

export type ComparisonScope =
  | 'collection-vs-project'
  | 'source-vs-collection'
  | 'source-vs-project';

export interface ComparisonSelectorProps {
  value: ComparisonScope;
  onChange: (scope: ComparisonScope) => void;
  hasSource: boolean;
  hasProject: boolean;
}

interface ScopeOption {
  value: ComparisonScope;
  label: string;
  shortLabel: string;
  requiresSource: boolean;
  requiresProject: boolean;
}

const scopeOptions: ScopeOption[] = [
  {
    value: 'collection-vs-project',
    label: 'Collection vs. Project',
    shortLabel: 'Coll vs Proj',
    requiresSource: false,
    requiresProject: true,
  },
  {
    value: 'source-vs-collection',
    label: 'Source vs. Collection',
    shortLabel: 'Src vs Coll',
    requiresSource: true,
    requiresProject: false,
  },
  {
    value: 'source-vs-project',
    label: 'Source vs. Project',
    shortLabel: 'Src vs Proj',
    requiresSource: true,
    requiresProject: true,
  },
];

export function ComparisonSelector({
  value,
  onChange,
  hasSource,
  hasProject,
}: ComparisonSelectorProps) {
  const isOptionDisabled = (option: ScopeOption): boolean => {
    if (option.requiresSource && !hasSource) return true;
    if (option.requiresProject && !hasProject) return true;
    return false;
  };

  const getDisabledReason = (option: ScopeOption): string | null => {
    if (option.requiresSource && !hasSource && option.requiresProject && !hasProject) {
      return 'No source or project available';
    }
    if (option.requiresSource && !hasSource) {
      return 'No upstream source configured';
    }
    if (option.requiresProject && !hasProject) {
      return 'No project deployment found';
    }
    return null;
  };

  return (
    <div className="space-y-3">
      {/* Select Dropdown */}
      <div className="flex items-center gap-2">
        <GitCompare className="h-4 w-4 text-muted-foreground" />
        <Label htmlFor="comparison-select" className="text-sm">
          Compare:
        </Label>
        <Select value={value} onValueChange={onChange}>
          <SelectTrigger id="comparison-select" className="flex-1">
            <SelectValue placeholder="Select comparison..." />
          </SelectTrigger>
          <SelectContent>
            {scopeOptions.map((option) => (
              <SelectItem
                key={option.value}
                value={option.value}
                disabled={isOptionDisabled(option)}
              >
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Quick Switch Buttons */}
      <div className="flex gap-1">
        {scopeOptions.map((option) => {
          const isActive = value === option.value;
          const isDisabled = isOptionDisabled(option);
          const disabledReason = getDisabledReason(option);

          return (
            <Button
              key={option.value}
              variant={isActive ? 'default' : 'outline'}
              size="sm"
              onClick={() => onChange(option.value)}
              disabled={isDisabled}
              className={cn('flex-1 text-xs', isActive && 'pointer-events-none')}
              title={isDisabled && disabledReason ? disabledReason : option.label}
            >
              {option.shortLabel}
            </Button>
          );
        })}
      </div>
    </div>
  );
}
