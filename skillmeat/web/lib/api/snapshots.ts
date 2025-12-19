/**
 * Version snapshot API service functions
 */
import type {
  Snapshot,
  SnapshotListResponse,
  CreateSnapshotRequest,
  CreateSnapshotResponse,
  RollbackSafetyAnalysis,
  RollbackRequest,
  RollbackResponse,
  DiffSnapshotsRequest,
  SnapshotDiff,
} from '@/types/snapshot';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Fetch paginated list of snapshots
 * @param filters - Optional filters for collection name, limit, and pagination
 */
export async function fetchSnapshots(filters?: {
  collectionName?: string;
  limit?: number;
  after?: string;
}): Promise<SnapshotListResponse> {
  const params = new URLSearchParams();
  if (filters?.collectionName) params.set('collection_name', filters.collectionName);
  if (filters?.limit) params.set('limit', filters.limit.toString());
  if (filters?.after) params.set('after', filters.after);

  const url = buildUrl(`/versions/snapshots${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch snapshots: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch single snapshot by ID
 * @param id - Snapshot SHA-256 hash identifier
 * @param collectionName - Optional collection name
 */
export async function fetchSnapshot(
  id: string,
  collectionName?: string
): Promise<Snapshot> {
  const params = new URLSearchParams();
  if (collectionName) params.set('collection_name', collectionName);

  const url = buildUrl(`/versions/snapshots/${id}${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch snapshot: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create new version snapshot
 * @param data - Snapshot creation request data
 */
export async function createSnapshot(
  data: CreateSnapshotRequest
): Promise<CreateSnapshotResponse> {
  const response = await fetch(buildUrl('/versions/snapshots'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      collection_name: data.collectionName,
      message: data.message || 'Manual snapshot',
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create snapshot: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete snapshot by ID
 * @param id - Snapshot SHA-256 hash identifier
 * @param collectionName - Optional collection name
 */
export async function deleteSnapshot(
  id: string,
  collectionName?: string
): Promise<void> {
  const params = new URLSearchParams();
  if (collectionName) params.set('collection_name', collectionName);

  const url = buildUrl(`/versions/snapshots/${id}${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete snapshot: ${response.statusText}`);
  }
  // DELETE returns 204 No Content
}

/**
 * Analyze rollback safety for a snapshot
 * @param snapshotId - Snapshot SHA-256 hash identifier
 * @param collectionName - Optional collection name
 */
export async function analyzeRollbackSafety(
  snapshotId: string,
  collectionName?: string
): Promise<RollbackSafetyAnalysis> {
  const params = new URLSearchParams();
  if (collectionName) params.set('collection_name', collectionName);

  const url = buildUrl(`/versions/snapshots/${snapshotId}/rollback-analysis${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to analyze rollback safety: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Execute rollback to a snapshot
 * @param snapshotId - Snapshot SHA-256 hash identifier
 * @param data - Rollback request configuration
 */
export async function executeRollback(
  snapshotId: string,
  data: RollbackRequest
): Promise<RollbackResponse> {
  const response = await fetch(buildUrl(`/versions/snapshots/${snapshotId}/rollback`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      snapshot_id: data.snapshotId,
      collection_name: data.collectionName,
      preserve_changes: data.preserveChanges ?? true,
      selective_paths: data.selectivePaths,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to execute rollback: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Compare two snapshots and get diff
 * @param data - Snapshot IDs to compare
 */
export async function diffSnapshots(
  data: DiffSnapshotsRequest
): Promise<SnapshotDiff> {
  const response = await fetch(buildUrl('/versions/snapshots/diff'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      snapshot_id_1: data.snapshotId1,
      snapshot_id_2: data.snapshotId2,
      collection_name: data.collectionName,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to diff snapshots: ${response.statusText}`);
  }

  return response.json();
}
