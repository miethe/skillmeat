/**
 * Custom Colors API service functions
 *
 * Provides functions for managing user-defined custom colors.
 * Endpoints: /api/v1/colors
 */

import type { ColorOption } from '@/lib/color-constants';

// ---------------------------------------------------------------------------
// Request / response shapes
// ---------------------------------------------------------------------------

export interface ColorCreateRequest {
  hex: string;
  name?: string;
}

export interface ColorUpdateRequest {
  hex?: string;
  name?: string;
}

// The API response shape mirrors ColorOption, plus a server-assigned `id`.
export interface ColorResponse extends ColorOption {
  id: string;
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
 * Fetch all custom colors
 */
export async function fetchCustomColors(): Promise<ColorResponse[]> {
  const response = await fetch(buildUrl('/colors'));
  if (!response.ok) {
    throw new Error(`Failed to fetch custom colors: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create a new custom color
 */
export async function createCustomColor(data: ColorCreateRequest): Promise<ColorResponse> {
  const response = await fetch(buildUrl('/colors'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      (errorBody as { detail?: string }).detail ||
        `Failed to create custom color: ${response.statusText}`
    );
  }
  return response.json();
}

/**
 * Update an existing custom color
 */
export async function updateCustomColor(
  id: string,
  data: ColorUpdateRequest
): Promise<ColorResponse> {
  const response = await fetch(buildUrl(`/colors/${id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      (errorBody as { detail?: string }).detail ||
        `Failed to update custom color: ${response.statusText}`
    );
  }
  return response.json();
}

/**
 * Delete a custom color
 */
export async function deleteCustomColor(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/colors/${id}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      (errorBody as { detail?: string }).detail ||
        `Failed to delete custom color: ${response.statusText}`
    );
  }
}
