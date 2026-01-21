/**
 * Merge and conflict resolution API service functions
 */
import type {
  MergeAnalyzeRequest,
  MergeSafetyResponse,
  MergePreviewResponse,
  MergeExecuteRequest,
  MergeExecuteResponse,
  ConflictResolveRequest,
  ConflictResolveResponse,
} from '@/types/merge';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Convert camelCase to snake_case for API requests
 */
function toSnakeCase(obj: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {};
  for (const [key, value] of Object.entries(obj)) {
    const snakeKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
    result[snakeKey] = value;
  }
  return result;
}

/**
 * Convert snake_case to camelCase for API responses
 */
function toCamelCase(obj: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {};
  for (const [key, value] of Object.entries(obj)) {
    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
    if (Array.isArray(value)) {
      result[camelKey] = value.map((item) =>
        typeof item === 'object' && item !== null ? toCamelCase(item) : item
      );
    } else if (typeof value === 'object' && value !== null) {
      result[camelKey] = toCamelCase(value);
    } else {
      result[camelKey] = value;
    }
  }
  return result;
}

/**
 * Analyze merge safety between snapshots
 */
export async function analyzeMergeSafety(
  request: MergeAnalyzeRequest
): Promise<MergeSafetyResponse> {
  const response = await fetch(buildUrl('/merge/analyze'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toSnakeCase(request)),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to analyze merge: ${response.statusText}`);
  }

  const data = await response.json();
  return toCamelCase(data) as MergeSafetyResponse;
}

/**
 * Preview merge changes between snapshots
 */
export async function previewMerge(request: MergeAnalyzeRequest): Promise<MergePreviewResponse> {
  const response = await fetch(buildUrl('/merge/preview'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toSnakeCase(request)),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to preview merge: ${response.statusText}`);
  }

  const data = await response.json();
  return toCamelCase(data) as MergePreviewResponse;
}

/**
 * Execute merge between snapshots
 */
export async function executeMerge(request: MergeExecuteRequest): Promise<MergeExecuteResponse> {
  const response = await fetch(buildUrl('/merge/execute'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toSnakeCase(request)),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to execute merge: ${response.statusText}`);
  }

  const data = await response.json();
  return toCamelCase(data) as MergeExecuteResponse;
}

/**
 * Resolve a merge conflict
 */
export async function resolveConflict(
  request: ConflictResolveRequest
): Promise<ConflictResolveResponse> {
  const response = await fetch(buildUrl('/merge/resolve'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toSnakeCase(request)),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to resolve conflict: ${response.statusText}`);
  }

  const data = await response.json();
  return toCamelCase(data) as ConflictResolveResponse;
}
