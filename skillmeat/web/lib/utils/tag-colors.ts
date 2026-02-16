/**
 * Tag Color Utilities
 *
 * Provides deterministic color generation for tags based on their names.
 * Uses a hash function to consistently assign colors from a predefined palette.
 * This ensures the same tag always gets the same color across the app.
 */

/**
 * Predefined tag color palette.
 * A vibrant selection of colors that work well in both light and dark modes.
 */
export const TAG_COLORS = [
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#d946ef', // Fuchsia
  '#ec4899', // Pink
  '#f43f5e', // Rose
  '#ef4444', // Red
  '#f97316', // Orange
  '#eab308', // Yellow
  '#84cc16', // Lime
  '#22c55e', // Green
  '#14b8a6', // Teal
  '#06b6d4', // Cyan
  '#0ea5e9', // Sky
  '#3b82f6', // Blue
] as const;

/**
 * Hashes a string to produce a consistent integer.
 * Used to deterministically select a color for a tag name.
 *
 * @param str - The string to hash
 * @returns A positive integer hash value
 */
export function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

/**
 * Gets a deterministic color for a tag based on its name.
 * The same tag name will always return the same color.
 *
 * @param tag - The tag name
 * @returns A hex color string from the TAG_COLORS palette
 *
 * @example
 * ```ts
 * getTagColor('react')
 * // Returns: '#6366f1' (always the same for 'react')
 *
 * getTagColor('typescript')
 * // Returns: '#ec4899' (always the same for 'typescript')
 * ```
 */
export function getTagColor(tag: string): string {
  const hash = hashString(tag.toLowerCase());
  return TAG_COLORS[hash % TAG_COLORS.length] ?? '#6366f1';
}
