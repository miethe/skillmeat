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
}

export function ArtifactTypeTabs({ value, onChange, counts, className }: ArtifactTypeTabsProps) {
  const types = getAllArtifactTypes();

  const renderCount = (tab: ArtifactTypeTabValue) => {
    const count = counts?.[tab];
    return typeof count === 'number' ? ` (${count})` : '';
  };

  return (
    <Tabs
      value={value}
      onValueChange={(next) => onChange(next as ArtifactTypeTabValue)}
      className={className}
    >
      <TabsList className="grid w-full grid-cols-6">
        <TabsTrigger value="all" className="flex items-center gap-2">
          <LucideIcons.LayoutGrid className="h-4 w-4" />
          <span>{`All${renderCount('all')}`}</span>
        </TabsTrigger>

        {types.map((type) => {
          const config = ARTIFACT_TYPES[type];
          const Icon = (LucideIcons as unknown as Record<string, LucideIcon>)[config.icon];

          return (
            <TabsTrigger key={type} value={type} className="flex items-center gap-2">
              {Icon && <Icon className="h-4 w-4" />}
              <span className="hidden sm:inline">{`${config.pluralLabel}${renderCount(type)}`}</span>
              <span className="sm:hidden">{`${config.label}${renderCount(type)}`}</span>
            </TabsTrigger>
          );
        })}
      </TabsList>
    </Tabs>
  );
}
