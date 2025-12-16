/**
 * Context sync API service functions
 *
 * API client for bi-directional synchronization of context entities between
 * user collections and deployed projects.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Resolution type for sync conflict resolution
 */
export type SyncResolution = 'keep_local' | 'keep_remote' | 'merge';

/**
 * Sync result for a single entity
 */
export interface SyncResult {
  entity_id: string;
  entity_name: string;
  action: 'pulled' | 'pushed' | 'resolved' | 'conflict' | 'skipped';
  message: string;
}

/**
 * Sync conflict between collection and project
 */
export interface SyncConflict {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  collection_hash: string;
  deployed_hash: string;
  collection_content: string;
  deployed_content: string;
  collection_path: string;
  deployed_path: string;
}

/**
 * Sync status response
 */
export interface SyncStatus {
  modified_in_project: string[];
  modified_in_collection: string[];
  conflicts: SyncConflict[];
}

/**
 * Pull changes from project to collection
 *
 * Reads deployed files and updates collection entities with new content.
 */
export async function pullChanges(
  projectPath: string,
  entityIds?: string[]
): Promise<SyncResult[]> {
  const response = await fetch(buildUrl('/context-sync/pull'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_path: projectPath,
      entity_ids: entityIds,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to pull changes: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Push collection changes to project
 *
 * Writes collection entity content to deployed files.
 */
export async function pushChanges(
  projectPath: string,
  entityIds?: string[],
  overwrite: boolean = false
): Promise<SyncResult[]> {
  const response = await fetch(buildUrl('/context-sync/push'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_path: projectPath,
      entity_ids: entityIds,
      overwrite,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to push changes: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get sync status for a project
 *
 * Detects modified entities and conflicts between collection and project.
 */
export async function getSyncStatus(projectPath: string): Promise<SyncStatus> {
  const params = new URLSearchParams({ project_path: projectPath });
  const response = await fetch(buildUrl(`/context-sync/status?${params.toString()}`));

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to get sync status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Resolve sync conflict
 *
 * Applies user-selected resolution strategy:
 * - keep_local: Update collection from project (project wins)
 * - keep_remote: Update project from collection (collection wins)
 * - merge: Use provided merged_content for both
 */
export async function resolveConflict(
  projectPath: string,
  entityId: string,
  resolution: SyncResolution,
  mergedContent?: string
): Promise<SyncResult> {
  const response = await fetch(buildUrl('/context-sync/resolve'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_path: projectPath,
      entity_id: entityId,
      resolution,
      merged_content: mergedContent,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to resolve conflict: ${response.statusText}`);
  }

  return response.json();
}
