'use client';

import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ARTIFACT_TYPES, ArtifactType, getAllArtifactTypes } from '@/types/artifact';
import * as LucideIcons from 'lucide-react';
import { LucideIcon } from 'lucide-react';

interface EntityTabsProps {
  children: (entityType: ArtifactType) => React.ReactNode;
}

export function EntityTabs({ children }: EntityTabsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeTab = (searchParams.get('type') as ArtifactType) || 'skill';
  const compositeSubtype = searchParams.get('subtype') || 'all';

  const handleTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('type', value);
    // Clear subtype filter when switching away from composite tab
    if (value !== 'composite') {
      params.delete('subtype');
    }
    router.push(`${pathname}?${params.toString()}`);
  };

  const handleSubtypeChange = (subtype: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (subtype === 'all') {
      params.delete('subtype');
    } else {
      params.set('subtype', subtype);
    }
    router.push(`${pathname}?${params.toString()}`);
  };

  const entityTypes = getAllArtifactTypes();
  const compositeConfig = ARTIFACT_TYPES['composite'];
  const showSubtypeFilter =
    activeTab === 'composite' &&
    compositeConfig.subtypes &&
    compositeConfig.subtypes.length > 0;

  return (
    <div className="w-full">
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-6 h-8">
          {entityTypes.map((type) => {
            const config = ARTIFACT_TYPES[type];
            const IconComponent = (LucideIcons as any)[config.icon] as LucideIcon;

            return (
              <TabsTrigger key={type} value={type} className="flex items-center gap-1 px-2 py-1 text-xs">
                {IconComponent && <IconComponent className="h-3.5 w-3.5 shrink-0" />}
                <span className="hidden sm:inline truncate">{config.pluralLabel}</span>
              </TabsTrigger>
            );
          })}
        </TabsList>

        {showSubtypeFilter && (
          <div
            className="mt-1.5 flex items-center gap-1.5 flex-wrap px-1"
            role="group"
            aria-label="Filter by composite type"
          >
            {compositeConfig.subtypes!.map((subtype) => (
              <button
                key={subtype.value}
                type="button"
                onClick={() => handleSubtypeChange(subtype.value)}
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

        {entityTypes.map((type) => (
          <TabsContent key={type} value={type} className="flex-1">
            {children(type)}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
