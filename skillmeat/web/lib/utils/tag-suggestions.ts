/**
 * Tag suggestion utilities for directory-based tagging
 *
 * Generates tag suggestions from directory paths by splitting
 * path segments and filtering out common/meaningless words.
 */

/**
 * Common directory/path words to filter out from suggestions.
 * These words are too generic to be useful as tags.
 */
const EXCLUDED_WORDS = new Set([
  // Common source code directories
  'src',
  'lib',
  'dist',
  'build',
  'out',
  'bin',
  'node_modules',
  'vendor',
  'public',
  'static',
  'assets',
  'resources',
  // Common project structure
  'app',
  'apps',
  'packages',
  'modules',
  'components',
  'utils',
  'helpers',
  'common',
  'shared',
  'core',
  'internal',
  'external',
  // Version/environment indicators
  'v1',
  'v2',
  'v3',
  'dev',
  'prod',
  'test',
  'tests',
  'testing',
  'staging',
  // Other common names
  'config',
  'configs',
  'scripts',
  'docs',
  'documentation',
  'examples',
  'samples',
  'demo',
  'demos',
]);

/**
 * Minimum length for a path segment to be considered a valid tag suggestion.
 */
const MIN_TAG_LENGTH = 2;

/**
 * Generate tag suggestions from a directory path.
 *
 * Splits the path into segments, filters out common/meaningless words,
 * and returns unique, normalized tag suggestions.
 *
 * @param path - Directory path (e.g., "skills/canvas-design/v2")
 * @returns Array of suggested tags
 *
 * @example
 * ```ts
 * generateTagSuggestions("skills/canvas-design")
 * // Returns: ["skills", "canvas-design"]
 *
 * generateTagSuggestions("src/components/ui/button")
 * // Returns: ["ui", "button"] (filters out "src", "components")
 *
 * generateTagSuggestions("packages/ai-tools/prompts")
 * // Returns: ["ai-tools", "prompts"] (filters out "packages")
 * ```
 */
export function generateTagSuggestions(path: string): string[] {
  if (!path || typeof path !== 'string') {
    return [];
  }

  // Split path into segments
  const segments = path
    .split('/')
    .filter(Boolean)
    .map((segment) => segment.toLowerCase().trim())
    .filter((segment) => segment.length >= MIN_TAG_LENGTH);

  // Filter out excluded words and deduplicate
  const suggestions = new Set<string>();

  for (const segment of segments) {
    // Skip excluded words
    if (EXCLUDED_WORDS.has(segment)) {
      continue;
    }

    // Skip pure numbers
    if (/^\d+$/.test(segment)) {
      continue;
    }

    suggestions.add(segment);
  }

  return Array.from(suggestions);
}

/**
 * Check if a string is a valid tag.
 *
 * @param tag - Tag string to validate
 * @returns True if the tag is valid
 */
export function isValidTag(tag: string): boolean {
  if (!tag || typeof tag !== 'string') {
    return false;
  }

  const trimmed = tag.trim().toLowerCase();

  // Must meet minimum length
  if (trimmed.length < MIN_TAG_LENGTH) {
    return false;
  }

  // Cannot be only whitespace
  if (!trimmed) {
    return false;
  }

  return true;
}

/**
 * Normalize a tag string for consistent storage.
 *
 * @param tag - Raw tag string
 * @returns Normalized tag (lowercase, trimmed)
 */
export function normalizeTag(tag: string): string {
  return tag.trim().toLowerCase();
}

/**
 * Normalize a tag string for storage with stricter formatting.
 *
 * - Converts to lowercase
 * - Replaces spaces with underscores
 * - Trims whitespace
 * - Removes special characters except underscores and hyphens
 *
 * @param tag - Raw tag string
 * @returns Normalized tag ready for storage
 *
 * @example
 * ```ts
 * normalizeTagForStorage("  My Tag  ")
 * // Returns: "my_tag"
 *
 * normalizeTagForStorage("React.js & TypeScript")
 * // Returns: "reactjs_typescript"
 *
 * normalizeTagForStorage("AI-Powered Tools")
 * // Returns: "ai-powered_tools"
 * ```
 */
export function normalizeTagForStorage(tag: string): string {
  return tag
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_') // Replace spaces with underscores
    .replace(/[^a-z0-9_-]/g, ''); // Remove special chars except _ and -
}
