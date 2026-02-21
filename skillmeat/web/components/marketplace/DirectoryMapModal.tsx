/**
 * Directory Map Modal
 *
 * Modal for mapping directories to artifact types during GitHub source creation/update.
 * Allows users to manually specify which directories contain which artifact types.
 */

'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  Search,
  AlertCircle,
  Loader2,
  Save,
  X,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks';
import type { ArtifactType } from '@/types/marketplace';

// Available artifact types for directory mapping
const ARTIFACT_TYPES: ArtifactType[] = ['skill', 'command', 'agent', 'mcp_server', 'hook', 'composite'];

// Human-readable labels for artifact types
const ARTIFACT_TYPE_LABELS: Record<ArtifactType, string> = {
  skill: 'Skill',
  command: 'Command',
  agent: 'Agent',
  mcp_server: 'MCP Server',
  mcp: 'MCP Server',
  hook: 'Hook',
  composite: 'Plugin',
};

// ============================================================================
// Types
// ============================================================================

export interface DirectoryNode {
  path: string;
  name: string;
  type: 'tree' | 'blob';
  children?: DirectoryNode[];
}

interface DirectoryMapModalProps {
  /** Controls modal open state */
  open: boolean;
  /** Callback when modal open state changes */
  onOpenChange: (open: boolean) => void;
  /** Source ID for context (used in header/description) */
  sourceId: string;
  /** Repository owner and name for display */
  repoInfo?: { owner: string; repo: string; ref: string };
  /** Directory tree data from GitHub API */
  treeData?: DirectoryNode[];
  /** Loading state for tree data */
  isLoadingTree?: boolean;
  /** Error state for tree data */
  treeError?: string;
  /** Initial directory mappings to pre-populate the form */
  initialMappings?: Record<string, string>;
  /** Callback when user confirms the mappings */
  onConfirm?: (mappings: Record<string, string>) => void;
  /** Callback when user confirms the mappings and triggers rescan */
  onConfirmAndRescan?: (mappings: Record<string, string>) => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Build tree structure from flat GitHub tree API response
 */
function buildTree(items: Array<{ path: string; type: 'tree' | 'blob' }>): DirectoryNode[] {
  const root: DirectoryNode[] = [];
  const nodeMap = new Map<string, DirectoryNode>();

  // Sort by path depth to ensure parents are processed first
  const sorted = [...items].sort((a, b) => {
    const aDepth = a.path.split('/').length;
    const bDepth = b.path.split('/').length;
    return aDepth - bDepth;
  });

  for (const item of sorted) {
    // Only process directories
    if (item.type !== 'tree') continue;

    const parts = item.path.split('/');
    const name = parts[parts.length - 1] || item.path;
    const node: DirectoryNode = {
      path: item.path,
      name,
      type: item.type,
      children: [],
    };

    nodeMap.set(item.path, node);

    if (parts.length === 1) {
      // Top-level item
      root.push(node);
    } else {
      // Find parent
      const parentPath = parts.slice(0, -1).join('/');
      const parent = nodeMap.get(parentPath);
      if (parent && parent.children) {
        parent.children.push(node);
      }
    }
  }

  return root;
}

/**
 * Get all descendant paths for a given node
 */
function getAllDescendantPaths(node: DirectoryNode): string[] {
  const paths: string[] = [];

  function traverse(n: DirectoryNode) {
    if (n.children) {
      for (const child of n.children) {
        paths.push(child.path);
        traverse(child);
      }
    }
  }

  traverse(node);
  return paths;
}

/**
 * Find a node by path in the tree
 */
function findNodeByPath(nodes: DirectoryNode[], targetPath: string): DirectoryNode | null {
  for (const node of nodes) {
    if (node.path === targetPath) {
      return node;
    }
    if (node.children) {
      const found = findNodeByPath(node.children, targetPath);
      if (found) return found;
    }
  }
  return null;
}

/**
 * Get parent path from a given path
 */
function getParentPath(path: string): string | null {
  const parts = path.split('/');
  if (parts.length <= 1) return null;
  return parts.slice(0, -1).join('/');
}

/**
 * Check if a node has any selected descendants
 */
function hasSelectedDescendants(
  node: DirectoryNode,
  selectedPaths: Map<string, ArtifactType | null>
): boolean {
  if (node.children) {
    for (const child of node.children) {
      if (selectedPaths.has(child.path)) return true;
      if (hasSelectedDescendants(child, selectedPaths)) return true;
    }
  }
  return false;
}

/**
 * Get inherited artifact type from parent path
 */
function getInheritedType(
  path: string,
  selectedPaths: Map<string, ArtifactType | null>
): ArtifactType | null {
  let currentPath = path;

  while (currentPath) {
    const parentPath = getParentPath(currentPath);
    if (!parentPath) break;

    const parentType = selectedPaths.get(parentPath);
    if (parentType) return parentType;

    currentPath = parentPath;
  }

  return null;
}

/**
 * Filter tree nodes by search query
 */
function filterTree(nodes: DirectoryNode[], query: string): DirectoryNode[] {
  if (!query) return nodes;

  const lowerQuery = query.toLowerCase();
  const filtered: DirectoryNode[] = [];

  for (const node of nodes) {
    const matches =
      node.name.toLowerCase().includes(lowerQuery) || node.path.toLowerCase().includes(lowerQuery);

    if (node.children && node.children.length > 0) {
      const filteredChildren = filterTree(node.children, query);
      if (matches || filteredChildren.length > 0) {
        filtered.push({
          ...node,
          children: filteredChildren.length > 0 ? filteredChildren : node.children,
        });
      }
    } else if (matches) {
      filtered.push(node);
    }
  }

  return filtered;
}

/**
 * Count total directories in tree
 */
function countDirectories(nodes: DirectoryNode[]): number {
  let count = 0;
  for (const node of nodes) {
    if (node.type === 'tree') {
      count++;
      if (node.children) {
        count += countDirectories(node.children);
      }
    }
  }
  return count;
}

// ============================================================================
// TreeNode Component
// ============================================================================

interface TreeNodeProps {
  node: DirectoryNode;
  level: number;
  selectedPaths: Map<string, ArtifactType | null>;
  expandedPaths: Set<string>;
  tree: DirectoryNode[];
  onToggleSelect: (path: string) => void;
  onToggleExpand: (path: string) => void;
  onTypeChange: (path: string, type: ArtifactType | null) => void;
}

function TreeNode({
  node,
  level,
  selectedPaths,
  expandedPaths,
  tree,
  onToggleSelect,
  onToggleExpand,
  onTypeChange,
}: TreeNodeProps) {
  const isExpanded = expandedPaths.has(node.path);
  const isSelected = selectedPaths.has(node.path);
  const selectedType = selectedPaths.get(node.path);

  // Check for inherited type from parent
  const inheritedType = getInheritedType(node.path, selectedPaths);
  const isInherited = !isSelected && inheritedType !== null;

  // Check if this is a partial selection (some children selected, not all)
  const hasPartialSelection = !isSelected && hasSelectedDescendants(node, selectedPaths);

  // Display type: explicit selection or inherited from parent
  const displayType = selectedType || inheritedType;

  const handleCheckboxChange = useCallback(() => {
    onToggleSelect(node.path);
  }, [node.path, onToggleSelect]);

  const handleToggle = useCallback(() => {
    onToggleExpand(node.path);
  }, [node.path, onToggleExpand]);

  const childCount = node.children?.length || 0;

  return (
    <div role="none">
      <div
        className={cn(
          'flex items-center gap-2 rounded px-2 py-1.5 transition-colors hover:bg-accent',
          isSelected && 'bg-accent/50',
          isInherited && 'bg-accent/20'
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        {/* Expand/collapse button */}
        <button
          type="button"
          onClick={handleToggle}
          className="flex-shrink-0 rounded p-0.5 transition-colors hover:bg-accent-foreground/10"
          aria-label={isExpanded ? 'Collapse directory' : 'Expand directory'}
          aria-expanded={isExpanded}
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </button>

        {/* Checkbox */}
        <Checkbox
          checked={isSelected ? true : hasPartialSelection ? 'indeterminate' : false}
          onCheckedChange={handleCheckboxChange}
          aria-label={`Select ${node.name} directory`}
        />

        {/* Folder icon */}
        {isExpanded ? (
          <FolderOpen className="h-4 w-4 flex-shrink-0 text-blue-500" aria-hidden="true" />
        ) : (
          <Folder className="h-4 w-4 flex-shrink-0 text-blue-500" aria-hidden="true" />
        )}

        {/* Directory name and path */}
        <div className="min-w-0 flex-1">
          <span className="text-sm font-medium">{node.name}</span>
          <span className="ml-2 truncate text-xs text-muted-foreground">{node.path}</span>
        </div>

        {/* Child count badge */}
        {childCount > 0 && (
          <span className="flex-shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {childCount}
          </span>
        )}

        {/* Type selector (shown when selected) */}
        {isSelected && (
          <Select
            value={selectedType || ''}
            onValueChange={(value) =>
              onTypeChange(node.path, value ? (value as ArtifactType) : null)
            }
          >
            <SelectTrigger
              className="h-8 w-[140px]"
              aria-label={`Select artifact type for ${node.name}`}
              onClick={(e) => e.stopPropagation()}
            >
              <SelectValue placeholder="Select type..." />
            </SelectTrigger>
            <SelectContent>
              {ARTIFACT_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {ARTIFACT_TYPE_LABELS[type]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {/* Inherited type indicator (shown when not selected but has inherited type) */}
        {isInherited && displayType && (
          <div className="flex items-center gap-1.5 text-xs italic text-muted-foreground">
            <span className="rounded-full border border-dashed bg-muted/50 px-2 py-0.5">
              {ARTIFACT_TYPE_LABELS[displayType]}
            </span>
            <span className="text-[10px]">(inherited)</span>
          </div>
        )}
      </div>

      {/* Render children when expanded */}
      {isExpanded && node.children && node.children.length > 0 && (
        <div role="group" aria-label={`Contents of ${node.name}`}>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              level={level + 1}
              selectedPaths={selectedPaths}
              expandedPaths={expandedPaths}
              tree={tree}
              onToggleSelect={onToggleSelect}
              onToggleExpand={onToggleExpand}
              onTypeChange={onTypeChange}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Loading Skeleton
// ============================================================================

function TreeSkeleton() {
  return (
    <div className="space-y-2 p-2">
      {[...Array(8)].map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-2"
          style={{ paddingLeft: `${(i % 3) * 16 + 8}px` }}
        >
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 flex-1" />
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * DirectoryMapModal Component
 *
 * Provides a modal interface for mapping directory paths to artifact types.
 * Used during GitHub source setup to help the scanner identify artifacts.
 *
 * Features:
 * - Hierarchical directory tree view from GitHub API
 * - Checkbox selection for directories
 * - Expand/collapse directory nodes
 * - Inline artifact type dropdown for each selected directory
 * - Search/filter directories by name or path
 * - Keyboard navigation support (Arrow keys, Space, Enter)
 *
 * @example
 * ```tsx
 * <DirectoryMapModal
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   sourceId="source-123"
 *   repoInfo={{ owner: "anthropics", repo: "skills", ref: "main" }}
 *   treeData={[
 *     { path: "skills", name: "skills", type: "tree" },
 *     { path: "agents", name: "agents", type: "tree" },
 *   ]}
 *   initialMappings={{ "skills/": "skill", "agents/": "agent" }}
 *   onConfirm={(mappings) => console.log(mappings)}
 * />
 * ```
 */
export function DirectoryMapModal({
  open,
  onOpenChange,
  sourceId,
  repoInfo,
  treeData = [],
  isLoadingTree = false,
  treeError,
  initialMappings = {},
  onConfirm,
  onConfirmAndRescan,
}: DirectoryMapModalProps) {
  // State for managing directory selections (path -> artifact type)
  const [selectedPaths, setSelectedPaths] = useState<Map<string, ArtifactType | null>>(new Map());
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [showConfirmClose, setShowConfirmClose] = useState(false);

  const { toast } = useToast();

  // Build tree structure from flat data
  const tree = useMemo(() => buildTree(treeData), [treeData]);

  // Filter tree based on search query
  const filteredTree = useMemo(() => filterTree(tree, searchQuery), [tree, searchQuery]);

  // Count total directories for display
  const totalDirectories = useMemo(() => countDirectories(tree), [tree]);

  // Initialize selected paths from initial mappings
  useEffect(() => {
    if (open) {
      const paths = new Map<string, ArtifactType | null>();
      for (const [path, type] of Object.entries(initialMappings)) {
        paths.set(path, type as ArtifactType);
      }
      setSelectedPaths(paths);
      setIsDirty(false); // Reset dirty state when opening

      // Auto-expand paths that have initial mappings
      if (Object.keys(initialMappings).length > 0) {
        const toExpand = new Set<string>();
        for (const path of Object.keys(initialMappings)) {
          const parts = path.split('/');
          for (let i = 1; i < parts.length; i++) {
            toExpand.add(parts.slice(0, i).join('/'));
          }
        }
        setExpandedPaths(toExpand);
      }
    }
  }, [open, initialMappings]);

  // Auto-expand directories when searching
  useEffect(() => {
    if (searchQuery) {
      const allPaths = new Set<string>();
      const collectPaths = (nodes: DirectoryNode[]) => {
        for (const node of nodes) {
          allPaths.add(node.path);
          if (node.children) {
            collectPaths(node.children);
          }
        }
      };
      collectPaths(filteredTree);
      setExpandedPaths(allPaths);
    }
  }, [searchQuery, filteredTree]);

  const handleToggleSelect = useCallback(
    (path: string) => {
      setSelectedPaths((prev) => {
        const next = new Map(prev);
        const node = findNodeByPath(tree, path);

        if (!node) return next;

        if (next.has(path)) {
          // Deselecting: remove this path and all descendants
          next.delete(path);
          const descendantPaths = getAllDescendantPaths(node);
          for (const descendantPath of descendantPaths) {
            next.delete(descendantPath);
          }
        } else {
          // Selecting: add this path and all descendants with same type
          const currentType = next.get(path) || null;
          next.set(path, currentType);

          // Auto-select all descendants with the same type (or null if parent has no type)
          const descendantPaths = getAllDescendantPaths(node);
          for (const descendantPath of descendantPaths) {
            // Only auto-select if not already explicitly selected with a different type
            if (!next.has(descendantPath)) {
              next.set(descendantPath, currentType);
            }
          }
        }

        return next;
      });
      setIsDirty(true); // Mark as dirty when selection changes
    },
    [tree]
  );

  const handleToggleExpand = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const handleTypeChange = useCallback(
    (path: string, type: ArtifactType | null) => {
      setSelectedPaths((prev) => {
        const next = new Map(prev);
        const node = findNodeByPath(tree, path);

        if (!node) {
          // Simple case: just update this path
          next.set(path, type);
          return next;
        }

        // Update this path
        next.set(path, type);

        // Propagate type to descendants that don't have an explicit override
        const descendantPaths = getAllDescendantPaths(node);
        for (const descendantPath of descendantPaths) {
          // Only propagate if the child is selected but has no type set (null)
          // This allows children to override the parent type
          if (next.has(descendantPath) && next.get(descendantPath) === null) {
            next.set(descendantPath, type);
          }
        }

        return next;
      });
      setIsDirty(true); // Mark as dirty when type changes
    },
    [tree]
  );

  const handleCancel = () => {
    if (isDirty) {
      setShowConfirmClose(true);
    } else {
      setSearchQuery('');
      onOpenChange(false);
    }
  };

  const handleConfirmClose = () => {
    setShowConfirmClose(false);
    setSearchQuery('');
    setIsDirty(false);
    onOpenChange(false);
  };

  const handleCancelClose = () => {
    setShowConfirmClose(false);
  };

  const handleSave = async () => {
    // Convert selected paths to mappings format (path -> type)
    const mappings: Record<string, string> = {};
    selectedPaths.forEach((type, path) => {
      if (type) {
        mappings[path] = type;
      }
    });

    setIsSaving(true);
    try {
      await onConfirm?.(mappings);
      toast({
        title: 'Mappings saved',
        description: `${Object.keys(mappings).length} directory mappings saved successfully`,
      });
      setSearchQuery('');
      setIsDirty(false);
      onOpenChange(false);
    } catch (error) {
      toast({
        title: 'Failed to save mappings',
        description: error instanceof Error ? error.message : 'An error occurred',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAndRescan = async () => {
    // Convert selected paths to mappings format (path -> type)
    const mappings: Record<string, string> = {};
    selectedPaths.forEach((type, path) => {
      if (type) {
        mappings[path] = type;
      }
    });

    setIsSaving(true);
    try {
      await onConfirmAndRescan?.(mappings);
      toast({
        title: 'Mappings saved and rescan triggered',
        description: `${Object.keys(mappings).length} directory mappings saved. Rescan in progress...`,
      });
      setSearchQuery('');
      setIsDirty(false);
      onOpenChange(false);
    } catch (error) {
      toast({
        title: 'Failed to save and rescan',
        description: error instanceof Error ? error.message : 'An error occurred',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Count selected directories with assigned types
  const selectedCount = Array.from(selectedPaths.values()).filter(Boolean).length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex max-h-[85vh] flex-col sm:max-w-4xl"
        aria-describedby="directory-map-description"
      >
        <DialogHeader>
          <DialogTitle>Map Directories to Artifact Types</DialogTitle>
          <DialogDescription id="directory-map-description">
            {repoInfo ? (
              <>
                Select directories containing artifacts in{' '}
                <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                  {repoInfo.owner}/{repoInfo.repo}@{repoInfo.ref}
                </code>
              </>
            ) : (
              `Select directories containing artifacts for source ${sourceId}`
            )}
          </DialogDescription>
        </DialogHeader>

        {/* Search input */}
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search directories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
            aria-label="Search directories"
          />
        </div>

        {/* Directory tree */}
        <div className="max-h-[450px] min-h-[350px] flex-1 overflow-auto rounded-md border">
          {isLoadingTree ? (
            <TreeSkeleton />
          ) : treeError ? (
            <div className="flex flex-col items-center justify-center px-4 py-12 text-center">
              <AlertCircle className="mb-4 h-12 w-12 text-destructive opacity-50" />
              <h3 className="mb-2 text-sm font-medium text-destructive">
                Failed to load directories
              </h3>
              <p className="max-w-md text-xs text-muted-foreground">{treeError}</p>
            </div>
          ) : filteredTree.length === 0 ? (
            <div className="flex flex-col items-center justify-center px-4 py-12 text-center">
              <Folder className="mb-4 h-12 w-12 text-muted-foreground opacity-50" />
              <h3 className="mb-2 text-sm font-medium text-muted-foreground">
                {searchQuery ? 'No directories match your search' : 'No directories found'}
              </h3>
              <p className="text-xs text-muted-foreground">
                {searchQuery ? 'Try a different search term' : 'This repository has no directories'}
              </p>
            </div>
          ) : (
            <div className="p-2" role="tree" aria-label="Directory tree">
              {filteredTree.map((node) => (
                <TreeNode
                  key={node.path}
                  node={node}
                  level={0}
                  selectedPaths={selectedPaths}
                  expandedPaths={expandedPaths}
                  tree={tree}
                  onToggleSelect={handleToggleSelect}
                  onToggleExpand={handleToggleExpand}
                  onTypeChange={handleTypeChange}
                />
              ))}
            </div>
          )}
        </div>

        {/* Summary and stats */}
        <div className="flex items-center justify-between border-t pt-3 text-sm text-muted-foreground">
          <div>
            {totalDirectories > 0 && (
              <span>
                {totalDirectories} {totalDirectories === 1 ? 'directory' : 'directories'} total
              </span>
            )}
          </div>
          <div>
            {selectedCount > 0 && (
              <span className="font-medium text-foreground">
                {selectedCount} {selectedCount === 1 ? 'mapping' : 'mappings'} configured
              </span>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button type="button" variant="outline" onClick={handleCancel} disabled={isSaving}>
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={handleSave}
              disabled={selectedCount === 0 || isSaving || !isDirty}
            >
              {isSaving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save ({selectedCount})
            </Button>
            <Button
              type="button"
              onClick={handleSaveAndRescan}
              disabled={selectedCount === 0 || isSaving || !isDirty}
            >
              {isSaving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Save & Rescan
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>

      {/* Confirmation dialog for closing with unsaved changes */}
      <Dialog open={showConfirmClose} onOpenChange={setShowConfirmClose}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Unsaved Changes</DialogTitle>
            <DialogDescription>
              You have unsaved directory mappings. Are you sure you want to close without saving?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCancelClose}>
              Keep Editing
            </Button>
            <Button type="button" variant="destructive" onClick={handleConfirmClose}>
              Discard Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Dialog>
  );
}
