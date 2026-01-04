/**
 * Marketplace API service functions
 */
import type { InferUrlResponse } from '@/types/marketplace';

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
