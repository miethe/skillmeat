'use client';

import { useState, useEffect, Suspense } from 'react';
import { useParams, useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  GitBranch,
  ArrowLeft,
  Package,
  Clock,
  AlertCircle,
  ExternalLink,
  Folder,
  FileText,
  Bot,
  Plug,
  Code,
  Settings,
  Loader2,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { EntityLifecycleProvider } from '@/components/entity/EntityLifecycleProvider';
import { UnifiedEntityModal } from '@/components/entity/unified-entity-modal';
import { useProject } from '@/hooks/useProjects';
import { useArtifacts } from '@/hooks/useArtifacts';
import { useProjectDiscovery } from '@/hooks/useProjectDiscovery';
import { DiscoveryBanner } from '@/components/discovery/DiscoveryBanner';
import { DiscoveryTab } from '@/components/discovery/DiscoveryTab';
import { BulkImportModal } from '@/components/discovery/BulkImportModal';
import { useToast } from '@/hooks/use-toast';
import type { DeployedArtifact } from '@/types/project';
import type { Entity, EntityType } from '@/types/entity';
import type { DiscoveredArtifact } from '@/types/discovery';

const artifactTypeIcons = {
  skill: Folder,
  command: FileText,
  agent: Bot,
  mcp: Plug,
  hook: Code,
};

const artifactTypeColors = {
  skill: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  command: 'bg-green-500/10 text-green-500 border-green-500/20',
  agent: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  mcp: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
  hook: 'bg-pink-500/10 text-pink-500 border-pink-500/20',
};

function ProjectDetailPageContent() {
  const params = useParams();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const projectId = params.id as string;
  const { toast } = useToast();

  // Tab state from URL
  const activeTab = searchParams.get('tab') || 'deployed';

  const { data: project, isLoading, error } = useProject(projectId);

  // Modal state for entity detail
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  // Fetch all artifacts to match by name
  const { data: artifactsData } = useArtifacts();

  // Project-specific discovery hook
  const {
    discoveredArtifacts,
    discoveredCount,
    importableCount,
    isDiscovering,
    refetchDiscovery,
    bulkImport,
    skipPrefs,
  } = useProjectDiscovery(project?.path, projectId);

  // Tab change handler
  const handleTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', value);
    router.push(`${pathname}?${params.toString()}`);
  };

  // Trigger discovery when project loads
  useEffect(() => {
    if (project?.path) {
      refetchDiscovery();
    }
  }, [project?.path, refetchDiscovery]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  };

  const getArtifactIcon = (type: string) => {
    const Icon = artifactTypeIcons[type as keyof typeof artifactTypeIcons] || Package;
    return Icon;
  };

  const getArtifactColorClass = (type: string) => {
    return (
      artifactTypeColors[type as keyof typeof artifactTypeColors] ||
      'bg-gray-500/10 text-gray-500 border-gray-500/20'
    );
  };

  const groupArtifactsByType = (artifacts: DeployedArtifact[]) => {
    const grouped: Record<string, DeployedArtifact[]> = {};
    artifacts.forEach((artifact) => {
      if (!grouped[artifact.artifact_type]) {
        grouped[artifact.artifact_type] = [];
      }
      grouped[artifact.artifact_type]?.push(artifact);
    });
    return grouped;
  };

  const handleArtifactClick = async (deployedArtifact: DeployedArtifact) => {
    // Try to find matching artifact from collection by name
    const matchingArtifact = artifactsData?.artifacts.find(
      (artifact) => artifact.name === deployedArtifact.artifact_name
    );

    if (matchingArtifact) {
      // Convert Artifact to Entity with project context
      const entity: Entity = {
        id: `${matchingArtifact.type}:${matchingArtifact.name}`,
        name: matchingArtifact.name,
        type: matchingArtifact.type,
        description: matchingArtifact.metadata?.description,
        source: matchingArtifact.source,
        version: matchingArtifact.version,
        tags: matchingArtifact.metadata?.tags,
        aliases: matchingArtifact.aliases,
        status: deployedArtifact.local_modifications ? 'modified' : 'synced',
        collection: deployedArtifact.from_collection,
        projectPath: project?.path, // Set project path for project-level operations
        deployedAt: deployedArtifact.deployed_at,
        modifiedAt: deployedArtifact.local_modifications ? new Date().toISOString() : undefined,
      };

      setSelectedEntity(entity);
      setIsDetailOpen(true);
    } else {
      // If not found in collection, show a notification or error
      console.warn(`Artifact ${deployedArtifact.artifact_name} not found in collection`);
    }
  };

  const handleDetailClose = () => {
    setIsDetailOpen(false);
    // Keep selectedEntity for a moment to avoid flickering
    setTimeout(() => setSelectedEntity(null), 300);
  };

  // Handle bulk import from discovery
  const handleImport = async (
    selected: DiscoveredArtifact[],
    skipList?: string[],
    applyPathTags?: boolean
  ) => {
    try {
      const result = await bulkImport({
        artifacts: selected.map((a) => ({
          source: a.source || `local/${a.type}/${a.name}`,
          artifact_type: a.type,
          name: a.name,
          description: a.description,
          tags: a.tags,
          scope: a.scope || 'user',
          path: a.path,
        })),
        skip_list: skipList,
        apply_path_tags: applyPathTags,
      });

      if (result.total_imported > 0) {
        toast({
          title: 'Import Successful',
          description: `Imported ${result.total_imported} artifact(s) into collection`,
        });
        // Refetch discovery to update the list
        refetchDiscovery();
      }
      if (result.total_failed > 0) {
        toast({
          title: 'Partial Import',
          description: `${result.total_failed} artifact(s) failed to import`,
          variant: 'destructive',
        });
      }

      return result;
    } catch (error) {
      toast({
        title: 'Import Failed',
        description: error instanceof Error ? error.message : 'Failed to import artifacts',
        variant: 'destructive',
      });
      throw error;
    }
  };

  // Handle single artifact import from DiscoveryTab
  const handleSingleImport = (_artifact: DiscoveredArtifact) => {
    // Open BulkImportModal with just this artifact
    setShowImportModal(true);
    // Note: BulkImportModal will need to be filtered to show only this artifact
    // For now, it will show all artifacts - filtering can be added in DIS-4.7
  };

  // Handle artifact detail view from DiscoveryTab
  const handleViewArtifactDetails = (artifact: DiscoveredArtifact) => {
    // Convert DiscoveredArtifact to Entity for modal
    const entity: Entity = {
      id: `${artifact.type}:${artifact.name}`,
      name: artifact.name,
      type: artifact.type as EntityType,
      description: artifact.description,
      source: artifact.source,
      tags: artifact.tags,
      status: 'synced', // Default status for discovered artifacts
      collection: 'discovered',
      projectPath: project?.path,
    };
    setSelectedEntity(entity);
    setIsDetailOpen(true);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.push('/projects')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Projects
        </Button>
        <Card>
          <CardContent className="pt-6">
            <div className="animate-pulse space-y-4">
              <div className="h-8 w-1/3 rounded bg-muted" />
              <div className="h-4 w-1/2 rounded bg-muted" />
              <div className="h-32 rounded bg-muted" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.push('/projects')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Projects
        </Button>
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <p>Failed to load project details. Please try again.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const groupedArtifacts = groupArtifactsByType(project.deployments || []);

  return (
    <EntityLifecycleProvider mode="project" projectPath={project?.path}>
      <div className="space-y-6">
        {/* Discovery Banner */}
        {importableCount > 0 && !isDiscovering && (
          <DiscoveryBanner
            importableCount={importableCount}
            discoveredCount={discoveredCount}
            onReview={() => setShowImportModal(true)}
            dismissible
          />
        )}

        {/* Header */}
        <div className="space-y-4">
          <Button variant="ghost" onClick={() => router.push('/projects')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Projects
          </Button>

          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <GitBranch className="h-8 w-8 text-muted-foreground" />
                <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
              </div>
              <p className="font-mono text-sm text-muted-foreground">{project.path}</p>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={() => router.push(`/projects/${projectId}/manage`)}>
                <Settings className="mr-2 h-4 w-4" />
                Manage Entities
              </Button>
              <Button variant="outline" asChild>
                <a
                  href={`file://${project.path}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2"
                >
                  Open in Finder
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            </div>
          </div>
        </div>

        {/* Tabs: Deployed vs Discovery */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="deployed" className="flex items-center gap-2">
              <Package className="h-4 w-4" />
              Deployed
            </TabsTrigger>
            <TabsTrigger value="discovery" className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Discovery
              {importableCount > 0 && (
                <Badge variant="default" className="ml-1 bg-green-500">
                  {importableCount}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          {/* Deployed Tab Content */}
          <TabsContent value="deployed" className="mt-6 space-y-6">
            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Total Deployments
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{project.deployment_count}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Last Deployed
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold">
                    {project.last_deployment ? formatDate(project.last_deployment) : 'Never'}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Modified Locally
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{project.stats.modified_count}</div>
                </CardContent>
              </Card>
            </div>

            {/* Statistics */}
            <Card>
              <CardHeader>
                <CardTitle>Deployment Statistics</CardTitle>
                <CardDescription>Breakdown of deployed artifacts</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="mb-3 text-sm font-medium">By Type</h3>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(project.stats.by_type).map(([type, count]) => {
                      const Icon = getArtifactIcon(type);
                      return (
                        <Badge key={type} variant="outline" className="px-3 py-1.5">
                          <Icon className="mr-1.5 h-3 w-3" />
                          {type}: {count}
                        </Badge>
                      );
                    })}
                  </div>
                </div>

                <div className="my-4 border-t" />

                <div>
                  <h3 className="mb-3 text-sm font-medium">By Collection</h3>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(project.stats.by_collection).map(([collection, count]) => (
                      <Badge key={collection} variant="secondary" className="px-3 py-1.5">
                        {collection}: {count}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Deployed Artifacts Tree */}
            <Card>
              <CardHeader>
                <CardTitle>Deployed Artifacts</CardTitle>
                <CardDescription>Complete list of artifacts deployed to this project</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {Object.entries(groupedArtifacts).map(([type, artifacts]) => {
                    const Icon = getArtifactIcon(type);
                    const colorClass = getArtifactColorClass(type);

                    return (
                      <div key={type}>
                        <div className="mb-3 flex items-center gap-2">
                          <div className={`rounded-md border p-2 ${colorClass}`}>
                            <Icon className="h-4 w-4" />
                          </div>
                          <h3 className="font-semibold capitalize">
                            {type}s ({artifacts.length})
                          </h3>
                        </div>

                        <div className="ml-6 space-y-2">
                          {artifacts.map((artifact) => (
                            <div
                              key={`${artifact.artifact_type}-${artifact.artifact_name}`}
                              className="flex cursor-pointer items-start justify-between rounded-lg border bg-card p-3 transition-colors hover:bg-accent/50"
                              onClick={() => handleArtifactClick(artifact)}
                              role="button"
                              tabIndex={0}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault();
                                  handleArtifactClick(artifact);
                                }
                              }}
                            >
                              <div className="flex-1 space-y-1">
                                <div className="flex items-center gap-2">
                                  <p className="font-medium">{artifact.artifact_name}</p>
                                  {artifact.local_modifications && (
                                    <Badge variant="outline" className="text-xs">
                                      <AlertCircle className="mr-1 h-3 w-3" />
                                      Modified
                                    </Badge>
                                  )}
                                </div>
                                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                  <span className="font-mono">{artifact.artifact_path}</span>
                                  <span>•</span>
                                  <span>from {artifact.from_collection}</span>
                                  {artifact.version && (
                                    <>
                                      <span>•</span>
                                      <span>{artifact.version}</span>
                                    </>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Clock className="h-3 w-3" />
                                {formatDate(artifact.deployed_at)}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Discovery Tab Content */}
          <TabsContent value="discovery" className="mt-6 space-y-6">
            <DiscoveryTab
              artifacts={discoveredArtifacts}
              isLoading={isDiscovering}
              skipPrefs={skipPrefs}
              onImport={handleSingleImport}
              onViewDetails={handleViewArtifactDetails}
            />
          </TabsContent>
        </Tabs>

        {/* Entity Detail Modal - Project Mode */}
        <UnifiedEntityModal
          entity={selectedEntity}
          open={isDetailOpen}
          onClose={handleDetailClose}
        />

        {/* Bulk Import Modal */}
        <BulkImportModal
          artifacts={discoveredArtifacts}
          open={showImportModal}
          onClose={() => setShowImportModal(false)}
          onImport={handleImport}
        />
      </div>
    </EntityLifecycleProvider>
  );
}

export default function ProjectDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      }
    >
      <ProjectDetailPageContent />
    </Suspense>
  );
}
