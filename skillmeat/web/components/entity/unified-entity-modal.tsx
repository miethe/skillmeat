'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import {
  Calendar,
  Tag,
  GitBranch,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  RotateCcw,
  ArrowUp,
  ArrowDown,
  FileText,
  User,
  GitMerge,
  RefreshCw,
  Github,
  ChevronDown,
  ChevronRight,
  Pencil,
} from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { LucideIcon } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Entity, ENTITY_TYPES } from '@/types/entity';
import { useEntityLifecycle } from '@/hooks/useEntityLifecycle';
import { DiffViewer } from '@/components/entity/diff-viewer';
import { RollbackDialog } from '@/components/entity/rollback-dialog';
import { MergeWorkflow } from '@/components/entity/merge-workflow';
import { FileTree } from '@/components/entity/file-tree';
import { ContentPane } from '@/components/entity/content-pane';
import { FileCreationDialog } from '@/components/entity/file-creation-dialog';
import { FileDeletionDialog } from '@/components/entity/file-deletion-dialog';
import { UnsavedChangesDialog } from '@/components/entity/unsaved-changes-dialog';
import { ProjectSelectorForDiff } from '@/components/entity/project-selector-for-diff';
import { SyncStatusTab } from '@/components/sync-status';
import { ParameterEditorModal } from '@/components/discovery/ParameterEditorModal';
import { useEditArtifactParameters } from '@/hooks/useDiscovery';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/api';
import type { ArtifactDiffResponse, ArtifactUpstreamDiffResponse, ArtifactSyncRequest } from '@/sdk';
import type { FileListResponse, FileContentResponse, FileUpdateRequest } from '@/types/files';
import type { ArtifactParameters } from '@/types/discovery';

interface UnifiedEntityModalProps {
  entity: Entity | null;
  open: boolean;
  onClose: () => void;
}

interface HistoryEntry {
  id: string;
  type: 'deploy' | 'sync' | 'rollback';
  direction: 'upstream' | 'downstream';
  timestamp: string;
  filesChanged?: number;
  user?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Truncate SHA or version string for display
 */
function truncateSha(sha: string | undefined, length: number = 7): string {
  if (!sha) return 'unknown';
  return sha.substring(0, length);
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
 * Generate mock history entries based on entity metadata
 */
function generateMockHistory(entity: Entity): HistoryEntry[] {
  const history: HistoryEntry[] = [];

  // Create history entries from available timestamps
  if (entity.deployedAt) {
    const deployedDate = new Date(entity.deployedAt);
    history.push({
      id: `deploy-${entity.deployedAt}`,
      type: 'deploy',
      direction: 'downstream',
      timestamp: entity.deployedAt,
      filesChanged: Math.floor(Math.random() * 5) + 1,
      user: 'You',
    });

    // Add a sync entry a bit before deployment if entity is modified
    if (entity.status === 'modified' || entity.status === 'outdated') {
      const syncDate = new Date(deployedDate.getTime() - 2 * 60 * 60 * 1000); // 2 hours before
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

  if (entity.modifiedAt && entity.modifiedAt !== entity.deployedAt) {
    // Add sync entry for modifications
    history.push({
      id: `sync-${entity.modifiedAt}`,
      type: 'sync',
      direction: 'upstream',
      timestamp: entity.modifiedAt,
      filesChanged: Math.floor(Math.random() * 4) + 1,
      user: 'You',
    });
  }

  // Add a rollback entry for conflict status
  if (entity.status === 'conflict' && entity.modifiedAt) {
    const rollbackDate = new Date(new Date(entity.modifiedAt).getTime() + 1 * 60 * 60 * 1000); // 1 hour after modification
    history.push({
      id: `rollback-${rollbackDate.toISOString()}`,
      type: 'rollback',
      direction: 'downstream',
      timestamp: rollbackDate.toISOString(),
      filesChanged: Math.floor(Math.random() * 3) + 1,
      user: 'You',
    });
  }

  // Sort by timestamp (most recent first)
  return history.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

// Mock data generator functions removed - using real API calls now

// ============================================================================
// Loading Skeleton
// ============================================================================

function EntityModalSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>

      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>

      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * UnifiedEntityModal - Unified modal for entity management
 *
 * Consolidated modal component that combines the best of both Sheet and Dialog approaches.
 * Uses Dialog for consistency with collection UI and provides comprehensive entity management.
 *
 * Features:
 * - Overview tab with metadata, status, version, tags, timestamps, location
 * - Contents tab with file tree, file creation, and file deletion
 * - Sync Status tab with deploy/sync buttons, diff viewer, status alerts
 * - History tab with timeline of deploy/sync/rollback events
 * - Skeleton loading state
 * - Rollback dialog integration
 * - Full TypeScript support
 *
 * @example
 * ```tsx
 * <UnifiedEntityModal
 *   entity={selectedEntity}
 *   open={isModalOpen}
 *   onClose={() => setIsModalOpen(false)}
 * />
 * ```
 */
export function UnifiedEntityModal({ entity, open, onClose }: UnifiedEntityModalProps) {
  const [activeTab, setActiveTab] = useState('overview');
  const { deployEntity, syncEntity, refetch } = useEntityLifecycle();
  const [isDeploying, setIsDeploying] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [showRollbackDialog, setShowRollbackDialog] = useState(false);
  const [showMergeWorkflow, setShowMergeWorkflow] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [showFileCreationDialog, setShowFileCreationDialog] = useState(false);
  const [showFileDeletionDialog, setShowFileDeletionDialog] = useState(false);
  const [fileToDelete, setFileToDelete] = useState<string | null>(null);
  // Selected project for diff comparison (when viewing collection-mode entities)
  const [selectedProjectForDiff, setSelectedProjectForDiff] = useState<string | null>(null);
  // Upstream diff section collapsed/expanded state
  const [isUpstreamExpanded, setIsUpstreamExpanded] = useState(false);
  // Edit mode state (lifted from ContentPane)
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [showUnsavedChangesDialog, setShowUnsavedChangesDialog] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState<{
    type: 'file' | 'tab';
    target: string;
  } | null>(null);
  // Parameter editor state
  const [showParameterEditor, setShowParameterEditor] = useState(false);
  const { mutateAsync: updateParameters } = useEditArtifactParameters();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Generate mock history entries
  const historyEntries = useMemo(() => {
    if (!entity) return [];
    return generateMockHistory(entity);
  }, [entity]);

  // Fetch file list from API
  const {
    data: filesData,
    isLoading: isFilesLoading,
    error: filesError,
    refetch: refetchFiles,
  } = useQuery<FileListResponse>({
    queryKey: ['artifact-files', entity?.id],
    queryFn: async () => {
      if (!entity?.id) {
        throw new Error('Missing entity ID');
      }

      const params = new URLSearchParams();
      if (entity.collection) {
        params.set('collection', entity.collection);
      }

      return await apiRequest<FileListResponse>(
        `/artifacts/${encodeURIComponent(entity.id)}/files?${params.toString()}`
      );
    },
    enabled: !!entity?.id && activeTab === 'contents',
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });

  // Fetch file content when a file is selected
  const {
    data: contentData,
    isLoading: isContentLoading,
    error: contentError,
    refetch: refetchContent,
  } = useQuery<FileContentResponse>({
    queryKey: ['artifact-file-content', entity?.id, selectedPath],
    queryFn: async () => {
      if (!entity?.id || !selectedPath) {
        throw new Error('Missing entity ID or file path');
      }

      const params = new URLSearchParams();
      if (entity.collection) {
        params.set('collection', entity.collection);
      }

      return await apiRequest<FileContentResponse>(
        `/artifacts/${entity.id}/files/${encodeURIComponent(selectedPath)}?${params.toString()}`
      );
    },
    enabled: !!entity?.id && !!selectedPath,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });

  // Check if there are unsaved changes
  const hasUnsavedChanges = isEditing && editedContent !== (contentData?.content || '');

  // Determine which project path to use for diff
  // If entity has projectPath (project-mode), use that
  // If entity is collection-mode but user selected a project, use selectedProjectForDiff
  const effectiveProjectPath = entity?.projectPath || selectedProjectForDiff;

  // Fetch diff data when sync tab is active and we have a project path to compare against
  // Allow diff fetching for ALL statuses (synced, modified, outdated, conflict)
  // Key requirement: must have a valid entity ID and effectiveProjectPath
  const shouldFetchDiff = !!(activeTab === 'sync' && entity?.id && effectiveProjectPath);

  const {
    data: diffData,
    isLoading: isDiffLoading,
    error: diffError,
    refetch: refetchDiff,
  } = useQuery<ArtifactDiffResponse>({
    queryKey: ['artifact-diff', entity?.id, effectiveProjectPath],
    queryFn: async () => {
      if (!entity?.id) {
        throw new Error('Missing entity ID for diff');
      }

      if (!effectiveProjectPath) {
        throw new Error('Missing project path for diff');
      }

      // Ensure projectPath is properly encoded
      const params = new URLSearchParams({
        project_path: effectiveProjectPath,
      });

      if (entity.collection) {
        params.set('collection', entity.collection);
      }

      try {
        const response = await apiRequest<ArtifactDiffResponse>(
          `/artifacts/${encodeURIComponent(entity.id)}/diff?${params.toString()}`
        );

        // Validate response structure
        if (!response || typeof response !== 'object') {
          throw new Error('Invalid diff response format');
        }

        return response;
      } catch (error) {
        // Log error for debugging
        console.error('Diff fetch error:', error);
        throw error;
      }
    },
    enabled: shouldFetchDiff,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
    retry: 2, // Retry failed requests up to 2 times
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
  });

  // Fetch upstream diff data when sync tab is active
  // This compares the collection version against the GitHub upstream source
  const {
    data: upstreamDiff,
    isLoading: upstreamLoading,
    error: upstreamError,
    refetch: refetchUpstream,
  } = useQuery<ArtifactUpstreamDiffResponse>({
    queryKey: ['upstream-diff', entity?.id, entity?.collection],
    queryFn: async () => {
      if (!entity?.id) {
        throw new Error('Missing entity ID for upstream diff');
      }

      const params = new URLSearchParams();
      if (entity.collection) {
        params.set('collection', entity.collection);
      }

      try {
        const response = await apiRequest<ArtifactUpstreamDiffResponse>(
          `/artifacts/${encodeURIComponent(entity.id)}/upstream-diff?${params.toString()}`
        );

        // Validate response structure
        if (!response || typeof response !== 'object') {
          throw new Error('Invalid upstream diff response format');
        }

        return response;
      } catch (error) {
        // Log error for debugging
        console.error('Upstream diff fetch error:', error);
        throw error;
      }
    },
    enabled: activeTab === 'sync' && !!entity?.id,
    staleTime: 60 * 1000, // Cache for 1 minute (upstream changes less frequently)
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
    retry: 2, // Retry failed requests up to 2 times
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
  });

  // Track if we've shown the error toast to prevent spam
  const shownErrorRef = useRef<string | null>(null);

  // Show toast notification when diff fetch fails (only once per unique error)
  useEffect(() => {
    if (diffError && shouldFetchDiff && activeTab === 'sync') {
      const errorMessage = diffError instanceof Error ? diffError.message : 'Failed to load diff';

      // Only show toast if this is a new error message
      if (shownErrorRef.current !== errorMessage) {
        shownErrorRef.current = errorMessage;
        toast({
          title: 'Diff Load Failed',
          description: errorMessage,
          variant: 'destructive',
        });
      }
    } else if (!diffError) {
      // Reset when error is cleared
      shownErrorRef.current = null;
    }
  }, [diffError, shouldFetchDiff, activeTab, toast]);

  if (!entity) {
    return null;
  }

  const config = ENTITY_TYPES[entity.type];
  const IconComponent = (LucideIcons as any)[config.icon] as LucideIcon;

  // ============================================================================
  // Event Handlers
  // ============================================================================

  const handleDeploy = async () => {
    if (!entity.projectPath) {
      toast({
        title: 'Deploy Failed',
        description: 'Please select a project to deploy to',
        variant: 'destructive',
      });
      return;
    }

    setIsDeploying(true);
    try {
      await deployEntity(entity.id, entity.projectPath);
      toast({
        title: 'Deploy Successful',
        description: `${entity.name} has been deployed to the project.`,
      });
      // Refresh entity data after successful deployment
      refetch();
    } catch (error) {
      console.error('Deploy failed:', error);
      toast({
        title: 'Deploy Failed',
        description: error instanceof Error ? error.message : 'Failed to deploy entity',
        variant: 'destructive',
      });
    } finally {
      setIsDeploying(false);
    }
  };

  const handleSync = async () => {
    if (!entity.projectPath) {
      toast({
        title: 'Sync Failed',
        description: 'Please select a project to sync with',
        variant: 'destructive',
      });
      return;
    }

    setIsSyncing(true);
    try {
      await syncEntity(entity.id, entity.projectPath);
      toast({
        title: 'Sync Successful',
        description: `${entity.name} has been synced with upstream.`,
      });
      // Refresh entity data after successful sync
      refetch();
    } catch (error) {
      console.error('Sync failed:', error);
      toast({
        title: 'Sync Failed',
        description: error instanceof Error ? error.message : 'Failed to sync entity',
        variant: 'destructive',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRollback = async () => {
    if (!entity.projectPath) {
      toast({
        title: 'Rollback Failed',
        description: 'Please select a project to rollback',
        variant: 'destructive',
      });
      return;
    }

    setIsRollingBack(true);
    try {
      // Call sync API with 'theirs' strategy to pull collection version
      const request: ArtifactSyncRequest = {
        project_path: entity.projectPath,
        strategy: 'theirs', // Take collection version
        force: true, // Force overwrite local changes
      };

      await apiRequest(`/artifacts/${encodeURIComponent(entity.id)}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      toast({
        title: 'Rollback Successful',
        description: `${entity.name} has been rolled back to the collection version.`,
      });

      // Refresh the entity list
      refetch();
    } catch (error) {
      console.error('Rollback failed:', error);
      toast({
        title: 'Rollback Failed',
        description: error instanceof Error ? error.message : 'Failed to rollback entity',
        variant: 'destructive',
      });
      throw error; // Re-throw to let dialog handle it
    } finally {
      setIsRollingBack(false);
    }
  };

  const handleSaveFile = async (content: string) => {
    if (!entity?.id || !selectedPath) {
      toast({
        title: 'Save Failed',
        description: 'No file selected',
        variant: 'destructive',
      });
      return;
    }

    try {
      const params = new URLSearchParams();
      if (entity.collection) {
        params.set('collection', entity.collection);
      }

      const requestBody: FileUpdateRequest = { content };

      await apiRequest<FileContentResponse>(
        `/artifacts/${entity.id}/files/${encodeURIComponent(selectedPath)}?${params.toString()}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        }
      );

      toast({
        title: 'File Saved',
        description: `${selectedPath} has been updated successfully.`,
      });

      // Refresh file content
      await refetchContent();
    } catch (error) {
      console.error('Save file failed:', error);
      toast({
        title: 'Save Failed',
        description: error instanceof Error ? error.message : 'Failed to save file',
        variant: 'destructive',
      });
      throw error;
    }
  };

  const handleCreateFile = async (fileName: string) => {
    if (!entity?.id) {
      throw new Error('No entity selected');
    }

    try {
      const params = new URLSearchParams();
      if (entity.collection) {
        params.set('collection', entity.collection);
      }

      const requestBody: FileUpdateRequest = { content: '' };

      await apiRequest<FileContentResponse>(
        `/artifacts/${entity.id}/files/${encodeURIComponent(fileName)}?${params.toString()}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        }
      );

      toast({
        title: 'File Created',
        description: `${fileName} has been created successfully.`,
      });

      // Refresh file list
      await refetchFiles();

      // Invalidate and refetch file list query
      queryClient.invalidateQueries({ queryKey: ['artifact-files', entity.id] });

      // Auto-select the newly created file
      setSelectedPath(fileName);
    } catch (error) {
      console.error('Create file failed:', error);
      throw error;
    }
  };

  const handleDeleteFile = async (filePath: string) => {
    setFileToDelete(filePath);
    setShowFileDeletionDialog(true);
  };

  const handleConfirmDelete = async () => {
    if (!entity?.id || !fileToDelete) {
      throw new Error('No file selected for deletion');
    }

    try {
      const params = new URLSearchParams();
      if (entity.collection) {
        params.set('collection', entity.collection);
      }

      await apiRequest(
        `/artifacts/${entity.id}/files/${encodeURIComponent(fileToDelete)}?${params.toString()}`,
        {
          method: 'DELETE',
        }
      );

      toast({
        title: 'File Deleted',
        description: `${fileToDelete} has been deleted successfully.`,
      });

      // Clear selection if deleted file was selected
      if (selectedPath === fileToDelete) {
        setSelectedPath(null);
      }

      // Refresh file list
      await refetchFiles();

      // Invalidate and refetch file list query
      queryClient.invalidateQueries({ queryKey: ['artifact-files', entity.id] });
    } catch (error) {
      console.error('Delete file failed:', error);
      throw error;
    }
  };

  const handleRetryDiff = async () => {
    try {
      await refetchDiff();
      toast({
        title: 'Diff Reloaded',
        description: 'Successfully reloaded the diff data.',
      });
    } catch (error) {
      console.error('Retry diff failed:', error);
      toast({
        title: 'Retry Failed',
        description: error instanceof Error ? error.message : 'Failed to retry diff',
        variant: 'destructive',
      });
    }
  };

  const handleRefreshUpstream = async () => {
    try {
      await refetchUpstream();
      toast({
        title: 'Upstream Check Complete',
        description: 'Successfully checked for upstream updates.',
      });
    } catch (error) {
      console.error('Refresh upstream failed:', error);
      toast({
        title: 'Refresh Failed',
        description: error instanceof Error ? error.message : 'Failed to check upstream',
        variant: 'destructive',
      });
    }
  };

  // Handle file selection with unsaved changes guard
  const handleFileSelect = (path: string) => {
    if (hasUnsavedChanges) {
      setPendingNavigation({ type: 'file', target: path });
      setShowUnsavedChangesDialog(true);
    } else {
      setSelectedPath(path);
      setIsEditing(false);
      setEditedContent('');
    }
  };

  // Handle tab change with unsaved changes guard
  const handleTabChange = (tab: string) => {
    if (hasUnsavedChanges && activeTab === 'contents') {
      setPendingNavigation({ type: 'tab', target: tab });
      setShowUnsavedChangesDialog(true);
    } else {
      setActiveTab(tab);
      if (tab !== 'contents') {
        setIsEditing(false);
        setEditedContent('');
      }
    }
  };

  // Handle discard from unsaved changes dialog
  const handleDiscardChanges = () => {
    if (pendingNavigation) {
      if (pendingNavigation.type === 'file') {
        setSelectedPath(pendingNavigation.target);
      } else {
        setActiveTab(pendingNavigation.target);
      }
      setIsEditing(false);
      setEditedContent('');
      setPendingNavigation(null);
    }
  };

  // Handle save from unsaved changes dialog
  const handleSaveAndNavigate = async () => {
    if (pendingNavigation && selectedPath) {
      await handleSaveFile(editedContent);
      if (pendingNavigation.type === 'file') {
        setSelectedPath(pendingNavigation.target);
      } else {
        setActiveTab(pendingNavigation.target);
      }
      setIsEditing(false);
      setEditedContent('');
      setPendingNavigation(null);
      setShowUnsavedChangesDialog(false);
    }
  };

  const handleSaveParameters = async (parameters: ArtifactParameters) => {
    if (!entity) return;

    try {
      await updateParameters({
        artifactId: entity.id,
        parameters,
      });

      toast({
        title: 'Parameters Updated',
        description: `Updated parameters for ${entity.name}`,
      });

      // Refresh entity data
      refetch();
    } catch (error) {
      console.error('Parameter update failed:', error);
      toast({
        title: 'Update Failed',
        description: error instanceof Error ? error.message : 'Failed to update parameters',
        variant: 'destructive',
      });
      throw error;
    }
  };

  // ============================================================================
  // Status Helpers
  // ============================================================================

  const getStatusIcon = () => {
    switch (entity.status) {
      case 'synced':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'modified':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'outdated':
        return <Clock className="h-4 w-4 text-blue-500" />;
      case 'conflict':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusLabel = () => {
    switch (entity.status) {
      case 'synced':
        return 'Synced';
      case 'modified':
        return 'Modified';
      case 'outdated':
        return 'Outdated';
      case 'conflict':
        return 'Conflict';
      default:
        return 'Unknown';
    }
  };

  const getHistoryTypeLabel = (type: HistoryEntry['type']) => {
    switch (type) {
      case 'deploy':
        return 'Deployed';
      case 'sync':
        return 'Synced';
      case 'rollback':
        return 'Rolled back';
      default:
        return type;
    }
  };

  const getHistoryTypeColor = (type: HistoryEntry['type']) => {
    switch (type) {
      case 'deploy':
        return 'text-green-600 dark:text-green-400';
      case 'sync':
        return 'text-blue-600 dark:text-blue-400';
      case 'rollback':
        return 'text-orange-600 dark:text-orange-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  // ============================================================================
  // Render Upstream Status Section
  // ============================================================================

  const renderUpstreamSection = () => {
    // Check if artifact has a GitHub source (not local-only)
    const hasUpstreamSource = entity?.source && !entity.source.startsWith('local:');

    // Don't show upstream section for local-only artifacts
    if (!hasUpstreamSource) {
      return null;
    }

    return (
      <div className="space-y-3">
        <Card>
          <CardHeader
            className="cursor-pointer transition-colors hover:bg-muted/50"
            onClick={() => setIsUpstreamExpanded(!isUpstreamExpanded)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Github className="h-4 w-4" />
                <CardTitle className="text-sm font-medium">Upstream Status</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRefreshUpstream();
                  }}
                  disabled={upstreamLoading}
                  className="h-8 px-2"
                >
                  <RefreshCw className={`h-3 w-3 ${upstreamLoading ? 'animate-spin' : ''}`} />
                </Button>
                {isUpstreamExpanded ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent className="pt-0">
            {/* Loading State */}
            {upstreamLoading && (
              <div className="flex items-center gap-3 py-4">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Checking upstream...</p>
              </div>
            )}

            {/* Error State - Local-only or fetch failed */}
            {!upstreamLoading && upstreamError && (
              <div className="py-2">
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-sm">
                    {upstreamError instanceof Error && upstreamError.message.includes('no upstream')
                      ? 'This artifact has no upstream source (local-only).'
                      : upstreamError instanceof Error
                        ? upstreamError.message
                        : 'Failed to check upstream status'}
                  </AlertDescription>
                </Alert>
              </div>
            )}

            {/* Success State */}
            {!upstreamLoading && !upstreamError && upstreamDiff && (
              <div className="space-y-3">
                {/* Status Badge and Version Info */}
                <div className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-2">
                    {upstreamDiff.has_changes ? (
                      <>
                        <Badge variant="secondary" className="gap-1">
                          <Clock className="h-3 w-3" />
                          Update Available
                        </Badge>
                      </>
                    ) : (
                      <>
                        <Badge variant="default" className="gap-1 bg-green-600">
                          <CheckCircle2 className="h-3 w-3" />
                          Up to Date
                        </Badge>
                      </>
                    )}
                  </div>
                </div>

                {/* Version SHA Info */}
                <div className="space-y-1 text-xs text-muted-foreground">
                  <div className="flex justify-between">
                    <span>Current Collection:</span>
                    <code className="font-mono">{truncateSha(entity?.version)}</code>
                  </div>
                  <div className="flex justify-between">
                    <span>Upstream Version:</span>
                    <code className="font-mono">
                      {truncateSha(upstreamDiff.upstream_version || 'latest')}
                    </code>
                  </div>
                </div>

                {/* Expandable Diff Viewer */}
                {isUpstreamExpanded &&
                  upstreamDiff.has_changes &&
                  upstreamDiff.files &&
                  upstreamDiff.files.length > 0 && (
                    <div className="mt-4 overflow-hidden rounded-lg border">
                      <div className="flex-shrink-0 border-b bg-muted/30 px-3 py-2">
                        <p className="text-xs font-medium">Changes from Upstream</p>
                      </div>
                      <div className="h-[400px]">
                        <DiffViewer
                          files={upstreamDiff.files}
                          leftLabel="Collection"
                          rightLabel="Upstream"
                        />
                      </div>
                    </div>
                  )}

                {/* No changes message when expanded */}
                {isUpstreamExpanded && !upstreamDiff.has_changes && (
                  <div className="py-4 text-center">
                    <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-green-500" />
                    <p className="text-sm font-medium">No upstream changes</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Your collection is up to date with the upstream source
                    </p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  };

  // ============================================================================
  // Render Diff Section
  // ============================================================================

  const renderDiffSection = () => {
    // Show project selector for collection-mode entities (no projectPath)
    // This allows users to select which project to compare against
    if (!entity.projectPath && entity.collection) {
      return (
        <div>
          <ProjectSelectorForDiff
            entityId={entity.id}
            entityName={entity.name}
            entityType={entity.type}
            collection={entity.collection}
            onProjectSelected={(projectPath) => {
              setSelectedProjectForDiff(projectPath);
              // Auto-refetch diff once project is selected
              if (shouldFetchDiff) {
                refetchDiff();
              }
            }}
          />
        </div>
      );
    }

    // If we have an effective project path (either from entity or user selection), show diff viewer
    if (!effectiveProjectPath) {
      return null;
    }

    return (
      <div>
        <h3 className="mb-2 text-sm font-medium">Changes</h3>

        {/* Loading State */}
        {isDiffLoading && (
          <div className="flex flex-col items-center justify-center gap-3 rounded-lg border bg-muted/20 p-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <div className="text-center">
              <p className="text-sm font-medium text-foreground">Loading diff...</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Comparing collection and project versions
              </p>
            </div>
          </div>
        )}

        {/* Error State */}
        {!isDiffLoading && diffError && (
          <div className="overflow-hidden rounded-lg border border-red-500/20 bg-red-500/10">
            <div className="p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-700 dark:text-red-400" />
                <div className="min-w-0 flex-1">
                  <p className="mb-1 text-sm font-medium text-red-700 dark:text-red-400">
                    Failed to load diff
                  </p>
                  <p className="break-words text-xs text-red-600/80 dark:text-red-400/80">
                    {diffError instanceof Error ? diffError.message : 'An unknown error occurred'}
                  </p>
                  {!entity.projectPath && (
                    <p className="mt-2 text-xs text-red-600/80 dark:text-red-400/80">
                      Project path is missing. Please ensure the entity is properly configured.
                    </p>
                  )}
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <Button
                  onClick={handleRetryDiff}
                  variant="outline"
                  size="sm"
                  className="border-red-500/20 text-red-700 hover:bg-red-500/10 dark:text-red-400"
                >
                  <RefreshCw className="mr-1.5 h-3 w-3" />
                  Retry
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Success State with Data */}
        {!isDiffLoading && !diffError && diffData && (
          <>
            {/* Has changes - show diff viewer */}
            {diffData.has_changes && diffData.files && diffData.files.length > 0 ? (
              <div className="overflow-hidden rounded-lg border bg-background">
                <DiffViewer
                  files={diffData.files}
                  leftLabel={entity.collection ? 'Collection' : 'Current'}
                  rightLabel={entity.projectPath ? 'Project' : 'Upstream'}
                />
              </div>
            ) : (
              /* No changes detected */
              <div className="rounded-lg border bg-muted/20 p-6">
                <div className="flex flex-col items-center justify-center gap-2">
                  <CheckCircle2 className="h-8 w-8 text-green-500" />
                  <p className="text-sm font-medium text-foreground">No changes detected</p>
                  <p className="max-w-sm text-center text-xs text-muted-foreground">
                    The collection and project versions are identical
                  </p>
                </div>
              </div>
            )}
          </>
        )}

        {/* Edge case: No diff data and no error (shouldn't happen) */}
        {!isDiffLoading && !diffError && !diffData && (
          <div className="rounded-lg border bg-muted/20 p-6">
            <div className="flex flex-col items-center justify-center gap-2">
              <AlertCircle className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm font-medium text-foreground">No diff data available</p>
              <p className="max-w-sm text-center text-xs text-muted-foreground">
                Unable to retrieve diff information
              </p>
              <Button onClick={handleRetryDiff} variant="outline" size="sm" className="mt-2">
                <RefreshCw className="mr-1.5 h-3 w-3" />
                Try Again
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  };

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <>
      <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="flex h-[90vh] max-h-[90vh] max-w-4xl flex-col overflow-hidden p-0 lg:max-w-6xl xl:max-w-7xl min-h-0">
          {/* Header Section - Fixed */}
          <div className="border-b px-6 pb-4 pt-6">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-3">
                {IconComponent && <IconComponent className={`h-5 w-5 ${config.color}`} />}
                <span className="flex-1">{entity.name}</span>
                <Badge variant="outline" className="gap-1">
                  {config.label}
                </Badge>
                {entity.status && (
                  <Badge variant={entity.status === 'synced' ? 'default' : 'secondary'}>
                    {getStatusLabel()}
                  </Badge>
                )}
              </DialogTitle>
            </DialogHeader>
          </div>

          {/* Tabs Section */}
          <Tabs
            value={activeTab}
            onValueChange={handleTabChange}
            className="flex h-full min-h-0 flex-1 flex-col px-6"
          >
            <TabsList className="h-auto w-full justify-start rounded-none border-b bg-transparent p-0">
              <TabsTrigger
                value="overview"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                Overview
              </TabsTrigger>
              <TabsTrigger
                value="contents"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                Contents
              </TabsTrigger>
              <TabsTrigger
                value="sync"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                Sync Status
              </TabsTrigger>
              <TabsTrigger
                value="history"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                History
              </TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="mt-0 flex-1">
              <ScrollArea className="h-[calc(90vh-12rem)]">
                <div className="space-y-6 py-4">
                  {/* Edit Parameters Button */}
                  <div className="flex justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowParameterEditor(true)}
                    >
                      <Pencil className="h-4 w-4 mr-2" />
                      Edit Parameters
                    </Button>
                  </div>
                  {/* Status */}
                  {entity.status && (
                    <div>
                      <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                        {getStatusIcon()}
                        Status
                      </h3>
                      <div className="flex items-center gap-2">
                        <Badge variant={entity.status === 'synced' ? 'default' : 'secondary'}>
                          {getStatusLabel()}
                        </Badge>
                      </div>
                    </div>
                  )}

                  {/* Description */}
                  {entity.description && (
                    <div>
                      <h3 className="mb-2 text-sm font-medium">Description</h3>
                      <p className="text-sm text-muted-foreground">{entity.description}</p>
                    </div>
                  )}

                  {/* Source */}
                  <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                      <GitBranch className="h-4 w-4" />
                      Source
                    </h3>
                    <p className="rounded bg-muted px-3 py-2 font-mono text-sm">
                      {entity.source || 'Unknown'}
                    </p>
                  </div>

                  {/* Version */}
                  {entity.version && (
                    <div>
                      <h3 className="mb-2 text-sm font-medium">Version</h3>
                      <p className="text-sm text-muted-foreground">{entity.version}</p>
                    </div>
                  )}

                  {/* Tags */}
                  {entity.tags && entity.tags.length > 0 && (
                    <div>
                      <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                        <Tag className="h-4 w-4" />
                        Tags
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {entity.tags.map((tag) => (
                          <Badge key={tag} variant="outline">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Aliases */}
                  {entity.aliases && entity.aliases.length > 0 && (
                    <div>
                      <h3 className="mb-2 text-sm font-medium">Aliases</h3>
                      <div className="flex flex-wrap gap-2">
                        {entity.aliases.map((alias) => (
                          <Badge key={alias} variant="secondary">
                            {alias}
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
                      {entity.deployedAt && (
                        <div className="flex justify-between">
                          <span>Deployed:</span>
                          <span>{new Date(entity.deployedAt).toLocaleString()}</span>
                        </div>
                      )}
                      {entity.modifiedAt && (
                        <div className="flex justify-between">
                          <span>Modified:</span>
                          <span>{new Date(entity.modifiedAt).toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Location */}
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Location</h3>
                    <div className="space-y-2 text-sm text-muted-foreground">
                      {entity.collection && (
                        <div className="flex justify-between">
                          <span>Collection:</span>
                          <span>{entity.collection}</span>
                        </div>
                      )}
                      {entity.projectPath && (
                        <div className="flex flex-col gap-1">
                          <span>Project Path:</span>
                          <code className="break-all rounded bg-muted px-2 py-1 text-xs">
                            {entity.projectPath}
                          </code>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </ScrollArea>
            </TabsContent>

            {/* Contents Tab */}
            <TabsContent value="contents" className="mt-0 min-h-0 flex-1 overflow-hidden">
              <div className="flex h-[calc(90vh-12rem)] min-w-0 gap-0 overflow-hidden">
                {/* File Tree - Left Panel - Narrower in edit mode */}
                <div className={cn(
                  "flex-shrink-0 overflow-hidden border-r transition-all duration-200",
                  isEditing ? "w-48" : "w-64 lg:w-72"
                )}>
                  <FileTree
                    entityId={entity.id}
                    files={filesData?.files || []}
                    selectedPath={selectedPath}
                    onSelect={handleFileSelect}
                    onAddFile={() => setShowFileCreationDialog(true)}
                    onDeleteFile={handleDeleteFile}
                    isLoading={isFilesLoading}
                  />
                </div>

                {/* Content Pane - Right Panel */}
                <div className="min-w-0 flex-1 overflow-hidden">
                  <ContentPane
                    path={selectedPath}
                    content={contentData?.content || null}
                    isLoading={isContentLoading}
                    error={contentError?.message || filesError?.message || null}
                    isEditing={isEditing}
                    editedContent={editedContent}
                    onEditStart={() => setIsEditing(true)}
                    onEditChange={setEditedContent}
                    onSave={handleSaveFile}
                    onCancel={() => {
                      setIsEditing(false);
                      setEditedContent('');
                    }}
                  />
                </div>
              </div>
            </TabsContent>

            {/* Sync Status Tab */}
            <TabsContent value="sync" className="mt-0 flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
              <SyncStatusTab
                entity={entity}
                mode={entity.projectPath ? 'project' : 'collection'}
                projectPath={entity.projectPath || selectedProjectForDiff || undefined}
                onClose={onClose}
              />
            </TabsContent>

            {/* History Tab */}
            <TabsContent value="history" className="mt-0 flex-1">
              <ScrollArea className="h-[calc(90vh-12rem)]">
                <div className="space-y-4 py-4">
                  {/* Rollback Section */}
                  {(entity.status === 'modified' || entity.status === 'conflict') &&
                    entity.projectPath && (
                      <div className="rounded-lg border bg-muted/20 p-4">
                        <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                          <RotateCcw className="h-4 w-4" />
                          Rollback to Collection Version
                        </h3>
                        <p className="mb-4 text-sm text-muted-foreground">
                          Your local version has been modified. You can rollback to the collection
                          version to discard all local changes.
                        </p>
                        <Button
                          onClick={() => setShowRollbackDialog(true)}
                          variant="outline"
                          size="sm"
                          disabled={isRollingBack}
                        >
                          <RotateCcw className="mr-2 h-4 w-4" />
                          {isRollingBack ? 'Rolling Back...' : 'Rollback to Collection'}
                        </Button>
                      </div>
                    )}

                  {/* History Timeline */}
                  {historyEntries.length > 0 ? (
                    <div>
                      <h3 className="mb-4 text-sm font-medium">Sync History</h3>
                      <div className="relative space-y-0">
                        {/* Timeline line */}
                        <div className="absolute bottom-0 left-4 top-0 w-px bg-border" />

                        {historyEntries.map((entry) => (
                          <div
                            key={entry.id}
                            className="pl-13 group relative -ml-2 rounded-lg py-2 pb-6 pl-11 pr-2 transition-colors last:pb-0 hover:bg-muted/30"
                          >
                            {/* Timeline dot and icon */}
                            <div
                              className={`absolute left-4 top-2 z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 bg-background ${
                                entry.type === 'deploy'
                                  ? 'border-green-500'
                                  : entry.type === 'sync'
                                    ? 'border-blue-500'
                                    : 'border-orange-500'
                              }`}
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
                                    className={`text-sm font-medium ${getHistoryTypeColor(entry.type)}`}
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
                                      <span>•</span>
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
                    // Empty state
                    <div className="py-12 text-center">
                      <Clock className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
                      <h3 className="mb-2 text-lg font-semibold">No sync history yet</h3>
                      <p className="mx-auto max-w-sm text-sm text-muted-foreground">
                        Sync operations and deployments will appear here once you start managing
                        this entity.
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Rollback Confirmation Dialog */}
      <RollbackDialog
        entity={entity}
        open={showRollbackDialog}
        onOpenChange={setShowRollbackDialog}
        onConfirm={handleRollback}
      />

      {/* Merge Workflow Dialog */}
      {showMergeWorkflow && entity.projectPath && (
        <Dialog open={showMergeWorkflow} onOpenChange={setShowMergeWorkflow}>
          <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Resolve Conflicts - {entity.name}</DialogTitle>
            </DialogHeader>
            <MergeWorkflow
              entityId={entity.id}
              projectPath={entity.projectPath}
              direction="upstream"
              onComplete={() => {
                setShowMergeWorkflow(false);
                refetch();
                toast({
                  title: 'Merge Complete',
                  description: 'Conflicts have been resolved successfully.',
                });
              }}
              onCancel={() => setShowMergeWorkflow(false)}
            />
          </DialogContent>
        </Dialog>
      )}

      {/* File Creation Dialog */}
      <FileCreationDialog
        open={showFileCreationDialog}
        onOpenChange={setShowFileCreationDialog}
        onConfirm={handleCreateFile}
      />

      {/* File Deletion Dialog */}
      <FileDeletionDialog
        open={showFileDeletionDialog}
        onOpenChange={setShowFileDeletionDialog}
        onConfirm={handleConfirmDelete}
        fileName={fileToDelete}
      />

      {/* Unsaved Changes Dialog */}
      <UnsavedChangesDialog
        open={showUnsavedChangesDialog}
        onOpenChange={setShowUnsavedChangesDialog}
        currentFile={selectedPath || undefined}
        targetFile={pendingNavigation?.type === 'file' ? pendingNavigation.target : undefined}
        onSave={handleSaveAndNavigate}
        onDiscard={handleDiscardChanges}
        onCancel={() => {
          setPendingNavigation(null);
          setShowUnsavedChangesDialog(false);
        }}
      />

      {/* Parameter Editor Modal */}
      {entity && (
        <ParameterEditorModal
          artifact={{
            name: entity.name,
            type: entity.type as any,
            source: entity.source,
            version: entity.version,
            scope: (entity.collection || 'user') as any,
            tags: entity.tags,
            aliases: entity.aliases,
          }}
          open={showParameterEditor}
          onClose={() => setShowParameterEditor(false)}
          onSave={handleSaveParameters}
        />
      )}
    </>
  );
}
