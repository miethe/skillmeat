/**
 * Semantic filtering utilities for folder tree navigation
 *
 * Filters folder trees to show only "semantic" navigation folders,
 * excluding both root-level containers and leaf artifact containers.
 */

import type { FolderTree, FolderNode } from './tree-builder';

/**
 * Root-level folders to exclude (depth 1)
 * These are too high-level to be useful for navigation
 */
// Note: 'skills' intentionally excluded - it's a meaningful folder that should be shown
const ROOT_EXCLUSIONS = ['plugins', 'src', 'lib', 'packages', 'apps', 'examples'];

/**
 * Leaf container folders to exclude (any depth)
 * These are artifact type containers that don't aid navigation
 */
const LEAF_CONTAINERS = ['commands', 'agents', 'mcp_servers', 'hooks', 'mcp-servers'];

/**
 * Determines if a folder should be included in semantic navigation
 *
 * @param folderPath - Full path of the folder
 * @param depth - Depth in the tree (1 = root level)
 * @returns true if folder should be included in navigation
 *
 * @example
 * isSemanticFolder('plugins', 1) // false - root exclusion
 * isSemanticFolder('anthropics/tools/commands', 3) // false - leaf container
 * isSemanticFolder('anthropics/tools', 2) // true - intermediate folder
 */
export function isSemanticFolder(folderPath: string, depth: number): boolean {
  // Extract folder name from path
  const folderName = folderPath.split('/').pop() || '';

  // Exclude root-level folders from exclusion list
  if (depth === 1 && ROOT_EXCLUSIONS.includes(folderName)) {
    return false;
  }

  // Exclude leaf container folders at any depth
  if (LEAF_CONTAINERS.includes(folderName)) {
    return false;
  }

  return true;
}

/**
 * Recursively filters a folder tree to only include semantic navigation folders
 *
 * @param tree - The folder tree to filter
 * @param depth - Current depth in the tree (internal, starts at 1)
 * @returns Filtered tree with only semantic folders
 *
 * @example
 * const filtered = filterSemanticTree(fullTree);
 * // Result: Tree without root containers or leaf artifact folders
 */
export function filterSemanticTree(tree: FolderTree, depth: number = 1): FolderTree {
  const filtered: FolderTree = {};

  for (const [path, node] of Object.entries(tree)) {
    // Check if this folder should be included
    if (!isSemanticFolder(path, depth)) {
      continue;
    }

    // Create filtered node with recursively filtered children
    const filteredChildren = filterSemanticTree(node.children, depth + 1);
    const filteredNode: FolderNode = {
      ...node,
      children: filteredChildren,
      hasSubfolders: Object.keys(filteredChildren).length > 0,
    };

    // Only include node if it has children or direct artifacts
    // This prevents including empty intermediate folders
    const hasChildren = Object.keys(filteredNode.children).length > 0;
    const hasArtifacts = filteredNode.directArtifacts && filteredNode.directArtifacts.length > 0;

    if (hasChildren || hasArtifacts) {
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
