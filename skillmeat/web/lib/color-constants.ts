/**
 * Shared color constants and helpers for site-wide color management.
 *
 * These presets are extracted from the group color picker in lib/group-constants.ts.
 * Consumers that previously relied on group-constants.ts can re-import ColorOption,
 * PRESET_COLORS, and isValidHex from there — backward-compat re-exports are provided.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ColorOption {
  hex: string;
  name?: string;
  isCustom?: boolean;
}

// ---------------------------------------------------------------------------
// Preset colors
// ---------------------------------------------------------------------------

/**
 * Five preset colors sourced from the group color picker.
 * Hex values match the canonical values in GROUP_CONSTANTS.COLOR_OPTIONS.
 */
export const PRESET_COLORS: ColorOption[] = [
  { hex: '#64748b', name: 'Slate' },
  { hex: '#3b82f6', name: 'Blue' },
  { hex: '#22c55e', name: 'Green' },
  { hex: '#f59e0b', name: 'Amber' },
  { hex: '#f43f5e', name: 'Rose' },
];

/**
 * Extended palette for unique entity type default colors.
 * 12 distinct hues that cycle for newly created entity types.
 */
export const ENTITY_TYPE_DEFAULT_COLORS: string[] = [
  '#3b82f6', // Blue
  '#22c55e', // Green
  '#f59e0b', // Amber
  '#f43f5e', // Rose
  '#8b5cf6', // Violet
  '#06b6d4', // Cyan
  '#f97316', // Orange
  '#ec4899', // Pink
  '#14b8a6', // Teal
  '#84cc16', // Lime
  '#6366f1', // Indigo
  '#a855f7', // Purple
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns true when `hex` is a valid CSS hex color string.
 * Accepts the forms: #RGB, #RRGGBB (case-insensitive, leading # required).
 */
export function isValidHex(hex: string): boolean {
  return /^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/.test(hex);
}
