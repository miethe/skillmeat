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

  const handleTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('type', value);
    // Use current pathname instead of hardcoded /manage
    router.push(`${pathname}?${params.toString()}`);
  };

  const entityTypes = getAllArtifactTypes();

  return (
    <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
      <TabsList className="grid w-full grid-cols-5">
        {entityTypes.map((type) => {
          const config = ARTIFACT_TYPES[type];
          const IconComponent = (LucideIcons as any)[config.icon] as LucideIcon;

          return (
            <TabsTrigger key={type} value={type} className="flex items-center gap-2">
              {IconComponent && <IconComponent className="h-4 w-4" />}
              <span className="hidden sm:inline">{config.pluralLabel}</span>
              <span className="sm:hidden">{config.label}</span>
            </TabsTrigger>
          );
        })}
      </TabsList>

      {entityTypes.map((type) => (
        <TabsContent key={type} value={type} className="flex-1">
          {children(type)}
        </TabsContent>
      ))}
    </Tabs>
  );
}
