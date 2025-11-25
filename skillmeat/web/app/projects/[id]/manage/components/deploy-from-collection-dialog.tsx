'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { Entity, EntityType, ENTITY_TYPES, getAllEntityTypes } from '@/types/entity';
import { apiRequest } from '@/lib/api';
import { ArtifactListResponse, ArtifactDeployRequest } from '@/sdk';
import { Search, Loader2, Package, CheckCircle2 } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { LucideIcon } from 'lucide-react';

interface DeployFromCollectionDialogProps {
  projectPath: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function DeployFromCollectionDialog({
  projectPath,
  open,
  onOpenChange,
  onSuccess,
}: DeployFromCollectionDialogProps) {
  const [selectedEntities, setSelectedEntities] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<EntityType>('skill');
  const [isLoading, setIsLoading] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [entities, setEntities] = useState<Entity[]>([]);

  // Fetch collection entities
  useEffect(() => {
    if (open) {
      fetchEntities(activeTab);
    }
  }, [open, activeTab]);

  const fetchEntities = async (type: EntityType) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        artifact_type: type,
        limit: '100',
      });

      const response = await apiRequest<ArtifactListResponse>(`/artifacts?${params.toString()}`);

      const mappedEntities: Entity[] = response.items.map(item => ({
        id: item.id,
        name: item.name,
        type: item.type as EntityType,
        collection: 'default',
        status: 'synced',
        tags: item.metadata?.tags || [],
        description: item.metadata?.description || undefined,
        version: item.version || item.metadata?.version || undefined,
        source: item.source,
        deployedAt: item.added,
        modifiedAt: item.updated,
      }));

      setEntities(mappedEntities);
    } catch (error) {
      console.error('Failed to fetch entities:', error);
      setEntities([]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredEntities = searchQuery
    ? entities.filter(
        (entity) =>
          entity.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          entity.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          entity.tags?.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : entities;

  const toggleEntity = (entityId: string) => {
    const newSelected = new Set(selectedEntities);
    if (newSelected.has(entityId)) {
      newSelected.delete(entityId);
    } else {
      newSelected.add(entityId);
    }
    setSelectedEntities(newSelected);
  };

  const handleDeploy = async () => {
    if (selectedEntities.size === 0) return;

    setIsDeploying(true);
    try {
      // Deploy each selected entity
      const deployPromises = Array.from(selectedEntities).map(async (entityId) => {
        const request: ArtifactDeployRequest = {
          project_path: projectPath,
        };

        await apiRequest(`/artifacts/${entityId}/deploy`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });
      });

      await Promise.all(deployPromises);

      // Success
      onSuccess?.();
      setSelectedEntities(new Set());
      setSearchQuery('');
    } catch (error) {
      console.error('Deploy failed:', error);
      alert('Failed to deploy some entities. Please try again.');
    } finally {
      setIsDeploying(false);
    }
  };

  const entityTypes = getAllEntityTypes();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Deploy from Collection</DialogTitle>
          <DialogDescription>
            Select entities from your collection to deploy to this project
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 flex flex-col min-h-0">
          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Entity Type Tabs */}
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as EntityType)}>
            <TabsList className="grid w-full grid-cols-5 mb-4">
              {entityTypes.map((type) => {
                const config = ENTITY_TYPES[type];
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
              <TabsContent key={type} value={type} className="flex-1 min-h-0">
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : filteredEntities.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <Package className="h-12 w-12 text-muted-foreground mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No {ENTITY_TYPES[type].pluralLabel} Found</h3>
                    <p className="text-sm text-muted-foreground">
                      {searchQuery
                        ? 'No entities match your search.'
                        : `Add ${ENTITY_TYPES[type].pluralLabel.toLowerCase()} to your collection first.`}
                    </p>
                  </div>
                ) : (
                  <ScrollArea className="h-[400px]">
                    <div className="space-y-2 pr-4">
                      {filteredEntities.map((entity) => {
                        const isSelected = selectedEntities.has(entity.id);

                        return (
                          <div
                            key={entity.id}
                            className="flex items-start gap-3 p-3 border rounded-lg hover:bg-accent/50 transition-colors cursor-pointer"
                            onClick={() => toggleEntity(entity.id)}
                          >
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={() => toggleEntity(entity.id)}
                              className="mt-1"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className="font-medium">{entity.name}</h4>
                                {entity.version && (
                                  <Badge variant="outline" className="text-xs">
                                    {entity.version}
                                  </Badge>
                                )}
                              </div>
                              {entity.description && (
                                <p className="text-sm text-muted-foreground mb-2">
                                  {entity.description}
                                </p>
                              )}
                              {entity.tags && entity.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {entity.tags.map((tag) => (
                                    <Badge key={tag} variant="secondary" className="text-xs">
                                      {tag}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                            {isSelected && (
                              <CheckCircle2 className="h-5 w-5 text-primary flex-shrink-0" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                )}
              </TabsContent>
            ))}
          </Tabs>
        </div>

        <DialogFooter>
          <div className="flex items-center justify-between w-full">
            <div className="text-sm text-muted-foreground">
              {selectedEntities.size} {selectedEntities.size === 1 ? 'entity' : 'entities'} selected
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isDeploying}>
                Cancel
              </Button>
              <Button
                onClick={handleDeploy}
                disabled={selectedEntities.size === 0 || isDeploying}
              >
                {isDeploying ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Deploying...
                  </>
                ) : (
                  <>
                    <Package className="h-4 w-4 mr-2" />
                    Deploy Selected
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
