/**
 * Icon Packs API service functions
 *
 * Provides functions for managing icon pack settings.
 * Endpoints: /api/v1/settings/icon-packs
 */

import type { IconPack } from '@/lib/icon-constants';

// ---------------------------------------------------------------------------
// Request shapes
// ---------------------------------------------------------------------------

export interface IconPackPatchEntry {
  pack_id: string;
  enabled: boolean;
}

// ---------------------------------------------------------------------------
// Transport
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * Fetch all icon packs with their enabled state
 */
export async function fetchIconPacks(): Promise<IconPack[]> {
  const response = await fetch(buildUrl('/settings/icon-packs'));
  if (!response.ok) {
    throw new Error(`Failed to fetch icon packs: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Patch icon pack enabled states
 *
 * Accepts an array of `{ pack_id, enabled }` objects so the caller can toggle
 * one or many packs in a single request.
 */
export async function patchIconPacks(entries: IconPackPatchEntry[]): Promise<IconPack[]> {
  const response = await fetch(buildUrl('/settings/icon-packs'), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entries),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      (errorBody as { detail?: string }).detail ||
        `Failed to patch icon packs: ${response.statusText}`
    );
  }
  return response.json();
}
