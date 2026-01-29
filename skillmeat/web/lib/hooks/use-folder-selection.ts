/**
 * Folder selection and expansion state management hook
 *
 * Manages the folder view state including selected folder and expanded folders.
 * Used by SourceFolderLayout and SemanticTree components for marketplace navigation.
 *
 * @example
 * ```tsx
 * const tree = buildFolderTree(catalogEntries, 0);
 * const {
 *   selectedFolder,
 *   setSelectedFolder,
 *   expanded,
 *   toggleExpand,
 *   expandPath,
 * } = useFolderSelection(tree);
 *
 * // Auto-expands ancestors when selecting a folder
 * const handleSelect = (path: string) => {
 *   expandPath(path);
 *   setSelectedFolder(path);
 * };
 * ```
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import type { FolderTree, FolderNode } from '@/lib/tree-builder';

export interface UseFolderSelectionReturn {
  /**
   * Currently selected folder path (e.g., "plugins/dev-tools")
   */
  selectedFolder: string | null;

  /**
   * Update the selected folder
   */
  setSelectedFolder: (path: string | null) => void;

  /**
   * Set of expanded folder paths
   */
  expanded: Set<string>;

  /**
   * Toggle expansion state for a folder
   */
  toggleExpand: (path: string) => void;

  /**
   * Expand all ancestor folders for a given path
   * Useful for auto-expanding when selecting a folder
   */
  expandPath: (path: string) => void;

  /**
   * Collapse all folders
   */
  collapseAll: () => void;

  /**
   * Expand all folders in the tree
   */
  expandAll: () => void;
}

/**
 * Find the first semantic folder in a tree (depth-first, alphabetically sorted)
 *
 * @param tree - The filtered semantic folder tree
 * @returns First folder node found, or null if tree is empty
 */
function findFirstSemanticFolder(tree: FolderTree): FolderNode | null {
  // Get all top-level folders and sort alphabetically
  const topLevelFolders = Object.values(tree).sort((a, b) => a.name.localeCompare(b.name));

  if (topLevelFolders.length === 0) {
    return null;
  }

  // Return the first folder (alphabetically), handle undefined case
  return topLevelFolders[0] ?? null;
}

/**
 * Manage folder selection and expansion state for folder tree views.
 *
 * @param tree - The folder tree structure built from catalog entries
 * @returns Folder selection state and controls
 */
export function useFolderSelection(tree: FolderTree): UseFolderSelectionReturn {
  const [selectedFolder, setSelectedFolderInternal] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // Track if user has manually interacted to avoid overriding their choice
  const hasUserInteracted = useRef(false);

  /**
   * Wrapped setter that tracks user interaction
   */
  const setSelectedFolder = useCallback((path: string | null) => {
    hasUserInteracted.current = true;
    setSelectedFolderInternal(path);
  }, []);

  /**
   * Get all folder paths from the tree (for expandAll)
   */
  const allFolderPaths = useMemo(() => {
    const paths: string[] = [];

    function collectPaths(node: Record<string, any>): void {
      for (const folderNode of Object.values(node)) {
        if (folderNode && typeof folderNode === 'object' && 'fullPath' in folderNode) {
          paths.push(folderNode.fullPath);

          // Recursively collect from children
          if (folderNode.children && typeof folderNode.children === 'object') {
            collectPaths(folderNode.children);
          }
        }
      }
    }

    collectPaths(tree);
    return paths;
  }, [tree]);

  /**
   * Auto-select first semantic folder when tree loads.
   * Only runs if user hasn't manually interacted with the selection.
   */
  useEffect(() => {
    // Only auto-select if:
    // 1. User hasn't manually interacted
    // 2. No current selection
    // 3. Tree has content
    if (!hasUserInteracted.current && selectedFolder === null && Object.keys(tree).length > 0) {
      const firstFolder = findFirstSemanticFolder(tree);

      if (firstFolder) {
        // Set selection without triggering user interaction flag
        setSelectedFolderInternal(firstFolder.fullPath);

        // Auto-expand path to first folder
        const segments = firstFolder.fullPath.split('/').filter(Boolean);
        const pathsToExpand: string[] = [];
        let currentPath = '';

        for (const segment of segments) {
          currentPath = currentPath ? `${currentPath}/${segment}` : segment;
          pathsToExpand.push(currentPath);
        }

        if (pathsToExpand.length > 0) {
          setExpanded(new Set(pathsToExpand));
        }
      }
    }
  }, [tree, selectedFolder]);

  /**
   * Toggle expansion state for a folder
   */
  const toggleExpand = useCallback((path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  /**
   * Expand all ancestor folders for a given path
   * Example: "plugins/dev-tools/formatter" expands ["plugins", "plugins/dev-tools"]
   */
  const expandPath = useCallback((path: string) => {
    if (!path) return;

    setExpanded((prev) => {
      const next = new Set(prev);
      const segments = path.split('/').filter(Boolean);

      // Build all ancestor paths
      let currentPath = '';
      for (const segment of segments) {
        currentPath = currentPath ? `${currentPath}/${segment}` : segment;
        next.add(currentPath);
      }

      return next;
    });
  }, []);

  /**
   * Collapse all folders
   */
  const collapseAll = useCallback(() => {
    setExpanded(new Set());
  }, []);

  /**
   * Expand all folders in the tree
   */
  const expandAll = useCallback(() => {
    setExpanded(new Set(allFolderPaths));
  }, [allFolderPaths]);

  return {
    selectedFolder,
    setSelectedFolder,
    expanded,
    toggleExpand,
    expandPath,
    collapseAll,
    expandAll,
  };
}
