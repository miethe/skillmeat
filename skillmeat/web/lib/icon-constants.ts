/**
 * Shared icon constants for site-wide icon management.
 *
 * DEFAULT_ICONS mirrors the six Lucide icons currently used in the group
 * metadata editor (see lib/group-constants.ts → GROUP_ICONS).
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface IconOption {
  name: string;
  label?: string;
}

export interface IconPack {
  id: string;
  name: string;
  icons: IconOption[];
  enabled: boolean;
}

// ---------------------------------------------------------------------------
// Default icons
// ---------------------------------------------------------------------------

/**
 * The six default Lucide icons used in the group metadata editor.
 * Names match the Lucide icon name format (lowercase, hyphen-separated).
 */
export const DEFAULT_ICONS: IconOption[] = [
  { name: 'layers', label: 'Layers' },
  { name: 'folder', label: 'Folder' },
  { name: 'tag', label: 'Tag' },
  { name: 'sparkles', label: 'Sparkles' },
  { name: 'book', label: 'Book' },
  { name: 'wrench', label: 'Wrench' },
];

/**
 * The built-in icon pack wrapping the six default Lucide icons.
 * Enabled by default; additional packs can be added in the future.
 */
export const DEFAULT_ICON_PACK: IconPack = {
  id: 'lucide-default',
  name: 'Lucide (Default)',
  icons: DEFAULT_ICONS,
  enabled: true,
};
