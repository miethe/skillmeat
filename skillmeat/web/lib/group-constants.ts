import { Book, Folder, Layers, Sparkles, Tag, Wrench } from 'lucide-react';
import type { ComponentType } from 'react';

// ---------------------------------------------------------------------------
// Color constants
// ---------------------------------------------------------------------------

export const GROUP_COLORS = ['slate', 'blue', 'green', 'amber', 'rose'] as const;

export type GroupColorToken = (typeof GROUP_COLORS)[number];

/** A color token name OR a hex string (#RRGGBB). */
export type GroupColor = GroupColorToken | string;

export const COLOR_OPTIONS: Array<{
  value: GroupColorToken;
  label: string;
  hex: string;
}> = [
  { value: 'slate', label: 'Slate', hex: '#64748b' },
  { value: 'blue', label: 'Blue', hex: '#3b82f6' },
  { value: 'green', label: 'Green', hex: '#22c55e' },
  { value: 'amber', label: 'Amber', hex: '#f59e0b' },
  { value: 'rose', label: 'Rose', hex: '#f43f5e' },
];

export const COLOR_HEX_BY_TOKEN: Record<GroupColorToken, string> = Object.fromEntries(
  COLOR_OPTIONS.map((option) => [option.value, option.hex.toLowerCase()])
) as Record<GroupColorToken, string>;

/** Tailwind border-left classes keyed by color token. */
export const COLOR_TAILWIND_CLASSES: Record<string, string> = {
  slate: 'border-l-slate-500',
  blue: 'border-l-blue-500',
  green: 'border-l-green-500',
  amber: 'border-l-amber-500',
  rose: 'border-l-rose-500',
};

// ---------------------------------------------------------------------------
// Icon constants
// ---------------------------------------------------------------------------

export const GROUP_ICONS = ['layers', 'folder', 'tag', 'sparkles', 'book', 'wrench'] as const;

export type GroupIcon = (typeof GROUP_ICONS)[number];

export const ICON_OPTIONS: Array<{
  value: GroupIcon;
  label: string;
  Icon: ComponentType<{ className?: string }>;
}> = [
  { value: 'layers', label: 'Layers', Icon: Layers },
  { value: 'folder', label: 'Folder', Icon: Folder },
  { value: 'tag', label: 'Tag', Icon: Tag },
  { value: 'sparkles', label: 'Sparkles', Icon: Sparkles },
  { value: 'book', label: 'Book', Icon: Book },
  { value: 'wrench', label: 'Wrench', Icon: Wrench },
];

/** Lucide icon components keyed by icon token name. */
export const ICON_MAP: Record<GroupIcon, ComponentType<{ className?: string }>> =
  Object.fromEntries(ICON_OPTIONS.map((option) => [option.value, option.Icon])) as Record<
    GroupIcon,
    ComponentType<{ className?: string }>
  >;

// ---------------------------------------------------------------------------
// Color helper functions
// ---------------------------------------------------------------------------

export function isColorToken(value: string): value is GroupColorToken {
  return value in COLOR_HEX_BY_TOKEN;
}

export function normalizeHex(value: string): string {
  const hex = value.trim().replace(/^#/, '').toLowerCase();
  if (/^[0-9a-f]{8}$/.test(hex)) {
    return `#${hex.slice(0, 6)}`;
  }
  if (/^[0-9a-f]{3}$/.test(hex)) {
    return `#${hex
      .split('')
      .map((part) => `${part}${part}`)
      .join('')}`;
  }
  if (/^[0-9a-f]{6}$/.test(hex)) {
    return `#${hex}`;
  }
  return COLOR_HEX_BY_TOKEN.slate;
}

export function resolveColorHex(value: GroupColor): string {
  if (isColorToken(value)) {
    return COLOR_HEX_BY_TOKEN[value];
  }
  return normalizeHex(value);
}

export function dedupeHexColors(values: string[]): string[] {
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const value of values) {
    const next = normalizeHex(value);
    if (seen.has(next)) {
      continue;
    }
    seen.add(next);
    normalized.push(next);
  }
  return normalized;
}

export function hexToRgb(hex: string): [number, number, number] {
  const normalized = normalizeHex(hex).replace('#', '');
  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);
  return [r, g, b];
}

export function getClosestColorToken(hex: string): GroupColorToken {
  const normalizedHex = normalizeHex(hex);
  const normalizedRgb = hexToRgb(normalizedHex);

  let nearest: GroupColorToken = 'slate';
  let minDistance = Number.POSITIVE_INFINITY;

  for (const option of COLOR_OPTIONS) {
    const [r, g, b] = hexToRgb(option.hex);
    const distance =
      (normalizedRgb[0] - r) ** 2 + (normalizedRgb[1] - g) ** 2 + (normalizedRgb[2] - b) ** 2;
    if (distance < minDistance) {
      nearest = option.value;
      minDistance = distance;
    }
  }

  return nearest;
}

/** Returns true if `hex` exactly matches one of the preset COLOR_OPTIONS hex values. */
export function isPresetHex(hex: string): boolean {
  return COLOR_OPTIONS.some((option) => normalizeHex(option.hex) === hex);
}
