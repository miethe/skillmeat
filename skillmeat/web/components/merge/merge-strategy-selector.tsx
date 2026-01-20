/**
 * Merge strategy selector component
 */
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { GitMerge, Eye, XCircle } from 'lucide-react';
import type { MergeStrategy } from '@/types/merge';
import { cn } from '@/lib/utils';

interface MergeStrategySelectorProps {
  value: MergeStrategy;
  onChange: (strategy: MergeStrategy) => void;
  disabled?: boolean;
}

interface StrategyOption {
  value: MergeStrategy;
  icon: typeof GitMerge;
  label: string;
  description: string;
  color: string;
}

const strategies: StrategyOption[] = [
  {
    value: 'auto',
    icon: GitMerge,
    label: 'Auto-merge where possible',
    description: 'Automatically merge non-conflicting changes and prompt only for conflicts',
    color: 'text-green-600',
  },
  {
    value: 'manual',
    icon: Eye,
    label: 'Manual review all',
    description: 'Review and approve every change before merging',
    color: 'text-blue-600',
  },
  {
    value: 'abort_on_conflict',
    icon: XCircle,
    label: 'Abort on any conflict',
    description: 'Stop the merge process if any conflicts are detected, no partial merges',
    color: 'text-red-600',
  },
];

export function MergeStrategySelector({
  value,
  onChange,
  disabled = false,
}: MergeStrategySelectorProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Merge Strategy</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Label className="text-sm text-muted-foreground">
          Choose how to handle the merge process
        </Label>
        <div className="space-y-2">
          {strategies.map((strategy) => {
            const Icon = strategy.icon;
            const isSelected = value === strategy.value;

            return (
              <button
                key={strategy.value}
                onClick={() => onChange(strategy.value)}
                disabled={disabled}
                className={cn(
                  'w-full rounded-lg border p-4 text-left transition-colors',
                  'hover:border-accent-foreground/20 hover:bg-accent',
                  'disabled:cursor-not-allowed disabled:opacity-50',
                  isSelected && 'border-primary bg-primary/5'
                )}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      'mt-0.5 h-5 w-5 flex-shrink-0 rounded-full border-2',
                      isSelected ? 'border-primary bg-primary' : 'border-muted-foreground'
                    )}
                  >
                    {isSelected && <div className="h-full w-full scale-50 rounded-full bg-white" />}
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Icon className={cn('h-4 w-4', strategy.color)} />
                      <p className="font-semibold">{strategy.label}</p>
                    </div>
                    <p className="text-sm text-muted-foreground">{strategy.description}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Current Selection Summary */}
        {value && (
          <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3">
            <p className="text-sm font-semibold text-blue-900">Selected Strategy:</p>
            <p className="text-sm text-blue-700">
              {strategies.find((s) => s.value === value)?.label}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
