/**
 * Catalog Entry Modal
 *
 * Modal for displaying detailed catalog entry information including confidence scores.
 */

'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { ScoreBadge } from '@/components/ScoreBadge';
import {
  GitBranch,
  GitCommit,
  Calendar,
  Download,
  ExternalLink,
  Loader2,
  FileText,
  List,
  AlertCircle,
  RefreshCw,
  Tag,
  Pencil,
  MoreVertical,
  FolderOpen,
  Rocket,
  Blocks,
} from 'lucide-react';
import { HeuristicScoreBreakdown } from '@/components/HeuristicScoreBreakdown';
import { FileTree, type FileNode } from '@/components/entity/file-tree';
import { ContentPane } from '@/components/entity/content-pane';
import {
  useCatalogFileTree,
  useCatalogFileContent,
  useUpdateCatalogEntryName,
  useReimportCatalogEntry,
  useDeployments,
  useSourceCatalog,
} from '@/hooks';
import { fetchArtifactsPaginated, type ArtifactsPaginatedResponse } from '@/lib/api/artifacts';
import type { FileTreeEntry } from '@/lib/api/catalog';
import type { CatalogEntry, ArtifactType, CatalogStatus } from '@/types/marketplace';
import { PathTagReview } from '@/components/marketplace/path-tag-review';
import { Input } from '@/components/ui/input';
import { FrontmatterDisplay } from '@/components/entity/frontmatter-display';
import { parseFrontmatter, detectFrontmatter } from '@/lib/frontmatter';
import {
  CompositePreview,
  type CompositePreview as CompositePreviewData,
  type CompositeArtifactEntry,
  type CompositeConflictEntry,
} from '@/components/import/composite-preview';

interface CatalogEntryModalProps {
  entry: CatalogEntry | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport?: (entry: CatalogEntry) => void;
  isImporting?: boolean;
  onEntryUpdated?: (entry: CatalogEntry) => void;
  onNavigateToCollection?: (collectionId: string, artifactId: string) => void;
  onNavigateToDeployment?: (projectPath: string, artifactId: string) => void;
}

/**
 * Format ISO date string to human-readable format
 */
function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Shorten SHA to first 7 characters
 */
function shortenSha(sha: string): string {
  return sha.slice(0, 7);
}

// Type badge color configuration
const typeConfig: Record<ArtifactType, { label: string; color: string }> = {
  skill: { label: 'Skill', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
  command: {
    label: 'Command',
    color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  },
  agent: {
    label: 'Agent',
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  },
  mcp: {
    label: 'MCP',
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  },
  mcp_server: {
    label: 'MCP',
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  },
  hook: { label: 'Hook', color: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200' },
  composite: { label: 'Plugin', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200' },
};

// Status badge configuration
const statusConfig: Record<CatalogStatus, { label: string; className: string }> = {
  new: {
    label: 'New',
    className: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
  },
  updated: {
    label: 'Updated',
    className: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950',
  },
  imported: {
    label: 'Imported',
    className: 'border-gray-500 text-gray-700 bg-gray-50 dark:bg-gray-950',
  },
  removed: {
    label: 'Removed',
    className: 'border-red-500 text-red-700 bg-red-50 dark:bg-red-950 line-through',
  },
  excluded: {
    label: 'Excluded',
    className: 'border-gray-400 text-gray-600 bg-gray-100 dark:bg-gray-800',
  },
};

/**
 * Transform flat file list from API to hierarchical FileNode structure
 *
 * Converts flat paths like ["src/index.ts", "src/utils/helper.ts"]
 * to nested structure: [{name: "src", type: "directory", children: [...]}]
 */
function buildFileStructure(files: FileTreeEntry[]): FileNode[] {
  // Build a map of path -> node for quick lookup
  const nodeMap = new Map<string, FileNode>();

  // Sort files to ensure directories are processed before their children
  const sortedFiles = [...files].sort((a, b) => {
    // Directories first, then by path length, then alphabetically
    if (a.type !== b.type) return a.type === 'tree' ? -1 : 1;
    const depthA = a.path.split('/').length;
    const depthB = b.path.split('/').length;
    if (depthA !== depthB) return depthA - depthB;
    return a.path.localeCompare(b.path);
  });

  // First pass: create all nodes
  for (const entry of sortedFiles) {
    const parts = entry.path.split('/');
    let currentPath = '';

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i] as string; // Safe: parts comes from split() which always returns string[]
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLast = i === parts.length - 1;

      if (!nodeMap.has(currentPath)) {
        const node: FileNode = {
          name: part,
          path: currentPath,
          type: isLast ? (entry.type === 'tree' ? 'directory' : 'file') : 'directory',
          children: isLast && entry.type !== 'tree' ? undefined : [],
        };
        nodeMap.set(currentPath, node);
      }
    }
  }

  // Second pass: build parent-child relationships
  for (const [path, node] of nodeMap) {
    const lastSlashIndex = path.lastIndexOf('/');
    if (lastSlashIndex > 0) {
      const parentPath = path.substring(0, lastSlashIndex);
      const parentNode = nodeMap.get(parentPath);
      if (parentNode && parentNode.children) {
        // Only add if not already present (avoid duplicates)
        if (!parentNode.children.some((child) => child.path === node.path)) {
          parentNode.children.push(node);
        }
      }
    }
  }

  // Get root nodes (no parent path, i.e., no slash in path)
  const result: FileNode[] = [];
  for (const [path, node] of nodeMap) {
    if (!path.includes('/')) {
      result.push(node);
    }
  }

  sortFileNodes(result);
  return result;
}

/**
 * Recursively sort file nodes: directories first, then alphabetically
 */
function sortFileNodes(nodes: FileNode[]): void {
  nodes.sort((a, b) => {
    if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  for (const node of nodes) {
    if (node.children) {
      sortFileNodes(node.children);
    }
  }
}

/**
 * Build GitHub URL to view a specific file in a repository
 *
 * Constructs a URL like: https://github.com/{owner}/{repo}/blob/{sha}/{artifact_path}/{file_path}
 *
 * @param upstreamUrl - The upstream URL from the catalog entry (e.g., https://github.com/owner/repo/tree/main/path)
 * @param artifactPath - Path to the artifact within the repository
 * @param filePath - Path to the file within the artifact
 * @param sha - Git SHA for the specific version (optional, defaults to HEAD)
 * @returns Full GitHub URL to view the file
 */
function buildGitHubFileUrl(
  upstreamUrl: string,
  artifactPath: string,
  filePath: string,
  sha?: string
): string {
  // Parse the upstream URL to extract owner and repo
  // Expected format: https://github.com/{owner}/{repo}/tree/{ref}/{path}
  const match = upstreamUrl.match(/github\.com\/([^/]+)\/([^/]+)/);
  if (!match) {
    // Fallback: just append file path to upstream URL
    return `${upstreamUrl}/${filePath}`;
  }

  const [, owner, repo] = match;
  const ref = sha || 'HEAD';
  const fullPath = artifactPath ? `${artifactPath}/${filePath}` : filePath;

  return `https://github.com/${owner}/${repo}/blob/${ref}/${fullPath}`;
}

/**
 * Check if an error is a rate limit error (HTTP 429 or rate limit message)
 */
function isRateLimitError(error: Error | null): boolean {
  if (!error) return false;
  const message = error.message?.toLowerCase() ?? '';
  return (
    message.includes('rate limit') ||
    message.includes('rate-limit') ||
    message.includes('429') ||
    message.includes('too many requests')
  );
}

/**
 * Get user-friendly error message based on error type
 */
function getErrorMessage(
  error: Error | null,
  isTree: boolean
): { title: string; description: string } {
  if (!error) {
    return {
      title: isTree ? 'Failed to load file tree' : 'Failed to load file',
      description: 'An unknown error occurred.',
    };
  }

  if (isRateLimitError(error)) {
    return {
      title: 'GitHub rate limit reached',
      description: 'Too many requests. Please wait a few minutes and try again.',
    };
  }

  // Check for network errors
  if (
    error.message?.toLowerCase().includes('network') ||
    error.message?.toLowerCase().includes('fetch')
  ) {
    return {
      title: isTree ? 'Failed to load file tree' : 'Failed to load file',
      description: 'Network error. Please check your connection and try again.',
    };
  }

  // Check for not found errors
  if (error.message?.includes('404') || error.message?.toLowerCase().includes('not found')) {
    return {
      title: isTree ? 'File tree not found' : 'File not found',
      description: 'The requested content could not be found on GitHub.',
    };
  }

  // Default error message
  return {
    title: isTree ? 'Failed to load file tree' : 'Failed to load file',
    description: 'Unable to fetch content. Please try again.',
  };
}

export function CatalogEntryModal({
  entry,
  open,
  onOpenChange,
  onImport,
  isImporting = false,
  onEntryUpdated,
  onNavigateToCollection,
  onNavigateToDeployment,
}: CatalogEntryModalProps) {
  const [activeTab, setActiveTab] = useState<
    'overview' | 'contents' | 'tags' | 'collections' | 'deployments' | 'plugin'
  >('overview');
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [isEditingName, setIsEditingName] = useState(false);
  const [draftName, setDraftName] = useState('');
  const [nameError, setNameError] = useState<string | null>(null);
  const [showReimportDialog, setShowReimportDialog] = useState(false);
  const [keepDeployments, setKeepDeployments] = useState(false);

  // Use source_id directly as string for API calls
  const sourceId = entry?.source_id ?? null;
  const nameSourceId = entry?.source_id ?? '';
  const artifactPath = entry?.path ?? null;

  const updateNameMutation = useUpdateCatalogEntryName(nameSourceId);
  const reimportMutation = useReimportCatalogEntry(nameSourceId);

  // Fetch file tree when modal opens (needed for both Contents and Overview tabs)
  const {
    data: fileTreeData,
    isLoading: isTreeLoading,
    error: treeError,
    refetch: refetchTree,
  } = useCatalogFileTree(entry ? sourceId : null, entry ? artifactPath : null);

  // Fetch file content when a file is selected
  const {
    data: fileContentData,
    isLoading: isContentLoading,
    error: contentError,
    refetch: refetchContent,
  } = useCatalogFileContent(sourceId, artifactPath, selectedFilePath);

  // Find the primary markdown file path for frontmatter extraction
  // Priority: SKILL.md > README.md > first .md file
  const primaryMdPath = useMemo(() => {
    if (!fileTreeData?.entries) return null;

    const files = fileTreeData.entries;
    // Priority: SKILL.md > README.md > first .md file
    const skillMd = files.find((f) => f.type === 'file' && f.path.toLowerCase() === 'skill.md');
    if (skillMd) return skillMd.path;

    const readmeMd = files.find((f) => f.type === 'file' && f.path.toLowerCase() === 'readme.md');
    if (readmeMd) return readmeMd.path;

    const firstMd = files.find((f) => f.type === 'file' && f.path.toLowerCase().endsWith('.md'));
    return firstMd?.path ?? null;
  }, [fileTreeData?.entries]);

  // Fetch frontmatter from primary markdown file for Overview tab
  const { data: frontmatterContent, isLoading: isFrontmatterLoading } = useCatalogFileContent(
    activeTab === 'overview' ? sourceId : null,
    activeTab === 'overview' ? artifactPath : null,
    activeTab === 'overview' ? primaryMdPath : null
  );

  // Parse frontmatter from the content
  const parsedFrontmatter = useMemo(() => {
    if (!frontmatterContent?.content) return null;
    if (!detectFrontmatter(frontmatterContent.content)) return null;
    const { frontmatter } = parseFrontmatter(frontmatterContent.content);
    return frontmatter;
  }, [frontmatterContent?.content]);

  // State for imported artifact data (collections tab)
  const [importedArtifact, setImportedArtifact] = useState<
    ArtifactsPaginatedResponse['items'][0] | null
  >(null);
  const [isLoadingArtifact, setIsLoadingArtifact] = useState(false);

  // Fetch imported artifact when collections tab is active and entry is imported
  // Search by name and type since import_id lookup may not be available
  useEffect(() => {
    if (!entry || entry.status !== 'imported' || activeTab !== 'collections') {
      return;
    }

    const findImportedArtifact = async () => {
      setIsLoadingArtifact(true);
      try {
        // NEW: Try import_id first (for new imports)
        if (entry.import_id) {
          const response = await fetchArtifactsPaginated({
            import_id: entry.import_id,
            limit: 10,
          });
          if (response.items.length > 0) {
            setImportedArtifact(response.items[0] || null);
            return;
          }
        }

        // DEPRECATED FALLBACK: Search by name (for legacy imports without import_id)
        console.warn('Using deprecated name-based artifact lookup for legacy import');
        const response = await fetchArtifactsPaginated({
          search: entry.name,
          artifact_type: entry.artifact_type,
          limit: 50,
        });

        // Find exact match by name and type
        const matchingArtifact = response.items.find(
          (a) => a.name === entry.name && a.type === entry.artifact_type
        );

        setImportedArtifact(matchingArtifact || null);
      } catch (error) {
        console.error('Failed to find imported artifact:', error);
        setImportedArtifact(null);
      } finally {
        setIsLoadingArtifact(false);
      }
    };

    findImportedArtifact();
  }, [entry, activeTab]);

  // Fetch deployments for the deployments tab
  const { data: deploymentsData, isLoading: isLoadingDeployments } = useDeployments({
    // Only fetch when tab is active and entry is imported
  });

  // Fetch catalog entries for composite plugin breakdown tab.
  // Enabled only when the modal is open, the entry is composite, and the plugin tab is active.
  const isComposite = entry?.artifact_type === 'composite';
  const showPluginTab = isComposite && activeTab === 'plugin';
  // Pass empty string when disabled — useSourceCatalog uses !!sourceId to guard the query
  const pluginTabSourceId = showPluginTab && sourceId ? sourceId : '';
  const { data: compositeCatalogData, isLoading: isLoadingCompositeCatalog } = useSourceCatalog(
    pluginTabSourceId,
    // Include below-threshold entries to catch all children; no type/status filter
    { include_below_threshold: true },
    // API enforces max 100 per page; infinite query handles pagination
    100
  );

  // Derive CompositePreviewData from catalog entries.
  // Children are catalog entries whose paths start with the composite's path + '/'.
  const compositePreviewData = useMemo<CompositePreviewData | null>(() => {
    if (!entry || !isComposite) return null;

    // Flatten all catalog pages
    const allCatalogEntries: CatalogEntry[] =
      compositeCatalogData?.pages?.flatMap((p) => p.items) ?? [];

    const compositePath = entry.path;

    // A child entry's path must be directly or transitively under the composite path.
    // We exclude the composite entry itself and entries of type 'composite' (parent containers).
    const children = allCatalogEntries.filter(
      (e) =>
        e.id !== entry.id &&
        e.artifact_type !== 'composite' &&
        e.path.startsWith(compositePath + '/')
    );

    // Bucket children by their import status:
    //   - imported  → Existing (Will Link)
    //   - in_collection (and not imported) → Conflict (same name, already in collection)
    //   - new/updated/other → New (Will Import)
    const newArtifacts: CompositeArtifactEntry[] = [];
    const existingArtifacts: (CompositeArtifactEntry & { hash: string })[] = [];
    const conflictArtifacts: CompositeConflictEntry[] = [];

    for (const child of children) {
      if (child.status === 'imported') {
        // Already imported — will link to existing copy
        existingArtifacts.push({
          name: child.name,
          type: child.artifact_type,
          hash: child.detected_sha ?? 'unknown',
        });
      } else if (child.in_collection) {
        // Same name/type exists in collection with potentially different content
        conflictArtifacts.push({
          name: child.name,
          type: child.artifact_type,
          currentHash: 'existing',
          newHash: child.detected_sha ?? 'incoming',
        });
      } else {
        // Net-new artifact
        newArtifacts.push({
          name: child.name,
          type: child.artifact_type,
        });
      }
    }

    return {
      pluginName: entry.name,
      totalChildren: children.length,
      newArtifacts,
      existingArtifacts,
      conflictArtifacts,
    };
  }, [entry, isComposite, compositeCatalogData]);

  // Filter deployments to match this artifact
  const artifactDeployments = useMemo(() => {
    if (!deploymentsData || !entry) return [];
    return deploymentsData.filter(
      (d) => d.artifact_name === entry.name && d.artifact_type === entry.artifact_type
    );
  }, [deploymentsData, entry]);

  // Get collections count from imported artifact
  const collectionsCount = importedArtifact?.collections?.length ?? 0;
  const deploymentsCount = artifactDeployments.length;

  // Transform flat file list to hierarchical structure for FileTree component
  const fileStructure = fileTreeData?.entries ? buildFileStructure(fileTreeData.entries) : [];

  // Auto-select default file when file tree loads
  // Priority: first .md file (case-insensitive), then first file alphabetically
  useEffect(() => {
    // Only auto-select if no file is currently selected and we have entries
    if (selectedFilePath !== null || !fileTreeData?.entries?.length) {
      return;
    }

    const files = fileTreeData.entries;

    // Find first markdown file (case-insensitive)
    // Note: API returns 'file' for files and 'tree' for directories
    const firstMdFile = files.find(
      (f) => f.type === 'file' && f.path.toLowerCase().endsWith('.md')
    );

    if (firstMdFile) {
      setSelectedFilePath(firstMdFile.path);
      return;
    }

    // Fallback: first file alphabetically (by path)
    const sortedFiles = files
      .filter((f) => f.type === 'file')
      .sort((a, b) => a.path.localeCompare(b.path));

    if (sortedFiles.length > 0 && sortedFiles[0]) {
      setSelectedFilePath(sortedFiles[0].path);
    }
  }, [fileTreeData?.entries, selectedFilePath]);

  // Reset file selection and imported artifact when artifact entry changes
  useEffect(() => {
    setSelectedFilePath(null);
    setImportedArtifact(null);
  }, [entry?.id]);

  useEffect(() => {
    if (!entry) {
      return;
    }

    if (!isEditingName) {
      setDraftName(entry.name);
      setNameError(null);
    }
  }, [entry, isEditingName]);

  // Reset selected file when modal closes
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setSelectedFilePath(null);
      setActiveTab('overview');
      setIsEditingName(false);
      setNameError(null);
      setShowReimportDialog(false);
      setKeepDeployments(false);
      setImportedArtifact(null);
    }
    onOpenChange(newOpen);
  };

  if (!entry) return null;

  const handleStartEditName = () => {
    setDraftName(entry.name);
    setNameError(null);
    setIsEditingName(true);
  };

  const handleCancelEditName = () => {
    setDraftName(entry.name);
    setNameError(null);
    setIsEditingName(false);
  };

  const handleSaveName = async () => {
    const trimmedName = draftName.trim();
    if (!trimmedName) {
      setNameError('Name is required.');
      return;
    }

    if (trimmedName === entry.name) {
      setIsEditingName(false);
      setNameError(null);
      return;
    }

    try {
      const updatedEntry = await updateNameMutation.mutateAsync({
        entryId: entry.id,
        name: trimmedName,
      });
      setIsEditingName(false);
      setNameError(null);
      onEntryUpdated?.(updatedEntry);
    } catch (error) {
      setNameError(error instanceof Error ? error.message : 'Failed to update name');
    }
  };

  const handleReimport = async () => {
    try {
      await reimportMutation.mutateAsync({
        entryId: entry.id,
        keepDeployments,
      });
      setShowReimportDialog(false);
      setKeepDeployments(false);
      // Close the modal after successful reimport
      handleOpenChange(false);
    } catch {
      // Error is handled by the mutation's onError callback
    }
  };

  // Determine if import button should be disabled
  const isImportDisabled = entry.status === 'imported' || entry.status === 'removed' || isImporting;
  const isSavingName = updateNameMutation.isPending;
  const isSaveDisabled = isSavingName || !draftName.trim() || draftName.trim() === entry.name;
  const isReimporting = reimportMutation.isPending;
  const canReimport = entry.status === 'imported';

  return (
    <>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="flex h-[85vh] max-h-[85vh] min-h-0 max-w-4xl flex-col overflow-hidden p-0 lg:max-w-5xl">
          {/* Header Section - Fixed */}
          <div className="border-b px-6 pb-4 pt-6">
            <DialogHeader className="flex flex-row items-start justify-between gap-4">
              <div className="flex-1">
                <DialogTitle>Catalog Entry Details</DialogTitle>
                <DialogDescription className="sr-only">
                  Detailed view of the {entry.name} artifact including confidence scores, metadata,
                  and import options
                </DialogDescription>
              </div>
              {canReimport && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0"
                      aria-label="More options"
                    >
                      <MoreVertical className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => setShowReimportDialog(true)}
                      disabled={isReimporting}
                    >
                      <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                      Force Re-import
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </DialogHeader>
          </div>

          {/* Tabs Section */}
          <Tabs
            value={activeTab}
            onValueChange={(value) =>
              setActiveTab(
                value as 'overview' | 'contents' | 'tags' | 'collections' | 'deployments' | 'plugin'
              )
            }
            className="flex h-full min-h-0 flex-1 flex-col px-6"
          >
            <TabsList className="h-auto w-full justify-start rounded-none border-b bg-transparent p-0">
              <TabsTrigger
                value="overview"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                <List className="mr-2 h-4 w-4" aria-hidden="true" />
                Overview
              </TabsTrigger>
              <TabsTrigger
                value="contents"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                <FileText className="mr-2 h-4 w-4" aria-hidden="true" />
                Contents
              </TabsTrigger>
              <TabsTrigger
                value="tags"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                <Tag className="mr-2 h-4 w-4" aria-hidden="true" />
                Suggested Tags
              </TabsTrigger>
              {isComposite && (
                <TabsTrigger
                  value="plugin"
                  className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                >
                  <Blocks className="mr-2 h-4 w-4 text-indigo-500" aria-hidden="true" />
                  <span className="text-indigo-500 dark:text-indigo-400">Plugin Breakdown</span>
                </TabsTrigger>
              )}
              {entry.status === 'imported' && (
                <>
                  <TabsTrigger
                    value="collections"
                    className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                  >
                    <FolderOpen className="mr-2 h-4 w-4" aria-hidden="true" />
                    Collections
                    {collectionsCount > 0 && (
                      <Badge variant="secondary" className="ml-2">
                        {collectionsCount}
                      </Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger
                    value="deployments"
                    className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                  >
                    <Rocket className="mr-2 h-4 w-4" aria-hidden="true" />
                    Deployments
                    {deploymentsCount > 0 && (
                      <Badge variant="secondary" className="ml-2">
                        {deploymentsCount}
                      </Badge>
                    )}
                  </TabsTrigger>
                </>
              )}
            </TabsList>

            {/* Overview Tab */}
            <TabsContent
              value="overview"
              className="mt-0 min-h-0 flex-1 overflow-y-auto overflow-x-hidden py-4"
            >
              <div className="grid gap-6">
                {/* Header Section */}
                <div className="space-y-2 border-b pb-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex min-w-0 flex-1 items-center gap-2">
                      {isEditingName ? (
                        <form
                          className="flex w-full flex-wrap items-center gap-2"
                          onSubmit={(event) => {
                            event.preventDefault();
                            handleSaveName();
                          }}
                        >
                          <Input
                            value={draftName}
                            onChange={(event) => {
                              setDraftName(event.target.value);
                              setNameError(null);
                            }}
                            onKeyDown={(event) => {
                              if (event.key === 'Escape') {
                                event.preventDefault();
                                handleCancelEditName();
                              }
                            }}
                            maxLength={100}
                            className="min-w-[220px] flex-1"
                            aria-label="Artifact name"
                          />
                          <Button type="submit" size="sm" disabled={isSaveDisabled}>
                            {isSavingName ? (
                              <>
                                <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                                Saving
                              </>
                            ) : (
                              'Save'
                            )}
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={handleCancelEditName}
                            disabled={isSavingName}
                          >
                            Cancel
                          </Button>
                        </form>
                      ) : (
                        <>
                          <h2 className="truncate text-xl font-semibold">{entry.name}</h2>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={handleStartEditName}
                            aria-label={`Edit name for ${entry.name}`}
                          >
                            <Pencil className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={typeConfig[entry.artifact_type]?.color || 'bg-gray-100'}>
                        {typeConfig[entry.artifact_type]?.label || entry.artifact_type}
                      </Badge>
                      <Badge variant="outline" className={statusConfig[entry.status]?.className}>
                        {statusConfig[entry.status]?.label || entry.status}
                      </Badge>
                    </div>
                  </div>
                  {nameError && (
                    <p className="text-xs text-destructive" role="alert">
                      {nameError}
                    </p>
                  )}
                  <div className="flex min-w-0 items-center gap-3">
                    <ScoreBadge
                      confidence={entry.confidence_score}
                      size="md"
                      breakdown={entry.score_breakdown}
                    />
                    <div className="min-w-0 flex-1 overflow-x-auto">
                      <code className="break-all rounded bg-muted px-2 py-1 text-xs text-muted-foreground">
                        {entry.path}
                      </code>
                    </div>
                  </div>
                </div>

                {/* Frontmatter Metadata Section */}
                {isFrontmatterLoading && (
                  <section aria-label="Loading artifact metadata" className="space-y-3">
                    <h3 className="text-sm font-medium">Artifact Metadata</h3>
                    <div className="animate-pulse space-y-2">
                      <div className="h-4 w-1/3 rounded bg-muted" />
                      <div className="h-4 w-2/3 rounded bg-muted" />
                      <div className="h-4 w-1/2 rounded bg-muted" />
                    </div>
                  </section>
                )}

                {parsedFrontmatter && Object.keys(parsedFrontmatter).length > 0 && (
                  <section aria-label="Artifact metadata from frontmatter" className="space-y-3">
                    <h3 className="text-sm font-medium">Artifact Metadata</h3>
                    <FrontmatterDisplay
                      frontmatter={parsedFrontmatter}
                      defaultCollapsed={false}
                      className="bg-background"
                    />
                  </section>
                )}

                {/* Confidence Section */}
                <section
                  aria-label="Confidence score breakdown"
                  className="space-y-3 border-t pt-4"
                >
                  <h3 className="text-sm font-medium">Confidence Score Breakdown</h3>
                  <div className="max-h-[200px] overflow-y-auto">
                    {entry.score_breakdown ? (
                      <HeuristicScoreBreakdown breakdown={entry.score_breakdown} variant="full" />
                    ) : (
                      <div className="space-y-2">
                        <p className="text-sm text-muted-foreground">
                          Score breakdown not available for this entry.
                        </p>
                        <p className="text-xs text-muted-foreground/70">
                          Rescan the source to generate detailed scoring breakdown for artifacts.
                        </p>
                      </div>
                    )}
                  </div>
                </section>

                {/* Metadata Section */}
                <section aria-label="Artifact details" className="space-y-4">
                  <h3 className="text-sm font-semibold">Metadata</h3>

                  {/* Path Details */}
                  <div className="space-y-2">
                    <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                      <span className="font-medium text-muted-foreground">Path:</span>
                      <div className="overflow-x-auto">
                        <code className="break-all rounded bg-muted px-2 py-1 font-mono text-xs">
                          {entry.path}
                        </code>
                      </div>
                    </div>

                    <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                      <span className="font-medium text-muted-foreground">Upstream URL:</span>
                      <div className="overflow-x-auto">
                        <a
                          href={entry.upstream_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 break-all text-primary hover:underline"
                          aria-label={`View source repository for ${entry.name} on GitHub`}
                        >
                          <span>{entry.upstream_url}</span>
                          <ExternalLink className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                        </a>
                      </div>
                    </div>

                    {entry.detected_version && (
                      <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                        <span className="inline-flex items-center gap-1 font-medium text-muted-foreground">
                          <GitBranch className="h-3 w-3" aria-hidden="true" />
                          Version:
                        </span>
                        <div className="overflow-x-auto">
                          <code className="break-all rounded bg-muted px-2 py-1 font-mono text-xs">
                            {entry.detected_version}
                          </code>
                        </div>
                      </div>
                    )}

                    {entry.detected_sha && (
                      <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                        <span className="inline-flex items-center gap-1 font-medium text-muted-foreground">
                          <GitCommit className="h-3 w-3" aria-hidden="true" />
                          SHA:
                        </span>
                        <div className="overflow-x-auto">
                          <code className="break-all rounded bg-muted px-2 py-1 font-mono text-xs">
                            {shortenSha(entry.detected_sha)}
                          </code>
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                      <span className="inline-flex items-center gap-1 font-medium text-muted-foreground">
                        <Calendar className="h-3 w-3" aria-hidden="true" />
                        Detected at:
                      </span>
                      <span>{formatDate(entry.detected_at)}</span>
                    </div>
                  </div>
                </section>
              </div>
            </TabsContent>

            {/* Contents Tab - FileTree + ContentPane split layout */}
            <TabsContent
              value="contents"
              className="mt-0 min-h-0 flex-1 overflow-hidden data-[state=active]:flex data-[state=active]:flex-col"
            >
              <div className="flex h-full min-h-0 min-w-0 flex-1 gap-0 overflow-hidden">
                {/* Left Panel - File Tree */}
                <div className="flex w-[280px] flex-shrink-0 flex-col overflow-hidden border-r">
                  {treeError ? (
                    <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
                      <AlertCircle className="h-8 w-8 text-destructive" aria-hidden="true" />
                      <div>
                        <p className="text-sm font-medium">
                          {getErrorMessage(treeError, true).title}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {getErrorMessage(treeError, true).description}
                        </p>
                      </div>
                      <div className="flex w-full max-w-[200px] flex-col gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => refetchTree()}
                          className="w-full"
                        >
                          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                          Try again
                        </Button>
                        <Button variant="ghost" size="sm" asChild className="w-full">
                          <a href={entry.upstream_url} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="mr-2 h-4 w-4" aria-hidden="true" />
                            View on GitHub
                          </a>
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <FileTree
                      entityId={entry.id}
                      files={fileStructure}
                      selectedPath={selectedFilePath}
                      onSelect={setSelectedFilePath}
                      isLoading={isTreeLoading}
                      readOnly
                      ariaLabel={`File browser for ${entry.name}`}
                    />
                  )}
                </div>

                {/* Right Panel - Content Pane with enhanced error handling */}
                <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
                  {contentError ? (
                    <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
                      <AlertCircle className="h-8 w-8 text-destructive" aria-hidden="true" />
                      <div>
                        <p className="text-sm font-medium">
                          {getErrorMessage(contentError, false).title}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {getErrorMessage(contentError, false).description}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => refetchContent()}>
                          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                          Try again
                        </Button>
                        <Button variant="ghost" size="sm" asChild>
                          <a href={entry.upstream_url} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="mr-2 h-4 w-4" aria-hidden="true" />
                            View on GitHub
                          </a>
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <ContentPane
                      path={selectedFilePath}
                      content={fileContentData?.content ?? null}
                      isLoading={isContentLoading}
                      readOnly
                      truncationInfo={
                        fileContentData?.truncated
                          ? {
                              truncated: true,
                              originalSize: fileContentData.original_size,
                              fullFileUrl: selectedFilePath
                                ? buildGitHubFileUrl(
                                    entry.upstream_url,
                                    entry.path,
                                    selectedFilePath,
                                    entry.detected_sha
                                  )
                                : undefined,
                            }
                          : undefined
                      }
                    />
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Suggested Tags Tab */}
            <TabsContent value="tags" className="mt-0 min-h-0 flex-1 overflow-y-auto py-4">
              <div className="space-y-4">
                <div className="space-y-1">
                  <h3 className="text-sm font-medium">Path-Based Tag Suggestions</h3>
                  <p className="text-xs text-muted-foreground">
                    Review and approve tags extracted from the artifact path. Approved tags will be
                    applied when importing.
                  </p>
                </div>
                <PathTagReview sourceId={entry.source_id} entryId={entry.id} />
              </div>
            </TabsContent>

            {/* Plugin Breakdown Tab - only rendered for composite artifacts */}
            {isComposite && (
              <TabsContent value="plugin" className="mt-0 min-h-0 flex-1 overflow-y-auto py-4">
                <div className="space-y-4">
                  <div className="space-y-1">
                    <h3 className="text-sm font-medium text-indigo-600 dark:text-indigo-400">
                      Plugin Breakdown
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      Child artifacts included in this plugin, categorised by import impact.
                    </p>
                  </div>

                  {isLoadingCompositeCatalog ? (
                    <div className="flex items-center justify-center py-8" role="status">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
                      <span className="ml-2 text-sm text-muted-foreground">
                        Loading plugin breakdown...
                      </span>
                    </div>
                  ) : compositePreviewData && compositePreviewData.totalChildren > 0 ? (
                    <CompositePreview preview={compositePreviewData} />
                  ) : compositePreviewData && compositePreviewData.totalChildren === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <Blocks
                        className="mb-2 h-10 w-10 text-indigo-400/50 dark:text-indigo-500/50"
                        aria-hidden="true"
                      />
                      <p className="text-sm font-medium text-muted-foreground">
                        No child artifacts detected
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground/70">
                        Open the Plugin Breakdown tab again after a source rescan to populate children.
                      </p>
                    </div>
                  ) : (
                    // compositePreviewData is null — tab not yet fetched (first render)
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <Blocks
                        className="mb-2 h-10 w-10 text-muted-foreground/50"
                        aria-hidden="true"
                      />
                      <p className="text-sm font-medium text-muted-foreground">
                        Select the Plugin Breakdown tab to load child artifacts
                      </p>
                    </div>
                  )}
                </div>
              </TabsContent>
            )}

            {/* Collections Tab - only rendered for imported artifacts */}
            {entry.status === 'imported' && (
              <TabsContent value="collections" className="mt-0 min-h-0 flex-1 overflow-y-auto py-4">
                <div className="space-y-4">
                  <div className="space-y-1">
                    <h3 className="text-sm font-medium">Collections</h3>
                    <p className="text-xs text-muted-foreground">
                      Collections this artifact belongs to in your library.
                    </p>
                  </div>

                  {isLoadingArtifact ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      <span className="ml-2 text-sm text-muted-foreground">
                        Loading collections...
                      </span>
                    </div>
                  ) : importedArtifact?.collections && importedArtifact.collections.length > 0 ? (
                    <div className="grid gap-3">
                      {importedArtifact.collections.map((collection) => (
                        <button
                          key={collection.id}
                          type="button"
                          onClick={() =>
                            onNavigateToCollection?.(collection.id, importedArtifact.id)
                          }
                          className="flex items-center gap-3 rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
                        >
                          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
                            <FolderOpen className="h-5 w-5 text-primary" aria-hidden="true" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate font-medium">{collection.name}</p>
                            {collection.artifact_count !== undefined && (
                              <p className="text-xs text-muted-foreground">
                                {collection.artifact_count} artifact
                                {collection.artifact_count !== 1 ? 's' : ''}
                              </p>
                            )}
                          </div>
                          <ExternalLink
                            className="h-4 w-4 flex-shrink-0 text-muted-foreground"
                            aria-hidden="true"
                          />
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <FolderOpen
                        className="mb-2 h-10 w-10 text-muted-foreground/50"
                        aria-hidden="true"
                      />
                      <p className="text-sm font-medium text-muted-foreground">No collections</p>
                      <p className="mt-1 text-xs text-muted-foreground/70">
                        This artifact is not in any collections yet.
                      </p>
                    </div>
                  )}
                </div>
              </TabsContent>
            )}

            {/* Deployments Tab - only rendered for imported artifacts */}
            {entry.status === 'imported' && (
              <TabsContent value="deployments" className="mt-0 min-h-0 flex-1 overflow-y-auto py-4">
                <div className="space-y-4">
                  <div className="space-y-1">
                    <h3 className="text-sm font-medium">Deployments</h3>
                    <p className="text-xs text-muted-foreground">
                      Projects where this artifact is deployed.
                    </p>
                  </div>

                  {isLoadingDeployments ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      <span className="ml-2 text-sm text-muted-foreground">
                        Loading deployments...
                      </span>
                    </div>
                  ) : artifactDeployments.length > 0 ? (
                    <div className="grid gap-3">
                      {artifactDeployments.map((deployment, index) => (
                        <button
                          key={`${deployment.project_path}-${deployment.artifact_name}-${index}`}
                          type="button"
                          onClick={() =>
                            onNavigateToDeployment?.(
                              deployment.project_path,
                              entry.import_id || entry.id
                            )
                          }
                          className="flex items-center gap-3 rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
                        >
                          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-green-500/10">
                            <Rocket className="h-5 w-5 text-green-600" aria-hidden="true" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate font-medium">{deployment.artifact_name}</p>
                            <p
                              className="truncate text-xs text-muted-foreground"
                              title={deployment.project_path}
                            >
                              {deployment.project_path}
                            </p>
                            <p className="text-xs text-muted-foreground/70">
                              Deployed {formatDate(deployment.deployed_at)}
                            </p>
                          </div>
                          <div className="flex flex-shrink-0 items-center gap-2">
                            {deployment.local_modifications && (
                              <Badge
                                variant="outline"
                                className="border-yellow-500 text-yellow-600"
                              >
                                Modified
                              </Badge>
                            )}
                            <ExternalLink
                              className="h-4 w-4 text-muted-foreground"
                              aria-hidden="true"
                            />
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <Rocket
                        className="mb-2 h-10 w-10 text-muted-foreground/50"
                        aria-hidden="true"
                      />
                      <p className="text-sm font-medium text-muted-foreground">No deployments</p>
                      <p className="mt-1 text-xs text-muted-foreground/70">
                        This artifact has not been deployed to any projects.
                      </p>
                    </div>
                  )}
                </div>
              </TabsContent>
            )}
          </Tabs>

          {/* Action Buttons */}
          <DialogFooter className="mt-auto flex-shrink-0 border-t px-6 py-4">
            <Button
              variant="outline"
              onClick={() => window.open(entry.upstream_url, '_blank', 'noopener,noreferrer')}
              aria-label={`View ${entry.name} source repository on GitHub`}
            >
              <ExternalLink className="mr-2 h-4 w-4" aria-hidden="true" />
              View on GitHub
            </Button>

            {onImport && (
              <Button
                variant="default"
                onClick={() => onImport(entry)}
                disabled={isImportDisabled}
                aria-label={
                  isImporting
                    ? `Importing ${entry.name}...`
                    : isImportDisabled
                      ? `Cannot import ${entry.name} - ${entry.status === 'imported' ? 'already imported' : 'artifact removed'}`
                      : `Import ${entry.name} artifact`
                }
              >
                {isImporting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    Importing...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" aria-hidden="true" />
                    Import
                  </>
                )}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Force Re-import Confirmation Dialog */}
      <AlertDialog open={showReimportDialog} onOpenChange={setShowReimportDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Force Re-import Artifact</AlertDialogTitle>
            <AlertDialogDescription>
              This will re-download the artifact from the upstream source. Any local changes will be
              overwritten.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="flex items-center space-x-3 py-4">
            <Switch
              id="keep-deployments"
              checked={keepDeployments}
              onCheckedChange={setKeepDeployments}
              disabled={isReimporting}
            />
            <Label htmlFor="keep-deployments" className="cursor-pointer">
              Keep existing deployments
            </Label>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={isReimporting}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleReimport} disabled={isReimporting}>
              {isReimporting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  Re-importing...
                </>
              ) : (
                'Re-import'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
