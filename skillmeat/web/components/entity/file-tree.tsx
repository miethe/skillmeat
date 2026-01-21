'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  FileText,
  FileCode,
  File,
  Braces,
  Trash2,
  Plus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

// ============================================================================
// Types
// ============================================================================

export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
}

export interface FileTreeProps {
  entityId: string;
  files: FileNode[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onAddFile?: () => void;
  onDeleteFile?: (path: string) => void;
  isLoading?: boolean;
  /**
   * When true, hides create/delete buttons while keeping
   * file selection and expand/collapse functionality.
   * @default false
   */
  readOnly?: boolean;
  /**
   * Accessible label for the file tree.
   * @default "File browser"
   */
  ariaLabel?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get the appropriate icon for a file based on its extension
 */
function getFileIcon(fileName: string) {
  const extension = fileName.split('.').pop()?.toLowerCase();

  switch (extension) {
    case 'md':
    case 'txt':
      return FileText;
    case 'ts':
    case 'tsx':
    case 'js':
    case 'jsx':
    case 'py':
    case 'java':
    case 'cpp':
    case 'c':
    case 'go':
    case 'rs':
      return FileCode;
    case 'json':
      return Braces;
    default:
      return File;
  }
}

// ============================================================================
// Helper: Flatten tree to ordered list for keyboard navigation
// ============================================================================

/**
 * Flatten tree nodes into a linear list for keyboard navigation.
 * Only includes visible nodes (respects expanded state).
 */
function flattenVisibleNodes(nodes: FileNode[], expandedPaths: Set<string>): FileNode[] {
  const result: FileNode[] = [];

  function traverse(nodeList: FileNode[]) {
    for (const node of nodeList) {
      result.push(node);
      if (node.type === 'directory' && expandedPaths.has(node.path) && node.children) {
        traverse(node.children);
      }
    }
  }

  traverse(nodes);
  return result;
}

// ============================================================================
// TreeNode Component
// ============================================================================

interface TreeNodeProps {
  node: FileNode;
  level: number;
  selectedPath: string | null;
  focusedPath: string | null;
  expandedPaths: Set<string>;
  onSelect: (path: string) => void;
  onToggle: (path: string) => void;
  onDelete?: (path: string) => void;
  onFocus: (path: string) => void;
  onKeyNavigation: (e: React.KeyboardEvent, node: FileNode) => void;
  /** Total number of visible items in the tree (for aria-setsize) */
  treeSize: number;
  /** 1-based position of this item in the visible tree (for aria-posinset) */
  positionInSet: number;
}

function TreeNode({
  node,
  level,
  selectedPath,
  focusedPath,
  expandedPaths,
  onSelect,
  onToggle,
  onDelete,
  onFocus,
  onKeyNavigation,
  treeSize,
  positionInSet,
}: TreeNodeProps) {
  const nodeRef = useRef<HTMLDivElement>(null);
  const isExpanded = expandedPaths.has(node.path);
  const isSelected = selectedPath === node.path;
  const isFocused = focusedPath === node.path;
  const isDirectory = node.type === 'directory';

  // Focus the element when it becomes the focused item (roving tabindex)
  useEffect(() => {
    if (isFocused && nodeRef.current) {
      nodeRef.current.focus();
    }
  }, [isFocused]);

  const handleClick = useCallback(() => {
    onFocus(node.path);
    if (isDirectory) {
      onToggle(node.path);
    } else {
      onSelect(node.path);
    }
  }, [isDirectory, node.path, onSelect, onToggle, onFocus]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Handle Enter and Space for activation
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (isDirectory) {
          onToggle(node.path);
        } else {
          onSelect(node.path);
        }
        return;
      }

      // Handle ArrowRight to expand directory
      if (e.key === 'ArrowRight' && isDirectory) {
        e.preventDefault();
        if (!isExpanded) {
          onToggle(node.path);
        }
        return;
      }

      // Handle ArrowLeft to collapse directory
      if (e.key === 'ArrowLeft' && isDirectory && isExpanded) {
        e.preventDefault();
        onToggle(node.path);
        return;
      }

      // Delegate Up/Down/Home/End navigation to parent
      onKeyNavigation(e, node);
    },
    [isDirectory, isExpanded, node, onSelect, onToggle, onKeyNavigation]
  );

  const handleDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (onDelete) {
        onDelete(node.path);
      }
    },
    [node.path, onDelete]
  );

  const IconComponent = isDirectory ? (isExpanded ? FolderOpen : Folder) : getFileIcon(node.name);

  return (
    <div role="none">
      <div
        ref={nodeRef}
        role="treeitem"
        tabIndex={isFocused ? 0 : -1}
        aria-selected={isSelected}
        aria-expanded={isDirectory ? isExpanded : undefined}
        aria-level={level + 1}
        aria-setsize={treeSize}
        aria-posinset={positionInSet}
        data-testid={`tree-item-${node.path}`}
        className={cn(
          'group flex cursor-pointer items-center gap-1 rounded px-2 py-1 transition-colors hover:bg-accent',
          isSelected && 'bg-accent text-accent-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
        )}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        onFocus={() => onFocus(node.path)}
      >
        {isDirectory ? (
          <span className="flex-shrink-0" aria-hidden="true">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </span>
        ) : (
          <span className="w-4 flex-shrink-0" aria-hidden="true" />
        )}

        <IconComponent
          className={cn(
            'h-4 w-4 flex-shrink-0',
            isDirectory ? 'text-blue-500' : 'text-muted-foreground'
          )}
          aria-hidden="true"
        />

        <span className="min-w-0 flex-1 truncate text-sm">{node.name}</span>

        {onDelete && !isDirectory && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 transition-opacity focus:opacity-100 group-hover:opacity-100"
            onClick={handleDelete}
            aria-label={`Delete ${node.name}`}
            tabIndex={-1}
          >
            <Trash2 className="h-3 w-3" aria-hidden="true" />
          </Button>
        )}
      </div>

      {isDirectory && isExpanded && node.children && (
        <div role="group" aria-label={`Contents of ${node.name}`}>
          {node.children.map((child, index) => {
            // Calculate position in the flattened visible list
            // This is a simplified version - the parent handles the full calculation
            return (
              <TreeNode
                key={child.path}
                node={child}
                level={level + 1}
                selectedPath={selectedPath}
                focusedPath={focusedPath}
                expandedPaths={expandedPaths}
                onSelect={onSelect}
                onToggle={onToggle}
                onDelete={onDelete}
                onFocus={onFocus}
                onKeyNavigation={onKeyNavigation}
                treeSize={treeSize}
                positionInSet={index + 1}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Loading Skeleton
// ============================================================================

function FileTreeSkeleton() {
  return (
    <div className="space-y-2 p-2">
      {[...Array(8)].map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-2"
          style={{ paddingLeft: `${(i % 3) * 12 + 8}px` }}
        >
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
 * FileTree - Recursive file browser component
 *
 * Displays a hierarchical tree of files and directories with expand/collapse functionality.
 * Supports keyboard navigation, file selection, and optional delete actions.
 *
 * Features:
 * - Recursive rendering of nested directories
 * - Expandable/collapsible folders with chevron icons
 * - File type icons (markdown, code, JSON, etc.)
 * - Selected file highlighting
 * - Full keyboard navigation (Arrow keys, Enter, Space, Home, End)
 * - ARIA tree pattern for screen reader accessibility
 * - Roving tabindex for efficient keyboard focus management
 * - Optional context actions (delete)
 * - Loading skeleton state
 * - Read-only mode (hides create/delete buttons)
 *
 * Keyboard Controls:
 * - ArrowUp/ArrowDown: Move focus between visible items
 * - ArrowRight: Expand folder (if collapsed) or move to first child
 * - ArrowLeft: Collapse folder (if expanded) or move to parent
 * - Enter/Space: Select file or toggle folder
 * - Home: Move to first item
 * - End: Move to last visible item
 *
 * @example
 * ```tsx
 * // Editable mode (default)
 * <FileTree
 *   entityId="skill-123"
 *   files={fileStructure}
 *   selectedPath={selectedPath}
 *   onSelect={(path) => setSelectedPath(path)}
 *   onDeleteFile={(path) => handleDelete(path)}
 * />
 *
 * // Read-only mode (no create/delete buttons)
 * <FileTree
 *   entityId="skill-123"
 *   files={fileStructure}
 *   selectedPath={selectedPath}
 *   onSelect={(path) => setSelectedPath(path)}
 *   readOnly
 *   ariaLabel="Artifact file browser"
 * />
 * ```
 */
export function FileTree({
  entityId: _entityId,
  files,
  selectedPath,
  onSelect,
  onAddFile,
  onDeleteFile,
  isLoading = false,
  readOnly = false,
  ariaLabel = 'File browser',
}: FileTreeProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [focusedPath, setFocusedPath] = useState<string | null>(null);
  const treeRef = useRef<HTMLDivElement>(null);

  // Get flat list of all visible nodes for keyboard navigation
  const visibleNodes = flattenVisibleNodes(files, expandedPaths);

  // Initialize focus to first item or selected item
  useEffect(() => {
    if (focusedPath === null && visibleNodes.length > 0) {
      // If there's a selected path, focus it; otherwise focus first item
      const firstNode = visibleNodes[0];
      if (selectedPath && visibleNodes.some((n) => n.path === selectedPath)) {
        setFocusedPath(selectedPath);
      } else if (firstNode) {
        setFocusedPath(firstNode.path);
      }
    }
  }, [focusedPath, visibleNodes, selectedPath]);

  const handleToggle = useCallback((path: string) => {
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

  const handleFocus = useCallback((path: string) => {
    setFocusedPath(path);
  }, []);

  // Handle keyboard navigation for the tree
  const handleKeyNavigation = useCallback(
    (e: React.KeyboardEvent, currentNode: FileNode) => {
      const currentIndex = visibleNodes.findIndex((n) => n.path === currentNode.path);
      if (currentIndex === -1) return;

      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault();
          const nextNode = visibleNodes[currentIndex + 1];
          if (nextNode) {
            setFocusedPath(nextNode.path);
          }
          break;
        }
        case 'ArrowUp': {
          e.preventDefault();
          const prevNode = visibleNodes[currentIndex - 1];
          if (prevNode) {
            setFocusedPath(prevNode.path);
          }
          break;
        }
        case 'Home': {
          e.preventDefault();
          const firstNode = visibleNodes[0];
          if (firstNode) {
            setFocusedPath(firstNode.path);
          }
          break;
        }
        case 'End': {
          e.preventDefault();
          const lastNode = visibleNodes[visibleNodes.length - 1];
          if (lastNode) {
            setFocusedPath(lastNode.path);
          }
          break;
        }
        case 'ArrowLeft': {
          // If not a directory or not expanded, try to move to parent
          e.preventDefault();
          const isDirectory = currentNode.type === 'directory';
          const isExpanded = expandedPaths.has(currentNode.path);

          if (isDirectory && isExpanded) {
            // Let TreeNode handle collapsing
            return;
          }

          // Find parent directory
          const pathParts = currentNode.path.split('/');
          if (pathParts.length > 1) {
            pathParts.pop();
            const parentPath = pathParts.join('/');
            const parentNode = visibleNodes.find((n) => n.path === parentPath);
            if (parentNode) {
              setFocusedPath(parentPath);
            }
          }
          break;
        }
        case 'ArrowRight': {
          // If directory is expanded, move to first child
          const isDirectory = currentNode.type === 'directory';
          const isExpanded = expandedPaths.has(currentNode.path);

          if (isDirectory && isExpanded && currentNode.children?.length) {
            e.preventDefault();
            const firstChild = currentNode.children[0];
            if (firstChild) {
              setFocusedPath(firstChild.path);
            }
          }
          // If not expanded, TreeNode will handle expanding
          break;
        }
      }
    },
    [visibleNodes, expandedPaths]
  );

  if (isLoading) {
    return <FileTreeSkeleton />;
  }

  if (files.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center py-12 text-center">
        <Folder className="mb-4 h-12 w-12 text-muted-foreground opacity-50" aria-hidden="true" />
        <h3 className="mb-1 text-sm font-medium text-muted-foreground">No files found</h3>
        <p className="text-xs text-muted-foreground">This entity does not contain any files yet.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header with optional actions */}
      {onAddFile && !readOnly && (
        <div className="flex items-center justify-between border-b p-2">
          <span className="whitespace-nowrap text-xs font-medium text-muted-foreground">FILES</span>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 flex-shrink-0"
            onClick={onAddFile}
            aria-label="Add new file"
          >
            <Plus className="h-3 w-3" aria-hidden="true" />
          </Button>
        </div>
      )}

      {/* File tree with ARIA tree role */}
      <div
        ref={treeRef}
        role="tree"
        aria-label={ariaLabel}
        className="flex-1 overflow-auto p-2"
        data-testid="file-tree"
      >
        {files.map((node, index) => (
          <TreeNode
            key={node.path}
            node={node}
            level={0}
            selectedPath={selectedPath}
            focusedPath={focusedPath}
            expandedPaths={expandedPaths}
            onSelect={onSelect}
            onToggle={handleToggle}
            onDelete={readOnly ? undefined : onDeleteFile}
            onFocus={handleFocus}
            onKeyNavigation={handleKeyNavigation}
            treeSize={visibleNodes.length}
            positionInSet={index + 1}
          />
        ))}
      </div>
    </div>
  );
}
