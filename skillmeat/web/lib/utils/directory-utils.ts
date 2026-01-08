/**
 * Directory utility functions for marketplace catalog operations.
 *
 * Provides functions for extracting and manipulating directory paths
 * from catalog entry artifact paths.
 */

/**
 * Get parent directory from artifact path.
 *
 * @param path - Artifact path (e.g., "skills/canvas-design")
 * @returns Parent directory path, or empty string for root-level artifacts
 *
 * @example
 * getParentDirectory("skills/canvas-design") // "skills"
 * getParentDirectory("commands/ai/prompt-generator") // "commands/ai"
 * getParentDirectory("canvas") // ""
 * getParentDirectory("skills/") // "skills"
 */
export function getParentDirectory(path: string): string {
  if (!path) {
    return '';
  }

  // Remove trailing slash if present
  const normalizedPath = path.endsWith('/') ? path.slice(0, -1) : path;

  // Find the last slash
  const lastSlashIndex = normalizedPath.lastIndexOf('/');

  // No slash means root-level artifact
  if (lastSlashIndex === -1) {
    return '';
  }

  // Return everything before the last slash
  return normalizedPath.slice(0, lastSlashIndex);
}

/**
 * Extract full directory path from artifact path (including the artifact's directory).
 *
 * Unlike getParentDirectory which returns the parent, this returns the full
 * directory path where the artifact resides.
 *
 * @param path - Artifact path (e.g., "skills/canvas-design")
 * @returns Full directory path, or empty string for single-segment paths
 *
 * @example
 * extractDirectoryPath("skills/canvas-design") // "skills/canvas-design"
 * extractDirectoryPath("commands/ai/prompt-generator") // "commands/ai/prompt-generator"
 * extractDirectoryPath("canvas") // ""
 * extractDirectoryPath("skills/") // "skills"
 */
export function extractDirectoryPath(path: string): string {
  if (!path) {
    return '';
  }

  // Remove trailing slash if present
  const normalizedPath = path.endsWith('/') ? path.slice(0, -1) : path;

  // Single segment paths (no directory structure)
  if (!normalizedPath.includes('/')) {
    return '';
  }

  return normalizedPath;
}

/**
 * Extract unique directory paths from catalog entries.
 *
 * Parses the path field from each entry and extracts the full directory
 * path where each artifact resides. Returns a deduplicated, sorted list.
 *
 * @param entries - Array of objects with 'path' field
 * @returns Sorted array of unique directory paths (excludes empty strings for root-level)
 *
 * @example
 * extractDirectories([
 *   { path: "skills/canvas-design" },
 *   { path: "skills/document-skills" },
 *   { path: "commands/ai/prompt-generator" },
 *   { path: "canvas" },  // root-level, excluded
 * ])
 * // Returns: ["commands/ai/prompt-generator", "skills/canvas-design", "skills/document-skills"]
 */
export function extractDirectories(entries: Array<{ path: string }>): string[] {
  if (!entries || entries.length === 0) {
    return [];
  }

  const directories = new Set<string>();

  for (const entry of entries) {
    const directory = extractDirectoryPath(entry.path);
    // Only add non-empty directories (skip root-level artifacts)
    if (directory) {
      directories.add(directory);
    }
  }

  // Convert to array and sort alphabetically
  return Array.from(directories).sort((a, b) => a.localeCompare(b));
}

/**
 * Extract unique parent directories from catalog entries.
 *
 * Similar to extractDirectories but returns parent directories instead
 * of full paths. Useful for grouping by top-level category.
 *
 * @param entries - Array of objects with 'path' field
 * @returns Sorted array of unique parent directory paths
 *
 * @example
 * extractParentDirectories([
 *   { path: "skills/canvas-design" },
 *   { path: "skills/document-skills" },
 *   { path: "commands/ai/prompt-generator" },
 * ])
 * // Returns: ["commands/ai", "skills"]
 */
export function extractParentDirectories(
  entries: Array<{ path: string }>
): string[] {
  if (!entries || entries.length === 0) {
    return [];
  }

  const directories = new Set<string>();

  for (const entry of entries) {
    const directory = getParentDirectory(entry.path);
    // Only add non-empty directories (skip root-level artifacts)
    if (directory) {
      directories.add(directory);
    }
  }

  // Convert to array and sort alphabetically
  return Array.from(directories).sort((a, b) => a.localeCompare(b));
}

/**
 * Group entries by their parent directory.
 *
 * @param entries - Array of objects with 'path' field
 * @returns Map of parent directory to entries in that directory
 *
 * @example
 * groupByDirectory([
 *   { path: "skills/canvas", name: "Canvas" },
 *   { path: "skills/docs", name: "Docs" },
 *   { path: "commands/ai", name: "AI" },
 * ])
 * // Returns Map:
 * // "skills" -> [{ path: "skills/canvas", name: "Canvas" }, { path: "skills/docs", name: "Docs" }]
 * // "commands" -> [{ path: "commands/ai", name: "AI" }]
 * // "" -> [] (root-level entries)
 */
export function groupByDirectory<T extends { path: string }>(
  entries: T[]
): Map<string, T[]> {
  const groups = new Map<string, T[]>();

  for (const entry of entries) {
    const directory = getParentDirectory(entry.path);
    const existing = groups.get(directory) || [];
    existing.push(entry);
    groups.set(directory, existing);
  }

  return groups;
}
