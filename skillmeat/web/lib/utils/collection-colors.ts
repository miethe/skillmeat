/**
 * Collection Color Utilities
 *
 * Provides deterministic color assignment for collection names.
 * Uses a hash-based approach to ensure consistent colors across renders.
 *
 * Extracted pattern from tag-badge.tsx for reuse across the application.
 */

// ============================================================================
// Constants
// ============================================================================

/**
 * Predefined color palette for collections.
 * Selected for WCAG AA contrast compliance with both light and dark text.
 *
 * Colors are intentionally vibrant to provide clear visual distinction
 * between different collections in the UI.
 */
export const COLLECTION_COLORS = [
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

// ============================================================================
// Hash Function
// ============================================================================

/**
 * Generate a deterministic hash from a string.
 *
 * Uses a simple hash algorithm to convert strings into consistent numeric values.
 * This ensures that the same collection name always maps to the same color.
 *
 * Algorithm: FNV-1a variant (bitwise operations for speed)
 *
 * @param str - The string to hash (typically a collection name)
 * @returns A positive integer hash value
 *
 * @example
 * ```typescript
 * hashString('my-collection'); // => 1234567890 (always same for 'my-collection')
 * hashString('other-collection'); // => 9876543210 (different hash)
 * ```
 */
export function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash);
}

// ============================================================================
// Color Assignment
// ============================================================================

/**
 * Get a consistent color for a collection based on its name.
 *
 * Uses deterministic hashing to map collection names to colors from the palette.
 * The same collection name will always return the same color across renders and sessions.
 *
 * @param collectionName - The name of the collection
 * @returns A hex color string from the COLLECTION_COLORS palette
 *
 * @example
 * ```typescript
 * getCollectionColor('my-skills');        // => '#6366f1' (always indigo)
 * getCollectionColor('My-Skills');        // => '#6366f1' (case-insensitive)
 * getCollectionColor('other-collection'); // => '#8b5cf6' (different color)
 * ```
 */
export function getCollectionColor(collectionName: string): string {
  const hash = hashString(collectionName.toLowerCase());
  const index = hash % COLLECTION_COLORS.length;
  return COLLECTION_COLORS[index] ?? COLLECTION_COLORS[0];
}
