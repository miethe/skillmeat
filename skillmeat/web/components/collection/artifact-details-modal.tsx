/**
 * ArtifactDetailsModal - Discovery-focused modal for the /collection page
 *
 * This modal emphasizes browsing and discovery content (overview, contents, links,
 * collections, sources, history) rather than operational sync/health details.
 *
 * @example
 * ```tsx
 * <ArtifactDetailsModal
 *   artifact={selectedArtifact}
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   initialTab="overview"
 *   onTabChange={(tab) => updateUrlState(tab)}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { useState, useMemo, useEffect, useCallback } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import * as LucideIcons from 'lucide-react';
import {
  Calendar,
  Tag,
  GitBranch,
  Clock,
  Loader2,
  User,
  Github,
  FileText,
  FolderOpen,
  Rocket,
  ExternalLink,
  Copy,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Tabs, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ModalHeader } from '@/components/shared/modal-header';
import { TabNavigation, type Tab } from '@/components/shared/tab-navigation';
import { TabContentWrapper } from '@/components/shared/tab-content-wrapper';
import { CrossNavigationButtons } from '@/components/shared/cross-navigation-buttons';
import { ModalCollectionsTab } from '@/components/entity/modal-collections-tab';
import { LinkedArtifactsSection, type LinkedArtifactReference } from '@/components/entity';
import { ArtifactLinkingDialog } from '@/components/entity';
import { FileTree } from '@/components/entity/file-tree';
import { ContentPane } from '@/components/entity/content-pane';
import { DeployDialog } from '@/components/collection/deploy-dialog';
import { ARTIFACT_TYPES, type Artifact, type ArtifactType } from '@/types/artifact';
import { getCollectionColor } from '@/lib/utils/collection-colors';
import { apiRequest } from '@/lib/api';
import { useToast, useSources, useTags, useUpdateArtifactTags } from '@/hooks';
import { TagEditor } from '@/components/shared/tag-editor';
import type { FileListResponse, FileContentResponse } from '@/types/files';
import { Skeleton } from '@/components/ui/skeleton';

// ============================================================================
// Types
// ============================================================================

/** Valid tab values for the artifact details modal */
export type ArtifactDetailsTab =
  | 'overview'
  | 'contents'
  | 'links'
  | 'collections'
  | 'sources'
  | 'history';

export interface ArtifactDetailsModalProps {
  /** The artifact to display in the modal */
  artifact: Artifact | null;
  /** Whether the modal is open */
  open: boolean;
  /** Callback when the modal is closed */
  onClose: () => void;
  /** Initial tab to display (defaults to 'overview') */
  initialTab?: ArtifactDetailsTab;
  /** Callback when the active tab changes */
  onTabChange?: (tab: ArtifactDetailsTab) => void;
  /** URL to return to if navigated from another page */
  returnTo?: string;
  /** Whether artifact data is currently loading */
  isLoading?: boolean;
}

// ============================================================================
// Skeleton Components
// ============================================================================

/**
 * ModalHeaderSkeleton - Loading skeleton for modal header
 */
function ModalHeaderSkeleton() {
  return (
    <div className="flex items-start justify-between gap-4 border-b px-6 py-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-lg" />
        <div className="space-y-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Skeleton className="h-9 w-9 rounded-md" />
        <Skeleton className="h-9 w-24 rounded-md" />
      </div>
    </div>
  );
}

/**
 * OverviewTabSkeleton - Loading skeleton for overview tab content
 */
function OverviewTabSkeleton() {
  return (
    <div className="space-y-6 p-6">
      {/* Description skeleton */}
      <div>
        <Skeleton className="mb-2 h-4 w-24" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="mt-1 h-4 w-3/4" />
      </div>

      {/* Collections skeleton */}
      <div>
        <Skeleton className="mb-2 h-4 w-20" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
      </div>

      {/* Source skeleton */}
      <div>
        <Skeleton className="mb-2 h-4 w-16" />
        <Skeleton className="h-10 w-full rounded-md" />
      </div>

      {/* Tags skeleton */}
      <div>
        <Skeleton className="mb-2 h-4 w-12" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-16 rounded-full" />
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-14 rounded-full" />
        </div>
      </div>

      {/* Timestamps skeleton */}
      <div>
        <Skeleton className="mb-2 h-4 w-24" />
        <div className="space-y-2">
          <div className="flex justify-between">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-32" />
          </div>
          <div className="flex justify-between">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ContentsTabSkeleton - Loading skeleton for contents tab
 */
function ContentsTabSkeleton() {
  return (
    <div className="flex h-full gap-0">
      {/* File tree skeleton */}
      <div className="w-64 flex-shrink-0 border-r p-4 lg:w-72">
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-4" style={{ width: `${60 + Math.random() * 40}%` }} />
            </div>
          ))}
        </div>
      </div>
      {/* Content pane skeleton */}
      <div className="flex-1 p-4">
        <div className="space-y-2">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="h-4" style={{ width: `${40 + Math.random() * 50}%` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * LinksTabSkeleton - Loading skeleton for links tab
 */
function LinksTabSkeleton() {
  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-9 w-24 rounded-md" />
      </div>
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 rounded-lg border p-4">
            <Skeleton className="h-8 w-8 rounded-md" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-48" />
            </div>
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * HistoryTabSkeleton - Loading skeleton for history tab
 */
function HistoryTabSkeleton() {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-5 w-32" />
      <div className="relative space-y-4 pl-6">
        <div className="absolute bottom-0 left-4 top-0 w-px bg-muted" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="relative">
            <Skeleton className="absolute -left-4 h-4 w-4 rounded-full" />
            <div className="rounded-lg border p-4">
              <div className="flex justify-between">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-32" />
                </div>
                <Skeleton className="h-4 w-16" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface HistoryEntry {
  id: string;
  type: 'deploy' | 'sync' | 'rollback';
  direction: 'upstream' | 'downstream';
  timestamp: string;
  filesChanged?: number;
  user?: string;
}

interface LinkedArtifactsResponse {
  linked_artifacts: LinkedArtifactReference[];
  unlinked_references: string[];
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get the Lucide icon component for an artifact type
 */
function getArtifactIcon(type: ArtifactType): React.ComponentType<{ className?: string }> {
  const config = ARTIFACT_TYPES[type];
  if (!config) return LucideIcons.Package;

  const iconName = config.icon as keyof typeof LucideIcons;
  const IconComponent = LucideIcons[iconName];

  return (IconComponent as React.ComponentType<{ className?: string }>) || LucideIcons.Package;
}

/**
 * Get the color class for an artifact type
 */
function getArtifactColor(type: ArtifactType): string {
  const config = ARTIFACT_TYPES[type];
  return config?.color || 'text-muted-foreground';
}

/**
 * Check if entity has a valid upstream source (not local-only)
 */
function hasValidUpstreamSource(source: string | undefined | null): boolean {
  if (!source) return false;
  if (source === 'local' || source === 'unknown') return false;
  if (source.startsWith('local:')) return false;
  const segments = source.split('/').filter(Boolean);
  return segments.length >= 3 && !source.startsWith('local');
}

/**
 * Format relative time for display
 */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) {
    return 'just now';
  } else if (diffMins < 60) {
    return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
  } else if (diffDays < 30) {
    return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;
  } else {
    return date.toLocaleDateString();
  }
}

/**
 * Generate mock history entries based on artifact metadata
 */
function generateMockHistory(artifact: Artifact): HistoryEntry[] {
  const history: HistoryEntry[] = [];

  if (artifact.deployedAt) {
    const deployedDate = new Date(artifact.deployedAt);
    history.push({
      id: `deploy-${artifact.deployedAt}`,
      type: 'deploy',
      direction: 'downstream',
      timestamp: artifact.deployedAt,
      filesChanged: Math.floor(Math.random() * 5) + 1,
      user: 'You',
    });

    if (artifact.syncStatus === 'modified' || artifact.syncStatus === 'outdated') {
      const syncDate = new Date(deployedDate.getTime() - 2 * 60 * 60 * 1000);
      history.push({
        id: `sync-${syncDate.toISOString()}`,
        type: 'sync',
        direction: 'upstream',
        timestamp: syncDate.toISOString(),
        filesChanged: Math.floor(Math.random() * 3) + 1,
        user: 'You',
      });
    }
  }

  if (artifact.modifiedAt && artifact.modifiedAt !== artifact.deployedAt) {
    history.push({
      id: `sync-${artifact.modifiedAt}`,
      type: 'sync',
      direction: 'upstream',
      timestamp: artifact.modifiedAt,
      filesChanged: Math.floor(Math.random() * 4) + 1,
      user: 'You',
    });
  }

  if (artifact.syncStatus === 'conflict' && artifact.modifiedAt) {
    const rollbackDate = new Date(
      new Date(artifact.modifiedAt).getTime() + 1 * 60 * 60 * 1000
    );
    history.push({
      id: `rollback-${rollbackDate.toISOString()}`,
      type: 'rollback',
      direction: 'downstream',
      timestamp: rollbackDate.toISOString(),
      filesChanged: Math.floor(Math.random() * 3) + 1,
      user: 'You',
    });
  }

  return history.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
}

/**
 * Get color for history entry type
 */
function getHistoryTypeColor(type: HistoryEntry['type']): string {
  switch (type) {
    case 'deploy':
      return 'text-green-600 dark:text-green-400';
    case 'sync':
      return 'text-blue-600 dark:text-blue-400';
    case 'rollback':
      return 'text-orange-600 dark:text-orange-400';
    default:
      return 'text-muted-foreground';
  }
}

/**
 * Get label for history entry type
 */
function getHistoryTypeLabel(type: HistoryEntry['type']): string {
  switch (type) {
    case 'deploy':
      return 'Deployed';
    case 'sync':
      return 'Synced';
    case 'rollback':
      return 'Rolled Back';
    default:
      return type;
  }
}

// ============================================================================
// Tab Configuration
// ============================================================================

const TABS: Tab[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'contents', label: 'Contents' },
  { value: 'links', label: 'Links' },
  { value: 'collections', label: 'Collections' },
  { value: 'sources', label: 'Sources' },
  { value: 'history', label: 'History' },
];

// ============================================================================
// Main Component
// ============================================================================

/**
 * ArtifactDetailsModal - Discovery-focused modal for artifact browsing
 *
 * Shows artifact information with tabs for:
 * - Overview: Basic info, description, metadata, tags
 * - Contents: File tree and content viewer
 * - Links: Related/linked artifacts
 * - Collections: Which collections this artifact belongs to
 * - Sources: Upstream source information
 * - History: General artifact timeline
 */
export function ArtifactDetailsModal({
  artifact,
  open,
  onClose,
  initialTab = 'overview',
  onTabChange,
  returnTo,
  isLoading = false,
}: ArtifactDetailsModalProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // State
  const [activeTab, setActiveTab] = useState<ArtifactDetailsTab>(initialTab);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [showDeployDialog, setShowDeployDialog] = useState(false);
  const [showLinkingDialog, setShowLinkingDialog] = useState(false);
  const [localTags, setLocalTags] = useState<string[] | null>(null);

  // Source entry state for Sources tab
  const [sourceEntry, setSourceEntry] = useState<{
    sourceId: string;
    entryPath: string;
    sourceName: string;
  } | null>(null);
  const [isLoadingSource, setIsLoadingSource] = useState(false);

  // Get returnTo from props or URL
  const effectiveReturnTo = returnTo || searchParams.get('returnTo');

  // Sync activeTab with initialTab when modal opens
  useEffect(() => {
    if (open && initialTab) {
      setActiveTab(initialTab);
    }
  }, [open, initialTab]);

  // Reset selectedPath when artifact changes or modal closes
  useEffect(() => {
    setSelectedPath(null);
  }, [artifact?.id, open]);

  // Update URL when tab changes
  const handleTabChange = useCallback(
    (tab: string) => {
      const newTab = tab as ArtifactDetailsTab;
      setActiveTab(newTab);
      onTabChange?.(newTab);

      // Update URL state
      if (artifact) {
        const params = new URLSearchParams(searchParams.toString());
        params.set('artifact', artifact.id);
        params.set('tab', newTab);
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });
      }
    },
    [artifact, onTabChange, pathname, router, searchParams]
  );

  // Copy link handler
  const handleCopyLink = useCallback(() => {
    if (!artifact) return;

    const params = new URLSearchParams();
    params.set('artifact', artifact.id);
    params.set('tab', activeTab);
    const url = `${window.location.origin}${pathname}?${params.toString()}`;

    navigator.clipboard.writeText(url).then(() => {
      toast({
        title: 'Link copied',
        description: 'Artifact link copied to clipboard',
      });
    });
  }, [artifact, activeTab, pathname, toast]);

  // Handle return navigation
  const handleReturn = useCallback(() => {
    if (effectiveReturnTo) {
      router.push(effectiveReturnTo);
    }
  }, [effectiveReturnTo, router]);

  // Fetch tags for autocomplete
  const { data: tagsData, isLoading: isTagsLoading } = useTags(100);
  const availableTags = useMemo(() => {
    if (!tagsData?.items) return [];
    return tagsData.items.map((tag) => tag.name);
  }, [tagsData]);

  // Tag update mutation
  const { mutate: updateTags, isPending: isUpdatingTags } = useUpdateArtifactTags();

  // Handle tags change
  const handleTagsChange = useCallback(
    (newTags: string[]) => {
      if (!artifact) return;

      setLocalTags(newTags);

      updateTags(
        { artifactId: artifact.id, tags: newTags },
        {
          onSuccess: () => {
            toast({
              title: 'Tags updated',
              description: 'Artifact tags have been updated.',
            });
            queryClient.invalidateQueries({ queryKey: ['artifacts'] });
          },
          onError: (error) => {
            setLocalTags(null);
            toast({
              title: 'Failed to update tags',
              description: error instanceof Error ? error.message : 'Unknown error',
              variant: 'destructive',
            });
          },
        }
      );
    },
    [artifact, updateTags, toast, queryClient]
  );

  // Fetch marketplace sources for Sources tab
  const { data: sourcesData } = useSources(100);

  // Find source catalog entry when Sources tab is active
  useEffect(() => {
    if (!artifact?.source || !open || activeTab !== 'sources') {
      return;
    }

    const findSourceEntry = async () => {
      setIsLoadingSource(true);
      try {
        const allSources = sourcesData?.pages?.flatMap((page) => page.items) || [];
        const artifactSource = artifact.source || '';

        for (const source of allSources) {
          const repoPattern = `${source.owner}/${source.repo_name}`;
          if (
            artifactSource.includes(repoPattern) ||
            artifactSource.includes(source.repo_url)
          ) {
            try {
              const catalogResponse = await apiRequest<{
                items: Array<{ name: string; artifact_type: string; path: string }>;
              }>(
                `/marketplace/sources/${source.id}/artifacts?search=${encodeURIComponent(artifact.name)}&limit=10`
              );

              const entry = catalogResponse.items?.find(
                (e) => e.name === artifact.name && e.artifact_type === artifact.type
              );

              if (entry) {
                setSourceEntry({
                  sourceId: source.id,
                  entryPath: entry.path,
                  sourceName: `${source.owner}/${source.repo_name}`,
                });
                setIsLoadingSource(false);
                return;
              }
            } catch {
              // Continue to next source
            }
          }
        }

        setSourceEntry(null);
      } catch (error) {
        console.error('Failed to find source entry:', error);
        setSourceEntry(null);
      } finally {
        setIsLoadingSource(false);
      }
    };

    findSourceEntry();
  }, [artifact, open, activeTab, sourcesData]);

  // Generate history entries
  const historyEntries = useMemo(() => {
    if (!artifact) return [];
    return generateMockHistory(artifact);
  }, [artifact]);

  // Fetch file list
  const {
    data: filesData,
    isLoading: isFilesLoading,
    error: filesError,
  } = useQuery<FileListResponse>({
    queryKey: ['artifact-files', artifact?.id],
    queryFn: async () => {
      if (!artifact?.id) {
        throw new Error('Missing artifact ID');
      }

      const params = new URLSearchParams();
      if (artifact.collection) {
        params.set('collection', artifact.collection);
      }

      return await apiRequest<FileListResponse>(
        `/artifacts/${encodeURIComponent(artifact.id)}/files?${params.toString()}`
      );
    },
    enabled: !!artifact?.id && activeTab === 'contents',
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });

  // Fetch file content
  const {
    data: contentData,
    isLoading: isContentLoading,
    error: contentError,
  } = useQuery<FileContentResponse>({
    queryKey: ['artifact-file-content', artifact?.id, selectedPath],
    queryFn: async () => {
      if (!artifact?.id || !selectedPath) {
        throw new Error('Missing artifact ID or file path');
      }

      const params = new URLSearchParams();
      if (artifact.collection) {
        params.set('collection', artifact.collection);
      }

      return await apiRequest<FileContentResponse>(
        `/artifacts/${encodeURIComponent(artifact.id)}/files/${encodeURIComponent(selectedPath)}?${params.toString()}`
      );
    },
    enabled: !!artifact?.id && !!selectedPath,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });

  // Fetch linked artifacts
  const {
    data: linkedArtifactsData,
    isLoading: isLinkedArtifactsLoading,
    error: linkedArtifactsError,
    refetch: refetchLinkedArtifacts,
  } = useQuery<LinkedArtifactsResponse>({
    queryKey: ['linked-artifacts', artifact?.id],
    queryFn: async () => {
      if (!artifact?.id) {
        throw new Error('Missing artifact ID');
      }

      const params = new URLSearchParams();
      if (artifact.collection) {
        params.set('collection', artifact.collection);
      }

      return await apiRequest<LinkedArtifactsResponse>(
        `/artifacts/${encodeURIComponent(artifact.id)}/linked-artifacts?${params.toString()}`
      );
    },
    enabled: !!artifact?.id && activeTab === 'links',
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  // Handle link changes
  const handleLinkChange = useCallback(() => {
    refetchLinkedArtifacts();
    queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  }, [refetchLinkedArtifacts, queryClient]);

  // Handle file selection
  const handleFileSelect = useCallback((path: string) => {
    setSelectedPath(path);
  }, []);

  // Early return if no artifact and not loading
  if (!artifact && !isLoading) return null;

  // Show loading skeleton when modal is open but artifact is loading
  if (isLoading || !artifact) {
    return (
      <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
        <DialogContent className="flex h-[90vh] max-w-5xl flex-col gap-0 overflow-hidden p-0">
          <ModalHeaderSkeleton />
          <div className="border-b px-6">
            <div className="flex gap-4 py-2">
              {TABS.map((tab) => (
                <Skeleton key={tab.value} className="h-8 w-20 rounded-md" />
              ))}
            </div>
          </div>
          <OverviewTabSkeleton />
        </DialogContent>
      </Dialog>
    );
  }

  const Icon = getArtifactIcon(artifact.type);
  const iconColor = getArtifactColor(artifact.type);

  return (
    <>
      <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
        <DialogContent className="flex h-[90vh] max-w-5xl flex-col gap-0 overflow-hidden p-0">
          {/* Header */}
          <ModalHeader
            icon={Icon}
            iconClassName={iconColor}
            title={artifact.name}
            description={artifact.description}
            actions={
              <div className="flex items-center gap-2">
                {/* Return button if navigated from another page */}
                {effectiveReturnTo && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleReturn}
                    className="gap-2 text-muted-foreground hover:text-foreground"
                    aria-label="Return to previous page"
                  >
                    <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                    <span>Return</span>
                  </Button>
                )}

                {/* Cross navigation */}
                <CrossNavigationButtons
                  currentPage="collection"
                  artifactId={artifact.id}
                  collectionId={artifact.collection}
                  onNavigate={onClose}
                />

                {/* Copy link */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleCopyLink}
                  aria-label="Copy link to artifact"
                >
                  <Copy className="h-4 w-4" aria-hidden="true" />
                </Button>

                {/* Deploy button */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDeployDialog(true)}
                  className="gap-2"
                >
                  <Rocket className="h-4 w-4" aria-hidden="true" />
                  <span>Deploy</span>
                </Button>
              </div>
            }
          />

          {/* Tabs */}
          <Tabs
            value={activeTab}
            onValueChange={handleTabChange}
            className="flex min-h-0 flex-1 flex-col"
          >
            <div className="border-b px-6">
              <TabNavigation tabs={TABS} />
            </div>

            {/* Overview Tab */}
            <TabContentWrapper value="overview">
              <div className="space-y-6">
                {/* Description */}
                {artifact.description && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Description</h3>
                    <p className="text-sm text-muted-foreground">{artifact.description}</p>
                  </div>
                )}

                {/* Collections */}
                {artifact.collections && artifact.collections.length > 0 && (
                  <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                      <FolderOpen className="h-4 w-4" />
                      Collections
                    </h3>
                    <div className="flex flex-wrap items-center gap-2">
                      {artifact.collections.map((collection) => (
                        <Badge
                          key={collection.id || collection.name}
                          colorStyle={getCollectionColor(collection.name)}
                        >
                          {collection.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Origin */}
                {artifact.origin && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Origin</h3>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="capitalize">
                        {artifact.origin}
                      </Badge>
                      {artifact.origin === 'marketplace' && artifact.origin_source && (
                        <Badge variant="secondary">{artifact.origin_source}</Badge>
                      )}
                    </div>
                  </div>
                )}

                {/* Source */}
                <div>
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <GitBranch className="h-4 w-4" />
                    Source
                  </h3>
                  <p className="rounded bg-muted px-3 py-2 font-mono text-sm">
                    {artifact.source || 'Unknown'}
                  </p>
                </div>

                {/* Version */}
                {artifact.version && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Version</h3>
                    <p className="text-sm text-muted-foreground">{artifact.version}</p>
                  </div>
                )}

                {/* Author */}
                {artifact.author && (
                  <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                      <User className="h-4 w-4" />
                      Author
                    </h3>
                    <p className="text-sm text-muted-foreground">{artifact.author}</p>
                  </div>
                )}

                {/* License */}
                {artifact.license && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">License</h3>
                    <Badge variant="outline">{artifact.license}</Badge>
                  </div>
                )}

                {/* Tags */}
                <div>
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <Tag className="h-4 w-4" />
                    Tags
                  </h3>
                  <TagEditor
                    tags={localTags ?? artifact.tags ?? []}
                    onTagsChange={handleTagsChange}
                    availableTags={availableTags}
                    isLoading={isTagsLoading || isUpdatingTags}
                    disabled={isUpdatingTags}
                  />
                </div>

                {/* Aliases */}
                {artifact.aliases && artifact.aliases.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Aliases</h3>
                    <div className="flex flex-wrap gap-2">
                      {artifact.aliases.map((alias) => (
                        <Badge key={alias} variant="secondary">
                          {alias}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Dependencies */}
                {artifact.dependencies && artifact.dependencies.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Dependencies</h3>
                    <div className="flex flex-wrap gap-2">
                      {artifact.dependencies.map((dep) => (
                        <Badge key={dep} variant="secondary">
                          {dep}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Timestamps */}
                <div>
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <Calendar className="h-4 w-4" />
                    Timestamps
                  </h3>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div className="flex justify-between">
                      <span>Created:</span>
                      <span>{new Date(artifact.createdAt).toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Updated:</span>
                      <span>{new Date(artifact.updatedAt).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            </TabContentWrapper>

            {/* Contents Tab */}
            <TabsContent
              value="contents"
              className="mt-0 h-full min-h-0 flex-1 overflow-hidden data-[state=active]:flex data-[state=active]:flex-col"
            >
              <div className="flex min-h-0 min-w-0 flex-1 gap-0 overflow-hidden">
                {/* File Tree */}
                <div className="w-64 flex-shrink-0 overflow-hidden border-r lg:w-72">
                  <FileTree
                    entityId={artifact.id}
                    files={filesData?.files || []}
                    selectedPath={selectedPath}
                    onSelect={handleFileSelect}
                    isLoading={isFilesLoading}
                    readOnly
                  />
                </div>

                {/* Content Pane */}
                <div className="min-w-0 flex-1 overflow-hidden">
                  <ContentPane
                    path={selectedPath}
                    content={contentData?.content || null}
                    isLoading={isContentLoading}
                    error={contentError?.message || filesError?.message || null}
                    readOnly
                  />
                </div>
              </div>
            </TabsContent>

            {/* Links Tab */}
            <TabContentWrapper value="links">
              <LinkedArtifactsSection
                artifactId={artifact.id}
                linkedArtifacts={linkedArtifactsData?.linked_artifacts || []}
                unlinkedReferences={linkedArtifactsData?.unlinked_references || []}
                onLinkCreated={handleLinkChange}
                onLinkDeleted={handleLinkChange}
                onAddLinkClick={() => setShowLinkingDialog(true)}
                isLoading={isLinkedArtifactsLoading}
                error={
                  linkedArtifactsError instanceof Error
                    ? linkedArtifactsError.message
                    : linkedArtifactsError
                      ? 'Failed to load linked artifacts'
                      : null
                }
                onRetry={() => refetchLinkedArtifacts()}
              />
            </TabContentWrapper>

            {/* Collections Tab */}
            <TabContentWrapper value="collections">
              <ModalCollectionsTab artifact={artifact} />
            </TabContentWrapper>

            {/* Sources Tab */}
            <TabContentWrapper value="sources">
              <div className="space-y-4">
                <div className="text-sm font-medium text-muted-foreground">Imported From</div>

                {isLoadingSource ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : sourceEntry ? (
                  <div className="cursor-pointer rounded-lg border p-4 transition-colors hover:bg-muted/50">
                    <div className="flex items-center gap-3">
                      <Github className="h-5 w-5 text-muted-foreground" />
                      <div className="flex-1">
                        <div className="font-medium">{sourceEntry.sourceName}</div>
                        <div className="text-sm text-muted-foreground">
                          {sourceEntry.entryPath}
                        </div>
                        {artifact.version && (
                          <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                            <Tag className="h-3 w-3" />
                            <span>{artifact.version}</span>
                          </div>
                        )}
                      </div>
                      <ExternalLink className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>
                ) : artifact?.source && hasValidUpstreamSource(artifact.source) ? (
                  <div className="rounded-lg border p-4">
                    <div className="flex items-center gap-3">
                      <GitBranch className="h-5 w-5 text-muted-foreground" />
                      <div className="flex-1">
                        <div className="font-medium">Source</div>
                        <div className="text-sm text-muted-foreground">{artifact.source}</div>
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Unable to find the source entry in marketplace sources.
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <GitBranch className="h-12 w-12 text-muted-foreground/50" />
                    <p className="mt-4 text-sm text-muted-foreground">
                      No upstream source information available.
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      This artifact was created locally or imported without source tracking.
                    </p>
                  </div>
                )}
              </div>
            </TabContentWrapper>

            {/* History Tab */}
            <TabContentWrapper value="history">
              <div className="space-y-4">
                {historyEntries.length > 0 ? (
                  <div>
                    <h3 className="mb-4 text-sm font-medium">Activity Timeline</h3>
                    <div className="relative space-y-0">
                      {/* Timeline line */}
                      <div className="absolute bottom-0 left-4 top-0 w-px bg-border" />

                      {historyEntries.map((entry) => (
                        <div
                          key={entry.id}
                          className="pl-13 group relative -ml-2 rounded-lg py-2 pb-6 pl-11 pr-2 transition-colors last:pb-0 hover:bg-muted/30"
                        >
                          {/* Timeline dot */}
                          <div
                            className={cn(
                              'absolute left-4 top-2 z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 bg-background',
                              entry.type === 'deploy'
                                ? 'border-green-500'
                                : entry.type === 'sync'
                                  ? 'border-blue-500'
                                  : 'border-orange-500'
                            )}
                          >
                            {entry.direction === 'downstream' ? (
                              <ArrowDown className="h-4 w-4" />
                            ) : (
                              <ArrowUp className="h-4 w-4" />
                            )}
                          </div>

                          {/* Entry content */}
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <div className="mb-1 flex items-center gap-2">
                                <span
                                  className={cn(
                                    'text-sm font-medium',
                                    getHistoryTypeColor(entry.type)
                                  )}
                                >
                                  {getHistoryTypeLabel(entry.type)}
                                </span>
                                {entry.filesChanged && (
                                  <Badge variant="secondary" className="text-xs">
                                    <FileText className="mr-1 h-3 w-3" />
                                    {entry.filesChanged}{' '}
                                    {entry.filesChanged === 1 ? 'file' : 'files'}
                                  </Badge>
                                )}
                              </div>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Clock className="h-3 w-3" />
                                <span>{formatRelativeTime(new Date(entry.timestamp))}</span>
                                {entry.user && (
                                  <>
                                    <span>-</span>
                                    <User className="h-3 w-3" />
                                    <span>{entry.user}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {new Date(entry.timestamp).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="py-12 text-center">
                    <Clock className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
                    <h3 className="mb-2 text-lg font-semibold">No activity yet</h3>
                    <p className="mx-auto max-w-sm text-sm text-muted-foreground">
                      Activity such as deployments and syncs will appear here once you start
                      using this artifact.
                    </p>
                  </div>
                )}
              </div>
            </TabContentWrapper>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Deploy Dialog */}
      <DeployDialog
        artifact={artifact}
        isOpen={showDeployDialog}
        onClose={() => setShowDeployDialog(false)}
        onSuccess={() => {
          toast({
            title: 'Artifact deployed',
            description: `${artifact.name} has been deployed successfully.`,
          });
          queryClient.invalidateQueries({ queryKey: ['deployments'] });
        }}
      />

      {/* Artifact Linking Dialog */}
      <ArtifactLinkingDialog
        open={showLinkingDialog}
        onOpenChange={setShowLinkingDialog}
        artifactId={artifact.id}
        onSuccess={handleLinkChange}
      />
    </>
  );
}
