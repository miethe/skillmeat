'use client';

import { useState, useCallback } from 'react';
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
// TreeNode Component
// ============================================================================

interface TreeNodeProps {
  node: FileNode;
  level: number;
  selectedPath: string | null;
  expandedPaths: Set<string>;
  onSelect: (path: string) => void;
  onToggle: (path: string) => void;
  onDelete?: (path: string) => void;
}

function TreeNode({
  node,
  level,
  selectedPath,
  expandedPaths,
  onSelect,
  onToggle,
  onDelete,
}: TreeNodeProps) {
  const isExpanded = expandedPaths.has(node.path);
  const isSelected = selectedPath === node.path;
  const isDirectory = node.type === 'directory';

  const handleClick = useCallback(() => {
    if (isDirectory) {
      onToggle(node.path);
    } else {
      onSelect(node.path);
    }
  }, [isDirectory, node.path, onSelect, onToggle]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleClick();
      } else if (e.key === 'ArrowRight' && isDirectory && !isExpanded) {
        e.preventDefault();
        onToggle(node.path);
      } else if (e.key === 'ArrowLeft' && isDirectory && isExpanded) {
        e.preventDefault();
        onToggle(node.path);
      }
    },
    [handleClick, isDirectory, isExpanded, node.path, onToggle]
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
    <div>
      <div
        role="button"
        tabIndex={0}
        className={cn(
          'group flex cursor-pointer items-center gap-1 rounded px-2 py-1 transition-colors hover:bg-accent',
          isSelected && 'bg-accent text-accent-foreground',
          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring'
        )}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
      >
        {isDirectory ? (
          <span className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </span>
        ) : (
          <span className="w-4 flex-shrink-0" />
        )}

        <IconComponent
          className={cn(
            'h-4 w-4 flex-shrink-0',
            isDirectory ? 'text-blue-500' : 'text-muted-foreground'
          )}
        />

        <span className="min-w-0 flex-1 truncate text-sm">{node.name}</span>

        {onDelete && !isDirectory && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100"
            onClick={handleDelete}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        )}
      </div>

      {isDirectory && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              level={level + 1}
              selectedPath={selectedPath}
              expandedPaths={expandedPaths}
              onSelect={onSelect}
              onToggle={onToggle}
              onDelete={onDelete}
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
 * - Keyboard navigation (arrow keys, enter)
 * - Optional context actions (delete)
 * - Loading skeleton state
 *
 * @example
 * ```tsx
 * <FileTree
 *   entityId="skill-123"
 *   files={fileStructure}
 *   selectedPath={selectedPath}
 *   onSelect={(path) => setSelectedPath(path)}
 *   onDeleteFile={(path) => handleDelete(path)}
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
}: FileTreeProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

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

  if (isLoading) {
    return <FileTreeSkeleton />;
  }

  if (files.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center py-12 text-center">
        <Folder className="mb-4 h-12 w-12 text-muted-foreground opacity-50" />
        <h3 className="mb-1 text-sm font-medium text-muted-foreground">No files found</h3>
        <p className="text-xs text-muted-foreground">This entity does not contain any files yet.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header with optional actions */}
      {onAddFile && (
        <div className="flex items-center justify-between border-b p-2">
          <span className="text-xs font-medium text-muted-foreground">FILES</span>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onAddFile}>
            <Plus className="h-3 w-3" />
          </Button>
        </div>
      )}

      {/* File tree */}
      <div className="flex-1 overflow-auto p-2">
        {files.map((node) => (
          <TreeNode
            key={node.path}
            node={node}
            level={0}
            selectedPath={selectedPath}
            expandedPaths={expandedPaths}
            onSelect={onSelect}
            onToggle={handleToggle}
            onDelete={onDeleteFile}
          />
        ))}
      </div>
    </div>
  );
}
