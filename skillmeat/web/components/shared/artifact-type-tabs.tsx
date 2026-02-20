'use client';

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ARTIFACT_TYPES, type ArtifactType, getAllArtifactTypes } from '@/types/artifact';
import * as LucideIcons from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type ArtifactTypeTabValue = 'all' | ArtifactType;

interface ArtifactTypeTabsProps {
  value: ArtifactTypeTabValue;
  onChange: (value: ArtifactTypeTabValue) => void;
  counts?: Partial<Record<ArtifactTypeTabValue, number>>;
  className?: string;
  /** Currently selected composite sub-type (only relevant when value === 'composite') */
  compositeSubtype?: string;
  /** Called when the composite sub-type filter changes */
  onCompositeSubtypeChange?: (subtype: string) => void;
}

export function ArtifactTypeTabs({
  value,
  onChange,
  counts,
  className,
  compositeSubtype = 'all',
  onCompositeSubtypeChange,
}: ArtifactTypeTabsProps) {
  const types = getAllArtifactTypes();

  const renderCount = (tab: ArtifactTypeTabValue) => {
    const count = counts?.[tab];
    return typeof count === 'number' ? ` (${count})` : '';
  };

  const compositeConfig = ARTIFACT_TYPES['composite'];
  const showSubtypeFilter = value === 'composite' && compositeConfig.subtypes && compositeConfig.subtypes.length > 0;

  return (
    <div className={className}>
      <Tabs
        value={value}
        onValueChange={(next) => onChange(next as ArtifactTypeTabValue)}
      >
        <TabsList className="grid w-full grid-cols-7 h-8">
          <TabsTrigger value="all" className="flex items-center gap-1 px-2 py-1 text-xs">
            <LucideIcons.LayoutGrid className="h-3.5 w-3.5 shrink-0" />
            <span className="hidden sm:inline truncate">{`All${renderCount('all')}`}</span>
          </TabsTrigger>

          {types.map((type) => {
            const config = ARTIFACT_TYPES[type];
            const Icon = (LucideIcons as unknown as Record<string, LucideIcon>)[config.icon];

            return (
              <TabsTrigger key={type} value={type} className="flex items-center gap-1 px-2 py-1 text-xs">
                {Icon && <Icon className="h-3.5 w-3.5 shrink-0" />}
                <span className="hidden sm:inline truncate">{`${config.pluralLabel}${renderCount(type)}`}</span>
              </TabsTrigger>
            );
          })}
        </TabsList>
      </Tabs>

      {showSubtypeFilter && (
        <div
          className="mt-1.5 flex items-center gap-1.5 flex-wrap"
          role="group"
          aria-label="Filter by composite type"
        >
          {compositeConfig.subtypes!.map((subtype) => (
            <button
              key={subtype.value}
              type="button"
              onClick={() => onCompositeSubtypeChange?.(subtype.value)}
              aria-pressed={compositeSubtype === subtype.value}
              className={[
                'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
                compositeSubtype === subtype.value
                  ? 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground',
              ].join(' ')}
            >
              {subtype.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
