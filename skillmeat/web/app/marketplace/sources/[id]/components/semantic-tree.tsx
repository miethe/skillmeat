'use client';

/**
 * SemanticTree Component
 *
 * Left pane navigation tree for marketplace folder view.
 * Displays folders filtered by semantic rules (excludes roots/leafs).
 * Integrates with useFolderSelection hook and TreeNode component.
 *
 * Keyboard Navigation (WAI-ARIA TreeView pattern):
 * - Arrow Up/Down: Navigate between visible tree items
 * - Arrow Left: Collapse folder or move to parent
 * - Arrow Right: Expand folder or move to first child
 * - Enter/Space: Select the focused folder
 * - Home: Jump to first tree item
 * - End: Jump to last visible tree item
 * - Tab: Exit tree (roving tabindex pattern - single tab stop)
 *
 * Performance: Uses lazy rendering - collapsed folders have 0 child DOM nodes.
 * Children are only rendered when the parent folder is expanded, preventing
 * DOM explosion for large trees (typically 60-80% DOM reduction).
 */

import { useMemo, useCallback, useRef, useState, useEffect } from 'react';
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
  /** Enable DOM node count logging in development (for performance validation) */
  debugDomCount?: boolean;
}

/** Flat representation of a visible tree item for keyboard navigation */
interface VisibleTreeItem {
  path: string;
  parentPath: string | null;
  hasChildren: boolean;
  isExpanded: boolean;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Flatten visible tree items into a list for keyboard navigation.
 * Only includes items that are visible (not hidden by collapsed parents).
 */
function getVisibleItems(
  tree: FolderTree,
  expanded: Set<string>,
  parentPath: string | null = null
): VisibleTreeItem[] {
  const items: VisibleTreeItem[] = [];

  // Sort nodes alphabetically for consistent ordering
  const sortedNodes = Object.values(tree).sort((a, b) =>
    a.name.localeCompare(b.name)
  );

  for (const node of sortedNodes) {
    const hasChildren = Object.keys(node.children).length > 0;
    const isExpanded = expanded.has(node.fullPath);

    items.push({
      path: node.fullPath,
      parentPath,
      hasChildren,
      isExpanded,
    });

    // Recursively add children if expanded
    if (isExpanded && hasChildren) {
      const childItems = getVisibleItems(node.children, expanded, node.fullPath);
      items.push(...childItems);
    }
  }

  return items;
}

/**
 * Counts total potential nodes in a tree (for comparison with rendered DOM nodes).
 * Used in development to validate lazy rendering effectiveness.
 */
function countTotalTreeNodes(tree: FolderTree): number {
  let count = 0;
  for (const node of Object.values(tree)) {
    count += 1; // This node
    count += countTotalTreeNodes(node.children); // Children recursively
  }
  return count;
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
  /** Currently focused folder path (for roving tabindex) */
  focusedPath: string | null;
  /** Set of expanded folder paths */
  expanded: Set<string>;
  /** Callback when a folder is selected */
  onSelectFolder: (path: string) => void;
  /** Callback to toggle folder expansion */
  onToggleExpand: (path: string) => void;
  /** Callback when a node receives focus */
  onFocus: (path: string) => void;
  /** Ref map for focusing elements programmatically */
  nodeRefs: React.MutableRefObject<Map<string, HTMLDivElement>>;
}

/**
 * Recursively renders a branch of the tree.
 *
 * LAZY RENDERING: Children are only rendered when isExpanded is true.
 * When a folder is collapsed, its children are removed from the DOM entirely.
 * This prevents DOM explosion for large trees with many nested folders.
 */
function TreeBranch({
  nodes,
  depth,
  selectedFolder,
  focusedPath,
  expanded,
  onSelectFolder,
  onToggleExpand,
  onFocus,
  nodeRefs,
}: TreeBranchProps) {
  // Sort folders alphabetically for consistent ordering
  const sortedNodes = useMemo(() => {
    return Object.values(nodes).sort((a, b) => a.name.localeCompare(b.name));
  }, [nodes]);

  if (sortedNodes.length === 0) {
    return null;
  }

  const siblingCount = sortedNodes.length;

  // Use semantic <ul>/<li> structure for proper ARIA tree pattern
  return (
    <ul role="group" className="list-none m-0 p-0">
      {sortedNodes.map((node, index) => {
        const isSelected = selectedFolder === node.fullPath;
        const isExpanded = expanded.has(node.fullPath);
        const hasChildren = Object.keys(node.children).length > 0;
        const isFocused = focusedPath === node.fullPath;

        return (
          <li key={node.fullPath} role="none">
            <TreeNode
              ref={(el) => {
                if (el) {
                  nodeRefs.current.set(node.fullPath, el);
                } else {
                  nodeRefs.current.delete(node.fullPath);
                }
              }}
              name={node.name}
              fullPath={node.fullPath}
              depth={depth}
              directCount={node.directCount}
              totalCount={node.totalArtifactCount}
              hasDirectArtifacts={node.hasDirectArtifacts}
              hasSubfolders={hasChildren}
              isSelected={isSelected}
              isExpanded={isExpanded}
              isFocused={isFocused}
              onSelect={() => onSelectFolder(node.fullPath)}
              onToggleExpand={() => onToggleExpand(node.fullPath)}
              onFocus={() => onFocus(node.fullPath)}
              siblingCount={siblingCount}
              positionInSet={index + 1}
            />

            {/*
             * LAZY RENDERING: Children only mount when expanded.
             * When collapsed (isExpanded = false), this entire subtree
             * is removed from the DOM, not just hidden with CSS.
             * This provides 60-80% DOM node reduction for large trees.
             */}
            {isExpanded && hasChildren && (
              <TreeBranch
                nodes={node.children}
                depth={depth + 1}
                selectedFolder={selectedFolder}
                focusedPath={focusedPath}
                expanded={expanded}
                onSelectFolder={onSelectFolder}
                onToggleExpand={onToggleExpand}
                onFocus={onFocus}
                nodeRefs={nodeRefs}
              />
            )}
          </li>
        );
      })}
    </ul>
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
 * Implements WAI-ARIA TreeView keyboard navigation pattern with roving tabindex.
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
  debugDomCount = false,
}: SemanticTreeProps) {
  // Apply semantic filtering to the tree
  const filteredTree = useMemo(() => {
    return filterSemanticTree(tree);
  }, [tree]);

  const hasContent = Object.keys(filteredTree).length > 0;

  // Track which node is currently focused (for roving tabindex)
  const [focusedPath, setFocusedPath] = useState<string | null>(null);

  // Map of path -> DOM element refs for programmatic focus
  const nodeRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Ref to the tree container for event handling
  const treeRef = useRef<HTMLElement>(null);

  // Get flat list of all visible items for navigation calculations
  const visibleItems = useMemo(
    () => getVisibleItems(filteredTree, expanded),
    [filteredTree, expanded]
  );

  // Initialize focused path to selected folder or first item
  useEffect(() => {
    if (focusedPath === null && visibleItems.length > 0) {
      // Prefer selected folder, otherwise use first item
      const initialPath = selectedFolder || visibleItems[0]?.path || null;
      setFocusedPath(initialPath);
    }
  }, [focusedPath, visibleItems, selectedFolder]);

  // Update focused path if it becomes invisible (parent collapsed)
  useEffect(() => {
    if (focusedPath && !visibleItems.find((item) => item.path === focusedPath)) {
      // Focused item is no longer visible, find nearest visible ancestor or first item
      const segments = focusedPath.split('/');
      for (let i = segments.length - 1; i >= 0; i--) {
        const parentPath = segments.slice(0, i).join('/');
        if (parentPath && visibleItems.find((item) => item.path === parentPath)) {
          setFocusedPath(parentPath);
          return;
        }
      }
      // No ancestor found, move to first item
      const firstItem = visibleItems[0];
      if (firstItem) {
        setFocusedPath(firstItem.path);
      }
    }
  }, [focusedPath, visibleItems]);

  // Development-only DOM node counting for performance validation
  useEffect(() => {
    if (!debugDomCount || process.env.NODE_ENV !== 'development') {
      return;
    }

    const totalPossibleNodes = countTotalTreeNodes(filteredTree);
    const renderedNodes =
      treeRef.current?.querySelectorAll('[role="treeitem"]').length ?? 0;
    const expandedCount = expanded.size;
    const reductionPercent =
      totalPossibleNodes > 0
        ? Math.round((1 - renderedNodes / totalPossibleNodes) * 100)
        : 0;

    console.log('[SemanticTree] DOM Stats:', {
      totalPossibleNodes,
      renderedNodes,
      expandedFolders: expandedCount,
      domReduction: `${reductionPercent}%`,
    });
  }, [filteredTree, expanded, debugDomCount]);

  // Focus the DOM element when focusedPath changes programmatically
  const focusNode = useCallback((path: string) => {
    // Use requestAnimationFrame to ensure DOM is updated
    requestAnimationFrame(() => {
      const el = nodeRefs.current.get(path);
      if (el) {
        el.focus();
      }
    });
  }, []);

  // Handle keyboard navigation at tree level
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (visibleItems.length === 0 || !focusedPath) return;

      const currentIndex = visibleItems.findIndex(
        (item) => item.path === focusedPath
      );
      const currentItem = visibleItems[currentIndex];

      if (currentIndex === -1) return;

      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault();
          // Move to next visible item
          const nextIndex = Math.min(currentIndex + 1, visibleItems.length - 1);
          const nextItem = visibleItems[nextIndex];
          if (nextIndex !== currentIndex && nextItem) {
            setFocusedPath(nextItem.path);
            focusNode(nextItem.path);
          }
          break;
        }

        case 'ArrowUp': {
          e.preventDefault();
          // Move to previous visible item
          const prevIndex = Math.max(currentIndex - 1, 0);
          const prevItem = visibleItems[prevIndex];
          if (prevIndex !== currentIndex && prevItem) {
            setFocusedPath(prevItem.path);
            focusNode(prevItem.path);
          }
          break;
        }

        case 'ArrowRight': {
          e.preventDefault();
          if (currentItem?.hasChildren) {
            if (!currentItem.isExpanded) {
              // Expand the folder
              onToggleExpand(focusedPath);
            } else {
              // Already expanded, move to first child
              const nextIndex = currentIndex + 1;
              const childItem = visibleItems[nextIndex];
              // Verify it's actually a child (its path starts with current path)
              if (childItem && childItem.path.startsWith(focusedPath + '/')) {
                setFocusedPath(childItem.path);
                focusNode(childItem.path);
              }
            }
          }
          break;
        }

        case 'ArrowLeft': {
          e.preventDefault();
          if (currentItem?.hasChildren && currentItem.isExpanded) {
            // Collapse the folder
            onToggleExpand(focusedPath);
          } else if (currentItem?.parentPath) {
            // Move to parent folder
            setFocusedPath(currentItem.parentPath);
            focusNode(currentItem.parentPath);
          }
          break;
        }

        case 'Home': {
          e.preventDefault();
          // Move to first item
          const firstItem = visibleItems[0];
          if (firstItem) {
            setFocusedPath(firstItem.path);
            focusNode(firstItem.path);
          }
          break;
        }

        case 'End': {
          e.preventDefault();
          // Move to last visible item
          const lastItem = visibleItems[visibleItems.length - 1];
          if (lastItem) {
            setFocusedPath(lastItem.path);
            focusNode(lastItem.path);
          }
          break;
        }

        case 'Enter':
        case ' ': {
          e.preventDefault();
          // Select the focused folder
          onSelectFolder(focusedPath);
          break;
        }
      }
    },
    [visibleItems, focusedPath, onToggleExpand, onSelectFolder, focusNode]
  );

  // Handle when a node receives native focus (e.g., via click or tab)
  const handleNodeFocus = useCallback((path: string) => {
    setFocusedPath(path);
  }, []);

  return (
    <nav
      ref={treeRef}
      role="tree"
      aria-label="Folder navigation"
      className={cn('overflow-y-auto', className)}
      onKeyDown={handleKeyDown}
    >
      {hasContent ? (
        <TreeBranch
          nodes={filteredTree}
          depth={0}
          selectedFolder={selectedFolder}
          focusedPath={focusedPath}
          expanded={expanded}
          onSelectFolder={onSelectFolder}
          onToggleExpand={onToggleExpand}
          onFocus={handleNodeFocus}
          nodeRefs={nodeRefs}
        />
      ) : (
        <p className="py-4 text-center text-sm text-muted-foreground">
          No folders to display
        </p>
      )}
    </nav>
  );
}
