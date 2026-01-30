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
import type { CatalogEntry } from '@/types/marketplace';
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
 * Check if a folder is a root exclusion (only applies at depth 1)
 */
function isRootExclusion(
  folderPath: string,
  depth: number,
  config?: SemanticFilterConfig
): boolean {
  const rootExclusions = config?.rootExclusions ?? DEFAULT_ROOT_EXCLUSIONS;
  const folderName = folderPath.split('/').pop() || '';
  return depth === 1 && rootExclusions.includes(folderName);
}

/**
 * Check if a folder is a leaf container (applies at any depth)
 */
function isLeafContainer(
  folderPath: string,
  config?: SemanticFilterConfig
): boolean {
  const leafContainers = config?.leafContainers ?? DEFAULT_LEAF_CONTAINERS;
  const folderName = folderPath.split('/').pop() || '';
  return leafContainers.includes(folderName);
}

/**
 * Result from filtering that includes promoted content
 */
interface FilterResult {
  /** Filtered tree at this level */
  tree: FolderTree;
  /** Artifacts promoted from filtered-out leaf containers */
  promotedArtifacts: CatalogEntry[];
  /** Count of artifacts promoted from leaf containers */
  promotedCount: number;
}

/**
 * Recursively filters a folder tree to only include semantic navigation folders.
 *
 * When leaf containers (skills, commands, etc.) are filtered out, their contents
 * are "promoted" to the parent level:
 * - Artifacts from leaf containers become accessible via the parent folder
 * - Non-leaf subfolders inside leaf containers are promoted as direct children
 *
 * Root exclusions (src, lib, etc.) at depth 1 are completely skipped - nothing
 * inside them is promoted.
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
 *
 * @example
 * // Promotion behavior:
 * // Input:  plugins/skills/dev/my-skill (skills is leaf container)
 * // Output: plugins/dev/my-skill (dev promoted from skills/dev)
 */
export function filterSemanticTree(
  tree: FolderTree,
  depth: number = 1,
  config?: SemanticFilterConfig
): FolderTree {
  const result = filterSemanticTreeInternal(tree, depth, config);
  return result.tree;
}

/**
 * Internal implementation that tracks promoted content through recursion
 */
function filterSemanticTreeInternal(
  tree: FolderTree,
  depth: number,
  config?: SemanticFilterConfig
): FilterResult {
  const filtered: FolderTree = {};
  let allPromotedArtifacts: CatalogEntry[] = [];
  let allPromotedCount = 0;

  for (const [path, node] of Object.entries(tree)) {
    // Root exclusions at depth 1 are completely skipped - nothing promoted
    if (isRootExclusion(path, depth, config)) {
      continue;
    }

    // Leaf containers: filter out the container itself but promote its contents
    if (isLeafContainer(path, config)) {
      // Recursively filter the leaf container's children to get promotable content
      const childResult = filterSemanticTreeInternal(node.children, depth + 1, config);

      // Promote semantic children from this leaf container to parent level
      for (const [childPath, childNode] of Object.entries(childResult.tree)) {
        filtered[childPath] = childNode;
      }

      // Accumulate artifacts from this leaf container for parent to access
      // Include both direct artifacts and any promoted from deeper levels
      allPromotedArtifacts = [
        ...allPromotedArtifacts,
        ...node.directArtifacts,
        ...childResult.promotedArtifacts,
      ];
      allPromotedCount += node.directCount + childResult.promotedCount;

      continue;
    }

    // Semantic folder: include it with recursively filtered children
    const childResult = filterSemanticTreeInternal(node.children, depth + 1, config);

    // Merge promoted children into this node's children
    const mergedChildren = { ...childResult.tree };

    // Create the filtered node
    const filteredNode: FolderNode = {
      ...node,
      children: mergedChildren,
      hasSubfolders: Object.keys(mergedChildren).length > 0,
      // Note: directArtifacts stays as-is; promoted artifacts are handled
      // at the folder-detail-pane level via getDisplayArtifactsForFolder
    };

    // Include node if it has children, direct artifacts, or artifacts in subtree
    // (including promoted artifacts from leaf containers)
    const hasChildren = Object.keys(filteredNode.children).length > 0;
    const hasArtifactsInSubtree = node.totalArtifactCount > 0;
    const hasPromotedArtifacts = childResult.promotedCount > 0;

    if (hasChildren || hasArtifactsInSubtree || hasPromotedArtifacts) {
      filtered[path] = filteredNode;
    }
  }

  return {
    tree: filtered,
    promotedArtifacts: allPromotedArtifacts,
    promotedCount: allPromotedCount,
  };
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
