/**
 * Catalog Entry Modal
 *
 * Modal for displaying detailed catalog entry information including confidence scores.
 */

'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
} from 'lucide-react';
import { HeuristicScoreBreakdown } from '@/components/HeuristicScoreBreakdown';
import { FileTree, type FileNode } from '@/components/entity/file-tree';
import { ContentPane } from '@/components/entity/content-pane';
import { useCatalogFileTree, useCatalogFileContent } from '@/hooks/use-catalog-files';
import type { FileTreeEntry } from '@/lib/api/catalog';
import type { CatalogEntry, ArtifactType, CatalogStatus } from '@/types/marketplace';

interface CatalogEntryModalProps {
  entry: CatalogEntry | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport?: (entry: CatalogEntry) => void;
  isImporting?: boolean;
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
  command: { label: 'Command', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
  agent: { label: 'Agent', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
  mcp_server: { label: 'MCP', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
  hook: { label: 'Hook', color: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200' },
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
};

/**
 * Transform flat file list from API to hierarchical FileNode structure
 *
 * Converts flat paths like ["src/index.ts", "src/utils/helper.ts"]
 * to nested structure: [{name: "src", type: "directory", children: [...]}]
 */
function buildFileStructure(files: FileTreeEntry[]): FileNode[] {
  const root: Map<string, FileNode> = new Map();

  // Sort files to ensure directories are processed before their children
  const sortedFiles = [...files].sort((a, b) => {
    // Directories first, then by path length, then alphabetically
    if (a.type !== b.type) return a.type === 'tree' ? -1 : 1;
    const depthA = a.path.split('/').length;
    const depthB = b.path.split('/').length;
    if (depthA !== depthB) return depthA - depthB;
    return a.path.localeCompare(b.path);
  });

  for (const entry of sortedFiles) {
    const parts = entry.path.split('/');
    let currentLevel = root;
    let currentPath = '';

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i] as string; // Safe: parts comes from split() which always returns string[]
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLast = i === parts.length - 1;

      if (!currentLevel.has(part)) {
        const node: FileNode = {
          name: part,
          path: currentPath,
          type: isLast ? (entry.type === 'tree' ? 'directory' : 'file') : 'directory',
          children: isLast && entry.type !== 'tree' ? undefined : [],
        };
        currentLevel.set(part, node);
      }

      const existingNode = currentLevel.get(part);
      if (existingNode && existingNode.children) {
        // Convert children array to Map for next iteration
        const childMap = new Map<string, FileNode>();
        for (const child of existingNode.children) {
          childMap.set(child.name, child);
        }
        currentLevel = childMap;

        // Update the parent's children from the map (will be done at the end)
        if (!isLast) {
          existingNode.children = Array.from(childMap.values());
        }
      }
    }
  }

  // Convert root map to array and sort (directories first, then alphabetically)
  const result = Array.from(root.values());
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
function getErrorMessage(error: Error | null, isTree: boolean): { title: string; description: string } {
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
  if (error.message?.toLowerCase().includes('network') || error.message?.toLowerCase().includes('fetch')) {
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
}: CatalogEntryModalProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'contents'>('overview');
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);

  // Parse source_id as number for API calls
  const sourceId = entry ? parseInt(entry.source_id, 10) : null;
  const artifactPath = entry?.path ?? null;

  // Fetch file tree when Contents tab is active
  const {
    data: fileTreeData,
    isLoading: isTreeLoading,
    error: treeError,
    refetch: refetchTree,
  } = useCatalogFileTree(
    activeTab === 'contents' ? sourceId : null,
    activeTab === 'contents' ? artifactPath : null
  );

  // Fetch file content when a file is selected
  const {
    data: fileContentData,
    isLoading: isContentLoading,
    error: contentError,
    refetch: refetchContent,
  } = useCatalogFileContent(sourceId, artifactPath, selectedFilePath);

  // Transform flat file list to hierarchical structure for FileTree component
  const fileStructure = fileTreeData?.files
    ? buildFileStructure(fileTreeData.files)
    : [];

  // Auto-select default file when file tree loads
  // Priority: first .md file (case-insensitive), then first file alphabetically
  useEffect(() => {
    // Only auto-select if no file is currently selected and we have files
    if (selectedFilePath !== null || !fileTreeData?.files?.length) {
      return;
    }

    const files = fileTreeData.files;

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
  }, [fileTreeData?.files, selectedFilePath]);

  // Reset selected file when modal closes or entry changes
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setSelectedFilePath(null);
      setActiveTab('overview');
    }
    onOpenChange(newOpen);
  };

  if (!entry) return null;

  // Determine if import button should be disabled
  const isImportDisabled = entry.status === 'imported' || entry.status === 'removed' || isImporting;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="flex h-[85vh] max-h-[85vh] min-h-0 max-w-4xl flex-col overflow-hidden p-0 lg:max-w-5xl">
        {/* Header Section - Fixed */}
        <div className="border-b px-6 pb-4 pt-6">
          <DialogHeader>
            <DialogTitle>Catalog Entry Details</DialogTitle>
            <DialogDescription className="sr-only">
              Detailed view of the {entry.name} artifact including confidence scores, metadata, and import options
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Tabs Section */}
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as 'overview' | 'contents')}
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
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="mt-0 flex-1 overflow-y-auto overflow-x-hidden min-h-0 py-4">
            <div className="grid gap-6">
              {/* Header Section */}
              <div className="border-b pb-4 space-y-2">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold">{entry.name}</h2>
                  <div className="flex items-center gap-2">
                    <Badge className={typeConfig[entry.artifact_type]?.color || 'bg-gray-100'}>
                      {typeConfig[entry.artifact_type]?.label || entry.artifact_type}
                    </Badge>
                    <Badge variant="outline" className={statusConfig[entry.status]?.className}>
                      {statusConfig[entry.status]?.label || entry.status}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-3 min-w-0">
                  <ScoreBadge
                    confidence={entry.confidence_score}
                    size="md"
                    breakdown={entry.score_breakdown}
                  />
                  <div className="overflow-x-auto flex-1 min-w-0">
                    <code className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded whitespace-nowrap">
                      {entry.path}
                    </code>
                  </div>
                </div>
              </div>

              {/* Confidence Section */}
              <section
                aria-label="Confidence score breakdown"
                className="space-y-3 border-t pt-4"
              >
                <h3 className="text-sm font-medium">Confidence Score Breakdown</h3>
                <div className="max-h-[200px] overflow-y-auto">
                  {entry.score_breakdown ? (
                    <HeuristicScoreBreakdown
                      breakdown={entry.score_breakdown}
                      variant="full"
                    />
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
              <section
                aria-label="Artifact details"
                className="space-y-4"
              >
                <h3 className="font-semibold text-sm">Metadata</h3>

                {/* Path Details */}
                <div className="space-y-2">
                  <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                    <span className="text-muted-foreground font-medium">Path:</span>
                    <div className="overflow-x-auto">
                      <code className="text-xs bg-muted px-2 py-1 rounded font-mono whitespace-nowrap">
                        {entry.path}
                      </code>
                    </div>
                  </div>

                  <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                    <span className="text-muted-foreground font-medium">Upstream URL:</span>
                    <div className="overflow-x-auto">
                      <a
                        href={entry.upstream_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline inline-flex items-center gap-1 whitespace-nowrap"
                        aria-label={`View source repository for ${entry.name} on GitHub`}
                      >
                        <span>{entry.upstream_url}</span>
                        <ExternalLink className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                      </a>
                    </div>
                  </div>

                  {entry.detected_version && (
                    <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                      <span className="text-muted-foreground font-medium inline-flex items-center gap-1">
                        <GitBranch className="h-3 w-3" aria-hidden="true" />
                        Version:
                      </span>
                      <div className="overflow-x-auto">
                        <code className="text-xs bg-muted px-2 py-1 rounded font-mono whitespace-nowrap">
                          {entry.detected_version}
                        </code>
                      </div>
                    </div>
                  )}

                  {entry.detected_sha && (
                    <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                      <span className="text-muted-foreground font-medium inline-flex items-center gap-1">
                        <GitCommit className="h-3 w-3" aria-hidden="true" />
                        SHA:
                      </span>
                      <div className="overflow-x-auto">
                        <code className="text-xs bg-muted px-2 py-1 rounded font-mono whitespace-nowrap">
                          {shortenSha(entry.detected_sha)}
                        </code>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-[140px_1fr] gap-2 text-sm">
                    <span className="text-muted-foreground font-medium inline-flex items-center gap-1">
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
          <TabsContent value="contents" className="mt-0 flex-1 overflow-hidden min-h-0">
            <div className="flex h-full">
              {/* Left Panel - File Tree */}
              <div className="w-[280px] flex-shrink-0 border-r overflow-hidden flex flex-col">
                {treeError ? (
                  <div className="flex flex-col items-center justify-center h-full p-6 text-center gap-4">
                    <AlertCircle className="h-8 w-8 text-destructive" aria-hidden="true" />
                    <div>
                      <p className="font-medium text-sm">
                        {getErrorMessage(treeError, true).title}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {getErrorMessage(treeError, true).description}
                      </p>
                    </div>
                    <div className="flex flex-col gap-2 w-full max-w-[200px]">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetchTree()}
                        className="w-full"
                      >
                        <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                        Try again
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        asChild
                        className="w-full"
                      >
                        <a
                          href={entry.upstream_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
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
                  />
                )}
              </div>

              {/* Right Panel - Content Pane with enhanced error handling */}
              <div className="flex-1 min-w-0 overflow-hidden">
                {contentError ? (
                  <div className="flex flex-col items-center justify-center h-full p-6 text-center gap-4">
                    <AlertCircle className="h-8 w-8 text-destructive" aria-hidden="true" />
                    <div>
                      <p className="font-medium text-sm">
                        {getErrorMessage(contentError, false).title}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {getErrorMessage(contentError, false).description}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetchContent()}
                      >
                        <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                        Try again
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        asChild
                      >
                        <a
                          href={entry.upstream_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
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
                  />
                )}
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Action Buttons */}
        <DialogFooter className="flex-shrink-0 border-t px-6 py-4 mt-auto">
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
  );
}
