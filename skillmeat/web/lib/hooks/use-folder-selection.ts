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

import { useState, useCallback, useMemo, useEffect } from 'react';
import type { FolderTree } from '@/lib/tree-builder';

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
 * Manage folder selection and expansion state for folder tree views.
 *
 * @param tree - The folder tree structure built from catalog entries
 * @returns Folder selection state and controls
 */
export function useFolderSelection(tree: FolderTree): UseFolderSelectionReturn {
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  /**
   * Get all folder paths from the tree (for expandAll)
   */
  const allFolderPaths = useMemo(() => {
    const paths: string[] = [];

    function collectPaths(node: Record<string, any>, parentPath: string = ''): void {
      for (const [key, folderNode] of Object.entries(node)) {
        if (folderNode && typeof folderNode === 'object' && 'fullPath' in folderNode) {
          paths.push(folderNode.fullPath);

          // Recursively collect from children
          if (folderNode.children && typeof folderNode.children === 'object') {
            collectPaths(folderNode.children, folderNode.fullPath);
          }
        }
      }
    }

    collectPaths(tree);
    return paths;
  }, [tree]);

  /**
   * Auto-select first semantic folder when tree loads
   */
  useEffect(() => {
    // Only auto-select if no selection exists and tree has content
    if (selectedFolder === null && Object.keys(tree).length > 0) {
      // Get first top-level folder
      const firstFolderKey = Object.keys(tree)[0];
      if (firstFolderKey && tree[firstFolderKey]) {
        const firstFolder = tree[firstFolderKey];
        setSelectedFolder(firstFolder.fullPath);

        // Auto-expand the first folder if it has children
        if (firstFolder.hasSubfolders) {
          setExpanded(new Set([firstFolder.fullPath]));
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
