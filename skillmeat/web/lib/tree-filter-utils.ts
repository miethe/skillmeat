/**
 * Semantic filtering utilities for folder tree navigation
 *
 * Filters folder trees to show only "semantic" navigation folders,
 * excluding both root-level containers and leaf artifact containers.
 *
 * These are pure functions that work in SSR context. Use with
 * useDetectionPatterns() hook at the component level for dynamic config.
 */

import type { FolderTree, FolderNode } from './tree-builder';
import {
  DEFAULT_LEAF_CONTAINERS,
  DEFAULT_ROOT_EXCLUSIONS,
} from '@/hooks/use-detection-patterns';

/**
 * Configuration for semantic folder filtering
 *
 * Allows overriding default filtering behavior with custom patterns.
 * Typically populated from useDetectionPatterns() hook at the component level.
 */
export interface SemanticFilterConfig {
  /** Leaf container folders to exclude (any depth) - artifact type containers */
  leafContainers?: string[];
  /** Root-level folders to exclude (depth 1) - too high-level for navigation */
  rootExclusions?: string[];
}

/**
 * Determines if a folder should be included in semantic navigation
 *
 * @param folderPath - Full path of the folder
 * @param depth - Depth in the tree (1 = root level)
 * @param config - Optional filter configuration (defaults to centralized patterns)
 * @returns true if folder should be included in navigation
 *
 * @example
 * // Using defaults
 * isSemanticFolder('plugins', 1) // false - root exclusion
 * isSemanticFolder('anthropics/tools/commands', 3) // false - leaf container
 * isSemanticFolder('anthropics/tools', 2) // true - intermediate folder
 *
 * @example
 * // Using custom config from hook
 * const { leafContainers } = useDetectionPatterns();
 * isSemanticFolder('mypath', 2, { leafContainers });
 */
export function isSemanticFolder(
  folderPath: string,
  depth: number,
  config?: SemanticFilterConfig
): boolean {
  const leafContainers = config?.leafContainers ?? DEFAULT_LEAF_CONTAINERS;
  const rootExclusions = config?.rootExclusions ?? DEFAULT_ROOT_EXCLUSIONS;

  // Extract folder name from path
  const folderName = folderPath.split('/').pop() || '';

  // Exclude root-level folders from exclusion list
  if (depth === 1 && rootExclusions.includes(folderName)) {
    return false;
  }

  // Exclude leaf container folders at any depth
  if (leafContainers.includes(folderName)) {
    return false;
  }

  return true;
}

/**
 * Recursively filters a folder tree to only include semantic navigation folders
 *
 * @param tree - The folder tree to filter
 * @param depth - Current depth in the tree (internal, starts at 1)
 * @param config - Optional filter configuration (defaults to centralized patterns)
 * @returns Filtered tree with only semantic folders
 *
 * @example
 * // Using defaults
 * const filtered = filterSemanticTree(fullTree);
 *
 * @example
 * // Using custom config from hook
 * const { leafContainers } = useDetectionPatterns();
 * const filtered = filterSemanticTree(fullTree, 1, { leafContainers });
 */
export function filterSemanticTree(
  tree: FolderTree,
  depth: number = 1,
  config?: SemanticFilterConfig
): FolderTree {
  const filtered: FolderTree = {};

  for (const [path, node] of Object.entries(tree)) {
    // Check if this folder should be included
    if (!isSemanticFolder(path, depth, config)) {
      continue;
    }

    // Create filtered node with recursively filtered children
    const filteredChildren = filterSemanticTree(node.children, depth + 1, config);
    const filteredNode: FolderNode = {
      ...node,
      children: filteredChildren,
      hasSubfolders: Object.keys(filteredChildren).length > 0,
    };

    // Only include node if it has children or any artifacts in its subtree
    // Use totalArtifactCount (not directArtifacts) to include artifacts in leaf containers
    // e.g., skills/commands/my-cmd - "skills" has artifacts via "commands" even if commands is filtered
    const hasChildren = Object.keys(filteredNode.children).length > 0;
    const hasArtifactsInSubtree = node.totalArtifactCount > 0;

    if (hasChildren || hasArtifactsInSubtree) {
      filtered[path] = filteredNode;
    }
  }

  return filtered;
}

/**
 * Counts total semantic folders in a tree
 *
 * @param tree - The folder tree to count
 * @returns Number of semantic folders
 */
export function countSemanticFolders(tree: FolderTree): number {
  let count = 0;

  for (const node of Object.values(tree)) {
    count++;
    if (node.children) {
      count += countSemanticFolders(node.children);
    }
  }

  return count;
}

/**
 * Gets all semantic folder paths from a tree (flattened)
 *
 * @param tree - The folder tree to flatten
 * @param prefix - Path prefix for nested folders (internal)
 * @returns Array of all semantic folder paths
 *
 * @example
 * const paths = getSemanticFolderPaths(tree);
 * // ['anthropics', 'anthropics/tools', 'user/utilities']
 */
export function getSemanticFolderPaths(tree: FolderTree, prefix: string = ''): string[] {
  const paths: string[] = [];

  for (const [path, node] of Object.entries(tree)) {
    const fullPath = prefix ? `${prefix}/${path}` : path;
    paths.push(fullPath);

    if (node.children) {
      paths.push(...getSemanticFolderPaths(node.children, fullPath));
    }
  }

  return paths;
}
