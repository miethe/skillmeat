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
 *   navigateToFolder,
 * } = useFolderSelection(tree);
 *
 * // Auto-expands ancestors when selecting a folder
 * const handleSelect = (path: string) => {
 *   expandPath(path);
 *   setSelectedFolder(path);
 * };
 *
 * // Navigate to folder (expands ancestors + selects in one operation)
 * const handleNavigate = (path: string) => {
 *   navigateToFolder(path);
 * };
 * ```
 */

import { useState, useCallback, useMemo, useRef } from 'react';
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

  /**
   * Navigate to a folder by path, expanding all parent folders and selecting it.
   * This is a combined operation that expands the tree path and selects the folder
   * in a single smooth state update.
   *
   * @param path - Full path of the folder to navigate to (e.g., "plugins/dev-tools/linter")
   *
   * @example
   * ```tsx
   * // Navigate to subfolder when clicked
   * <SubfolderCard
   *   folder={subfolder}
   *   onSelect={(path) => navigateToFolder(path)}
   * />
   * ```
   */
  navigateToFolder: (path: string) => void;
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

  // NOTE: Auto-selection of first folder was removed to show "Source Root" by default.
  // This allows users to see root-level artifacts when entering folder view.
  // Users can click a folder to navigate into it, or click "Source Root" to return.

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

  /**
   * Navigate to a folder by path, expanding all parent folders and selecting it.
   *
   * This performs a combined operation in a single smooth state update:
   * 1. Parse the path to get all parent folder paths
   * 2. Add all parent paths to the expanded set
   * 3. Set the selected folder to the target path
   *
   * Example: navigating to "plugins/dev-tools/linter"
   * - Expands: ["plugins", "plugins/dev-tools", "plugins/dev-tools/linter"]
   * - Selects: "plugins/dev-tools/linter"
   */
  const navigateToFolder = useCallback((path: string) => {
    if (!path) return;

    // Mark user interaction
    hasUserInteracted.current = true;

    // Build all ancestor paths (including target)
    const segments = path.split('/').filter(Boolean);
    const pathsToExpand: string[] = [];
    let currentPath = '';

    for (const segment of segments) {
      currentPath = currentPath ? `${currentPath}/${segment}` : segment;
      pathsToExpand.push(currentPath);
    }

    // Update both expanded and selected in separate state updates
    // (React will batch these automatically)
    setExpanded((prev) => {
      const next = new Set(prev);
      for (const pathToExpand of pathsToExpand) {
        next.add(pathToExpand);
      }
      return next;
    });

    setSelectedFolderInternal(path);
  }, []);

  return {
    selectedFolder,
    setSelectedFolder,
    expanded,
    toggleExpand,
    expandPath,
    collapseAll,
    expandAll,
    navigateToFolder,
  };
}
