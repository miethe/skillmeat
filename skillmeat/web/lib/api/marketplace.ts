/**
 * Marketplace API service functions
 */
import type { InferUrlResponse } from '@/types/marketplace';
import type { PathSegmentsResponse } from '@/types/path-tags';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Infer repository structure from GitHub URL
 */
export async function inferUrl(url: string): Promise<InferUrlResponse> {
  const response = await fetch(buildUrl('/marketplace/sources/infer-url'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to infer URL: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get extracted path tag segments for a marketplace catalog entry
 */
export async function getPathTags(
  sourceId: string,
  entryId: string
): Promise<PathSegmentsResponse> {
  const response = await fetch(
    buildUrl(`/marketplace/sources/${sourceId}/catalog/${entryId}/path-tags`)
  );
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to get path tags: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Update status of a specific path tag segment (approve or reject)
 */
export async function updatePathTagStatus(
  sourceId: string,
  entryId: string,
  segment: string,
  status: 'approved' | 'rejected'
): Promise<PathSegmentsResponse> {
  const response = await fetch(
    buildUrl(`/marketplace/sources/${sourceId}/catalog/${entryId}/path-tags`),
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ segment, status }),
    }
  );
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to update path tag status: ${response.statusText}`);
  }
  return response.json();
}

// ============================================================================
// Source Auto-Tags (GitHub Topics)
// ============================================================================

import type {
  AutoTagsResponse,
  UpdateAutoTagRequest,
  UpdateAutoTagResponse,
} from '@/types/marketplace';

/**
 * Get auto-tag suggestions for a marketplace source (from GitHub topics)
 */
export async function getSourceAutoTags(sourceId: string): Promise<AutoTagsResponse> {
  const response = await fetch(buildUrl(`/marketplace/sources/${sourceId}/auto-tags`));
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch auto-tags: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Update the status of a source auto-tag (approve or reject)
 */
export async function updateSourceAutoTag(
  sourceId: string,
  request: UpdateAutoTagRequest
): Promise<UpdateAutoTagResponse> {
  const response = await fetch(buildUrl(`/marketplace/sources/${sourceId}/auto-tags`), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to update auto-tag: ${response.statusText}`);
  }
  return response.json();
}
