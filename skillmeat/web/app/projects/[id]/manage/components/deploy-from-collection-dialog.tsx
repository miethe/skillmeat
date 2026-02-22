'use client';

import { useState, useEffect, useMemo } from 'react';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Artifact, ArtifactType, ARTIFACT_TYPES, getAllArtifactTypes } from '@/types/artifact';
import { apiRequest } from '@/lib/api';
import { ArtifactListResponse, DeployRequest } from '@/sdk';
import { Search, Loader2, Package, CheckCircle2, Eye } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { TagFilterPopover } from '@/components/ui/tag-filter-popover';
import { GroupFilterSelect } from '@/components/shared/group-filter-select';
import { ArtifactDetailsModal } from '@/components/collection/artifact-details-modal';
import { useGroupArtifacts } from '@/hooks';

interface DeployedArtifactKey {
  name: string;
  type: string;
}

interface DeployFromCollectionDialogProps {
  projectPath: string;
  collection_id?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  /** Set of artifacts already deployed to this project (name + type pairs) */
  deployedArtifacts?: DeployedArtifactKey[];
}

export function DeployFromCollectionDialog({
  projectPath,
  collection_id,
  open,
  onOpenChange,
  onSuccess,
  deployedArtifacts = [],
}: DeployFromCollectionDialogProps) {
  const [selectedEntities, setSelectedEntities] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<ArtifactType>('skill');
  const [isLoading, setIsLoading] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [entities, setEntities] = useState<Artifact[]>([]);

  // Filter state
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | undefined>(undefined);

  // Details modal state
  const [detailsArtifact, setDetailsArtifact] = useState<Artifact | null>(null);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);

  // Build a lookup set for deployed artifacts (key = "type:name")
  const deployedSet = useMemo(() => {
    const set = new Set<string>();
    for (const artifact of deployedArtifacts) {
      set.add(`${artifact.type}:${artifact.name}`);
    }
    return set;
  }, [deployedArtifacts]);

  const isAlreadyDeployed = (entity: Artifact): boolean => {
    return deployedSet.has(`${entity.type}:${entity.name}`);
  };

  // Fetch group artifacts when a group is selected
  const { data: groupArtifacts } = useGroupArtifacts(selectedGroupId);

  // Build a set of artifact IDs in the selected group for filtering
  const groupArtifactIds = useMemo(() => {
    if (!selectedGroupId || !groupArtifacts) return null;
    const set = new Set<string>();
    for (const ga of groupArtifacts) {
      // Use artifact_id (type:name) when available for entity.id comparison;
      // also add artifact_uuid as fallback for orphaned entries.
      if (ga.artifact_id) {
        set.add(ga.artifact_id);
      }
      set.add(ga.artifact_uuid);
    }
    return set;
  }, [selectedGroupId, groupArtifacts]);

  // Fetch collection entities
  useEffect(() => {
    if (open) {
      fetchEntities(activeTab);
    }
  }, [open, activeTab]);

  // Reset filters when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedTags([]);
      setSelectedGroupId(undefined);
      setDetailsArtifact(null);
      setDetailsModalOpen(false);
    }
  }, [open]);

  const fetchEntities = async (type: ArtifactType) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        artifact_type: type,
        limit: '100',
      });

      const response = await apiRequest<ArtifactListResponse>(`/artifacts?${params.toString()}`);

      const collectionId = collection_id || 'default';
      const mappedEntities: Artifact[] = response.items.map((item) => ({
        id: item.id,
        uuid: (item as any).uuid ?? '',
        name: item.name,
        type: item.type as ArtifactType,
        collection: collectionId,
        syncStatus: 'synced',
        scope: 'user',
        tags: item.tags ?? (item.metadata as any)?.tags ?? [],
        description: item.metadata?.description || undefined,
        version: item.version || item.metadata?.version || undefined,
        source: item.source,
        deployedAt: item.added,
        createdAt: item.added || new Date().toISOString(),
        updatedAt: item.updated || new Date().toISOString(),
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

  // Apply all filters: search, tags, group
  const filteredEntities = useMemo(() => {
    let result = entities;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (entity) =>
          entity.name.toLowerCase().includes(query) ||
          entity.description?.toLowerCase().includes(query) ||
          entity.tags?.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    // Tag filter
    if (selectedTags.length > 0) {
      result = result.filter((entity) =>
        selectedTags.some((tag) => entity.tags?.includes(tag))
      );
    }

    // Group filter (client-side: filter by group artifact membership)
    if (groupArtifactIds) {
      result = result.filter((entity) => groupArtifactIds.has(entity.id));
    }

    return result;
  }, [entities, searchQuery, selectedTags, groupArtifactIds]);

  const toggleEntity = (entityId: string) => {
    // Find the entity and check if it's already deployed
    const entity = entities.find((e) => e.id === entityId);
    if (entity && isAlreadyDeployed(entity)) return;

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
      const collectionId = collection_id || 'default';

      // Deploy each selected entity
      const deployPromises = Array.from(selectedEntities).map(async (entityId) => {
        const entity = entities.find((e) => e.id === entityId);
        if (!entity) return;

        const request: DeployRequest = {
          artifact_id: entity.id,
          artifact_name: entity.name,
          artifact_type: entity.type,
          project_path: projectPath,
          collection_name: collectionId,
        };

        await apiRequest('/deploy', {
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

  const handleOpenDetails = (entity: Artifact, e: React.MouseEvent) => {
    e.stopPropagation();
    setDetailsArtifact(entity);
    setDetailsModalOpen(true);
  };

  const entityTypes = getAllArtifactTypes();
  const collectionId = collection_id || 'default';

  return (
    <TooltipProvider>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="flex max-h-[90vh] max-w-5xl flex-col">
          <DialogHeader>
            <DialogTitle>Deploy from Collection</DialogTitle>
            <DialogDescription>
              Select entities from your collection to deploy to this project
            </DialogDescription>
          </DialogHeader>

          <div className="flex min-h-0 flex-1 flex-col">
            {/* Search + Filters Row */}
            <div className="mb-4 flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-muted-foreground" />
                <Input
                  placeholder="Search entities..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                  aria-label="Search entities"
                />
              </div>
              <GroupFilterSelect
                collectionId={collectionId}
                value={selectedGroupId}
                onChange={setSelectedGroupId}
                className="w-[180px]"
              />
              <TagFilterPopover
                selectedTags={selectedTags}
                onChange={setSelectedTags}
              />
            </div>

            {/* Entity Type Tabs */}
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as ArtifactType)}>
              <TabsList className="mb-4 grid w-full grid-cols-5">
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
                <TabsContent key={type} value={type} className="min-h-0 flex-1">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                  ) : filteredEntities.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <Package className="mb-4 h-12 w-12 text-muted-foreground" />
                      <h3 className="mb-2 text-lg font-semibold">
                        No {ARTIFACT_TYPES[type].pluralLabel} Found
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {searchQuery || selectedTags.length > 0 || selectedGroupId
                          ? 'No entities match your filters.'
                          : `Add ${ARTIFACT_TYPES[type].pluralLabel.toLowerCase()} to your collection first.`}
                      </p>
                    </div>
                  ) : (
                    <ScrollArea className="h-[500px]">
                      <div className="space-y-2 pr-4">
                        {filteredEntities.map((entity) => {
                          const isSelected = selectedEntities.has(entity.id);
                          const deployed = isAlreadyDeployed(entity);

                          return (
                            <div
                              key={entity.id}
                              className={cn(
                                'group flex items-start gap-3 rounded-lg border p-3 transition-colors',
                                deployed
                                  ? 'cursor-default opacity-50'
                                  : 'cursor-pointer hover:bg-accent/50'
                              )}
                              onClick={() => !deployed && toggleEntity(entity.id)}
                            >
                              <Checkbox
                                checked={deployed ? false : isSelected}
                                onCheckedChange={() => toggleEntity(entity.id)}
                                disabled={deployed}
                                className="mt-1"
                                aria-label={
                                  deployed
                                    ? `${entity.name} is already deployed`
                                    : `Select ${entity.name} for deployment`
                                }
                              />
                              <div className="min-w-0 flex-1">
                                <div className="mb-1 flex items-center gap-2">
                                  <h4 className="font-medium">{entity.name}</h4>
                                  {entity.version && (
                                    <Badge variant="outline" className="text-xs">
                                      {entity.version}
                                    </Badge>
                                  )}
                                  {deployed && (
                                    <Badge
                                      variant="secondary"
                                      className="text-xs text-muted-foreground"
                                    >
                                      Already deployed
                                    </Badge>
                                  )}
                                </div>
                                {entity.description && (
                                  <p className="mb-2 text-sm text-muted-foreground">
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
                              <div className="flex flex-shrink-0 items-center gap-2">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      className="h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100"
                                      onClick={(e) => handleOpenDetails(entity, e)}
                                      aria-label={`View details for ${entity.name}`}
                                    >
                                      <Eye className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>View details</TooltipContent>
                                </Tooltip>
                                {isSelected && !deployed && (
                                  <CheckCircle2 className="h-5 w-5 text-primary" />
                                )}
                              </div>
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
            <div className="flex w-full items-center justify-between">
              <div className="text-sm text-muted-foreground">
                {selectedEntities.size} {selectedEntities.size === 1 ? 'entity' : 'entities'} selected
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isDeploying}>
                  Cancel
                </Button>
                <Button onClick={handleDeploy} disabled={selectedEntities.size === 0 || isDeploying}>
                  {isDeploying ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Deploying...
                    </>
                  ) : (
                    <>
                      <Package className="mr-2 h-4 w-4" />
                      Deploy Selected
                    </>
                  )}
                </Button>
              </div>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Artifact Details Modal (opens on top of the deploy dialog via portal) */}
      <ArtifactDetailsModal
        artifact={detailsArtifact}
        open={detailsModalOpen}
        onClose={() => {
          setDetailsModalOpen(false);
          setDetailsArtifact(null);
        }}
      />
    </TooltipProvider>
  );
}
