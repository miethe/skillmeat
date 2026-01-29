'use client';

/**
 * SemanticTree Component
 *
 * Left pane navigation tree for marketplace folder view.
 * Displays folders filtered by semantic rules (excludes roots/leafs).
 * Integrates with useFolderSelection hook and TreeNode component.
 */

import { useMemo } from 'react';
import type { FolderTree } from '@/lib/tree-builder';
import { filterSemanticTree } from '@/lib/tree-filter-utils';
import { TreeNode } from './tree-node';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface SemanticTreeProps {
  /** Folder tree structure (will be filtered internally) */
  tree: FolderTree;
  /** Currently selected folder path */
  selectedFolder: string | null;
  /** Set of expanded folder paths */
  expanded: Set<string>;
  /** Callback when a folder is selected */
  onSelectFolder: (path: string) => void;
  /** Callback to toggle folder expansion */
  onToggleExpand: (path: string) => void;
  /** Optional className for the container */
  className?: string;
}

// ============================================================================
// Helper Components
// ============================================================================

interface TreeBranchProps {
  /** Folder nodes to render at this level */
  nodes: FolderTree;
  /** Current depth in the tree (0 = root level) */
  depth: number;
  /** Currently selected folder path */
  selectedFolder: string | null;
  /** Set of expanded folder paths */
  expanded: Set<string>;
  /** Callback when a folder is selected */
  onSelectFolder: (path: string) => void;
  /** Callback to toggle folder expansion */
  onToggleExpand: (path: string) => void;
}

/**
 * Recursively renders a branch of the tree.
 * Handles expansion state and child rendering.
 */
function TreeBranch({
  nodes,
  depth,
  selectedFolder,
  expanded,
  onSelectFolder,
  onToggleExpand,
}: TreeBranchProps) {
  // Sort folders alphabetically for consistent ordering
  const sortedNodes = useMemo(() => {
    return Object.values(nodes).sort((a, b) => a.name.localeCompare(b.name));
  }, [nodes]);

  if (sortedNodes.length === 0) {
    return null;
  }

  return (
    <div role="group">
      {sortedNodes.map((node) => {
        const isSelected = selectedFolder === node.fullPath;
        const isExpanded = expanded.has(node.fullPath);
        const hasChildren = Object.keys(node.children).length > 0;

        return (
          <div key={node.fullPath}>
            <TreeNode
              name={node.name}
              fullPath={node.fullPath}
              depth={depth}
              directCount={node.directCount}
              totalCount={node.totalArtifactCount}
              hasDirectArtifacts={node.hasDirectArtifacts}
              hasSubfolders={hasChildren}
              isSelected={isSelected}
              isExpanded={isExpanded}
              onSelect={() => onSelectFolder(node.fullPath)}
              onToggleExpand={() => onToggleExpand(node.fullPath)}
            />

            {/* Render children if expanded */}
            {isExpanded && hasChildren && (
              <TreeBranch
                nodes={node.children}
                depth={depth + 1}
                selectedFolder={selectedFolder}
                expanded={expanded}
                onSelectFolder={onSelectFolder}
                onToggleExpand={onToggleExpand}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * SemanticTree - Navigational tree for marketplace folder view
 *
 * Renders a hierarchical tree of folders filtered by semantic rules.
 * Root-level containers (plugins, src, etc.) and leaf artifact containers
 * (commands, agents, etc.) are excluded to show only meaningful navigation.
 *
 * @example
 * ```tsx
 * const { selectedFolder, setSelectedFolder, expanded, toggleExpand } = useFolderSelection(tree);
 *
 * <SemanticTree
 *   tree={tree}
 *   selectedFolder={selectedFolder}
 *   expanded={expanded}
 *   onSelectFolder={setSelectedFolder}
 *   onToggleExpand={toggleExpand}
 * />
 * ```
 */
export function SemanticTree({
  tree,
  selectedFolder,
  expanded,
  onSelectFolder,
  onToggleExpand,
  className,
}: SemanticTreeProps) {
  // Apply semantic filtering to the tree
  const filteredTree = useMemo(() => {
    return filterSemanticTree(tree);
  }, [tree]);

  const hasContent = Object.keys(filteredTree).length > 0;

  return (
    <nav
      role="tree"
      aria-label="Folder navigation"
      className={cn('overflow-y-auto', className)}
    >
      {hasContent ? (
        <TreeBranch
          nodes={filteredTree}
          depth={0}
          selectedFolder={selectedFolder}
          expanded={expanded}
          onSelectFolder={onSelectFolder}
          onToggleExpand={onToggleExpand}
        />
      ) : (
        <p className="py-4 text-center text-sm text-muted-foreground">
          No folders to display
        </p>
      )}
    </nav>
  );
}
